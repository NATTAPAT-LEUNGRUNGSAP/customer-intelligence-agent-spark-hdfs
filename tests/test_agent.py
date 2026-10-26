import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'jobs'))
from retrieval import retrieve, retrieve_context
from sql_guard import validate_sql
from agent import answer, policy_check
from evaluate import same_result
from decimal import Decimal
from rag_metrics import retrieval_metrics
from context_budget import check_budget
from result_contracts import validate_result, validate_semantics


class EvaluationTests(unittest.TestCase):
    def test_result_equivalence_and_duplicates(self):
        a = {'truncated':False,'rows':[[Decimal('2.0000')],[Decimal('10.0000')]]}
        b = {'truncated':False,'rows':[[10.0],[2.0000001]]}
        self.assertTrue(same_result(a,b,False))
        self.assertFalse(same_result(a,b,True))
        self.assertFalse(same_result({'truncated':False,'rows':[[2],[2]]},b,False))
        self.assertFalse(same_result(dict(a,truncated=True),a,False))


class GuardTests(unittest.TestCase):
    def test_date_trunc_unit_order(self):
        for sql in ["SELECT date_trunc(invoice_ts,MONTH) FROM sales_lines",
                    "SELECT date_trunc('2011-03-01',TIMESTAMP) FROM sales_lines"]:
            with self.assertRaisesRegex(ValueError,'unit first'):
                validate_sql(sql)
        validate_sql("SELECT date_trunc('MONTH',invoice_ts) FROM sales_lines")
    def test_analytics(self):
        for query in [
            'SELECT country, SUM(order_amount) FROM orders GROUP BY country',
            "SELECT sum(order_amount) FROM orders WHERE order_ts>=TIMESTAMP '2011-10-01' AND order_ts<TIMESTAMP '2011-11-01'",
            'WITH x AS (SELECT * FROM orders) SELECT count(*) FROM x',
            'SELECT * FROM orders UNION ALL SELECT * FROM orders',
            "SELECT date_trunc('MONTH',order_ts),sum(order_amount)/nullif(count(*),0) FROM orders GROUP BY 1",
            "SELECT row_number() OVER (ORDER BY sales_180d DESC,customer_id) FROM customer_summary"]:
            with self.subTest(query=query):
                self.assertIn('LIMIT 201', validate_sql(query))

    def test_rejects_unsafe(self):
        for query in [
            'DROP TABLE orders', 'SELECT * FROM orders; SELECT * FROM orders',
            "SELECT * FROM parquet.`/etc/passwd`", 'SELECT * FROM secret',
            'SELECT * FROM default.orders', "SELECT reflect('java.lang.Runtime','getRuntime') FROM orders",
            "SELECT java_method('java.lang.System','getenv','HOME') FROM orders",
            "SELECT * FROM range(1000000000)", 'SELECT * INTO other FROM orders',
            "WITH secret AS (SELECT * FROM private) SELECT * FROM secret",
            "WITH private AS (SELECT * FROM orders) SELECT * FROM secret",
            'SELECT current_user() FROM orders', 'SELECT 1',
            'WITH orders AS (SELECT * FROM private) SELECT * FROM orders']:
            with self.subTest(query=query):
                with self.assertRaises(Exception):
                    validate_sql(query)


