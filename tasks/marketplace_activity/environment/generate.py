from __future__ import annotations

import csv
import json
import math
import os
import time
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
        "or run this generator with `uv run python harbor/tasks/marketplace_activity/environment/generate.py`."
    ) from exc


PROJECT_NAME = "marketplace activity"


CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "seed": 42,
    "rng_bit_generator": "PCG64",
    "simulation_start_date": "2025-01-01",
    "simulation_days": 180,
    "scale": {
        "n_users": 10000,
        "min_initial_listings_per_leaf_category": 18,
    },
    "locations": {
        "village_user_probability": 0.005,
        "village_activity_factor_range": [0.12, 0.35],
        "city_weights": {
            "Madrid": 0.145,
            "Barcelona": 0.122,
            "Valencia": 0.070,
            "Sevilla": 0.052,
            "Zaragoza": 0.043,
            "Malaga": 0.039,
            "Murcia": 0.034,
            "Palma": 0.032,
            "Las Palmas": 0.030,
            "Bilbao": 0.030,
            "Alicante": 0.029,
            "Cordoba": 0.024,
            "Valladolid": 0.023,
            "Vigo": 0.023,
            "Gijon": 0.021,
            "A Coruna": 0.020,
            "Granada": 0.020,
            "Elche": 0.019,
            "Oviedo": 0.018,
            "Santander": 0.017,
            "San Sebastian": 0.017,
            "Pamplona": 0.016,
            "Toledo": 0.015,
            "Salamanca": 0.015,
            "Burgos": 0.013,
            "Logrono": 0.012,
            "Leon": 0.012,
            "Cadiz": 0.012,
            "Almeria": 0.011,
            "Girona": 0.010,
        },
        "city_activity_factor": {
            "Madrid": 1.26,
            "Barcelona": 1.23,
            "Valencia": 1.13,
            "Sevilla": 1.09,
            "Zaragoza": 1.02,
            "Malaga": 1.08,
            "Murcia": 0.97,
            "Palma": 1.02,
            "Las Palmas": 0.88,
            "Bilbao": 0.96,
            "Alicante": 1.00,
            "Cordoba": 0.89,
            "Valladolid": 0.90,
            "Vigo": 0.92,
            "Gijon": 0.89,
            "A Coruna": 0.95,
            "Granada": 1.04,
            "Elche": 0.85,
            "Oviedo": 0.86,
            "Santander": 0.82,
            "San Sebastian": 1.10,
            "Pamplona": 0.94,
            "Toledo": 0.76,
            "Salamanca": 0.84,
            "Burgos": 0.78,
            "Logrono": 0.75,
            "Leon": 0.73,
            "Cadiz": 0.86,
            "Almeria": 0.82,
            "Girona": 0.87,
        },
        "villages": [
            "Albarracin",
            "Ainsa",
            "Besalu",
            "Comillas",
            "Frias",
            "Valldemossa",
            "Cudillero",
            "Potes",
            "Pedraza",
            "Mojacar",
            "Brihuega",
            "Maderuelo",
            "Alquezar",
            "Carmona",
            "Zahara",
            "Medinaceli",
            "Lastres",
            "Cadaqués",
            "Sepulveda",
            "Morella",
            "Lekeitio",
            "Tazones",
            "Capileira",
            "Bubion",
            "Candelario",
            "Rupit",
            "Miravet",
            "Pals",
            "Trujillo",
            "Covarrubias",
            "Setenil",
            "Ujue",
            "Alcala del Jucar",
            "Bulnes",
            "Tejeda",
            "Garachico",
            "Santillana",
            "Olite",
            "Sos del Rey",
            "Castrillo",
            "Zuheros",
            "Aracena",
            "Luarca",
            "Priego",
            "Buitrago",
            "Atienza",
            "Onati",
            "Laguardia",
            "Ezcaray",
            "Mogarraz",
            "Hervas",
            "Cazorla",
            "Montefrio",
            "Mondonedo",
            "Tui",
            "Cangas",
            "Betanzos",
            "Muxia",
            "Artajona",
            "Yanguas",
        ],
    },
    "catalog": {
        "category_tree": {
            "Fashion": [
                "Women's Clothing",
                "Men's Clothing",
                "Women's Shoes",
                "Men's Shoes",
                "Bags",
                "Watches",
                "Jewelry",
                "Formalwear",
            ],
            "Electronics": [
                "Phones",
                "Computers",
                "Cameras",
                "Audio",
                "Consoles",
                "Video Games",
                "Components",
                "Appliances",
            ],
            "Home": [
                "Furniture",
                "Decor",
                "Kitchen",
                "Lighting",
                "Garden",
                "Tools",
                "Home Textiles",
                "Cleaning",
            ],
            "Leisure": [
                "Books",
                "Music",
                "Movies",
                "Musical Instruments",
                "Art",
                "Collectibles",
                "Toys",
                "Board Games",
            ],
            "Vehicles": [
                "Cars",
                "Motorcycles",
                "Spare Parts",
                "Tires",
                "Car Accessories",
                "Helmets",
                "Motor Tools",
                "Navigation",
            ],
            "Family": [
                "Baby",
                "Strollers",
                "Children's Clothing",
                "Child Seats",
                "School Supplies",
                "Pets",
                "Personal Care",
                "Luggage",
            ],
            "Sports": [
                "Bicycles",
                "Fitness",
                "Camping",
                "Fishing",
                "Hiking",
                "Skates",
                "Sportswear",
                "Balls",
            ],
            "Services": [
                "Tutoring",
                "Repairs",
                "Moving",
                "Photography",
                "Beauty",
                "Events",
                "Training",
                "Catering",
            ],
        },
        "price_range_by_parent": {
            "Fashion": [5.0, 160.0],
            "Electronics": [12.0, 1100.0],
            "Home": [4.0, 600.0],
            "Leisure": [3.0, 500.0],
            "Vehicles": [8.0, 8000.0],
            "Family": [3.0, 500.0],
            "Sports": [4.0, 1500.0],
            "Services": [15.0, 600.0],
        },
        "parent_search_weight": {
            "Fashion": 1.18,
            "Electronics": 1.10,
            "Home": 0.95,
            "Leisure": 0.86,
            "Vehicles": 0.72,
            "Family": 0.80,
            "Sports": 0.78,
            "Services": 0.64,
        },
        "parent_supply_weight": {
            "Fashion": 1.06,
            "Electronics": 1.00,
            "Home": 0.92,
            "Leisure": 0.88,
            "Vehicles": 0.68,
            "Family": 0.82,
            "Sports": 0.77,
            "Services": 0.62,
        },
    },
    "low_activity": {
        "category_selection_multiplier": 1.00,
        "impression_multiplier": 0.64,
        "click_multiplier": 0.6,
        "favorite_multiplier": 0.56,
        "purchase_multiplier": 0.62,
        "seller_city_visibility_multiplier": 1.0,
        "city_category_names": {
            "Bilbao": ["Women's Shoes", "Bags", "Formalwear"],
            "Zaragoza": ["Cameras", "Musical Instruments", "Collectibles"],
            "Sevilla": ["Consoles", "Video Games", "Computers"],
            "Valencia": ["Bicycles", "Tools", "Furniture"],
            "Madrid": ["Garden", "Pets", "Fitness"],
            "Barcelona": ["Books", "Art", "Decor"],
        },
    },
    "activity": {
        "weekday_session_multipliers": [0.92, 0.96, 1.00, 1.05, 1.12, 1.22, 0.86],
        "inactive_user_session_multiplier": 0.0,
        "seller_listing_weekday_multipliers": [1.18, 1.16, 1.12, 1.08, 0.96, 0.55, 0.42],
        "seconds_between_feed_events_range": [2, 26],
    },
    "public_user_type_mix_by_behavior": {
        "casual_browser": {"regular": 0.86, "verified": 0.14, "business": 0.00},
        "intent_buyer": {"regular": 0.72, "verified": 0.28, "business": 0.00},
        "bargain_hunter": {"regular": 0.88, "verified": 0.12, "business": 0.00},
        "impulse_buyer": {"regular": 0.91, "verified": 0.09, "business": 0.00},
        "collector_enthusiast": {"regular": 0.58, "verified": 0.41, "business": 0.01},
        "power_seller": {"regular": 0.02, "verified": 0.20, "business": 0.78},
        "casual_seller": {"regular": 0.70, "verified": 0.25, "business": 0.05},
        "professional_seller": {"regular": 0.00, "verified": 0.14, "business": 0.86},
        "inactive_dormant": {"regular": 0.96, "verified": 0.04, "business": 0.00},
    },
    "user_groups": {
        "casual_browser": {
            "share": 0.270,
            "is_active_probability": 0.94,
            "avg_session_time_range": [4.5, 17.0],
            "daily_session_probability": 0.035,
            "searches_per_session": [1, 2],
            "impressions_per_search": [8, 18],
            "click_probability": 0.07,
            "favorite_probability": 0.050,
            "purchase_probability": 0.025,
            "cheap_preference": 0.35,
            "median_budget": 145.0,
            "local_listing_bonus": 1.05,
            "parent_affinity": {"Fashion": 1.08, "Electronics": 1.02, "Leisure": 1.08},
            "listing_daily_probability": 0.0,
            "listing_batch_range": [0, 0],
            "initial_listing_range": [0, 0],
            "seller_category_pool_size": [0, 0],
        },
        "intent_buyer": {
            "share": 0.150,
            "is_active_probability": 0.97,
            "avg_session_time_range": [3.0, 9.0],
            "daily_session_probability": 0.018,
            "searches_per_session": [1, 1],
            "impressions_per_search": [3, 8],
            "click_probability": 0.140,
            "favorite_probability": 0.040,
            "purchase_probability": 0.340,
            "cheap_preference": 0.40,
            "median_budget": 420.0,
            "local_listing_bonus": 1.08,
            "parent_affinity": {"Electronics": 1.20, "Home": 1.12, "Vehicles": 1.05},
            "listing_daily_probability": 0.0,
            "listing_batch_range": [0, 0],
            "initial_listing_range": [0, 0],
            "seller_category_pool_size": [0, 0],
        },
        "bargain_hunter": {
            "share": 0.150,
            "is_active_probability": 0.96,
            "avg_session_time_range": [13.0, 36.0],
            "daily_session_probability": 0.032,
            "searches_per_session": [1, 3],
            "impressions_per_search": [16, 34],
            "click_probability": 0.125,
            "favorite_probability": 0.340,
            "purchase_probability": 0.140,
            "cheap_preference": 1.45,
            "median_budget": 180.0,
            "local_listing_bonus": 1.04,
            "parent_affinity": {"Fashion": 1.12, "Home": 1.10, "Leisure": 1.15, "Family": 1.10},
            "listing_daily_probability": 0.0,
            "listing_batch_range": [0, 0],
            "initial_listing_range": [0, 0],
            "seller_category_pool_size": [0, 0],
        },
        "impulse_buyer": {
            "share": 0.120,
            "is_active_probability": 0.95,
            "avg_session_time_range": [2.0, 8.5],
            "daily_session_probability": 0.028,
            "searches_per_session": [1, 2],
            "impressions_per_search": [5, 11],
            "click_probability": 0.240,
            "favorite_probability": 0.060,
            "purchase_probability": 0.220,
            "cheap_preference": 1.85,
            "median_budget": 85.0,
            "cheap_purchase_ceiling": 75.0,
            "local_listing_bonus": 1.03,
            "parent_affinity": {"Fashion": 1.28, "Leisure": 1.22, "Family": 1.10},
            "listing_daily_probability": 0.0,
            "listing_batch_range": [0, 0],
            "initial_listing_range": [0, 0],
            "seller_category_pool_size": [0, 0],
        },
        "collector_enthusiast": {
            "share": 0.080,
            "is_active_probability": 0.98,
            "avg_session_time_range": [10.0, 28.0],
            "daily_session_probability": 0.060,
            "searches_per_session": [1, 2],
            "impressions_per_search": [6, 14],
            "click_probability": 0.110,
            "favorite_probability": 0.260,
            "purchase_probability": 0.110,
            "cheap_preference": 0.20,
            "median_budget": 260.0,
            "favorite_revisit_probability": 0.48,
            "local_listing_bonus": 1.06,
            "parent_affinity": {"Leisure": 1.55, "Electronics": 1.18, "Fashion": 1.05},
            "listing_daily_probability": 0.0,
            "listing_batch_range": [0, 0],
            "initial_listing_range": [0, 0],
            "seller_category_pool_size": [0, 0],
        },
        "power_seller": {
            "share": 0.035,
            "is_active_probability": 0.99,
            "avg_session_time_range": [18.0, 54.0],
            "daily_session_probability": 0.055,
            "searches_per_session": [1, 2],
            "impressions_per_search": [4, 10],
            "click_probability": 0.045,
            "favorite_probability": 0.080,
            "purchase_probability": 0.025,
            "cheap_preference": 0.70,
            "median_budget": 130.0,
            "local_listing_bonus": 1.00,
            "parent_affinity": {"Fashion": 1.08, "Electronics": 1.04, "Home": 1.04},
            "listing_daily_probability": 0.160,
            "listing_batch_range": [1, 4],
            "initial_listing_range": [8, 16],
            "seller_category_pool_size": [6, 12],
            "seller_visibility_multiplier": 1.18,
            "price_strategy": "broad",
        },
        "casual_seller": {
            "share": 0.075,
            "is_active_probability": 0.90,
            "avg_session_time_range": [4.0, 16.0],
            "daily_session_probability": 0.015,
            "searches_per_session": [1, 2],
            "impressions_per_search": [5, 12],
            "click_probability": 0.035,
            "favorite_probability": 0.070,
            "purchase_probability": 0.030,
            "cheap_preference": 0.60,
            "median_budget": 120.0,
            "local_listing_bonus": 1.04,
            "parent_affinity": {"Fashion": 1.03, "Home": 1.05, "Leisure": 1.05},
            "listing_daily_probability": 0.020,
            "listing_batch_range": [1, 2],
            "initial_listing_range": [1, 4],
            "seller_category_pool_size": [1, 4],
            "seller_visibility_multiplier": 0.92,
            "price_strategy": "loose",
        },
        "professional_seller": {
            "share": 0.040,
            "is_active_probability": 1.00,
            "avg_session_time_range": [22.0, 62.0],
            "daily_session_probability": 0.070,
            "searches_per_session": [1, 3],
            "impressions_per_search": [4, 9],
            "click_probability": 0.055,
            "favorite_probability": 0.100,
            "purchase_probability": 0.026,
            "cheap_preference": 0.85,
            "median_budget": 150.0,
            "local_listing_bonus": 0.98,
            "parent_affinity": {"Electronics": 1.08, "Fashion": 1.06, "Home": 1.05},
            "listing_daily_probability": 0.120,
            "listing_batch_range": [1, 3],
            "initial_listing_range": [6, 12],
            "seller_category_pool_size": [4, 9],
            "seller_visibility_multiplier": 1.10,
            "price_strategy": "optimized",
        },
        "inactive_dormant": {
            "share": 0.080,
            "is_active_probability": 0.0,
            "avg_session_time_range": [1.0, 5.0],
            "daily_session_probability": 0.0,
            "searches_per_session": [1, 1],
            "impressions_per_search": [2, 5],
            "click_probability": 0.015,
            "favorite_probability": 0.020,
            "purchase_probability": 0.006,
            "cheap_preference": 0.80,
            "median_budget": 70.0,
            "local_listing_bonus": 1.00,
            "parent_affinity": {},
            "listing_daily_probability": 0.0,
            "listing_batch_range": [0, 0],
            "initial_listing_range": [0, 0],
            "seller_category_pool_size": [0, 0],
        },
    },
    "listing_model": {
        "condition_weights": {
            "new": 0.20,
            "like_new": 0.24,
            "good": 0.40,
            "fair": 0.16,
        },
        "condition_price_multiplier": {
            "new": 1.14,
            "like_new": 1.03,
            "good": 0.84,
            "fair": 0.61,
        },
        "price_strategy_noise": {
            "optimized": [0.92, 1.02, 0.12],
            "broad": [0.82, 1.20, 0.24],
            "loose": [0.72, 1.34, 0.30],
            "default": [0.78, 1.28, 0.28],
        },
        "hot_listing_probability": 0.13,
        "weak_listing_probability": 0.20,
        "hot_listing_lognormal": [0.78, 0.24],
        "weak_listing_lognormal": [-0.82, 0.25],
        "normal_listing_lognormal": [0.00, 0.36],
        "recency_half_life_days": 26.0,
        "listing_expiration_days": 60,
        "position_click_decay": 0.090,
        "own_listing_impression_multiplier": 0.04,
    },
    "purchase_model": {
        "negotiation_discount_range_by_user_type": {
            "casual_browser": [0.00, 0.04],
            "intent_buyer": [0.00, 0.03],
            "bargain_hunter": [0.04, 0.18],
            "impulse_buyer": [0.00, 0.025],
            "collector_enthusiast": [0.00, 0.07],
            "power_seller": [0.00, 0.05],
            "casual_seller": [0.00, 0.05],
            "professional_seller": [0.00, 0.06],
            "inactive_dormant": [0.00, 0.02],
        },
        "shipping_base_range": [2.50, 12.00],
        "shipping_price_rate": 0.012,
        "shipping_max": 32.00,
    },
    "output": {
        "csv_split": "row_chunk",
        "rows_per_file": 25000,
        "write_simulation_output": False,
        "float_rounding": 4,
        "cleanup_outputs": True,
    },
}


