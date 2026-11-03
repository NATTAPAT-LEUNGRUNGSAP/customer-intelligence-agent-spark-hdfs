# Shared input guard

Latest platform validation and deployment details are in [platform-improvements.md](platform-improvements.md); the 113-test count below describes this input-guard milestone.

`jobs/input_guard.py` is the single validation boundary used by web, MCP, CLI and direct `answer()` callers. All accept nonempty strings of at most **2,000 raw Python characters**, including whitespace before trimming. Validated text is trimmed. The CLI rejects invalid input before importing or starting Spark; the core rejects it before retrieval or model calls. Web HTTP request byte limits and context-token budgets remain independent protections.

The guard rejects unsupported control characters, known role-delimiter tokens and explicit English/Thai attempts to override system instructions or bypass SQL guards, OPA, security checks or review. Unicode NFKC variants are checked without rewriting the user's analytics question. Ordinary requests such as excluding anonymous customers or asking what OPA is remain allowed.

The generator and reviewer now receive the same explicit rule treating user text, retrieval, proposals and tool observations as untrusted data. A keyword/pattern filter cannot detect every paraphrase, encoding or indirect injection. It does not prove semantic resistance or replace the AST allowlist, OPA, reviewer, bounded query runtime or result contracts. Those controls remain mandatory even if a malicious question evades input detection.

Validation: 113/113 unit tests passed on the Linux Spark image (106 prior tests plus seven input-boundary tests). Checks cover the 2,000/2,001 boundary, English/Thai and Unicode overrides, ordinary analytics, no downstream calls on rejected web/core/MCP input, CLI rejection without Spark and unsafe SQL blocked even when the generator is compromised. See the delivery's `input-guard-validation.json` and logs for current live MCP validation. Earlier paired accuracy/timing results in the live-validation report predate this guard change and are historical, not a rebenchmark of this revision.

This change is local; it does not replace the already running web deployment or publish to GitHub.
