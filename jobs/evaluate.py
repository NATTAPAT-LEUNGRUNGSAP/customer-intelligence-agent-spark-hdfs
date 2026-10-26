"""RAG-only result evaluation. Previous test is regression, new holdout stays separate."""
import argparse
import json
import math
import time
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from agent import answer, generate
from query_runtime import load_views, run_query
from sql_guard import validate_sql
from provenance import fingerprint
from rag_metrics import retrieval_metrics, percentile95


def same_value(a,b):
    if isinstance(a,(int,float,Decimal)) and isinstance(b,(int,float,Decimal)):
        return math.isclose(float(a),float(b),rel_tol=1e-6,abs_tol=1e-4)
    return a==b


def same_result(actual,gold,ordered):
    if actual['truncated'] or gold['truncated']:
        return False
    left,right=actual['rows'],gold['rows']
    if len(left)!=len(right):
        return False
    def equal(a,b):
        return len(a)==len(b) and all(same_value(x,y) for x,y in zip(a,b))
    if ordered:
        return all(equal(a,b) for a,b in zip(left,right))
    remaining=list(right)
    for row in left:
        match=next((i for i,wanted in enumerate(remaining) if equal(row,wanted)),None)
        if match is None:
            return False
        remaining.pop(match)
    return True


def summarize(cases,gates):
    total=len(cases)
    clarification=[c for c in cases if c['expected']=='clarification']
    metrics={'accuracy':sum(c['correct'] for c in cases)/total,
             'correct':sum(c['correct'] for c in cases),'total':total,
             'executed':sum(c['result'].get('status')=='executed' for c in cases),
             'failed_or_error':sum(c['result'].get('status') in ('failed','error') for c in cases),
             'clarification_accuracy':sum(c['correct'] for c in clarification)/len(clarification) if clarification else None,
             'citation_validity':sum(c['citation_valid'] for c in cases)/total,
             'latency_p95_seconds':percentile95([c['elapsed_seconds'] for c in cases]),
             'latency_mean_seconds':sum(c['elapsed_seconds'] for c in cases)/total,
             'model_calls':sum(c['result'].get('model_calls',0) for c in cases)}
    metrics['citation_scope']='All response traces, including failed attempts with validated evidence IDs; not proof of a correct answer'
    labeled=[c for c in cases if c.get('retrieval_metrics')]
    if labeled:
        metrics['cited_relevant_evidence_rate']=sum(c['cites_relevant'] for c in labeled)/len(labeled)
        metrics['retrieval']={name:sum(c['retrieval_metrics'][name] for c in labeled)/len(labeled)
                              for name in labeled[0]['retrieval_metrics']}
    checks={'accuracy':metrics['accuracy']>=gates['accuracy_min'],
            'citations_valid':metrics['citation_validity']>=gates['citation_validity_min'],
            'latency':metrics['latency_p95_seconds']<=gates['latency_p95_seconds_max']}
    if clarification:
        checks['clarification']=metrics['clarification_accuracy']>=gates['clarification_accuracy_min']
    if labeled:
        checks['cited_relevant']=metrics['cited_relevant_evidence_rate']>=gates['cited_relevant_evidence_rate_min']
    return metrics,checks


def main():
    from pyspark.sql import SparkSession
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--split',choices=['dev','regression','regression-v2','regression-v3','regression-v4','regression-v5','holdout'],default='dev')
    parser.add_argument('--model',required=True)
    parser.add_argument('--endpoint',default='http://host.docker.internal:11434')
    args=parser.parse_args()
    paths={'dev':'dev.json','regression':'test.json','regression-v2':'rag_holdout_v2.json',
           'regression-v3':'rag_holdout_v3.json','regression-v4':'rag_holdout_v4.json',
           'regression-v5':'rag_holdout_v5.json','holdout':'rag_holdout_v6.json'}
    cases=json.loads(Path('/app/evaluation/'+paths[args.split]).read_text(encoding='utf-8'))
    gates=json.loads(Path('/app/evaluation/quality_gates_v2.json').read_text())['end_to_end']
    spark=SparkSession.builder.appName('customer-intelligence-rag-evaluation').config(
        'spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    output=Path('/app/reports')/('rag-v2.4-'+args.split+'-'+uuid.uuid4().hex+'.json')
    report={'status':'running','version':'rag-required-v2.4','benchmark':paths[args.split],
            'rag_required':True,'model':args.model,'split':args.split,'cases':[],
            'started_at_utc':datetime.now(timezone.utc).isoformat(),
            'spark_version':spark.version,'spark_master':spark.sparkContext.master,'gates':gates}
    try:
        report['provenance']=fingerprint(endpoint=args.endpoint,model=args.model)
        schema,manifest=load_views(spark,args.manifest)
        report['build_run_id']=manifest['run_id']
        warmup_started=time.monotonic()
        generate([{'role':'user','content':'Return JSON {"ready":true} only.'}],args.model,args.endpoint)
        report['model_warmup_seconds']=time.monotonic()-warmup_started
        for case in cases:
            gold=run_query(spark,validate_sql(case['gold_sql'])) if case.get('gold_sql') else None
            started=time.monotonic()
            try:
                result=answer(case['question'],schema,lambda sql:run_query(spark,sql),
                              args.model,args.endpoint,'/app/knowledge')
                correct=(result['status']=='clarification' if gold is None else
                         result['status']=='executed' and same_result(result['result'],gold,case.get('ordered',False)))
                if gold is None and case.get('clarification_policy'):
                    correct=correct and case['clarification_policy'] in result.get('citations',[])
            except Exception as error:
                result,correct={'status':'error','error':str(error)},False
            citations=result.get('citations',[])
            ids={c['id'] for c in result.get('references',[])}
            valid=bool(citations) and all(c in ids for c in citations)
            row={'id':case['id'],'question':case['question'],'correct':correct,
                 'expected':'clarification' if gold is None else 'result',
                 'citation_valid':valid,'elapsed_seconds':time.monotonic()-started,
                 'result':result,'gold':gold}
            if case.get('relevant_ids'):
                row['retrieval_metrics']=retrieval_metrics(
                    result.get('retrieval',{}).get('ranked_ids',[]),case['relevant_ids'],
                    result.get('retrieval',{}).get('context_ids',[]))
                row['cites_relevant']=bool(set(citations)&set(case['relevant_ids']))
            report['cases'].append(row)
            output.write_text(json.dumps(report,indent=2,default=str,ensure_ascii=False),encoding='utf-8')
        report['summary'],report['quality_checks']=summarize(report['cases'],gates)
        report['quality_passed']=all(report['quality_checks'].values())
        report['status']='completed'
        output.write_text(json.dumps(report,indent=2,default=str,ensure_ascii=False),encoding='utf-8')
        print(json.dumps({'report':str(output),'summary':report['summary'],'quality_checks':report['quality_checks']}))
    except Exception as error:
        report.update(status='failed',error=str(error))
        output.write_text(json.dumps(report,indent=2,default=str,ensure_ascii=False),encoding='utf-8')
        raise
    finally:
        spark.stop()


if __name__=='__main__':
    main()
