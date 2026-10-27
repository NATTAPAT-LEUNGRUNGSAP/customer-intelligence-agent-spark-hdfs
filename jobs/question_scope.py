"""Explicit, visible defaults for otherwise unqualified month comparisons."""
import re
import datetime as dt


def validate_time_selection(selection):
    if selection is None:return
    if not isinstance(selection,dict):raise ValueError('Invalid time selection')
    if selection=={'mode':'all'}:return
    if set(selection)!={'mode','start','end'} or selection['mode']!='custom':
        raise ValueError('Choose all data or a custom date range')
    start,end=(dt.date.fromisoformat(selection[k]) for k in ('start','end'))
    if start>end or end==dt.date.max:raise ValueError('Invalid date range')


def apply_time_selection(question, metadata, selection):
    validate_time_selection(selection)
    if selection is None:return question,None
    # Explicit dates/periods and snapshot requests always take precedence.
    if re.search(r'\b(?:19|20|25|26)\d{2}\b|all available|entire.*data|whole.*data|all.time|ข้อมูลทั้งหมด|ตลอดช่วงข้อมูล|snapshot|\brfm\b|high[ -]value|recency|กลุ่มลูกค้า|มูลค่าสูง|แชมเปี้ยน|inactive|champion|180d',question,re.I):
        return question,{'source':'question','default_applied':False,'note':'ใช้ช่วงเวลาหรือ snapshot ตามคำถาม ซึ่งมีลำดับเหนือช่วงเวลาที่เลือกบนเว็บ'}
    if re.search(r'วันนี้|เมื่อวาน|เดือนนี้|เดือนก่อน|ปีนี้|ปีก่อน|ล่าสุด|today|yesterday|last month|this month|this year|last year|latest',question,re.I):
        return question,{'source':'question','default_applied':False,'note':'คำถามระบุเวลาแบบสัมพัทธ์ ต้องตรวจความหมายก่อนใช้ข้อมูลประวัติศาสตร์'}
    if re.search(r'มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b',question,re.I):
        return question,{'source':'question','default_applied':False,'note':'คำถามระบุเดือน ต้องระบุปีให้ชัดเจนก่อนวิเคราะห์'}
    if selection['mode']=='all':
        start,end=metadata.get('observed_min_timestamp'),metadata.get('observed_max_timestamp')
        return question+'\nScope: all available data.',{'source':'web_selection','mode':'all','default_applied':True,'start':start,'end':end,'note':f'ใช้ข้อมูลทั้งหมดที่มี: {start} ถึง {end}'}
    start=selection['start'];end=selection['end']
    exclusive=(dt.date.fromisoformat(end)+dt.timedelta(days=1)).isoformat()
    return (question+f'\nScope: from {start} before {exclusive} (end exclusive).',
            {'source':'web_selection','mode':'custom','default_applied':True,'start':start,'end':end,'end_exclusive':exclusive,'note':f'ใช้ช่วงเวลาที่เลือก: {start} ถึง {end} (รวมวันสิ้นสุด)'})


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
    resolved=(question+'\nScope: all available data. Count completed invoices by calendar year-month. '
              'Output only month and invoice count for all tied highest months, ordered by month. '
              'Use all orders without filters. Do not add label/status columns; '
              'put any partial-month warning in explanation text, not SQL columns.')
    return resolved,{'default_applied':True,'start':start,'end':end,'note':note}


def validate_month_comparison(sql):
    from sqlglot import parse_one, exp
    from sqlglot.optimizer.scope import traverse_scope
    tree=parse_one(sql,read='spark')
    def is_rank(node):
        return isinstance(node,exp.Func) and (node.name.upper() if isinstance(node,exp.Anonymous) else node.sql_name()) in ('RANK','DENSE_RANK')
    count_aliases={a.alias for a in tree.find_all(exp.Alias) if isinstance(a.this,exp.Count)}
    max_aliases={a.alias for a in tree.find_all(exp.Alias) if isinstance(a.this,exp.Max) and isinstance(a.this.this,exp.Column) and a.this.this.name in count_aliases}
    rank_aliases={a.alias for a in tree.find_all(exp.Alias) if isinstance(a.this,exp.Window) and is_rank(a.this.this)}
    selected_maximum=False
    for condition in list(tree.find_all(exp.Where))+list(tree.find_all(exp.Having)):
        if any(condition.find_all(exp.Or)):raise ValueError('Highest-month filter cannot be bypassed with OR')
        for predicate in condition.find_all(exp.EQ):
            for value,other in ((predicate.this,predicate.expression),(predicate.expression,predicate.this)):
                is_count=isinstance(value,exp.Count) or isinstance(value,exp.Column) and value.name in count_aliases
                max_value=(isinstance(other,exp.Column) and other.name in max_aliases or any(isinstance(m.this,exp.Column) and m.this.name in count_aliases for m in other.find_all(exp.Max)))
                is_first_rank=isinstance(value,exp.Column) and value.name in rank_aliases and isinstance(other,exp.Literal) and other.this=='1'
                selected_maximum|=bool(is_count and max_value or is_first_rank)
    if not selected_maximum:
        raise ValueError('Select only tied highest months: filter monthly counts equal to their MAX, or RANK/DENSE_RANK=1. Returning all months sorted by count is not the requested answer')
    if any(tree.find_all(exp.RowNumber,exp.Limit)):
        raise ValueError('All tied highest months are required: do not use ROW_NUMBER or LIMIT; use MAX or rank by count DESC only')
    for window in tree.find_all(exp.Window):
        order=window.args.get('order')
        if is_rank(window.this) and (not order or len(order.expressions)!=1 or not order.expressions[0].args.get('desc')):
            raise ValueError('Preserve ties: rank only by invoice count DESC, without a month tiebreaker')
        if is_rank(window.this) and (not isinstance(order.expressions[0].this,exp.Column) or order.expressions[0].this.name not in count_aliases):
            raise ValueError('Highest-month ranking must order by the aggregated invoice count, not the month itself')
    for scope in traverse_scope(tree):
        tables=[s for s in scope.sources.values() if isinstance(s,exp.Table)]
        if not tables:continue
        if len(tables)!=1 or tables[0].name.lower()!='orders' or scope.expression.args.get('where') or scope.expression.args.get('joins'):
            raise ValueError('All-data invoice comparison requires orders without filters or joins; do not exclude the maximum observed timestamp')
        group=scope.expression.args.get('group')
        grouped=group.expressions[0] if group and len(group.expressions)==1 else None
        if isinstance(grouped,exp.Column):
            grouped=next((e.this for e in scope.expression.expressions if isinstance(e,exp.Alias) and e.alias==grouped.name),grouped)
        if isinstance(grouped,exp.Literal) and grouped.is_int:
            position=int(grouped.this)-1
            if 0<=position<len(scope.expression.expressions):
                grouped=scope.expression.expressions[position]
                if isinstance(grouped,exp.Alias):grouped=grouped.this
        if not isinstance(grouped,exp.TimestampTrunc):
            raise ValueError("Group source invoices by DATE_TRUNC('MONTH', order_ts) to retain both year and month")
        month=grouped
        if str(month.args.get('unit')).upper()!='MONTH' or not isinstance(month.this,exp.Column) or month.this.name.lower()!='order_ts':
            raise ValueError('Monthly invoice grouping must use order_ts at MONTH precision')
