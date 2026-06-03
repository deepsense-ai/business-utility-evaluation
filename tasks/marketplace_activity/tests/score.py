"""
Verifier for the marketplace_activity task.

The agent must write /app/answer.json as a JSON object mapping city names to
category-name arrays. A wrapper {"answer": {...}} is accepted for convenience.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ANSWER_PATH = Path("/app/answer.json")
GT_PATH = Path("/tests/gt.json")

def _normalize(payload: Any) -> dict[str, list[str]]:
    if isinstance(payload, dict) and set(payload) == {"answer"}:
        payload = payload["answer"]

    if not isinstance(payload, dict):
        raise AssertionError("answer must be a JSON object")

    normalized: dict[str, list[str]] = {}
    for city, categories in payload.items():
        if not isinstance(city, str) or not city:
            raise AssertionError(f"invalid city name: {city!r}")
        if not isinstance(categories, list):
            raise AssertionError(f"value for {city!r} must be an array")

        normalized_categories: list[str] = []
        for category in categories:
            if not isinstance(category, str) or not category:
                raise AssertionError(f"invalid category for {city!r}: {category!r}")
            normalized_categories.append(category)

        if len(normalized_categories) != len(set(normalized_categories)):
            raise AssertionError(f"duplicate categories provided for {city!r}")

        normalized[city] = sorted(normalized_categories)

    return dict(sorted(normalized.items()))


def compute_micro_jaccard(
    predicted: dict[str, list[Any]],
    ground_truth: dict[str, list[Any]],
) -> float:
    tp = 0
    fp = 0
    fn = 0

    for instance_id in sorted(set(predicted) | set(ground_truth)):
        pred_labels = set(predicted.get(instance_id, ()))
        gt_labels = set(ground_truth.get(instance_id, ()))
        tp += len(pred_labels & gt_labels)
        fp += len(pred_labels - gt_labels)
        fn += len(gt_labels - pred_labels)

    denominator = tp + fp + fn
    if denominator == 0:
        return 1.0
    return tp / denominator


def main() -> None:
    if not ANSWER_PATH.exists():
        raise AssertionError(f"missing answer file: {ANSWER_PATH}")

    answer = _normalize(json.loads(ANSWER_PATH.read_text(encoding="utf-8")))
    expected = _normalize(json.loads(GT_PATH.read_text(encoding="utf-8")))

    score = compute_micro_jaccard(answer, expected)
    print(score)


if __name__ == "__main__":
    main()
