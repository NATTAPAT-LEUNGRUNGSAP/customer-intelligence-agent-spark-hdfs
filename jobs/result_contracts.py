"""Narrow result contracts; these do not certify general SQL semantics."""
import re
import math
from decimal import Decimal
from sqlglot import parse_one, exp
from sqlglot.optimizer.scope import traverse_scope
from metric_contracts import has_breakdown, invoice_share_target


def validate_semantics(question, sql):
    """Require explicit identified population where orders feed a customer metric."""
    text=question.lower()
    tree=parse_one(sql,read='spark')
    grouped_request=has_breakdown(text)
    scalar_request=re.search(r'total|count|average|mean|median|standard deviation|percentile|minimum|maximum|how many|ยอดขายรวม|จำนวน|เท่าไร|เฉลี่ย|มัธยฐาน|เปอร์เซ็นไทล์|ส่วนเบี่ยงเบน',text)
    scalar_pair=(re.search(r'total.*sales|sales.*total',text)
                 and re.search(r'invoice count|count.*invoice',text)
                 and not re.search(r'\bby\b|\bper\b|monthly|\beach\b|\bevery\b|distribution|\btop\b|rank',
                                   text.replace('followed by','')))
    if scalar_pair and (len(tree.expressions)!=2 or tree.args.get('group')):
        raise ValueError('This question requests exactly two scalar outputs: total sales and invoice count. '
                         'Remove the extra month/date column and GROUP BY; retain the requested period filter.')
    if tree.args.get('group') and scalar_request and not grouped_request:
        raise ValueError('Question asks for an overall statistic, not a breakdown: remove unrequested GROUP BY and month/date columns')
    if not re.search(r'\bidentified\b|ระบุตัวตน|(?<!ไม่)มี\s*(?:รหัส|customer.?id)',text):
        return
    scopes=list(traverse_scope(tree))
    def excludes_null(node):
        if isinstance(node,exp.Paren):return excludes_null(node.this)
        if isinstance(node,exp.And):return excludes_null(node.this) or excludes_null(node.expression)
        return (isinstance(node,exp.Not) and isinstance(node.this,exp.Is)
                and isinstance(node.this.this,exp.Column)
                and node.this.this.name.lower()=='customer_id'
                and isinstance(node.this.expression,exp.Null))
    def safe_population(scope,seen):
        if id(scope) in seen:return False
        seen=seen|{id(scope)}
        where=scope.expression.args.get('where')
        if where and excludes_null(where.this):return True
        expression=scope.expression
        # Carry raw invoice rows through a simple CTE only. Every consumer must
        # exclude NULL before aggregation. DISTINCT/LIMIT/joins/renames block proof.
        if (not isinstance(expression,exp.Select) or len(scope.selected_sources)!=1
                or any(expression.args.get(k) for k in ('group','distinct','limit','offset','joins','having'))
                or any(isinstance(n,(exp.AggFunc,exp.Window)) for n in expression.walk())):
            return False
        projections=expression.expressions
        passthrough=any(isinstance(e,exp.Star) or isinstance(e,exp.Column) and
                        (e.name=='*' or e.name.lower()=='customer_id') for e in projections)
        # No alias may redefine the key carried through SELECT *.
        if not passthrough or any(isinstance(e,exp.Alias) and e.alias.lower()=='customer_id' for e in projections):
            return False
        consumers=[s for s in scopes if any(source is scope for _,source in s.selected_sources.values())]
        return bool(consumers) and all(safe_population(s,seen) for s in consumers)
    for scope in scopes:
        if not any(isinstance(source,exp.Table) and source.name.lower()=='orders'
                   for source in scope.sources.values()):
            continue
        if not safe_population(scope,set()):
            raise ValueError('Identified customer population requires customer_id IS NOT NULL '
                             'before grouping/frequency calculation, in the source WHERE or every transparent CTE consumer.')


