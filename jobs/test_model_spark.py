"""End-to-end synthetic fixture with a REAL model and REAL Spark execution."""
import argparse
import json
import uuid
from pathlib import Path
from pyspark.sql import SparkSession
from agent import answer
from query_runtime import run_query


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='qwen3.5:9b')
    args = parser.parse_args()
    spark = SparkSession.builder.appName('real-model-synthetic-spark').getOrCreate()
    try:
        frame = spark.sql("""SELECT * FROM VALUES
            ('1','A','United Kingdom',TIMESTAMP '2011-10-01',10.0),
            ('2','B','France',TIMESTAMP '2011-10-31 23:59:59',20.0),
            ('3','A','United Kingdom',TIMESTAMP '2011-11-01',999.0)
            AS t(invoice_id,customer_id,country,order_ts,order_amount)""")
        frame.createOrReplaceTempView('orders')
        result = answer('What were total completed sales in GBP in October 2011?',
            {'orders':frame.schema.simpleString()}, lambda sql: run_query(spark,sql),
            args.model, 'http://host.docker.internal:11434', '/app/knowledge')
        passed = (result['status']=='executed' and not result['result']['truncated'] and
                  result['result']['rows']==[[30]])
        report = {'status':'passed' if passed else 'failed', 'fixture':'synthetic',
                  'real_model':True, 'real_spark':True, 'model':args.model,
                  'expected_rows':[[30]], 'result':result}
        Path('/app/reports/model-spark-'+uuid.uuid4().hex+'.json').write_text(
            json.dumps(report,indent=2,default=str),encoding='utf-8')
        print(json.dumps(report,indent=2,default=str))
        assert passed, 'Real model answer failed synthetic result check; inspect report'
    finally:
        spark.stop()


if __name__=='__main__':
    main()
