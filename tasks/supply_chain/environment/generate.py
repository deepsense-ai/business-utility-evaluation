from __future__ import annotations

import csv
import json
import math
import os
import random
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque


PROJECT_NAME = "supply chain"
SCHEMA_VERSION = 1
DEFAULT_SUPPLY_LOG_MODE = "raw_receipts"
LEGACY_SUPPLY_LOG_MODE = "legacy_tables"
SUPPORTED_SUPPLY_LOG_MODES = {DEFAULT_SUPPLY_LOG_MODE, LEGACY_SUPPLY_LOG_MODE}
DEFAULT_STORE_ALLOCATION_LOG_MODE = "raw_receipts"
LEGACY_STORE_ALLOCATION_LOG_MODE = "legacy_table"
SUPPORTED_STORE_ALLOCATION_LOG_MODES = {
    DEFAULT_STORE_ALLOCATION_LOG_MODE,
    LEGACY_STORE_ALLOCATION_LOG_MODE,
}


def resolve_supply_log_mode() -> str:
    mode = os.environ.get("SUPPLY_LOG_MODE", DEFAULT_SUPPLY_LOG_MODE).strip().lower()
    if mode not in SUPPORTED_SUPPLY_LOG_MODES:
        supported_modes = ", ".join(sorted(SUPPORTED_SUPPLY_LOG_MODES))
        raise ValueError(
            f"Unsupported SUPPLY_LOG_MODE={mode!r}. Expected one of: {supported_modes}."
        )
    return mode


def resolve_store_allocation_log_mode() -> str:
    mode = os.environ.get(
        "STORE_ALLOCATION_LOG_MODE",
        DEFAULT_STORE_ALLOCATION_LOG_MODE,
    ).strip().lower()
    if mode not in SUPPORTED_STORE_ALLOCATION_LOG_MODES:
        supported_modes = ", ".join(sorted(SUPPORTED_STORE_ALLOCATION_LOG_MODES))
        raise ValueError(
            f"Unsupported STORE_ALLOCATION_LOG_MODE={mode!r}. "
            f"Expected one of: {supported_modes}."
        )
    return mode


CONFIG: dict[str, Any] = {
    "seed": 2,
    "T": 365,
    "n_products": 30, # 10/30/10 lub 10/90/10 to sa trudne setupy
    "n_producers": 60, #super hard setup: 90 producers, 2-10 products regular demand, normalny 30 producers
    "n_stores": 10,
    "min_C": 40,
    "max_C": 60,
    "global_lag": 14,
    "lag_demand_schedule": [
        {"start_day": 1, "end_day": 3, "demand_multiplier": 0.2},
        {"start_day": 4, "end_day": 7, "demand_multiplier": 0.5},
        {"start_day": 8, "end_day": 14, "demand_multiplier": 0.8},
    ],
    "P_req": 0.5,
    "min_Req": 2,
    "max_Req": 3, #z10
    "min_Qual": 0.55,
    "max_Qual": 0.75,
    "calendar_year_days": 365,
    "vacation_start_day": 165,
    "vacation_end_day": 235,
    "vacation_ramp_days": 14,
    "min_vacation_dip": 0.10,
    "max_vacation_dip": 0.28,
    "holiday_peak_day": 358,
    "holiday_half_width_days": 24,
    "min_holiday_shift": -0.06,
    "max_holiday_shift": 0.30,
    "min_Forecast": 7,
    "max_Forecast": 7,
    "min_Threshold": 0.1,
    "max_Threshold": 0.1,
    "order_format_weights": {
        "api_json": 0.25,
        "table_csv": 0.25,
        "text_template": 0.25,
        "key_value": 0.25,
    },
    "P_prod": 0.4,
    "min_prod": 10,
    "max_prod": 27,
    "min_ProdQual": 0.70,
    "max_ProdQual": 0.85,
    "SUPPLY_LOG_MODE": resolve_supply_log_mode(),
    "STORE_ALLOCATION_LOG_MODE": resolve_store_allocation_log_mode(),
    "LOG_RAW_ORDERS": True,
    "LOG_SALES": True,
    "LOG_INVENTORY": False,
    "LOG_WHOLESALER_METRICS": True,
    "LOG_SOURCING_AND_SUPPLY": True,
    "LOG_LAG_EVENTS": False,
}


RAW_ORDER_EXTENSIONS = {
    "api_json": ".json",
    "table_csv": ".csv",
    "text_template": ".txt",
    "key_value": ".txt",
}

SUPPLIER_RECEIPT_FORMATS = tuple(RAW_ORDER_EXTENSIONS.keys())


BASE_CSV_SCHEMAS: dict[str, list[str]] = {
    "sales_log": [
        "Day",
        "Store_ID",
        "Product_ID",
        "Reported_Demand",
        "Sold_Quantity",
        "Lost_Sales",
    ],
    "inventory_log": [
        "Day",
        "Store_ID",
        "Product_ID",
        "Inventory_Units",
    ],
    "lag_event_log": [
        "Day",
        "Consumer_ID",
        "Store_ID",
        "Product_ID",
        "Received_Quality",
        "Required_Quality",
        "Lag_Duration_Days",
    ],
}

LEGACY_SUPPLY_CSV_SCHEMAS: dict[str, list[str]] = {
    "sourcing_log": [
        "Day",
        "Product_ID",
        "Producer_ID",
        "Collected_Quantity",
    ],
    "supply_production_log": [
        "Day",
        "Producer_ID",
        "Product_ID",
        "Drawn_Daily_Supply",
        "Quantity_Sent_To_Wholesaler",
        "Unused_Surplus",
    ],
}

LEGACY_STORE_CSV_SCHEMAS: dict[str, list[str]] = {
    "service_level_log": [
        "Day",
        "Store_ID",
        "Product_ID",
        "Received_Delivery",
        "Service_Level_Percent",
    ],
}

ALL_CSV_SCHEMAS: dict[str, list[str]] = {
    **BASE_CSV_SCHEMAS,
    **LEGACY_SUPPLY_CSV_SCHEMAS,
    **LEGACY_STORE_CSV_SCHEMAS,
}


@dataclass(slots=True)
class InventoryBatch:
    qty: int
    quality: float
    producer_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "qty": self.qty,
            "quality": round(self.quality, 4),
            "producer_id": self.producer_id,
        }


@dataclass(slots=True)
class ProductionMatrixEntry:
    max_prod: int
    quality: float


@dataclass(slots=True)
class Consumer:
    consumer_id: str
    store_id: str
    req: dict[str, int]
    min_quality: dict[str, float]
    lag: dict[str, int]


