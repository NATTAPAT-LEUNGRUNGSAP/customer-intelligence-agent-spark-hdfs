"""Runtime integration on synthetic views. This does NOT evaluate an LLM."""
from pathlib import Path
import json
import uuid
from pyspark.sql import SparkSession
from query_runtime import run_query
from sql_guard import validate_sql


def main():
    spark = SparkSession.builder.appName('guarded-spark-fixture').getOrCreate()
    try:
        spark.createDataFrame([('A', 'UK', 10), ('A', 'UK', 20), (None, 'FR', 30)],
            'customer_id string,country string,order_amount int').createOrReplaceTempView('orders')
        query = validate_sql('WITH x AS (SELECT * FROM orders) SELECT country,sum(order_amount) AS sales FROM x GROUP BY country ORDER BY country')
        result = run_query(spark, query)
        assert result['rows'] == [['FR',30],['UK',30]], result
        capped = run_query(spark, validate_sql('SELECT * FROM orders'), max_rows=2)
        assert capped['truncated'] and len(capped['rows']) == 2
        rejected = 0
        for query in ['DROP TABLE orders', 'SELECT * FROM parquet.`/app/data/retail.csv`',
                      "SELECT reflect('java.lang.System','getenv','HOME') FROM orders"]:
            try:
                validate_sql(query)
            except ValueError:
                rejected += 1
        assert rejected == 3
        timed_out = False
        try:
            # Trusted fixture only: the agent guard itself rejects range().
            run_query(spark, 'SELECT sum(sqrt(id)) FROM range(100000000000)', timeout=1)
        except TimeoutError:
            timed_out = True
        assert timed_out, 'Long-running job was not cancelled by deadline'
        assert run_query(spark, validate_sql('SELECT count(*) FROM orders'))['rows'] == [[3]]
        report = {'status':'passed', 'fixture':'synthetic', 'spark_version':spark.version,
                  'checks':['guarded CTE aggregate','result cap','unsafe SQL rejected',
                            'long-running Spark job cancelled','session usable after cancellation']}
        Path('/app/reports/guarded-spark-' + uuid.uuid4().hex + '.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
