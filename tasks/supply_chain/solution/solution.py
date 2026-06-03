from __future__ import annotations

import csv
import json
import re
from collections import defaultdict, deque
from pathlib import Path

import numpy as np


MAX_LAG_DAYS = 14
BASELINE_SMOOTHING_DAYS = 7
RIDGE_ALPHA = 1.0
ABSOLUTE_SCORE_FLOOR = 0.02
RELATIVE_SCORE_THRESHOLD = 0.45
MIN_WEIGHTED_SUPPORT = 2.0
PURE_BONUS_WEIGHT = 0.2
WEIGHTED_EFFECT_WEIGHT = 0.35
REGRESSION_WEIGHT = 0.45


def resolve_dataset_dir() -> Path:
    candidates = [
        Path("/app"),
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
    ]
    for candidate in candidates:
        if (candidate / "raw_orders").exists() and (candidate / "sales_log.csv").exists():
            return candidate
    return Path("/app")


def sort_agent_ids(agent_ids: set[str]) -> list[str]:
    return sorted(agent_ids, key=lambda agent_id: int(agent_id.split("_")[1]))


def parse_raw_orders(raw_orders_dir: Path) -> dict[tuple[int, str], dict[str, int]]:
    raw_orders: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for path in sorted(raw_orders_dir.iterdir()):
        if not path.is_file():
            continue

        match = re.match(r"day_(\d+)_(S_\d+)_(.+)\.(json|csv|txt)$", path.name)
        if match is None:
            continue

        day = int(match.group(1))
        store_id = match.group(2)
        order_format = match.group(3)
        content = path.read_text(encoding="utf-8").strip()
        items: list[tuple[str, int]] = []

        if order_format == "api-json":
            payload = json.loads(content)
            items = [(str(item["prod_id"]), int(item["qty"])) for item in payload["items"]]
        elif order_format == "table-csv":
            for line in content.splitlines()[1:]:
                if not line.strip():
                    continue
                product_id, qty = line.split(";")
                items.append((product_id, int(qty)))
        elif order_format == "text-template":
            for line in content.splitlines():
                result = re.search(r"(\d+) units of product (P_\d+)", line)
                if result is not None:
                    items.append((result.group(2), int(result.group(1))))
        elif order_format == "key-value":
            for line in content.splitlines():
                result = re.search(r"ORDER_PRODUCT: (P_\d+) \| ORDER_QTY: (\d+)", line)
                if result is not None:
                    items.append((result.group(1), int(result.group(2))))

        for product_id, qty in items:
            raw_orders[(day, store_id)][product_id] += qty

    return {key: dict(value) for key, value in raw_orders.items()}


def parse_raw_supplier_receipts(
    raw_supplier_receipts_dir: Path,
) -> tuple[dict[tuple[int, str], dict[str, int]], set[str], int]:
    delivered_to_wholesaler: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    products: set[str] = set()
    max_day = 0

    if not raw_supplier_receipts_dir.exists():
        return {}, set(), 0

    for path in sorted(raw_supplier_receipts_dir.iterdir()):
        if not path.is_file():
            continue

        match = re.match(r"day_(\d+)_(PR_\d+)_(.+)\.(json|csv|txt)$", path.name)
        if match is None:
            continue

        day = int(match.group(1))
        producer_id = match.group(2)
        receipt_format = match.group(3)
        content = path.read_text(encoding="utf-8").strip()
        items: list[tuple[str, int]] = []

        if receipt_format == "api-json":
            payload = json.loads(content)
            items = [
                (str(item["prod_id"]), int(item["delivered_qty"]))
                for item in payload["items"]
            ]
        elif receipt_format == "table-csv":
            for line in content.splitlines()[1:]:
                if not line.strip():
                    continue
                product_id, qty = line.split(";")
                items.append((product_id, int(qty)))
        elif receipt_format == "text-template":
            for line in content.splitlines():
                result = re.search(r"delivered (\d+) units of product (P_\d+)", line)
                if result is not None:
                    items.append((result.group(2), int(result.group(1))))
        elif receipt_format == "key-value":
            for line in content.splitlines():
                result = re.search(r"PRODUCT: (P_\d+) \| DELIVERED_QTY: (\d+)", line)
                if result is not None:
                    items.append((result.group(1), int(result.group(2))))

        for product_id, qty in items:
            delivered_to_wholesaler[(day, producer_id)][product_id] += qty
            products.add(product_id)
        max_day = max(max_day, day)

    return (
        {key: dict(value) for key, value in delivered_to_wholesaler.items()},
        products,
        max_day,
    )


