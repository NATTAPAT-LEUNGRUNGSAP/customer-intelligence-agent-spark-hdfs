"""Opt-in integration: requires the actual OPA service, no mocked policy engine."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from agent import answer
from policy_engine import authorize, policy_facts, PolicyUnavailable
from result_contracts import result_violations


class ActualOPAIntegration(unittest.TestCase):
    def test_real_engine_checks_result_fixtures(self):
        good={'columns':['n'],'rows':[[3]],'truncated':False}
        self.assertTrue(authorize(policy_facts('SELECT count(*) FROM orders',1,'post',result_violations('',good,'SELECT count(*) FROM orders')))['allow'])
        for value in (-1,1.5,float('nan')):
            bad=dict(good,rows=[[value]])
            codes=result_violations('',bad,'SELECT count(*) FROM orders')
            self.assertTrue(codes)
            with self.assertRaisesRegex(ValueError,'OPA denied'):
                authorize(policy_facts('SELECT count(*) FROM orders',1,'post',codes))
    def test_post_denial_never_delivers_bad_answer(self):
        sql="SELECT count(*) FROM orders WHERE order_ts>=TIMESTAMP '2011-06-01' AND order_ts<TIMESTAMP '2011-07-01'"
        proposal={'sql':sql,'citations':['metric.orders']}
        review={'approved':True,'citations':['metric.orders']}
        calls=[]
        # Only model output is a fixture; HTTP policy evaluation is real.
        with patch('agent.generate',side_effect=[dict(proposal),dict(review)]*3):
            result=answer('Count completed invoices in June 2011',{},
                          lambda sql:calls.append(sql) or {'columns':['n'],'rows':[[-1]],'truncated':False},
                          'fixture','unused',Path(__file__).resolve().parents[1]/'knowledge')
        self.assertEqual(result['status'],'failed')
        self.assertNotIn('result',result)
        self.assertEqual(len(calls),3)
        self.assertTrue(all('OPA denied' in a['error'] for a in result['attempts']))
    def test_unreachable_endpoint_fails_closed(self):
        with self.assertRaises(PolicyUnavailable):
            authorize(policy_facts('SELECT count(*) FROM orders',1),endpoint='http://127.0.0.1:9')


if __name__=='__main__':unittest.main(verbosity=2)
