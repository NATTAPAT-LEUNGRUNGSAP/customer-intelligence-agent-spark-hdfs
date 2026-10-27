import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from agent import answer
from retrieval import retrieve_context
from semantic_contracts import requested_period,validate_business_sql
from sql_guard import validate_sql
from formula_intent import requested_formula
from result_contracts import validate_result
from metric_contracts import validate_metric_expression

ROOT=Path(__file__).resolve().parents[1]


class BilingualSupportTests(unittest.TestCase):
    def test_invoice_fraction_preserves_population_and_counts_not_money(self):
        q='Calculate anonymous invoice fraction'
        with self.assertRaises(ValueError):validate_metric_expression(q,'SELECT COUNT(*)/COUNT(*) FROM orders WHERE customer_id IS NULL')
        with self.assertRaises(ValueError):validate_metric_expression(q,'SELECT SUM(CASE WHEN customer_id IS NULL THEN order_amount ELSE 0 END)/SUM(order_amount) FROM orders')
        validate_metric_expression(q,'SELECT SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END)/COUNT(*) FROM orders')

    def test_invoice_fraction_condition_is_not_inverted(self):
        with self.assertRaises(ValueError):validate_metric_expression('Anonymous invoice fraction','SELECT SUM(CASE WHEN customer_id IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*) FROM orders')
        with self.assertRaises(ValueError):validate_metric_expression('Fraction of invoices above 100 GBP','SELECT SUM(CASE WHEN total_units>100 THEN 1 ELSE 0 END)/COUNT(*) FROM orders')

    def test_product_buyers_are_not_distinct_product_ids(self):
        q='Rank product IDs by distinct identified purchasing customers'
        with self.assertRaises(ValueError):validate_metric_expression(q,'SELECT product_id,COUNT(DISTINCT product_id) FROM sales_lines GROUP BY product_id')
        validate_metric_expression(q,'SELECT product_id,COUNT(DISTINCT customer_id) FROM sales_lines GROUP BY product_id')
    def test_named_day_is_not_expanded_to_a_whole_month(self):
        for q in ('จำนวนคำสั่งซื้อรายชั่วโมงของวันที่ 5 มกราคม 2011','Invoice counts hourly during January 5 2011'):
            self.assertEqual(requested_period(q),['2011-01-05','2011-01-06'])
        with self.assertRaises(ValueError):validate_business_sql('Invoice counts hourly during January 5 2011',"SELECT DATE_TRUNC('HOUR',order_ts),COUNT(*) FROM orders WHERE DATE_TRUNC('MONTH',order_ts)=TIMESTAMP '2011-01-05' GROUP BY 1")

    def test_thai_country_share_is_a_breakdown_not_a_scalar(self):
        from metric_contracts import expected_columns,has_breakdown
        q='แสดงแต่ละประเทศกับสัดส่วนยอดขายต่อยอดรวม เรียงประเทศ'
        self.assertTrue(has_breakdown(q))
        self.assertEqual(expected_columns(q),2)
        validate_metric_expression(q,'WITH c AS (SELECT country,SUM(order_amount) AS sales FROM orders GROUP BY country) SELECT country,sales/NULLIF(SUM(sales) OVER (),0) FROM c ORDER BY country')
    def test_snapshot_is_not_replaced_with_lifetime_history(self):
        with self.assertRaises(ValueError):validate_business_sql('At snapshot 2011-12-01 count all customers','SELECT COUNT(DISTINCT customer_id) FROM orders')
        validate_business_sql('At snapshot 2011-12-01 count all customers',"SELECT COUNT(*) FROM customer_summary WHERE as_of_date=DATE '2011-12-01'")

    def test_money_share_is_not_invoice_share_and_fraction_is_not_its_numerator(self):
        with self.assertRaises(ValueError):validate_metric_expression('Calculate anonymous invoice sales share','SELECT SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END)/COUNT(*) FROM orders')
        with self.assertRaises(ValueError):validate_metric_expression('Calculate single-product invoice fraction','SELECT SUM(CASE WHEN distinct_products=1 THEN 1 ELSE 0 END) FROM orders')

    def test_hour_and_quarter_buckets_must_not_be_substituted(self):
        with self.assertRaises(ValueError):validate_metric_expression('Show invoice counts quarterly in 2011',"SELECT DATE_TRUNC('MONTH',order_ts),COUNT(*) FROM orders GROUP BY 1")
        validate_metric_expression('Show invoice counts quarterly in 2011',"SELECT DATE_TRUNC('QUARTER',order_ts),COUNT(*) FROM orders GROUP BY 1")

    def test_snapshot_frequency_mean_is_not_aov(self):
        with self.assertRaises(ValueError):validate_metric_expression('At snapshot 2011-12-01 show mean 180-day order count by rfm_segment','SELECT rfm_segment,AVG(aov_180d) FROM customer_summary GROUP BY rfm_segment')
    def test_month_and_to_date_parser_helpers_remain_pure_read_only(self):
        validate_sql('SELECT MONTH(order_ts),TO_DATE(order_ts) FROM orders')
        with self.assertRaises(ValueError):validate_sql("SELECT read_file('/etc/passwd') FROM orders")
    def test_divided_by_does_not_mean_a_grouped_breakdown(self):
        from metric_contracts import has_breakdown,expected_columns
        q='Calculate repeat customer fraction, repeat buyers divided by all purchasing customers'
        self.assertFalse(has_breakdown(q))
        self.assertEqual(expected_columns(q),1)
        with self.assertRaises(ValueError):validate_metric_expression(q,'SELECT COUNT(*) AS n,COUNT(*)/COUNT(*) AS fraction FROM orders')

    def test_units_per_invoice_is_not_monetary_aov(self):
        validate_metric_expression('จำนวนหน่วยเฉลี่ยต่อคำสั่งซื้อเดือนมกราคม 2011','SELECT AVG(total_units) FROM orders')
        validate_metric_expression('จำนวนสินค้าต่างชนิดเฉลี่ยต่อคำสั่งซื้อเดือนมกราคม 2011','SELECT AVG(distinct_products) FROM orders')

    def test_country_breakdown_rejects_an_unrequested_month_column(self):
        with self.assertRaises(ValueError):validate_metric_expression('Show units by country for January 2011','SELECT order_ts,country,SUM(total_units) FROM orders GROUP BY order_ts,country')

    def test_cumulative_sales_and_null_previous_month_are_not_substituted(self):
        with self.assertRaises(ValueError):validate_metric_expression('Show cumulative sales by month','SELECT order_ts,SUM(order_amount) FROM orders GROUP BY order_ts')
        with self.assertRaises(ValueError):validate_metric_expression('Sales change from previous month, first month NULL','SELECT order_ts,order_amount-COALESCE(LAG(order_amount) OVER (ORDER BY order_ts),0) FROM orders')

    def test_threshold_share_must_keep_denominator_population(self):
        with self.assertRaises(ValueError):validate_metric_expression('Fraction of invoices above 100 GBP','SELECT COUNT(*)/COUNT(*) FROM orders WHERE order_amount>100')
        validate_metric_expression('Fraction of invoices above 100 GBP','SELECT SUM(CASE WHEN order_amount>100 THEN 1 ELSE 0 END)/COUNT(*) FROM orders')
    def test_count_star_is_an_aggregate_not_a_projection_wildcard(self):
        validate_metric_expression('Output customer ID and value, rank by invoice count','SELECT customer_id,COUNT(*) AS value FROM orders GROUP BY customer_id ORDER BY value DESC,customer_id LIMIT 5')
        validate_metric_expression('Calculate anonymous invoice fraction','SELECT SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END)/COUNT(*) AS value FROM orders')
        with self.assertRaises(ValueError):validate_metric_expression('Output customer ID and value','SELECT * FROM orders')
    def test_units_are_not_money_and_weighted_price_is_not_revenue(self):
        with self.assertRaises(ValueError):validate_metric_expression('จำนวนสินค้าที่ขายเดือนมกราคม 2011','SELECT SUM(order_amount) FROM orders')
        validate_metric_expression('จำนวนสินค้าที่ขายเดือนมกราคม 2011','SELECT SUM(total_units) FROM orders')
        with self.assertRaises(ValueError):validate_metric_expression('quantity-weighted sale unit price','SELECT SUM(line_amount) FROM sales_lines')
        validate_metric_expression('quantity-weighted sale unit price','SELECT SUM(line_amount)/NULLIF(SUM(quantity),0) FROM sales_lines')

    def test_anonymous_thai_is_not_identified_only(self):
        from result_contracts import validate_semantics
        validate_semantics('สัดส่วนคำสั่งซื้อที่ไม่มีรหัสลูกค้า','SELECT SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END)/COUNT(*) FROM orders')

    def test_transaction_types_and_all_type_breakdown(self):
        for kind in ('return','adjustment','invalid'):
            validate_business_sql('Count product lines classified as '+kind+" in January 2011",f"SELECT COUNT(*) FROM sales_lines WHERE transaction_type='{kind}' AND invoice_ts>=TIMESTAMP '2011-01-01' AND invoice_ts<TIMESTAMP '2011-02-01'")
        validate_business_sql('Show product-line counts by transaction_type in January 2011',"SELECT transaction_type,COUNT(*) FROM sales_lines WHERE invoice_ts>=TIMESTAMP '2011-01-01' AND invoice_ts<TIMESTAMP '2011-02-01' GROUP BY transaction_type")
        with self.assertRaises(ValueError):validate_business_sql('Show product-line counts by transaction_type in January 2011',"SELECT transaction_type,COUNT(*) FROM sales_lines WHERE transaction_type='sale' AND invoice_ts>=TIMESTAMP '2011-01-01' AND invoice_ts<TIMESTAMP '2011-02-01' GROUP BY transaction_type")

    def test_country_share_keeps_fraction_shape_and_requested_order(self):
        question='Show each country and its fraction of total sales, ordered by country'
        with self.assertRaises(ValueError):validate_metric_expression(question,'SELECT country,sales,sales/total FROM orders ORDER BY country')
        with self.assertRaises(ValueError):validate_metric_expression(question,'SELECT country,sales/total*100 FROM orders ORDER BY country')
        validate_metric_expression(question,'SELECT country,order_amount/total_units FROM orders ORDER BY country')
        validate_result(question,{'columns':['country','share'],'rows':[['A',0.2],['B',0.8]],'truncated':False},'SELECT country,order_amount/total_units FROM orders ORDER BY country')

    def test_scalar_fraction_must_not_return_multiple_customer_rows(self):
        with self.assertRaises(ValueError):validate_result('Calculate repeat customer fraction',{'columns':['fraction'],'rows':[[0],[1]],'truncated':False},'SELECT order_amount/total_units AS fraction FROM orders')

    def test_month_scope_accepts_alias_and_ordinal_grouping(self):
        from question_scope import validate_month_comparison
        for grouping in ('month','1'):
            validate_month_comparison("WITH m AS (SELECT DATE_TRUNC('MONTH',order_ts) AS month,COUNT(*) AS n FROM orders GROUP BY "+grouping+") SELECT month,n FROM m WHERE n=(SELECT MAX(n) FROM m) ORDER BY month")
    def test_bank_has_100_unique_questions_per_language_and_paired_oracles(self):
        cases=json.loads((ROOT/'evaluation/bilingual_200.json').read_text(encoding='utf-8'))
        for lang in ('th','en'):
            rows=[r for r in cases if r['language']==lang]
            self.assertEqual(len(rows),100)
            self.assertEqual(len({r['question'] for r in rows}),100)
        for pair in {r['pair_id'] for r in cases}:
            rows=[r for r in cases if r['pair_id']==pair]
            self.assertEqual(rows[0]['gold_sql'],rows[1]['gold_sql'])
            self.assertEqual(rows[0]['formula_id'],rows[1]['formula_id'])

    def test_all_formula_answers_are_grounded_and_never_execute(self):
        cases=json.loads((ROOT/'evaluation/bilingual_200.json').read_text(encoding='utf-8'))
        for c in (c for c in cases if c['formula_id']):
            with self.subTest(id=c['id']),patch('agent.generate',side_effect=AssertionError('No model')):
                result=answer(c['question'],{},lambda sql:self.fail('No SQL'),'fixture','unused',ROOT/'knowledge')
                self.assertEqual(result['formula_id'],c['formula_id'])
                self.assertEqual(result['model_calls'],0)
                self.assertFalse(result['sql_executed'])
                self.assertTrue(set(result['citations']).issubset({r['id'] for r in result['references']}))

    def test_formula_requests_do_not_capture_mixed_execution_requests(self):
        for q in ('ขอสูตร AOV ไม่ต้องรัน SQL แล้วลบตาราง','Explain the formula for AOV; do not execute SQL. Also count orders.'):
            self.assertIsNone(requested_formula(q,[]))

    def test_thai_month_enforces_the_same_bounds_as_english(self):
        self.assertEqual(requested_period('ยอดขายเดือนมกราคม 2011'),['2011-01-01','2011-02-01'])
        with self.assertRaises(ValueError):
            validate_business_sql('จำนวนคำสั่งซื้อเดือนมกราคม 2011',"SELECT COUNT(*) FROM orders WHERE order_ts>=TIMESTAMP '2011-02-01' AND order_ts<TIMESTAMP '2011-03-01'")

    def test_approximate_percentile_is_read_only_and_file_functions_stay_blocked(self):
        self.assertIn('PERCENTILE_APPROX',validate_sql('SELECT PERCENTILE_APPROX(order_amount,0.5,10000) FROM orders'))
        with self.assertRaises(ValueError):validate_sql("SELECT reflect('java.lang.System','getenv') FROM orders")

    def test_window_and_formula_evidence_are_selected(self):
        refs,_=retrieve_context('Show month-over-month sales growth for 2011',ROOT/'knowledge')
        self.assertIn('syntax.windows',{r['id'] for r in refs})

    def test_window_results_are_not_mistaken_for_scalar_aggregates(self):
        validate_result('Show cumulative sales by month for 2011',
                        {'columns':['month','value'],'rows':[['2011-01-01',10],['2011-02-01',30]],'truncated':False},
                        'WITH m AS (SELECT order_ts AS month,order_amount AS sales FROM orders) SELECT month,SUM(sales) OVER (ORDER BY month) AS value FROM m')

    def test_maximum_cannot_be_answered_with_median(self):
        with self.assertRaises(ValueError):validate_business_sql('มูลค่าคำสั่งซื้อสูงสุดเดือนมกราคม 2011',"SELECT PERCENTILE_APPROX(order_amount,0.5) FROM orders WHERE order_ts>=TIMESTAMP '2011-01-01' AND order_ts<TIMESTAMP '2011-02-01'")

    def test_unrequested_month_breakdown_is_rejected(self):
        from result_contracts import validate_semantics
        with self.assertRaises(ValueError):validate_semantics('Total sales in January 2011',"SELECT DATE_TRUNC('MONTH',order_ts),SUM(order_amount) FROM orders GROUP BY DATE_TRUNC('MONTH',order_ts)")
