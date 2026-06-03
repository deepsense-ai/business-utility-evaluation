# Machinery Malfunctions

## Description

This task models a factory where technicians service machines, hidden faults can persist after maintenance, and later quality rejections must be traced back through machine timelines rather than simple aggregates.

The analytical goal is to identify confirmed technicians whose maintenance repeatedly caused downstream rejected batches, then return every affected product for those confirmed technicians.

## Task Design

### Difficulty and Signal Strength

The task is made easier or harder mostly by how strongly maintenance-introduced faults affect later quality outcomes and by how clearly responsible technicians stand out from confounding noise.

The main knobs are in the tiered technician structure (`obvious`, `moderate`, `borderline`, `decoy`, `normal`), whose sizes are set by `n_obvious_risky_technicians`, `n_moderate_risky_technicians`, `n_borderline_risky_technicians`, and `n_decoy_technicians`. Each risky tier defines its fault-introduction rate (`*_intro_base_*`), its targeted `*_risk_boost`, how many fault classes and machine types it harms, and how readily it removes faults (`*_removal_base_*`). Wider gaps between the obvious tier and the normal baseline make the task easier; shrinking those rates or shifting technicians toward the borderline tier makes the responsible technicians blend in.

Two features drive the hardest cases:

- The **borderline** tier is designed to produce evidence near the confirmation thresholds, so correct solutions must count linked rejected batches and distinct work orders precisely.
- The **decoy** tier never introduces faults (`decoy_intro_base = 0.0`); it only looks suspicious because assignment is biased toward high-load days via `decoy_load_excess_weight_boost`. Raising this boost makes count-based solutions more likely to flag innocent technicians.

Fault visibility is controlled by `fault_effect_min` / `fault_effect_max`, tier introduction probabilities, and `fault_intro_probability_cap`. Larger effects and higher introduction rates make rejected batches easier to attribute; smaller effects force the solver to separate maintenance faults from natural variation. The confounding background is controlled by base defect rates, rejection thresholds, daily conditions, job difficulty, operator experience, and load effects. `inspection_delay_min` / `inspection_delay_max` decouple production day from inspection day, so attribution must use production timing. Fault persistence is shaped by `minimum_fault_age_before_random_removal`, `corrective_fault_removal_bonus`, `partial_repair_severity_multiplier`, and fault-class persistence. `affected_products_per_fault_min` / `affected_products_per_fault_max` control how product-specific faults are, penalizing the assumption that every product on a faulty machine is affected.

### Expected Solution Approach

The intended path is to reconstruct the per-machine maintenance timeline and attribute rejected batches causally rather than by correlation:

- extract each work order's machine, technician, and completion time from the service reports,
- link each technician's work orders to the machines and time windows they govern (after completion, before the next service on that machine),
- map batches to those windows using production day, not inspection day,
- connect batches to products and rejection outcomes,
- separate fault-driven rejections from natural variation, operators, load, difficulty, and factory-wide conditions,
- confirm technicians only on repeated, multi-work-order evidence, then report every product with at least one linked rejected batch for those confirmed technicians.

## Generation

### Local Generation

From the repository root:

```bash
uv run python harbor/tasks/machinery_malfunctions/environment/generate.py
```

To also emit the deterministic answer locally:

```bash
MACHINERY_MALFUNCTIONS_ANSWER_PATH=/tmp/machinery_malfunctions_gt.json \
uv run python harbor/tasks/machinery_malfunctions/environment/generate.py
```

When `CONFIG["write_debug_outputs"]` and/or `CONFIG["write_seed_info"]` are enabled, the generator writes those hidden artifacts into `./debug/` relative to the current working directory.

### Generated Outputs

The environment exposes these public files directly in `/app/`:

- `products.csv`
- `machines.csv`
- `technicians.csv`
- `operators.csv`
- `maintenance_work_orders.csv`
- `production_jobs.csv`
- `machine_assignment_log.csv`
- `production_batches.csv`
- `quality_inspections.csv`
- `operator_shift_log.csv`
- `daily_factory_conditions.csv`
- `raw_service_reports/`

The correct solution requires reconstructing maintenance intervals, matching later production on the same machine, accounting for inspection delay, and filtering out natural defect noise and misleading post-maintenance correlations.
