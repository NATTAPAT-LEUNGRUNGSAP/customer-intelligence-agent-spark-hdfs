"""Trusted view registration and bounded Spark action, shared by agent/evaluation."""
import json
import re
import threading
import uuid
from pathlib import Path
from sql_guard import TABLES


def load_views(spark, path):
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    root = manifest.get('root', '')
    if manifest.get('status') != 'passed' or not re.fullmatch(
            r'hdfs://namenode:9000/customer_intelligence/runs/[a-f0-9]{32}', root):
        raise ValueError('Expected a passed build manifest with a versioned HDFS root')
    schema = {}
    for name in sorted(TABLES):
        frame = spark.read.parquet(root + '/' + name)
        frame.createOrReplaceTempView(name)
        schema[name] = frame.schema.simpleString()
    schema['_dataset_metadata'] = {key: manifest.get(key) for key in (
        'as_of_date', 'observed_min_timestamp', 'observed_max_timestamp',
        'duplicate_policy', 'excluded_inconsistent_invoice_sale_rows')}
    return schema, manifest


def run_query(spark, sql, timeout=45, max_rows=200):
    if not 1 <= timeout <= 300:
        raise ValueError('Query timeout must be 1..300 seconds')
    group = uuid.uuid4().hex
    expired = threading.Event()
    def cancel():
        expired.set()
        spark.sparkContext.cancelJobGroup(group)
    spark.sparkContext.setJobGroup(group, 'guarded analytics', interruptOnCancel=True)
    timer = threading.Timer(timeout, cancel)
    timer.daemon = True
    timer.start()
    try:
        frame = spark.sql(sql)
        rows = frame.limit(max_rows+1).collect()
        if expired.is_set():
            raise TimeoutError('Spark query deadline exceeded')
        return {'columns': frame.columns, 'rows': [list(row) for row in rows[:max_rows]],
                'truncated': len(rows) > max_rows}
    except Exception as error:
        if expired.is_set():
            raise TimeoutError('Spark query deadline exceeded; job group cancellation requested') from error
        raise
    finally:
        timer.cancel()
        spark.sparkContext.setLocalProperty('spark.jobGroup.id', None)
        spark.sparkContext.setLocalProperty('spark.job.description', None)
