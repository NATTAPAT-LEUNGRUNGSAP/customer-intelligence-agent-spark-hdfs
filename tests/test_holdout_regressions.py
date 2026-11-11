import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'jobs'))
from metric_contracts import request_constraints, validate_metric_expression


class HoldoutRegressionTests(unittest.TestCase):
    def test_spelled_ranking_limit(self):
        question = 'Return the top four countries by invoice count'
        query = 'SELECT country, COUNT(*) AS n FROM orders GROUP BY country ORDER BY n DESC'
        validate_metric_expression(question, query + ' LIMIT 4')
        with self.assertRaisesRegex(ValueError, 'LIMIT 4'):
            validate_metric_expression(question, query + ' LIMIT 5')

    def test_anonymous_invoice_sales_requires_explicit_null_filter(self):
        question = 'What were total sales from invoices without a customer ID?'
        query = 'SELECT SUM(order_amount) FROM orders'
        validate_metric_expression(question, query + ' WHERE customer_id IS NULL')
        for suffix in ('', ' WHERE customer_id IS NOT NULL'):
            with self.assertRaisesRegex(ValueError, 'IS NULL'):
                validate_metric_expression(question, query + suffix)

    def test_top_sales_day_keeps_anonymous_invoices(self):
        question = 'Return the highest-sales day in the UK and its sales.'
        query = "SELECT DATE_TRUNC('DAY', order_ts),SUM(order_amount) FROM orders"
        self.assertEqual(request_constraints(question)['time_bucket_unit'], 'DAY')
        with self.assertRaisesRegex(ValueError, 'customer ID filter'):
            validate_metric_expression(question, query + ' WHERE customer_id IS NOT NULL')

    def test_requested_day_count_does_not_include_month(self):
        question = 'แยกตามวัน คืนวันที่และจำนวน'
        query = "SELECT DATE_TRUNC('DAY', order_ts),COUNT(*) FROM orders GROUP BY 1"
        validate_metric_expression(question, query)
        with self.assertRaisesRegex(ValueError, 'exactly 2'):
            validate_metric_expression(question, query.replace('COUNT(*)', "COUNT(*),DATE_TRUNC('MONTH', order_ts)"))