def parse_legacy_supply_tables(
    sourcing_log_file: Path,
    supply_production_log_file: Path,
) -> tuple[dict[tuple[int, str], dict[str, int]], dict[int, list[str]], set[str], int]:
    delivered_to_wholesaler: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    producer_order_by_day: dict[int, list[str]] = defaultdict(list)
    seen_producers_by_day: dict[int, set[str]] = defaultdict(set)
    products: set[str] = set()
    max_day = 0

    if sourcing_log_file.exists():
        with sourcing_log_file.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                day = int(row["Day"])
                product_id = row["Product_ID"]
                producer_id = row["Producer_ID"]
                qty = int(row["Collected_Quantity"])
                delivered_to_wholesaler[(day, producer_id)][product_id] += qty
                products.add(product_id)
                max_day = max(max_day, day)

    if supply_production_log_file.exists():
        with supply_production_log_file.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                day = int(row["Day"])
                producer_id = row["Producer_ID"]
                product_id = row["Product_ID"]
                if producer_id not in seen_producers_by_day[day]:
                    seen_producers_by_day[day].add(producer_id)
                    producer_order_by_day[day].append(producer_id)
                products.add(product_id)
                max_day = max(max_day, day)

    return (
        {key: dict(value) for key, value in delivered_to_wholesaler.items()},
        dict(producer_order_by_day),
        products,
        max_day,
    )


def parse_raw_wholesaler_receipts(
    raw_wholesaler_receipts_dir: Path,
) -> tuple[dict[int, list[str]], int]:
    receipts_by_day: dict[int, list[tuple[int, str]]] = defaultdict(list)
    max_day = 0

    if not raw_wholesaler_receipts_dir.exists():
        return {}, 0

    for path in sorted(raw_wholesaler_receipts_dir.iterdir()):
        if not path.is_file():
            continue

        match = re.match(r"day_(\d+)_(PR_\d+)_receipt\.txt$", path.name)
        if match is None:
            continue

        day = int(match.group(1))
        producer_id = match.group(2)
        content = path.read_text(encoding="utf-8")
        sequence_match = re.search(r"DAILY_SEQUENCE_NO: (\d+)", content)
        if sequence_match is None:
            continue

        receipts_by_day[day].append((int(sequence_match.group(1)), producer_id))
        max_day = max(max_day, day)

    producer_order_by_day = {
        day: [producer_id for _seq, producer_id in sorted(items)]
        for day, items in receipts_by_day.items()
    }
    return producer_order_by_day, max_day


def parse_raw_store_receipts(
    raw_store_receipts_dir: Path,
) -> tuple[dict[int, list[str]], int]:
    receipts_by_day: dict[int, list[tuple[int, str]]] = defaultdict(list)
    max_day = 0

    if not raw_store_receipts_dir.exists():
        return {}, 0

    for path in sorted(raw_store_receipts_dir.iterdir()):
        if not path.is_file():
            continue

        match = re.match(r"day_(\d+)_(S_\d+)_receipt\.txt$", path.name)
        if match is None:
            continue

        day = int(match.group(1))
        store_id = match.group(2)
        content = path.read_text(encoding="utf-8")
        sequence_match = re.search(r"DAILY_SEQUENCE_NO: (\d+)", content)
        if sequence_match is None:
            continue

        receipts_by_day[day].append((int(sequence_match.group(1)), store_id))
        max_day = max(max_day, day)

    store_queue_by_day = {
        day: [store_id for _seq, store_id in sorted(items)]
        for day, items in receipts_by_day.items()
    }
    return store_queue_by_day, max_day


