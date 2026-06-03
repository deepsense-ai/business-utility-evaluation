from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    missing = exc.name or "pandas/numpy"
    raise SystemExit(
        f"Missing dependency {missing!r}. Install project dependencies with `uv sync` "
        "or run this generator with `uv run python generation/generate.py`."
    ) from exc


PROJECT_NAME = "sales representatives"

CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "seed": 42,
    "rng_bit_generator": "PCG64",
    "simulation_start_date": "2025-01-01",
    "simulation_days": 365,
    "scale": {
        "n_regions": 20,
        "n_stores": 500,
        "n_reps": 100,
        "reps_per_region": 5,
        "n_bad_reps": 10,
        "max_bad_reps_per_region": 1,
    },
    "catalog": {
        "n_categories": 4,
        "n_products": 24,
        "category_names": ["Beverages", "Snacks", "Personal Care", "Household"],
        "brands": [
            "Aster",
            "BrightWay",
            "Cedar",
            "DailyCo",
            "EverGood",
            "NorthStar",
        ],
        "package_types": ["bottle", "can", "box", "bag", "multipack", "pouch"],
        "unit_price_range_by_category": {
            "Beverages": [1.49, 4.99],
            "Snacks": [1.19, 5.49],
            "Personal Care": [3.49, 14.99],
            "Household": [2.99, 18.99],
        },
        "base_units_per_100_customers_by_category": {
            "Beverages": [0.75, 1.65],
            "Snacks": [0.55, 1.25],
            "Personal Care": [0.12, 0.42],
            "Household": [0.10, 0.35],
        },
    },
    "stores": {
        "store_type_mix": {
            "large_scale_store": 0.24,
            "discount": 0.36,
            "local_shop": 0.40,
        },
        "location_mix_by_store_type": {
            "large_scale_store": {"city": 0.72, "town": 0.28},
            "discount": {"city": 0.45, "town": 0.55},
            "local_shop": {"city": 0.24, "town": 0.48, "village": 0.28},
        },
        "store_size_sqm_range_by_type": {
            "large_scale_store": [1800, 5200],
            "discount": [600, 1700],
            "local_shop": [70, 380],
        },
        "traffic_range_by_type_location": {
            "large_scale_store": {
                "city": [1900, 4200],
                "town": [1250, 2800],
            },
            "discount": {
                "city": [900, 2100],
                "town": [650, 1650],
            },
            "local_shop": {
                "city": [260, 850],
                "town": [170, 620],
                "village": [70, 310],
            },
        },
        "store_type_sales_factor": {
            "large_scale_store": 1.08,
            "discount": 1.00,
            "local_shop": 0.86,
        },
        "location_sales_factor": {"city": 1.12, "town": 1.00, "village": 0.78},
        "size_sales_lift": 0.22,
    },
    "traffic": {
        "weekday_multipliers": [0.92, 0.94, 0.98, 1.02, 1.12, 1.24, 0.88],
        "annual_amplitude": 0.10,
        "annual_peak_day": 330,
        "daily_noise_cv": 0.13,
    },
    "visits": {
        "visit_frequency_days_by_store_type": {
            "large_scale_store": 6,
            "discount": 10,
            "local_shop": 17,
        },
        "planned_visit_probability": 0.7,
        "unplanned_visit_probability": 0.3,
        "other_rep_visit_share_range": [0.30, 0.40],
        "duration_minutes_by_store_type": {
            "large_scale_store": [65, 120],
            "discount": [45, 90],
            "local_shop": [25, 55],
        },
        "audit_products_by_store_type": {
            "large_scale_store": 11,
            "discount": 8,
            "local_shop": 5,
        },
        "visit_types": ["merchandising", "audit", "order_support", "promo_setup"],
    },
    "rep_profiles": {
        "good": {
            "visit_completion_probability": 0.94,
            "order_delay_probability": 0.08,
            "under_order_probability": 0.06,
            "under_order_factor_range": [0.90, 0.95],
            "planogram_compliance_probability": 0.86,
            "endcap_display_probability": 0.45,
            "checkout_display_probability": 0.38,
            "promo_stand_probability": 0.6,
            "pos_materials_probability": 0.75,
            "eye_level_probability": 0.56,
            "audit_quality_multiplier": 1.12,
        },
        "bad": {
            "visit_completion_probability": 0.92,
            "order_delay_probability": 0.11,
            "under_order_probability": 0.08,
            "under_order_factor_range": [0.85, 0.93],
            "planogram_compliance_probability": 0.81,
            "endcap_display_probability": 0.43,
            "checkout_display_probability": 0.36,
            "promo_stand_probability": 0.58,
            "pos_materials_probability": 0.73,
            "eye_level_probability": 0.54,
            "audit_quality_multiplier": 1.09,
        },
    },
    "sales_model": {
        "rep_influence_strength": 0.15,
        "traffic_alpha": 0.82,
        "display_lift": 0.18,
        "placement_lift": 0.22,
        "planogram_lift": 0.16,
        "facings_log_min_multiplier": 0.45,
        "facings_log_max_multiplier": 1.65,
        "promotion_max_lift": 0.42,
        "promotion_sigmoid_midpoint": 0.14,
        "promotion_sigmoid_steepness": 35.0,
        "promotion_display_bonus_by_store_type": {
            "large_scale_store": 0.08,
            "discount": 0.15,
            "local_shop": 0.24,
        },
        "competitor_pressure_strength": 0.35,
        "competitor_promotion_penalty": 0.3,
        "stockout_sales_multiplier": 0.0,
        "minimum_execution_multiplier": 0.52,
        "maximum_execution_multiplier": 1.85,
    },
    "inventory_orders": {
        "initial_stock_days": {
            "large_scale_store": 9.0,
            "discount": 8.0,
            "local_shop": 10.0,
        },
        "reorder_threshold_days": {
            "large_scale_store": 3.7,
            "discount": 3.2,
            "local_shop": 4.4,
        },
        "target_stock_days": {
            "large_scale_store": 9.5,
            "discount": 8.2,
            "local_shop": 11.5,
        },
        "base_order_lead_time_days": [1, 4],
        "extra_delay_days": [1, 3],
        "minimum_order_units": 3,
    },
    "promotions": {
        "n_promotions": 12,
        "duration_days_range": [16, 34],
        "products_per_promotion": [2, 5],
        "store_fraction_range": [0.15, 0.34],
        "discount_range": [0.08, 0.26],
        "promotion_types": ["price_cut", "bundle", "endcap_feature", "loyalty_coupon"],
    },
    "competitors": {
        "competitor_brands": ["ValueMax", "PrimeChoice", "NovaGoods", "QuickBuy"],
        "daily_pressure_beta": [2.1, 6.0],
        "promotion_probability": 0.06,
        "location_pressure_factor": {"city": 1.12, "town": 1.00, "village": 0.72},
        "audit_count_range": [1, 3],
        "audit_facings_range": [4, 26],
    },
    "output": {
        "csv_split": "monthly",
        "write_kpi_daily": False,
        "write_simulation_output": True,
        "float_rounding": 4,
        "cleanup_outputs": True,
    },
}


STATIC_SCHEMAS: dict[str, list[str]] = {
    "retail_chain": ["retail_chain_id", "chain_name", "country", "headquarters_region"],
    "product_category": ["category_id", "category_name", "department"],
    "store": [
        "store_id",
        "retail_chain_id",
        "store_name",
        "store_type",
        "region",
        "location",
        "store_size_sqm",
    ],
    "sales_rep": ["rep_id", "first_name", "last_name", "region", "hire_date"],
    "product": [
        "product_id",
        "category_id",
        "sku",
        "product_name",
        "brand",
        "package_type",
        "unit_price",
    ],
    "promotion": [
        "promotion_id",
        "promotion_name",
        "promotion_type",
        "start_date",
        "end_date",
    ],
}


MONTHLY_SCHEMAS: dict[str, list[str]] = {
    "store_traffic": ["traffic_id", "store_id", "traffic_date", "customer_count"],
    "store_visit": [
        "visit_id",
        "store_id",
        "rep_id",
        "visit_start",
        "visit_end",
        "duration_minutes",
        "visit_type",
        "planned_visit",
        "completed_visit",
    ],
    "shelf_audit": [
        "audit_id",
        "visit_id",
        "product_id",
        "facings",
        "shelf_width_cm",
        "shelf_level",
        "endcap_display",
        "checkout_display",
        "promo_stand",
        "pos_materials",
        "planogram_compliance",
    ],
    "inventory_status": [
        "inventory_id",
        "store_id",
        "product_id",
        "inventory_date",
        "stock_units",
        "out_of_stock",
    ],
    "sales_transaction": [
        "sales_id",
        "store_id",
        "product_id",
        "sales_date",
        "units_sold",
        "revenue",
        "promo_price",
    ],
    "store_order": [
        "order_id",
        "store_id",
        "product_id",
        "order_date",
        "ordered_units",
        "delivery_date",
    ],
    "store_promotion": [
        "store_promotion_id",
        "store_id",
        "promotion_id",
        "product_id",
        "display_active",
        "discounted_price",
    ],
    "competitor_audit": [
        "competitor_audit_id",
        "visit_id",
        "competitor_brand",
        "competitor_facings",
        "competitor_promotion",
    ],
    "kpi_daily": [
        "kpi_id",
        "store_id",
        "rep_id",
        "kpi_date",
        "sales_uplift",
        "share_of_shelf",
        "execution_score",
        "out_of_stock_rate",
    ],
}