class RetrievalTests(unittest.TestCase):
    def test_return_instruction_is_not_refund_and_two_or_more_is_repeat(self):
        from retrieval import tokens
        self.assertNotIn('concept_returns',tokens('Return the invoice count in 2011'))
        self.assertIn('concept_returns',tokens('Count return product lines in 2011'))
        ids=[c['id'] for c in retrieve('Fraction of identified customers with two or more invoices in March 2011',Path(__file__).resolve().parents[1]/'knowledge')]
        self.assertEqual(ids[0],'metric.repeat_rate')
        self.assertIn('schema.orders',ids)
    def test_gold_queries_obey_guard(self):
        root = Path(__file__).resolve().parents[1] / 'evaluation'
        counts = {}
        for path in (root/'dev.json',root/'test.json',root/'rag_holdout_v2.json',root/'rag_holdout_v3.json',root/'rag_holdout_v4.json',root/'rag_holdout_v5.json',root/'rag_holdout_v6.json'):
            cases = json.loads(path.read_text(encoding='utf-8'))
            counts[path.stem] = len(cases)
            for case in cases:
                if 'gold_sql' in case:
                    with self.subTest(id=case['id']):
                        validate_sql(case['gold_sql'])
        self.assertEqual(counts, {'dev': 10, 'test': 20, 'rag_holdout_v2': 20, 'rag_holdout_v3': 20,'rag_holdout_v4':20,'rag_holdout_v5':20,'rag_holdout_v6':20})

    def test_metric_rule_brings_schema_and_top_n_syntax(self):
        root=Path(__file__).resolve().parents[1]/'knowledge'
        ids={c['id'] for c in retrieve('Top five countries by completed invoice count in October 2011',root)}
        self.assertTrue({'metric.orders','schema.orders','syntax.ranking'}.issubset(ids))

    def test_ranking_metrics_penalize_missing_and_low_rank_evidence(self):
        result = retrieval_metrics(['other','metric.orders'],['metric.orders','schema.orders'])
        self.assertEqual(result['recall_at_6'],0.5)
        self.assertEqual(result['mrr_at_6'],0.5)
        self.assertLess(result['ndcg_at_6'],0.5)

    def test_required_policy_documents_and_unknown_corpus(self):
        root = Path(__file__).resolve().parents[1] / 'knowledge'
        context,trace = retrieve_context('completed orders',root)
        self.assertTrue({'policy.period','policy.availability','policy.snapshot'}.issubset(
            {c['id'] for c in context}))
        self.assertTrue(trace['ranked_ids'])
        with self.assertRaises(ValueError):
            retrieve_context('anything',root/'missing')

    def test_repeatable_and_relevant(self):
        path = Path(__file__).resolve().parents[1] / 'knowledge'
        results = retrieve('repeat customer rate identified customers selected period', path, 3)
        self.assertEqual(results, retrieve('repeat customer rate identified customers selected period', path, 3))
        self.assertTrue(any('Repeat customer rate' in r['text'] for r in results))
        self.assertTrue(all(len(r['sha256']) == 64 for r in results))


