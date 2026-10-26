# RAG-required delivery plan — 26 October to 9 November 2026

Scope: Spark + HDFS + Online Retail II + mandatory RAG + one SQL-generating agent.
Current checkpoint: v2.4 web application implemented; 25 unit tests passed;
new v6 combinations 20/20 correct and both retrieval/end-to-end gates passed.
14-slide presentation exported. Source prepared in local Git; remote publication
awaits user browser sign-in. See DELIVERY_REPORT.md; do not use older pending-state
sentences below as the current status.
Revised required deliverables: local web application, presentation and GitHub
repository. Include context engineering assessment, token budgeting and context
stress measurements. Details and presentation order: PRESENTATION_BRIEF.md.
MongoDB Policy Storage and Churn Prediction/Campaign Recommendation are excluded.
UI and GitHub delivery are pending; current passing v2.1 metrics do not verify them.
Acceptance is measured RAG quality, not a with/without-RAG comparison.
Original frozen benchmark remains historical evidence; exposed cases are regression only.

| Dates (Asia/Bangkok) | Deliverable | Acceptance evidence |
|---|---|---|
| 26–28 Oct | Runtime baseline/data | 2 DataNodes, 2 workers, replication 2, real HDFS smoke, UCI hashes and reconciliation |
| 29–31 Oct | Retrieval quality | Stable knowledge IDs, bilingual ranking, labeled qrels, Recall/MRR/nDCG/context coverage |
| 1–3 Nov | Grounded SQL + application | Correct known failures, context budgeting/stress checks, real web UI to guarded Spark flow |
| 4 Nov | Quality freeze | Development/regression results, published gates, code/corpus/model fingerprints |
| 5–6 Nov | New RAG holdout | 20 fresh questions, Spark result accuracy, evidence metrics, warm p95 and separate load time |
| 7–8 Nov | GitHub + slides + rehearsal/buffer | Clean setup verification, repository publication, architecture/workflow/evaluation slides and real UI demo; retain failures |
| 9 Nov | Submission | Runnable web application, GitHub source and presentation with measured results and honest limitations |

Minimum project gates: Recall@6 >=95%, MRR@6 >=85%, nDCG@6 >=80%, retrieval p95 <=50 ms;
end-to-end accuracy >=90%, clarification/citation validity 100%, relevant evidence citation
>=95%, warm query p95 <=20 seconds. Exact machine-readable gates are in evaluation/.
These are project acceptance thresholds, not industry certification.

If a gate fails, improve on development cases and create another fresh final set if
the previous holdout was exposed. Never silently retune and relabel a rerun as untouched.
No HDFS volume deletion; keep source archives and hashes. Small sample size, local-only
security, soft cancellation and residual model semantic errors remain limitations.
