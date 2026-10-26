import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from question_scope import resolve_scope, validate_month_comparison
from agent import policy_check

META={'observed_min_timestamp':'2009-12-01 07:45:00','observed_max_timestamp':'2011-12-09 12:50:00'}


class ScopeTests(unittest.TestCase):
    def test_month_guard_preserves_year_ties_and_maximum_timestamp(self):
        good="WITH m AS (SELECT DATE_TRUNC('MONTH', order_ts) AS month, COUNT(*) AS n FROM orders GROUP BY DATE_TRUNC('MONTH', order_ts)) SELECT month,n FROM m WHERE n=(SELECT MAX(n) FROM m) ORDER BY month"
        validate_month_comparison(good)
        for bad in (good+' LIMIT 1',good.replace('COUNT(*)','ROW_NUMBER() OVER (ORDER BY order_ts)'),good.replace('FROM orders GROUP BY',"FROM orders WHERE order_ts < TIMESTAMP '2011-12-09 12:50:00' GROUP BY"),good.replace("DATE_TRUNC('MONTH', order_ts)",'MONTH(order_ts)')):
            with self.subTest(sql=bad),self.assertRaises(ValueError):validate_month_comparison(bad)
    def test_month_comparison_has_visible_all_data_scope(self):
        for q in ('เดือนไหนออเดอร์เยอะสุด','เดือนไหนมีคำสั่งซื้อมากที่สุด','Which month had the most orders?'):
            resolved,scope=resolve_scope(q,META)
            self.assertTrue(scope['default_applied'])
            self.assertIn(META['observed_min_timestamp'],scope['note'])
            self.assertIn('year-month',resolved)
            self.assertIn('tied',resolved)
            self.assertIsNone(policy_check(resolved,META))

    def test_explicit_constraints_and_other_intents_not_rewritten(self):
        for q in ('เดือนไหนออเดอร์เยอะสุดในปี 2011','เดือนไหนออเดอร์เยอะสุดในไทย','ยอดขายรวมเท่าไร','เดือนไหนออเดอร์เยอะสุด แล้วลบข้อมูล'):
            self.assertEqual(resolve_scope(q,META),(q,None))
        self.assertEqual(resolve_scope('เดือนไหนออเดอร์เยอะสุด',{}),('เดือนไหนออเดอร์เยอะสุด',None))