def parse_store_queue_from_service_level(service_level_file: Path) -> tuple[dict[int, list[str]], int]:
    store_queue_by_day: dict[int, list[str]] = defaultdict(list)
    seen_stores_by_day: dict[int, set[str]] = defaultdict(set)
    max_day = 0

    if not service_level_file.exists():
        return {}, 0

    with service_level_file.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            day = int(row["Day"])
            store_id = row["Store_ID"]
            if store_id not in seen_stores_by_day[day]:
                seen_stores_by_day[day].add(store_id)
                store_queue_by_day[day].append(store_id)
            max_day = max(max_day, day)

    return dict(store_queue_by_day), max_day


def parse_sales(
    sales_file: Path,
) -> tuple[dict[int, list[tuple[str, str, int, int]]], dict[tuple[str, str, int], int], int]:
    sales_rows_by_day: dict[int, list[tuple[str, str, int, int]]] = defaultdict(list)
    demand_event_counts: dict[tuple[str, str, int], int] = defaultdict(int)
    max_day = 0

    with sales_file.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            day = int(row["Day"])
            store_id = row["Store_ID"]
            product_id = row["Product_ID"]
            demand = int(row["Reported_Demand"])
            sold = int(row["Sold_Quantity"])
            sales_rows_by_day[day].append((store_id, product_id, demand, sold))
            demand_event_counts[(store_id, product_id, day)] += 1
            max_day = max(max_day, day)

    return dict(sales_rows_by_day), demand_event_counts, max_day


def aggregate_daily_sales(
    sales_rows_by_day: dict[int, list[tuple[str, str, int, int]]],
) -> tuple[
    dict[tuple[str, str, int], int],
    dict[tuple[str, str, int], int],
    dict[tuple[str, str, int], int],
]:
    daily_reported_demand: dict[tuple[str, str, int], int] = defaultdict(int)
    daily_sold_qty: dict[tuple[str, str, int], int] = defaultdict(int)
    daily_lost_sales: dict[tuple[str, str, int], int] = defaultdict(int)

    for day, rows in sales_rows_by_day.items():
        for store_id, product_id, demand, sold in rows:
            key = (store_id, product_id, day)
            daily_reported_demand[key] += demand
            daily_sold_qty[key] += sold
            daily_lost_sales[key] += max(demand - sold, 0)

    return dict(daily_reported_demand), dict(daily_sold_qty), dict(daily_lost_sales)


