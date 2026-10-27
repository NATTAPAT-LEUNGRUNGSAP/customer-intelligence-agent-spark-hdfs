"""Narrow metric/shape checks, never query generation or an evaluation lookup."""
import re
from sqlglot import parse_one,exp


def invoice_share_target(text):
    return bool(re.search(r'anonymous invoice fraction|fraction of invoices|single.product invoice fraction|สัดส่วนคำสั่งซื้อ',text))


def has_breakdown(text):
    return bool(re.search(r'\bby\s+(?:country|month|year|quarter|week|day|hour|product|customer|rfm_segment|segment|transaction_type)\b|\bper\s+(?:country|month|year|product|customer_id)\b|monthly|daily|weekly|hourly|quarterly|yearly|each (?:month|country|customer|product)|แต่ละประเทศ|แยก|รายเดือน|รายวัน|รายชั่วโมง|รายไตรมาส|รายปี|รายสัปดาห์|อันดับ|\brank\b|\btop\s+\d|which month|เดือนไหน|distribution',text))


def expected_columns(text):
    if re.search(r'แสดงรหัสและค่า|output (?:customer|product) id and value|แสดงเฉพาะเดือนและค่า|output only month and|each country and its fraction|แต่ละประเทศกับสัดส่วน',text):return 2
    if re.search(r'\bfraction\b|สัดส่วน',text) and not has_breakdown(text):return 1
    metrics=(r'\bsales\b|ยอดขาย',r'invoice count|จำนวนคำสั่งซื้อ',r'\baov\b|average order value|มูลค่าเฉลี่ยต่อคำสั่งซื้อ',r'distinct purchasing customer|จำนวนลูกค้าไม่ซ้ำ',r'\bunits\b|จำนวนสินค้าที่ขาย')
    compound=re.search(r'\b(?:and|plus)\b.+\b(?:sales|count|aov|units|mean|average|growth|cumulative)\b',text)
    if has_breakdown(text) and sum(bool(re.search(m,text)) for m in metrics)==1 and not compound:return 2
    if has_breakdown(text) and re.search(r'by transaction_type|แยก transaction_type',text):return 2
    if not has_breakdown(text) and not compound and not re.search(r'\band\b|followed by|และ|กับ',text) and re.search(r'\bcount\b|how many|\bcalculate\b|find the|เท่าไร|คำนวณ|นับ|\bnumber of\b',text):return 1
    return None


def projection_wildcard(expression):
    expression=expression.this if isinstance(expression,exp.Alias) else expression
    return isinstance(expression,exp.Star) or isinstance(expression,exp.Column) and isinstance(expression.this,exp.Star)


