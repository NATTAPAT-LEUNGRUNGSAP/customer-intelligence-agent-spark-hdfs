import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts.evaluate_hallucination import evaluate_case, export_scores, summarize


class HallucinationEvaluationTests(unittest.TestCase):
    def test_faithful_explanation_can_have_wrong_result_and_never_sees_gold(self):
        case = {
            'id': 'test', 'language': 'en', 'family': 'scalar',
            'question': 'How many orders?', 'correct': False, 'gold': {'rows': [[5]]},
            'result': {
                'status': 'executed', 'explanation': 'The result contains 3 orders.',
                'executed_sql': 'SELECT COUNT(*) FROM orders WHERE country = \'France\'',
                'result': {'rows': [[3]]},
                'references': [{'id': 'kept', 'text': 'One row per order.'},
                               {'id': 'dropped', 'text': 'Excluded evidence.'}],
                'context_plan': {'selected_ids': ['kept'], 'all_selected_evidence_retained': True},
            },
        }

        def judge(packet):
            self.assertEqual(packet['evidence'], {'kept': 'One row per order.'})
            self.assertEqual(packet['returned_result'], {'rows': [[3]]})
            self.assertNotIn('gold', packet)
            self.assertNotIn('correct', packet)
            return {'claims': [{'text': '3 orders', 'verdict': 'supported'}]}

        row = evaluate_case(case, judge)
        self.assertEqual(row['faithfulness'], 1)
        self.assertFalse(row['sql_result_correctness'])

    def test_skipped_case_is_not_a_perfect_faithfulness_score(self):
        row = evaluate_case({
            'id': 'test', 'language': 'th', 'family': 'clarification',
            'question': 'ยอดขายดีไหม', 'correct': True,
            'result': {'status': 'clarification', 'message': 'ต้องการช่วงเวลาใด'},
        }, lambda _: self.fail('Clarification must not call the SQL prose judge'))
        summary = summarize([row])
        self.assertEqual(summary['cases_correct'], 1)
        self.assertEqual(summary['faithfulness_scored'], 0)
        self.assertIsNone(summary['mean_faithfulness'])

    def test_export_keeps_answer_and_context_local(self):
        client = MagicMock()
        client.create_trace_id.return_value = 'f' * 32
        sdk = SimpleNamespace(get_client=lambda: client)
        env = {key: 'test' for key in (
            'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY', 'LANGFUSE_BASE_URL')}
        report = {
            'status': 'completed', 'run_id': 'run', 'source_sha256': 'hash',
            'judge_model': 'judge', 'cases': [{
                'id': 'case', 'language': 'en', 'family': 'scalar',
                'status': 'executed', 'judge_status': 'scored', 'faithfulness': 0,
                'sql_result_correctness': True, 'case_correctness': True,
                'has_ungrounded_claim': True, 'claims': ['sensitive-local-text'],
            }],
        }
        with patch.dict(sys.modules, {'langfuse': sdk}), patch.dict(os.environ, env):
            export_scores(report)
        self.assertEqual(client.create_score.call_count, 4)
        self.assertNotIn('sensitive-local-text', repr(client.mock_calls))
        client.flush.assert_called_once()
