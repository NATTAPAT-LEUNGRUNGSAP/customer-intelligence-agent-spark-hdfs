"""Narrow result contracts; these do not certify general SQL semantics."""
import re
from sqlglot import parse_one, exp
from sqlglot.optimizer.scope import traverse_scope


def validate_semantics(question, sql):
    """Require explicit identified population where orders feed a customer metric."""
    text=question.lower()
    tree=parse_one(sql,read='spark')
    scalar_pair=(re.search(r'total.*sales|sales.*total',text)
                 and re.search(r'invoice count|count.*invoice',text)
                 and not re.search(r'\bby\b|\bper\b|monthly|\beach\b|\bevery\b|distribution|\btop\b|rank',
                                   text.replace('followed by','')))
    if scalar_pair and (len(tree.expressions)!=2 or tree.args.get('group')):
        raise ValueError('This question requests exactly two scalar outputs: total sales and invoice count. '
                         'Remove the extra month/date column and GROUP BY; retain the requested period filter.')
    if not re.search(r'identified|ระบุตัวตน|มี.*(?:รหัส|customer.?id)',text):
        return
    for scope in traverse_scope(tree):
        if not any(isinstance(source,exp.Table) and source.name.lower()=='orders'
                   for source in scope.sources.values()):
            continue
        where=scope.expression.args.get('where')
        # Require an unambiguous conjunct; an OR can still admit anonymous rows.
        def excludes_null(node):
            if isinstance(node,exp.Paren):
                return excludes_null(node.this)
            if isinstance(node,exp.And):
                return excludes_null(node.this) or excludes_null(node.expression)
            return (isinstance(node,exp.Not) and isinstance(node.this,exp.Is)
                    and isinstance(node.this.this,exp.Column)
                    and node.this.this.name.lower()=='customer_id'
                    and isinstance(node.this.expression,exp.Null))
        if not where or not excludes_null(where.this):
            raise ValueError('Identified customer population requires customer_id IS NOT NULL '
                             'in each orders source WHERE, before grouping or computing repeat frequencies.')


def validate_result(question, result):
    text = question.lower()
    columns = result.get('columns', [])
    rows = result.get('rows', [])
    identified = re.search(r'identified|ระบุตัวตน|มี.*(?:รหัส|customer.?id)', text)
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
    return {'status':'passed','checks':['identified_ids_non_null','fraction_range_when_applicable'],
            'scope':'limited result invariants; not independent semantic certification'}
