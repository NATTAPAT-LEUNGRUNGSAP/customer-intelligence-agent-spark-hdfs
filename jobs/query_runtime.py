"""Trusted view registration and bounded Spark action, shared by agent/evaluation."""
import json
import re
import threading
import uuid
from pathlib import Path
from sql_guard import TABLES


def load_views(spark, path):
    """Register the passed build's Parquet tables as Spark SQL views and expose their schema."""
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
        schema.setdefault('_table_metadata',{})[name] = {
            'schema':schema[name], 'columns':frame.schema.jsonValue()['fields'],
            'approximate_rows':manifest.get(name+'_rows'),
            'grain':{'orders':'one completed-sale invoice','sales_lines':'one source product line',
                     'customer_summary':'one customer at one snapshot'}[name],
            'logical_keys':{'orders':['invoice_id'],'sales_lines':['source_sheet','source_row'],
                            'customer_summary':['customer_id','as_of_date']}[name],
            'relationships':{'customer_id':'customer_summary.customer_id (snapshot-dependent)'} if name!='customer_summary' else {},
            'keys_enforced_by_database':False}
    schema['_dataset_metadata'] = {key: manifest.get(key) for key in (
        'as_of_date', 'observed_min_timestamp', 'observed_max_timestamp',
        'duplicate_policy', 'excluded_inconsistent_invoice_sale_rows')}
    return schema, manifest


def require_read_only(spark, root):
    """Ask HDFS itself, not the SQL guard, to confirm read is allowed/write denied."""
    path = spark._jvm.org.apache.hadoop.fs.Path(root)
    fs = path.getFileSystem(spark._jsc.hadoopConfiguration())
    action = spark._jvm.org.apache.hadoop.fs.permission.FsAction
    fs.access(path, action.READ_EXECUTE)
    for location in (root, '/customer_intelligence/runs', '/customer_intelligence'):
        target=spark._jvm.org.apache.hadoop.fs.Path(location)
        try:
            fs.access(target, action.WRITE)
        except Exception as error:
            if 'AccessControlException' not in str(error):raise
            continue
        raise RuntimeError('Analytics identity has HDFS write access; refusing to serve queries')


def run_query(spark, sql, timeout=45, max_rows=200):
    """Run caller-validated SQL and return a bounded table to the caller."""
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
