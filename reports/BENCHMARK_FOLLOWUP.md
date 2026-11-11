# SQL evaluation and faithfulness audit

The 200-question development bank was run with Spark local mode, the existing
HDFS data, OPA, and the local Ollama model before the SQL contract changes.

| Measure | Overall | Thai | English |
|---|---:|---:|---:|
| SQL result matches separately executed Gold SQL | 144/160 | 71/80 | 73/80 |
| Formula response matches expected formula | 24/24 | 12/12 | 12/12 |
| Clarifies when expected | 16/16 | 8/8 | 8/8 |

Of the 16 SQL cases that did not pass, 7 stopped after a failure, 6 asked an
unnecessary clarification, and 3 returned results that differed from Gold SQL.
The first set of 16 newly authored prompts scored 11/16 before the fixes.

After changes to ranking, day buckets, projected columns and invoice population,
that same set scored **16/16** on retest. A separately prepared set of 12 new
prompts scored **11/12** (Thai 5/6, English 6/6). The remaining failure was an
incorrect model review rejection of combining a country filter with anonymous
invoices. The 200-question benchmark was not rerun after these changes.

The new sets were written for this project. Each underlying SQL task appears in
Thai and English. They are small samples, and the first set became a regression
set once used to guide fixes. The follow-up run used the same runtime inputs as
the regression rerun. The 44 focused Python tests passed.

The separate [faithfulness evidence audit](FAITHFULNESS_EVIDENCE_AUDIT.md) found
that the explanation judge detected **2 of 8 unsupported statements** and
passed all 8 supported statements. This is a check of the judge on 16 controls,
not an estimate of the Agent's hallucination rate. Raw traces and case-level
results remain local. [Offline summary](evaluation-scores.html)
