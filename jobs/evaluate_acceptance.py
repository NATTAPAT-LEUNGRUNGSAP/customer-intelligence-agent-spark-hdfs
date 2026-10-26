"""Frozen-source acceptance + exposed regression + paired context evaluation."""
import hashlib
import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from agent import answer
from evaluate import same_result, summarize
from provenance import fingerprint
from query_runtime import load_views, run_query
from sql_guard import validate_sql
from rag_metrics import retrieval_metrics, percentile95
from policy_engine import authorize, policy_facts


def main():
    from pyspark.sql import SparkSession
    root=Path('/app')
    cases=json.loads((root/'evaluation/acceptance.json').read_text(encoding='utf-8'))
    regression=json.loads((root/'evaluation/rag_holdout_v6.json').read_text(encoding='utf-8'))
    exposed=root/'evaluation/acceptance_exposed.json'
    if exposed.exists():regression+=json.loads(exposed.read_text(encoding='utf-8'))
    gates=json.loads((root/'evaluation/quality_gates_v2.json').read_text())['end_to_end']
    model,endpoint='qwen3.5:9b','http://host.docker.internal:11434'
    output=root/'reports'/('acceptance-'+uuid.uuid4().hex+'.json')
    record={'status':'running','started_at_utc':datetime.now(timezone.utc).isoformat(),
            'benchmark':'acceptance.json','description':'60 newly authored supported-family combinations; not independent external validation',
            'acceptance':[],'regression':[],'context':[],'policy_integration':[],
            'gates':gates,'context_protocol':{'cases':12,'strategies':['clean','managed','unfiltered'],
              'background_characters':3000,'rag_in_all_conditions':True,
              'success_metric':'actual result vs independently executed gold, errors/stops count wrong',
              'noise_location':'optional nonauthoritative background outside selected evidence',
              'positions':'front/middle/end cyclic across 12 questions',
              'limits':'12 distinct questions, 36 trials; not proof of general model-internal context rot prevention'}}
    def save():output.write_text(json.dumps(record,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    record['pre_run_provenance']=fingerprint(endpoint=endpoint,model=model)
    record['case_sha256']=hashlib.sha256((root/'evaluation/acceptance.json').read_bytes()).hexdigest()
    # This file is saved before Spark/gold/model output and verified unchanged at the end.
    save()
    spark=SparkSession.builder.appName('customer-intelligence-acceptance').config('spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        schema,manifest=load_views(spark,'/app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json')
        record['build_run_id']=manifest['run_id']
        # Actual OPA integration checks do not rely on mocks or a live LLM judge.
        tests=[('allowed_read',{},True),('forbidden_table',{'tables':['private']},False),
               ('write_denied',{'read_only':False},False),('attempt_cap',{'attempt':4},False),
               ('post_negative_count',{'stage':'post','result_violations':['count_must_be_nonnegative_integer']},False),
               ('post_null_customer',{'stage':'post','result_violations':['identified_customer_id_null']},False),
               ('post_fraction',{'stage':'post','result_violations':['fraction_out_of_range']},False),
               ('post_nan',{'stage':'post','result_violations':['non_finite_numeric_value']},False)]
        for name,changes,expected in tests:
            facts=policy_facts('SELECT count(*) FROM orders',1);facts.update(changes)
            try:decision=authorize(facts);allowed=True
            except ValueError as error:decision={'error':str(error)};allowed=False
            record['policy_integration'].append(dict(name=name,correct=allowed==expected,decision=decision))
        save()
        gold={}
        def run(case,**options):
            if case.get('gold_sql') and case['id'] not in gold:
                gold[case['id']]=run_query(spark,validate_sql(case['gold_sql']))
            expected=gold.get(case['id']);started=time.monotonic()
            try:
                result=answer(case['question'],schema,lambda sql:run_query(spark,sql),model,endpoint,root/'knowledge',**options)
                correct=(result['status']=='executed' and same_result(result['result'],expected,case.get('ordered',False)) if expected is not None else result['status']=='clarification' and case.get('clarification_policy') in result.get('citations',[]))
            except Exception as error:result,correct={'status':'error','error':str(error)},False
            citations=result.get('citations',[])
            retrieved=result.get('retrieval',{})
            row={'id':case['id'],'question':case['question'],'correct':correct,'expected':'result' if expected else 'clarification',
                 'gold':expected,'result':result,'elapsed_seconds':time.monotonic()-started,
                 'citation_valid':bool(citations) and set(citations).issubset({r['id'] for r in result.get('references',[])}),
                 'cites_relevant':bool(set(citations)&set(case['relevant_ids'])),
                 'retrieval_metrics':retrieval_metrics(retrieved.get('ranked_ids',[]),case['relevant_ids'],retrieved.get('context_ids',[]))}
            return row
        for split,items in [('regression',regression),('acceptance',cases)]:
            for case in items:
                row=run(case);record[split].append(row);save()
                print(split,case['id'],row['correct'],row['result'].get('status'),flush=True)
            if split=='regression' and not all(c['correct'] for c in record[split]):
                record.update(status='blocked_by_regression',acceptance_exposed_count=0)
                save()
                print('Regression failed; acceptance not exposed',flush=True)
                return
        # Exposed after the first run: this is a paired stress experiment, not another fresh holdout.
        chosen=[cases[i] for i in (0,4,8,12,16,20,24,28,32,36,40,44)]
        noise=('Archived optional background about office furniture and weather; not a metric definition. '*40)[:3000]
        matrix=[(c,i,strategy) for i,c in enumerate(chosen) for strategy in ('clean','managed','unfiltered')]
        random.Random(20261026).shuffle(matrix)
        for case,i,strategy in matrix:
            options={} if strategy=='clean' else {'context_strategy':strategy,'background':noise,'evidence_position':('front','middle','end')[i%3]}
            row=run(case,**options);row['condition']=strategy;record['context'].append(row);save()
            print('context',case['id'],strategy,row['correct'],flush=True)
        record['summary']={};record['checks']={}
        for split in ('acceptance','regression'):
            record['summary'][split],record['checks'][split]=summarize(record[split],gates)
        for strategy in ('clean','managed','unfiltered'):
            rows=[r for r in record['context'] if r['condition']==strategy]
            usages=[u for r in rows for u in r['result'].get('context_usage',[]) if u.get('prompt_eval_count')]
            record['summary'][strategy]={'correct':sum(r['correct'] for r in rows),'total':len(rows),
                'blocked_before_model':sum(r['result'].get('context_blocked',False) and r['result'].get('model_calls',0)==0 for r in rows),
                'blocked_during_repair':sum(r['result'].get('context_blocked',False) and r['result'].get('model_calls',0)>0 for r in rows),
                'other_failed':sum(not r['correct'] and not r['result'].get('context_blocked',False) for r in rows),
                'retained_evidence':sum(r['result'].get('context_plan',{}).get('all_selected_evidence_retained',False) for r in rows),
                'prompt_tokens_min':min((u['prompt_eval_count'] for u in usages),default=None),
                'prompt_tokens_max':max((u['prompt_eval_count'] for u in usages),default=None)}
        record['post_run_provenance']=fingerprint(endpoint=endpoint,model=model)
        record['source_unchanged']=record['pre_run_provenance']==record['post_run_provenance']
        record['quality_passed']=all(all(c.values()) for c in record['checks'].values()) and record['source_unchanged'] and all(r['correct'] for r in record['policy_integration'])
        record.update(status='completed',ended_at_utc=datetime.now(timezone.utc).isoformat());save()
        print(json.dumps({'report':str(output),'summary':record['summary'],'quality_passed':record['quality_passed']}),flush=True)
    except Exception as error:
        record.update(status='failed',error=str(error));save();raise
    finally:spark.stop()


if __name__=='__main__':main()
