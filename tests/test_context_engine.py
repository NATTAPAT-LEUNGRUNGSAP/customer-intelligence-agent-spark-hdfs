import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from context_engine import assemble_evidence, repair_messages
from context_budget import check_budget, ContextBudgetExceeded
from agent import answer


class ContextTests(unittest.TestCase):
    def test_selected_facts_and_all_policies_are_lossless(self):
        references=[{'id':'metric.repeat_rate','text':'Include one-order customers in denominator.', 'score':9},
                    {'id':'policy.snapshot','text':'Only snapshot 2011-12-01 is available.'}]
        packet,trace=assemble_evidence(references,'irrelevant '*10000)
        data=json.loads(packet)
        self.assertEqual(data,[{'id':r['id'],'text':r['text']} for r in references])
        self.assertNotIn('score',data[0])
        self.assertTrue(trace['all_selected_evidence_retained'])
        self.assertEqual(trace['background_supplied_characters'],0)
        self.assertGreater(trace['background_omitted_characters'],0)
        self.assertEqual(trace['wire_format'],'complete-evidence-id-text-json')
        self.assertTrue(trace['retrieval_metadata_omitted'])

    def test_duplicate_conflicts_fail_closed(self):
        one={'id':'metric.sales','text':'Gross sales'}
        _,trace=assemble_evidence([one,one])
        self.assertEqual(trace['duplicates_removed'],1)
        with self.assertRaisesRegex(ValueError,'Conflicting evidence'):
            assemble_evidence([one,dict(one,text='Net profit')])

    def test_position_control_and_same_selected_facts(self):
        refs=[{'id':'metric.orders','text':'Count invoices'}]
        traces=[]
        for position in ('front','middle','end'):
            packet,trace=assemble_evidence(refs,'abcdefgh','unfiltered',position)
            data=json.loads(packet)
            self.assertEqual(data['untrusted_background_before']+data['untrusted_background_after'],'abcdefgh')
            traces.append(trace)
        self.assertEqual(len({t['selected_evidence_sha256'] for t in traces}),1)
        self.assertEqual(len({t['packet_sha256'] for t in traces}),3)

    def test_fifty_repairs_keep_original_constraints_and_latest_state(self):
        original=[{'role':'system','content':'Snapshot and schema facts'},
                  {'role':'user','content':'June2011, identified customers, UK'}]
        messages=original
        for i in range(50):
            messages=repair_messages(messages,{'sql':f'SELECT {i}', 'citations':['metric.orders'],
                                               'explanation':'discard '*10000},'Latest error\n'+('Spark plan '*10000))
        self.assertEqual(messages[:2],original)
        self.assertEqual(len(messages),4)
        self.assertIn('SELECT 49',messages[2]['content'])
        self.assertNotIn('discard',messages[2]['content'])
        self.assertNotIn('Spark plan',messages[3]['content'])

    def test_required_oversize_is_blocked_without_execution(self):
        refs=[{'id':'metric.orders','text':'Required fact '*5000}]
        packet,_=assemble_evidence(refs)
        with self.assertRaises(ContextBudgetExceeded):
            check_budget([{'role':'system','content':packet}])

    def test_budget_block_does_not_repeat_identical_model_attempt(self):
        with patch('agent.generate',side_effect=ContextBudgetExceeded('Context budget exceeded')) as model:
            result=answer('Count invoices in October 2011',{},lambda sql:self.fail('No SQL'),
                          'fixture','unused',Path(__file__).resolve().parents[1]/'knowledge')
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['context_blocked'])
        self.assertEqual(len(result['attempts']),1)
        self.assertEqual(model.call_count,1)
