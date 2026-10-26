"""Author public evaluation oracles, never imported by the production agent."""
import calendar
import argparse
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--followup',action='store_true')
followup=parser.parse_args().followup
old=[c for p in (root/'evaluation').glob('*.json') for c in
     (json.loads(p.read_text(encoding='utf-8')) if p.name.startswith(('rag_holdout','test','dev.')) else [])]
used={' '.join(c.get('gold_sql','').lower().split()) for c in old}
cases=[]
countries=['Norway','Finland','Greece','Poland'] if followup else ['Belgium','Spain','Switzerland','Portugal']
for family in range(12):
    for i,country in enumerate(countries):
        year=(2011 if i<2 else 2010) if followup else (2010 if i<2 else 2011)
        month=(family*3+i*2+(4 if followup else 0))%11+1
        start=f'{year}-{month:02}-01'; end=f'{year+(month==12)}-{month%12+1:02}-01'
        period=f'{calendar.month_name[month]} {year}'
        where=f"country='{country}' AND order_ts>=TIMESTAMP '{start}' AND order_ts<TIMESTAMP '{end}'"
        linewhere=where.replace('order_ts','invoice_ts')
        snapshot="as_of_date=DATE '2011-12-01'"
        choices=[
          (f'Count completed invoices for {country} in {period}.',f'SELECT count(*) FROM orders WHERE {where}',['metric.orders','schema.orders'],False),
          (f'Return total completed sales in {country} during {period}.',f'SELECT sum(order_amount) FROM orders WHERE {where}',['metric.sales','schema.orders'],False),
          (f'Calculate average order value including anonymous invoices for {country} in {period}.',f'SELECT avg(order_amount) FROM orders WHERE {where}',['metric.aov','schema.orders'],False),
          (f'Count distinct identified purchasing customers in {country} during {period}.',f'SELECT count(distinct customer_id) FROM orders WHERE customer_id IS NOT NULL AND {where}',['metric.customers','schema.orders'],False),
          (f'For {country} in {period}, return the repeat customer fraction among all identified purchasing customers.',f'WITH f AS (SELECT customer_id,count(*) n FROM orders WHERE customer_id IS NOT NULL AND {where} GROUP BY customer_id) SELECT sum(CASE WHEN n>=2 THEN 1 ELSE 0 END)/nullif(count(*),0) FROM f',['metric.repeat_rate','schema.orders'],False),
          (f'Rank the top {i+2} identified customers by completed sales in {country} in {period}. Output customer ID and sales, descending sales then ascending customer ID.',f'SELECT customer_id,sum(order_amount) sales FROM orders WHERE customer_id IS NOT NULL AND {where} GROUP BY customer_id ORDER BY sales DESC,customer_id ASC LIMIT {i+2}',['metric.sales','schema.orders','syntax.ranking'],True),
          (f'In {period} return the top {i+2} countries by completed invoice count. Output country and count, descending count then ascending country.',f"SELECT country,count(*) n FROM orders WHERE order_ts>=TIMESTAMP '{start}' AND order_ts<TIMESTAMP '{end}' GROUP BY country ORDER BY n DESC,country ASC LIMIT {i+2}",['metric.orders','schema.orders','syntax.ranking'],True),
          (f'Count cancellation product lines in {country} in {period}.',f"SELECT count(*) FROM sales_lines WHERE transaction_type='cancellation' AND {linewhere}",['schema.sales_lines'],False),
          (f'Count original return product lines in {country} in {period}.',f"SELECT count(*) FROM sales_lines WHERE transaction_type='return' AND {linewhere}",['schema.sales_lines'],False),
          (f'In {country} in {period}, rank the top {i+2} product IDs by total sale quantity. Use only sale lines. Output product ID and units, descending units then ascending product ID.',f"SELECT product_id,sum(quantity) units FROM sales_lines WHERE transaction_type='sale' AND {linewhere} GROUP BY product_id ORDER BY units DESC,product_id ASC LIMIT {i+2}",['schema.sales_lines','syntax.ranking'],True),
          (f'At snapshot 2011-12-01 count Inactive customers with at least {i+8} orders in the 180-day window.',f"SELECT count(*) FROM customer_summary WHERE {snapshot} AND rfm_segment='Inactive' AND orders_180d>={i+8}",['segment.inactive','schema.customer_summary'],False),
          (f'At snapshot 2011-12-01 count high-value customers with at least {i+9} orders in the 180-day window.',f'SELECT count(*) FROM customer_summary WHERE {snapshot} AND is_high_value=true AND orders_180d>={i+9}',['metric.high_value','schema.customer_summary'],False)
        ]
        q,sql,ids,ordered=choices[family]
        if followup and family in (5,6,9):
            q=q.replace(f'top {i+2}',f'top {i+7}')
            sql=sql.replace(f'LIMIT {i+2}',f'LIMIT {i+7}')
        if followup and family in (10,11):
            threshold=i+(8 if family==10 else 9)
            q=q.replace(f'at least {threshold} orders',f'at least {threshold+10} orders')
            sql=sql.replace(f'>={threshold}',f'>={threshold+10}')
        if ' '.join(sql.lower().split()) in used:raise ValueError('Previously exposed exact gold SQL')
        used.add(' '.join(sql.lower().split()))
        cases.append(dict(id=f'accept{len(cases)+1:02}',question=q,gold_sql=sql,relevant_ids=ids,ordered=ordered,family=family))