@dataclass(slots=True)
class Store:
    store_id: str
    forecast_window: int
    threshold: float
    order_format: str
    inventory: dict[str, Deque[InventoryBatch]]
    demand_history: dict[str, list[int]]
    current_order: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class Producer:
    producer_id: str
    production_matrix: dict[str, ProductionMatrixEntry]


@dataclass(slots=True)
class OrderRecord:
    round_no: int
    store_id: str
    order_format: str
    items: list[dict[str, Any]]


@dataclass(slots=True)
class SupplierReceiptRecord:
    round_no: int
    producer_id: str
    receipt_format: str
    items: list[dict[str, Any]]


@dataclass(slots=True)
class WholesalerReceiptRecord:
    round_no: int
    producer_id: str
    daily_sequence_no: int


@dataclass(slots=True)
class StoreAllocationReceiptRecord:
    round_no: int
    store_id: str
    daily_sequence_no: int
    total_delivered_units: int


@dataclass(slots=True)
class CalendarEffectProfile:
    vacation_dip: float
    holiday_shift: float

    def to_dict(self) -> dict[str, float]:
        return {
            "vacation_dip": round(self.vacation_dip, 4),
            "holiday_shift": round(self.holiday_shift, 4),
        }


def uses_raw_supply_receipts(config: dict[str, Any]) -> bool:
    return config["SUPPLY_LOG_MODE"] == DEFAULT_SUPPLY_LOG_MODE


def uses_raw_store_allocation_receipts(config: dict[str, Any]) -> bool:
    return config["STORE_ALLOCATION_LOG_MODE"] == DEFAULT_STORE_ALLOCATION_LOG_MODE


def active_csv_schemas(config: dict[str, Any]) -> dict[str, list[str]]:
    schemas = dict(BASE_CSV_SCHEMAS)
    if config["SUPPLY_LOG_MODE"] == LEGACY_SUPPLY_LOG_MODE:
        schemas.update(LEGACY_SUPPLY_CSV_SCHEMAS)
    if config["STORE_ALLOCATION_LOG_MODE"] == LEGACY_STORE_ALLOCATION_LOG_MODE:
        schemas.update(LEGACY_STORE_CSV_SCHEMAS)
    return schemas


class LogManager:
    def __init__(self, base_dir: Path, config: dict[str, Any]) -> None:
        output_dir = Path(os.environ.get("SUPPLY_CHAIN_OUTPUT_DIR", Path.cwd())).resolve()
        self.csv_schemas = active_csv_schemas(config)
        self.raw_order_dir = output_dir / "raw_orders"
        self.raw_supplier_receipt_dir = output_dir / "raw_supplier_receipts"
        self.raw_wholesaler_receipt_dir = output_dir / "raw_wholesaler_receipts"
        self.raw_store_receipt_dir = output_dir / "raw_wholesaler_store_receipts"
        self.raw_document_dirs = [
            self.raw_order_dir,
            self.raw_supplier_receipt_dir,
            self.raw_wholesaler_receipt_dir,
            self.raw_store_receipt_dir,
        ]
        self.active_raw_document_dirs = [self.raw_order_dir]
        if uses_raw_supply_receipts(config):
            self.active_raw_document_dirs.extend(
                [self.raw_supplier_receipt_dir, self.raw_wholesaler_receipt_dir]
            )
        if uses_raw_store_allocation_receipts(config):
            self.active_raw_document_dirs.append(self.raw_store_receipt_dir)
        self.csv_target_dirs = [output_dir]
        self.csv_files: list[Any] = []
        self.csv_writers: dict[str, list[csv.writer]] = defaultdict(list)
        self.config = config

        output_dir.mkdir(parents=True, exist_ok=True)
        self._clear_managed_outputs(output_dir)
        for raw_document_dir in self.active_raw_document_dirs:
            raw_document_dir.mkdir(parents=True, exist_ok=True)

        for schema_name, columns in self.csv_schemas.items():
            enabled = self._is_schema_enabled(schema_name)
            if not enabled:
                continue
            for target_dir in self.csv_target_dirs:
                file_handle = open(target_dir / f"{schema_name}.csv", "w", newline="", encoding="utf-8")
                writer = csv.writer(file_handle)
                writer.writerow(columns)
                self.csv_files.append(file_handle)
                self.csv_writers[schema_name].append(writer)

    def _clear_managed_outputs(self, output_dir: Path) -> None:
        files_to_remove = [output_dir / f"{schema_name}.csv" for schema_name in ALL_CSV_SCHEMAS]
        stale_files_to_remove = [
            output_dir / "aggregated_demand_log.csv",
            output_dir / "store_order_log.csv",
            output_dir / "sourcing_log.csv",
            output_dir / "supply_production_log.csv",
            output_dir / "simulation_output.txt",
            output_dir / "simulation_events.jsonl",
            output_dir / "simulation_meta.json",
            output_dir / "answer.txt",
            output_dir / "bullwhip_summary.json",
            output_dir / "product_producer_ranking.md",
        ]

        for path in files_to_remove + stale_files_to_remove:
            if path.exists():
                path.unlink()

        for raw_document_dir in self.raw_document_dirs:
            if not raw_document_dir.exists():
                continue
            for raw_document_path in raw_document_dir.iterdir():
                if raw_document_path.is_file():
                    raw_document_path.unlink()

    def _is_schema_enabled(self, schema_name: str) -> bool:
        flag_mapping = {
            "sales_log": "LOG_SALES",
            "inventory_log": "LOG_INVENTORY",
            "service_level_log": "LOG_WHOLESALER_METRICS",
            "sourcing_log": "LOG_SOURCING_AND_SUPPLY",
            "supply_production_log": "LOG_SOURCING_AND_SUPPLY",
            "lag_event_log": "LOG_LAG_EVENTS",
        }
        return bool(self.config.get(flag_mapping[schema_name], False))

    def log_csv(self, schema_name: str, row: list[Any]) -> None:
        for writer in self.csv_writers.get(schema_name, []):
            writer.writerow(row)

    def write_output(self, line: str) -> None:
        return None

    def log_event(self, event: dict[str, Any]) -> None:
        return None

    def write_json_file(self, filename: str, payload: Any) -> None:
        return None

    def write_text_file(self, filename: str, content: str) -> None:
        return None

    def write_raw_order(self, record: OrderRecord, content: str) -> None:
        if not self.config["LOG_RAW_ORDERS"] or not record.items:
            return
        extension = RAW_ORDER_EXTENSIONS[record.order_format]
        safe_format = record.order_format.replace("_", "-")
        filename = f"day_{record.round_no:03d}_{record.store_id}_{safe_format}{extension}"
        with open(self.raw_order_dir / filename, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)

    def write_raw_supplier_receipt(self, record: SupplierReceiptRecord, content: str) -> None:
        if (
            not self.config["LOG_SOURCING_AND_SUPPLY"]
            or not uses_raw_supply_receipts(self.config)
            or not record.items
        ):
            return
        extension = RAW_ORDER_EXTENSIONS[record.receipt_format]
        safe_format = record.receipt_format.replace("_", "-")
        filename = f"day_{record.round_no:03d}_{record.producer_id}_{safe_format}{extension}"
        with open(self.raw_supplier_receipt_dir / filename, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)

    def write_raw_wholesaler_receipt(self, record: WholesalerReceiptRecord, content: str) -> None:
        if not self.config["LOG_SOURCING_AND_SUPPLY"] or not uses_raw_supply_receipts(self.config):
            return
        filename = f"day_{record.round_no:03d}_{record.producer_id}_receipt.txt"
        with open(self.raw_wholesaler_receipt_dir / filename, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)

    def write_raw_store_receipt(self, record: StoreAllocationReceiptRecord, content: str) -> None:
        if (
            not self.config["LOG_WHOLESALER_METRICS"]
            or not uses_raw_store_allocation_receipts(self.config)
        ):
            return
        filename = f"day_{record.round_no:03d}_{record.store_id}_receipt.txt"
        with open(self.raw_store_receipt_dir / filename, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)

    def close(self) -> None:
        for file_handle in self.csv_files:
            file_handle.close()


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def lag_recovery_duration(config: dict[str, Any]) -> int:
    return max((int(stage["end_day"]) for stage in config["lag_demand_schedule"]), default=0)


