# Context engineering — measured Context v2

Controlled local experiment on Qwen3.5:9b, Spark and HDFS. Protocols were recorded
before their runs. Both arms use mandatory RAG. This is not a fresh holdout or an
independent evaluation of general context-rot prevention.

## Actual results

| Measure | Managed | Unfiltered control |
|---|---:|---:|
| Controlled trials (3 exposed tasks) | 21 | 21 |
| Correct result | 21 | 8 |
| Budget rejection before any model call | 0 | 9 |
| Budget rejection after model work started | 0 | 3 |
| Trials that ever called the model | 21 | 12 |
| Correct among trials that called model | 21 | 8 |
| Other unsuccessful trials | 0 | 1 |
| Incorrect executed result delivered | 0 | 0 |
| Selected ID/text retained verbatim | 100% | 100% |
| Actual prompt token range, observed calls | 2188–2484 | 2188–2895 |
| Unique evidence packet hashes | 3 | 21 |

Ordinary exposed regression: **20/20 correct**.
Actual unit suite: **31 passed** (context-v2-unit-tests.log).
All predeclared Context v2 checks: **PASS**.

Background lengths were 0/3000/12000 characters. Evidence appeared at front/middle/end
of the packet. A fixed shuffled order produced 42 trials:21 in each arm.

## What changed

- Selected RAG facts and original task constraints remain intact, with packet hashes
  and deduplication/conflict checks. Production uses the validated evidence formatting.
- Caller-marked nonessential background is omitted before inference in managed mode.
- Repairs retain the original task/facts and latest SQL/citations/short error, without
  old explanations or full Spark plans. 50 repairs are a unit simulation, not 50 model turns.
- Oversized required input is stopped rather than silently truncating it or retrying
  the same impossible request. The trace distinguishes a preflight stop from a call
  already made before a postflight violation or later repair budget stop.
- Model token counts, budget margins and evidence assembly are visible in the trace/UI.

## Negative result retained

The first candidate stripped metadata and changed evidence serialization. All selected
fact text was retained, and stress trials passed, but exposed regression fell to 18/20.
That representation was not adopted as the default. After preserving the prior
representation, the repeated regression returned to 20/20. A single small experiment
does not establish which individual formatting change caused the difference.
Raw V1 report: context-v1-9d66b9e8b1ab45c7bef19fabaf693ae4.json.

## Interpretation and remaining weaknesses

These results support a narrow claim: selecting context and bounding repair state
can prevent budget-related failures in this controlled setting while preserving the
tested ordinary task behavior. They do not show that model-internal context rot has
been solved. Optional noise was labeled by the caller; noise inside required facts
was not tested. Managed packet position becomes identical after noise is removed:
the 21 managed trials are repetitions of 3 packets, not21 independent long-context tasks.

The 6000-token preflight estimate remains heuristic and overestimates many observed
requests. Budget rejection therefore does not prove the original text could not fit
the 8192-token model window. Actual served prompts in this run were below 3000 tokens;
this does not test model behavior near the full window. Post-generation counters do
not guarantee detection of server-side truncation. Exact model/template-matched
tokenization, harder retained-noise tests and independent cases remain future work.

Do not present the overall managed/unfiltered success gap as a pure model reasoning
or context-rot improvement: most control losses are application budget policy stops.
Raw report admitted_count means no budget block at any stage; use the separately
reported initial-call and repair-block populations above to avoid selection bias.

## Reproduce

Stop the web service to free Spark worker resources, then run:

```powershell
docker compose run --rm --no-deps --use-aliases spark-job --master spark://spark-master:7077 --conf spark.driver.host=spark-job --conf spark.driver.bindAddress=0.0.0.0 --conf spark.executor.memory=512m /app/jobs/evaluate_context.py
```

The current source and covered pre-run fingerprints match context-v2-fc31fe03f55a442ba0c39f9969c72d7b.json.
Hashes cover the files mounted into Spark-job; UI assets are verified separately.
Original frozen v2.4 scores are historical; current source includes this extension.
See [design and limits](../docs/CONTEXT_ENGINEERING.md), context-quality-summary.json,
and evaluation/context_protocol_v2.json. Replay results must retain their own source
fingerprints; a protocol replay with changed code is not the original experiment.
