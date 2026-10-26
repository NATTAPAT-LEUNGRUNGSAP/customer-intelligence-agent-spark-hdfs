"""Fail-closed AST guard for a deliberately small Spark analytics dialect."""
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

TABLES = {'sales_lines', 'orders', 'customer_summary'}
FUNCTIONS = set('AND OR NOT SUM COUNT AVG MIN MAX NULLIF COALESCE CASE IF CAST TRY_CAST '
                'DATE_TRUNC TIMESTAMP_TRUNC DATEDIFF DATE_DIFF DATE_ADD DATE_SUB TO_DATE '
                'ROW_NUMBER RANK DENSE_RANK LAG LEAD ROUND CEIL FLOOR ABS '
                'YEAR MONTH DAY EXTRACT UPPER LOWER TRIM CONCAT LENGTH '
                'STDDEV VARIANCE PERCENTILE_APPROX'.split())


def validate_sql(sql, max_rows=200):
    if not isinstance(sql, str) or len(sql) > 20000:
        raise ValueError('SQL must be text of at most 20000 characters')
    statements = sqlglot.parse(sql, read='spark')
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union)):
        raise ValueError('Exactly one SELECT/WITH query is allowed')
    tree = statements[0]
    forbidden = {'Into', 'Command', 'Insert', 'Delete', 'Update', 'Create', 'Drop',
                 'Alter', 'Merge', 'Copy', 'Use', 'Set', 'Transaction', 'Lock',
                 'Lateral', 'UDTF', 'TableFromRows'}
    for node in tree.walk():
        if isinstance(node,exp.TimestampTrunc):
            unit=node.args.get('unit')
            if not isinstance(unit,exp.Var) or unit.name.upper() not in {
                    'YEAR','YYYY','YY','QUARTER','MONTH','MON','MM','WEEK','DAY','DD',
                    'HOUR','MINUTE','SECOND','MILLISECOND','MICROSECOND'}:
                raise ValueError("Spark DATE_TRUNC requires DATE_TRUNC('MONTH', timestamp_column), "
                                 "unit first. Prefer timestamp_column >= TIMESTAMP 'YYYY-MM-01' "
                                 "AND timestamp_column < TIMESTAMP 'next-month-01' for month filters.")
        if type(node).__name__ in forbidden:
            raise ValueError('Unsupported SQL operation: ' + type(node).__name__)
        if isinstance(node, exp.Func):
            name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
            if name not in FUNCTIONS:
                raise ValueError('Function is not allowed: ' + name)
    referenced = set()
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                if (source.catalog or source.db or not isinstance(source.this, exp.Identifier)
                        or source.name.lower() not in TABLES):
                    raise ValueError('Only unqualified analytics views are allowed')
                referenced.add(source.name.lower())
    if not referenced:
        raise ValueError('Query must read an analytics view')
    # Outer cap handles oversized/nonliteral LIMIT and UNION consistently.
    return f'SELECT * FROM ({tree.sql(dialect="spark")}) AS guarded_result LIMIT {int(max_rows)+1}'