def result_violations(question, result, sql=None, max_rows=200):
    errors = []
    if not isinstance(result, dict):
        return ['malformed_result']
    columns, rows = result.get('columns'), result.get('rows')
    if (not isinstance(columns, list) or not columns or not all(isinstance(c,str) for c in columns)
            or len(set(c.lower() for c in columns)) != len(columns)
            or not isinstance(rows,list) or type(result.get('truncated')) is not bool):
        return ['malformed_result_envelope']
    if len(rows) > max_rows:
        errors.append('row_cap_exceeded')
    if any(not isinstance(row,(list,tuple)) or len(row) != len(columns) for row in rows):
        return errors + ['row_width_mismatch']
    if any(isinstance(v,(float,Decimal)) and not math.isfinite(float(v)) for row in rows for v in row):
        errors.append('non_finite_numeric_value')
    if sql:
        tree = parse_one(sql, read='spark')
        expressions = tree.expressions
        scalar = (not tree.args.get('group') and any(isinstance(n,exp.AggFunc)
                  for e in expressions if not any(e.find_all(exp.Window)) for n in e.walk()))
        if scalar and len(rows) != 1:
            errors.append('scalar_aggregate_requires_one_row')
        overall_fraction=re.search(r'\bfraction\b|สัดส่วน',question.lower()) and not has_breakdown(question.lower())
        if overall_fraction and (len(rows)!=1 or len(columns)!=1):
            errors.append('overall_fraction_requires_one_value')
        for i, expr in enumerate(expressions):
            expr = expr.this if isinstance(expr, exp.Alias) else expr
            if i < len(columns) and isinstance(expr,exp.Count):
                if any(type(row[i]) is bool or not isinstance(row[i],(int,float,Decimal))
                       or not math.isfinite(float(row[i])) or row[i] < 0
                       or float(row[i]) != int(row[i]) for row in rows):
                    errors.append('count_must_be_nonnegative_integer')
        group = tree.args.get('group')
        if group:
            indices = [i for i,e in enumerate(expressions)
                       if isinstance(e.this if isinstance(e,exp.Alias) else e,exp.Column)]
            if indices and not tree.args.get('joins'):
                keys = [tuple(str(row[i]) for i in indices if i < len(columns)) for row in rows]
                if len(keys) != len(set(keys)):
                    errors.append('duplicate_group_keys')
    text = question.lower()
    if invoice_share_target(text) and len(columns)==1:
        if any(row[0] is not None and (not isinstance(row[0],(int,float,Decimal)) or not 0<=row[0]<=1) for row in rows):
            errors.append('invoice_fraction_out_of_range')
    if re.search(r'identified|ระบุตัวตน',text):
        if any(row[i] is None for i,c in enumerate(columns) if c.lower() == 'customer_id' for row in rows):
            errors.append('identified_customer_id_null')
    if re.search(r'repeat.*(?:rate|fraction)|fraction.*customers|อัตรา.*ซื้อซ้ำ',text) and len(columns)==1:
        if any(row[0] is not None and (not isinstance(row[0],(int,float,Decimal)) or not 0<=row[0]<=1) for row in rows):
            errors.append('fraction_out_of_range')
    return sorted(set(errors))


def validate_result(question, result, sql=None):
    # Envelope checks are mandatory when called by the production agent with SQL.
    if sql:
        violations = result_violations(question,result,sql)
        if violations:
            raise ValueError('Post-tool contract failed: ' + ', '.join(violations))
    text = question.lower()
    columns = result.get('columns', [])
    rows = result.get('rows', [])
    identified = re.search(r'\bidentified\b|ระบุตัวตน|(?<!ไม่)มี\s*(?:รหัส|customer.?id)', text)
    if identified:
        ids = [i for i, name in enumerate(columns) if name.lower() == 'customer_id']
        if any(row[i] is None for row in rows for i in ids):
            raise ValueError('Identified-customer result includes NULL customer_id. '
                             'Exclude anonymous orders before aggregation/ranking using customer_id IS NOT NULL.')
    if re.search(r'repeat.*(?:rate|fraction)|fraction.*customers|อัตรา.*ซื้อซ้ำ', text):
        if len(columns) == 1:
            for row in rows:
                if row[0] is not None and not 0 <= float(row[0]) <= 1:
                    raise ValueError('Repeat customer fraction must be within [0,1]. '
                                     'Count repeat customers divided by ALL identified purchasing customers.')
    return {'status':'passed','checks':['result_envelope','row_width_and_cap','finite_numbers',
            'scalar_shape','nonnegative_integer_counts','unique_group_keys',
            'identified_ids_non_null','fraction_range_when_applicable'] if sql else
            ['identified_ids_non_null','fraction_range_when_applicable'],
            'scope':'deterministic applicable invariants; full answer correctness is measured separately against gold'}
