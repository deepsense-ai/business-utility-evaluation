"""
Verifier for the machinery_malfunctions task.

The agent must write /app/answer.json as a JSON object mapping product IDs to
technician ID arrays. A wrapper {"answer": {...}} is accepted for convenience.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ANSWER_PATH = Path("/app/answer.json")
GT_PATH = Path("/tests/gt.json")

PRODUCT_ID_RE = re.compile(r"^P_(\d+)$")
TECHNICIAN_ID_RE = re.compile(r"^TECH_(\d+)$")

def _id_sort_key(identifier: str) -> int:
    return int(identifier.split("_", 1)[1])


def _normalize(payload: Any) -> dict[str, list[str]]:
    if isinstance(payload, dict) and set(payload) == {"answer"}:
        payload = payload["answer"]

    if not isinstance(payload, dict):
        raise AssertionError("answer must be a JSON object")

    normalized: dict[str, list[str]] = {}
    for product_id, technician_ids in payload.items():
        if not isinstance(product_id, str) or PRODUCT_ID_RE.match(product_id) is None:
            raise AssertionError(f"invalid product ID: {product_id!r}")
        if not isinstance(technician_ids, list):
            raise AssertionError(f"value for {product_id!r} must be an array")

        normalized_technicians: list[str] = []
        for technician_id in technician_ids:
            if (
                not isinstance(technician_id, str)
                or TECHNICIAN_ID_RE.match(technician_id) is None
            ):
                raise AssertionError(
                    f"invalid technician ID for {product_id!r}: {technician_id!r}"
                )
            normalized_technicians.append(technician_id)

        if len(normalized_technicians) != len(set(normalized_technicians)):
            raise AssertionError(f"duplicate technicians provided for {product_id!r}")

        normalized[product_id] = sorted(
            normalized_technicians,
            key=_id_sort_key,
        )

    return dict(sorted(normalized.items(), key=lambda item: _id_sort_key(item[0])))


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
