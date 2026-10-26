"""Real Spark-to-HDFS roundtrip; synthetic fixture, never a dataset evaluation."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from pyspark.sql import SparkSession


def main():
    spark = SparkSession.builder.appName("customer-intelligence-hdfs-smoke").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    run_id = uuid.uuid4().hex
    target = f"hdfs://namenode:9000/customer_intelligence/smoke/{run_id}"
    expected = [("C001", 1000), ("C002", 2500), ("C001", 500)]
    try:
        configured_replication = spark.sparkContext._jsc.hadoopConfiguration().get('dfs.replication')
        assert configured_replication == '2', f'Client replication must be 2, got {configured_replication}'
        with urlopen('http://spark-master:8080/json/', timeout=10) as response:
            cluster = json.load(response)
        live_workers = [w['id'] for w in cluster['workers'] if w['state']=='ALIVE']
        assert len(live_workers)==2, f'Expected two Spark workers, got {live_workers}'
        source = spark.createDataFrame(expected, "customer_id string, amount_minor long")
        source.repartition(2).write.mode("errorifexists").parquet(target)
        actual = spark.read.parquet(target)
        assert sorted(tuple(row) for row in actual.collect()) == sorted(expected)
        totals = {r.customer_id: r.total for r in actual.groupBy("customer_id").sum("amount_minor").withColumnRenamed("sum(amount_minor)", "total").collect()}
        assert totals == {"C001": 1500, "C002": 2500}, totals
        report = {"status": "passed", "fixture": "synthetic", "run_id": run_id,
                  "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                  "spark_version": spark.version, "spark_master": spark.sparkContext.master,
                  "live_spark_workers": live_workers,
                  "client_replication": configured_replication,
                  "hdfs_path": target, "rows": 3, "customer_totals_minor": totals}
        Path("/app/reports").mkdir(parents=True, exist_ok=True)
        Path(f"/app/reports/smoke-{run_id}.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