def active_monthly_schemas(config: dict[str, Any]) -> dict[str, list[str]]:
    schemas = dict(MONTHLY_SCHEMAS)
    if not bool(config["output"].get("write_kpi_daily", False)):
        schemas.pop("kpi_daily", None)
    return schemas


FIRST_NAMES = [
    "Alex",
    "Blake",
    "Casey",
    "Dana",
    "Elliot",
    "Finley",
    "Harper",
    "Jordan",
    "Morgan",
    "Parker",
    "Quinn",
    "Riley",
    "Rowan",
    "Skyler",
    "Taylor",
    "Avery",
    "Jamie",
    "Kendall",
    "Logan",
    "Reese",
]

LAST_NAMES = [
    "Adams",
    "Bennett",
    "Carter",
    "Diaz",
    "Evans",
    "Foster",
    "Garcia",
    "Hayes",
    "Ivanov",
    "Jensen",
    "Kowalski",
    "Lewis",
    "Miller",
    "Nowak",
    "Ortiz",
    "Patel",
    "Reed",
    "Silva",
    "Turner",
    "Wright",
]

SHELF_LEVELS = np.array(["bottom", "middle", "eye_level", "top"])
SHELF_LEVEL_SCORE = np.array([0.18, 0.48, 1.00, 0.62])


def native_json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.Period):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def details_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=native_json_default)


def as_python_set(values: set[int]) -> str:
    if not values:
        return "set()"
    return "{" + ", ".join(str(value) for value in sorted(values)) + "}"


def choose_from_weights(
    rng: np.random.Generator,
    labels: list[str],
    weights_by_label: dict[str, float],
    size: int,
) -> np.ndarray:
    weights = np.array([weights_by_label[label] for label in labels], dtype=float)
    weights = weights / weights.sum()
    return rng.choice(np.array(labels), size=size, p=weights)


def inclusive_int(rng: np.random.Generator, low: int, high: int, size: int | None = None) -> Any:
    return rng.integers(low, high + 1, size=size)


def build_rng(config: dict[str, Any]) -> np.random.Generator:
    bit_generator = str(config.get("rng_bit_generator", "PCG64"))
    seed = int(config["seed"])
    if bit_generator != "PCG64":
        raise ValueError(f"Unsupported rng_bit_generator={bit_generator!r}; expected 'PCG64'.")
    return np.random.Generator(np.random.PCG64(seed))


def validate_config(config: dict[str, Any]) -> None:
    scale = config["scale"]
    expected_reps = int(scale["n_regions"]) * int(scale["reps_per_region"])
    if int(scale["n_reps"]) != expected_reps:
        raise ValueError(
            f"n_reps must equal n_regions * reps_per_region ({expected_reps}); "
            f"got {scale['n_reps']}."
        )
    max_bad = int(scale["n_regions"]) * int(scale["max_bad_reps_per_region"])
    if int(scale["n_bad_reps"]) > max_bad:
        raise ValueError(f"n_bad_reps={scale['n_bad_reps']} exceeds max allowed {max_bad}.")
    if int(config["catalog"]["n_products"]) < int(config["catalog"]["n_categories"]):
        raise ValueError("n_products must be at least n_categories.")


