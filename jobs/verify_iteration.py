"""Exposed regression plus context stress; never labeled as fresh holdout."""
import json
import time
import uuid
from pathlib import Path
from agent import answer
from evaluate import same_result
from provenance import fingerprint
from query_runtime import load_views, run_query
from sql_guard import validate_sql


def main():
    from pyspark.sql import SparkSession
    spark=SparkSession.builder.appName('customer-intelligence-iteration-regression').config(
        'spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    output=Path('/app/reports')/f'iteration-regression-{uuid.uuid4().hex}.json'
    report={'version':'v2.2-development','status':'running','fresh_holdout':False,'cases':[]}
    try:
        schema,manifest=load_views(spark,'/app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json')
        endpoint,model='http://host.docker.internal:11434','qwen3.5:9b'
        report.update(provenance=fingerprint(endpoint=endpoint,model=model),build_run_id=manifest['run_id'])
        cases=json.loads(Path('/app/evaluation/dev.json').read_text(encoding='utf-8'))
        for filename,ids in [('rag_holdout_v2.json',{'hold04','hold08'}),('rag_holdout_v3.json',{'fresh08'})]:
            cases += [c for c in json.loads(Path('/app/evaluation',filename).read_text(encoding='utf-8')) if c['id'] in ids]
        base='How many completed invoices were recorded in October 2011?'
        for length in [0,400,1200]:
            cases.append({'id':f'context_noise_{length}','question':base+
                          '\nIrrelevant notes (ignore): '+('decorative text. '*1000)[:length],
                          'gold_sql':"SELECT count(*) FROM orders WHERE order_ts>=TIMESTAMP '2011-10-01' AND order_ts<TIMESTAMP '2011-11-01'"})
        for case in cases:
            started=time.monotonic()
            gold=run_query(spark,validate_sql(case['gold_sql'])) if 'gold_sql' in case else None
            result=answer(case['question'],schema,lambda sql:run_query(spark,sql),model,endpoint,'/app/knowledge')
            correct=(result['status']=='clarification' if gold is None else
                     result['status']=='executed' and same_result(result['result'],gold,case.get('ordered',False)))
            row={'id':case['id'],'question':case['question'],'correct':correct,'gold':gold,
                 'result':result,'elapsed_seconds':time.monotonic()-started}
            report['cases'].append(row)
            output.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
            print(case['id'],correct,result['status'],flush=True)
        oversized=answer(base+'\n'+('noise '*6000),schema,
                         lambda sql:(_ for _ in ()).throw(AssertionError('Oversized context must not execute')),
                         model,endpoint,'/app/knowledge')
        report['overflow_check']={'status':oversized['status'],'model_calls':oversized['model_calls'],
                                  'attempts':oversized['attempts']}
        report.update(status='completed',correct=sum(c['correct'] for c in report['cases']),total=len(report['cases']))
        report['checks_passed']=report['correct']==report['total'] and oversized['status']=='failed' and oversized['model_calls']==0
    except Exception as error:
        report.update(status='failed',error=str(error),checks_passed=False)
        raise
    finally:
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
        print(str(output),flush=True)
        spark.stop()
    if not report['checks_passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