STATIC_SCHEMAS: dict[str, list[str]] = {
    "user": [
        "user_id",
        "user_type",
        "city",
        "registration_date",
        "avg_session_time",
        "is_active",
    ],
    "category": ["category_id", "category_name", "parent_category_id"],
}


MONTHLY_SCHEMAS: dict[str, list[str]] = {
    "listing": [
        "listing_id",
        "seller_id",
        "category_id",
        "title",
        "price",
        "condition",
        "created_at",
        "expires_at",
    ],
    "search_event": [
        "search_id",
        "user_id",
        "query",
        "category_id",
        "timestamp",
        "results_count",
    ],
    "impression_event": [
        "impression_id",
        "user_id",
        "listing_id",
        "search_id",
        "position_in_feed",
        "source_type",
        "timestamp",
    ],
    "click_event": ["click_id", "user_id", "listing_id", "impression_id", "timestamp"],
    "favorite_event": ["favorite_id", "user_id", "listing_id", "timestamp"],
    "purchase": [
        "purchase_id",
        "buyer_id",
        "listing_id",
        "final_price",
        "shipping_cost",
        "purchase_time",
    ],
}


TITLE_ADJECTIVES = np.array(
    [
        "new",
        "clean",
        "urban",
        "light",
        "classic",
        "compact",
        "simple",
        "modern",
        "practical",
        "careful",
        "extra",
        "basic",
    ]
)

TITLE_NOUNS = np.array(
    [
        "lot",
        "piece",
        "pack",
        "model",
        "set",
        "item",
        "unit",
        "edition",
        "kit",
        "option",
    ]
)

QUERY_WORDS = np.array(
    [
        "cheap",
        "new",
        "nearby",
        "deal",
        "used",
        "fast",
        "good",
        "local",
        "small",
        "large",
    ]
)


def native_json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def details_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=native_json_default)


def normalize_weights(weights: np.ndarray) -> np.ndarray:
    weights = np.asarray(weights, dtype=float)
    weights = np.where(np.isfinite(weights), weights, 0.0)
    total = float(weights.sum())
    if total <= 0:
        return np.full(len(weights), 1.0 / max(len(weights), 1))
    return weights / total


def inclusive_int(rng: np.random.Generator, low: int, high: int) -> int:
    return int(rng.integers(int(low), int(high) + 1))


def weighted_choice(
    rng: np.random.Generator,
    labels: list[Any] | np.ndarray,
    weights: list[float] | np.ndarray,
) -> Any:
    labels_array = np.asarray(labels, dtype=object)
    probabilities = normalize_weights(np.asarray(weights, dtype=float))
    return labels_array[int(rng.choice(np.arange(len(labels_array)), p=probabilities))]


def allocate_counts(total: int, shares_by_label: dict[str, float]) -> dict[str, int]:
    raw = {label: float(share) * total for label, share in shares_by_label.items()}
    counts = {label: int(math.floor(value)) for label, value in raw.items()}
    remainder = total - sum(counts.values())
    labels_by_fraction = sorted(
        raw,
        key=lambda label: (raw[label] - counts[label], label),
        reverse=True,
    )
    for label in labels_by_fraction[:remainder]:
        counts[label] += 1
    return counts


def build_rng(config: dict[str, Any]) -> np.random.Generator:
    bit_generator = str(config.get("rng_bit_generator", "PCG64"))
    if bit_generator != "PCG64":
        raise ValueError(f"Unsupported rng_bit_generator={bit_generator!r}; expected 'PCG64'.")
    return np.random.Generator(np.random.PCG64(int(config["seed"])))