class OutputManager:
    def __init__(self, generation_dir: Path, config: dict[str, Any]) -> None:
        self.output_dir = Path(os.environ.get("SALES_REP_OUTPUT_DIR", Path.cwd())).resolve()
        self.answer_path_env = os.environ.get("SALES_REP_ANSWER_PATH", "").strip()
        self.float_rounding = int(config["output"]["float_rounding"])
        self.monthly_schemas = active_monthly_schemas(config)
        self.write_simulation_output = False
        self.output_file: Any | None = None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if config["output"]["cleanup_outputs"]:
            self.cleanup()

    def cleanup(self) -> None:
        for path in sorted(self.output_dir.glob("*.csv")):
            path.unlink()
        for filename in ["answer.txt", "simulation_output.txt"]:
            path = self.output_dir / filename
            if path.exists():
                path.unlink()
        if self.answer_path_env:
            answer_path = Path(self.answer_path_env).resolve()
            if answer_path.exists():
                answer_path.unlink()

    def initialize_monthly_files(self, month_indices: list[int]) -> None:
        for table_name, columns in self.monthly_schemas.items():
            for month_index in month_indices:
                path = self.output_dir / f"{table_name}_{month_index:03d}.csv"
                pd.DataFrame(columns=columns).to_csv(path, index=False)

    def write_static(self, table_name: str, dataframe: pd.DataFrame) -> None:
        columns = STATIC_SCHEMAS[table_name]
        prepared = self.prepare_dataframe(dataframe, columns)
        prepared.to_csv(self.output_dir / f"{table_name}_001.csv", index=False)

    def append_monthly(
        self,
        table_name: str,
        month_index: int,
        rows: list[dict[str, Any]] | pd.DataFrame,
    ) -> None:
        if isinstance(rows, pd.DataFrame):
            if rows.empty:
                return
            dataframe = rows
        elif rows:
            dataframe = pd.DataFrame.from_records(rows)
        else:
            return

        if table_name not in self.monthly_schemas:
            return

        columns = self.monthly_schemas[table_name]
        prepared = self.prepare_dataframe(dataframe, columns)
        path = self.output_dir / f"{table_name}_{month_index:03d}.csv"
        prepared.to_csv(path, mode="a", header=False, index=False)

    def prepare_dataframe(self, dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        prepared = dataframe.copy()
        for column in columns:
            if column not in prepared.columns:
                prepared[column] = ""
        prepared = prepared[columns]
        float_columns = prepared.select_dtypes(include=["floating"]).columns
        if len(float_columns) > 0:
            prepared.loc[:, float_columns] = prepared.loc[:, float_columns].round(self.float_rounding)
        return prepared

    def write_output(self, line: str = "") -> None:
        if self.output_file is None:
            return
        self.output_file.write(line + "\n")

    def write_steps(self, steps: list[dict[str, Any]]) -> None:
        if not self.write_simulation_output:
            return
        for step in steps:
            source_table = step.get("source_table", "")
            source_id = step.get("source_id", "")
            source = f"{source_table}[{source_id}]" if source_table and source_id != "" else source_table
            self.write_output(
                "ACTION "
                f"step_id={step['step_id']} "
                f"step_date={step['step_date']} "
                f"action_type={step['action_type']} "
                f"store_id={step.get('store_id', '')} "
                f"rep_id={step.get('rep_id', '')} "
                f"product_id={step.get('product_id', '')} "
                f"source={source} "
                f"details={step.get('details_json', '{}')}"
            )

    def write_answer(self, bad_rep_ids: set[int]) -> None:
        if not self.answer_path_env:
            return
        payload = {"answer": sorted(bad_rep_ids)}
        with open(Path(self.answer_path_env) / "answer.txt", "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, separators=(",", ":"))
            file_handle.write("\n")

    def close(self) -> None:
        if self.output_file is not None:
            self.output_file.close()


def build_month_index(dates: pd.DatetimeIndex) -> tuple[dict[pd.Timestamp, int], list[int]]:
    periods = pd.Series(dates.to_period("M")).drop_duplicates().tolist()
    period_to_index = {period: index + 1 for index, period in enumerate(periods)}
    date_to_month = {pd.Timestamp(date): period_to_index[date.to_period("M")] for date in dates}
    return date_to_month, list(period_to_index.values())


def build_regions(config: dict[str, Any]) -> list[str]:
    return [f"Region_{index:02d}" for index in range(1, int(config["scale"]["n_regions"]) + 1)]


def build_reps(
    config: dict[str, Any],
    rng: np.random.Generator,
    regions: list[str],
    start_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, set[int]]:
    scale = config["scale"]
    reps_per_region = int(scale["reps_per_region"])
    n_reps = int(scale["n_reps"])
    rep_ids = np.arange(1, n_reps + 1)
    rep_regions = np.repeat(np.array(regions), reps_per_region)

    bad_region_indices = sorted(
        int(region_index)
        for region_index in rng.choice(np.arange(len(regions)), size=int(scale["n_bad_reps"]), replace=False)
    )
    bad_rep_ids: set[int] = set()
    for region_index in bad_region_indices:
        region_rep_ids = rep_ids[rep_regions == regions[region_index]]
        chosen = int(rng.choice(region_rep_ids))
        bad_rep_ids.add(chosen)

    hire_offsets = inclusive_int(rng, 240, 3300, size=n_reps)
    first_names = rng.choice(np.array(FIRST_NAMES), size=n_reps)
    last_names = rng.choice(np.array(LAST_NAMES), size=n_reps)

    private_reps = pd.DataFrame(
        {
            "rep_id": rep_ids,
            "first_name": first_names,
            "last_name": last_names,
            "region": rep_regions,
            "hire_date": (start_date - pd.to_timedelta(hire_offsets, unit="D")).date.astype(str),
            "is_bad": [int(rep_id) in bad_rep_ids for rep_id in rep_ids],
        }
    )
    public_reps = private_reps.drop(columns=["is_bad"])
    return public_reps, private_reps, bad_rep_ids


def build_stores(
    config: dict[str, Any],
    rng: np.random.Generator,
    regions: list[str],
    reps_private: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    scale = config["scale"]
    n_stores = int(scale["n_stores"])
    n_regions = int(scale["n_regions"])

    stores_per_region = np.full(n_regions, n_stores // n_regions, dtype=int)
    stores_per_region[: n_stores % n_regions] += 1
    store_regions = np.repeat(np.array(regions), stores_per_region)

    store_types = choose_from_weights(
        rng,
        list(config["stores"]["store_type_mix"]),
        config["stores"]["store_type_mix"],
        n_stores,
    )
    locations = []
    for store_type in store_types:
        location_weights = config["stores"]["location_mix_by_store_type"][str(store_type)]
        locations.append(
            str(
                choose_from_weights(
                    rng,
                    list(location_weights),
                    location_weights,
                    1,
                )[0]
            )
        )
    locations_array = np.array(locations)

    sizes = np.empty(n_stores, dtype=int)
    base_traffic = np.empty(n_stores, dtype=float)
    for index, (store_type, location) in enumerate(zip(store_types, locations_array, strict=True)):
        size_low, size_high = config["stores"]["store_size_sqm_range_by_type"][str(store_type)]
        traffic_low, traffic_high = config["stores"]["traffic_range_by_type_location"][str(store_type)][
            str(location)
        ]
        sizes[index] = int(inclusive_int(rng, int(size_low), int(size_high)))
        base_traffic[index] = float(rng.uniform(float(traffic_low), float(traffic_high)))

    primary_rep_ids = np.empty(n_stores, dtype=int)
    for region in regions:
        store_positions = np.flatnonzero(store_regions == region)
        region_rep_ids = reps_private.loc[reps_private["region"] == region, "rep_id"].to_numpy()
        shuffled_reps = rng.permutation(region_rep_ids)
        for offset, store_position in enumerate(store_positions):
            primary_rep_ids[store_position] = int(shuffled_reps[offset % len(shuffled_reps)])

    other_visit_share_low, other_visit_share_high = config["visits"]["other_rep_visit_share_range"]
    store_ids = np.arange(1, n_stores + 1)
    store_names = [
        f"{region.replace('_', ' ')} {store_type.replace('_', ' ').title()} {store_id:03d}"
        for store_id, region, store_type in zip(store_ids, store_regions, store_types, strict=True)
    ]

    private_stores = pd.DataFrame(
        {
            "store_id": store_ids,
            "retail_chain_id": 1,
            "store_name": store_names,
            "store_type": store_types,
            "region": store_regions,
            "location": locations_array,
            "store_size_sqm": sizes,
            "base_daily_traffic": base_traffic,
            "primary_rep_id": primary_rep_ids,
            "other_rep_visit_share": rng.uniform(
                float(other_visit_share_low),
                float(other_visit_share_high),
                size=n_stores,
            ),
        }
    )
    public_stores = private_stores.drop(
        columns=["base_daily_traffic", "primary_rep_id", "other_rep_visit_share"]
    )
    return public_stores, private_stores


def build_catalog(
    config: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    catalog = config["catalog"]
    category_names = catalog["category_names"][: int(catalog["n_categories"])]
    category_rows = [
        {"category_id": index, "category_name": name, "department": "Core Grocery"}
        for index, name in enumerate(category_names, start=1)
    ]
    categories = pd.DataFrame(category_rows)

    product_rows: list[dict[str, Any]] = []
    hidden_rows: list[dict[str, Any]] = []
    for product_id in range(1, int(catalog["n_products"]) + 1):
        category_id = ((product_id - 1) % len(category_names)) + 1
        category_name = category_names[category_id - 1]
        brand = str(rng.choice(np.array(catalog["brands"])))
        package_type = str(rng.choice(np.array(catalog["package_types"])))
        price_low, price_high = catalog["unit_price_range_by_category"][category_name]
        demand_low, demand_high = catalog["base_units_per_100_customers_by_category"][category_name]
        unit_price = round(float(rng.uniform(float(price_low), float(price_high))), 2)
        product_name = f"{brand} {category_name[:-1] if category_name.endswith('s') else category_name} {product_id:02d}"
        product_rows.append(
            {
                "product_id": product_id,
                "category_id": category_id,
                "sku": f"SKU-{product_id:04d}",
                "product_name": product_name,
                "brand": brand,
                "package_type": package_type,
                "unit_price": unit_price,
            }
        )
        hidden_rows.append(
            {
                "product_id": product_id,
                "base_units_per_100_customers": float(rng.uniform(float(demand_low), float(demand_high))),
                "target_facings": float(rng.uniform(5.0, 12.0)),
                "competitor_sensitivity": float(rng.uniform(0.85, 1.25)),
            }
        )

    return categories, pd.DataFrame(product_rows), pd.DataFrame(hidden_rows)


def build_promotions(
    config: dict[str, Any],
    rng: np.random.Generator,
    dates: pd.DatetimeIndex,
    stores_private: pd.DataFrame,
    reps_private: pd.DataFrame,
    products: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    promotions_config = config["promotions"]
    n_promotions = int(promotions_config["n_promotions"])
    simulation_days = len(dates)
    anchor_days = np.linspace(0, simulation_days - 35, n_promotions).astype(int)
    promo_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []

    rep_bad_by_id = reps_private.set_index("rep_id")["is_bad"].to_dict()
    product_ids = products["product_id"].to_numpy()
    store_ids = stores_private["store_id"].to_numpy()
    unit_price_by_product = products.set_index("product_id")["unit_price"].to_dict()

    store_promotion_id = 1
    for promotion_id, anchor_day in enumerate(anchor_days, start=1):
        jitter = int(rng.integers(-8, 9))
        start_day = int(np.clip(anchor_day + jitter, 0, simulation_days - 8))
        duration_low, duration_high = promotions_config["duration_days_range"]
        duration = int(inclusive_int(rng, int(duration_low), int(duration_high)))
        end_day = int(min(start_day + duration - 1, simulation_days - 1))
        promotion_type = str(rng.choice(np.array(promotions_config["promotion_types"])))
        promotion_name = f"{promotion_type.replace('_', ' ').title()} Campaign {promotion_id:02d}"
        promo_rows.append(
            {
                "promotion_id": promotion_id,
                "promotion_name": promotion_name,
                "promotion_type": promotion_type,
                "start_date": dates[start_day].date().isoformat(),
                "end_date": dates[end_day].date().isoformat(),
                "start_day": start_day,
                "end_day": end_day,
            }
        )

        products_low, products_high = promotions_config["products_per_promotion"]
        selected_products = rng.choice(
            product_ids,
            size=int(inclusive_int(rng, int(products_low), int(products_high))),
            replace=False,
        )
        store_fraction_low, store_fraction_high = promotions_config["store_fraction_range"]
        n_assigned_stores = max(1, int(round(len(store_ids) * rng.uniform(store_fraction_low, store_fraction_high))))
        selected_stores = rng.choice(store_ids, size=n_assigned_stores, replace=False)
        discount_low, discount_high = promotions_config["discount_range"]
        discount = float(rng.uniform(discount_low, discount_high))

        for store_id in selected_stores:
            rep_id = int(stores_private.loc[stores_private["store_id"] == store_id, "primary_rep_id"].iloc[0])
            profile_key = "bad" if bool(rep_bad_by_id[rep_id]) else "good"
            profile = config["rep_profiles"][profile_key]
            display_active = bool(rng.random() < float(profile["promo_stand_probability"]))
            for product_id in selected_products:
                unit_price = float(unit_price_by_product[int(product_id)])
                assignment_rows.append(
                    {
                        "store_promotion_id": store_promotion_id,
                        "store_id": int(store_id),
                        "promotion_id": promotion_id,
                        "product_id": int(product_id),
                        "display_active": display_active,
                        "discounted_price": round(unit_price * (1.0 - discount), 2),
                        "start_day": start_day,
                        "end_day": end_day,
                    }
                )
                store_promotion_id += 1

    promotions = pd.DataFrame(promo_rows)
    assignments = pd.DataFrame(assignment_rows)
    return promotions, assignments


def initialize_execution_state(
    config: dict[str, Any],
    rng: np.random.Generator,
    stores_private: pd.DataFrame,
    reps_private: pd.DataFrame,
    products_hidden: pd.DataFrame,
) -> dict[str, np.ndarray]:
    n_stores = len(stores_private)
    n_products = len(products_hidden)
    rep_bad_by_id = reps_private.set_index("rep_id")["is_bad"].to_dict()
    store_bad = np.array(
        [bool(rep_bad_by_id[int(rep_id)]) for rep_id in stores_private["primary_rep_id"].to_numpy()],
        dtype=bool,
    )
    good = config["rep_profiles"]["good"]
    bad = config["rep_profiles"]["bad"]

    planogram_prob = np.where(
        store_bad[:, None],
        float(bad["planogram_compliance_probability"]),
        float(good["planogram_compliance_probability"]),
    )
    endcap_prob = np.where(
        store_bad[:, None],
        float(bad["endcap_display_probability"]),
        float(good["endcap_display_probability"]),
    )
    checkout_prob = np.where(
        store_bad[:, None],
        float(bad["checkout_display_probability"]),
        float(good["checkout_display_probability"]),
    )
    promo_prob = np.where(
        store_bad[:, None],
        float(bad["promo_stand_probability"]),
        float(good["promo_stand_probability"]),
    )
    pos_prob = np.where(
        store_bad[:, None],
        float(bad["pos_materials_probability"]),
        float(good["pos_materials_probability"]),
    )
    eye_prob = np.where(
        store_bad[:, None],
        float(bad["eye_level_probability"]),
        float(good["eye_level_probability"]),
    )

    target_facings = products_hidden["target_facings"].to_numpy(dtype=float)
    facings_noise = rng.normal(1.0, 0.22, size=(n_stores, n_products))
    quality_multiplier = np.where(
        store_bad[:, None],
        float(bad["audit_quality_multiplier"]),
        float(good["audit_quality_multiplier"]),
    )
    facings = np.maximum(1, np.rint(target_facings[None, :] * facings_noise * quality_multiplier)).astype(int)

    shelf_level = np.where(
        rng.random((n_stores, n_products)) < eye_prob,
        2,
        rng.choice(np.array([0, 1, 3]), size=(n_stores, n_products), p=[0.22, 0.54, 0.24]),
    )

    return {
        "facings": facings,
        "shelf_level": shelf_level.astype(int),
        "endcap_display": rng.random((n_stores, n_products)) < endcap_prob,
        "checkout_display": rng.random((n_stores, n_products)) < checkout_prob,
        "promo_stand": rng.random((n_stores, n_products)) < promo_prob,
        "pos_materials": rng.random((n_stores, n_products)) < pos_prob,
        "planogram_compliance": rng.random((n_stores, n_products)) < planogram_prob,
    }


def build_baseline_demand(
    config: dict[str, Any],
    stores_private: pd.DataFrame,
    products_hidden: pd.DataFrame,
) -> np.ndarray:
    store_type_factor = stores_private["store_type"].map(config["stores"]["store_type_sales_factor"]).to_numpy(float)
    location_factor = stores_private["location"].map(config["stores"]["location_sales_factor"]).to_numpy(float)

    size_factor = np.ones(len(stores_private), dtype=float)
    for store_type, indexes in stores_private.groupby("store_type").groups.items():
        positions = np.array(list(indexes), dtype=int)
        size_values = stores_private.iloc[positions]["store_size_sqm"].to_numpy(float)
        low, high = config["stores"]["store_size_sqm_range_by_type"][str(store_type)]
        normalized = (size_values - float(low)) / max(float(high) - float(low), 1.0)
        size_factor[positions] = 1.0 + float(config["stores"]["size_sales_lift"]) * np.clip(normalized, 0, 1)

    base_traffic = stores_private["base_daily_traffic"].to_numpy(float)
    product_rate = products_hidden["base_units_per_100_customers"].to_numpy(float)
    baseline = (
        (base_traffic[:, None] / 100.0)
        * product_rate[None, :]
        * store_type_factor[:, None]
        * location_factor[:, None]
        * size_factor[:, None]
    )
    return np.maximum(baseline, 0.03)


def initialize_inventory(
    config: dict[str, Any],
    rng: np.random.Generator,
    stores_private: pd.DataFrame,
    baseline_demand: np.ndarray,
) -> np.ndarray:
    stock_days = stores_private["store_type"].map(config["inventory_orders"]["initial_stock_days"]).to_numpy(float)
    stock = np.ceil(baseline_demand * stock_days[:, None] * rng.uniform(0.75, 1.25, size=baseline_demand.shape))
    return np.maximum(stock, 1).astype(int)


def build_visit_plan(
    config: dict[str, Any],
    rng: np.random.Generator,
    dates: pd.DatetimeIndex,
    stores_private: pd.DataFrame,
    reps_private: pd.DataFrame,
    visit_frequency: np.ndarray,
    visit_offsets: np.ndarray,
) -> list[list[tuple[int, bool, int, bool]]]:
    n_stores = len(stores_private)
    raw_visits_by_store: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    for day_index in range(len(dates)):
        scheduled_store_indices = np.flatnonzero(day_index % visit_frequency == visit_offsets)
        if len(scheduled_store_indices) > 0:
            scheduled_store_indices = scheduled_store_indices[
                rng.random(len(scheduled_store_indices)) < float(config["visits"]["planned_visit_probability"])
            ]
        unplanned_store_indices = np.flatnonzero(
            rng.random(n_stores) < float(config["visits"]["unplanned_visit_probability"])
        )

        for store_idx in scheduled_store_indices:
            raw_visits_by_store[int(store_idx)].append((day_index, True))
        for store_idx in unplanned_store_indices:
            raw_visits_by_store[int(store_idx)].append((day_index, False))

    rep_ids_by_region = {
        str(region): group["rep_id"].to_numpy(int)
        for region, group in reps_private.groupby("region", sort=False)
    }
    primary_rep_ids = stores_private["primary_rep_id"].to_numpy(int)
    store_regions = stores_private["region"].to_numpy(str)
    other_rep_visit_shares = stores_private["other_rep_visit_share"].to_numpy(float)
    min_share, max_share = config["visits"]["other_rep_visit_share_range"]
    min_share = float(min_share)
    max_share = float(max_share)

    visit_plan_by_day: list[list[tuple[int, bool, int, bool]]] = [[] for _ in range(len(dates))]
    for store_idx in range(n_stores):
        store_visits = raw_visits_by_store.get(store_idx, [])
        total_visits = len(store_visits)
        if total_visits == 0:
            continue

        primary_rep_id = int(primary_rep_ids[store_idx])
        regional_rep_ids = rep_ids_by_region[str(store_regions[store_idx])]
        backup_rep_ids = regional_rep_ids[regional_rep_ids != primary_rep_id]
        target_backup_visits = 0
        if len(backup_rep_ids) > 0:
            min_backup_visits = math.ceil(min_share * total_visits)
            max_backup_visits = math.floor(max_share * total_visits)
            target_backup_visits = int(round(other_rep_visit_shares[store_idx] * total_visits))
            if min_backup_visits <= max_backup_visits:
                target_backup_visits = max(
                    min_backup_visits,
                    min(max_backup_visits, target_backup_visits),
                )
            else:
                target_backup_visits = max(0, min(total_visits, target_backup_visits))

        backup_positions = set()
        if target_backup_visits > 0:
            backup_positions = set(
                rng.choice(np.arange(total_visits), size=target_backup_visits, replace=False).tolist()
            )

        for visit_position, (day_index, planned_visit) in enumerate(store_visits):
            use_backup_rep = visit_position in backup_positions
            rep_id = (
                int(rng.choice(backup_rep_ids))
                if use_backup_rep
                else primary_rep_id
            )
            visit_plan_by_day[day_index].append((store_idx, planned_visit, rep_id, use_backup_rep))

    for daily_visits in visit_plan_by_day:
        rng.shuffle(daily_visits)

    return visit_plan_by_day


def build_active_promotions_by_day(
    assignments: pd.DataFrame,
    stores_private: pd.DataFrame,
    products: pd.DataFrame,
    simulation_days: int,
) -> list[list[tuple[int, int, float, bool, int]]]:
    active_by_day: list[list[tuple[int, int, float, bool, int]]] = [[] for _ in range(simulation_days)]
    store_position = {int(store_id): index for index, store_id in enumerate(stores_private["store_id"].to_numpy())}
    product_position = {int(product_id): index for index, product_id in enumerate(products["product_id"].to_numpy())}
    for row in assignments.itertuples(index=False):
        store_idx = store_position[int(row.store_id)]
        product_idx = product_position[int(row.product_id)]
        for day_index in range(int(row.start_day), int(row.end_day) + 1):
            active_by_day[day_index].append(
                (
                    store_idx,
                    product_idx,
                    float(row.discounted_price),
                    bool(row.display_active),
                    int(row.promotion_id),
                )
            )
    return active_by_day


def make_traffic(
    config: dict[str, Any],
    rng: np.random.Generator,
    stores_private: pd.DataFrame,
    date: pd.Timestamp,
    day_index: int,
) -> np.ndarray:
    traffic_config = config["traffic"]
    base_traffic = stores_private["base_daily_traffic"].to_numpy(float)
    weekday_multiplier = float(traffic_config["weekday_multipliers"][date.weekday()])
    annual_phase = 2.0 * math.pi * ((day_index - int(traffic_config["annual_peak_day"])) / 365.0)
    annual_multiplier = 1.0 + float(traffic_config["annual_amplitude"]) * math.cos(annual_phase)
    mean = base_traffic * weekday_multiplier * annual_multiplier
    noise = rng.normal(1.0, float(traffic_config["daily_noise_cv"]), size=len(stores_private))
    return np.maximum(0, np.rint(mean * noise)).astype(int)


def execution_scores(state: dict[str, np.ndarray], target_facings: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    shelf_scores = SHELF_LEVEL_SCORE[state["shelf_level"]]
    placement_score = np.clip(
        0.55 * shelf_scores
        + 0.25 * state["endcap_display"].astype(float)
        + 0.20 * state["checkout_display"].astype(float),
        0,
        1,
    )
    display_score = np.clip(
        0.50 * state["promo_stand"].astype(float)
        + 0.35 * state["pos_materials"].astype(float)
        + 0.15 * state["endcap_display"].astype(float),
        0,
        1,
    )
    facing_score = np.clip(state["facings"].astype(float) / target_facings[None, :], 0, 1.6)
    execution_score = np.clip(
        0.30 * state["planogram_compliance"].astype(float)
        + 0.25 * display_score
        + 0.25 * placement_score
        + 0.20 * np.clip(facing_score, 0, 1),
        0,
        1,
    )
    return placement_score, display_score, execution_score


def apply_visit_effects(
    config: dict[str, Any],
    rng: np.random.Generator,
    state: dict[str, np.ndarray],
    products_hidden: pd.DataFrame,
    store_idx: int,
    product_indices: np.ndarray,
    profile_key: str,
) -> list[dict[str, Any]]:
    profile = config["rep_profiles"][profile_key]
    target_facings = products_hidden["target_facings"].to_numpy(float)
    updates: list[dict[str, Any]] = []
    for product_idx in product_indices:
        quality_multiplier = float(profile["audit_quality_multiplier"])
        facings = max(1, int(round(target_facings[product_idx] * rng.uniform(0.75, 1.35) * quality_multiplier)))
        eye_level = bool(rng.random() < float(profile["eye_level_probability"]))
        if eye_level:
            shelf_level_idx = 2
        else:
            shelf_level_idx = int(rng.choice(np.array([0, 1, 3]), p=[0.20, 0.58, 0.22]))
        update = {
            "product_idx": int(product_idx),
            "facings": facings,
            "shelf_level_idx": shelf_level_idx,
            "shelf_level": str(SHELF_LEVELS[shelf_level_idx]),
            "endcap_display": bool(rng.random() < float(profile["endcap_display_probability"])),
            "checkout_display": bool(rng.random() < float(profile["checkout_display_probability"])),
            "promo_stand": bool(rng.random() < float(profile["promo_stand_probability"])),
            "pos_materials": bool(rng.random() < float(profile["pos_materials_probability"])),
            "planogram_compliance": bool(rng.random() < float(profile["planogram_compliance_probability"])),
        }
        state["facings"][store_idx, product_idx] = update["facings"]
        state["shelf_level"][store_idx, product_idx] = update["shelf_level_idx"]
        state["endcap_display"][store_idx, product_idx] = update["endcap_display"]
        state["checkout_display"][store_idx, product_idx] = update["checkout_display"]
        state["promo_stand"][store_idx, product_idx] = update["promo_stand"]
        state["pos_materials"][store_idx, product_idx] = update["pos_materials"]
        state["planogram_compliance"][store_idx, product_idx] = update["planogram_compliance"]
        updates.append(update)
    return updates


def build_static_outputs(
    writer: OutputManager,
    categories: pd.DataFrame,
    products: pd.DataFrame,
    stores: pd.DataFrame,
    reps: pd.DataFrame,
    promotions: pd.DataFrame,
) -> None:
    retail_chain = pd.DataFrame(
        [
            {
                "retail_chain_id": 1,
                "chain_name": "Meridian Franchise Stores",
                "country": "United States",
                "headquarters_region": "Region_01",
            }
        ]
    )
    writer.write_static("retail_chain", retail_chain)
    writer.write_static("product_category", categories)
    writer.write_static("store", stores)
    writer.write_static("sales_rep", reps)
    writer.write_static("product", products)
    writer.write_static("promotion", promotions.drop(columns=["start_day", "end_day"]))


def main() -> None:
    validate_config(CONFIG)
    rng = build_rng(CONFIG)
    generation_dir = Path(__file__).resolve().parent
    writer = OutputManager(generation_dir, CONFIG)

    start_date = pd.Timestamp(CONFIG["simulation_start_date"])
    dates = pd.date_range(start=start_date, periods=int(CONFIG["simulation_days"]), freq="D")
    date_to_month, month_indices = build_month_index(dates)
    writer.initialize_monthly_files(month_indices)

    regions = build_regions(CONFIG)
    public_reps, private_reps, bad_rep_ids = build_reps(CONFIG, rng, regions, start_date)
    public_stores, private_stores = build_stores(CONFIG, rng, regions, private_reps)
    categories, products, products_hidden = build_catalog(CONFIG, rng)
    promotions, store_promotions = build_promotions(
        CONFIG,
        rng,
        dates,
        private_stores,
        private_reps,
        products,
    )
    build_static_outputs(writer, categories, products, public_stores, public_reps, promotions)

    for _month_key, month_group in promotions.groupby(promotions["start_date"].str.slice(0, 7), sort=True):
        output_month = date_to_month[pd.Timestamp(month_group["start_date"].iloc[0])]
        promotion_ids = set(month_group["promotion_id"].astype(int))
        rows = store_promotions[store_promotions["promotion_id"].isin(promotion_ids)].drop(
            columns=["start_day", "end_day"]
        )
        writer.append_monthly("store_promotion", output_month, rows)

    n_stores = len(private_stores)
    n_products = len(products)
    store_ids = private_stores["store_id"].to_numpy(int)
    product_ids = products["product_id"].to_numpy(int)
    rep_ids_by_store = private_stores["primary_rep_id"].to_numpy(int)
    store_types = private_stores["store_type"].to_numpy(str)
    locations = private_stores["location"].to_numpy(str)
    unit_prices = products["unit_price"].to_numpy(float)
    target_facings = products_hidden["target_facings"].to_numpy(float)
    competitor_sensitivity = products_hidden["competitor_sensitivity"].to_numpy(float)
    rep_bad_by_id = private_reps.set_index("rep_id")["is_bad"].to_dict()
    store_bad = np.array([bool(rep_bad_by_id[int(rep_id)]) for rep_id in rep_ids_by_store], dtype=bool)

    baseline_demand = build_baseline_demand(CONFIG, private_stores, products_hidden)
    inventory = initialize_inventory(CONFIG, rng, private_stores, baseline_demand)
    pending_units = np.zeros_like(inventory, dtype=int)
    deliveries_by_day: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
    state = initialize_execution_state(CONFIG, rng, private_stores, private_reps, products_hidden)
    active_promotions_by_day = build_active_promotions_by_day(
        store_promotions,
        private_stores,
        products,
        len(dates),
    )

    row_store_idx = np.repeat(np.arange(n_stores), n_products)
    row_product_idx = np.tile(np.arange(n_products), n_stores)
    row_store_ids = store_ids[row_store_idx]
    row_product_ids = product_ids[row_product_idx]

    visit_frequency = np.array(
        [CONFIG["visits"]["visit_frequency_days_by_store_type"][store_type] for store_type in store_types],
        dtype=int,
    )
    visit_offsets = np.array([int(rng.integers(0, max(freq, 1))) for freq in visit_frequency], dtype=int)
    visit_plan_by_day = build_visit_plan(
        CONFIG,
        rng,
        dates,
        private_stores,
        private_reps,
        visit_frequency,
        visit_offsets,
    )

    counters = {
        "traffic_id": 1,
        "visit_id": 1,
        "audit_id": 1,
        "inventory_id": 1,
        "sales_id": 1,
        "order_id": 1,
        "competitor_audit_id": 1,
        "kpi_id": 1,
        "step_id": 1,
    }

    kpi_execution_sum = np.zeros(int(CONFIG["scale"]["n_reps"]) + 1, dtype=float)
    kpi_oos_sum = np.zeros(int(CONFIG["scale"]["n_reps"]) + 1, dtype=float)
    kpi_count = np.zeros(int(CONFIG["scale"]["n_reps"]) + 1, dtype=int)
    total_sales_rows = 0
    total_order_rows = 0
    total_visit_rows = 0
    total_stockout_sales_rows = 0
    visit_count_by_store = np.zeros(n_stores, dtype=int)
    other_rep_visit_count_by_store = np.zeros(n_stores, dtype=int)

    writer.write_output("== Sales Representatives Simulation ==")
    writer.write_output(f"Project: {PROJECT_NAME}")
    writer.write_output(f"Seed: {CONFIG['seed']}")
    writer.write_output(f"Simulation start: {dates[0].date().isoformat()}")
    writer.write_output(f"Simulation days: {len(dates)}")
    writer.write_output(
        f"Stores: {n_stores} | Regions: {len(regions)} | Sales reps: {len(public_reps)} | Products: {n_products}"
    )
    writer.write_output(f"KPI daily CSV export: {bool(CONFIG['output'].get('write_kpi_daily', False))}")
    writer.write_output(
        "Other same-region representative visit share target: "
        f"{CONFIG['visits']['other_rep_visit_share_range'][0]:.0%}-"
        f"{CONFIG['visits']['other_rep_visit_share_range'][1]:.0%} per store"
    )
    writer.write_output("Bad representative IDs are intentionally omitted from public logs.")

    for day_index, date in enumerate(dates):
        date_string = date.date().isoformat()
        month_index = date_to_month[pd.Timestamp(date)]
        daily_steps: list[dict[str, Any]] = []
        daily_visits: list[dict[str, Any]] = []
        daily_audits: list[dict[str, Any]] = []
        daily_competitor_audits: list[dict[str, Any]] = []
        daily_orders: list[dict[str, Any]] = []

        customer_count = make_traffic(CONFIG, rng, private_stores, date, day_index)
        traffic_count = len(customer_count)
        traffic_ids = np.arange(counters["traffic_id"], counters["traffic_id"] + traffic_count)
        counters["traffic_id"] += traffic_count
        traffic_df = pd.DataFrame(
            {
                "traffic_id": traffic_ids,
                "store_id": store_ids,
                "traffic_date": date_string,
                "customer_count": customer_count,
            }
        )
        writer.append_monthly("store_traffic", month_index, traffic_df)
        for traffic_id, store_id, count in zip(traffic_ids, store_ids, customer_count, strict=True):
            daily_steps.append(
                {
                    "step_id": counters["step_id"],
                    "step_date": date_string,
                    "action_type": "TRAFFIC",
                    "store_id": int(store_id),
                    "rep_id": "",
                    "product_id": "",
                    "source_table": "store_traffic",
                    "source_id": int(traffic_id),
                    "details_json": details_json({"customer_count": int(count)}),
                }
            )
            counters["step_id"] += 1

        delivered_today = deliveries_by_day.pop(day_index, [])
        for order_id, store_idx, product_idx, qty in delivered_today:
            inventory[store_idx, product_idx] += qty
            pending_units[store_idx, product_idx] = max(0, pending_units[store_idx, product_idx] - qty)
            daily_steps.append(
                {
                    "step_id": counters["step_id"],
                    "step_date": date_string,
                    "action_type": "DELIVERY",
                    "store_id": int(store_ids[store_idx]),
                    "rep_id": int(rep_ids_by_store[store_idx]),
                    "product_id": int(product_ids[product_idx]),
                    "source_table": "store_order",
                    "source_id": int(order_id),
                    "details_json": details_json({"delivered_units": int(qty)}),
                }
            )
            counters["step_id"] += 1

        for store_idx, planned_visit, rep_id, other_rep_visit in visit_plan_by_day[day_index]:
            profile_key = "bad" if bool(rep_bad_by_id[rep_id]) else "good"
            profile = CONFIG["rep_profiles"][profile_key]
            completed = bool(rng.random() < float(profile["visit_completion_probability"]))
            duration_low, duration_high = CONFIG["visits"]["duration_minutes_by_store_type"][store_types[store_idx]]
            duration = int(inclusive_int(rng, int(duration_low), int(duration_high))) if completed else 0
            start_minutes = int(rng.integers(8 * 60, 16 * 60))
            visit_start = date + pd.Timedelta(minutes=start_minutes)
            visit_end = visit_start + pd.Timedelta(minutes=duration)
            visit_type = str(rng.choice(np.array(CONFIG["visits"]["visit_types"])))
            visit_id = counters["visit_id"]
            counters["visit_id"] += 1
            visit_count_by_store[store_idx] += 1
            other_rep_visit_count_by_store[store_idx] += int(other_rep_visit)
            daily_visits.append(
                {
                    "visit_id": visit_id,
                    "store_id": int(store_ids[store_idx]),
                    "rep_id": rep_id,
                    "visit_start": visit_start.isoformat(),
                    "visit_end": visit_end.isoformat(),
                    "duration_minutes": duration,
                    "visit_type": visit_type,
                    "planned_visit": planned_visit,
                    "completed_visit": completed,
                }
            )
            daily_steps.append(
                {
                    "step_id": counters["step_id"],
                    "step_date": date_string,
                    "action_type": "STORE_VISIT",
                    "store_id": int(store_ids[store_idx]),
                    "rep_id": rep_id,
                    "product_id": "",
                    "source_table": "store_visit",
                    "source_id": visit_id,
                    "details_json": details_json(
                        {
                            "planned_visit": planned_visit,
                            "completed_visit": completed,
                            "visit_type": visit_type,
                            "duration_minutes": duration,
                            "same_region_non_primary_rep": other_rep_visit,
                        }
                    ),
                }
            )
            counters["step_id"] += 1
            if not completed:
                continue

            sample_size = min(
                n_products,
                int(CONFIG["visits"]["audit_products_by_store_type"][store_types[store_idx]]),
            )
            product_sample = rng.choice(np.arange(n_products), size=sample_size, replace=False)
            updates = apply_visit_effects(
                CONFIG,
                rng,
                state,
                products_hidden,
                store_idx,
                product_sample,
                profile_key,
            )
            for update in updates:
                product_idx = int(update["product_idx"])
                audit_id = counters["audit_id"]
                counters["audit_id"] += 1
                shelf_width = float(update["facings"] * rng.uniform(7.5, 12.0))
                daily_audits.append(
                    {
                        "audit_id": audit_id,
                        "visit_id": visit_id,
                        "product_id": int(product_ids[product_idx]),
                        "facings": int(update["facings"]),
                        "shelf_width_cm": round(shelf_width, 2),
                        "shelf_level": update["shelf_level"],
                        "endcap_display": bool(update["endcap_display"]),
                        "checkout_display": bool(update["checkout_display"]),
                        "promo_stand": bool(update["promo_stand"]),
                        "pos_materials": bool(update["pos_materials"]),
                        "planogram_compliance": bool(update["planogram_compliance"]),
                    }
                )
                daily_steps.append(
                    {
                        "step_id": counters["step_id"],
                        "step_date": date_string,
                        "action_type": "AUDIT",
                        "store_id": int(store_ids[store_idx]),
                        "rep_id": rep_id,
                        "product_id": int(product_ids[product_idx]),
                        "source_table": "shelf_audit",
                        "source_id": audit_id,
                        "details_json": details_json(
                            {
                                "facings": int(update["facings"]),
                                "shelf_level": update["shelf_level"],
                                "planogram_compliance": bool(update["planogram_compliance"]),
                            }
                        ),
                    }
                )
                counters["step_id"] += 1

            competitor_audit_count = int(
                inclusive_int(
                    rng,
                    int(CONFIG["competitors"]["audit_count_range"][0]),
                    int(CONFIG["competitors"]["audit_count_range"][1]),
                )
            )
            for _ in range(competitor_audit_count):
                competitor_audit_id = counters["competitor_audit_id"]
                counters["competitor_audit_id"] += 1
                competitor_brand = str(rng.choice(np.array(CONFIG["competitors"]["competitor_brands"])))
                competitor_facings = int(
                    inclusive_int(
                        rng,
                        int(CONFIG["competitors"]["audit_facings_range"][0]),
                        int(CONFIG["competitors"]["audit_facings_range"][1]),
                    )
                )
                competitor_promotion = bool(
                    rng.random() < float(CONFIG["competitors"]["promotion_probability"]) * 1.6
                )
                daily_competitor_audits.append(
                    {
                        "competitor_audit_id": competitor_audit_id,
                        "visit_id": visit_id,
                        "competitor_brand": competitor_brand,
                        "competitor_facings": competitor_facings,
                        "competitor_promotion": competitor_promotion,
                    }
                )
                daily_steps.append(
                    {
                        "step_id": counters["step_id"],
                        "step_date": date_string,
                        "action_type": "COMPETITOR_AUDIT",
                        "store_id": int(store_ids[store_idx]),
                        "rep_id": rep_id,
                        "product_id": "",
                        "source_table": "competitor_audit",
                        "source_id": competitor_audit_id,
                        "details_json": details_json(
                            {
                                "competitor_brand": competitor_brand,
                                "competitor_facings": competitor_facings,
                                "competitor_promotion": competitor_promotion,
                            }
                        ),
                    }
                )
                counters["step_id"] += 1

        writer.append_monthly("store_visit", month_index, daily_visits)
        writer.append_monthly("shelf_audit", month_index, daily_audits)
        writer.append_monthly("competitor_audit", month_index, daily_competitor_audits)
        total_visit_rows += len(daily_visits)

        promo_active = np.zeros((n_stores, n_products), dtype=bool)
        promo_display = np.zeros((n_stores, n_products), dtype=bool)
        promo_price = np.zeros((n_stores, n_products), dtype=float)
        for store_idx, product_idx, discounted_price, display_active, _promotion_id in active_promotions_by_day[day_index]:
            current_price = promo_price[store_idx, product_idx]
            if current_price == 0.0 or discounted_price < current_price:
                promo_active[store_idx, product_idx] = True
                promo_display[store_idx, product_idx] = display_active
                promo_price[store_idx, product_idx] = discounted_price

        competitor_a, competitor_b = CONFIG["competitors"]["daily_pressure_beta"]
        competitor_pressure = rng.beta(float(competitor_a), float(competitor_b), size=n_stores)
        location_pressure = np.array(
            [CONFIG["competitors"]["location_pressure_factor"][location] for location in locations],
            dtype=float,
        )
        competitor_pressure = np.clip(competitor_pressure * location_pressure, 0, 1.0)
        competitor_promo_matrix = (
            rng.random((n_stores, n_products))
            < float(CONFIG["competitors"]["promotion_probability"])
            * competitor_pressure[:, None]
            * competitor_sensitivity[None, :]
        )

        placement_score, display_score, execution_score_matrix = execution_scores(state, target_facings)
        sales_model = CONFIG["sales_model"]
        target_facings_log = np.maximum(np.log1p(target_facings.astype(float))[None, :], 1e-9)
        facings_log_ratio = np.log1p(np.maximum(state["facings"].astype(float), 0.0)) / target_facings_log
        facings_multiplier = np.clip(
            facings_log_ratio,
            float(sales_model["facings_log_min_multiplier"]),
            float(sales_model["facings_log_max_multiplier"]),
        )
        execution_delta = (
            float(sales_model["display_lift"]) * (display_score - 0.45)
            + float(sales_model["placement_lift"]) * (placement_score - 0.45)
            + float(sales_model["planogram_lift"]) * (state["planogram_compliance"].astype(float) - 0.55)
        )
        execution_multiplier = np.clip(
            1.0 + float(sales_model["rep_influence_strength"]) * execution_delta,
            float(sales_model["minimum_execution_multiplier"]),
            float(sales_model["maximum_execution_multiplier"]),
        )

        discount_depth = np.where(
            promo_active,
            np.clip(1.0 - promo_price / np.maximum(unit_prices[None, :], 0.01), 0.0, 1.0),
            0.0,
        )
        promotion_curve_arg = np.clip(
            float(sales_model["promotion_sigmoid_steepness"])
            * (discount_depth - float(sales_model["promotion_sigmoid_midpoint"])),
            -60.0,
            60.0,
        )
        promotion_curve = 1.0 / (1.0 + np.exp(-promotion_curve_arg))
        zero_discount_arg = np.clip(
            -float(sales_model["promotion_sigmoid_steepness"]) * float(sales_model["promotion_sigmoid_midpoint"]),
            -60.0,
            60.0,
        )
        zero_discount_curve = 1.0 / (1.0 + math.exp(-float(zero_discount_arg)))
        promotion_response = np.clip((promotion_curve - zero_discount_curve) / (1.0 - zero_discount_curve), 0.0, 1.0)
        display_bonus_by_store = np.array(
            [
                float(sales_model["promotion_display_bonus_by_store_type"][store_type])
                for store_type in store_types
            ],
            dtype=float,
        )
        promotion_multiplier = np.where(
            promo_active,
            1.0
            + float(sales_model["promotion_max_lift"]) * promotion_response
            + np.where(promo_display, display_bonus_by_store[:, None], 0.0),
            1.0,
        )
        competitor_multiplier = np.clip(
            1.0
            - float(sales_model["competitor_pressure_strength"]) * competitor_pressure[:, None]
            - float(sales_model["competitor_promotion_penalty"]) * competitor_promo_matrix.astype(float),
            0.42,
            1.05,
        )

        traffic_ratio = customer_count[:, None] / np.maximum(
            private_stores["base_daily_traffic"].to_numpy(float)[:, None],
            1.0,
        )
        traffic_scaled_baseline = baseline_demand * np.power(
            np.maximum(traffic_ratio, 0.0),
            float(sales_model["traffic_alpha"]),
        )
        demand_mean = np.clip(
            traffic_scaled_baseline
            * execution_multiplier
            * facings_multiplier
            * promotion_multiplier
            * competitor_multiplier,
            0,
            None,
        )
        demand_units = rng.poisson(demand_mean)
        inventory_before_sales = inventory.copy()
        sold_units = np.minimum(demand_units, inventory)
        inventory = inventory - sold_units
        stockout_demand_mask = (inventory_before_sales <= 0) & (demand_units > 0)
        total_stockout_sales_rows += int(stockout_demand_mask.sum())

        effective_price = np.where(promo_active, promo_price, unit_prices[None, :])
        revenue = sold_units * effective_price
        sales_mask = (demand_units > 0) | (sold_units > 0)
        flat_sales = np.flatnonzero(sales_mask.ravel())
        sales_count = len(flat_sales)
        if sales_count:
            sales_ids = np.arange(counters["sales_id"], counters["sales_id"] + sales_count)
            counters["sales_id"] += sales_count
            sales_df = pd.DataFrame(
                {
                    "sales_id": sales_ids,
                    "store_id": row_store_ids[flat_sales],
                    "product_id": row_product_ids[flat_sales],
                    "sales_date": date_string,
                    "units_sold": sold_units.ravel()[flat_sales],
                    "revenue": revenue.ravel()[flat_sales],
                    "promo_price": np.where(
                        promo_active.ravel()[flat_sales],
                        promo_price.ravel()[flat_sales],
                        0.0,
                    ),
                }
            )
            writer.append_monthly("sales_transaction", month_index, sales_df)
            total_sales_rows += sales_count

        store_sales_units = sold_units.sum(axis=1)
        store_sales_revenue = revenue.sum(axis=1)
        store_stockout_lines = stockout_demand_mask.sum(axis=1)
        for store_idx in range(n_stores):
            daily_steps.append(
                {
                    "step_id": counters["step_id"],
                    "step_date": date_string,
                    "action_type": "SALES_DAY",
                    "store_id": int(store_ids[store_idx]),
                    "rep_id": int(rep_ids_by_store[store_idx]),
                    "product_id": "",
                    "source_table": "sales_transaction",
                    "source_id": "",
                    "details_json": details_json(
                        {
                            "units_sold": int(store_sales_units[store_idx]),
                            "revenue": round(float(store_sales_revenue[store_idx]), 2),
                            "stockout_product_lines": int(store_stockout_lines[store_idx]),
                        }
                    ),
                }
            )
            counters["step_id"] += 1

        inventory_count = n_stores * n_products
        inventory_ids = np.arange(counters["inventory_id"], counters["inventory_id"] + inventory_count)
        counters["inventory_id"] += inventory_count
        inventory_flat = inventory_before_sales.ravel()
        inventory_df = pd.DataFrame(
            {
                "inventory_id": inventory_ids,
                "store_id": row_store_ids,
                "product_id": row_product_ids,
                "inventory_date": date_string,
                "stock_units": inventory_flat,
                "out_of_stock": inventory_flat <= 0,
            }
        )
        writer.append_monthly("inventory_status", month_index, inventory_df)

        threshold_days = private_stores["store_type"].map(CONFIG["inventory_orders"]["reorder_threshold_days"]).to_numpy(
            float
        )
        target_days = private_stores["store_type"].map(CONFIG["inventory_orders"]["target_stock_days"]).to_numpy(float)
        reorder_point = baseline_demand * threshold_days[:, None]
        target_stock = baseline_demand * target_days[:, None]
        available_units = inventory + pending_units
        order_needed = available_units < reorder_point
        order_quantity = np.ceil(np.maximum(target_stock - available_units, 0)).astype(int)
        order_quantity[order_quantity < int(CONFIG["inventory_orders"]["minimum_order_units"])] = 0
        order_mask = order_needed & (order_quantity > 0)

        if order_mask.any():
            order_store_idx, order_product_idx = np.where(order_mask)
            order_count = len(order_store_idx)
            order_ids = np.arange(counters["order_id"], counters["order_id"] + order_count)
            counters["order_id"] += order_count
            profile_delay_probability = np.where(
                store_bad[order_store_idx],
                float(CONFIG["rep_profiles"]["bad"]["order_delay_probability"]),
                float(CONFIG["rep_profiles"]["good"]["order_delay_probability"]),
            )
            profile_under_probability = np.where(
                store_bad[order_store_idx],
                float(CONFIG["rep_profiles"]["bad"]["under_order_probability"]),
                float(CONFIG["rep_profiles"]["good"]["under_order_probability"]),
            )
            under_order_event = rng.random(order_count) < profile_under_probability
            under_order_factor = np.ones(order_count, dtype=float)
            for profile_key in ["good", "bad"]:
                profile_mask = store_bad[order_store_idx] if profile_key == "bad" else ~store_bad[order_store_idx]
                profile_mask = profile_mask & under_order_event
                if profile_mask.any():
                    low, high = CONFIG["rep_profiles"][profile_key]["under_order_factor_range"]
                    under_order_factor[profile_mask] = rng.uniform(float(low), float(high), size=int(profile_mask.sum()))
            ordered_units = np.maximum(
                int(CONFIG["inventory_orders"]["minimum_order_units"]),
                np.floor(order_quantity[order_store_idx, order_product_idx] * under_order_factor).astype(int),
            )

            lead_low, lead_high = CONFIG["inventory_orders"]["base_order_lead_time_days"]
            lead_times = inclusive_int(rng, int(lead_low), int(lead_high), size=order_count)
            delayed = rng.random(order_count) < profile_delay_probability
            delay_low, delay_high = CONFIG["inventory_orders"]["extra_delay_days"]
            extra_delay = np.where(
                delayed,
                inclusive_int(rng, int(delay_low), int(delay_high), size=order_count),
                0,
            )
            delivery_day_indices = day_index + lead_times + extra_delay
            delivery_dates = [
                (date + pd.Timedelta(days=int(lead_times[pos] + extra_delay[pos]))).date().isoformat()
                for pos in range(order_count)
            ]
            for pos in range(order_count):
                store_idx = int(order_store_idx[pos])
                product_idx = int(order_product_idx[pos])
                qty = int(ordered_units[pos])
                pending_units[store_idx, product_idx] += qty
                delivery_day_index = int(delivery_day_indices[pos])
                if delivery_day_index < len(dates):
                    deliveries_by_day[delivery_day_index].append((int(order_ids[pos]), store_idx, product_idx, qty))
                daily_orders.append(
                    {
                        "order_id": int(order_ids[pos]),
                        "store_id": int(store_ids[store_idx]),
                        "product_id": int(product_ids[product_idx]),
                        "order_date": date_string,
                        "ordered_units": qty,
                        "delivery_date": delivery_dates[pos],
                    }
                )
                daily_steps.append(
                    {
                        "step_id": counters["step_id"],
                        "step_date": date_string,
                        "action_type": "STORE_ORDER",
                        "store_id": int(store_ids[store_idx]),
                        "rep_id": int(rep_ids_by_store[store_idx]),
                        "product_id": int(product_ids[product_idx]),
                        "source_table": "store_order",
                        "source_id": int(order_ids[pos]),
                        "details_json": details_json(
                            {
                                "ordered_units": qty,
                                "delivery_date": delivery_dates[pos],
                                "delayed": bool(delayed[pos]),
                                "under_ordered": bool(under_order_event[pos]),
                            }
                        ),
                    }
                )
                counters["step_id"] += 1

        writer.append_monthly("store_order", month_index, daily_orders)
        total_order_rows += len(daily_orders)

        own_facings = state["facings"].sum(axis=1).astype(float)
        competitor_facings_estimate = n_products * (2.0 + competitor_pressure * 12.0)
        share_of_shelf = own_facings / np.maximum(own_facings + competitor_facings_estimate, 1.0)
        out_of_stock_rate = (inventory <= 0).mean(axis=1)
        baseline_units = baseline_demand.sum(axis=1)
        sales_uplift = (store_sales_units - baseline_units) / np.maximum(baseline_units, 1.0)
        execution_score = execution_score_matrix.mean(axis=1)

        kpi_ids = np.arange(counters["kpi_id"], counters["kpi_id"] + n_stores)
        counters["kpi_id"] += n_stores
        kpi_df = pd.DataFrame(
            {
                "kpi_id": kpi_ids,
                "store_id": store_ids,
                "rep_id": rep_ids_by_store,
                "kpi_date": date_string,
                "sales_uplift": sales_uplift,
                "share_of_shelf": share_of_shelf,
                "execution_score": execution_score,
                "out_of_stock_rate": out_of_stock_rate,
            }
        )
        writer.append_monthly("kpi_daily", month_index, kpi_df)

        for rep_id in np.unique(rep_ids_by_store):
            mask = rep_ids_by_store == rep_id
            kpi_execution_sum[int(rep_id)] += float(execution_score[mask].sum())
            kpi_oos_sum[int(rep_id)] += float(out_of_stock_rate[mask].sum())
            kpi_count[int(rep_id)] += int(mask.sum())

        writer.write_steps(daily_steps)
        writer.write_output(
            f"{date_string}: traffic={int(customer_count.sum())}, "
            f"visits={len(daily_visits)}, completed_visits="
            f"{sum(1 for row in daily_visits if row['completed_visit'])}, "
            f"sales_units={int(store_sales_units.sum())}, revenue={float(store_sales_revenue.sum()):.2f}, "
            f"orders={len(daily_orders)}, deliveries={len(delivered_today)}, "
            f"stockout_rate={float(out_of_stock_rate.mean()):.4f}"
        )

    writer.write_answer(bad_rep_ids)

    rep_ids = private_reps["rep_id"].to_numpy(int)
    bad_mask = private_reps["is_bad"].to_numpy(bool)
    rep_execution_mean = kpi_execution_sum[rep_ids] / np.maximum(kpi_count[rep_ids], 1)
    rep_oos_mean = kpi_oos_sum[rep_ids] / np.maximum(kpi_count[rep_ids], 1)

    bad_region_counts = private_reps.loc[private_reps["is_bad"]].groupby("region").size()
    if len(bad_rep_ids) != int(CONFIG["scale"]["n_bad_reps"]):
        raise AssertionError("Bad representative count does not match CONFIG.")
    if bad_region_counts.max() > int(CONFIG["scale"]["max_bad_reps_per_region"]):
        raise AssertionError("A region received too many bad representatives.")
    if (public_stores["location"] == "village").any():
        village_non_local = public_stores[
            (public_stores["location"] == "village") & (public_stores["store_type"] != "local_shop")
        ]
        if not village_non_local.empty:
            raise AssertionError("Village stores must all be local shops.")
    visited_store_mask = visit_count_by_store > 0
    realized_other_rep_share = (
        other_rep_visit_count_by_store[visited_store_mask]
        / np.maximum(visit_count_by_store[visited_store_mask], 1)
    )
    min_other_rep_share, max_other_rep_share = CONFIG["visits"]["other_rep_visit_share_range"]
    if (
        np.any(realized_other_rep_share < float(min_other_rep_share) - 1e-12)
        or np.any(realized_other_rep_share > float(max_other_rep_share) + 1e-12)
    ):
        raise AssertionError(
            "A store has an out-of-range same-region non-primary representative visit share."
        )

    writer.write_output("")
    writer.write_output("== Final Summary ==")
    writer.write_output(f"Sales transaction rows: {total_sales_rows}")
    writer.write_output(f"Store order rows: {total_order_rows}")
    writer.write_output(f"Store visit rows: {total_visit_rows}")
    writer.write_output(
        "Same-region non-primary representative visit share range: "
        f"{float(realized_other_rep_share.min()):.4f}-"
        f"{float(realized_other_rep_share.max()):.4f}"
    )
    writer.write_output(f"Stockout demand rows in sales transactions: {total_stockout_sales_rows}")
    writer.write_output(
        "Hidden quality signal check: lower execution and higher stockout rate for the worse-performing group."
    )
    writer.close()


if __name__ == "__main__":
    main()
