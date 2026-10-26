# Context engineering

The agent treats context as a bounded input that must retain the selected business
definitions and user constraints. This reduces avoidable context growth; it does
not establish a general solution to context rot inside the model.

## What the runtime does

1. Retrieve selected metric, schema, syntax and policy sections through mandatory RAG.
2. Preserve the validated model-facing JSON representation, including metadata,
   while independently hashing the selected ID/full-text sequence for auditing.
   An earlier metadata-stripping candidate preserved the facts but regressed task
   accuracy; preserving representation avoids assuming shorter is always better.
   Exact duplicate IDs are deduplicated; conflicting bodies for the same ID are
   rejected. Selected evidence is not summarized or silently truncated.
3. Exclude caller-marked optional, nonauthoritative background in managed mode.
   This does not detect arbitrary irrelevant or malicious text inside a selected
   evidence section. The production UI currently supplies no optional background.
4. Check a heuristic input estimate against 6000 tokens, an 8192 context setting,
   output reserve and 1024 safety reserve. Oversized required input is blocked before
   generation, with a reason; retrying the identical oversized prompt is avoided.
5. For a repair, preserve the original question and evidence plus only the latest
   SQL, citations, grain and short first error line. Old explanations and Spark plans
   do not accumulate. This compaction does not rewrite the question or business facts.
6. Record actual Ollama prompt_eval_count/eval_count for successful calls. A detected
   post-generation reserve violation blocks execution and records the model call.

The estimate remains heuristic. Actual counts are observed after inference, so they
cannot prove that server-side truncation did not occur before generation. There is
no claim of exact tokenizer preflight or arbitrary long-conversation memory.

## Controlled evaluation

Protocols: evaluation/context_protocol_v1.json and context_protocol_v2.json, each
declared before observing its run. V1 regressed exposed task accuracy to 18/20;
the revised V2 preserves evidence formatting and requires no regression against
the 20/20 exposed reference. These are development/repeated-case experiments.
Both strategies use RAG and the same current model, SQL guard, evidence
review and selected facts. This is not a RAG versus no-RAG comparison.

- Managed: lossless selected-evidence packet, optional background omitted.
- Unfiltered control: the same selected-evidence packet plus all optional background.
- Three previously exposed task cases: invoice count, repeat fraction and customer
  ranking. Gold SQL executes separately on real Spark and is never supplied to the model.
- Background sizes 0/3000/12000 characters; selected evidence at front/middle/end of
  the packet. Zero-background trials use one position; 42 controlled trials.
- A fixed shuffled order reduces a simple order effect. It does not remove model
  nondeterminism, caching effects or the limitations of a single local machine.

The report separates budget rejection, correctness after admission, actual input
tokens, estimate error, evidence retention, unique packet hashes and latency.
Packet hashes verify the full selected ID/text sequence; source bodies are retained
verbatim. The 20-case exposed v6 regression also checks ordinary task behavior.

Important interpretation: managed inputs become identical across background positions
when that background is removed. They are repeated trials of three managed packets,
not 21 independent tests that the model can recover facts anywhere in long context.
If the unfiltered control is rejected by its budget, that is an admission-policy
effect, not evidence of a model reasoning failure or a context-rot event.

## What would support stronger claims

- More independent questions, users, business metrics and unseen schema families.
- Repeated trials with uncertainty estimates, rather than a single small matrix.
- Actual token lengths closer to the context limit, multiple context windows and
  language mixes; compare only admitted inputs when measuring model degradation.
- Noise or conflicting evidence *inside* selected sections, where whole-background
  removal cannot solve the problem. Define which source is authoritative in advance.
- A tokenizer and chat-template implementation verified against the serving model,
  before calling preflight token counts exact.

## Sources

- Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
  Conceptual guidance on selecting context and compaction; not validation of Qwen.
- Ollama, [API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md).
  Response token counters are measurements of the served request, not independent
  certification that its original input was complete.

Actual results belong in reports/CONTEXT_REPORT.md after the runtime finishes.
Do not substitute this design description for a completed experiment.

Both experiments are now complete; reports/CONTEXT_REPORT.md records actual results.
The original V1 packing module is retained in docs/experiments/ with a byte hash
matching its pre-run fingerprint. The current production default is Context v2.