def validate_config(config: dict[str, Any]) -> None:
    city_count = len(config["locations"]["city_weights"])
    if city_count < 20:
        raise ValueError(f"At least 20 cities are required; got {city_count}.")

    category_tree = config["catalog"]["category_tree"]
    leaf_categories = [category for children in category_tree.values() for category in children]
    if len(leaf_categories) < 50:
        raise ValueError(f"At least 50 leaf listing categories are required; got {len(leaf_categories)}.")
    if len(set(leaf_categories)) != len(leaf_categories):
        raise ValueError("Leaf category names must be unique.")

    missing_price_ranges = set(category_tree) - set(config["catalog"]["price_range_by_parent"])
    if missing_price_ranges:
        raise ValueError(f"Missing price ranges for parent categories: {sorted(missing_price_ranges)}")

    group_shares = {name: float(profile["share"]) for name, profile in config["user_groups"].items()}
    if not math.isclose(sum(group_shares.values()), 1.0, abs_tol=1e-9):
        raise ValueError(f"User group shares must sum to 1.0; got {sum(group_shares.values())}.")
    missing_public_mixes = set(config["user_groups"]) - set(config["public_user_type_mix_by_behavior"])
    if missing_public_mixes:
        raise ValueError(f"Missing public user type mixes for: {sorted(missing_public_mixes)}")
    for behavior_type, weights in config["public_user_type_mix_by_behavior"].items():
        if behavior_type not in config["user_groups"]:
            raise ValueError(f"Unknown behavior type in public user type mix: {behavior_type!r}.")
        if not math.isclose(sum(float(weight) for weight in weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError(f"Public user type weights for {behavior_type!r} must sum to 1.0.")

    csv_split = str(config["output"].get("csv_split", "row_chunk"))
    if csv_split not in {"monthly", "row_chunk"}:
        raise ValueError("output.csv_split must be either 'monthly' or 'row_chunk'.")
    if csv_split == "row_chunk" and int(config["output"].get("rows_per_file", 0)) <= 0:
        raise ValueError("output.rows_per_file must be positive when output.csv_split='row_chunk'.")
    if int(config["listing_model"].get("listing_expiration_days", 0)) <= 0:
        raise ValueError("listing_model.listing_expiration_days must be positive.")

    low_activity = config["low_activity"]["city_category_names"]
    if len(low_activity) < 5:
        raise ValueError("At least 5 cities must have unexpectedly low activity categories.")
    known_cities = set(config["locations"]["city_weights"])
    known_categories = set(leaf_categories)
    for city, categories in low_activity.items():
        if city not in known_cities:
            raise ValueError(f"Unexpectedly low activity city {city!r} is not configured.")
        if len(categories) < 3:
            raise ValueError(f"City {city!r} must have at least 3 low activity categories.")
        missing = set(categories) - known_categories
        if missing:
            raise ValueError(f"Unknown low activity categories for {city!r}: {sorted(missing)}")

    n_users = int(config["scale"]["n_users"])
    n_villages = int(round(n_users * float(config["locations"]["village_user_probability"])))
    if n_villages > len(config["locations"]["villages"]):
        raise ValueError("Not enough village names to keep at most one user per village.")


class OutputManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.output_dir = Path(os.environ.get("MARKETPLACE_ACTIVITY_OUTPUT_DIR", Path.cwd())).resolve()
        self.answer_path_env = os.environ.get("MARKETPLACE_ACTIVITY_ANSWER_PATH", "").strip()
        self.float_rounding = int(config["output"]["float_rounding"])
        self.csv_split = str(config["output"].get("csv_split", "row_chunk"))
        self.rows_per_file = int(config["output"].get("rows_per_file", 25000))
        self.chunk_file_index: dict[str, int] = defaultdict(lambda: 1)
        self.row_buffers: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.write_simulation_output = bool(config["output"].get("write_simulation_output", True))
        self.output_file: Any | None = None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if bool(config["output"].get("cleanup_outputs", True)):
            self.cleanup()

        if self.write_simulation_output:
            self.output_file = open(self.output_dir / "simulation_output.txt", "w", encoding="utf-8")

    def cleanup(self) -> None:
        for path in sorted(self.output_dir.glob("*.csv")):
            path.unlink()
        simulation_output_path = self.output_dir / "simulation_output.txt"
        if simulation_output_path.exists():
            simulation_output_path.unlink()
        if self.answer_path_env:
            answer_path = Path(self.answer_path_env).resolve()
            if answer_path.exists():
                answer_path.unlink()

    def initialize_monthly_files(self, month_indices: list[int]) -> None:
        if self.csv_split != "monthly":
            return
        for table_name, columns in MONTHLY_SCHEMAS.items():
            for month_index in month_indices:
                path = self.output_dir / f"{table_name}_{month_index:03d}.csv"
                pd.DataFrame(columns=columns).to_csv(path, index=False)

    def write_static(self, table_name: str, dataframe: pd.DataFrame) -> None:
        prepared = self.prepare_dataframe(dataframe, STATIC_SCHEMAS[table_name])
        prepared.to_csv(self.output_dir / f"{table_name}_001.csv", index=False)

    def append_monthly(
        self,
        table_name: str,
        month_index: int,
        rows: list[dict[str, Any]] | pd.DataFrame,
    ) -> None:
        if self.csv_split == "row_chunk":
            if isinstance(rows, pd.DataFrame):
                if rows.empty:
                    return
                records = rows.to_dict("records")
            elif rows:
                records = rows
            else:
                return
            self.row_buffers[table_name].extend(records)
            self.flush_table(table_name)
            return

        if isinstance(rows, pd.DataFrame):
            if rows.empty:
                return
            dataframe = rows
        elif rows:
            dataframe = pd.DataFrame.from_records(rows)
        else:
            return

        columns = MONTHLY_SCHEMAS[table_name]
        prepared = self.prepare_dataframe(dataframe, columns)
        if self.csv_split == "monthly":
            path = self.output_dir / f"{table_name}_{month_index:03d}.csv"
            prepared.to_csv(path, mode="a", header=False, index=False)
            return

        offset = 0
        while offset < len(prepared):
            chunk = prepared.iloc[offset : offset + self.rows_per_file]
            self.write_record_chunk(table_name, chunk.to_dict("records"))
            offset += len(chunk)

    def flush_table(self, table_name: str, force: bool = False) -> None:
        buffer = self.row_buffers[table_name]
        while len(buffer) >= self.rows_per_file or (force and buffer):
            chunk_size = min(len(buffer), self.rows_per_file)
            chunk = buffer[:chunk_size]
            del buffer[:chunk_size]
            self.write_record_chunk(table_name, chunk)

    def flush_all(self) -> None:
        for table_name in list(self.row_buffers):
            self.flush_table(table_name, force=True)

    def write_record_chunk(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        columns = MONTHLY_SCHEMAS[table_name]
        path = self.output_dir / f"{table_name}_{self.chunk_file_index[table_name]:03d}.csv"
        self.chunk_file_index[table_name] += 1
        with open(path, "w", newline="", encoding="utf-8") as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(self.prepare_record(row, columns))

    def prepare_record(self, row: dict[str, Any], columns: list[str]) -> dict[str, Any]:
        prepared: dict[str, Any] = {}
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, np.integer):
                value = int(value)
            elif isinstance(value, np.floating):
                value = round(float(value), self.float_rounding)
            elif isinstance(value, float):
                value = round(value, self.float_rounding)
            elif isinstance(value, np.bool_):
                value = bool(value)
            prepared[column] = value
        return prepared

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
        if self.output_file is not None:
            self.output_file.write(line + "\n")

    def write_steps(self, steps: list[dict[str, Any]]) -> None:
        if self.output_file is None:
            return
        for step in steps:
            source_table = step.get("source_table", "")
            source_id = step.get("source_id", "")
            source = f"{source_table}[{source_id}]" if source_table and source_id != "" else source_table
            self.write_output(
                "ACTION "
                f"step_id={step['step_id']} "
                f"timestamp={step['timestamp']} "
                f"action_type={step['action_type']} "
                f"user_id={step.get('user_id', '')} "
                f"city={step.get('city', '')} "
                f"category_id={step.get('category_id', '')} "
                f"listing_id={step.get('listing_id', '')} "
                f"source={source} "
                f"details={step.get('details_json', '{}')}"
            )

    def write_answer(self, low_activity_mapping: dict[str, list[str]]) -> None:
        if not self.answer_path_env:
            return
        answer_path = Path(self.answer_path_env).resolve()
        answer_path.parent.mkdir(parents=True, exist_ok=True)
        with open(answer_path, "w", encoding="utf-8") as file_handle:
            json.dump(low_activity_mapping, file_handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            file_handle.write("\n")

    def close(self) -> None:
        self.flush_all()
        if self.output_file is not None:
            self.output_file.close()


def build_month_index(dates: pd.DatetimeIndex) -> tuple[dict[pd.Timestamp, int], list[int]]:
    periods = pd.Series(dates.to_period("M")).drop_duplicates().tolist()
    period_to_index = {period: index + 1 for index, period in enumerate(periods)}
    date_to_month = {pd.Timestamp(date).normalize(): period_to_index[date.to_period("M")] for date in dates}
    return date_to_month, list(period_to_index.values())


def build_categories(
    config: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int], dict[int, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    meta_rows: list[dict[str, Any]] = []
    category_id_by_name: dict[str, int] = {}
    parent_ids: dict[str, int] = {}
    next_category_id = 1

    for parent_name in config["catalog"]["category_tree"]:
        parent_ids[parent_name] = next_category_id
        category_id_by_name[parent_name] = next_category_id
        rows.append(
            {
                "category_id": next_category_id,
                "category_name": parent_name,
                "parent_category_id": 0,
            }
        )
        next_category_id += 1

    for parent_name, children in config["catalog"]["category_tree"].items():
        price_low, price_high = config["catalog"]["price_range_by_parent"][parent_name]
        parent_search_weight = float(config["catalog"]["parent_search_weight"].get(parent_name, 1.0))
        parent_supply_weight = float(config["catalog"]["parent_supply_weight"].get(parent_name, 1.0))
        for child_name in children:
            category_id = next_category_id
            category_id_by_name[child_name] = category_id
            rows.append(
                {
                    "category_id": category_id,
                    "category_name": child_name,
                    "parent_category_id": parent_ids[parent_name],
                }
            )

            log_low = math.log(float(price_low))
            log_high = math.log(float(price_high))
            base_price = float(math.exp(rng.uniform(log_low, log_high)))
            cheapness_score = float(np.clip(90.0 / max(base_price, 1.0), 0.25, 2.3))
            meta_rows.append(
                {
                    "category_id": category_id,
                    "category_name": child_name,
                    "parent_category_id": parent_ids[parent_name],
                    "parent_category_name": parent_name,
                    "price_low": float(price_low),
                    "price_high": float(price_high),
                    "base_price": base_price,
                    "search_weight": parent_search_weight * float(rng.uniform(0.72, 1.34)),
                    "seller_weight": parent_supply_weight * float(rng.uniform(0.76, 1.28)),
                    "cheapness_score": cheapness_score,
                }
            )
            next_category_id += 1

    category_meta = pd.DataFrame(meta_rows)
    category_meta_by_id = {
        int(row.category_id): {
            "category_id": int(row.category_id),
            "category_name": str(row.category_name),
            "parent_category_id": int(row.parent_category_id),
            "parent_category_name": str(row.parent_category_name),
            "price_low": float(row.price_low),
            "price_high": float(row.price_high),
            "base_price": float(row.base_price),
            "search_weight": float(row.search_weight),
            "seller_weight": float(row.seller_weight),
            "cheapness_score": float(row.cheapness_score),
        }
        for row in category_meta.itertuples(index=False)
    }
    return pd.DataFrame(rows), category_meta, category_id_by_name, category_meta_by_id


def assign_locations(
    config: dict[str, Any],
    rng: np.random.Generator,
    n_users: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    city_names = np.array(list(config["locations"]["city_weights"]), dtype=object)
    city_weights = normalize_weights(np.array(list(config["locations"]["city_weights"].values()), dtype=float))
    city_activity = config["locations"]["city_activity_factor"]

    n_villages = int(round(n_users * float(config["locations"]["village_user_probability"])))
    village_positions = set(rng.choice(np.arange(n_users), size=n_villages, replace=False).tolist())
    selected_villages = list(
        rng.choice(np.array(config["locations"]["villages"], dtype=object), size=n_villages, replace=False)
    )
    village_factor_low, village_factor_high = config["locations"]["village_activity_factor_range"]

    locations: list[str] = []
    location_kinds: list[str] = []
    activity_factors: list[float] = []
    village_offset = 0
    for position in range(n_users):
        if position in village_positions:
            village_name = str(selected_villages[village_offset])
            village_offset += 1
            locations.append(village_name)
            location_kinds.append("village")
            activity_factors.append(float(rng.uniform(float(village_factor_low), float(village_factor_high))))
        else:
            city = str(rng.choice(city_names, p=city_weights))
            locations.append(city)
            location_kinds.append("city")
            activity_factors.append(float(city_activity[city]))

    return np.array(locations, dtype=object), np.array(location_kinds, dtype=object), np.array(activity_factors)


def choose_public_user_type(config: dict[str, Any], rng: np.random.Generator, behavior_type: str) -> str:
    weights_by_type = config["public_user_type_mix_by_behavior"][behavior_type]
    return str(weighted_choice(rng, list(weights_by_type), list(weights_by_type.values())))


def build_users(
    config: dict[str, Any],
    rng: np.random.Generator,
    start_date: pd.Timestamp,
    category_meta: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, list[int]]]:
    n_users = int(config["scale"]["n_users"])
    group_counts = allocate_counts(
        n_users,
        {name: float(profile["share"]) for name, profile in config["user_groups"].items()},
    )

    behavior_types: list[str] = []
    for behavior_type, count in group_counts.items():
        behavior_types.extend([behavior_type] * count)
    behavior_types_array = np.array(behavior_types, dtype=object)
    rng.shuffle(behavior_types_array)

    cities, location_kinds, city_activity_factors = assign_locations(config, rng, n_users)
    user_ids = np.arange(1, n_users + 1)

    registration_offsets = rng.integers(1, 1800, size=n_users)
    registration_dates = [
        (start_date - pd.Timedelta(days=int(offset))).date().isoformat()
        for offset in registration_offsets
    ]

    avg_session_times: list[float] = []
    is_active: list[bool] = []
    daily_probabilities: list[float] = []
    public_user_types: list[str] = []
    for behavior_type in behavior_types_array:
        behavior_type_string = str(behavior_type)
        profile = config["user_groups"][behavior_type_string]
        session_low, session_high = profile["avg_session_time_range"]
        avg_session_times.append(round(float(rng.uniform(float(session_low), float(session_high))), 2))
        is_active.append(bool(rng.random() < float(profile["is_active_probability"])))
        daily_probabilities.append(float(profile["daily_session_probability"]))
        public_user_types.append(choose_public_user_type(config, rng, behavior_type_string))

    public_users = pd.DataFrame(
        {
            "user_id": user_ids,
            "user_type": public_user_types,
            "city": cities,
            "registration_date": registration_dates,
            "avg_session_time": avg_session_times,
            "is_active": is_active,
        }
    )

    category_ids = category_meta["category_id"].to_numpy(int)
    collector_weights = category_meta["search_weight"].to_numpy(float)
    collector_parent_names = category_meta["parent_category_name"].to_numpy(str)
    collector_weights = collector_weights * np.where(
        np.isin(collector_parent_names, np.array(["Leisure", "Electronics", "Fashion"])),
        1.55,
        0.55,
    )
    seller_weights = category_meta["seller_weight"].to_numpy(float)

    focus_category_ids = np.zeros(n_users, dtype=int)
    seller_category_pools: dict[int, list[int]] = {}
    for index, (user_id, behavior_type) in enumerate(zip(user_ids, behavior_types_array, strict=True)):
        behavior_type_string = str(behavior_type)
        profile = config["user_groups"][behavior_type_string]
        if behavior_type_string == "collector_enthusiast":
            focus_category_ids[index] = int(weighted_choice(rng, category_ids, collector_weights))

        pool_low, pool_high = profile["seller_category_pool_size"]
        if int(pool_high) > 0:
            pool_size = inclusive_int(rng, int(pool_low), int(pool_high))
            chosen = rng.choice(
                category_ids,
                size=min(pool_size, len(category_ids)),
                replace=False,
                p=normalize_weights(seller_weights),
            )
            seller_category_pools[int(user_id)] = [int(category_id) for category_id in chosen]
        else:
            seller_category_pools[int(user_id)] = []

    private_users = public_users.copy()
    private_users["behavior_type"] = behavior_types_array
    private_users["location_kind"] = location_kinds
    private_users["city_activity_factor"] = city_activity_factors
    private_users["daily_session_probability"] = daily_probabilities
    private_users["focus_category_id"] = focus_category_ids

    return public_users, private_users, seller_category_pools


def low_activity_category_ids(config: dict[str, Any], category_id_by_name: dict[str, int]) -> dict[str, set[int]]:
    mapping: dict[str, set[int]] = {}
    for city, category_names in config["low_activity"]["city_category_names"].items():
        mapping[city] = {int(category_id_by_name[name]) for name in category_names}
    return mapping


def low_activity_answer(config: dict[str, Any]) -> dict[str, list[str]]:
    return {
        str(city): sorted(str(category) for category in categories)
        for city, categories in sorted(config["low_activity"]["city_category_names"].items())
    }


def is_low_activity(city: str, category_id: int, low_by_city: dict[str, set[int]]) -> bool:
    return int(category_id) in low_by_city.get(str(city), set())


def make_listing_title(rng: np.random.Generator, category_name: str) -> str:
    first_word = str(category_name).split()[0].lower()
    adjective = str(rng.choice(TITLE_ADJECTIVES))
    noun = str(rng.choice(TITLE_NOUNS))
    if rng.random() < 0.55:
        return f"{first_word} {adjective}"
    return f"{noun} {first_word}"


def make_query(rng: np.random.Generator, category_name: str, behavior_type: str) -> str:
    category_terms = str(category_name).lower().split()
    if behavior_type == "collector_enthusiast":
        return " ".join(category_terms[:2])
    if behavior_type == "bargain_hunter" and rng.random() < 0.72:
        return f"{category_terms[0]} cheap"
    if behavior_type == "impulse_buyer" and rng.random() < 0.55:
        return f"{category_terms[0]} deal"
    if rng.random() < 0.40:
        return category_terms[0]
    return f"{category_terms[0]} {str(rng.choice(QUERY_WORDS))}"


def choose_condition(config: dict[str, Any], rng: np.random.Generator) -> str:
    weights_by_condition = config["listing_model"]["condition_weights"]
    return str(weighted_choice(rng, list(weights_by_condition), list(weights_by_condition.values())))


def generate_listing_record(
    config: dict[str, Any],
    rng: np.random.Generator,
    listing_id: int,
    seller_id: int,
    seller_behavior_type: str,
    seller_city: str,
    category_id: int,
    timestamp: pd.Timestamp,
    category_meta_by_id: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    category_meta = category_meta_by_id[int(category_id)]
    profile = config["user_groups"][seller_behavior_type]
    condition = choose_condition(config, rng)
    condition_multiplier = float(config["listing_model"]["condition_price_multiplier"][condition])
    price_strategy = str(profile.get("price_strategy", "default"))
    multiplier_low, multiplier_high, sigma = config["listing_model"]["price_strategy_noise"].get(
        price_strategy,
        config["listing_model"]["price_strategy_noise"]["default"],
    )
    strategy_multiplier = float(rng.uniform(float(multiplier_low), float(multiplier_high)))
    price = (
        float(category_meta["base_price"])
        * condition_multiplier
        * strategy_multiplier
        * float(rng.lognormal(0.0, float(sigma)))
    )
    price = float(np.clip(price, float(category_meta["price_low"]), float(category_meta["price_high"])))

    listing_model = config["listing_model"]
    quality_roll = float(rng.random())
    if quality_roll < float(listing_model["hot_listing_probability"]):
        mean, std = listing_model["hot_listing_lognormal"]
        quality_segment = "hot"
    elif quality_roll < float(listing_model["hot_listing_probability"]) + float(
        listing_model["weak_listing_probability"]
    ):
        mean, std = listing_model["weak_listing_lognormal"]
        quality_segment = "weak"
    else:
        mean, std = listing_model["normal_listing_lognormal"]
        quality_segment = "normal"
    market_fit = float(rng.lognormal(float(mean), float(std)))
    visibility_multiplier = float(profile.get("seller_visibility_multiplier", 1.0))
    visibility_score = market_fit * visibility_multiplier * float(rng.lognormal(0.0, 0.24))
    click_affinity = market_fit * float(rng.uniform(0.70, 1.32))
    expires_at = timestamp.normalize() + pd.Timedelta(days=int(listing_model["listing_expiration_days"]))

    public_row = {
        "listing_id": listing_id,
        "seller_id": seller_id,
        "category_id": category_id,
        "title": make_listing_title(rng, str(category_meta["category_name"])),
        "price": round(price, 2),
        "condition": condition,
        "created_at": timestamp.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    private_row = {
        **public_row,
        "seller_behavior_type": seller_behavior_type,
        "seller_city": seller_city,
        "created_at_ts": timestamp,
        "expires_at_ts": expires_at,
        "parent_category_name": str(category_meta["parent_category_name"]),
        "category_name": str(category_meta["category_name"]),
        "base_price": float(category_meta["base_price"]),
        "market_fit": market_fit,
        "visibility_score": visibility_score,
        "click_affinity": click_affinity,
        "quality_segment": quality_segment,
        "sold": False,
        "sold_at": None,
    }
    return public_row, private_row


def create_listing(
    config: dict[str, Any],
    rng: np.random.Generator,
    counters: dict[str, int],
    listing_private_by_id: dict[int, dict[str, Any]],
    listing_ids_by_category: dict[int, list[int]],
    seller_id: int,
    seller_behavior_type: str,
    seller_city: str,
    category_id: int,
    timestamp: pd.Timestamp,
    category_meta_by_id: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    listing_id = counters["listing_id"]
    counters["listing_id"] += 1
    public_row, private_row = generate_listing_record(
        config,
        rng,
        listing_id,
        seller_id,
        seller_behavior_type,
        seller_city,
        category_id,
        timestamp,
        category_meta_by_id,
    )
    listing_private_by_id[listing_id] = private_row
    listing_ids_by_category[int(category_id)].append(listing_id)
    step = {
        "step_id": counters["step_id"],
        "timestamp": timestamp.isoformat(),
        "action_type": "LISTING_CREATE",
        "user_id": seller_id,
        "city": seller_city,
        "category_id": category_id,
        "listing_id": listing_id,
        "source_table": "listing",
        "source_id": listing_id,
        "details_json": details_json(
            {
                "condition": public_row["condition"],
                "price": public_row["price"],
            }
        ),
    }
    counters["step_id"] += 1
    return public_row, step


def seller_user_ids(private_users: pd.DataFrame, seller_category_pools: dict[int, list[int]]) -> np.ndarray:
    ids = [
        int(user_id)
        for user_id, is_active in zip(
            private_users["user_id"].to_numpy(int),
            private_users["is_active"].to_numpy(bool),
            strict=True,
        )
        if bool(is_active) and len(seller_category_pools.get(int(user_id), [])) > 0
    ]
    return np.array(ids, dtype=int)


def timestamp_in_day(rng: np.random.Generator, date: pd.Timestamp, start_hour: int = 6, end_hour: int = 23) -> pd.Timestamp:
    start_minute = int(start_hour * 60)
    end_minute = int(end_hour * 60)
    minute = int(rng.integers(start_minute, end_minute))
    second = int(rng.integers(0, 60))
    return date.normalize() + pd.Timedelta(minutes=minute, seconds=second)


def seed_initial_listings(
    config: dict[str, Any],
    rng: np.random.Generator,
    counters: dict[str, int],
    date: pd.Timestamp,
    private_users_by_id: dict[int, dict[str, Any]],
    seller_ids: np.ndarray,
    seller_category_pools: dict[int, list[int]],
    category_meta: pd.DataFrame,
    category_meta_by_id: dict[int, dict[str, Any]],
    listing_private_by_id: dict[int, dict[str, Any]],
    listing_ids_by_category: dict[int, list[int]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    listing_rows: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    for seller_id in seller_ids:
        seller = private_users_by_id[int(seller_id)]
        if not bool(seller["is_active"]):
            continue
        seller_behavior_type = str(seller["behavior_type"])
        profile = config["user_groups"][seller_behavior_type]
        initial_low, initial_high = profile["initial_listing_range"]
        if int(initial_high) <= 0:
            continue
        listing_count = inclusive_int(rng, int(initial_low), int(initial_high))
        pool = seller_category_pools[int(seller_id)]
        for _ in range(listing_count):
            category_id = int(rng.choice(np.array(pool, dtype=int)))
            timestamp = timestamp_in_day(rng, date, start_hour=0, end_hour=8)
            public_row, step = create_listing(
                config,
                rng,
                counters,
                listing_private_by_id,
                listing_ids_by_category,
                int(seller_id),
                seller_behavior_type,
                str(seller["city"]),
                category_id,
                timestamp,
                category_meta_by_id,
            )
            listing_rows.append(public_row)
            steps.append(step)

    min_per_category = int(config["scale"]["min_initial_listings_per_leaf_category"])
    category_ids = category_meta["category_id"].to_numpy(int)
    for category_id in category_ids:
        current_count = len(listing_ids_by_category[int(category_id)])
        deficit = max(0, min_per_category - current_count)
        if deficit == 0:
            continue
        eligible_sellers = [
            int(seller_id)
            for seller_id in seller_ids
            if bool(private_users_by_id[int(seller_id)]["is_active"])
            and int(category_id) in seller_category_pools.get(int(seller_id), [])
        ]
        if not eligible_sellers:
            eligible_sellers = [
                int(seller_id)
                for seller_id in seller_ids
                if bool(private_users_by_id[int(seller_id)]["is_active"])
            ]
        if not eligible_sellers:
            raise ValueError("No active seller users are available to seed initial listings.")
        for _ in range(deficit):
            seller_id = int(rng.choice(np.array(eligible_sellers, dtype=int)))
            seller = private_users_by_id[seller_id]
            timestamp = timestamp_in_day(rng, date, start_hour=0, end_hour=8)
            public_row, step = create_listing(
                config,
                rng,
                counters,
                listing_private_by_id,
                listing_ids_by_category,
                seller_id,
                str(seller["behavior_type"]),
                str(seller["city"]),
                int(category_id),
                timestamp,
                category_meta_by_id,
            )
            listing_rows.append(public_row)
            steps.append(step)

    return listing_rows, steps


def create_daily_seller_listings(
    config: dict[str, Any],
    rng: np.random.Generator,
    counters: dict[str, int],
    date: pd.Timestamp,
    private_users_by_id: dict[int, dict[str, Any]],
    seller_ids: np.ndarray,
    seller_category_pools: dict[int, list[int]],
    category_meta_by_id: dict[int, dict[str, Any]],
    listing_private_by_id: dict[int, dict[str, Any]],
    listing_ids_by_category: dict[int, list[int]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    listing_rows: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    weekday_multiplier = float(config["activity"]["seller_listing_weekday_multipliers"][date.weekday()])
    for seller_id in seller_ids:
        seller = private_users_by_id[int(seller_id)]
        if not bool(seller["is_active"]):
            continue
        seller_behavior_type = str(seller["behavior_type"])
        profile = config["user_groups"][seller_behavior_type]
        probability = float(profile["listing_daily_probability"]) * weekday_multiplier
        if rng.random() >= min(probability, 0.95):
            continue
        batch_low, batch_high = profile["listing_batch_range"]
        listing_count = inclusive_int(rng, int(batch_low), int(batch_high))
        pool = seller_category_pools[int(seller_id)]
        for _ in range(listing_count):
            category_id = int(rng.choice(np.array(pool, dtype=int)))
            timestamp = timestamp_in_day(rng, date, start_hour=7, end_hour=22)
            public_row, step = create_listing(
                config,
                rng,
                counters,
                listing_private_by_id,
                listing_ids_by_category,
                int(seller_id),
                seller_behavior_type,
                str(seller["city"]),
                category_id,
                timestamp,
                category_meta_by_id,
            )
            listing_rows.append(public_row)
            steps.append(step)
    return listing_rows, steps


def choose_category_for_user(
    config: dict[str, Any],
    rng: np.random.Generator,
    user: dict[str, Any],
    seller_category_pools: dict[int, list[int]],
    category_meta: pd.DataFrame,
    low_by_city: dict[str, set[int]],
) -> int:
    behavior_type = str(user["behavior_type"])
    user_id = int(user["user_id"])
    profile = config["user_groups"][behavior_type]
    focus_category_id = int(user.get("focus_category_id", 0))
    if focus_category_id > 0:
        return focus_category_id

    seller_pool = seller_category_pools.get(user_id, [])
    if seller_pool and rng.random() < 0.74:
        return int(rng.choice(np.array(seller_pool, dtype=int)))

    category_ids = category_meta["category_id"].to_numpy(int)
    weights = category_meta["search_weight"].to_numpy(float).copy()
    parent_names = category_meta["parent_category_name"].to_numpy(str)
    cheapness_scores = category_meta["cheapness_score"].to_numpy(float)

    for parent_name, factor in profile.get("parent_affinity", {}).items():
        weights *= np.where(parent_names == str(parent_name), float(factor), 1.0)

    cheap_preference = float(profile.get("cheap_preference", 0.0))
    if cheap_preference > 0:
        weights *= np.power(cheapness_scores, min(cheap_preference, 1.8) * 0.35)

    city = str(user["city"])
    if city in low_by_city:
        low_ids = low_by_city[city]
        low_multiplier = float(config["low_activity"]["category_selection_multiplier"])
        weights *= np.array([low_multiplier if int(category_id) in low_ids else 1.0 for category_id in category_ids])

    return int(weighted_choice(rng, category_ids, weights))


class ActiveListingCache:
    def __init__(
        self,
        listing_ids_by_category: dict[int, list[int]],
        listing_private_by_id: dict[int, dict[str, Any]],
    ) -> None:
        self.listing_ids_by_category = listing_ids_by_category
        self.listing_private_by_id = listing_private_by_id
        self.dirty_categories: set[int] = set()
        self.last_expiration_check_by_category: dict[int, pd.Timestamp] = {}
        self.snapshots_by_category: dict[int, dict[str, np.ndarray]] = {}

    def active_snapshot(self, category_id: int, timestamp: pd.Timestamp) -> dict[str, np.ndarray]:
        category_id = int(category_id)
        check_date = pd.Timestamp(timestamp).normalize()
        if (
            category_id in self.dirty_categories
            or self.last_expiration_check_by_category.get(category_id) != check_date
        ):
            active_ids: list[int] = []
            seller_ids: list[int] = []
            seller_cities: list[str] = []
            prices: list[float] = []
            base_prices: list[float] = []
            visibility_scores: list[float] = []
            market_fits: list[float] = []
            click_affinities: list[float] = []
            created_at_ns: list[int] = []

            for listing_id in self.listing_ids_by_category.get(category_id, []):
                listing = self.listing_private_by_id[int(listing_id)]
                if bool(listing["sold"]) or listing["expires_at_ts"] <= timestamp:
                    continue
                active_ids.append(int(listing_id))
                seller_ids.append(int(listing["seller_id"]))
                seller_cities.append(str(listing["seller_city"]))
                prices.append(float(listing["price"]))
                base_prices.append(float(listing["base_price"]))
                visibility_scores.append(float(listing["visibility_score"]))
                market_fits.append(float(listing["market_fit"]))
                click_affinities.append(float(listing["click_affinity"]))
                created_at_ns.append(int(listing["created_at_ts"].value))

            self.listing_ids_by_category[category_id] = active_ids
            self.snapshots_by_category[category_id] = {
                "ids": np.asarray(active_ids, dtype=np.int64),
                "seller_ids": np.asarray(seller_ids, dtype=np.int64),
                "seller_cities": np.asarray(seller_cities, dtype=object),
                "prices": np.asarray(prices, dtype=float),
                "base_prices": np.asarray(base_prices, dtype=float),
                "visibility_scores": np.asarray(visibility_scores, dtype=float),
                "market_fits": np.asarray(market_fits, dtype=float),
                "click_affinities": np.asarray(click_affinities, dtype=float),
                "created_at_ns": np.asarray(created_at_ns, dtype=np.int64),
            }
            self.dirty_categories.discard(category_id)
            self.last_expiration_check_by_category[category_id] = check_date
        return self.snapshots_by_category.get(
            category_id,
            {
                "ids": np.array([], dtype=np.int64),
                "seller_ids": np.array([], dtype=np.int64),
                "seller_cities": np.array([], dtype=object),
                "prices": np.array([], dtype=float),
                "base_prices": np.array([], dtype=float),
                "visibility_scores": np.array([], dtype=float),
                "market_fits": np.array([], dtype=float),
                "click_affinities": np.array([], dtype=float),
                "created_at_ns": np.array([], dtype=np.int64),
            },
        )

    def mark_sold(self, listing_id: int) -> None:
        listing = self.listing_private_by_id[int(listing_id)]
        self.dirty_categories.add(int(listing["category_id"]))


def listings_visible_at(
    snapshot: dict[str, np.ndarray],
    timestamp: pd.Timestamp,
) -> dict[str, np.ndarray]:
    if len(snapshot["ids"]) == 0:
        return snapshot
    visible_mask = snapshot["created_at_ns"] <= int(timestamp.value)
    if bool(np.all(visible_mask)):
        return snapshot
    return {name: values[visible_mask] for name, values in snapshot.items()}


def price_scores_for_user(profile: dict[str, Any], prices: np.ndarray, base_prices: np.ndarray) -> np.ndarray:
    relative_price = np.maximum(prices, 1.0) / np.maximum(base_prices, 1.0)
    cheap_score = np.clip(1.0 / relative_price, 0.25, 3.0)
    cheap_preference = float(profile.get("cheap_preference", 0.0))
    if cheap_preference > 0:
        score = np.power(cheap_score, cheap_preference)
    else:
        score = np.ones_like(cheap_score, dtype=float)
    return np.clip(score, 0.18, 4.0)


def listing_search_weights(
    config: dict[str, Any],
    user: dict[str, Any],
    profile: dict[str, Any],
    snapshot: dict[str, np.ndarray],
    timestamp: pd.Timestamp,
    category_id: int,
    low_by_city: dict[str, set[int]],
) -> np.ndarray:
    ids = snapshot["ids"]
    if len(ids) == 0:
        return np.array([], dtype=float)

    age_days = np.maximum((int(timestamp.value) - snapshot["created_at_ns"]) / (86400.0 * 1_000_000_000.0), 0.0)
    half_life = float(config["listing_model"]["recency_half_life_days"])
    recency = 0.35 + 0.65 * np.exp(-age_days / max(half_life, 1.0))
    price_score = price_scores_for_user(profile, snapshot["prices"], snapshot["base_prices"])
    local_bonus = np.where(
        snapshot["seller_cities"] == str(user["city"]),
        float(profile.get("local_listing_bonus", 1.0)),
        1.0,
    )
    own_listing_multiplier = np.where(
        snapshot["seller_ids"] == int(user["user_id"]),
        float(config["listing_model"]["own_listing_impression_multiplier"]),
        1.0,
    )

    low_seller_cities = [
        city
        for city, category_ids in low_by_city.items()
        if int(category_id) in category_ids
    ]
    if low_seller_cities:
        seller_city_low_multiplier = np.where(
            np.isin(snapshot["seller_cities"], np.asarray(low_seller_cities, dtype=object)),
            float(config["low_activity"]["seller_city_visibility_multiplier"]),
            1.0,
        )
    else:
        seller_city_low_multiplier = 1.0

    weights = (
        snapshot["visibility_scores"]
        * recency
        * np.power(price_score, 0.55)
        * local_bonus
        * own_listing_multiplier
        * seller_city_low_multiplier
    )
    return np.maximum(weights, 1e-9)


def weighted_top_k_indices(
    rng: np.random.Generator,
    weights: np.ndarray,
    k: int,
) -> np.ndarray:
    if len(weights) == 0 or k <= 0:
        return np.array([], dtype=np.int64)
    k = min(int(k), len(weights))
    scores = np.log(np.maximum(weights, 1e-12)) + rng.gumbel(size=len(weights))
    if k == len(weights):
        return np.argsort(scores)[::-1]
    top_positions = np.argpartition(scores, -k)[-k:]
    return top_positions[np.argsort(scores[top_positions])[::-1]]


def sample_impression_listings(
    config: dict[str, Any],
    rng: np.random.Generator,
    user: dict[str, Any],
    profile: dict[str, Any],
    category_id: int,
    timestamp: pd.Timestamp,
    requested_count: int,
    active_snapshot: dict[str, np.ndarray],
    low_by_city: dict[str, set[int]],
    favorites_by_user: dict[int, set[int]],
) -> tuple[list[int], set[int]]:
    candidate_ids = active_snapshot["ids"]
    if len(candidate_ids) == 0:
        return [], set()

    requested_count = min(int(requested_count), len(candidate_ids))
    revisit_ids: list[int] = []
    if str(user["behavior_type"]) == "collector_enthusiast" and rng.random() < float(
        profile.get("favorite_revisit_probability", 0.0)
    ):
        favorited = favorites_by_user.get(int(user["user_id"]), set())
        if favorited:
            favorited_ids = np.fromiter((int(listing_id) for listing_id in favorited), dtype=np.int64)
            revisit_ids = favorited_ids[np.isin(favorited_ids, candidate_ids)].astype(int).tolist()
            if revisit_ids:
                rng.shuffle(revisit_ids)
                revisit_ids = revisit_ids[: min(2, requested_count)]

    remaining_count = requested_count - len(revisit_ids)
    sampled: list[int] = []
    if remaining_count > 0:
        selectable_mask = np.ones(len(candidate_ids), dtype=bool)
        if revisit_ids:
            selectable_mask &= ~np.isin(candidate_ids, np.asarray(revisit_ids, dtype=np.int64))
        selectable_positions = np.flatnonzero(selectable_mask)
        if len(selectable_positions) > 0:
            weights = listing_search_weights(
                config,
                user,
                profile,
                active_snapshot,
                timestamp,
                int(category_id),
                low_by_city,
            )
            selected_relative_positions = weighted_top_k_indices(
                rng,
                weights[selectable_positions],
                remaining_count,
            )
            sampled = candidate_ids[selectable_positions[selected_relative_positions]].astype(int).tolist()
    return revisit_ids + sampled, set(revisit_ids)


def source_type_for_impression(
    rng: np.random.Generator,
    behavior_type: str,
    is_revisit: bool,
) -> str:
    if is_revisit:
        return "favorite_revisit"
    if behavior_type == "collector_enthusiast":
        return str(rng.choice(np.array(["saved_search", "new_listing_alert"], dtype=object), p=[0.68, 0.32]))
    if behavior_type in {"power_seller", "professional_seller"}:
        return str(rng.choice(np.array(["category_feed", "search_results"], dtype=object), p=[0.58, 0.42]))
    return str(
        rng.choice(
            np.array(["search_results", "category_feed", "recommended"], dtype=object),
            p=[0.76, 0.15, 0.09],
        )
    )


def selected_listing_arrays(
    listing_private_by_id: dict[int, dict[str, Any]],
    listing_ids: list[int],
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    listings = [listing_private_by_id[int(listing_id)] for listing_id in listing_ids]
    return listings, {
        "ids": np.asarray(listing_ids, dtype=np.int64),
        "seller_ids": np.asarray([int(listing["seller_id"]) for listing in listings], dtype=np.int64),
        "prices": np.asarray([float(listing["price"]) for listing in listings], dtype=float),
        "base_prices": np.asarray([float(listing["base_price"]) for listing in listings], dtype=float),
        "market_fits": np.asarray([float(listing["market_fit"]) for listing in listings], dtype=float),
        "click_affinities": np.asarray([float(listing["click_affinity"]) for listing in listings], dtype=float),
    }


def click_probabilities_for_impressions(
    config: dict[str, Any],
    user: dict[str, Any],
    profile: dict[str, Any],
    listing_arrays: dict[str, np.ndarray],
    positions: np.ndarray,
    low_activity_pair: bool,
) -> np.ndarray:
    position_decay = float(config["listing_model"]["position_click_decay"])
    position_factor = 1.0 / (1.0 + position_decay * np.maximum(positions.astype(float) - 1.0, 0.0))
    quality_factor = np.clip(listing_arrays["click_affinities"], 0.30, 2.8)
    price_factor = np.power(
        price_scores_for_user(profile, listing_arrays["prices"], listing_arrays["base_prices"]),
        0.35,
    )
    low_factor = float(config["low_activity"]["click_multiplier"]) if low_activity_pair else 1.0
    probabilities = (
        float(profile["click_probability"])
        * position_factor
        * quality_factor
        * price_factor
        * low_factor
    )
    probabilities *= np.where(listing_arrays["seller_ids"] == int(user["user_id"]), 0.05, 1.0)
    return np.clip(probabilities, 0.0, 0.92)


def favorite_probabilities_for_listings(
    config: dict[str, Any],
    profile: dict[str, Any],
    listing_arrays: dict[str, np.ndarray],
    low_activity_pair: bool,
) -> np.ndarray:
    quality_factor = np.clip(listing_arrays["market_fits"], 0.35, 2.6)
    price_factor = np.power(
        price_scores_for_user(profile, listing_arrays["prices"], listing_arrays["base_prices"]),
        0.30,
    )
    low_factor = float(config["low_activity"]["favorite_multiplier"]) if low_activity_pair else 1.0
    probabilities = float(profile["favorite_probability"]) * quality_factor * price_factor * low_factor
    return np.clip(probabilities, 0.0, 0.82)


def purchase_probabilities_for_listings(
    config: dict[str, Any],
    user: dict[str, Any],
    profile: dict[str, Any],
    listing_arrays: dict[str, np.ndarray],
    low_activity_pair: bool,
) -> np.ndarray:
    quality_factor = np.clip(listing_arrays["market_fits"], 0.28, 3.2)
    price_factor = np.power(
        price_scores_for_user(profile, listing_arrays["prices"], listing_arrays["base_prices"]),
        0.75,
    )
    budget_multiplier = np.clip(
        np.power(float(profile["median_budget"]) / np.maximum(listing_arrays["prices"], 1.0), 0.25),
        0.16,
        1.60,
    )
    low_factor = float(config["low_activity"]["purchase_multiplier"]) if low_activity_pair else 1.0
    probabilities = (
        float(profile["purchase_probability"])
        * quality_factor
        * price_factor
        * budget_multiplier
        * low_factor
    )
    if str(user["behavior_type"]) == "impulse_buyer":
        ceiling = float(profile.get("cheap_purchase_ceiling", 75.0))
        probabilities *= np.clip(
            np.power(ceiling / np.maximum(listing_arrays["prices"], 1.0), 0.90),
            0.05,
            1.70,
        )
    probabilities = np.where(listing_arrays["seller_ids"] == int(user["user_id"]), 0.0, probabilities)
    return np.clip(probabilities, 0.0, 0.95)


def shipping_cost(
    config: dict[str, Any],
    rng: np.random.Generator,
    listing: dict[str, Any],
) -> float:
    if str(listing["parent_category_name"]) == "Services":
        return 0.0
    if str(listing["parent_category_name"]) == "Vehicles" and float(listing["price"]) > 900:
        return 0.0
    low, high = config["purchase_model"]["shipping_base_range"]
    cost = float(rng.uniform(float(low), float(high))) + float(listing["price"]) * float(
        config["purchase_model"]["shipping_price_rate"]
    )
    return round(min(cost, float(config["purchase_model"]["shipping_max"])), 2)


def final_purchase_price(
    config: dict[str, Any],
    rng: np.random.Generator,
    behavior_type: str,
    listing_price: float,
) -> float:
    discount_low, discount_high = config["purchase_model"]["negotiation_discount_range_by_user_type"][
        behavior_type
    ]
    discount = float(rng.uniform(float(discount_low), float(discount_high)))
    return round(float(listing_price) * (1.0 - discount), 2)


def simulation_users_for_day(
    config: dict[str, Any],
    rng: np.random.Generator,
    private_users: pd.DataFrame,
    date: pd.Timestamp,
) -> list[int]:
    weekday_multiplier = float(config["activity"]["weekday_session_multipliers"][date.weekday()])
    user_ids = private_users["user_id"].to_numpy(int)
    active = private_users["is_active"].to_numpy(bool)
    daily_probability = private_users["daily_session_probability"].to_numpy(float)
    city_activity = private_users["city_activity_factor"].to_numpy(float)
    probabilities = daily_probability * city_activity * weekday_multiplier
    probabilities = np.where(active, probabilities, 0.0)
    probabilities = np.clip(probabilities, 0.0, 0.85)
    selected = user_ids[rng.random(len(user_ids)) < probabilities]
    selected = rng.permutation(selected)
    return [int(user_id) for user_id in selected]


def simulate_user_sessions(
    config: dict[str, Any],
    rng: np.random.Generator,
    counters: dict[str, int],
    date: pd.Timestamp,
    private_users_by_id: dict[int, dict[str, Any]],
    private_users: pd.DataFrame,
    seller_category_pools: dict[int, list[int]],
    category_meta: pd.DataFrame,
    category_meta_by_id: dict[int, dict[str, Any]],
    low_by_city: dict[str, set[int]],
    listing_private_by_id: dict[int, dict[str, Any]],
    active_listing_cache: ActiveListingCache,
    favorites_by_user: dict[int, set[int]],
    favorited_pairs: set[tuple[int, int]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    search_rows: list[dict[str, Any]] = []
    impression_rows: list[dict[str, Any]] = []
    click_rows: list[dict[str, Any]] = []
    favorite_rows: list[dict[str, Any]] = []
    purchase_rows: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    for user_id in simulation_users_for_day(config, rng, private_users, date):
        user = private_users_by_id[int(user_id)]
        if not bool(user["is_active"]):
            raise AssertionError("Inactive user was selected for a simulation session.")
        behavior_type = str(user["behavior_type"])
        profile = config["user_groups"][behavior_type]
        searches_low, searches_high = profile["searches_per_session"]
        search_count = inclusive_int(rng, int(searches_low), int(searches_high))
        session_start = timestamp_in_day(rng, date, start_hour=7, end_hour=23)
        purchased_in_session = False

        for search_number in range(search_count):
            if purchased_in_session and behavior_type in {"intent_buyer", "impulse_buyer"}:
                break

            category_id = choose_category_for_user(
                config,
                rng,
                user,
                seller_category_pools,
                category_meta,
                low_by_city,
            )
            category_meta_row = category_meta_by_id[int(category_id)]
            category_name = str(category_meta_row["category_name"])
            low_pair = is_low_activity(str(user["city"]), int(category_id), low_by_city)
            timestamp = session_start + pd.Timedelta(minutes=search_number * inclusive_int(rng, 2, 11))
            active_snapshot = listings_visible_at(
                active_listing_cache.active_snapshot(int(category_id), timestamp),
                timestamp,
            )
            active_candidate_count = len(active_snapshot["ids"])

            search_id = counters["search_id"]
            counters["search_id"] += 1
            search_row = {
                "search_id": search_id,
                "user_id": int(user_id),
                "query": make_query(rng, category_name, behavior_type),
                "category_id": int(category_id),
                "timestamp": timestamp.isoformat(),
                "results_count": active_candidate_count,
            }
            search_rows.append(search_row)
            steps.append(
                {
                    "step_id": counters["step_id"],
                    "timestamp": timestamp.isoformat(),
                    "action_type": "SEARCH",
                    "user_id": int(user_id),
                    "city": str(user["city"]),
                    "category_id": int(category_id),
                    "listing_id": "",
                    "source_table": "search_event",
                    "source_id": search_id,
                    "details_json": details_json(
                        {
                            "query": search_row["query"],
                            "results_count": active_candidate_count,
                            "low_activity_pair": low_pair,
                        }
                    ),
                }
            )
            counters["step_id"] += 1

            if active_candidate_count == 0:
                continue

            impression_low, impression_high = profile["impressions_per_search"]
            requested_impressions = inclusive_int(rng, int(impression_low), int(impression_high))
            if low_pair:
                requested_impressions = max(
                    1,
                    int(round(requested_impressions * float(config["low_activity"]["impression_multiplier"]))),
                )
            requested_impressions = min(requested_impressions, active_candidate_count)
            impression_listing_ids, revisit_ids = sample_impression_listings(
                config,
                rng,
                user,
                profile,
                int(category_id),
                timestamp,
                requested_impressions,
                active_snapshot,
                low_by_city,
                favorites_by_user,
            )
            if not impression_listing_ids:
                continue

            selected_listings, listing_arrays = selected_listing_arrays(
                listing_private_by_id,
                impression_listing_ids,
            )
            positions = np.arange(1, len(impression_listing_ids) + 1, dtype=np.int64)
            delay_low, delay_high = config["activity"]["seconds_between_feed_events_range"]
            impression_delays = rng.integers(
                int(delay_low),
                int(delay_high) + 1,
                size=len(impression_listing_ids),
            )
            impression_timestamps = [
                timestamp + pd.Timedelta(seconds=int(position) * int(delay))
                for position, delay in zip(positions, impression_delays, strict=True)
            ]
            source_types = [
                source_type_for_impression(rng, behavior_type, int(listing_id) in revisit_ids)
                for listing_id in impression_listing_ids
            ]
            clicked_mask = rng.random(len(impression_listing_ids)) < click_probabilities_for_impressions(
                config,
                user,
                profile,
                listing_arrays,
                positions,
                low_pair,
            )
            favorite_mask = rng.random(len(impression_listing_ids)) < favorite_probabilities_for_listings(
                config,
                profile,
                listing_arrays,
                low_pair,
            )
            purchase_mask = rng.random(len(impression_listing_ids)) < purchase_probabilities_for_listings(
                config,
                user,
                profile,
                listing_arrays,
                low_pair,
            )

            for impression_index, listing_id in enumerate(impression_listing_ids):
                position = int(positions[impression_index])
                listing = selected_listings[impression_index]
                impression_timestamp = impression_timestamps[impression_index]
                source_type = source_types[impression_index]
                impression_id = counters["impression_id"]
                counters["impression_id"] += 1
                impression_rows.append(
                    {
                        "impression_id": impression_id,
                        "user_id": int(user_id),
                        "listing_id": int(listing_id),
                        "search_id": search_id,
                        "position_in_feed": position,
                        "source_type": source_type,
                        "timestamp": impression_timestamp.isoformat(),
                    }
                )
                steps.append(
                    {
                        "step_id": counters["step_id"],
                        "timestamp": impression_timestamp.isoformat(),
                        "action_type": "IMPRESSION",
                        "user_id": int(user_id),
                        "city": str(user["city"]),
                        "category_id": int(category_id),
                        "listing_id": int(listing_id),
                        "source_table": "impression_event",
                        "source_id": impression_id,
                        "details_json": details_json(
                            {
                                "position_in_feed": position,
                                "source_type": source_type,
                                "seller_city": listing["seller_city"],
                                "listing_price": listing["price"],
                            }
                        ),
                    }
                )
                counters["step_id"] += 1

                if not bool(clicked_mask[impression_index]):
                    continue

                click_timestamp = impression_timestamp + pd.Timedelta(seconds=inclusive_int(rng, 2, 48))
                click_id = counters["click_id"]
                counters["click_id"] += 1
                click_rows.append(
                    {
                        "click_id": click_id,
                        "user_id": int(user_id),
                        "listing_id": int(listing_id),
                        "impression_id": impression_id,
                        "timestamp": click_timestamp.isoformat(),
                    }
                )
                steps.append(
                    {
                        "step_id": counters["step_id"],
                        "timestamp": click_timestamp.isoformat(),
                        "action_type": "CLICK",
                        "user_id": int(user_id),
                        "city": str(user["city"]),
                        "category_id": int(category_id),
                        "listing_id": int(listing_id),
                        "source_table": "click_event",
                        "source_id": click_id,
                        "details_json": details_json(
                            {
                                "impression_id": impression_id,
                                "position_in_feed": position,
                                "low_activity_pair": low_pair,
                            }
                        ),
                    }
                )
                counters["step_id"] += 1

                pair = (int(user_id), int(listing_id))
                if pair not in favorited_pairs and bool(favorite_mask[impression_index]):
                    favorite_timestamp = click_timestamp + pd.Timedelta(seconds=inclusive_int(rng, 3, 90))
                    favorite_id = counters["favorite_id"]
                    counters["favorite_id"] += 1
                    favorited_pairs.add(pair)
                    favorites_by_user[int(user_id)].add(int(listing_id))
                    favorite_rows.append(
                        {
                            "favorite_id": favorite_id,
                            "user_id": int(user_id),
                            "listing_id": int(listing_id),
                            "timestamp": favorite_timestamp.isoformat(),
                        }
                    )
                    steps.append(
                        {
                            "step_id": counters["step_id"],
                            "timestamp": favorite_timestamp.isoformat(),
                            "action_type": "FAVORITE",
                            "user_id": int(user_id),
                            "city": str(user["city"]),
                            "category_id": int(category_id),
                            "listing_id": int(listing_id),
                            "source_table": "favorite_event",
                            "source_id": favorite_id,
                            "details_json": details_json(
                                {
                                    "click_id": click_id,
                                    "seller_city": listing["seller_city"],
                                    "low_activity_pair": low_pair,
                                }
                            ),
                        }
                    )
                    counters["step_id"] += 1

                if bool(listing["sold"]):
                    continue
                if not bool(purchase_mask[impression_index]):
                    continue

                purchase_timestamp = click_timestamp + pd.Timedelta(seconds=inclusive_int(rng, 20, 240))
                purchase_id = counters["purchase_id"]
                counters["purchase_id"] += 1
                final_price = final_purchase_price(config, rng, behavior_type, float(listing["price"]))
                ship_cost = shipping_cost(config, rng, listing)
                listing["sold"] = True
                listing["sold_at"] = purchase_timestamp.isoformat()
                active_listing_cache.mark_sold(int(listing_id))
                purchase_rows.append(
                    {
                        "purchase_id": purchase_id,
                        "buyer_id": int(user_id),
                        "listing_id": int(listing_id),
                        "final_price": final_price,
                        "shipping_cost": ship_cost,
                        "purchase_time": purchase_timestamp.isoformat(),
                    }
                )
                steps.append(
                    {
                        "step_id": counters["step_id"],
                        "timestamp": purchase_timestamp.isoformat(),
                        "action_type": "PURCHASE",
                        "user_id": int(user_id),
                        "city": str(user["city"]),
                        "category_id": int(category_id),
                        "listing_id": int(listing_id),
                        "source_table": "purchase",
                        "source_id": purchase_id,
                        "details_json": details_json(
                            {
                                "click_id": click_id,
                                "seller_id": listing["seller_id"],
                                "seller_city": listing["seller_city"],
                                "final_price": final_price,
                                "shipping_cost": ship_cost,
                                "low_activity_pair": low_pair,
                            }
                        ),
                    }
                )
                counters["step_id"] += 1
                purchased_in_session = True
                if behavior_type in {"intent_buyer", "impulse_buyer"}:
                    break

    return search_rows, impression_rows, click_rows, favorite_rows, purchase_rows, steps


def build_private_users_by_id(private_users: pd.DataFrame) -> dict[int, dict[str, Any]]:
    return {
        int(row.user_id): {
            "user_id": int(row.user_id),
            "user_type": str(row.user_type),
            "behavior_type": str(row.behavior_type),
            "city": str(row.city),
            "registration_date": str(row.registration_date),
            "avg_session_time": float(row.avg_session_time),
            "is_active": bool(row.is_active),
            "location_kind": str(row.location_kind),
            "city_activity_factor": float(row.city_activity_factor),
            "daily_session_probability": float(row.daily_session_probability),
            "focus_category_id": int(row.focus_category_id),
        }
        for row in private_users.itertuples(index=False)
    }


def validate_generated_outputs(
    config: dict[str, Any],
    public_users: pd.DataFrame,
    low_answer: dict[str, list[str]],
    listing_private_by_id: dict[int, dict[str, Any]],
    purchase_count: int,
    activity_user_ids: set[int],
) -> None:
    public_types = set(public_users["user_type"].astype(str))
    allowed_public_types = {
        str(account_type)
        for weights in config["public_user_type_mix_by_behavior"].values()
        for account_type in weights
    }
    hidden_behavior_types = set(config["user_groups"])
    if not public_types <= allowed_public_types:
        raise AssertionError(f"Unexpected public user_type values: {sorted(public_types - allowed_public_types)}")
    if public_types & hidden_behavior_types:
        raise AssertionError("Public user_type values reveal hidden behavioral segments.")

    inactive_user_ids = set(public_users.loc[~public_users["is_active"].astype(bool), "user_id"].astype(int))
    inactive_with_activity = inactive_user_ids & activity_user_ids
    if inactive_with_activity:
        raise AssertionError(f"Inactive users generated activity: {sorted(inactive_with_activity)[:10]}")

    village_names = set(config["locations"]["villages"])
    village_users = public_users[public_users["city"].isin(village_names)]
    village_counts = village_users.groupby("city").size()
    if not village_counts.empty and int(village_counts.max()) > 1:
        raise AssertionError("A village received more than one user.")

    if len(config["locations"]["city_weights"]) < 20:
        raise AssertionError("Generated config has fewer than 20 cities.")

    leaf_count = sum(len(children) for children in config["catalog"]["category_tree"].values())
    if leaf_count < 50:
        raise AssertionError("Generated config has fewer than 50 listing categories.")

    if len(low_answer) < 5 or any(len(categories) < 3 for categories in low_answer.values()):
        raise AssertionError("Unexpectedly low activity answer mapping is too small.")

    sold_listings = sum(1 for listing in listing_private_by_id.values() if bool(listing["sold"]))
    if sold_listings != purchase_count:
        raise AssertionError("Purchase count does not match sold listing count.")


def main() -> None:
    generation_started_at = time.perf_counter()
    validate_config(CONFIG)
    rng = build_rng(CONFIG)
    writer = OutputManager(CONFIG)

    start_date = pd.Timestamp(CONFIG["simulation_start_date"])
    dates = pd.date_range(start=start_date, periods=int(CONFIG["simulation_days"]), freq="D")
    date_to_month, month_indices = build_month_index(dates)
    writer.initialize_monthly_files(month_indices)

    categories, category_meta, category_id_by_name, category_meta_by_id = build_categories(CONFIG, rng)
    public_users, private_users, seller_category_pools = build_users(CONFIG, rng, start_date, category_meta)
    private_users_by_id = build_private_users_by_id(private_users)
    low_by_city = low_activity_category_ids(CONFIG, category_id_by_name)
    low_answer = low_activity_answer(CONFIG)
    sellers = seller_user_ids(private_users, seller_category_pools)

    writer.write_static("user", public_users)
    writer.write_static("category", categories)

    listing_private_by_id: dict[int, dict[str, Any]] = {}
    listing_ids_by_category: dict[int, list[int]] = defaultdict(list)
    active_listing_cache = ActiveListingCache(listing_ids_by_category, listing_private_by_id)
    favorites_by_user: dict[int, set[int]] = defaultdict(set)
    favorited_pairs: set[tuple[int, int]] = set()

    counters = {
        "listing_id": 1,
        "search_id": 1,
        "impression_id": 1,
        "click_id": 1,
        "favorite_id": 1,
        "purchase_id": 1,
        "step_id": 1,
    }

    writer.write_output("== Marketplace Activity Simulation ==")
    writer.write_output(f"Project: {PROJECT_NAME}")
    writer.write_output(f"Seed: {CONFIG['seed']}")
    writer.write_output(f"Simulation start: {dates[0].date().isoformat()}")
    writer.write_output(f"Simulation days: {len(dates)}")
    writer.write_output(
        f"Users: {len(public_users)} | Seller agents: {len(sellers)} | "
        f"Cities: {len(CONFIG['locations']['city_weights'])} | Leaf categories: {len(category_meta)}"
    )
    writer.write_output(
        f"CSV split mode: {CONFIG['output']['csv_split']} | "
        f"rows_per_file={CONFIG['output'].get('rows_per_file', '')}"
    )
    writer.write_output(
        "Unexpectedly low activity city/category pairs are intentionally omitted from public CSVs."
    )

    totals = {
        "listings": 0,
        "searches": 0,
        "impressions": 0,
        "clicks": 0,
        "favorites": 0,
        "purchases": 0,
    }
    activity_user_ids: set[int] = set()

    for day_index, date in enumerate(dates):
        month_index = date_to_month[pd.Timestamp(date).normalize()]
        daily_steps: list[dict[str, Any]] = []

        daily_listing_rows: list[dict[str, Any]]
        if day_index == 0:
            daily_listing_rows, listing_steps = seed_initial_listings(
                CONFIG,
                rng,
                counters,
                date,
                private_users_by_id,
                sellers,
                seller_category_pools,
                category_meta,
                category_meta_by_id,
                listing_private_by_id,
                listing_ids_by_category,
            )
        else:
            daily_listing_rows, listing_steps = create_daily_seller_listings(
                CONFIG,
                rng,
                counters,
                date,
                private_users_by_id,
                sellers,
                seller_category_pools,
                category_meta_by_id,
                listing_private_by_id,
                listing_ids_by_category,
            )
        daily_steps.extend(listing_steps)
        writer.append_monthly("listing", month_index, daily_listing_rows)

        (
            search_rows,
            impression_rows,
            click_rows,
            favorite_rows,
            purchase_rows,
            session_steps,
        ) = simulate_user_sessions(
            CONFIG,
            rng,
            counters,
            date,
            private_users_by_id,
            private_users,
            seller_category_pools,
            category_meta,
            category_meta_by_id,
            low_by_city,
            listing_private_by_id,
            active_listing_cache,
            favorites_by_user,
            favorited_pairs,
        )
        daily_steps.extend(session_steps)

        writer.append_monthly("search_event", month_index, search_rows)
        writer.append_monthly("impression_event", month_index, impression_rows)
        writer.append_monthly("click_event", month_index, click_rows)
        writer.append_monthly("favorite_event", month_index, favorite_rows)
        writer.append_monthly("purchase", month_index, purchase_rows)
        writer.write_steps(daily_steps)

        activity_user_ids.update(int(row["seller_id"]) for row in daily_listing_rows)
        activity_user_ids.update(int(row["user_id"]) for row in search_rows)
        activity_user_ids.update(int(row["user_id"]) for row in impression_rows)
        activity_user_ids.update(int(row["user_id"]) for row in click_rows)
        activity_user_ids.update(int(row["user_id"]) for row in favorite_rows)
        activity_user_ids.update(int(row["buyer_id"]) for row in purchase_rows)

        totals["listings"] += len(daily_listing_rows)
        totals["searches"] += len(search_rows)
        totals["impressions"] += len(impression_rows)
        totals["clicks"] += len(click_rows)
        totals["favorites"] += len(favorite_rows)
        totals["purchases"] += len(purchase_rows)

        active_listings = sum(1 for listing in listing_private_by_id.values() if not bool(listing["sold"]))
        writer.write_output(
            f"{date.date().isoformat()}: new_listings={len(daily_listing_rows)}, "
            f"searches={len(search_rows)}, impressions={len(impression_rows)}, "
            f"clicks={len(click_rows)}, favorites={len(favorite_rows)}, "
            f"purchases={len(purchase_rows)}, active_listings={active_listings}"
        )

    writer.write_answer(low_answer)
    validate_generated_outputs(
        CONFIG,
        public_users,
        low_answer,
        listing_private_by_id,
        totals["purchases"],
        activity_user_ids,
    )

    sold_count = sum(1 for listing in listing_private_by_id.values() if bool(listing["sold"]))
    hot_sold_count = sum(
        1
        for listing in listing_private_by_id.values()
        if bool(listing["sold"]) and str(listing["quality_segment"]) == "hot"
    )
    writer.write_output("")
    writer.write_output("== Final Summary ==")
    writer.write_output(f"Listing rows: {totals['listings']}")
    writer.write_output(f"Search rows: {totals['searches']}")
    writer.write_output(f"Impression rows: {totals['impressions']}")
    writer.write_output(f"Click rows: {totals['clicks']}")
    writer.write_output(f"Favorite rows: {totals['favorites']}")
    writer.write_output(f"Purchase rows: {totals['purchases']}")
    writer.write_output(f"Sold listings: {sold_count}")
    writer.write_output(f"Sold hot-listing hidden segment rows: {hot_sold_count}")
    writer.write_output(f"Unexpectedly low activity cities: {', '.join(sorted(low_answer))}")
    writer.flush_all()
    generation_seconds = time.perf_counter() - generation_started_at
    runtime_message = f"Total generation time: {generation_seconds:.2f} seconds"
    writer.write_output(runtime_message)
    print(runtime_message)
    writer.close()


if __name__ == "__main__":
    main()
