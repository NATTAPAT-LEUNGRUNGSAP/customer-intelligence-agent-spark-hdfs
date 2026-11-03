import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'jobs'))
from agent import answer, validate_citations
from agent_tools import observe_tools
from pseudonymization import pseudonymize_result

KNOWLEDGE = Path(__file__).resolve().parents[1] / 'knowledge'


class AgentToolTests(unittest.TestCase):
    def test_invalid_citations_explain_exact_allowed_ids_for_repair(self):
        context=[{'id':'metric.orders'},{'id':'schema.orders'}]
        for citations in (None,[],['evidence.id'],['metric_orders']):
            with self.subTest(citations=citations),self.assertRaises(ValueError) as caught:
                validate_citations(citations,context)
            self.assertIn('metric.orders',str(caught.exception))
            self.assertIn('schema.orders',str(caught.exception))
        self.assertEqual(validate_citations(['metric.orders'],context),['metric.orders'])
    def test_trace_evaluation_does_not_claim_accuracy(self):
        from evaluate_agent_trace import summarize
        result = summarize([{'status':'executed','attempts':[{}],'model_calls':3}])
        self.assertEqual(result['repaired_executions'],1)
        self.assertIsNone(result['answer_accuracy'])
        self.assertIsNone(summarize([])['execution_rate'])

    def test_metadata_cannot_request_execution_or_private_tables(self):
        for request in [{'name':'run_python','code':'x'},
                        {'name':'describe_table','table':'private'},
                        {'name':'list_tables','sql':'DROP TABLE orders'}]:
            with self.assertRaises(ValueError):
                observe_tools({'tools':[request]}, {'orders':'struct<n:int>'})

    def test_observation_drives_next_model_turn_before_execution(self):
        calls = []
        def generate(messages, *args, **kwargs):
            calls.append(messages)
            if len(calls) == 1:
                return {'plan':['inspect invoice schema'], 'tools':[
                    {'name':'describe_table','table':'orders'}], 'sql':'DROP TABLE orders'}
            if len(calls) == 2:
                self.assertIn('struct<n:int>', str(messages))
                return {'sql':"SELECT COUNT(*) AS n FROM orders WHERE order_ts >= TIMESTAMP '2011-10-01' AND order_ts < TIMESTAMP '2011-11-01'",'citations':['metric.orders']}
            return {'approved':True,'citations':['metric.orders']}
        executed = []
        with patch('agent.generate', side_effect=generate), patch('agent.authorize', return_value={'allow':True}):
            result = answer('Count invoices in October 2011', {'orders':'struct<n:int>'},
                lambda sql: executed.append(sql) or {'columns':['n'],'rows':[[3]],'truncated':False},
                'fixture','unused', KNOWLEDGE)
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(len(executed), 1)
        self.assertEqual(result['model_calls'], 3)
        self.assertEqual(result['agent_trace'][-1]['row_count'], 1)

    def test_tool_loop_is_bounded(self):
        with patch('agent.generate', return_value={'tools':[{'name':'list_tables'}]}):
            result = answer('Count invoices in October 2011', {'orders':'x'},
                lambda sql:self.fail('Tool loop must never execute'), 'fixture','unused',KNOWLEDGE)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['model_calls'], 3)

    def test_export_pseudonyms_preserve_nulls_and_source(self):
        source = {'columns':['customer_id','n'],'rows':[['123',2],[None,1]],'truncated':False}
        first = pseudonymize_result(source,b'a'*32)
        self.assertEqual(first, pseudonymize_result(source,b'a'*32))
        self.assertNotEqual(first, pseudonymize_result(source,b'b'*32))
        self.assertEqual(first['rows'][1], [None,1])
        self.assertEqual(source['rows'][0][0], '123')
        with self.assertRaises(ValueError):
            pseudonymize_result(source,b'short')

    def test_mcp_tool_boundary(self):
        try:
            from mcp_server import create_server
            import mcp
        except ImportError:
            self.skipTest('Install requirements-mcp.txt for MCP SDK test')
        async def check():
            server = create_server({'orders':'struct<n:int>'}, lambda question:{
                'status':'executed','sql':'private','attempts':[{'error':'private'}],
                'result':{'columns':['customer_id'],'rows':[['123']],'truncated':False}}, b'a'*32)
            tools = await server.list_tools()
            self.assertEqual({t.name for t in tools}, {'list_tables','describe_table','analyze'})
            result = await server.call_tool('analyze', {'question':'count invoices in 2011'})
            self.assertNotIn('private', str(result))
            self.assertIn('customer_', str(result))
            from mcp.server.fastmcp.exceptions import ToolError
            with self.assertRaises(ToolError):
                await server.call_tool('describe_table', {'table':'private'})
        asyncio.run(check())


if __name__ == '__main__':
    unittest.main()
