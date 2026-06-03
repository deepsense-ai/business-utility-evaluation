---
name: supply-chain-quality-task
description: How to identify confirmed quality-offender producers from the /app supply-chain simulation outputs
metadata: 
  node_type: memory
  type: project
  originSessionId: 7eac2eb6-d0b3-486c-ab10-cfa6be3f1f27
---

Task in `/app`: infer per-product `confirmed` quality-offender producers (60 producers, 30 products, 10 stores, 365 days) from raw outputs only. Answer written to `/app/answer.json`.

Key non-obvious facts (no quality field exists anywhere — it must be inferred from the demand trajectory):
- `sales_log.csv` rows are **individual consumers** per (Day,Store,Product); aggregate `Reported_Demand`.
- Supply chain is **fully deterministic & reconstructable**: wholesaler uses brutal first-come (producer order = `raw_wholesaler_receipts` DAILY_SEQUENCE_NO; store order = `raw_wholesaler_store_receipts`). Same-day allocation (no carryover) reproduces every `TOTAL_DELIVERED_UNITS` checksum exactly. Store FIFO is **sell-before-receive** (day 1 sold=0 despite delivery).
- Calendar effect is shared across stores per product (summer dip + year-end rise) → remove via cross-store median; recovery is store-specific.
- Detection method that worked: per-product **NNLS regression** of demand-reduction `1-R` on each producer's lagged exposure (share of consumed units convolved with staged recovery weights 0.8/0.5/0.2 for lags 1-3/4-7/8-14). Must **de-bias** baseline jointly (single-pass median absorbs ~half the signal → false negatives, esp. for chronic producers). Validate with circular-shift permutation FWER + cross-store-half replication + confounder-controlled partial lag (peak at lag 1-3, ~0 by lag 15 = genuine recovery vs calendar artifact).
- Final criterion: de-biased beta > FWER-99% permutation threshold AND replicates in both independent store-halves. Gave 67 producer-product pairs; coherent producer-level quality structure (PR_3/PR_15/PR_36/PR_50/PR_54 bad across 3 products; 16 producers never flagged).