def lag_demand_multiplier(config: dict[str, Any], remaining_lag_days: int) -> float:
    if remaining_lag_days <= 0:
        return 1.0

    total_duration = lag_recovery_duration(config)
    recovery_day = total_duration - remaining_lag_days + 1
    for stage in config["lag_demand_schedule"]:
        if int(stage["start_day"]) <= recovery_day <= int(stage["end_day"]):
            return float(stage["demand_multiplier"])
    return 1.0


def round_day_of_year(round_no: int, year_days: int) -> int:
    return ((round_no - 1) % year_days) + 1


def smooth_window(day_of_year: int, start_day: int, end_day: int, ramp_days: int) -> float:
    if start_day <= day_of_year <= end_day:
        return 1.0
    if ramp_days <= 0:
        return 0.0
    if start_day - ramp_days <= day_of_year < start_day:
        return (day_of_year - (start_day - ramp_days)) / ramp_days
    if end_day < day_of_year <= end_day + ramp_days:
        return ((end_day + ramp_days) - day_of_year) / ramp_days
    return 0.0


def circular_peak(day_of_year: int, peak_day: int, half_width_days: int, year_days: int) -> float:
    if half_width_days <= 0:
        return 0.0
    distance = abs(day_of_year - peak_day)
    wrapped_distance = min(distance, year_days - distance)
    if wrapped_distance > half_width_days:
        return 0.0
    return 0.5 * (1.0 + math.cos(math.pi * wrapped_distance / half_width_days))


def weighted_choice(randomizer: random.Random, weights: dict[str, float]) -> str:
    population = list(weights.keys())
    probabilities = list(weights.values())
    return randomizer.choices(population, weights=probabilities, k=1)[0]


def draw_daily_supply(
    randomizer: random.Random,
    config: dict[str, Any],
    entry: ProductionMatrixEntry,
) -> int:
    if entry.max_prod <= 0:
        return 0
    return randomizer.randint(config["min_prod"], entry.max_prod)


def inventory_total(inventory: Deque[InventoryBatch]) -> int:
    return sum(batch.qty for batch in inventory)


def inventory_snapshot(inventory: Deque[InventoryBatch]) -> list[dict[str, Any]]:
    return [batch.to_dict() for batch in inventory]


def build_calendar_profiles(
    config: dict[str, Any],
    products: list[str],
    randomizer: random.Random,
) -> dict[str, CalendarEffectProfile]:
    profiles: dict[str, CalendarEffectProfile] = {}
    for product_id in products:
        profiles[product_id] = CalendarEffectProfile(
            vacation_dip=randomizer.uniform(
                config["min_vacation_dip"],
                config["max_vacation_dip"],
            ),
            holiday_shift=randomizer.uniform(
                config["min_holiday_shift"],
                config["max_holiday_shift"],
            ),
        )
    return profiles


def calendar_state_for_round(
    config: dict[str, Any],
    round_no: int,
    calendar_profiles: dict[str, CalendarEffectProfile],
) -> dict[str, Any]:
    day_of_year = round_day_of_year(round_no, config["calendar_year_days"])
    vacation_intensity = smooth_window(
        day_of_year,
        config["vacation_start_day"],
        config["vacation_end_day"],
        config["vacation_ramp_days"],
    )
    holiday_intensity = circular_peak(
        day_of_year,
        config["holiday_peak_day"],
        config["holiday_half_width_days"],
        config["calendar_year_days"],
    )
    product_multipliers = {
        product_id: clamp(
            (1.0 - profile.vacation_dip * vacation_intensity)
            * (1.0 + profile.holiday_shift * holiday_intensity),
            0.15,
            2.0,
        )
        for product_id, profile in calendar_profiles.items()
    }
    return {
        "day_of_year": day_of_year,
        "vacation_intensity": vacation_intensity,
        "holiday_intensity": holiday_intensity,
        "product_multipliers": product_multipliers,
    }


def apply_demand_multiplier(
    randomizer: random.Random,
    base_demand: int,
    multiplier: float,
) -> int:
    if base_demand <= 0 or multiplier <= 0:
        return 0
    if multiplier <= 1.0:
        return sum(1 for _ in range(base_demand) if randomizer.random() < multiplier)

    extra_probability = min(multiplier - 1.0, 1.0)
    extra_units = sum(1 for _ in range(base_demand) if randomizer.random() < extra_probability)
    return base_demand + extra_units


def sell_from_inventory(
    inventory: Deque[InventoryBatch],
    demand: int,
) -> tuple[int, list[InventoryBatch]]:
    sold_batches: list[InventoryBatch] = []
    remaining = demand
    while remaining > 0 and inventory:
        batch = inventory[0]
        taken = min(batch.qty, remaining)
        sold_batches.append(InventoryBatch(qty=taken, quality=batch.quality, producer_id=batch.producer_id))
        batch.qty -= taken
        remaining -= taken
        if batch.qty == 0:
            inventory.popleft()
    sold_qty = demand - remaining
    return sold_qty, sold_batches


