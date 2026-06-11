---
name: supply-chain-offender-analysis
description: "Methodology and key findings for the /app supply chain quality-offender task (answer in /app/answer.json, scripts in /app/work/)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 71b22d81-3f23-47e5-a1ea-b9f9686e4497
---

Solved 2026-06-11. The /app dataset (365 days, 10 stores, 30 products, 60 producers) reconstructs exactly: wholesaler = per-product FIFO, suppliers enqueue in daily receipt sequence, stores served in store sequence, same-day; store sales consume FIFO before that day's delivery arrives. All 3,650 TOTAL_DELIVERED_UNITS matched with zero error (see /app/work/parse_and_simulate.py).

Key non-obvious findings:
- Rejection events are frequent and small (~half of demand-residual variance), so single-event detection is hopeless; the staged 14-day recovery shows up only in aggregate. Empirical kernel at lags 1-14 ≈ (1, 1.04, 1.01, .51, .45, .37, .33, then ~.07) — flatter tail than the spec's 0.8/0.5/0.2 reductions.
- Residual autocorrelation (0.40 at lag 1) is fully explained by the kernel's own ACF — not drift.
- Inference: per-product GLS (AR-whitened) regression of demand residuals on kernel-convolved per-producer sold units, run on both the demand-sum channel and the visit-count channel, combined (null-calibrated; max positive combined z over 728 pairs was +2.85). Confirmed = combined z ≤ -4.0 → 83 pairs.
- Circular-shift placebo tests are invalid here (breaking co-occurrence of producer exposures creates a positive bias); calibrate from the observed positive tail instead.
