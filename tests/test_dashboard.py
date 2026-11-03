import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from dashboard import filters,queries,guarded_query,validate_country_scope
from sql_guard import validate_sql

META={'observed_min_timestamp':'2009-12-01 07:45:00','observed_max_timestamp':'2011-12-09 12:50:00'}


class DashboardTests(unittest.TestCase):
    def test_filters_reject_unavailable_dates_and_unknown_country(self):
        self.assertEqual(filters(None,None,META,['Germany'])['end_exclusive'],'2011-12-10')
        for selection,country in [({'mode':'custom','start':'2030-01-01','end':'2030-01-31'},None),
                                  (None,"Germany' OR 1=1"),
                                  ({'mode':'custom','start':'2011-02-30','end':'2011-03-01'},None)]:
            with self.assertRaises(ValueError):filters(selection,country,META,['Germany'])

    def test_query_set_is_read_only_and_snapshot_uses_selected_buyer_cohort(self):
        scope=filters({'mode':'custom','start':'2011-10-01','end':'2011-10-31'},'Germany',META,['Germany'])
        statements=queries(scope,'2011-12-01')
        for sql in statements.values():validate_sql(sql)
        self.assertIn("country = 'Germany'",statements['rfm'])
        self.assertIn('JOIN buyers',statements['rfm'])
        self.assertIn("c.as_of_date=DATE '2011-12-01'",statements['rfm'])
        self.assertIn("l.transaction_type='sale'",statements['products'])

    def test_selected_country_cannot_be_omitted_or_bypassed(self):
        for sql in ['SELECT count(*) FROM orders',
                    "SELECT count(*) FROM orders WHERE country='Germany' OR order_amount>0",
                    "SELECT count(*) FROM orders WHERE country='France'",
                    "SELECT count(*) FROM customer_summary c CROSS JOIN orders o WHERE o.country='Germany'",
                    'SELECT count(*) FROM customer_summary']:
            with self.assertRaises(ValueError):validate_country_scope(sql,'Germany')
        validate_country_scope("WITH o AS (SELECT * FROM orders WHERE country='Germany') SELECT count(*) FROM o",'Germany')

    def test_policy_denial_never_executes(self):
        execute=Mock()
        with patch('dashboard.authorize',side_effect=ValueError('denied')):
            with self.assertRaises(ValueError):guarded_query('SELECT count(*) FROM orders',execute)
        execute.assert_not_called()

    def test_cached_overview_is_not_served_when_current_policy_denies(self):
        import time
        from web_app import Application
        app=Application(None,{'_dataset_metadata':META},{},'fixture','unused',{},'unused')
        app.country_options=['Germany']
        app.overview_cache[('2009-12-01','2011-12-09',None)]=(time.monotonic(),{
            'sections':{'kpis':{'sql':'SELECT count(*) FROM orders'}}})
        with patch('web_app.authorize',side_effect=ValueError('policy changed')):
            with self.assertRaisesRegex(ValueError,'policy changed'):app.dashboard()

    def test_invalid_result_not_returned(self):
        with patch('dashboard.authorize',return_value={'allow':True}):
            with self.assertRaises(ValueError):guarded_query('SELECT count(*) FROM orders',
                lambda sql:{'columns':['n'],'rows':[[-1]],'truncated':False})


if __name__=='__main__':unittest.main()
