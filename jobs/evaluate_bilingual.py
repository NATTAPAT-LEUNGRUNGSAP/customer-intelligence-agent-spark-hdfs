"""Exposed bilingual development evaluation; SQL oracles never reach the agent."""
import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from retrieval import retrieve_context
from rag_metrics import retrieval_metrics,percentile95
from provenance import fingerprint


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--retrieval-only',action='store_true')
    parser.add_argument('--output',required=True)
    parser.add_argument('--ids',nargs='*')
    args=parser.parse_args()
    root=Path('/app'); path=root/'evaluation/bilingual_200.json'
    cases=json.loads(path.read_text(encoding='utf-8'))
    if args.ids:cases=[c for c in cases if c['id'] in args.ids]
    record={'status':'running','purpose':'exposed development bank, not an independent holdout',
            'started_at_utc':datetime.now(timezone.utc).isoformat(),
            'bank_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cases':[]}
    model,endpoint='qwen3.5:9b','http://host.docker.internal:11434'
    record['pre_run_provenance']=fingerprint(endpoint=None if args.retrieval_only else endpoint,model=model)
    output=Path(args.output)
    def save():
        body=json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n'
        pending=output.with_suffix(output.suffix+'.pending')
        for attempt in range(12):
            try:
                pending.write_text(body,encoding='utf-8')
                try:pending.replace(output)
                except OSError:
                    # Some Windows bind mounts keep target handles open. The
                    # complete pending file remains recoverable during retry.
                    output.write_text(body,encoding='utf-8')
                    try:pending.unlink()
                    except OSError:pass
                return
            except OSError:
                if attempt==11:raise
                time.sleep(0.1)
    save(); spark=None
    try:
        if not args.retrieval_only:
            from pyspark.sql import SparkSession
            from query_runtime import load_views,run_query
            from sql_guard import validate_sql
            from agent import answer
            from evaluate import same_result
            spark=SparkSession.builder.appName('bilingual-development').config('spark.sql.session.timeZone','UTC').getOrCreate()
            spark.sparkContext.setLogLevel('WARN')
            schema,manifest=load_views(spark,'/app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json')
            record['build_run_id']=manifest['run_id']
            # Execute every gold SQL before any model call; invalid oracles stop the run.
            gold={}
            for c in cases:
                if c.get('gold_sql') and c['pair_id'] not in gold:
                    gold[c['pair_id']]=run_query(spark,validate_sql(c['gold_sql']))
            record['gold_queries_executed']=len(gold);save()
        for c in cases:
            started=time.monotonic()
            refs,retrieval=retrieve_context(c['question'],root/'knowledge')
            row={'id':c['id'],'pair_id':c['pair_id'],'language':c['language'],'family':c['family'],
                 'question':c['question'],'retrieval':retrieval,
                 'retrieval_metrics':retrieval_metrics(retrieval['ranked_ids'],c['relevant_ids'],retrieval['context_ids'])}
            if not args.retrieval_only:
                try:
                    result=answer(c['question'],schema,lambda sql:run_query(spark,sql),model,endpoint,root/'knowledge')
                    if c.get('gold_sql'):
                        correct=result['status']=='executed' and same_result(result['result'],gold[c['pair_id']],c['ordered'])
                        row['gold']=gold[c['pair_id']]
                    elif c.get('formula_id'):
                        correct=result.get('intent')=='formula' and result.get('formula_id')==c['formula_id'] and result.get('model_calls')==0 and not result.get('sql_executed',False)
                    else:
                        correct=result['status']=='clarification' and c['clarification_policy'] in result.get('citations',[])
                    row.update(result=result,correct=correct)
                    row['citation_valid']=bool(result.get('citations')) and set(result['citations']).issubset({r['id'] for r in result.get('references',[])})
                except Exception as error:row.update(correct=False,result={'status':'error','error':str(error)})
            row['elapsed_seconds']=time.monotonic()-started
            record['cases'].append(row);save()
            print(c['id'],row.get('correct'),row.get('result',{}).get('status'),flush=True)
        record['summary']={}
        for lang in ('th','en','all'):
            rows=[r for r in record['cases'] if lang=='all' or r['language']==lang]
            record['summary'][lang]={'total':len(rows),'retrieval':{key:sum(r['retrieval_metrics'][key] for r in rows)/len(rows) for key in rows[0]['retrieval_metrics']}}
            if not args.retrieval_only:
                record['summary'][lang].update(correct=sum(r['correct'] for r in rows),
                    by_family={family:{'correct':sum(r['correct'] for r in rows if r['family']==family),'total':sum(r['family']==family for r in rows)} for family in sorted({r['family'] for r in rows})},
                    statuses=dict(Counter(r['result']['status'] for r in rows)),
                    latency_p95_seconds=percentile95([r['elapsed_seconds'] for r in rows]))
        record['post_run_provenance']=fingerprint(endpoint=None if args.retrieval_only else endpoint,model=model)
        record['source_unchanged']=record['pre_run_provenance']==record['post_run_provenance']
        record['bank_unchanged']=record['bank_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        record.update(status='completed',ended_at_utc=datetime.now(timezone.utc).isoformat());save()
        print(json.dumps(record['summary'],ensure_ascii=False),flush=True)
    except Exception as error:
        record.update(status='failed',error=str(error));save();raise
    finally:
        if spark:spark.stop()


if __name__=='__main__':main()
