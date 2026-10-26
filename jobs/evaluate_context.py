"""Actual Spark/model regression and predeclared context stress; RAG in all arms."""
import hashlib
import argparse
import json
import random
import time
import uuid
from pathlib import Path
from agent import answer
from context_engine import compact_json
from evaluate import same_result
from provenance import fingerprint
from query_runtime import load_views, run_query
from sql_guard import validate_sql
from rag_metrics import percentile95


def main():
    from pyspark.sql import SparkSession
    parser=argparse.ArgumentParser()
    parser.add_argument('--protocol',default='context_protocol_v2.json')
    args=parser.parse_args()
    if args.protocol not in ('context_protocol_v1.json','context_protocol_v2.json'):
        parser.error('Use a versioned context protocol')
    spark=SparkSession.builder.appName('customer-intelligence-context-evaluation').config(
        'spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    protocol=json.loads(Path('/app/evaluation',args.protocol).read_text(encoding='utf-8'))
    cases=json.loads(Path('/app/evaluation/rag_holdout_v6.json').read_text(encoding='utf-8'))
    endpoint,model='http://host.docker.internal:11434',protocol['model']
    output=Path('/app/reports')/f"{protocol['version']}-{uuid.uuid4().hex}.json"
    report={'version':protocol['version'],'status':'running','fresh_holdout':False,'protocol':protocol,
            'regression':[],'stress':[]}
    def save():
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    try:
        schema,manifest=load_views(spark,'/app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json')
        report.update(provenance=fingerprint(endpoint=endpoint,model=model),build_run_id=manifest['run_id'])
        # One frozen pre-output inventory for this exposed-case experiment.
        report['pre_run_fingerprint_recorded']=True
        save()
        gold={c['id']:run_query(spark,validate_sql(c['gold_sql'])) for c in cases if c.get('gold_sql')}
        def run(case,**options):
            started=time.monotonic()
            try:
                result=answer(case['question'],schema,lambda sql:run_query(spark,sql),
                              model,endpoint,'/app/knowledge',**options)
                expected=gold.get(case['id'])
                correct=(result['status']=='clarification' if expected is None else
                    result['status']=='executed' and same_result(result['result'],expected,case.get('ordered',False)))
            except Exception as error:
                result,correct={'status':'error','error':str(error)},False
            if result.get('context_plan'):
                evidence=[{'id':c['id'],'text':c['text']} for c in result['references']]
                expected_hash=hashlib.sha256(compact_json(evidence).encode()).hexdigest()
                retained=(result['context_plan']['selected_evidence_sha256']==expected_hash
                          and result['context_plan']['selected_ids']==[r['id'] for r in evidence])
            else:
                retained=False
            return {'id':case['id'],'correct':correct,'elapsed_seconds':time.monotonic()-started,
                    'selected_evidence_retained':retained,'result':result}
        for case in cases:
            row=run(case)
            report['regression'].append(row)
            save()
            print('regression',case['id'],row['correct'],flush=True)
        matrix=[]
        selected=[c for c in cases if c['id'] in protocol['case_ids']]
        for case in selected:
            for length in protocol['background_characters']:
                positions=protocol['evidence_positions'] if length else [protocol['zero_background_position']]
                for position in positions:
                    for strategy in protocol['strategies']:
                        matrix.append((case,length,position,strategy))
        random.Random(protocol['shuffle_seed']).shuffle(matrix)
        noise=('Archived nonauthoritative background about office furniture, weather and packaging. '
               'These notes do not define sales metrics, table grain or the requested population. ')
        for index,(case,length,position,strategy) in enumerate(matrix):
            background=(noise*(length//len(noise)+1))[:length]
            row=run(case,context_strategy=strategy,background=background,evidence_position=position)
            row.update(strategy=strategy,background_characters=length,evidence_position=position)
            report['stress'].append(row)
            save()
            print('stress',index+1,len(matrix),case['id'],strategy,length,position,row['correct'],
                  row['result'].get('context_blocked',False),flush=True)
        summary={}
        for strategy in protocol['strategies']:
            rows=[r for r in report['stress'] if r['strategy']==strategy]
            admitted=[r for r in rows if not r['result'].get('context_blocked')]
            usages=[u for r in rows for u in r['result'].get('context_usage',[]) if u.get('prompt_eval_count')]
            summary[strategy]={'total':len(rows),'correct':sum(r['correct'] for r in rows),
                'accuracy':sum(r['correct'] for r in rows)/len(rows),
                'budget_blocks':len(rows)-len(admitted),
                'admitted_count':len(admitted),'admitted_correct':sum(r['correct'] for r in admitted),
                'admitted_accuracy':sum(r['correct'] for r in admitted)/len(admitted) if admitted else None,
                'incorrect_admitted_answers':sum(not r['correct'] for r in admitted),
                'selected_evidence_retention':sum(r['selected_evidence_retained'] for r in rows)/len(rows),
                'unique_packet_hashes':len({r['result'].get('context_plan',{}).get('packet_sha256') for r in rows}),
                'actual_prompt_tokens_min':min((u['prompt_eval_count'] for u in usages),default=None),
                'actual_prompt_tokens_max':max((u['prompt_eval_count'] for u in usages),default=None),
                'actual_prompt_tokens_mean':sum(u['prompt_eval_count'] for u in usages)/len(usages) if usages else None,
                'mean_estimate_minus_actual':sum(u['estimated_input_tokens']-u['prompt_eval_count'] for u in usages)/len(usages) if usages else None,
                'latency_p95_seconds':percentile95([r['elapsed_seconds'] for r in rows])}
        thresholds=protocol['stress_acceptance']
        checks={'managed_accuracy':summary['managed']['accuracy']>=thresholds['managed_accuracy_min'],
                'retention':all(v['selected_evidence_retention']==thresholds['selected_evidence_retention'] for v in summary.values()),
                'managed_blocks':summary['managed']['budget_blocks']<=thresholds['managed_budget_blocks_max'],
                'regression_accuracy':sum(r['correct'] for r in report['regression'])/len(cases)>=protocol.get('regression_accuracy_min',0.9)}
        report.update(status='completed',summary=summary,checks=checks,quality_passed=all(checks.values()),
                      regression_correct=sum(r['correct'] for r in report['regression']),regression_total=len(cases))
        save()
        print(json.dumps({'report':str(output),'summary':summary,'checks':checks}),flush=True)
    except Exception as error:
        report.update(status='failed',error=str(error),quality_passed=False)
        save()
        raise
    finally:
        spark.stop()


if __name__=='__main__':
    main()