def moving_average(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    radius = max(window // 2, 0)
    smoothed: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        smoothed.append(float(sum(values[start:end])) / max(end - start, 1))
    return smoothed


def build_store_product_means(
    stores: list[str],
    ordered_products: list[str],
    max_day: int,
    daily_reported_demand: dict[tuple[str, str, int], int],
) -> dict[tuple[str, str], float]:
    means: dict[tuple[str, str], float] = {}
    for store_id in stores:
        for product_id in ordered_products:
            total = sum(daily_reported_demand.get((store_id, product_id, day), 0) for day in range(1, max_day + 1))
            means[(store_id, product_id)] = float(total) / max(max_day, 1)
    return means


def estimate_daily_baseline(
    stores: list[str],
    ordered_products: list[str],
    max_day: int,
    daily_reported_demand: dict[tuple[str, str, int], int],
) -> tuple[dict[tuple[str, str, int], float], dict[tuple[str, str], float]]:
    store_product_means = build_store_product_means(stores, ordered_products, max_day, daily_reported_demand)
    baseline: dict[tuple[str, str, int], float] = {}

    for product_id in ordered_products:
        raw_factors: list[float] = []
        for day in range(1, max_day + 1):
            ratios: list[float] = []
            for store_id in stores:
                mean_value = store_product_means[(store_id, product_id)]
                if mean_value <= 0:
                    continue
                ratios.append(daily_reported_demand.get((store_id, product_id, day), 0) / mean_value)
            raw_factors.append(float(np.median(ratios)) if ratios else 1.0)

        smoothed_factors = moving_average(raw_factors, BASELINE_SMOOTHING_DAYS)
        for store_id in stores:
            mean_value = store_product_means[(store_id, product_id)]
            for day in range(1, max_day + 1):
                factor = smoothed_factors[day - 1] if smoothed_factors else 1.0
                baseline[(store_id, product_id, day)] = max(0.0, mean_value * factor)

    return baseline, store_product_means


def build_answer_payload(answer_by_product: dict[str, set[str]], ordered_products: list[str]) -> dict[str, list[str]]:
    return {
        product_id: sort_agent_ids(answer_by_product.get(product_id, set()))
        for product_id in ordered_products
    }


def reconstruct_sales_metrics(
    raw_orders: dict[tuple[int, str], dict[str, int]],
    delivered_to_wholesaler: dict[tuple[int, str], dict[str, int]],
    ordered_products: list[str],
    producer_order_by_day: dict[int, list[str]],
    sales_rows_by_day: dict[int, list[tuple[str, str, int, int]]],
    store_queue_by_day: dict[int, list[str]],
    max_day: int,
) -> tuple[
    dict[str, list[tuple[str, int, tuple[str, ...]]]],
    dict[str, dict[tuple[str, int], dict[str, int]]],
    list[str],
]:
    stores = sorted(
        {store_id for _, store_id in raw_orders.keys()},
        key=lambda store_id: int(store_id.split("_")[1]),
    )
    inventory: dict[str, dict[str, deque[tuple[str, int]]]] = {
        store_id: {product_id: deque() for product_id in ordered_products}
        for store_id in stores
    }
    producer_sets_by_product: dict[str, list[tuple[str, int, tuple[str, ...]]]] = defaultdict(list)
    producer_contributions_by_product: dict[str, dict[tuple[str, int], dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )

    for day in range(1, max_day + 1):
        for store_id, product_id, _demand, sold in sales_rows_by_day.get(day, []):
            remaining = sold
            contributing_batches: list[tuple[str, int]] = []
            while remaining > 0 and inventory[store_id][product_id]:
                producer_id, batch_qty = inventory[store_id][product_id][0]
                delivered = min(remaining, batch_qty)
                contributing_batches.append((producer_id, delivered))
                remaining -= delivered
                batch_qty -= delivered

                if batch_qty == 0:
                    inventory[store_id][product_id].popleft()
                else:
                    inventory[store_id][product_id][0] = (producer_id, batch_qty)

            if sold > 0 and contributing_batches:
                producer_set = tuple(
                    sort_agent_ids({producer_id for producer_id, _ in contributing_batches})
                )
                producer_sets_by_product[product_id].append((store_id, day, producer_set))
                contribution_bucket = producer_contributions_by_product[product_id][(store_id, day)]
                for producer_id, delivered in contributing_batches:
                    contribution_bucket[producer_id] += delivered

        pools: dict[str, deque[list[str | int]]] = {product_id: deque() for product_id in ordered_products}
        for producer_id in producer_order_by_day.get(day, []):
            receipt_items = delivered_to_wholesaler.get((day, producer_id), {})
            for product_id in ordered_products:
                qty = receipt_items.get(product_id, 0)
                if qty > 0:
                    pools[product_id].append([producer_id, qty])

        for store_id in store_queue_by_day.get(day, []):
            order_items = raw_orders.get((day, store_id), {})
            for product_id in ordered_products:
                remaining = order_items.get(product_id, 0)
                while remaining > 0 and pools[product_id]:
                    producer_id, batch_qty = pools[product_id][0]
                    delivered = min(remaining, int(batch_qty))
                    inventory[store_id][product_id].append((str(producer_id), delivered))
                    remaining -= delivered
                    batch_qty = int(batch_qty) - delivered

                    if batch_qty == 0:
                        pools[product_id].popleft()
                    else:
                        pools[product_id][0] = [producer_id, batch_qty]

    normalized_contributions = {
        product_id: {
            key: dict(contributions)
            for key, contributions in exposure_map.items()
        }
        for product_id, exposure_map in producer_contributions_by_product.items()
    }
    return producer_sets_by_product, normalized_contributions, stores


def reconstruct_sales_flow(
    raw_orders: dict[tuple[int, str], dict[str, int]],
    delivered_to_wholesaler: dict[tuple[int, str], dict[str, int]],
    ordered_products: list[str],
    producer_order_by_day: dict[int, list[str]],
    sales_rows_by_day: dict[int, list[tuple[str, str, int, int]]],
    store_queue_by_day: dict[int, list[str]],
    max_day: int,
) -> tuple[
    dict[str, list[tuple[str, int, tuple[str, ...]]]],
    list[str],
]:
    producer_sets_by_product, _producer_contributions_by_product, stores = reconstruct_sales_metrics(
        raw_orders=raw_orders,
        delivered_to_wholesaler=delivered_to_wholesaler,
        ordered_products=ordered_products,
        producer_order_by_day=producer_order_by_day,
        sales_rows_by_day=sales_rows_by_day,
        store_queue_by_day=store_queue_by_day,
        max_day=max_day,
    )
    return producer_sets_by_product, stores


def build_shortfall_ratio(
    stores: list[str],
    product_id: str,
    max_day: int,
    baseline: dict[tuple[str, str, int], float],
    daily_reported_demand: dict[tuple[str, str, int], int],
) -> dict[tuple[str, int], float]:
    shortfall_ratio: dict[tuple[str, int], float] = {}
    for store_id in stores:
        for day in range(1, max_day + 1):
            baseline_value = baseline.get((store_id, product_id, day), 0.0)
            actual = daily_reported_demand.get((store_id, product_id, day), 0)
            shortfall_ratio[(store_id, day)] = max(0.0, baseline_value - actual) / max(baseline_value, 1.0)
    return shortfall_ratio


def build_adjusted_shortfall_ratio(
    stores: list[str],
    raw_shortfall_ratio: dict[tuple[str, int], float],
    max_day: int,
) -> dict[tuple[str, int], float]:
    adjusted: dict[tuple[str, int], float] = {}
    for day in range(1, max_day + 1):
        day_values = [raw_shortfall_ratio.get((store_id, day), 0.0) for store_id in stores]
        day_median = float(np.median(day_values)) if day_values else 0.0
        for store_id in stores:
            adjusted[(store_id, day)] = raw_shortfall_ratio.get((store_id, day), 0.0) - day_median
    return adjusted


def ridge_regression(
    design_rows: list[list[float]],
    targets: list[float],
    alpha: float,
    unpenalized_columns: int,
) -> np.ndarray:
    if not design_rows:
        return np.zeros(0, dtype=float)

    design = np.array(design_rows, dtype=float)
    target = np.array(targets, dtype=float)
    regularization = np.eye(design.shape[1], dtype=float) * alpha
    regularization[:unpenalized_columns, :unpenalized_columns] = 0.0
    xtx = design.T @ design
    xty = design.T @ target
    return np.linalg.solve(xtx + regularization, xty)


def future_drop_score(
    store_id: str,
    day: int,
    max_day: int,
    adjusted_shortfall_ratio: dict[tuple[str, int], float],
) -> float:
    values = [
        max(0.0, adjusted_shortfall_ratio.get((store_id, future_day), 0.0))
        for future_day in range(day + 1, min(max_day, day + MAX_LAG_DAYS) + 1)
    ]
    return float(sum(values)) / max(len(values), 1)


def infer_confirmed_for_product(
    product_id: str,
    stores: list[str],
    producers: list[str],
    max_day: int,
    product_contributions_by_day: dict[tuple[str, int], dict[str, int]],
    daily_reported_demand: dict[tuple[str, str, int], int],
    baseline: dict[tuple[str, str, int], float],
    store_product_means: dict[tuple[str, str], float],
) -> set[str]:
    if not producers or max_day <= MAX_LAG_DAYS:
        return set()

    shortfall_ratio = build_shortfall_ratio(stores, product_id, max_day, baseline, daily_reported_demand)
    adjusted_shortfall_ratio = build_adjusted_shortfall_ratio(stores, shortfall_ratio, max_day)
    feature_rows: list[list[float]] = []
    targets: list[float] = []

    for store_id in stores:
        scale = max(store_product_means[(store_id, product_id)], 1.0)
        for day in range(MAX_LAG_DAYS + 1, max_day + 1):
            row = [1.0]
            for fixed_effect_store in stores[1:]:
                row.append(1.0 if store_id == fixed_effect_store else 0.0)
            for producer_id in producers:
                for lag in range(1, MAX_LAG_DAYS + 1):
                    contributions = product_contributions_by_day.get((store_id, day - lag), {})
                    row.append(contributions.get(producer_id, 0) / scale)
            feature_rows.append(row)
            targets.append(adjusted_shortfall_ratio[(store_id, day)])

    coefficients = ridge_regression(
        feature_rows,
        targets,
        alpha=RIDGE_ALPHA,
        unpenalized_columns=len(stores),
    )

    producer_regression_scores: dict[str, float] = {}
    offset = len(stores)
    for producer_index, producer_id in enumerate(producers):
        start = offset + producer_index * MAX_LAG_DAYS
        end = start + MAX_LAG_DAYS
        lag_coefficients = coefficients[start:end]
        producer_regression_scores[producer_id] = float(sum(max(0.0, coefficient) for coefficient in lag_coefficients))

    weighted_effect_sum: dict[str, float] = defaultdict(float)
    weighted_support_units: dict[str, float] = defaultdict(float)
    pure_effect_sum: dict[str, float] = defaultdict(float)
    pure_support_days: dict[str, int] = defaultdict(int)

    for (store_id, day), contributions in product_contributions_by_day.items():
        total_units = sum(contributions.values())
        if total_units <= 0:
            continue

        store_scale = max(store_product_means[(store_id, product_id)], 1.0)
        drop_score = future_drop_score(store_id, day, max_day, adjusted_shortfall_ratio)
        for producer_id, units in contributions.items():
            normalized_units = units / store_scale
            weighted_effect_sum[producer_id] += normalized_units * drop_score
            weighted_support_units[producer_id] += normalized_units

        if len(contributions) == 1:
            producer_id = next(iter(contributions))
            pure_effect_sum[producer_id] += drop_score
            pure_support_days[producer_id] += 1

    combined_scores: dict[str, float] = {}
    pure_average_scores: dict[str, float] = {}
    weighted_average_scores: dict[str, float] = {}
    for producer_id in producers:
        weighted_avg = weighted_effect_sum[producer_id] / max(weighted_support_units[producer_id], 1e-9)
        pure_avg = pure_effect_sum[producer_id] / max(pure_support_days[producer_id], 1)
        weighted_average_scores[producer_id] = weighted_avg
        pure_average_scores[producer_id] = pure_avg
        combined_scores[producer_id] = (
            REGRESSION_WEIGHT * producer_regression_scores[producer_id]
            + WEIGHTED_EFFECT_WEIGHT * weighted_avg
            + PURE_BONUS_WEIGHT * pure_avg
        )

    best_score = max(combined_scores.values(), default=0.0)
    if best_score < ABSOLUTE_SCORE_FLOOR:
        return set()

    support_threshold = max(
        MIN_WEIGHTED_SUPPORT,
        0.15 * max(weighted_support_units.values(), default=0.0),
    )
    score_threshold = max(ABSOLUTE_SCORE_FLOOR, RELATIVE_SCORE_THRESHOLD * best_score)

    confirmed = {
        producer_id
        for producer_id in producers
        if combined_scores[producer_id] >= score_threshold
        and weighted_support_units[producer_id] >= support_threshold
        and (
            pure_support_days[producer_id] > 0
            or weighted_average_scores[producer_id] >= 0.5 * max(weighted_average_scores.values(), default=0.0)
            or producer_regression_scores[producer_id] >= 0.75 * max(producer_regression_scores.values(), default=0.0)
        )
    }
    return confirmed


def solve() -> str:
    dataset_dir = resolve_dataset_dir()
    raw_orders = parse_raw_orders(dataset_dir / "raw_orders")
    delivered_to_wholesaler, products, supplier_max_day = parse_raw_supplier_receipts(
        dataset_dir / "raw_supplier_receipts"
    )
    producer_order_by_day, wholesaler_max_day = parse_raw_wholesaler_receipts(
        dataset_dir / "raw_wholesaler_receipts"
    )
    if not delivered_to_wholesaler and not producer_order_by_day:
        (
            delivered_to_wholesaler,
            producer_order_by_day,
            products,
            supplier_max_day,
        ) = parse_legacy_supply_tables(
            dataset_dir / "sourcing_log.csv",
            dataset_dir / "supply_production_log.csv",
        )
        wholesaler_max_day = supplier_max_day
    store_queue_by_day, raw_store_queue_max_day = parse_raw_store_receipts(
        dataset_dir / "raw_wholesaler_store_receipts"
    )
    if not store_queue_by_day:
        store_queue_by_day, raw_store_queue_max_day = parse_store_queue_from_service_level(
            dataset_dir / "service_level_log.csv"
        )
    sales_rows_by_day, _demand_event_counts, sales_max_day = parse_sales(dataset_dir / "sales_log.csv")
    daily_reported_demand, _daily_sold_qty, _daily_lost_sales = aggregate_daily_sales(sales_rows_by_day)

    max_day = max(supplier_max_day, wholesaler_max_day, raw_store_queue_max_day, sales_max_day)
    ordered_products = sorted(products, key=lambda product_id: int(product_id.split("_")[1]))
    (
        producer_sets_by_product,
        producer_contributions_by_product,
        stores,
    ) = reconstruct_sales_metrics(
        raw_orders=raw_orders,
        delivered_to_wholesaler=delivered_to_wholesaler,
        ordered_products=ordered_products,
        producer_order_by_day=producer_order_by_day,
        sales_rows_by_day=sales_rows_by_day,
        store_queue_by_day=store_queue_by_day,
        max_day=max_day,
    )
    baseline, store_product_means = estimate_daily_baseline(
        stores=stores,
        ordered_products=ordered_products,
        max_day=max_day,
        daily_reported_demand=daily_reported_demand,
    )

    inferred_by_product: dict[str, set[str]] = {}
    for product_id in ordered_products:
        contributions = producer_contributions_by_product.get(product_id, {})
        producers = sort_agent_ids(
            {
                producer_id
                for producer_set_entries in producer_sets_by_product.get(product_id, [])
                for producer_id in producer_set_entries[2]
            }
            | {
                producer_id
                for exposure in contributions.values()
                for producer_id in exposure
            }
        )
        inferred_by_product[product_id] = infer_confirmed_for_product(
            product_id=product_id,
            stores=stores,
            producers=producers,
            max_day=max_day,
            product_contributions_by_day=contributions,
            daily_reported_demand=daily_reported_demand,
            baseline=baseline,
            store_product_means=store_product_means,
        )

    answer = json.dumps(
        build_answer_payload(inferred_by_product, ordered_products),
        ensure_ascii=False,
        indent=2,
    )
    print(answer)
    return answer


if __name__ == "__main__":
    solve()
