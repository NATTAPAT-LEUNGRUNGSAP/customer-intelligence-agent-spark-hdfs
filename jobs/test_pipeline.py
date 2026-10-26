"""Execute actual Spark SQL on edge cases before building the UCI dataset."""
from pathlib import Path
from decimal import Decimal
from pyspark.sql import SparkSession


def main():
    spark = SparkSession.builder.appName("customer-intelligence-sql-tests").config("spark.sql.session.timeZone", "UTC").getOrCreate()
    try:
        fields = "invoice_id product_id description quantity invoice_ts unit_price customer_id country source_sheet source_row".split()
        rows = [
            ("1", "P", "gift", "2", "2011-11-01 12:00:00", "10", "A", "UK", "fixture", "2"),
            ("2", "P", "gift", "1", "2011-11-20 12:00:00", "10", "A", "UK", "fixture", "3"),
            ("3", "P", "gift", "1", "2011-11-25 12:00:00", "10", "A", "UK", "fixture", "4"),
            ("4", "P", "gift", "1", "2011-08-01 12:00:00", "20", "B", "UK", "fixture", "5"),
            ("5", "P", "gift", "1", "2011-11-01 12:00:00", "5", None, "UK", "fixture", "6"),
            ("C1", "P", "gift", "-1", "2011-11-02 12:00:00", "10", "A", "UK", "fixture", "7"),
            ("6", "P", "gift", "1", "2011-12-01 00:00:00", "999", "A", "UK", "fixture", "8"),
            ("7", "P", "gift", "1", "bad-date", "10", "A", "UK", "fixture", "9"),
            ("8", "P", "gift", "1", "2011-11-01 12:00:00", "10", "X", "UK", "fixture", "10"),
            ("8", "P", "gift", "1", "2011-11-01 12:00:00", "10", None, "UK", "fixture", "11"),
        ]
        spark.createDataFrame(rows, ",".join(f"{f} string" for f in fields)).createOrReplaceTempView("raw_retail")
        for table in ("sales_lines", "orders", "customer_summary"):
            sql = Path(f"/app/sql/{table}.sql").read_text().replace("${AS_OF}", "2011-12-01")
            spark.sql(sql).createOrReplaceTempView(table)
        assert spark.table("sales_lines").count() == 10
        assert spark.sql("SELECT * FROM sales_lines WHERE transaction_type='invalid'").count() == 1
        assert spark.sql("SELECT * FROM orders WHERE invoice_id='8'").count() == 0
        customers = {r.customer_id: r for r in spark.table("customer_summary").collect()}
        assert set(customers) == {"A", "B"}
        assert customers["A"].sales_180d == Decimal("40")
        assert customers["A"].orders_180d == 3
        assert customers["A"].rfm_segment == "Champions"
        assert customers["B"].rfm_segment == "Inactive"
        print("PASS: cancellation, invalid date, missing ID, inconsistent invoice, snapshot boundary, RFM")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
