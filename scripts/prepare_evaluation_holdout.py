"""Build a project-authored bilingual holdout before running the Agent."""
import argparse
import json
from pathlib import Path


CASES = [
    ('country_month', '2010-03', 'เดือนมีนาคม 2010 นับใบสั่งซื้อของ France แยกตามวัน คืนวันที่และจำนวน เรียงวันที่',
     'In March 2010, count France invoices by day. Return day and count sorted by day.',
     "SELECT DATE_TRUNC('DAY', order_ts), COUNT(*) FROM orders WHERE {period} AND country='France' GROUP BY 1 ORDER BY 1",
     'metric.orders', True),
    ('anonymous_sales', '2011-02', 'ยอดขายจากใบสั่งซื้อที่ไม่มีรหัสลูกค้าในกุมภาพันธ์ 2011 รวมเท่าไร',
     'What were total sales from invoices without a customer ID in February 2011?',
     'SELECT SUM(order_amount) FROM orders WHERE {period} AND customer_id IS NULL',
     'metric.sales', False),
    ('customer_country', '2011-06', 'มิถุนายน 2011 ประเทศ Germany มีลูกค้าที่มีรหัสและซื้อสินค้าไม่ซ้ำกี่คน',
     'How many distinct identified buyers purchased in Germany in June 2011?',
     "SELECT COUNT(DISTINCT customer_id) FROM orders WHERE {period} AND country='Germany'",
     'schema.orders', False),
    ('country_aov', '2010-10', 'ตุลาคม 2010 คำนวณมูลค่าเฉลี่ยต่อใบสั่งซื้อของ France โดยรวมใบที่ไม่มีรหัสลูกค้า',
     'What was average invoice value for France in October 2010, including anonymous invoices?',
     "SELECT SUM(order_amount)/NULLIF(COUNT(*),0) FROM orders WHERE {period} AND country='France'",
     'metric.aov', False),
    ('order_threshold', '2011-07', 'กรกฎาคม 2011 มีใบสั่งซื้อที่มูลค่ามากกว่า 500 GBP กี่ใบ',
     'How many invoices exceeded 500 GBP in July 2011?',
     'SELECT COUNT(*) FROM orders WHERE {period} AND order_amount>500',
     'metric.orders', False),
    ('rank_by_count', '2010-11', 'พฤศจิกายน 2010 ขอ 4 ประเทศแรกตามจำนวนใบสั่งซื้อ แสดงประเทศกับจำนวน เรียงจำนวนลงแล้วประเทศขึ้น',
     'In November 2010, return the top four countries by invoice count. Return country and count, sorted by count descending then country ascending.',
     'SELECT country, COUNT(*) AS n FROM orders WHERE {period} GROUP BY country ORDER BY n DESC,country ASC LIMIT 4',
     'metric.orders', True),
    ('buyer_threshold', '2011-08', 'สิงหาคม 2011 มีลูกค้าที่มีรหัสและสั่งซื้ออย่างน้อย 4 ใบกี่คน',
     'In August 2011 how many identified customers placed at least four invoices?',
     'WITH buyers AS (SELECT customer_id FROM orders WHERE {period} AND customer_id IS NOT NULL GROUP BY customer_id HAVING COUNT(*)>=4) SELECT COUNT(*) FROM buyers',
     'schema.orders', False),
    ('daily_sales', '2010-07', 'กรกฎาคม 2010 ขอวันยอดขายสูงสุดของ United Kingdom คืนวันและยอด ถ้าเท่ากันเลือกวันก่อน',
     'For July 2010, return the highest-sales day in the United Kingdom and its sales. Break ties by earliest day.',
     "SELECT DATE_TRUNC('DAY',order_ts) AS day, SUM(order_amount) AS sales FROM orders WHERE {period} AND country='United Kingdom' GROUP BY 1 ORDER BY sales DESC,day ASC LIMIT 1",
     'metric.sales', True),
]