def render_raw_order(record: OrderRecord) -> str:
    items = record.items
    if record.order_format == "api_json":
        payload = {
            "store_id": record.store_id,
            "date": f"Day_{record.round_no}",
            "items": [{"prod_id": item["product_id"], "qty": item["qty"]} for item in items],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if record.order_format == "table_csv":
        lines = ["PRODUCT;QUANTITY"]
        for item in items:
            lines.append(f"{item['product_id']};{item['qty']}")
        return "\n".join(lines)

    if record.order_format == "text_template":
        body_lines = []
        for item in items:
            body_lines.append(
                "Order from "
                f"Day_{record.round_no}. Please deliver "
                f"{item['qty']} units of product {item['product_id']}. "
                f"Regards, Store {record.store_id}."
            )
        return "\n".join(body_lines)

    lines = []
    for item in items:
        lines.append(
            f"RECEIVER: {record.store_id} | ORDER_PRODUCT: {item['product_id']} | ORDER_QTY: {item['qty']}"
        )
    return "\n".join(lines)


def select_supplier_receipt_format(round_no: int, producer_id: str) -> str:
    producer_index = int(producer_id.split("_")[1])
    format_index = (round_no + producer_index - 1) % len(SUPPLIER_RECEIPT_FORMATS)
    return SUPPLIER_RECEIPT_FORMATS[format_index]


def render_supplier_receipt(record: SupplierReceiptRecord) -> str:
    items = record.items
    if record.receipt_format == "api_json":
        payload = {
            "supplier_id": record.producer_id,
            "date": f"Day_{record.round_no}",
            "items": [
                {"prod_id": item["product_id"], "delivered_qty": item["qty"]}
                for item in items
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if record.receipt_format == "table_csv":
        lines = ["PRODUCT;DELIVERED_QTY"]
        for item in items:
            lines.append(f"{item['product_id']};{item['qty']}")
        return "\n".join(lines)

    if record.receipt_format == "text_template":
        body_lines = []
        for item in items:
            body_lines.append(
                f"Supplier {record.producer_id} delivered {item['qty']} units of product "
                f"{item['product_id']} to the wholesaler on Day_{record.round_no}."
            )
        return "\n".join(body_lines)

    lines = [f"SUPPLIER: {record.producer_id} | DAY: {record.round_no}"]
    for item in items:
        lines.append(
            f"PRODUCT: {item['product_id']} | DELIVERED_QTY: {item['qty']}"
        )
    return "\n".join(lines)


def render_wholesaler_receipt(record: WholesalerReceiptRecord) -> str:
    return "\n".join(
        [
            f"DAY: {record.round_no}",
            f"SUPPLIER_ID: {record.producer_id}",
            f"DAILY_SEQUENCE_NO: {record.daily_sequence_no}",
        ]
    )


def render_store_receipt(record: StoreAllocationReceiptRecord) -> str:
    return "\n".join(
        [
            f"DAY: {record.round_no}",
            f"STORE_ID: {record.store_id}",
            f"DAILY_SEQUENCE_NO: {record.daily_sequence_no}",
            f"TOTAL_DELIVERED_UNITS: {record.total_delivered_units}",
        ]
    )


def build_entities(config: dict[str, Any], randomizer: random.Random) -> tuple[list[str], list[Producer], list[Store], list[Consumer]]:
    products = [f"P_{index}" for index in range(1, config["n_products"] + 1)]

    producers: list[Producer] = []
    for producer_index in range(1, config["n_producers"] + 1):
        matrix: dict[str, ProductionMatrixEntry] = {}
        for product_id in products:
            if randomizer.random() <= config["P_prod"]:
                max_prod = randomizer.randint(config["min_prod"], config["max_prod"])
                quality = round(
                    randomizer.uniform(config["min_ProdQual"], config["max_ProdQual"]),
                    4,
                )
                matrix[product_id] = ProductionMatrixEntry(max_prod=max_prod, quality=quality)
            else:
                matrix[product_id] = ProductionMatrixEntry(max_prod=0, quality=0.0)
        producers.append(Producer(producer_id=f"PR_{producer_index}", production_matrix=matrix))

    stores: list[Store] = []
    consumers: list[Consumer] = []

    for store_index in range(1, config["n_stores"] + 1):
        store_id = f"S_{store_index}"
        forecast_window = randomizer.randint(config["min_Forecast"], config["max_Forecast"])
        threshold = round(randomizer.uniform(config["min_Threshold"], config["max_Threshold"]), 4)
        order_format = weighted_choice(randomizer, config["order_format_weights"])
        inventory = {product_id: deque() for product_id in products}
        demand_history = {product_id: [] for product_id in products}
        stores.append(
            Store(
                store_id=store_id,
                forecast_window=forecast_window,
                threshold=threshold,
                order_format=order_format,
                inventory=inventory,
                demand_history=demand_history,
            )
        )

        consumer_count = randomizer.randint(config["min_C"], config["max_C"])
        for local_index in range(1, consumer_count + 1):
            consumer_id = f"C_{store_index}_{local_index}"
            req: dict[str, int] = {}
            min_quality: dict[str, float] = {}
            lag: dict[str, int] = {}
            for product_id in products:
                wants_product = randomizer.random() <= config["P_req"]
                req[product_id] = (
                    randomizer.randint(config["min_Req"], config["max_Req"]) if wants_product else 0
                )
                min_quality[product_id] = round(
                    randomizer.uniform(config["min_Qual"], config["max_Qual"]),
                    4,
                )
                lag[product_id] = 0
            consumers.append(
                Consumer(
                    consumer_id=consumer_id,
                    store_id=store_id,
                    req=req,
                    min_quality=min_quality,
                    lag=lag,
                )
            )

    return products, producers, stores, consumers


def build_meta(
    config: dict[str, Any],
    products: list[str],
    producers: list[Producer],
    stores: list[Store],
    consumers: list[Consumer],
    calendar_profiles: dict[str, CalendarEffectProfile],
) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "projectName": PROJECT_NAME,
        "config": {
            "seed": config["seed"],
            "T": config["T"],
            "n_products": config["n_products"],
            "n_producers": config["n_producers"],
            "n_stores": config["n_stores"],
            "min_C": config["min_C"],
            "max_C": config["max_C"],
            "global_lag": lag_recovery_duration(config),
            "lag_demand_schedule": config["lag_demand_schedule"],
            "P_req": config["P_req"],
            "min_Req": config["min_Req"],
            "max_Req": config["max_Req"],
            "min_Qual": config["min_Qual"],
            "max_Qual": config["max_Qual"],
            "calendar_year_days": config["calendar_year_days"],
            "vacation_start_day": config["vacation_start_day"],
            "vacation_end_day": config["vacation_end_day"],
            "vacation_ramp_days": config["vacation_ramp_days"],
            "min_vacation_dip": config["min_vacation_dip"],
            "max_vacation_dip": config["max_vacation_dip"],
            "holiday_peak_day": config["holiday_peak_day"],
            "holiday_half_width_days": config["holiday_half_width_days"],
            "min_holiday_shift": config["min_holiday_shift"],
            "max_holiday_shift": config["max_holiday_shift"],
            "min_Forecast": config["min_Forecast"],
            "max_Forecast": config["max_Forecast"],
            "min_Threshold": config["min_Threshold"],
            "max_Threshold": config["max_Threshold"],
            "P_prod": config["P_prod"],
            "min_prod": config["min_prod"],
            "max_prod": config["max_prod"],
            "min_ProdQual": config["min_ProdQual"],
            "max_ProdQual": config["max_ProdQual"],
            "supply_log_mode": config["SUPPLY_LOG_MODE"],
            "store_allocation_log_mode": config["STORE_ALLOCATION_LOG_MODE"],
            "order_format_weights": config["order_format_weights"],
            "logging_flags": {
                key: config[key]
                for key in config
                if key.startswith("LOG_")
            },
        },
        "topology": {
            "flow": ["producer", "wholesaler", "store", "consumer"],
            "products": products,
            "producers": [
                {
                    "producer_id": producer.producer_id,
                    "production_matrix": {
                        product_id: {
                            "max_prod": entry.max_prod,
                            "quality": entry.quality,
                        }
                        for product_id, entry in producer.production_matrix.items()
                    },
                }
                for producer in producers
            ],
            "stores": [
                {
                    "store_id": store.store_id,
                    "forecast_window": store.forecast_window,
                    "threshold": store.threshold,
                    "order_format": store.order_format,
                }
                for store in stores
            ],
            "consumers": [
                {
                    "consumer_id": consumer.consumer_id,
                    "store_id": consumer.store_id,
                    "req": consumer.req,
                    "min_quality": consumer.min_quality,
                }
                for consumer in consumers
            ],
            "calendar_effects": {
                "vacation_window": {
                    "start_day": config["vacation_start_day"],
                    "end_day": config["vacation_end_day"],
                    "ramp_days": config["vacation_ramp_days"],
                },
                "holiday_window": {
                    "peak_day": config["holiday_peak_day"],
                    "half_width_days": config["holiday_half_width_days"],
                },
                "product_profiles": {
                    product_id: profile.to_dict()
                    for product_id, profile in calendar_profiles.items()
                },
            },
        },
    }


def store_lookup(stores: list[Store]) -> dict[str, Store]:
    return {store.store_id: store for store in stores}


def consumer_lookup(consumers: list[Consumer]) -> dict[str, list[Consumer]]:
    grouped: dict[str, list[Consumer]] = defaultdict(list)
    for consumer in consumers:
        grouped[consumer.store_id].append(consumer)
    return grouped


def build_product_producer_report(products: list[str], producers: list[Producer]) -> str:
    lines = [
        "# Product Producer Ranking",
        "",
        "Active producers are ranked per product by quality descending.",
        "Ties are broken by `MaxProd` descending and then producer ID ascending.",
        "",
    ]

    for product_id in products:
        ranked_producers = []
        for producer in producers:
            entry = producer.production_matrix[product_id]
            if entry.max_prod <= 0:
                continue
            ranked_producers.append(
                {
                    "producer_id": producer.producer_id,
                    "quality": entry.quality,
                    "max_prod": entry.max_prod,
                }
            )

        ranked_producers.sort(
            key=lambda item: (-item["quality"], -item["max_prod"], item["producer_id"])
        )

        lines.extend(
            [
                f"## {product_id}",
                "",
                "| Rank | Producer | Quality | MaxProd |",
                "| --- | --- | ---: | ---: |",
            ]
        )

        for index, producer_info in enumerate(ranked_producers, start=1):
            lines.append(
                "| "
                f"{index} | {producer_info['producer_id']} | "
                f"{producer_info['quality']:.4f} | {producer_info['max_prod']} |"
            )

        if not ranked_producers:
            lines.append("| - | no active producer | - | - |")

        lines.append("")

    return "\n".join(lines)


def build_worst_producer_answer(products: list[str], producers: list[Producer]) -> str:
    lines: list[str] = []
    for product_id in products:
        ranked_producers = []
        for producer in producers:
            entry = producer.production_matrix[product_id]
            if entry.max_prod <= 0:
                continue
            ranked_producers.append((entry.quality, entry.max_prod, producer.producer_id))

        ranked_producers.sort(key=lambda item: (item[0], item[1], -int(item[2].split("_")[1])))
        if ranked_producers:
            lines.append(f"{product_id}: {ranked_producers[0][2]}")

    return "\n".join(lines)


def format_answer_producer_ids(producer_ids: set[str]) -> str:
    if not producer_ids:
        return "NONE"
    ordered_ids = sorted(producer_ids, key=lambda producer_id: int(producer_id.split("_")[1]))
    return ", ".join(ordered_ids)


def build_answer_payload(
    products: list[str],
    confirmed_rejections_by_product: dict[str, set[str]],
) -> dict[str, list[str]]:
    return {
        product_id: sorted(
            confirmed_rejections_by_product.get(product_id, set()),
            key=lambda producer_id: int(producer_id.split("_")[1]),
        )
        for product_id in products
    }


def build_confirmed_answer(
    products: list[str],
    confirmed_rejections_by_product: dict[str, set[str]],
) -> str:
    payload = build_answer_payload(products, confirmed_rejections_by_product)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_round_snapshot(
    round_no: int,
    products: list[str],
    stores: list[Store],
    producer_order: list[Producer],
    store_order: list[str],
    actual_demand_by_product: dict[str, int],
    store_round_demand: dict[str, dict[str, int]],
    store_order_totals: dict[str, dict[str, int]],
    aggregated_demand_by_product: dict[str, int],
    service_level_by_store: dict[str, dict[str, float]],
    store_received_qty: dict[str, dict[str, int]],
    store_lost_qty: dict[str, dict[str, int]],
    producer_to_wholesaler: dict[str, dict[str, int]],
    producer_unused: dict[str, dict[str, int]],
) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "type": "ROUND_SNAPSHOT",
        "round": round_no,
        "producerOrder": [producer.producer_id for producer in producer_order],
        "storeOrder": store_order,
        "actualDemandByProduct": actual_demand_by_product,
        "storeOrdersByProduct": {
            product_id: sum(store_order_totals[store.store_id][product_id] for store in stores)
            for product_id in products
        },
        "aggregatedDemandByProduct": aggregated_demand_by_product,
        "stores": {
            store.store_id: {
                "forecastWindow": store.forecast_window,
                "threshold": store.threshold,
                "orderFormat": store.order_format,
                "roundDemand": store_round_demand[store.store_id],
                "inventoryTotals": {
                    product_id: inventory_total(store.inventory[product_id])
                    for product_id in products
                },
                "currentOrder": {
                    product_id: store.current_order.get(product_id, 0)
                    for product_id in products
                },
                "received": store_received_qty[store.store_id],
                "lostSales": store_lost_qty[store.store_id],
                "serviceLevels": service_level_by_store[store.store_id],
            }
            for store in stores
        },
        "producerMetrics": {
            producer_id: {
                "toWholesaler": producer_to_wholesaler[producer_id],
                "unused": producer_unused[producer_id],
            }
            for producer_id in producer_to_wholesaler
        },
    }


def main() -> None:
    randomizer = random.Random(CONFIG["seed"])
    base_dir = Path(__file__).resolve().parent
    logs = LogManager(base_dir, CONFIG)

    products, producers, stores, consumers = build_entities(CONFIG, randomizer)
    calendar_profiles = build_calendar_profiles(CONFIG, products, randomizer)
    stores_by_id = store_lookup(stores)
    consumers_by_store = consumer_lookup(consumers)

    meta = build_meta(CONFIG, products, producers, stores, consumers, calendar_profiles)
    logs.write_json_file("simulation_meta.json", meta)
    logs.write_text_file(
        "product_producer_ranking.md",
        build_product_producer_report(products, producers) + "\n",
    )

    logs.write_output("== Supply Chain Simulation ==")
    logs.write_output(f"Seed: {CONFIG['seed']}")
    logs.write_output(f"Days: {CONFIG['T']}")
    logs.write_output(f"Products: {len(products)} | Producers: {len(producers)} | Stores: {len(stores)} | Consumers: {len(consumers)}")

    logs.log_event(
        {
            "schemaVersion": SCHEMA_VERSION,
            "type": "SIMULATION_CONFIG",
            "round": 0,
            "message": "Simulation configuration loaded.",
            "meta": meta,
        }
    )

    bullwhip_history: dict[str, dict[str, list[int]]] = {
        product_id: {"actual_demand": [], "store_orders": []} for product_id in products
    }
    confirmed_rejections_by_product: dict[str, set[str]] = defaultdict(set)

    for round_no in range(1, CONFIG["T"] + 1):
        logs.write_output("")
        logs.write_output(f"== Day {round_no} ==")
        logs.log_event(
            {
                "schemaVersion": SCHEMA_VERSION,
                "type": "ROUND_START",
                "round": round_no,
                "message": f"Day {round_no} started.",
            }
        )

        actual_demand_by_product = {product_id: 0 for product_id in products}
        store_round_demand = {store.store_id: {product_id: 0 for product_id in products} for store in stores}
        store_lost_qty = {store.store_id: {product_id: 0 for product_id in products} for store in stores}
        store_received_qty = {store.store_id: {product_id: 0 for product_id in products} for store in stores}
        pending_lag_updates: dict[tuple[str, str], int] = {}
        calendar_state = calendar_state_for_round(CONFIG, round_no, calendar_profiles)
        recovery_duration = lag_recovery_duration(CONFIG)

        logs.log_event(
            {
                "schemaVersion": SCHEMA_VERSION,
                "type": "CALENDAR_EFFECT_ACTIVE",
                "round": round_no,
                "day_of_year": calendar_state["day_of_year"],
                "vacation_intensity": round(calendar_state["vacation_intensity"], 4),
                "holiday_intensity": round(calendar_state["holiday_intensity"], 4),
                "message": (
                    f"Calendar effect active for day-of-year {calendar_state['day_of_year']}: "
                    f"vacation={calendar_state['vacation_intensity']:.2f}, "
                    f"holiday_new_year={calendar_state['holiday_intensity']:.2f}."
                ),
            }
        )

        for consumer in consumers:
            for product_id in products:
                lag_before = consumer.lag[product_id]
                if lag_before > 0:
                    consumer.lag[product_id] = lag_before - 1
                    logs.log_event(
                        {
                            "schemaVersion": SCHEMA_VERSION,
                            "type": "LAG_DECREMENTED",
                            "round": round_no,
                            "consumer_id": consumer.consumer_id,
                            "store_id": consumer.store_id,
                            "product_id": product_id,
                            "from": lag_before,
                            "to": consumer.lag[product_id],
                            "message": (
                                f"{consumer.consumer_id} decremented lag for {product_id} "
                                f"from {lag_before} to {consumer.lag[product_id]}."
                            ),
                        }
                    )

        for store in stores:
            random_order = list(consumers_by_store[store.store_id])
            randomizer.shuffle(random_order)
            for consumer in random_order:
                for product_id in products:
                    base_demand = consumer.req[product_id]
                    lag_multiplier = lag_demand_multiplier(CONFIG, consumer.lag[product_id])
                    demand = apply_demand_multiplier(
                        randomizer,
                        base_demand,
                        calendar_state["product_multipliers"][product_id] * lag_multiplier,
                    )
                    if demand == 0:
                        continue

                    actual_demand_by_product[product_id] += demand
                    store_round_demand[store.store_id][product_id] += demand

                    logs.log_event(
                        {
                            "schemaVersion": SCHEMA_VERSION,
                            "type": "CONSUMER_DEMAND_REGISTERED",
                            "round": round_no,
                            "consumer_id": consumer.consumer_id,
                            "store_id": store.store_id,
                            "product_id": product_id,
                            "base_demand": base_demand,
                            "lag_multiplier": round(lag_multiplier, 4),
                            "calendar_multiplier": round(
                                calendar_state["product_multipliers"][product_id],
                                4,
                            ),
                            "demand": demand,
                            "message": (
                                f"{consumer.consumer_id} requested {demand} units of {product_id} "
                                f"at {store.store_id} (base={base_demand}, "
                                f"lag_multiplier={lag_multiplier:.2f}, "
                                f"calendar_multiplier="
                                f"{calendar_state['product_multipliers'][product_id]:.2f})."
                            ),
                        }
                    )

                    sold_qty, sold_batches = sell_from_inventory(store.inventory[product_id], demand)
                    lost_qty = demand - sold_qty
                    store_lost_qty[store.store_id][product_id] += lost_qty

                    logs.log_csv(
                        "sales_log",
                        [round_no, store.store_id, product_id, demand, sold_qty, lost_qty],
                    )

                    event_type = "SALE_FULFILLED" if lost_qty == 0 else "SALE_STOCKOUT"
                    logs.log_event(
                        {
                            "schemaVersion": SCHEMA_VERSION,
                            "type": event_type,
                            "round": round_no,
                            "consumer_id": consumer.consumer_id,
                            "store_id": store.store_id,
                            "product_id": product_id,
                            "demand": demand,
                            "sold": sold_qty,
                            "lost": lost_qty,
                            "batches": [batch.to_dict() for batch in sold_batches],
                            "message": (
                                f"{store.store_id} sold {sold_qty}/{demand} units of {product_id} "
                                f"to {consumer.consumer_id}."
                            ),
                        }
                    )

                    rejecting_batches = [
                        batch for batch in sold_batches if batch.quality < consumer.min_quality[product_id]
                    ]
                    if rejecting_batches:
                        pending_lag_updates[(consumer.consumer_id, product_id)] = recovery_duration + 1
                        confirmed_rejections_by_product[product_id].update(
                            batch.producer_id
                            for batch in rejecting_batches
                            if batch.producer_id is not None
                        )
                        triggering_batch = rejecting_batches[0]
                        logs.log_csv(
                            "lag_event_log",
                            [
                                round_no,
                                consumer.consumer_id,
                                store.store_id,
                                product_id,
                                round(triggering_batch.quality, 4),
                                round(consumer.min_quality[product_id], 4),
                                recovery_duration,
                            ],
                        )
                        logs.log_event(
                            {
                                "schemaVersion": SCHEMA_VERSION,
                                "type": "LAG_TRIGGERED",
                                "round": round_no,
                                "consumer_id": consumer.consumer_id,
                                "store_id": store.store_id,
                                "product_id": product_id,
                                "received_quality": round(triggering_batch.quality, 4),
                                "required_quality": round(consumer.min_quality[product_id], 4),
                                "lag_length": recovery_duration,
                                "message": (
                                    f"{consumer.consumer_id} rejected {product_id}: quality "
                                    f"{triggering_batch.quality:.2f} < "
                                    f"{consumer.min_quality[product_id]:.2f}; demand recovery profile applied."
                                ),
                            }
                        )

        consumers_index = {consumer.consumer_id: consumer for consumer in consumers}
        for (consumer_id, product_id), lag_value in pending_lag_updates.items():
            consumers_index[consumer_id].lag[product_id] = lag_value

        store_order_totals = {store.store_id: {product_id: 0 for product_id in products} for store in stores}

        for store in stores:
            order_items: list[dict[str, Any]] = []
            for product_id in products:
                history = store.demand_history[product_id]
                history.append(store_round_demand[store.store_id][product_id])
                while len(history) > store.forecast_window:
                    history.pop(0)

                target = sum(history)
                quantity_on_hand = inventory_total(store.inventory[product_id])
                order_qty = (
                    max(target - quantity_on_hand, 0)
                    if quantity_on_hand < store.threshold * target
                    else 0
                )
                store.current_order[product_id] = order_qty
                store_order_totals[store.store_id][product_id] = order_qty

                if order_qty > 0:
                    order_items.append({"product_id": product_id, "qty": order_qty, "target": target})

            order_record = OrderRecord(
                round_no=round_no,
                store_id=store.store_id,
                order_format=store.order_format,
                items=order_items,
            )
            raw_order_content = render_raw_order(order_record)
            logs.write_raw_order(order_record, raw_order_content)
            logs.log_event(
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "type": "STORE_ORDER_COMPUTED",
                    "round": round_no,
                    "store_id": store.store_id,
                    "order_format": store.order_format,
                    "items": order_items,
                    "message": (
                        f"{store.store_id} prepared {len(order_items)} order line(s) "
                        f"in format {store.order_format}."
                    ),
                }
            )

        store_queue = [store.store_id for store in stores]
        randomizer.shuffle(store_queue)

        aggregated_demand_by_product = {
            product_id: sum(store.current_order.get(product_id, 0) for store in stores)
            for product_id in products
        }

        product_pools: dict[str, Deque[InventoryBatch]] = {product_id: deque() for product_id in products}
        producer_to_wholesaler: dict[str, dict[str, int]] = {
            producer.producer_id: {product_id: 0 for product_id in products}
            for producer in producers
        }
        producer_unused: dict[str, dict[str, int]] = {
            producer.producer_id: {product_id: 0 for product_id in products}
            for producer in producers
        }
        product_supply_draws: dict[str, dict[str, int]] = defaultdict(dict)

        producer_order = list(producers)
        randomizer.shuffle(producer_order)
        supplier_receipt_items_by_producer: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for product_id in products:
            remaining_needed = aggregated_demand_by_product[product_id]
            for producer in producer_order:
                entry = producer.production_matrix[product_id]
                draw = draw_daily_supply(randomizer, CONFIG, entry)
                product_supply_draws[producer.producer_id][product_id] = draw
                taken = min(draw, remaining_needed)
                unused = draw - taken
                producer_to_wholesaler[producer.producer_id][product_id] = taken
                producer_unused[producer.producer_id][product_id] = unused

                if taken > 0:
                    batch = InventoryBatch(qty=taken, quality=entry.quality, producer_id=producer.producer_id)
                    product_pools[product_id].append(batch)
                    supplier_receipt_items_by_producer[producer.producer_id].append(
                        {"product_id": product_id, "qty": taken}
                    )
                    logs.log_event(
                        {
                            "schemaVersion": SCHEMA_VERSION,
                            "type": "WHOLESALER_POOL_COLLECTED",
                            "round": round_no,
                            "producer_id": producer.producer_id,
                            "product_id": product_id,
                            "taken_qty": taken,
                            "quality": round(entry.quality, 4),
                            "message": (
                                f"Wholesaler collected {taken} units of {product_id} "
                                f"from {producer.producer_id}."
                            ),
                        }
                    )
                remaining_needed = max(0, remaining_needed - taken)

        if uses_raw_supply_receipts(CONFIG):
            daily_sequence_no = 1
            for producer in producer_order:
                items = supplier_receipt_items_by_producer.get(producer.producer_id, [])
                if not items:
                    continue

                wholesaler_receipt = WholesalerReceiptRecord(
                    round_no=round_no,
                    producer_id=producer.producer_id,
                    daily_sequence_no=daily_sequence_no,
                )
                logs.write_raw_wholesaler_receipt(
                    wholesaler_receipt,
                    render_wholesaler_receipt(wholesaler_receipt),
                )

                supplier_receipt = SupplierReceiptRecord(
                    round_no=round_no,
                    producer_id=producer.producer_id,
                    receipt_format=select_supplier_receipt_format(round_no, producer.producer_id),
                    items=items,
                )
                logs.write_raw_supplier_receipt(
                    supplier_receipt,
                    render_supplier_receipt(supplier_receipt),
                )
                daily_sequence_no += 1
        else:
            for product_id in products:
                for producer in producer_order:
                    taken = producer_to_wholesaler[producer.producer_id][product_id]
                    if taken > 0:
                        logs.log_csv(
                            "sourcing_log",
                            [round_no, product_id, producer.producer_id, taken],
                        )
                    logs.log_csv(
                        "supply_production_log",
                        [
                            round_no,
                            producer.producer_id,
                            product_id,
                            product_supply_draws[producer.producer_id][product_id],
                            taken,
                            producer_unused[producer.producer_id][product_id],
                        ],
                    )

        service_level_by_store = {
            store.store_id: {product_id: 100.0 for product_id in products} for store in stores
        }

        for store_sequence_no, store_id in enumerate(store_queue, start=1):
            store = stores_by_id[store_id]
            for product_id in products:
                requested = store.current_order.get(product_id, 0)
                remaining_request = requested
                while remaining_request > 0 and product_pools[product_id]:
                    batch = product_pools[product_id].popleft()
                    delivered = min(remaining_request, batch.qty)
                    store.inventory[product_id].append(
                        InventoryBatch(qty=delivered, quality=batch.quality, producer_id=batch.producer_id)
                    )
                    store_received_qty[store_id][product_id] += delivered
                    remaining_request -= delivered
                    if batch.qty > delivered:
                        batch.qty -= delivered
                        product_pools[product_id].appendleft(batch)

                service_level = (
                    round((store_received_qty[store_id][product_id] / requested) * 100, 2)
                    if requested > 0
                    else 100.0
                )
                service_level_by_store[store_id][product_id] = service_level
                if not uses_raw_store_allocation_receipts(CONFIG):
                    logs.log_csv(
                        "service_level_log",
                        [
                            round_no,
                            store_id,
                            product_id,
                            store_received_qty[store_id][product_id],
                            service_level,
                        ],
                    )
                logs.log_event(
                    {
                        "schemaVersion": SCHEMA_VERSION,
                        "type": "WHOLESALER_ALLOCATION_DONE",
                        "round": round_no,
                        "store_id": store_id,
                        "product_id": product_id,
                        "requested": requested,
                        "received": store_received_qty[store_id][product_id],
                        "service_level": service_level,
                        "message": (
                            f"{store_id} received {store_received_qty[store_id][product_id]}/{requested} "
                            f"units of {product_id} ({service_level:.2f}% service level)."
                        ),
                    }
                )

            if uses_raw_store_allocation_receipts(CONFIG):
                store_receipt = StoreAllocationReceiptRecord(
                    round_no=round_no,
                    store_id=store_id,
                    daily_sequence_no=store_sequence_no,
                    total_delivered_units=sum(store_received_qty[store_id].values()),
                )
                logs.write_raw_store_receipt(
                    store_receipt,
                    render_store_receipt(store_receipt),
                )

        for store in stores:
            for product_id in products:
                logs.log_csv(
                    "inventory_log",
                    [round_no, store.store_id, product_id, inventory_total(store.inventory[product_id])],
                )

        for product_id in products:
            bullwhip_history[product_id]["actual_demand"].append(actual_demand_by_product[product_id])
            bullwhip_history[product_id]["store_orders"].append(
                sum(store.current_order.get(product_id, 0) for store in stores)
            )

        snapshot = build_round_snapshot(
            round_no=round_no,
            products=products,
            stores=stores,
            producer_order=producer_order,
            store_order=store_queue,
            actual_demand_by_product=actual_demand_by_product,
            store_round_demand=store_round_demand,
            store_order_totals=store_order_totals,
            aggregated_demand_by_product=aggregated_demand_by_product,
            service_level_by_store=service_level_by_store,
            store_received_qty=store_received_qty,
            store_lost_qty=store_lost_qty,
            producer_to_wholesaler=producer_to_wholesaler,
            producer_unused=producer_unused,
        )
        logs.log_event(snapshot)

        total_stockouts = sum(
            store_lost_qty[store.store_id][product_id]
            for store in stores
            for product_id in products
        )
        critical_stores = [
            store.store_id
            for store in stores
            if any(service_level_by_store[store.store_id][product_id] < 30 for product_id in products)
        ]
        logs.write_output(
            f"Day {round_no}: demand={sum(actual_demand_by_product.values())}, "
            f"orders={sum(aggregated_demand_by_product.values())}, stockouts={total_stockouts}, "
            f"critical_stores={','.join(critical_stores) if critical_stores else 'none'}"
        )

    amplification_scores: dict[str, float] = {}
    for product_id in products:
        demand_series = bullwhip_history[product_id]["actual_demand"]
        order_series = bullwhip_history[product_id]["store_orders"]
        avg_demand = sum(demand_series) / max(len(demand_series), 1)
        avg_orders = sum(order_series) / max(len(order_series), 1)
        amplification_scores[product_id] = round(avg_orders / avg_demand, 4) if avg_demand > 0 else 0.0

    strongest_product = max(amplification_scores, key=amplification_scores.get)
    logs.write_text_file(
        "answer.txt",
        build_confirmed_answer(
            products,
            confirmed_rejections_by_product,
        )
        + "\n",
    )
    logs.write_json_file(
        "bullwhip_summary.json",
        {
            "schemaVersion": SCHEMA_VERSION,
            "strongest_product": strongest_product,
            "amplification_scores": amplification_scores,
        },
    )

    logs.write_output("")
    logs.write_output("== Final Summary ==")
    logs.write_output(f"Strongest bullwhip product: {strongest_product}")
    for product_id, score in amplification_scores.items():
        logs.write_output(f"{product_id}: amplification={score}")

    logs.close()


if __name__ == "__main__":
    main()