def request_constraints(question):
    from semantic_contracts import requested_period
    text=question.lower()
    constraints={}
    period=requested_period(question)
    if period:
        constraints['transaction_period']={'start_inclusive':period[0]+' 00:00:00','end_exclusive':period[1]+' 00:00:00',
            'filter':'Use direct timestamp column comparisons >= TIMESTAMP start and < TIMESTAMP end; DATE_TRUNC is for GROUP BY, not WHERE',
            'columns':{'orders':'order_ts','sales_lines':'invoice_ts'}}
    columns=expected_columns(text)
    if columns:constraints['output_column_count']=columns
    if re.search(r'total units|units sold|units purchased|show units\b|จำนวนสินค้าที่ขาย|จำนวนสินค้าที่ซื้อ',text) and not re.search(r'product ids?|สินค้า\s*\d',text):
        constraints['metric']={'meaning':'sold/purchased unit quantity, not money','source':'orders.total_units','aggregation':'SUM'}
    if re.search(r'ordered by country|เรียงประเทศ|เรียงชื่อประเทศ',text):constraints['final_order']='country ASC'
    for word,unit in [('quarterly','QUARTER'),('รายไตรมาส','QUARTER'),('hourly','HOUR'),('รายชั่วโมง','HOUR'),('weekly','WEEK'),('รายสัปดาห์','WEEK'),('yearly','YEAR'),('รายปี','YEAR'),('daily','DAY'),('รายวัน','DAY'),('monthly','MONTH'),('รายเดือน','MONTH')]:
        if word in text:constraints['time_bucket_unit']=unit;break
    snapshot=re.search(r'snapshot\s+(\d{4}-\d{2}-\d{2})',text)
    if snapshot:
        constraints['snapshot']={'source_table':'customer_summary','as_of_date':snapshot[1],
                                 'meaning':'Use prebuilt customer fields for this snapshot; do not substitute all historical orders'}
        if re.search(r'mean 180.day order count|จำนวนคำสั่งซื้อ 180 วันเฉลี่ย',text):
            constraints['metric']={'source':'customer_summary.orders_180d','aggregation':'AVG'}
    if re.search(r'anonymous invoice sales share|สัดส่วนยอดขายจากคำสั่งซื้อที่ไม่มีรหัส',text):
        constraints['metric']={'source':'orders','numerator':'SUM order_amount for anonymous invoices only',
                               'denominator':'SUM order_amount for ALL invoices in the same period','unit':'fraction of money, not fraction of invoice counts'}
    if re.search(r'สัดส่วน|\bfraction\b',text):constraints['ratio']='Return the ratio itself, not just numerator or both intermediate counts'
    if invoice_share_target(text):
        constraints['metric']={'source':'orders','meaning':'fraction of invoice counts, not monetary share',
            'numerator':'count invoices satisfying the requested condition with CASE',
            'denominator':'count ALL invoices in the same time/country population; do not filter the condition in WHERE'}
        if re.search(r'anonymous|ไม่มีรหัส',text):constraints['metric']['condition']='customer_id IS NULL'
        elif re.search(r'single.product|ชนิดเดียว',text):constraints['metric']['condition']='distinct_products = 1'
        else:
            threshold=re.search(r'(?:above|ยอดมากกว่า)\s*(\d+(?:\.\d+)?)',text)
            if threshold:constraints['metric']['condition']='order_amount > '+threshold[1]
    if re.search(r'product ids?|สินค้า\s*\d',text) and re.search(r'distinct(?: identified)? purchasing customers|จำนวนลูกค้าที่มีรหัสไม่ซ้ำ',text):
        constraints['metric']={'source':'sales_lines.customer_id','aggregation':'COUNT DISTINCT',
            'group_by':'product_id','transaction_type':'sale','meaning':'product-specific buyers; orders has no product_id'}
    if re.search(r'each country and its fraction|แต่ละประเทศกับสัดส่วน',text):
        constraints['aggregation_stages']=['Sum order_amount per country in a CTE after the time filter',
                                           'On the grouped rows divide sales by SUM(sales) OVER ()',
                                           'Return country and fraction only; follow syntax.ratios']
    if re.search(r'\baov\b|average order value|average invoice value|มูลค่าเฉลี่ย(?:ต่อ)?คำสั่งซื้อ',text) and not snapshot:
        constraints['metric']={'source':'orders.order_amount','aggregation':'AVG','meaning':'transaction AOV in the requested period, not snapshot aov_180d'}
    return constraints


