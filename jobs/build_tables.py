"""Build versioned HDFS tables; publish manifest only after reconciliation passes."""
import argparse
import hashlib
import json
import uuid
from datetime import date
from pathlib import Path
from pyspark.sql import SparkSession, functions as F

FIELDS = ["invoice_id", "product_id", "description", "quantity", "invoice_ts",
          "unit_price", "customer_id", "country", "source_sheet", "source_row"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", default="2011-12-01")
    parser.add_argument("--input", default="/app/data/retail.csv")
    args = parser.parse_args()
    date.fromisoformat(args.as_of)
    source_manifest = json.loads(Path(args.input).with_name('manifest.json').read_text())
    digest = hashlib.sha256()
    with Path(args.input).open('rb') as source:
        while chunk := source.read(1024*1024):
            digest.update(chunk)
    if digest.hexdigest() != source_manifest['csv_sha256']:
        raise ValueError('Staged CSV does not match provenance manifest')
    run_id = uuid.uuid4().hex
    root = f"hdfs://namenode:9000/customer_intelligence/runs/{run_id}"
    spark = (SparkSession.builder.appName("customer-intelligence-build")
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "8").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    try:
        raw = (spark.read.option("header", True).option("multiLine", True)
               .option("escape", '"').option("mode", "FAILFAST")
               .schema(", ".join(f"{field} STRING" for field in FIELDS)).csv(args.input)).cache()
        raw_count = raw.count()
        if raw_count == 0:
            raise ValueError("Input has no data")
        raw.write.mode("errorifexists").parquet(root + "/raw_retail")
        raw.createOrReplaceTempView("raw_retail")
        metrics = {"raw_rows": raw_count, "as_of_date": args.as_of,
                   "run_id": run_id, "root": root, "duplicate_policy": "retain_all"}
        assert raw_count == source_manifest['rows'], 'Source manifest row count mismatch'
        metrics['source_provenance'] = source_manifest
        tables = {}
        for table in ("sales_lines", "orders", "customer_summary"):
            query = Path(f"/app/sql/{table}.sql").read_text().replace("${AS_OF}", args.as_of)
            result = spark.sql(query)
            target = root + "/" + table
            result.write.mode("errorifexists").parquet(target)
            result = spark.read.parquet(target).cache()
            result.createOrReplaceTempView(table)
            tables[table] = result
            metrics[table + "_rows"] = result.count()
        lines, orders = tables["sales_lines"], tables["orders"]
        assert metrics["sales_lines_rows"] == raw_count, "Source row loss"
        metrics["transaction_types"] = {r.transaction_type: r['count'] for r in lines.groupBy("transaction_type").count().collect()}
        identity = FIELDS[:8]
        metrics["exact_duplicate_extra_rows"] = raw_count - raw.select(*identity).distinct().count()
        metrics["missing_customer_rows"] = lines.where("customer_id IS NULL").count()
        sale = lines.where("transaction_type = 'sale'")
        consistent = sale.join(orders.select("invoice_id"), "invoice_id", "left_semi")
        expected = consistent.agg(F.sum("line_amount")).first()[0]
        actual = orders.agg(F.sum("order_amount")).first()[0]
        assert expected == actual, f"Sales reconciliation failed: {expected} vs {actual}"
        metrics["included_sales_amount"] = str(actual)
        metrics["excluded_inconsistent_invoice_sale_rows"] = sale.count() - consistent.count()
        bounds = lines.agg(F.min("invoice_ts"), F.max("invoice_ts")).first()
        metrics["observed_min_timestamp"], metrics["observed_max_timestamp"] = map(str, bounds)
        metrics["status"] = "passed"
        manifest_path = Path("/app/reports") / f"build-{run_id}.json"
        manifest_path.write_text(json.dumps(metrics, indent=2))
        print(json.dumps(metrics, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