class AgentTests(unittest.TestCase):
    def setUp(self):
        # These tests isolate the older correction/reviewer loop. New deterministic
        # contracts and actual OPA are exercised separately, without a live model.
        for target in ('agent.validate_business_sql','agent.authorize'):
            mock = patch(target,return_value={'status':'passed','allow':True})
            mock.start()
            self.addCleanup(mock.stop)
    def test_scalar_pair_contract_rejects_extra_month_column(self):
        with self.assertRaisesRegex(ValueError,'exactly two scalar'):
            validate_semantics('For Sweden in 2011 give total sales followed by invoice count',
                "SELECT date_trunc('MONTH',order_ts),sum(order_amount),count(*) FROM orders GROUP BY 1")
        validate_semantics('For Sweden in 2011 give total sales followed by invoice count',
                           'SELECT sum(order_amount),count(*) FROM orders')

    def test_failed_query_retains_only_validated_evidence_ids(self):
        result=self.run_agent([{'sql':'DROP TABLE orders','citations':['metric.orders']}]*3,
                              lambda sql:self.fail('Must not execute'))
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['citations'],['metric.orders'])
    def test_context_budget_rejects_oversized_prompt(self):
        with self.assertRaisesRegex(ValueError,'Context budget exceeded'):
            check_budget([{'role':'user','content':'noise '*5000}])
        self.assertFalse(check_budget([{'role':'user','content':'Hello'}])['exact_token_count'])

    def test_identified_contract_repairs_null_result(self):
        outputs=[{'sql':'SELECT customer_id FROM orders','citations':['schema.orders']},
                 {'sql':'SELECT customer_id FROM orders WHERE customer_id IS NOT NULL','citations':['schema.orders']},
                 {'approved':True,'citations':['schema.orders']}]
        results=iter([{'columns':['customer_id'],'rows':[['12346']],'truncated':False}])
        with patch('agent.generate',side_effect=outputs):
            result=answer('Top identified customers in January 2011',{},lambda sql:next(results),
                          'fixture','unused',Path(__file__).resolve().parents[1]/'knowledge')
        self.assertEqual(result['status'],'executed')
        self.assertEqual(len(result['attempts']),1)
        self.assertEqual(result['result']['rows'],[['12346']])

    def test_population_contract_rejects_or_that_admits_null(self):
        question='Repeat fraction for identified customers in June 2011'
        for sql in ['SELECT count(*) FROM orders',
                    'SELECT count(*) FROM orders WHERE customer_id IS NOT NULL OR country=\'UK\'']:
            with self.assertRaisesRegex(ValueError,'Identified customer population'):
                validate_semantics(question,sql)
        validate_semantics(question,'SELECT count(*) FROM orders WHERE customer_id IS NOT NULL AND order_amount>0')

    def test_contract_does_not_remove_legitimate_anonymous_groups(self):
        validate_result('Sales by customer including anonymous in 2011',
                        {'columns':['customer_id'],'rows':[[None]]})

    def test_snapshot_policy_does_not_reject_separate_transaction_range(self):
        self.assertIsNone(policy_check(
            'For Champions at snapshot 2011-12-01, count orders from 2011-10-01 to 2011-11-01',
            {'as_of_date':'2011-12-01'}))

    def run_agent(self, outputs, execute):
        with patch('agent.generate', side_effect=outputs):
            return answer('How many completed invoices in October 2011?', {}, execute, 'fixture', 'http://unused',
                          Path(__file__).resolve().parents[1] / 'knowledge')

    def test_rejected_sql_is_not_executed(self):
        calls = []
        result = self.run_agent([{'sql': 'DROP TABLE orders','citations':['metric.orders']},
                               {'sql': 'SELECT count(*) FROM orders','citations':['metric.orders']},
                               {'approved':True,'citations':['metric.orders']}],
                               lambda sql: calls.append(sql) or {'columns':['n'],'rows': [[3]],'truncated':False})
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(len(result['attempts']), 1)

    def test_clarification_never_executes(self):
        result = self.run_agent([{'clarification': 'Which period?','citations':['policy.period']}],
                               lambda sql: self.fail('Must not execute'))
        self.assertEqual(result['status'], 'clarification')

    def test_retry_budget(self):
        result = self.run_agent([{'sql': 'DROP TABLE orders','citations':['metric.orders']}]*3,
                               lambda sql: self.fail('Must not execute'))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['attempts']), 3)

    def test_invented_citations_never_execute(self):
        result = self.run_agent([{'sql':'SELECT count(*) FROM orders','citations':['invented.rule']}]*3,
                               lambda sql:self.fail('Must not execute'))
        self.assertEqual(result['status'],'failed')

    def test_missing_period_and_unavailable_snapshot_never_execute(self):
        for question in ['ยอดขายรวมเท่าไร?','RFM distribution at snapshot 2010-06-01']:
            with patch('agent.generate',side_effect=AssertionError('Must not call model')):
                result=answer(question,{'_dataset_metadata':{'as_of_date':'2011-12-01'}},
                    lambda sql:self.fail('Must not execute'),'fixture','http://unused',
                    Path(__file__).resolve().parents[1]/'knowledge')
            self.assertEqual(result['status'],'clarification')
            self.assertTrue(result['citations'])
            self.assertTrue(result['rag'])

    def test_semantic_review_blocks_wrong_grain_before_execution(self):
        calls=[]
        result=self.run_agent([
            {'sql':'SELECT count(*) FROM sales_lines','citations':['metric.orders']},
            {'approved':False,'reason':'Counting lines instead of invoices','citations':['metric.orders']},
            {'sql':'SELECT count(*) FROM orders','citations':['metric.orders']},
            {'approved':True,'citations':['metric.orders']}],lambda sql:calls.append(sql) or {'columns':['n'],'rows':[[3]],'truncated':False})
        self.assertEqual(result['status'],'executed')
        self.assertEqual(len(calls),1)
        self.assertNotIn('sales_lines',calls[0])


if __name__ == '__main__':
    unittest.main()
