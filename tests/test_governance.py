import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from rdflib import Graph, Literal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from ontology import resolve, validate_graph, ROOT, CI
from policy_engine import authorize, policy_facts, PolicyUnavailable
from semantic_contracts import validate_business_sql
from result_contracts import result_violations
from result_contracts import validate_semantics
from agent import answer


class OntologyTests(unittest.TestCase):
    def test_bilingual_mapping_has_table_grain_formula_and_evidence(self):
        for q in ('invoice count','จำนวนคำสั่งซื้อ'):
            m=resolve(q)['matches'][0]
            self.assertEqual((m['table'],m['grain']),('orders','invoice'))
            self.assertEqual(m['formula'],'COUNT(*)')
            self.assertEqual(m['evidence_ids'],['metric.orders','schema.orders'])
    def test_missing_relation_fails_shacl(self):
        g=Graph().parse(ROOT/'customer-intelligence.ttl')
        g.remove((CI.invoices,CI.sourceTable,None))
        with self.assertRaisesRegex(ValueError,'SHACL'):
            validate_graph(g,Graph().parse(ROOT/'shapes.ttl'))
    def test_conflicting_grain_fails(self):
        g=Graph().parse(ROOT/'customer-intelligence.ttl')
        g.set((CI.invoices,CI.hasGrain,CI.product_line))
        with self.assertRaisesRegex(ValueError,'grain mismatch'):
            validate_graph(g,Graph().parse(ROOT/'shapes.ttl'))
    def test_unknown_term_is_not_silently_mapped(self):
        self.assertEqual(resolve('office furniture policy')['matches'],[])


class BusinessTests(unittest.TestCase):
    good="SELECT count(*) FROM orders WHERE order_ts>=TIMESTAMP '2011-06-01' AND order_ts<TIMESTAMP '2011-07-01'"
    question='Count completed invoices in June 2011'
    def test_correct_month(self):
        self.assertIn('exact_requested_period',validate_business_sql(self.question,self.good)['checks'])
    def test_wrong_grain(self):
        with self.assertRaisesRegex(ValueError,'one invoice'):
            validate_business_sql(self.question,self.good.replace('orders','sales_lines'))
    def test_wrong_month(self):
        with self.assertRaisesRegex(ValueError,'Requested period'):
            validate_business_sql(self.question,self.good.replace('2011-06-01','2011-05-01'))
    def test_month_span_is_not_last_month_only(self):
        sql="SELECT date_trunc('MONTH',order_ts),sum(order_amount) FROM orders WHERE order_ts>=TIMESTAMP '2010-08-01' AND order_ts<TIMESTAMP '2010-11-01' GROUP BY 1"
        validate_business_sql('Show monthly completed sales from August through October 2010',sql)
    def test_or_bypass(self):
        with self.assertRaisesRegex(ValueError,'Requested period'):
            validate_business_sql(self.question,self.good.replace(' AND ',' OR '))
    def test_missing_snapshot(self):
        with self.assertRaisesRegex(ValueError,'as_of_date'):
            validate_business_sql('Count Champions at snapshot 2011-12-01','SELECT count(*) FROM customer_summary')
    def test_wrong_transaction_type(self):
        with self.assertRaisesRegex(ValueError,'transaction_type'):
            validate_business_sql('Count cancellation product lines in June 2011',self.good.replace('orders','sales_lines').replace('order_ts','invoice_ts'))
    def test_fanout(self):
        with self.assertRaisesRegex(ValueError,'fan-out'):
            validate_business_sql('Total sales all available data','SELECT sum(o.order_amount) FROM orders o JOIN sales_lines s ON o.invoice_id=s.invoice_id')
    def test_transparent_cte_can_filter_before_grouping(self):
        validate_semantics('repeat fraction of identified customers',
            'WITH p AS (SELECT * FROM orders), f AS (SELECT customer_id,count(*) n FROM p WHERE customer_id IS NOT NULL GROUP BY customer_id) SELECT count(*) FROM f')
    def test_cte_cannot_filter_after_destroying_population(self):
        for inner in ('SELECT DISTINCT customer_id FROM orders',
                      'SELECT customer_id FROM orders LIMIT 2',
                      'SELECT customer_id,count(*) n FROM orders GROUP BY customer_id'):
            with self.assertRaisesRegex(ValueError,'Identified customer population'):
                validate_semantics('repeat fraction of identified customers',
                    f'WITH p AS ({inner}) SELECT count(*) FROM p WHERE customer_id IS NOT NULL')
    def test_cte_all_branches_must_be_filtered(self):
        with self.assertRaisesRegex(ValueError,'Identified customer population'):
            validate_semantics('identified customers','WITH p AS (SELECT * FROM orders) SELECT customer_id FROM p WHERE customer_id IS NOT NULL UNION ALL SELECT customer_id FROM p')


