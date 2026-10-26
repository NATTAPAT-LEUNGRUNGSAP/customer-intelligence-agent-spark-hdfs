# Presentation and delivery requirements — 26 October 2026

Implementation update: local web application and the 14-slide presentation now
exist. Current verified v2.4 results are in DELIVERY_REPORT.md and
delivery-quality-summary.json: 20/20 new supported-family combinations correct,
Recall@6=100%, MRR@6=0.8917, nDCG@6=0.8934, warm p95=5.43s. This is a small
developer-authored benchmark, not external validation. Earlier v2.2/v2.3 failed
gates and all raw evidence remain intact. Git is initialized; publication awaits
user browser sign-in. Read the following sections as the original requirements,
not an assertion that implemented items are still pending.

This brief records the revised user requirements. Planned features below are not
implemented or verified merely because they appear in this document.

## Presentation sequence

1. Problem and users: business users need customer/sales answers without manually
   writing Spark SQL; explain the historical dataset and supported questions.
2. Project capabilities and value: sales, invoice counts, purchasing customers,
   repeat rate, RFM segments and high-value analysis. Do not claim measured
   productivity gains, real-time data, or unsupported business outcomes.
3. Architecture/framework: Docker, Spark master/two workers, HDFS NameNode/two
   DataNodes, versioned Parquet, knowledge corpus, local Ollama and Python agent
   harness. Describe the actual custom implementation; distinguish conceptual
   layers from third-party frameworks that are not installed.
4. Workflow: ingest/reconcile/build; question/retrieve/policy/generate/validate/
   review/execute; bounded repair; clarification and failure exits.
5. Application demonstration: planned browser UI accepts a question and shows
   status, result table, explanation, SQL, evidence and failures. CLI already exists.
6. Harness components: Data Dictionary/KM; RAG; semantic mapping/ontology;
   pre/post tool contracts; policy enforcement; self-correction; context engineering;
   evaluation. Label each implemented, partial, planned or optional research.
   OPA/Rego is not implemented; formal ontology and cross-organization schema
   matching are not implemented. Do not present them as completed features.
7. Evaluation methods and actual results, followed by failures and limitations.
8. Reproduction and GitHub delivery, then remaining work.

MongoDB Policy Storage and Churn Prediction/Campaign Recommendation are removed
from the presentation and delivery scope. Historical archived reports remain intact.
RAG remains mandatory in every evaluation; do not reinstate a no-RAG comparison.

## Current measured evidence

Use FINAL_REPORT.md and rag-v2-quality-summary.json as the source for slide figures:
Recall@6 97.5%, MRR@6 0.8792, nDCG@6 0.8410; Spark answers 19/20;
clarification and citation validity 100%; retrieval p95 13.25 ms;
warm-query p95 5.62 seconds. Full CLI sample 15.25 seconds includes Spark startup.
Show metric definitions, denominators, gates and the small authored sample size.
Citation validity is structural, not proof that every statement follows from evidence.
Show the anonymous-customer ranking failure and exposed regression failures.
Previous failures remain evidence; results apply to frozen v2.1, not future changes.

Planned measurements: business result contracts; repair success by failure type;
input/output token usage and context overflow; context distractor/length stress;
UI/backend integration and failures. No measured scores exist for these additions yet.

## Context engineering assessment

It is relevant: selecting and organizing useful context is already essential to
this RAG agent. Context rot is degradation in use of information as context grows;
increasing the context window alone is not evidence of solving it.

Implemented: atomic stable-ID evidence, ranked top six plus mandatory policies,
schema/syntax dependency expansion, actual schemas and dataset bounds, fresh
question messages, bounded three-attempt feedback, 8192 context setting and capped
generation. Review calls use separate messages; query result rows are not appended
to generation history. Retrieval logs context characters, not token counts.

Gaps: no explicit preflight token budget, no overflow detection, no retry-history
compaction, no measured long-context robustness, no conversational memory manager.
Three attempts limit growth but do not guarantee prompts fit 8192 tokens.

Next design: budget question/instructions/schema/evidence/history with output reserve;
preserve mandatory policies and required schema; remove duplicate/irrelevant optional
content; stop clearly if required context cannot fit. Keep current repair state and
useful error feedback. Start UI with independent questions; display history separately
instead of automatically injecting the entire conversation.

Measure with RAG always enabled: token use, required-evidence retention, answer
accuracy and latency across controlled distractor lengths/positions and retry counts.
Keep model/questions fixed within comparisons; separate stress tests from fresh
holdout claims. Do not claim context rot is solved until those tests run.

Reference: Anthropic, Effective context engineering for AI agents:
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
This provides conceptual guidance, not validation of this project's Qwen model.

## Application acceptance requirements

Deliver a runnable local web application connected to the actual agent and Spark,
not a mock response screen. Required: question entry, example questions, available
data dates/snapshot, busy/error/clarification states, result table, SQL/evidence
details and trace identifier. Keep technical details in an expandable view.
Serialize Spark requests initially; prevent duplicate submits and show resource state.
Backend owns the approved manifest and configuration; browser cannot select arbitrary
paths, submit shell commands or bypass SQL validation. UI success means actual
integration checks, not merely that the page renders. Production hosting is separate.

## GitHub acceptance requirements

Current directory is not yet a Git repository and has no configured remote.
Deliver source, setup instructions, architecture, evaluation methodology, selected
evidence, dependency versions and UI instructions. Exclude credentials, local config,
model weights, downloaded dataset archives, caches, volumes and bulky runtime logs.
Document dataset attribution/license and reproducible acquisition; review report data
before publication. Set up appropriate automated tests; distinguish CI unit checks
from local GPU/Spark runtime results. Choose repository owner/name/visibility before
remote creation or upload. No GitHub publication has occurred.

## Remaining delivery order

1. Correct known SQL semantics and add meaningful regression/result checks.
2. Add token budgeting/telemetry and context stress evaluation.
3. Build web application using the existing guarded agent path and verify real flow.
4. Freeze changed runtime, rerun checks, and use fresh cases for new holdout claims.
5. Prepare GitHub repository and reproducible setup; verify clean checkout workflow.
6. Produce slides/demo from verified evidence and rehearse before 9 November.

The slide deck and web application are required deliverables but are not created
by this brief. Do not count plans as implementation or test results.
