"""Explicit, visible defaults for otherwise unqualified month comparisons."""
import re


def resolve_scope(question, metadata):
    text=question.strip().rstrip('?？').strip().lower()
    # Full match deliberately excludes extra dates, countries and other intents.
    monthly_orders=re.fullmatch(
        r'(?:เดือน(?:ไหน|ใด)(?:มี)?(?:ออเดอร์|คำสั่งซื้อ|orders?)(?:เยอะ|มาก)(?:ที่)?สุด(?:ครับ|คะ|ค่ะ)?|'
        r'which month (?:has|had) (?:the )?most (?:orders|invoices))',text)
    start,end=metadata.get('observed_min_timestamp'),metadata.get('observed_max_timestamp')
    if not monthly_orders or not start or not end:return question,None
    note=(f'ใช้ข้อมูลทั้งหมดที่มี: {start} ถึง {end} โดยเปรียบเทียบแยกปีและเดือน '
          'นับคำสั่งซื้อสำเร็จเป็นใบ ไม่ใช่จำนวนรายการสินค้า '
          'เดือนต้นและท้ายช่วงอาจมีข้อมูลไม่ครบเดือน; แสดงทุกเดือนที่ได้อันดับสูงสุดเท่ากัน')
    resolved=(question+'\nScope: all available data from '+start+' through '+end+'. '
              'Which calendar year-month has the highest completed invoice count? '
              'Use all rows of orders without a WHERE time filter: the loaded table is already the observed dataset, '
              'and its maximum timestamp is inclusive. Count orders, not product lines; '
              'group by year-month, never merge the same month across years. '
              'Return every tied highest month and its invoice count, ordered by year-month. '
              'Use MAX comparison or RANK/DENSE_RANK ordered only by count DESC, never ROW_NUMBER or LIMIT 1. '
              'Do not discard partial boundary months; mention they may be partial. Respond in Thai.')
    return resolved,{'default_applied':True,'start':start,'end':end,'note':note}


def validate_month_comparison(sql):
    from sqlglot import parse_one, exp
    from sqlglot.optimizer.scope import traverse_scope
    tree=parse_one(sql,read='spark')
    if any(tree.find_all(exp.RowNumber,exp.Limit)):
        raise ValueError('All tied highest months are required: do not use ROW_NUMBER or LIMIT; use MAX or rank by count DESC only')
    for window in tree.find_all(exp.Window):
        order=window.args.get('order')
        if isinstance(window.this,(exp.Rank,exp.DenseRank)) and (not order or len(order.expressions)!=1 or not order.expressions[0].args.get('desc')):
            raise ValueError('Preserve ties: rank only by invoice count DESC, without a month tiebreaker')
    for scope in traverse_scope(tree):
        tables=[s for s in scope.sources.values() if isinstance(s,exp.Table)]
        if not tables:continue
        if len(tables)!=1 or tables[0].name.lower()!='orders' or scope.expression.args.get('where') or scope.expression.args.get('joins'):
            raise ValueError('All-data invoice comparison requires orders without filters or joins; do not exclude the maximum observed timestamp')
        group=scope.expression.args.get('group')
        if not group or len(group.expressions)!=1 or not isinstance(group.expressions[0],exp.TimestampTrunc):
            raise ValueError("Group source invoices by DATE_TRUNC('MONTH', order_ts) to retain both year and month")
        month=group.expressions[0]
        if str(month.args.get('unit')).upper()!='MONTH' or not isinstance(month.this,exp.Column) or month.this.name.lower()!='order_ts':
            raise ValueError('Monthly invoice grouping must use order_ts at MONTH precision')
