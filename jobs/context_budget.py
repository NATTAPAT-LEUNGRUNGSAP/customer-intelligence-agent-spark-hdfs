"""Conservative prompt-size control; estimate is not a tokenizer guarantee."""
import json
import math

CONTEXT_WINDOW = 8192
INPUT_BUDGET = 6000
SAFETY_RESERVE = 1024


class ContextBudgetExceeded(ValueError):
    def __init__(self,message,network_calls=0,usage=None):
        super().__init__(message)
        self.network_calls=network_calls
        self.usage=usage


def estimate_tokens(messages):
    # Heuristic with margin for English/Thai mixed evidence, NOT a token upper bound.
    # Ollama's actual prompt_eval_count remains the authoritative observation.
    return math.ceil(sum(len(m['content'].encode('utf-8')) + 64 for m in messages)/2) + 64


def check_budget(messages, max_tokens=768):
    if not isinstance(max_tokens,int) or not 1 <= max_tokens <= 1024:
        raise ValueError('Output reserve must be 1..1024 tokens')
    estimate = estimate_tokens(messages)
    budget=min(INPUT_BUDGET,CONTEXT_WINDOW-max_tokens-SAFETY_RESERVE)
    if estimate > budget:
        raise ContextBudgetExceeded(f'Context budget exceeded: heuristic estimate {estimate} > {budget}; '
                         'required evidence is retained; shorten the question or knowledge sections')
    return {'method':'utf8-bytes-divided-by-two-plus-framing-heuristic',
            'estimated_input_tokens':estimate,'input_budget':budget,
            'context_window':CONTEXT_WINDOW,'output_reserve':max_tokens,
            'safety_reserve':SAFETY_RESERVE,'message_count':len(messages),
            'input_utf8_bytes':sum(len(m['content'].encode('utf-8')) for m in messages),
            'exact_token_count':False}
