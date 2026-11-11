"""Synchronous tool lifecycle hooks for trusted application code.

Before/after failures block execution/delivery. Error observers cannot hide the
original failure. Hooks never come from model output or retrieved documents.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolHooks:
    before_tool: tuple[Callable, ...] = ()
    after_tool: tuple[Callable, ...] = ()
    on_error: tuple[Callable, ...] = ()
    events: list = field(default_factory=list)

    def run(self, tool, operation, *, attempt=1):
        context = {'tool': tool, 'attempt': attempt}
        stage = 'before_tool'
        try:
            for hook in self.before_tool:
                hook(context)
            self.events.append(dict(context, stage=stage, status='passed'))
            stage = 'execute'
            result = operation()
            stage = 'after_tool'
            for hook in self.after_tool:
                hook(context, result)
            self.events.append(dict(context, stage=stage, status='passed'))
            return result
        except Exception as error:
            self.events.append(dict(context, stage=stage, status='blocked',
                                    error_type=type(error).__name__))
            for hook in self.on_error:
                try:
                    hook(context, error)
                except Exception as observer_error:
                    self.events.append(dict(context, stage='on_error', status='failed',
                                            error_type=type(observer_error).__name__))
            raise
