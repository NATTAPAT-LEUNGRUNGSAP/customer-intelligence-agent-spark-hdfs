import datetime
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from conversation import Sessions, SessionLimit, followup
from chart_data import chart_data
from web_app import Application


class ConversationTests(unittest.TestCase):
    def test_month_followups_preserve_metric_country_and_year_rollover(self):
        q,scope=followup('แล้วเดือนก่อนล่ะ','ยอดขาย Germany เดือนมกราคม 2011')
        self.assertEqual(q,'ยอดขาย Germany เดือนธันวาคม 2010')
        self.assertEqual(scope['period'],['2010-12-01','2011-01-01'])
        q,_=followup('what about next month','Count invoices in December 2010')
        self.assertEqual(q,'Count invoices in January 2011')

    def test_half_open_scope_does_not_replace_dates_twice(self):
        q,_=followup('แล้วเดือนก่อนล่ะ','Sales from 2011-02-01 before 2011-03-01 (exclusive)')
        self.assertIn('2011-01-01 before 2011-02-01',q)

    def test_ambiguous_or_missing_context_asks_instead_of_guessing(self):
        for previous in [None,'Sales in 2011','Sales from 2011-01-15 before 2011-02-15']:
            with self.assertRaises(ValueError):followup('แล้วเดือนก่อนล่ะ',previous)
        with self.assertRaises(ValueError):followup('what about those','Sales in January 2011')
        self.assertEqual(followup('Sales in February 2011',None),('Sales in February 2011',None))

    def test_sessions_are_isolated_bounded_and_expire(self):
        now=[0.0];sessions=Sessions(clock=lambda:now[0],ttl=10,capacity=2,requests=1)
        token,first=sessions.get();other,second=sessions.get()
        self.assertNotEqual(token,other)
        first['history'].append({'question':'private'})
        self.assertEqual(second['history'],[])
        with self.assertRaises(SessionLimit):sessions.get()
        sessions.consume(first)
        with self.assertRaises(SessionLimit):sessions.consume(first)
        now[0]=11
        self.assertNotEqual(sessions.get(token)[0],token)

    def test_application_inherits_only_successful_question(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(None,{}, {'run_id':'fixture'},'fixture','unused',{},directory)
            token,state=app.sessions.get()
            with patch('web_app.answer',return_value={'status':'executed'}) as model:
                app.query('Sales in January 2011',session_id=token)
                result=app.query('แล้วเดือนก่อนล่ะ',session_id=token,follow_up=True)
                self.assertEqual(model.call_args.args[0],'Sales in December 2010')
                self.assertEqual(result['session_remaining'],18)
            self.assertEqual(len(state['history']),2)


class ChartTests(unittest.TestCase):
    def test_only_validated_successful_results_are_charted(self):
        result={'columns':['country','sales'],'rows':[['Germany',Decimal('1.25')]],'truncated':False}
        self.assertIsNone(chart_data({'status':'failed','result':result}))
        self.assertIsNone(chart_data({'status':'executed','result':result}))
        data=chart_data({'status':'executed','result':result,'result_contract':{'checked':True}})
        self.assertEqual(data['rows'],[['Germany',1.25]])
        self.assertEqual(data['numeric_indices'],[1])

    def test_chart_cap_and_nonfinite_values(self):
        result={'columns':['month','value'],'rows':[[str(i),i] for i in range(101)],'truncated':False}
        data=chart_data({'status':'executed','result':result,'result_contract':{'checked':True}})
        self.assertEqual(len(data['rows']),100);self.assertTrue(data['truncated'])
        result['rows']=[['bad',float('inf')]]
        self.assertIsNone(chart_data({'status':'executed','result':result,'result_contract':{'checked':True}}))


if __name__=='__main__':unittest.main()
