"""
Verifier for the sales_representatives task.

The agent must write /app/answer.json as {"answer": [rep_id, ...]}.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ANSWER_PATH = Path("/app/answer.json")
GT_PATH = Path("/tests/gt.json")

def _normalize_rep_id(value: Any) -> int:
    if isinstance(value, bool):
        raise AssertionError(f"invalid representative ID: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise AssertionError(f"invalid representative ID: {value!r}")


def _normalize(payload: Any) -> dict[str, list[int]]:
    if not isinstance(payload, dict) or set(payload) != {"answer"}:
        raise AssertionError('answer must be a JSON object with exactly one key: "answer"')

    raw_answer = payload["answer"]
    if not isinstance(raw_answer, list):
        raise AssertionError('"answer" must be an array')

    rep_ids = [_normalize_rep_id(value) for value in raw_answer]
    if len(rep_ids) != len(set(rep_ids)):
        raise AssertionError('"answer" must not contain duplicate representative IDs')

    return {"answer": sorted(rep_ids)}


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


def main():
    if not ANSWER_PATH.exists():
        raise AssertionError(f"missing answer file: {ANSWER_PATH}")

    answer = _normalize(json.loads(ANSWER_PATH.read_text(encoding="utf-8")))
    expected = _normalize(json.loads(GT_PATH.read_text(encoding="utf-8")))

    score = compute_micro_jaccard(answer, expected)
    print(score)


if __name__ == "__main__":
    main()
