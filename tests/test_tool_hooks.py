import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'jobs'))
from tool_hooks import ToolHooks


class ToolHookTests(unittest.TestCase):
    def test_order_and_result(self):
        order=[]
        hooks=ToolHooks(before_tool=(lambda ctx: order.append('pre'),),
                        after_tool=(lambda ctx, result: order.append(result),))
        self.assertEqual(hooks.run('spark_sql',lambda: order.append('execute') or 42),42)
        self.assertEqual(order,['pre','execute',42])
        self.assertEqual([e['stage'] for e in hooks.events],['before_tool','after_tool'])

    def test_pre_denial_never_executes(self):
        operation=Mock()
        observer=Mock()
        def deny(ctx):
            raise ValueError('denied')
        hooks=ToolHooks(before_tool=(deny,),on_error=(observer,))
        with self.assertRaisesRegex(ValueError,'denied'):
            hooks.run('spark_sql',operation)
        operation.assert_not_called()
        observer.assert_called_once()
        self.assertEqual(hooks.events[-1]['stage'],'before_tool')

    def test_post_denial_never_returns_result(self):
        operation=Mock(return_value={'rows':[[1]]})
        def deny(ctx, result):
            raise ValueError('bad result')
        hooks=ToolHooks(after_tool=(deny,))
        with self.assertRaisesRegex(ValueError,'bad result'):
            hooks.run('spark_sql',operation)
        operation.assert_called_once()
        self.assertEqual(hooks.events[-1]['stage'],'after_tool')

    def test_observer_failure_preserves_original_error(self):
        def broken(*args):
            raise RuntimeError('observer failed')
        def operation():
            raise ValueError('spark failed')
        hooks=ToolHooks(on_error=(broken,))
        with self.assertRaisesRegex(ValueError,'spark failed'):
            hooks.run('spark_sql',operation,attempt=2)
        self.assertEqual(hooks.events[1]['stage'],'execute')
        self.assertEqual(hooks.events[1]['attempt'],2)
        self.assertEqual(hooks.events[-1]['stage'],'on_error')
