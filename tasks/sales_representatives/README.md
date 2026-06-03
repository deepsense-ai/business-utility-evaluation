# Sales Representatives

## Description

This scenario models a company that sells products directly to a franchise network of stores and employs regional sales representatives to improve in-store execution.

The main analytical target is to identify the hidden underperforming sales representatives from public operational data. Bad representatives are not labeled in the CSV files; their effect is visible through worse visit completion, weaker shelf execution, poorer order support, more delivery delays, and worse downstream sales and stockout behavior.

## Task Design

### Difficulty and Signal Strength

The task is made easier or harder mostly by changing how strongly the hidden representative profile affects observable store outcomes.

The most important parameters are in `CONFIG["rep_profiles"]`. They define the behavioral gap between good and bad representatives. Wider gaps make the task easier; narrower gaps make the task harder.

The profile parameters affect visit completion, order delays, under-ordering, planogram compliance, display setup, POS material placement, shelf placement, and audit quality. These are the strongest direct knobs for how visibly bad representatives differ from good ones in operational data.

`CONFIG["sales_model"]["rep_influence_strength"]` controls how much representative-driven execution differences affect sales. Increasing it makes the bad representatives easier to identify from sales outcomes; decreasing it makes the signal weaker and forces the analysis to rely more on visits, audits, orders, stockouts, and execution records.

Visit-mixing parameters also affect difficulty:

- Lower `planned_visit_probability` makes regular coverage less clean and therefore weakens attribution.
- Higher `unplanned_visit_probability` adds more noisy visits and makes representative responsibility less direct.
- Higher `other_rep_visit_share_range` means more visits are performed by non-primary same-region representatives, which makes it harder to attribute store outcomes to a single representative.

Together, these parameters determine whether the model can mostly attribute outcomes to one representative or must reason from patterns across many visits, orders, audits, stockouts, and sales.

## Generation

### Local Generation

From the task directory:

```bash
cd tasks/sales_representatives/sales_representatives
uv run python generation/generate.py
```

The generator uses `pandas` and `numpy`. Running it rewrites managed outputs when `CONFIG["output"]["cleanup_outputs"] = True`.

Generated artifacts are written to the following locations:

- `generate.py`: canonical simulator implementation and global `CONFIG`
- `for_llm/`: generated public CSV files for analysis
- `additional/`: generated helper files and task artifacts
- `additional/prompt.txt`: downstream analytical prompt
- `additional/answer.txt`: answer key with the hidden bad representative IDs
- `additional/simulation_output.txt`: optional human-readable simulation trace, including action-level events, controlled by `CONFIG["output"]["write_simulation_output"]`

The dataset is fully reproducible given a fixed `CONFIG["seed"]` and RNG configuration.

### Generated Outputs

The generator writes static business entities as one indexed CSV each:

- `retail_chain_001.csv`
- `product_category_001.csv`
- `store_001.csv`
- `sales_rep_001.csv`
- `product_001.csv`
- `promotion_001.csv`

The generator writes time-series tables split by simulation month:

- `store_traffic_001.csv` through `store_traffic_012.csv`
- `store_visit_001.csv` through `store_visit_012.csv`
- `shelf_audit_001.csv` through `shelf_audit_012.csv`
- `inventory_status_001.csv` through `inventory_status_012.csv`
- `sales_transaction_001.csv` through `sales_transaction_012.csv`
- `store_order_001.csv` through `store_order_012.csv`
- `store_promotion_001.csv` through `store_promotion_012.csv`
- `competitor_audit_001.csv` through `competitor_audit_012.csv`

Only domain tables are written to `for_llm/`. Action-level records such as `TRAFFIC`, `STORE_VISIT`, `AUDIT`, `STORE_ORDER`, `DELIVERY`, and `SALES_DAY` are written to `additional/simulation_output.txt`, not to CSV, when enabled with `CONFIG["output"]["write_simulation_output"]`.

It is also possible to generate Key Performance Indicators (KPI, `kpi_daily`) data implemented in the simulator, but it is disabled by default with `CONFIG["output"]["write_kpi_daily"]`.

## Data Model

### Public Schema

 Public CSVs include the representative IDs and activity records, but not the profile labels.

### Hidden Data

Representatives have hidden `good` or `bad` profiles.

The hidden profile affects:

- visit completion probability
- order delay probability
- under-order probability and under-order severity
- planogram compliance probability
- endcap and checkout display probability
- promo stand setup probability
- POS materials probability
- eye-level placement probability
- audit quality and resulting facings

## Simulation Mechanics

### Simulation Setup

Default scale is controlled by the top-level `CONFIG` in `generation/generate.py`:

- 365 simulated days starting on `2025-01-01`
- 500 stores in 20 regions
- 100 sales representatives, 5 per region
- 10 hidden bad representatives, at most 1 per region
- 24 products across 4 product categories
- 3 store types: `large_scale_store`, `discount`, and `local_shop`
- 3 locations: `city`, `town`, and `village`; village stores are restricted to local shops

Stores have a hidden primary representative from their own region. Visit plans also assign some visits to other representatives from the same region.

### Representative Behavior

Completed visits generate shelf audits for a store-type-dependent product sample. These audits update the store/product execution state: facings, shelf level, display flags, POS materials, promo stands, and planogram compliance. Those execution states then affect later sales.

### Sales Drivers

The sales model includes store and market factors:

- store type and store size
- location
- daily customer count
- product category demand rate
- promotions and discount depth
- competitor pressure and competitor promotions
- stock availability

It also includes representative-driven execution factors:

- facings versus product target facings
- shelf level, especially eye-level placement
- endcap and checkout display
- promo stand and POS material setup
- planogram compliance

### Sales Calculation

Sales are calculated per store, product, and day.

First, the simulator builds a baseline expected demand:

```text
baseline_demand =
    base_daily_traffic / 100
    * product_base_units_per_100_customers
    * store_type_sales_factor
    * location_sales_factor
    * store_size_factor
```

Each day, baseline demand is adjusted by current traffic:

```text
traffic_scaled_baseline =
    baseline_demand * (customer_count / base_daily_traffic) ** traffic_alpha
```

Then the simulator applies execution, shelf facings, promotion, and competitor effects:

```text
demand_mean =
    traffic_scaled_baseline
    * execution_multiplier
    * facings_multiplier
    * promotion_multiplier
    * competitor_multiplier
```

Actual demand is sampled from a Poisson distribution:

```text
demand_units ~ Poisson(demand_mean)
```

Realized sales are inventory-capped:

```text
units_sold = min(demand_units, stock_units)
revenue = units_sold * effective_price
```

If a product is out of stock at the start of the sales step, sold units for that store/product/day are zero.

Promotions use a sigmoid response to discount depth, plus an extra display bonus when the promotion is actively supported in-store. Competitor activity reduces demand through daily pressure and product-level competitor promotion events.

The non-linearities are introduced to better reflect the real-world behavior, but also to better challenge the models, as they typically assume linear relationships.

### Inventory and Orders

Stores start with inventory based on expected demand and target stock days. Each day:

- delivered orders increase stock
- sales reduce stock
- inventory status is recorded
- stores reorder when available stock plus pending orders falls below a store-type reorder threshold

Order quantities target a configurable number of stock days. Bad representatives have a higher chance of delayed orders and under-ordering, which increases stockout risk.

## Validation Notes

The generator performs internal checks before finishing:

- bad representative count matches config
- no region has more than the configured maximum bad representatives
- village stores are only local shops
- each visited store has same-region non-primary representative visits within the configured share range
