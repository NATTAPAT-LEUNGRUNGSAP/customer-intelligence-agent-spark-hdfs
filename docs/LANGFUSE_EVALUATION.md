# Faithfulness and correctness evaluation

Run the bilingual benchmark first, then score its saved answers offline.
Gold SQL stays in the evaluation bank. The Agent and the faithfulness judge
never receive the gold query or gold rows.

| Score | What it compares |
|---|---|
| `faithfulness` | Supported factual claims divided by all claims the judge identifies in the displayed Agent explanation. The judge sees the selected RAG evidence, executed SQL, and returned Spark rows. |
| `has_ungrounded_claim` | At least one unsupported or contradicted claim in the explanation. |
| `sql_result_correctness` | Whether the live Spark result matches the independent Gold SQL result in the source benchmark. |
| `case_correctness` | The benchmark verdict for any case type, including formulas and clarification. |

Both metrics use a 0–1 scale. The report averages faithfulness across answers
with a score and divides matching SQL results by the number of SQL cases for
correctness. The summary includes the denominators for each language and overall.
An empty denominator produces no score.

The judge runs in local Ollama and defaults to `qwen2.5:7b`, a different model
from the answering model. A faithfulness score is an automated judgment of the
explanation, so manually audit claims and failures before interpreting it as a
hallucination rate. A result can be faithful to its returned rows yet incorrect
against Gold SQL. Missing context, oversized inputs, no factual claims, and
failed judge calls are reported separately. Always read scored coverage alongside
the mean. A previous benchmark report measures the source that produced it.

From the repository root, with Spark, HDFS, OPA, and Ollama running:

```powershell
docker compose --profile jobs run --rm --no-deps --use-aliases analytics-job --master local[2] /app/jobs/evaluate_bilingual.py --ids pair002-th pair002-en pair011-th pair011-en pair016-th pair016-en pair026-th pair026-en --output /app/reports/langfuse-pilot-source.json
& "C:/Users/Admin/anaconda3/python.exe" scripts/evaluate_hallucination.py --report reports/langfuse-pilot-source.json --output reports/langfuse-pilot-scores.json
```

Omit `--ids` to evaluate the full 200-question development bank. This is an
exposed benchmark, so use independently prepared questions for holdout claims.
Saved benchmark reports can contain customer IDs and should remain local.

For Langfuse, install the optional dependency and set `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` in the environment. Export sends
only case IDs, labels, model, source digest, and scores. The questions, customer
IDs, SQL, evidence, returned rows, and judge's claim text stay local.

```powershell
& "C:/Users/Admin/anaconda3/python.exe" -m pip install -r requirements-langfuse.txt
& "C:/Users/Admin/anaconda3/python.exe" scripts/evaluate_hallucination.py --upload-report reports/langfuse-pilot-scores.json
```

In Langfuse, find traces named `offline-analytics-evaluation`, filter by
`run_id`, and compare the two scores by language or question family.
[Langfuse score documentation](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk)

## Local pilot

On 11 November 2026, a live Spark local-mode run over HDFS, with OPA and
`qwen3.5:9b`, matched Gold SQL in all 8 cases (4 Thai, 4 English). The
`qwen2.5:7b` judge scored 5 of the 8 explanations and marked all 22 extracted
claims supported. Three answers returned a result table without prose and
received no faithfulness score. A separate two-example control scored the
supported answer 1.0 and the deliberately wrong amount 0.0. This pilot covers
four question families from the exposed development bank. It does not establish
the model's overall hallucination rate.

Raw input and score reports are local under `reports/langfuse-*.json`. Three
unit tests passed, including a mocked SDK export that checks raw claim text is
excluded. Live Langfuse upload remains unverified pending a configured project.

To render a completed score report as an offline table by language and question
family, run:

```powershell
& "C:/Users/Admin/anaconda3/python.exe" scripts/render_evaluation_report.py reports/langfuse-pilot-scores.json reports/evaluation-scores.html
```

## Full benchmark and judge calibration

- Run `evaluate_bilingual.py` without `--ids` for the 200-item development
  bank. Run `scripts/summarize_benchmark.py REPORT BANK` to report SQL,
  formula, and clarification separately. It verifies the bank hash and checks
  that every expected question has one recorded outcome.
- Generate the 16-item project-authored SQL holdout with
  `scripts/prepare_evaluation_holdout.py reports/langfuse-heldout-bank.json`.
  Mount that file over `/app/evaluation/bilingual_200.json` in a separate
  analytics-job container. The Agent receives only each question and its
  usual RAG evidence. Use the holdout bank path when summarizing the results.
- Run `scripts/calibrate_faithfulness.py SOURCE OUTPUT --manifest MANIFEST`
  against the 40-question source report. The controls contain both supported
  and deliberately changed statements. A positive label means at least one
  claim is unsupported or contradicted. Keep the confusion counts and
  unscored examples separate from the Agent's SQL accuracy. These controls
  were authored within this project and are not independently reviewed by
  humans.

The 16-control run with `qwen2.5:7b` returned TP 2, FN 6, TN 8, FP 0,
and no unscored controls. It caught 2/8 unsupported statements while passing
8/8 supported statements. These are synthetic controls, so the 25% recall
applies to this set only. In particular, a perfect score from this judge
should not be presented as evidence that the Agent made no unsupported claims.
A blinded worksheet for an independent check is stored locally in
`.private/langfuse-human-review.tsv`. Reviewers can fill `review_verdict`
with `supported`, `unsupported`, or `uncertain` and leave their reasoning in
`review_note`. The join key and judge output are stored separately.
