"""Author a paired development bank; never imported by the production agent.

Questions are original adaptations of UCI fields and documented Spark analytics,
not 200 quotations collected from a third party, nor an independent holdout.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PAIRS=[]


def add(family,th,en,sql=None,ids=(),formula=None,policy=None,ordered=False):
    PAIRS.append(dict(pair_id=f'pair{len(PAIRS)+1:03}',family=family,th=th,en=en,
                      gold_sql=sql,relevant_ids=list(ids),formula_id=formula,
                      clarification_policy=policy,ordered=ordered))


P="order_ts>=TIMESTAMP '2011-01-01' AND order_ts<TIMESTAMP '2011-02-01'"
L=P.replace('order_ts','invoice_ts')
Y="order_ts>=TIMESTAMP '2011-01-01' AND order_ts<TIMESTAMP '2012-01-01'"
S="as_of_date=DATE '2011-12-01'"
M="DATE_TRUNC('MONTH',order_ts)"
monthly=f'SELECT {M} AS month,SUM(order_amount) AS sales FROM orders WHERE {Y} GROUP BY {M}'

# 75 executable intents in 15 distinct analytical families (five per family).
for th,en,expr,metric in [
 ('ยอดขายรวม','total completed sales','SUM(order_amount)','sales'),
 ('จำนวนคำสั่งซื้อสำเร็จ','completed invoice count','COUNT(*)','orders'),
 ('มูลค่าเฉลี่ยต่อคำสั่งซื้อ','average order value','AVG(order_amount)','aov'),
 ('จำนวนลูกค้าที่ซื้อแบบไม่ซ้ำ','distinct purchasing customer count','COUNT(DISTINCT customer_id)','customers'),
 ('จำนวนสินค้าที่ขายรวมในคำสั่งซื้อสำเร็จ','total units in completed invoices','SUM(total_units)','orders')]:
    add('scalar',f'เดือนมกราคม 2011 {th}เท่าไร',f'For January 2011, what is the {en}?',f'SELECT {expr} AS value FROM orders WHERE {P}',[f'metric.{metric}','schema.orders'])

for th,en,expr in [
 ('มูลค่าคำสั่งซื้อสูงสุด','maximum invoice value','MAX(order_amount)'),
 ('มูลค่าคำสั่งซื้อต่ำสุด','minimum invoice value','MIN(order_amount)'),
 ('ส่วนเบี่ยงเบนมาตรฐานแบบตัวอย่างของมูลค่าคำสั่งซื้อ','sample standard deviation of invoice value','STDDEV(order_amount)'),
 ('มัธยฐานโดยประมาณของมูลค่าคำสั่งซื้อ','approximate median invoice value','PERCENTILE_APPROX(order_amount,0.5,10000)'),
 ('เปอร์เซ็นไทล์ที่ 90 โดยประมาณของมูลค่าคำสั่งซื้อ','approximate 90th percentile of invoice value','PERCENTILE_APPROX(order_amount,0.9,10000)')]:
    add('statistics',f'เดือนมกราคม 2011 {th}เท่าไร',f'For January 2011, calculate the {en}.',f'SELECT {expr} AS value FROM orders WHERE {P}',['schema.orders','syntax.statistics'])

for th,en,expr in [('ยอดขาย','sales','SUM(order_amount)'),('จำนวนคำสั่งซื้อ','invoice count','COUNT(*)'),('AOV','AOV','AVG(order_amount)'),('จำนวนลูกค้าไม่ซ้ำ','distinct purchasing customers','COUNT(DISTINCT customer_id)'),('จำนวนสินค้าที่ขาย','units','SUM(total_units)')]:
    add('country',f'แสดง{th}แยกประเทศเดือนมกราคม 2011 เรียงชื่อประเทศ',f'For January 2011 show {en} by country, ordered by country.',f'SELECT country,{expr} AS value FROM orders WHERE {P} GROUP BY country ORDER BY country',['schema.orders','syntax.aggregation'],ordered=True)

for th,en,expr in [('ยอดขาย','sales','SUM(order_amount)'),('จำนวนคำสั่งซื้อ','invoice count','COUNT(*)'),('มูลค่าเฉลี่ยคำสั่งซื้อ','average invoice value','AVG(order_amount)'),('จำนวนสินค้าที่ซื้อ','units purchased','SUM(total_units)'),('จำนวนสินค้าแตกต่างกันเฉลี่ยต่อใบ','mean distinct products per invoice','AVG(distinct_products)')]:
    add('customer_ranking',f'ลูกค้าที่มีรหัส 5 อันดับแรกตาม{th}เดือนมกราคม 2011 แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น',f'Rank the top 5 identified customers by {en} in January 2011. Output customer ID and value; order value descending then customer ID ascending.',f'SELECT customer_id,{expr} AS value FROM orders WHERE {P} AND customer_id IS NOT NULL GROUP BY customer_id ORDER BY value DESC,customer_id ASC LIMIT 5',['schema.orders','syntax.ranking'],ordered=True)

for th,en,expr,extra in [('ยอดขาย','sale revenue','SUM(line_amount)',''),('จำนวนหน่วย','sale units','SUM(quantity)',''),('จำนวนรายการขาย','sale product-line count','COUNT(*)',''),('ราคาขายต่อหน่วยเฉลี่ยแบบถ่วงน้ำหนัก','quantity-weighted sale unit price','SUM(line_amount)/NULLIF(SUM(quantity),0)',''),('จำนวนลูกค้าที่มีรหัสไม่ซ้ำ','distinct identified purchasing customers','COUNT(DISTINCT customer_id)','')]:
    add('product_ranking',f'สินค้า 5 อันดับตาม{th}เดือนมกราคม 2011 ใช้เฉพาะรายการ sale แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น',f'For January 2011 rank top 5 product IDs by {en}, using only sale lines. Output product ID and value; order value descending then product ID ascending.',f"SELECT product_id,{expr} AS value FROM sales_lines WHERE transaction_type='sale' AND {L} GROUP BY product_id ORDER BY value DESC,product_id ASC LIMIT 5",['schema.sales_lines','syntax.ranking'],ordered=True)

for th,en,expr in [('ยอดขาย','sales','SUM(order_amount)'),('จำนวนคำสั่งซื้อ','invoice count','COUNT(*)'),('AOV','AOV','AVG(order_amount)'),('จำนวนลูกค้าไม่ซ้ำ','distinct purchasing customers','COUNT(DISTINCT customer_id)'),('จำนวนสินค้าที่ขาย','units sold','SUM(total_units)')]:
    add('monthly',f'แสดง{th}รายเดือนตลอดปี 2011 แยกปีเดือน เรียงเดือน',f'Show monthly {en} for calendar year 2011, grouped by year-month and ordered by month.',f'SELECT {M} AS month,{expr} AS value FROM orders WHERE {Y} GROUP BY {M} ORDER BY month',['schema.orders','syntax.time'],ordered=True)

for kind,th in [('sale','ขาย'),('cancellation','ยกเลิก'),('return','คืนสินค้า'),('adjustment','ปรับปรุง'),('invalid','ไม่ถูกต้อง')]:
    add('transaction_types',f'เดือนมกราคม 2011 มีรายการสินค้าประเภท {kind} ({th}) กี่แถว',f'Count original product lines classified as {kind} in January 2011.',f"SELECT COUNT(*) AS value FROM sales_lines WHERE transaction_type='{kind}' AND {L}",['schema.sales_lines','syntax.transactions'])

for th,en,condition,ids in [('ลูกค้าทั้งหมด','all customers','1=1',['schema.customer_summary']),('ลูกค้ามูลค่าสูง','high-value customers','is_high_value=true',['metric.high_value']),('ลูกค้า Champions','Champions',"rfm_segment='Champions'",['segment.champions']),('ลูกค้า Inactive','Inactive customers',"rfm_segment='Inactive'",['segment.inactive']),('ลูกค้าที่เป็นทั้ง Champions และ high-value','customers who are both Champions and high-value',"rfm_segment='Champions' AND is_high_value=true",['segment.champions','metric.high_value'])]:
    add('snapshot_counts',f'ณ snapshot 2011-12-01 นับ{th}',f'At snapshot 2011-12-01 count {en}.',f'SELECT COUNT(*) AS value FROM customer_summary WHERE {S} AND {condition}',ids+['schema.customer_summary'])

for th,en,expr in [('recency เฉลี่ย','mean recency days','AVG(recency_days)'),('จำนวนคำสั่งซื้อ 180 วันเฉลี่ย','mean 180-day order count','AVG(orders_180d)'),('ยอดซื้อ 180 วันรวม','total 180-day sales','SUM(sales_180d)'),('AOV ของลูกค้าเฉลี่ยแบบไม่ถ่วงน้ำหนัก','unweighted mean of customer AOV','AVG(aov_180d)'),('จำนวนลูกค้าในแต่ละกลุ่ม RFM','customer count','COUNT(*)')]:
    add('segment_statistics',f'ณ snapshot 2011-12-01 แสดง{th}แยก rfm_segment เรียงชื่อกลุ่ม',f'At snapshot 2011-12-01 show {en} by rfm_segment, ordered by segment.',f'SELECT rfm_segment,{expr} AS value FROM customer_summary WHERE {S} GROUP BY rfm_segment ORDER BY rfm_segment',['segment.distribution','schema.customer_summary'],ordered=True)

for th,en,expr in [('จำนวนหน่วยเฉลี่ยต่อคำสั่งซื้อ','mean units per invoice','AVG(total_units)'),('จำนวนสินค้าต่างชนิดเฉลี่ยต่อคำสั่งซื้อ','mean distinct products per invoice','AVG(distinct_products)'),('จำนวนคำสั่งซื้อที่มีหน่วยสินค้ามากกว่า 20','count of invoices with more than 20 units','SUM(CASE WHEN total_units>20 THEN 1 ELSE 0 END)'),('จำนวนคำสั่งซื้อที่มีสินค้าอย่างน้อย 5 ชนิด','count of invoices with at least 5 distinct products','SUM(CASE WHEN distinct_products>=5 THEN 1 ELSE 0 END)'),('สัดส่วนคำสั่งซื้อที่มีสินค้าชนิดเดียว ไม่ใช่เปอร์เซ็นต์','fraction of single-product invoices, not a percentage','SUM(CASE WHEN distinct_products=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0)')]:
    add('basket',f'เดือนมกราคม 2011 คำนวณ{th}',f'For January 2011 calculate the {en}.',f'SELECT {expr} AS value FROM orders WHERE {P}',['schema.orders','syntax.basket'])

for country in ('United Kingdom','France','Germany','Spain','Netherlands'):
    where=f"{P} AND country='{country}' AND customer_id IS NOT NULL"
    add('repeat_rate',f'สัดส่วนลูกค้าที่มีรหัสและซื้อซ้ำอย่างน้อย 2 ใบในเดือนมกราคม 2011 ประเทศ {country} เท่าไร แสดงเป็น fraction',f'In {country} in January 2011, calculate the repeat customer fraction: identified customers with at least two invoices divided by all identified purchasing customers.',f'WITH f AS (SELECT customer_id,COUNT(*) AS n FROM orders WHERE {where} GROUP BY customer_id) SELECT SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0) AS value FROM f',['metric.repeat_rate','syntax.aggregation'])

for th,en,expr in [('สัดส่วนคำสั่งซื้อที่ไม่มีรหัสลูกค้า','anonymous invoice fraction','SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0)'),('สัดส่วนยอดขายจากคำสั่งซื้อที่ไม่มีรหัสลูกค้า','anonymous invoice sales share','SUM(CASE WHEN customer_id IS NULL THEN order_amount ELSE 0 END)/NULLIF(SUM(order_amount),0)'),('ยอดขายต่อผู้ซื้อที่มีรหัสหนึ่งคน โดยตัดคำสั่งซื้อไม่มีรหัสออกทั้งเศษและส่วน','sales per identified purchasing customer excluding anonymous invoices from numerator and denominator','SUM(CASE WHEN customer_id IS NOT NULL THEN order_amount ELSE 0 END)/NULLIF(COUNT(DISTINCT customer_id),0)'),('จำนวนคำสั่งซื้อเฉลี่ยต่อผู้ซื้อที่มีรหัส โดยตัดคำสั่งซื้อไม่มีรหัสออก','invoice frequency per identified purchasing customer excluding anonymous invoices','COUNT(customer_id)/NULLIF(COUNT(DISTINCT customer_id),0)'),('สัดส่วนคำสั่งซื้อที่ยอดมากกว่า 100 GBP','fraction of invoices above 100 GBP','SUM(CASE WHEN order_amount>100 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0)')]:
    add('ratios',f'เดือนมกราคม 2011 คำนวณ{th} แสดงเป็นสัดส่วนไม่คูณ 100',f'For January 2011 calculate {en}. Return a fraction, not multiplied by 100.',f'SELECT {expr} AS value FROM orders WHERE {P}',['schema.orders','syntax.ratios'])

for th,en,expression in [
 ('ยอดขายสะสมตั้งแต่ต้นปี','year-to-date cumulative sales','SUM(sales) OVER (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)'),
 ('ค่าเฉลี่ยเคลื่อนที่ยอดขาย 3 เดือนที่มีข้อมูล รวมเดือนปัจจุบัน','3-observed-month trailing moving average including current month','AVG(sales) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)'),
 ('ยอดขายเดือนก่อนหน้า โดยเดือนแรกเป็น NULL','previous observed month sales, NULL for first month','LAG(sales) OVER (ORDER BY month)'),
 ('การเปลี่ยนแปลงยอดขายจากเดือนก่อนหน้าเป็นจำนวนเงิน โดยเดือนแรกเป็น NULL','sales change from previous observed month in GBP, NULL for first month','sales-LAG(sales) OVER (ORDER BY month)'),
 ('อัตราเติบโตยอดขายเทียบเดือนก่อนหน้าเป็น fraction เดือนแรกหรือฐานศูนย์เป็น NULL','month-over-month sales growth as a fraction, NULL for first month or zero base','(sales-LAG(sales) OVER (ORDER BY month))/NULLIF(LAG(sales) OVER (ORDER BY month),0)')]:
    add('windows',f'แสดงรายเดือนปี 2011 พร้อม{th} แสดงเฉพาะเดือนและค่าที่ขอ เรียงเดือน',f'For each month of 2011 show {en}. Output only month and the requested value, ordered by month.',f'WITH m AS ({monthly}) SELECT month,{expression} AS value FROM m ORDER BY month',['schema.orders','syntax.windows'],ordered=True)

for th,en,unit,where in [('รายวันเดือนมกราคม','daily during January','DAY',P),('รายชั่วโมงของวันที่ 5 มกราคม','hourly during January 5','HOUR',"order_ts>=TIMESTAMP '2011-01-05' AND order_ts<TIMESTAMP '2011-01-06'"),('รายไตรมาส','quarterly','QUARTER',Y),('รายปีตลอดข้อมูลทั้งหมด','yearly over all available data','YEAR','1=1'),('รายสัปดาห์เดือนมกราคม','weekly during January','WEEK',P)]:
    grouping=f"DATE_TRUNC('{unit}',order_ts)"
    thq='แสดงจำนวนคำสั่งซื้อรายปีตลอดข้อมูลทั้งหมดทุกปี เรียงเวลา' if unit=='YEAR' else f'ปี 2011 แสดงจำนวนคำสั่งซื้อ{th} เรียงเวลา'
    enq='Show invoice counts yearly over all available data, ordered by time.' if unit=='YEAR' else f'Show invoice counts {en} 2011, ordered by time.'
    add('time_buckets',thq,enq,f'SELECT {grouping} AS bucket,COUNT(*) AS value FROM orders WHERE {where} GROUP BY {grouping} ORDER BY bucket',['metric.orders','syntax.time'],ordered=True)

for th,en,expr in [('วันซื้อที่พบครั้งแรกต่ำสุด','earliest observed first purchase date','MIN(first_purchase_date)'),('วันซื้อครั้งล่าสุดสูงสุด','latest observed purchase date','MAX(last_purchase_date)'),('recency สูงสุด','maximum recency days','MAX(recency_days)'),('จำนวนลูกค้าที่มีคำสั่งซื้อ 180 วันอย่างน้อย 10 ใบ','number of customers with at least 10 invoices in 180 days','SUM(CASE WHEN orders_180d>=10 THEN 1 ELSE 0 END)'),('จำนวนลูกค้าที่เป็น Inactive และไม่ใช่ high-value','number of Inactive customers who are not high-value',"SUM(CASE WHEN rfm_segment='Inactive' AND is_high_value=false THEN 1 ELSE 0 END)")]:
    add('snapshot_activity',f'ณ snapshot 2011-12-01 หา{th}',f'At snapshot 2011-12-01 find the {en}.',f'SELECT {expr} AS value FROM customer_summary WHERE {S}',['schema.customer_summary','segment.inactive'] if 'Inactive' in en else ['schema.customer_summary'])

# Five additional compositions, with independently executed SQL oracles.
add('monthly_max','เดือนไหนออเดอร์เยอะสุด','Which month had the most orders?',f"WITH m AS (SELECT {M} AS month,COUNT(*) AS n FROM orders GROUP BY {M}) SELECT month,n FROM m WHERE n=(SELECT MAX(n) FROM m) ORDER BY month",['metric.orders','syntax.monthly_extrema'],ordered=True)
add('country_share','เดือนมกราคม 2011 แสดงแต่ละประเทศกับสัดส่วนยอดขายต่อยอดรวม เรียงประเทศ','For January 2011 show each country and its fraction of total sales, ordered by country.',f'WITH c AS (SELECT country,SUM(order_amount) AS sales FROM orders WHERE {P} GROUP BY country) SELECT country,sales/NULLIF(SUM(sales) OVER (),0) AS value FROM c ORDER BY country',['schema.orders','syntax.ratios'],ordered=True)
add('having','เดือนมกราคม 2011 มีลูกค้าที่มีรหัสอย่างน้อย 3 คำสั่งซื้อกี่คน','How many identified customers placed at least three invoices in January 2011?',f'WITH c AS (SELECT customer_id FROM orders WHERE {P} AND customer_id IS NOT NULL GROUP BY customer_id HAVING COUNT(*)>=3) SELECT COUNT(*) AS value FROM c',['schema.orders','syntax.having'])
add('line_quality','เดือนมกราคม 2011 แสดงจำนวนแถวสินค้าแยก transaction_type เรียงประเภท','For January 2011 show product-line counts by transaction_type, ordered by type.',f'SELECT transaction_type,COUNT(*) AS value FROM sales_lines WHERE {L} GROUP BY transaction_type ORDER BY transaction_type',['schema.sales_lines','syntax.transactions'],ordered=True)
add('high_value_fraction','ณ snapshot 2011-12-01 ลูกค้า high-value เป็นสัดส่วนเท่าไรของลูกค้าทั้งหมด','At snapshot 2011-12-01 what fraction of customers are high-value?',f'SELECT SUM(CASE WHEN is_high_value THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0) AS value FROM customer_summary WHERE {S}',['metric.high_value','syntax.ratios'])

FORMULAS=[
 ('aov','AOV','AOV'),('repeat_rate','สัดส่วนลูกค้าซื้อซ้ำ','repeat customer fraction'),
 ('anonymous_share','สัดส่วนคำสั่งซื้อไม่มีรหัสลูกค้า','anonymous invoice fraction'),
 ('units_per_order','จำนวนหน่วยเฉลี่ยต่อคำสั่งซื้อ','units per order'),
 ('product_revenue','ยอดขายสินค้า','product sale revenue'),
 ('mom_growth','อัตราเติบโตยอดขายรายเดือน','month-over-month sales growth'),
 ('country_share','สัดส่วนยอดขายแต่ละประเทศ','country sales share'),
 ('cumulative_sales','ยอดขายสะสม','cumulative sales'),
 ('moving_average','ค่าเฉลี่ยเคลื่อนที่ 3 เดือน','three-month moving average'),
 ('median_order','มัธยฐานมูลค่าคำสั่งซื้อโดยประมาณ','approximate median order value'),
 ('high_value_share','สัดส่วนลูกค้ามูลค่าสูง','high-value customer fraction'),
 ('cancellation_share','สัดส่วนแถวรายการยกเลิก','cancellation line fraction')]
for key,th,en in FORMULAS:
    add('formula',f'ขอสูตร{th} ไม่ต้องรัน SQL',f'Explain the formula for {en}; do not execute SQL.',ids=['formula.'+key],formula=key)

for th,en,policy in [
 ('ยอดขายรวมเท่าไร','What is total revenue?','period'),
 ('ลูกค้าดีที่สุดคือใคร','Who are our best customers?','period'),
 ('แสดงกลุ่มลูกค้า RFM','Show RFM segments.','snapshot'),
 ('นับลูกค้ามูลค่าสูง','Count high-value customers.','snapshot'),
 ('แสดงกลุ่ม RFM ณ snapshot 2011-11-30','Show RFM segments at snapshot 2011-11-30.','snapshot'),
 ('กำไรเดือนมกราคม 2011 เท่าไร','What was profit in January 2011?','availability'),
 ('ยอดขายเดือนมกราคม 2024 เท่าไร','What were sales in January 2024?','availability'),
 ('วัดผลแคมเปญในปี 2011','Measure campaign uplift in 2011.','availability')]:
    add('clarification',th,en,ids=['policy.'+policy],policy='policy.'+policy)

assert len(PAIRS)==100,len(PAIRS)
cases=[]
for p in PAIRS:
    for language in ('th','en'):
        cases.append({k:v for k,v in p.items() if k not in ('th','en')}|dict(id=p['pair_id']+'-'+language,language=language,question=p[language]))
assert len({c['question'] for c in cases})==200
(ROOT/'evaluation/bilingual_200.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# ชุดคำถามพัฒนา: ไทย 100 / อังกฤษ 100','',
       'คำถามเรียบเรียงใหม่จาก schema ของ Online Retail II และรูปแบบวิเคราะห์ในเอกสาร Spark ไม่ใช่คำถามคัดลอก 200 ข้อจากเว็บไซต์ ชุดนี้เปิดเผยเพื่อพัฒนาระบบ จึงไม่ใช่ independent holdout.',
       '', '80 คู่รัน SQL · 12 คู่ขอสูตรโดยไม่รัน · 8 คู่ต้องถามกลับ/แจ้งข้อมูลไม่รองรับ', '',
       '| # | กลุ่ม | ภาษาไทย | English |','|---|---|---|---|']
lines += [f"| {i} | {p['family']} | {p['th']} | {p['en']} |" for i,p in enumerate(PAIRS,1)]
lines += ['', 'แหล่งอ้างอิงการออกแบบ:',
          '- [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)',
          '- [Spark built-in functions](https://spark.apache.org/docs/4.1.3/sql-ref-functions-builtin.html)',
          '- [Spark window functions](https://spark.apache.org/docs/4.1.3/sql-ref-syntax-qry-select-window.html)',
          '', 'Gold SQL อยู่เฉพาะ evaluation/ ไม่ถูกโหลดเข้า Agent หรือ RAG; ตัวอย่าง syntax ใน knowledge/ เป็นรูปแบบทั่วไป ไม่ใช่คลังคำตอบของแต่ละข้อ.']
(ROOT/'docs/QUESTION_BANK.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Authored 100 Thai + 100 English questions across',len({p['family'] for p in PAIRS}),'families')