FOLLOWUP = [
    ('daily_country', '2010-09', 'กันยายน 2010 นับใบสั่งซื้อของ Germany แยกตามวัน คืนวันที่และจำนวน เรียงวันที่',
     'For September 2010, show Germany invoices by day. Return day and count, earliest first.',
     "SELECT DATE_TRUNC('DAY',order_ts),COUNT(*) FROM orders WHERE {period} AND country='Germany' GROUP BY 1 ORDER BY 1",
     'metric.orders', True),
    ('anonymous_revenue_country', '2011-03', 'มีนาคม 2011 ยอดขายจากใบสั่งซื้อที่ไม่มีรหัสลูกค้าเฉพาะ United Kingdom รวมเท่าไร',
     'What was total revenue from anonymous invoices in the United Kingdom in March 2011?',
     "SELECT SUM(order_amount) FROM orders WHERE {period} AND country='United Kingdom' AND customer_id IS NULL",
     'metric.sales', False),
    ('rank_countries_sales', '2011-05', 'พฤษภาคม 2011 ขอ 3 ประเทศที่ยอดขายสูงสุด แสดงประเทศกับยอด เรียงยอดลงแล้วชื่อประเทศขึ้น',
     'For May 2011, list the top three countries by sales. Show country and sales; sort by sales descending then country ascending.',
     'SELECT country,SUM(order_amount) AS sales FROM orders WHERE {period} GROUP BY country ORDER BY sales DESC,country ASC LIMIT 3',
     'metric.sales', True),
    ('daily_sales_peak', '2010-06', 'มิถุนายน 2010 ขอวันยอดขายสูงสุดของ United Kingdom คืนวันและยอด ถ้าเท่ากันเลือกวันก่อน',
     'In June 2010 return the highest-sales day in the United Kingdom and its sales. Break ties by earliest day.',
     "SELECT DATE_TRUNC('DAY',order_ts) AS day,SUM(order_amount) AS sales FROM orders WHERE {period} AND country='United Kingdom' GROUP BY 1 ORDER BY sales DESC,day ASC LIMIT 1",
     'metric.sales', True),
    ('country_units', '2011-09', 'กันยายน 2011 นับจำนวนหน่วยสินค้าที่ขายใน France ทั้งหมด',
     'In September 2011, what were the total units sold in France?',
     "SELECT SUM(total_units) FROM orders WHERE {period} AND country='France'",
     'schema.orders', False),
    ('identified_invoices', '2010-08', 'สิงหาคม 2010 นับใบสั่งซื้อใน Germany เฉพาะใบที่มีรหัสลูกค้า',
     'Count invoices in Germany in August 2010 that have a customer ID.',
     "SELECT COUNT(*) FROM orders WHERE {period} AND country='Germany' AND customer_id IS NOT NULL",
     'metric.orders', False),
]


def build(definitions=CASES, prefix='held'):
    cases = []
    for index, (family, month, thai, english, sql, evidence, ordered) in enumerate(definitions, 1):
        year, number = map(int, month.split('-'))
        end = f'{year + (number == 12):04d}-{number % 12 + 1:02d}-01'
        period = f"order_ts >= TIMESTAMP '{month}-01' AND order_ts < TIMESTAMP '{end}'"
        for language, question in [('th', thai), ('en', english)]:
            pair = f'{prefix}{index:02}'
            cases.append(dict(id=f'{pair}-{language}', pair_id=pair, language=language,
                              family=family, question=question, gold_sql=sql.format(period=period),
                              relevant_ids=[evidence, 'schema.orders'] if evidence != 'schema.orders'
                              else [evidence], ordered=ordered))
    return cases


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--followup', action='store_true')
    args = parser.parse_args()
    with args.output.open('x', encoding='utf-8') as output:
        cases = build(FOLLOWUP, 'fresh') if args.followup else build()
        json.dump(cases, output, ensure_ascii=False, indent=2)
