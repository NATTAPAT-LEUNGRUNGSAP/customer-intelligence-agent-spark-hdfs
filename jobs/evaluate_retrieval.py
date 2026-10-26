"""Direct retrieval benchmark; no LLM judge and no Spark dependency."""
import argparse
import json
import time
import uuid
from pathlib import Path
from retrieval import retrieve_context
from rag_metrics import retrieval_metrics, percentile95
from provenance import fingerprint


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=['dev','regression-v2','regression-v3','regression-v4','regression-v5','holdout'],default='dev')
    parser.add_argument('--root',default='/app')
    args=parser.parse_args()
    root=Path(args.root)
    filename={'dev':'retrieval_dev_v2.json','regression-v2':'rag_holdout_v2.json',
              'regression-v3':'rag_holdout_v3.json','regression-v4':'rag_holdout_v4.json',
              'regression-v5':'rag_holdout_v5.json','holdout':'rag_holdout_v6.json'}[args.split]
    cases=json.loads((root/'evaluation'/filename).read_text(encoding='utf-8'))
    gates=json.loads((root/'evaluation/quality_gates_v2.json').read_text())['retrieval']
    results=[]
    for case in cases:
        context,trace=retrieve_context(case['question'],root/'knowledge')
        metrics=retrieval_metrics(trace['ranked_ids'],case['relevant_ids'],trace['context_ids'])
        results.append({'id':case['id'],'relevant_ids':case['relevant_ids'],'trace':trace,'metrics':metrics})
    summary={name:sum(c['metrics'][name] for c in results)/len(results) for name in results[0]['metrics']}
    summary['latency_p95_ms']=percentile95([c['trace']['elapsed_ms'] for c in results])
    checks={'recall':summary['recall_at_6']>=gates['recall_at_6_min'],
            'mrr':summary['mrr_at_6']>=gates['mrr_at_6_min'],
            'ndcg':summary['ndcg_at_6']>=gates['ndcg_at_6_min'],
            'latency':summary['latency_p95_ms']<=gates['latency_p95_ms_max']}
    report={'status':'completed','version':'rag-required-v2.4','benchmark':filename,
            'split':args.split,'cases':results,'summary':summary,
            'gates':gates,'quality_checks':checks,'quality_passed':all(checks.values()),
            'provenance':fingerprint(root)}
    output=root/'reports'/('retrieval-v2.4-'+args.split+'-'+uuid.uuid4().hex+'.json')
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'report':str(output),'summary':summary,'checks':checks}))


if __name__=='__main__':
    main()
