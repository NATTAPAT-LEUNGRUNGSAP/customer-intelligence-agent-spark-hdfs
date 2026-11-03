"""Targeted development diagnostic; gold SQL never enters the agent context."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    if args.baseline:sys.path.insert(0,'/baseline')
    from agent import answer
    from query_runtime import load_views,run_query
    from sql_guard import validate_sql
    from evaluate import same_result
    from provenance import fingerprint
    from pyspark.sql import SparkSession
    endpoint='http://host.docker.internal:11434';model='qwen3.5:9b'
    bank=Path('/app/evaluation/answerability_aggregation.json')
    cases=json.loads(bank.read_text(encoding='utf-8'))
    record={'status':'running','purpose':'targeted exposed development diagnostic, not holdout',
            'mode':'prior_source' if args.baseline else 'candidate',
            'bank_sha256':hashlib.sha256(bank.read_bytes()).hexdigest(),
            'pre_run_provenance':fingerprint(endpoint=endpoint,model=model),'cases':[]}
    if args.baseline:
        record['baseline_files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/baseline').glob('*.py')}
        record['baseline_commit']='76629c472bdde02c8c4490bf95a5bece468c1ea2'
    output=Path(args.output)
    def save():
        body=json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n'
        for attempt in range(12):
            try:output.write_text(body,encoding='utf-8');return
            except OSError:
                if attempt==11:raise
                time.sleep(.1)
    spark=None
    try:
        spark=SparkSession.builder.appName('aggregation-answerability').config('spark.sql.session.timeZone','UTC').getOrCreate()
        spark.sparkContext.setLogLevel('WARN')
        schema,manifest=load_views(spark,'/app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json')
        record['build_run_id']=manifest['run_id']
        gold={c['id']:run_query(spark,validate_sql(c['gold_sql'])) for c in cases}
        record['gold_queries_executed']=len(gold);save()
        for c in cases:
            started=time.monotonic()
            try:
                result=answer(c['question'],schema,lambda sql:run_query(spark,sql),model,endpoint,Path('/app/knowledge'))
                correct=result.get('status')=='executed' and same_result(result['result'],gold[c['id']],c['ordered'])
            except Exception as error:result={'status':'error','error':str(error)};correct=False
            record['cases'].append({'id':c['id'],'question':c['question'],'gold':gold[c['id']],
                                    'result':result,'correct':correct,'elapsed_seconds':time.monotonic()-started})
            save();print(c['id'],correct,result['status'],flush=True)
        record['post_run_provenance']=fingerprint(endpoint=endpoint,model=model)
        record['source_unchanged']=record['pre_run_provenance']==record['post_run_provenance']
        record['bank_unchanged']=record['bank_sha256']==hashlib.sha256(bank.read_bytes()).hexdigest()
        record['status']='completed';record['correct']=sum(c['correct'] for c in record['cases']);save()
    except Exception as error:
        record.update(status='failed',error=str(error));save();raise
    finally:
        if spark:spark.stop()


if __name__=='__main__':main()