def validate_metric_expression(question,sql):
    text=question.lower()
    tree=parse_one(sql,read='spark')
    checks=[]
    def aggregate(kind,column):
        return any(isinstance(n.this,exp.Column) and n.this.name.lower()==column for n in tree.find_all(kind))
    if invoice_share_target(text):
        forbidden={'customer_id'} if re.search(r'anonymous|ไม่มีรหัส',text) else {'order_amount'} if re.search(r'above|ยอดมากกว่า',text) else {'distinct_products'} if re.search(r'single.product|ชนิดเดียว',text) else set()
        for where in tree.find_all(exp.Where):
            if any(c.name.lower() in forbidden for c in where.find_all(exp.Column)):
                raise ValueError('Keep the full invoice denominator: move the requested anonymous/amount/product condition from WHERE to a CASE numerator')
        def number(node,value):
            if not isinstance(node,exp.Literal) or node.is_string:return False
            try:return float(node.this)==value
            except (ValueError,TypeError):return False
        def indicator_case(node,require_zero=False):
            return isinstance(node,exp.Case) and bool(node.args.get('ifs')) and all(number(branch.args.get('true'),1) for branch in node.args['ifs']) and (number(node.args.get('default'),0) or not require_zero and (node.args.get('default') is None or isinstance(node.args.get('default'),exp.Null)))
        count_rows=any(isinstance(c.this,exp.Star) or number(c.this,1) or isinstance(c.this,exp.Column) and c.this.name.lower()=='invoice_id' for c in tree.find_all(exp.Count))
        numerator=any(indicator_case(s.this,True) for s in tree.find_all(exp.Sum)) or any(indicator_case(c.this) and not number(c.this.args.get('default'),0) for c in tree.find_all(exp.Count))
        average_indicator=any(indicator_case(a.this,True) or isinstance(a.this,exp.Cast) and isinstance(a.this.this,(exp.EQ,exp.GT,exp.GTE,exp.LT,exp.LTE,exp.Is,exp.Not,exp.And,exp.Or)) for a in tree.find_all(exp.Avg))
        if not average_indicator and not (count_rows and numerator):
            raise ValueError('Invoice fraction needs a 1/0 CASE invoice numerator divided by COUNT(*) of all invoices, or AVG of a boolean indicator; do not substitute money or COUNT of only the filtered subset')
        condition=request_constraints(question).get('metric',{}).get('condition')
        if condition:
            candidates=[b.this for c in tree.find_all(exp.Case) for b in c.args.get('ifs',[])]+[c.this for c in tree.find_all(exp.Cast)]
            def terms(node):return terms(node.this)+terms(node.expression) if isinstance(node,exp.And) else [node]
            found=False
            for candidate in candidates:
                for term in terms(candidate):
                    if condition=='customer_id IS NULL':
                        found|=isinstance(term,exp.Is) and isinstance(term.this,exp.Column) and term.this.name.lower()=='customer_id' and isinstance(term.expression,exp.Null)
                    elif condition=='distinct_products = 1':
                        found|=isinstance(term,exp.EQ) and isinstance(term.this,exp.Column) and term.this.name.lower()=='distinct_products' and number(term.expression,1)
                    else:
                        value=float(condition.rsplit(' ',1)[1])
                        found|=isinstance(term,exp.GT) and isinstance(term.this,exp.Column) and term.this.name.lower()=='order_amount' and number(term.expression,value)
            if not found:raise ValueError('Invoice-share numerator must use the requested condition: '+condition)
        checks.append('invoice_share_population_and_unit')
    breakdown=has_breakdown(text)
    columns=expected_columns(text)
    if columns and len(tree.expressions)!=columns:
        raise ValueError('Requested output requires exactly '+str(columns)+' column(s); remove unrequested dimensions, totals and intermediate values')
    if re.search(r'\bfraction\b|สัดส่วน',text):
        if any(any(isinstance(child,exp.Literal) and child.this=='100' for child in (node.this,node.expression)) for node in tree.find_all(exp.Mul)):
            raise ValueError('Question asks for a fraction, not percent: remove multiplication by 100')
        if not breakdown and not any(tree.find_all(exp.Div)) and not any(isinstance(a.this,(exp.Case,exp.Cast,exp.If)) for a in tree.find_all(exp.Avg)):
            raise ValueError('A fraction requires numerator divided by denominator (or mean of an indicator), not a standalone subset count')
    if re.search(r'each country and its fraction|แต่ละประเทศกับสัดส่วน',text) and len(tree.expressions)!=2:
        raise ValueError('Return only country and sales share, not an extra sales amount column')
    if re.search(r'ordered by country|เรียงประเทศ|เรียงชื่อประเทศ',text):
        order=tree.args.get('order')
        if not order or not order.expressions or not isinstance(order.expressions[0].this,exp.Column) or order.expressions[0].this.name.lower()!='country' or order.expressions[0].args.get('desc'):
            raise ValueError('Requested final ordering is country ascending, not metric descending')
    if re.search(r'\bfraction\b|สัดส่วน',text) and not breakdown:
        if len(tree.expressions)!=1 or projection_wildcard(tree.expressions[0]):
            raise ValueError('Question asks for one overall fraction: return only the ratio, not numerator and denominator columns or individual customer rows')
        checks.append('scalar_fraction_shape')
    if re.search(r'แสดงรหัสและค่า|output (?:customer|product) id and value|แสดงเฉพาะเดือนและค่า|output only month and',text):
        if len(tree.expressions)!=2 or any(projection_wildcard(e) for e in tree.expressions):
            raise ValueError('Question explicitly asks for two columns: dimension ID/month and metric value. Do not add description, status or other columns; spell out both projections')
        checks.append('explicit_two_column_shape')
    product=bool(re.search(r'\bproduct ids?\b|สินค้า\s*\d',text))
    if product and re.search(r'distinct(?: identified)? purchasing customers|จำนวนลูกค้าที่มีรหัสไม่ซ้ำ',text):
        if not any(isinstance(c.this,exp.Distinct) and any(column.name.lower()=='customer_id' for column in c.this.find_all(exp.Column)) for c in tree.find_all(exp.Count)):
            raise ValueError('Product-specific purchasing customers require COUNT(DISTINCT customer_id) from sale lines, not distinct product IDs or invoice count')
        checks.append('product_buyer_count')
    units=re.search(r'total units|units sold|units purchased|show units\b|sale units|จำนวนสินค้าที่ขาย|จำนวนสินค้าที่ซื้อ|จำนวนหน่วยสินค้าที่ขาย|สินค้า\s*\d.*จำนวนหน่วย',text)
    if units:
        column='quantity' if product else 'total_units'
        if not aggregate(exp.Sum,column):
            raise ValueError('Requested sold/purchased units require SUM('+column+'), not invoice count, distinct product count or money')
        checks.append('units_not_money')
    aov=re.search(r'\baov\b|average order value|average invoice value|มูลค่าเฉลี่ย(?:ต่อ)?คำสั่งซื้อ',text)
    if aov and not re.search(r'snapshot|aov_180d',text):
        division=any(any(isinstance(n.this,exp.Column) and n.this.name.lower()=='order_amount' for n in d.this.find_all(exp.Sum)) and any(not isinstance(n.this,exp.Distinct) for n in d.expression.find_all(exp.Count)) for d in tree.find_all(exp.Div))
        if not aggregate(exp.Avg,'order_amount') and not division:
            raise ValueError('Transaction AOV requires AVG(order_amount) or SUM(order_amount)/NULLIF(COUNT(*),0) on orders, not snapshot aov_180d')
        checks.append('transaction_aov')
    if re.search(r'mean distinct products per invoice|จำนวนสินค้าแตกต่างกันเฉลี่ยต่อใบ|จำนวนสินค้าต่างชนิดเฉลี่ยต่อคำสั่งซื้อ',text):
        if not aggregate(exp.Avg,'distinct_products'):
            raise ValueError('Mean distinct products per invoice requires AVG(distinct_products) from orders; it is not units or monetary AOV')
        checks.append('basket_variety')
    frequency=re.search(r'invoice frequency per identified purchasing customer|จำนวนคำสั่งซื้อเฉลี่ยต่อผู้ซื้อที่มีรหัส',text)
    spend=re.search(r'sales per identified purchasing customer|ยอดขายต่อผู้ซื้อที่มีรหัส',text)
    if frequency or spend:
        if len(tree.expressions)!=1 or not any(tree.find_all(exp.Div)):
            raise ValueError('Requested population average is one scalar ratio, not a list of individual customer frequencies')
        if not any(isinstance(n.this,exp.Distinct) and any(c.name.lower()=='customer_id' for c in n.this.find_all(exp.Column)) for n in tree.find_all(exp.Count)):
            raise ValueError('Per-purchasing-customer average requires COUNT(DISTINCT customer_id) in the denominator, not invoice count or transaction AOV')
        if spend and not aggregate(exp.Sum,'order_amount'):
            raise ValueError('Sales per identified customer requires SUM(order_amount), excluding anonymous invoices')
        if frequency and aggregate(exp.Sum,'order_amount'):
            raise ValueError('Invoice frequency counts invoices, not money; do not substitute AOV')
        checks.append('population_average_metric')
    if re.search(r'sale product.line count|จำนวนรายการขาย',text) and product:
        if not any(isinstance(n.this,exp.Star) for n in tree.find_all(exp.Count)):
            raise ValueError('Sale product-line count requires COUNT(*) over filtered sales_lines, not SUM(quantity)')
        checks.append('line_count_not_units')
    if re.search(r'quantity.weighted sale unit price|ราคาขายต่อหน่วยเฉลี่ยแบบถ่วงน้ำหนัก',text):
        weighted=False
        for division in tree.find_all(exp.Div):
            denominator=any(isinstance(n.this,exp.Column) and n.this.name.lower()=='quantity' for n in division.expression.find_all(exp.Sum))
            numerator=any(isinstance(n.this,exp.Column) and n.this.name.lower()=='line_amount' or isinstance(n.this,exp.Mul) and {'quantity','unit_price'}.issubset({c.name.lower() for c in n.this.find_all(exp.Column)}) for n in division.this.find_all(exp.Sum))
            weighted|=denominator and numerator
        if not weighted:raise ValueError('Quantity-weighted sale unit price requires SUM(line_amount)/NULLIF(SUM(quantity),0), not revenue alone or AVG(unit_price)')
        checks.append('weighted_unit_price')
    if re.search(r'monthly invoice count|จำนวนคำสั่งซื้อรายเดือน',text):
        if not any(isinstance(n.this,exp.Star) or isinstance(n.this,exp.Column) and n.this.name.lower()=='invoice_id' for n in tree.find_all(exp.Count)):
            raise ValueError('Monthly invoice count requires a COUNT of invoice rows, in addition to the month bucket')
        checks.append('monthly_count_measure')
    requested_unit=request_constraints(question).get('time_bucket_unit')
    if requested_unit:
        if not any(str(n.args.get('unit')).upper()==requested_unit for n in tree.find_all(exp.TimestampTrunc)):
            raise ValueError('Requested time bucket is '+requested_unit+', not a different interval; include the requested count/value column')
        checks.append('requested_time_bucket')
    if re.search(r'anonymous invoice sales share|สัดส่วนยอดขายจากคำสั่งซื้อที่ไม่มีรหัส',text):
        if not any(any(c.name.lower()=='order_amount' for c in s.find_all(exp.Column)) for s in tree.find_all(exp.Sum)):
            raise ValueError('Anonymous invoice SALES share must sum order_amount, not count invoices; numerator and denominator are money')
        checks.append('sales_share_not_invoice_share')
    if re.search(r'snapshot',text) and re.search(r'mean 180.day order count|จำนวนคำสั่งซื้อ 180 วันเฉลี่ย',text):
        if not aggregate(exp.Avg,'orders_180d'):
            raise ValueError('Mean snapshot 180-day invoice count requires AVG(orders_180d), not customer AOV')
        checks.append('snapshot_frequency_not_aov')
    if re.search(r'cumulative sales|ยอดขายสะสม',text):
        if not any(isinstance(w.this,exp.Sum) for w in tree.find_all(exp.Window)):
            raise ValueError('Cumulative sales require a SUM window over monthly sales, not raw monthly sales with a cumulative alias')
        checks.append('cumulative_sum_window')
    if re.search(r'previous.*month|เดือนก่อน',text) and 'null' in text:
        if any(isinstance(value,exp.Literal) and value.this=='0' for n in tree.find_all(exp.Coalesce) for value in [n.this,*n.expressions]):
            raise ValueError('Question requires first-month NULL; do not replace the previous-month NULL with zero')
    conditional_fraction=re.search(r'fraction of invoices above|สัดส่วนคำสั่งซื้อที่ยอดมากกว่า',text)
    if conditional_fraction:
        for where in tree.find_all(exp.Where):
            if any(c.name.lower()=='order_amount' for c in where.find_all(exp.Column)):
                raise ValueError('Invoice amount threshold belongs in the numerator CASE, not WHERE; denominator must retain all invoices in the period')
    unique=re.search(r'distinct purchasing customers|distinct purchasing customer count|จำนวนลูกค้าไม่ซ้ำ|จำนวนลูกค้าที่ซื้อแบบไม่ซ้ำ',text)
    if unique:
        if not any(isinstance(n.this,exp.Distinct) and any(c.name.lower()=='customer_id' for c in n.this.find_all(exp.Column)) for n in tree.find_all(exp.Count)):
            raise ValueError('Unique purchasing customers require COUNT(DISTINCT customer_id), not only one-order customers or invoice count')
        explicit_identified=re.search(r'\bidentified\b|ระบุตัวตน|ที่มีรหัส',text)
        if re.search(r'by country|แยกประเทศ',text) and not explicit_identified and re.search(r'customer_id\s+IS\s+NOT\s+NULL',sql,re.I):
            raise ValueError('Keep all country groups, including countries with zero identified buyers: COUNT(DISTINCT customer_id) already excludes NULL; do not remove anonymous rows in WHERE')
        checks.append('unique_customers')
    return checks
