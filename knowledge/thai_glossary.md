# Versioned RAG evidence v2

## policy.period
For sales, orders, AOV, purchasing/return/cancellation counts or repeat rates, require an explicit time period or an explicit request for the entire available dataset. If missing (เช่น ยอดขายรวมเท่าไร), ASK which period, never silently use all data. Observed min/max timestamps and data-quality metadata questions may inspect the whole dataset. For ambiguous best customers / ลูกค้าดีที่สุด, ASK for metric and period/snapshot.

## policy.availability
Use observed_min_timestamp/observed_max_timestamp from the passed build manifest. Outside observed dates means UNAVAILABLE, not automatically zero. Label partial periods. No costs, margins, measured profit, campaign outcomes/uplift, or future measured sales exist. For กำไร / profit / campaign uplift, explain missing evidence instead of generating a numeric answer. Do not infer unsupported facts or introduce unrequested filters.

## policy.snapshot
This policy applies ONLY to customer_summary snapshot questions, NOT to orders or sales_lines transaction queries. Count distinct purchasing customers for a month from orders without a snapshot restriction. The manifest as_of_date identifies the ONLY built customer_summary snapshot. Never query another snapshot and interpret empty rows as its distribution: explain it is unavailable. Snapshot 2011-12-01 uses purchases strictly before that date within the 180-day window. For a customer_summary snapshot question require a snapshot date and check availability.

## policy.provenance
Source: UCI Online Retail II, DOI 10.24432/C5CG6D, CC BY 4.0. Source lines and exact duplicates are retained, not deduplicated. Build report contains duplicate counts and source archive/CSV hashes. Results describe historical observations under this duplicate policy, not current business activity.