for q,policy in [('Show total revenue','period'),('Who are our best customers?','period'),
    ('Show RFM segments','snapshot'),('Count high-value customers','snapshot'),
    ('Show RFM distribution at snapshot 2011-11-30','snapshot'),
    ('Calculate profit for Belgium in June 2010','availability'),
    ('What were sales during February 2023?','availability'),
    ('Measure campaign uplift in 2011','availability')]:
    cases.append(dict(id=f'accept{len(cases)+1:02}',question=q,clarification_policy='policy.'+policy,relevant_ids=['policy.'+policy],family='clarification'))
    if followup:
        cases[-1]['question']='Please answer this request or explain what is missing: '+q.replace('2023','2024').replace('2011-11-30','2011-11-29')
for i,country in enumerate(countries):
    month=i+(7 if followup else 3)
    year=2011 if followup else 2010
    q=f'ในเดือน {calendar.month_name[month]} {year} ประเทศ {country} มี completed invoice กี่ใบ'
    sql=f"SELECT count(*) FROM orders WHERE country='{country}' AND order_ts>=TIMESTAMP '{year}-{month:02}-01' AND order_ts<TIMESTAMP '{year}-{month+1:02}-01'"
    cases.append(dict(id=f'accept{len(cases)+1:02}',question=q,gold_sql=sql,relevant_ids=['metric.orders','schema.orders'],family='Thai'))
for i,country in enumerate(() if followup else ('Italy','Austria','Denmark')):
    month=i+8
    cases[i].update(question=f'Count completed invoices for {country} during {calendar.month_name[month]} 2010.',
        gold_sql=f"SELECT count(*) FROM orders WHERE country='{country}' AND order_ts>=TIMESTAMP '2010-{month:02}-01' AND order_ts<TIMESTAMP '2010-{month+1:02}-01'")
exposed=root/'evaluation/acceptance_pilot_exposed.json'
if exposed.exists():
    previous=json.loads(exposed.read_text(encoding='utf-8'))
    assert not {c.get('gold_sql') for c in previous}&{c.get('gold_sql') for c in cases if c.get('gold_sql')}
assert len(cases)==60 and len({c['question'] for c in cases})==60
if followup:
    prior=json.loads((root/'evaluation/acceptance_exposed.json').read_text(encoding='utf-8'))
    assert not {c['question'] for c in cases}&{c['question'] for c in prior}
    collisions={c.get('gold_sql') for c in cases if c.get('gold_sql')}&{c.get('gold_sql') for c in prior}
    assert not collisions,collisions
    for c in cases:c['id']=c['id'].replace('accept','final')
(root/'evaluation/acceptance.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False),encoding='utf-8')
print('Authored 60 new parameterized supported-family questions, including 8 clarification and 4 bilingual cases')
