"""Trusted overview queries over the same read-only, policy-guarded Spark views."""
import datetime as dt
from sqlglot import exp, parse_one
from sqlglot.optimizer.scope import traverse_scope
from sql_guard import validate_sql
from policy_engine import authorize, policy_facts
from result_contracts import validate_result


def filters(selection, country, metadata, countries):
    from question_scope import validate_time_selection
    validate_time_selection(selection)
    if selection is None or selection['mode']=='all':
        start=metadata['observed_min_timestamp'][:10]
        end=metadata['observed_max_timestamp'][:10]
    else:start,end=selection['start'],selection['end']
    if end<metadata['observed_min_timestamp'][:10] or start>metadata['observed_max_timestamp'][:10]:
        raise ValueError('Selected dates are outside the observed dataset')
    if country is not None and (not isinstance(country,str) or country not in countries):
        raise ValueError('Choose a country from the loaded dataset')
    return {'start':start,'end':end,'end_exclusive':(dt.date.fromisoformat(end)+dt.timedelta(days=1)).isoformat(),
            'country':country}


def where(scope, alias=''):
    prefix=alias+'.' if alias else ''
    text=(f"{prefix}order_ts >= TIMESTAMP '{scope['start']}' AND "
          f"{prefix}order_ts < TIMESTAMP '{scope['end_exclusive']}'")
    if scope['country'] is not None:
        text+=' AND '+prefix+'country = '+exp.Literal.string(scope['country']).sql(dialect='spark')
    return text


def queries(scope, snapshot):
    condition=where(scope)
    # Snapshot and dates come from trusted ISO build metadata / validated controls.
    dt.date.fromisoformat(snapshot)
    return {
        'kpis':f'SELECT COALESCE(SUM(order_amount),0) AS sales, COUNT(*) AS invoices, SUM(order_amount)/NULLIF(COUNT(*),0) AS aov, COUNT(DISTINCT customer_id) AS customers FROM orders WHERE {condition}',
        'monthly':f"SELECT DATE_TRUNC('MONTH',order_ts) AS month, SUM(order_amount) AS sales FROM orders WHERE {condition} GROUP BY DATE_TRUNC('MONTH',order_ts) ORDER BY month",
        'countries':f'SELECT country, SUM(order_amount) AS sales FROM orders WHERE {condition} GROUP BY country ORDER BY sales DESC,country ASC LIMIT 5',
        'products':f"SELECT l.product_id, SUM(l.line_amount) AS sales FROM sales_lines l JOIN orders o ON l.invoice_id=o.invoice_id WHERE l.transaction_type='sale' AND {where(scope,'o')} GROUP BY l.product_id ORDER BY sales DESC,l.product_id ASC LIMIT 5",
        'rfm':f"WITH buyers AS (SELECT DISTINCT customer_id FROM orders WHERE customer_id IS NOT NULL AND {condition}) SELECT c.rfm_segment AS segment, COUNT(*) AS customers FROM customer_summary c JOIN buyers b ON c.customer_id=b.customer_id WHERE c.as_of_date=DATE '{snapshot}' GROUP BY c.rfm_segment ORDER BY c.rfm_segment"
    }


def guarded_query(sql, execute):
    guarded=validate_sql(sql)
    pre=authorize(policy_facts(sql,1))
    result=execute(guarded)
    contract=validate_result('',result,sql)
    post=authorize(policy_facts(sql,1,'post',[]))
    return {'status':'executed','result':result,'result_contract':contract,
            'sql':sql,'policy_trace':[pre,post]}


def validate_country_scope(sql, country):
    """Fail closed when a base transaction scope omits the selected country."""
    tree=parse_one(sql,read='spark')
    found=False
    def conjuncts(node):
        if isinstance(node,exp.Paren):return conjuncts(node.this)
        if isinstance(node,exp.And):return conjuncts(node.this)+conjuncts(node.expression)
        return [node]
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source,exp.Table) and source.name=='customer_summary':
                raise ValueError('Use the dashboard verified cohort for country-filtered snapshot analysis')
            if not isinstance(source,exp.Table) or source.name not in {'orders','sales_lines'}:continue
            found=True
            clause=scope.expression.args.get('where')
            terms=conjuncts(clause.this) if clause else []
            if not any(isinstance(t,exp.EQ) and any(
                isinstance(a,exp.Column) and a.name=='country' and
                (not a.table or a.table==source.alias_or_name) and
                isinstance(b,exp.Literal) and b.is_string and b.this==country
                for a,b in [(t.this,t.expression),(t.expression,t.this)]) for t in terms):
                raise ValueError('Selected country must filter every transaction source before aggregation')
    if not found:raise ValueError('Selected country requires transaction data; use the dashboard for snapshot cohorts')
