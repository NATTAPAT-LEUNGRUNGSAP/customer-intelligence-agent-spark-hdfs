"""Deterministic checks for supported analytics; no benchmark/gold SQL is loaded."""
import calendar
import datetime as dt
import re
from sqlglot import exp, parse_one
from sqlglot.optimizer.scope import traverse_scope


def requested_period(question):
    text = question.lower()
    # Explicit half-open periods must say before / exclusive / to (exclusive).
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text)
    if len(dates) == 2 and re.search(r'before|exclusive', text):
        return dates
    names='|'.join(calendar.month_name[1:]).lower()
    span=re.search(r'\b('+names+r')\s+(?:through|to)\s+('+names+r')\s+((?:19|20)\d{2})\b',text)
    if span:
        months={calendar.month_name[m].lower():m for m in range(1,13)}
        first,last,year=months[span[1]],months[span[2]],int(span[3])
        if last<first:
            raise ValueError('Cross-year month range requires explicit years/dates')
        return [f'{year}-{first:02}-01',f'{year+(last==12)}-{last%12+1:02}-01']
    for month in range(1, 13):
        match = re.search(r'\b' + calendar.month_name[month].lower() + r'\s+((?:19|20)\d{2})\b', text)
        if match:
            year = int(match[1])
            return [f'{year:04}-{month:02}-01',
                    f'{year + (month == 12):04}-{month % 12 + 1:02}-01']
    return None


def conjuncts(node):
    if isinstance(node, exp.Paren):
        return conjuncts(node.this)
    if isinstance(node, exp.And):
        return conjuncts(node.this) + conjuncts(node.expression)
    return [node]


def literal_value(node):
    while isinstance(node, (exp.Cast, exp.TryCast, exp.Paren)):
        node = node.this
    return str(node.this) if isinstance(node, exp.Literal) else None


def time_is_bounded(where, column, period):
    """Accept half-open direct bounds or equal DATE_TRUNC month, not OR bypasses."""
    lower = upper = False
    for node in conjuncts(where.this) if where else []:
        if isinstance(node, (exp.GTE, exp.LT)) and isinstance(node.this, exp.Column):
            if node.this.name.lower() != column:
                continue
            value = literal_value(node.expression)
            if isinstance(node, exp.GTE) and value and value[:10] == period[0]:
                lower = True
            if isinstance(node, exp.LT) and value and value[:10] == period[1]:
                upper = True
        if isinstance(node, exp.EQ) and isinstance(node.this, exp.TimestampTrunc):
            col = node.this.this
            if (isinstance(col, exp.Column) and col.name.lower() == column
                    and str(node.this.args.get('unit')).upper() == 'MONTH'
                    and literal_value(node.expression) == period[0]):
                lower = upper = True
    return lower and upper


def validate_business_sql(question, sql):
    text = question.lower()
    tree = parse_one(sql, read='spark')
    scopes = list(traverse_scope(tree))
    sources = [(scope, source) for scope in scopes for source in scope.sources.values()
               if isinstance(source, exp.Table)]
    tables = {source.name.lower() for _, source in sources}
    checks = []
    invoice_count = bool(re.search(r'count.*(?:invoice|order)|how many.*(?:invoice|order)|จำนวนคำสั่งซื้อ|กี่ใบ', text))
    snapshot = bool(re.search(r'snapshot|\brfm\b|champions|inactive|high.value', text))
    line_metric = bool(re.search(r'product|sku|cancellation|return.*lines', text))
    if invoice_count and not snapshot and not line_metric and 'orders' not in tables:
        raise ValueError('Invoice count must read orders (one invoice per row), not sales_lines/customer_summary')
    if invoice_count and not snapshot and not line_metric:
        checks.append('invoice_source_grain')
    period = requested_period(question)
    for scope, source in sources:
        name = source.name.lower()
        where = scope.expression.args.get('where')
        if period and name in ('orders', 'sales_lines'):
            column = 'order_ts' if name == 'orders' else 'invoice_ts'
            if not time_is_bounded(where, column, period):
                raise ValueError(f'Requested period requires {column} >= {period[0]} AND '
                                 f'{column} < {period[1]} in each source WHERE; OR bypasses are rejected')
            checks.append('exact_requested_period')
        if name == 'customer_summary':
            dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text)
            if dates and not any(isinstance(n, exp.EQ) and isinstance(n.this, exp.Column)
                    and n.this.name.lower() == 'as_of_date' and literal_value(n.expression) == dates[0]
                    for n in (conjuncts(where.this) if where else [])):
                raise ValueError('customer_summary requires requested as_of_date equality in WHERE')
            checks.append('snapshot_filter')
        if name == 'sales_lines' and line_metric:
            required = ('cancellation' if 'cancellation' in text else 'return' if
                        re.search(r'return.*(?:product )?lines', text) else 'sale')
            if not any(isinstance(n, exp.EQ) and isinstance(n.this, exp.Column)
                       and n.this.name.lower() == 'transaction_type' and literal_value(n.expression) == required
                       for n in (conjuncts(where.this) if where else [])):
                raise ValueError('Product-line metric requires transaction_type=' + required)
            checks.append('transaction_type_filter')
    # Fan-out can duplicate invoice amounts. Reject this aggregate pattern before execution.
    if {'orders', 'sales_lines'}.issubset(tables) and any(
            isinstance(n, exp.Sum) and any(c.name.lower() == 'order_amount'
                                         for c in n.find_all(exp.Column)) for n in tree.walk()):
        raise ValueError('SUM(order_amount) across orders and sales_lines risks invoice fan-out; aggregate separately')
    return {'status': 'passed', 'checks': sorted(set(checks)),
            'scope': 'supported source grain, explicit English monthly/date bounds, snapshot and transaction type'}
