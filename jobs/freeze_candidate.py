"""Validate benchmark SQL schema and record a pre-run candidate fingerprint."""
import json
from datetime import datetime, timezone
from pathlib import Path
from provenance import fingerprint
from query_runtime import load_views
from sql_guard import validate_sql


def main():
    from pyspark.sql import SparkSession
    spark=SparkSession.builder.appName('freeze-v2.4-candidate').getOrCreate()
    try:
        schema,manifest=load_views(spark,'/app/reports/build-c81fa72c3c174a96bf8c03195b9e6f5e.json')
        development=Path('/app/reports/rag-v2.4-regression-v5-968f0bf891c445ae8ee598c68d1a93e0.json')
        dev=json.loads(development.read_text(encoding='utf-8'))
        if dev.get('status')!='completed' or not dev.get('quality_passed'):
            raise ValueError('Development regression has not passed')
        current=fingerprint()
        for name in ('jobs/agent.py','jobs/sql_guard.py','jobs/context_budget.py','jobs/retrieval.py',
                     'jobs/result_contracts.py','knowledge/metrics.md'):
            if current['files_sha256'][name]!=dev['provenance']['files_sha256'][name]:
                raise ValueError('Development core fingerprint differs: '+name)
        cases=json.loads(Path('/app/evaluation/rag_holdout_v6.json').read_text(encoding='utf-8'))
        checked=[]
        for case in cases:
            if case.get('gold_sql'):
                spark.sql(validate_sql(case['gold_sql'])).schema
                checked.append(case['id'])
        result={'version':'v2.4','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
                'benchmark':'rag_holdout_v6.json','gold_schema_analyzed':checked,
                'build_run_id':manifest['run_id'],
                'provenance':fingerprint(endpoint='http://host.docker.internal:11434',model='qwen3.5:9b'),
                'development_report':development.name,
                'unit_log':'candidate-v2.4-unit-tests-complete.log','note':'No agent outputs from this benchmark observed before freeze'}
        target=Path('/app/reports/freeze-rag-v2.4.json')
        if target.exists():
            raise ValueError('Freeze already exists; do not overwrite it')
        target.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('Frozen:',str(target),flush=True)
    finally:
        spark.stop()


if __name__=='__main__':
    main()