class PostToolTests(unittest.TestCase):
    def test_valid_count(self):
        self.assertEqual(result_violations('',{'columns':['n'],'rows':[[3]],'truncated':False},'SELECT count(*) FROM orders'),[])
    def test_bad_envelope_width_cap_nan_and_count(self):
        fixtures=[({'rows':[]},None,'malformed_result_envelope'),
          ({'columns':['n'],'rows':[[1,2]],'truncated':False},None,'row_width_mismatch'),
          ({'columns':['n'],'rows':[[1]]*201,'truncated':False},None,'row_cap_exceeded'),
          ({'columns':['n'],'rows':[[float('nan')]],'truncated':False},None,'non_finite_numeric_value'),
          ({'columns':['n'],'rows':[[float('nan')]],'truncated':False},'SELECT count(*) FROM orders','count_must_be_nonnegative_integer'),
          ({'columns':['n'],'rows':[[-1]],'truncated':False},'SELECT count(*) FROM orders','count_must_be_nonnegative_integer'),
          ({'columns':['n'],'rows':[[1],[2]],'truncated':False},'SELECT count(*) FROM orders','scalar_aggregate_requires_one_row')]
        for result,sql,code in fixtures:
            with self.subTest(code=code):self.assertIn(code,result_violations('',result,sql))
    def test_group_duplicate(self):
        self.assertIn('duplicate_group_keys',result_violations('',{'columns':['country','n'],'rows':[['UK',1],['UK',2]],'truncated':False},'SELECT country,count(*) FROM orders GROUP BY country'))
    def test_null_identified_and_fraction(self):
        self.assertIn('identified_customer_id_null',result_violations('identified customers',{'columns':['customer_id'],'rows':[[None]],'truncated':False}))
        self.assertIn('fraction_out_of_range',result_violations('repeat rate',{'columns':['rate'],'rows':[[1.1]],'truncated':False}))


class PolicyTests(unittest.TestCase):
    def test_unavailable_opa_denies(self):
        with patch('policy_engine.urlopen',side_effect=OSError('offline')):
            with self.assertRaises(PolicyUnavailable):authorize(policy_facts('SELECT count(*) FROM orders',1))
    def test_undefined_decision_denies(self):
        with patch('policy_engine.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value=b'{}'
            with self.assertRaises(PolicyUnavailable):authorize(policy_facts('SELECT count(*) FROM orders',1))
    def test_agent_never_executes_if_opa_unavailable(self):
        proposal={'sql':BusinessTests.good,'citations':['metric.orders']}
        with patch('agent.generate',return_value=proposal),patch('agent.authorize',side_effect=PolicyUnavailable('offline')):
            r=answer(BusinessTests.question,{},lambda sql:self.fail('Must not execute'),
                     'fixture','unused',Path(__file__).resolve().parents[1]/'knowledge')
        self.assertEqual(r['status'],'failed')
        self.assertTrue(r['policy_blocked'])
        self.assertEqual(len(r['attempts']),1)
