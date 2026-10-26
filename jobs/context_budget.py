"""Conservative prompt-size control; estimate is not a tokenizer guarantee."""
import json
import math

CONTEXT_WINDOW = 8192
INPUT_BUDGET = 6000


def estimate_tokens(messages):
    # Heuristic with margin for English/Thai mixed evidence, NOT a token upper bound.
    # Ollama's actual prompt_eval_count remains the authoritative observation.
    return math.ceil(sum(len(m['content'].encode('utf-8')) + 64 for m in messages)/2) + 64


def check_budget(messages, max_tokens=768):
    estimate = estimate_tokens(messages)
    if estimate > INPUT_BUDGET:
        raise ValueError(f'Context budget exceeded: heuristic estimate {estimate} > {INPUT_BUDGET}; '
                         'required evidence is retained; shorten the question or knowledge sections')
    return {'method':'utf8-bytes-divided-by-two-plus-framing-heuristic',
            'estimated_input_tokens':estimate,'input_budget':INPUT_BUDGET,
            'context_window':CONTEXT_WINDOW,'output_reserve':max_tokens,
            'exact_token_count':False}
