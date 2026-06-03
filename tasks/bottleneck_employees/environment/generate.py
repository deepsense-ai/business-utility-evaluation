from __future__ import annotations

import csv
import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_NAME = "bottleneck employees"

CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "seed": 42,
    "rng_bit_generator": "PCG64",
    "simulation_start_date": "2024-01-06",
    "simulation_days": 365,
    "scale": {
        "n_employees": 330,
        "n_projects": 36,
        "base_tasks_per_weekday": 7.2,
        "minimum_tasks_per_day": 2,
    },
    "calendar": {
        "workday_start_hour": 9,
        "workday_end_hour": 17,
        "timezone_label": "UTC",
    },
    "organization": {
        "seniority_mix": {
            "junior": 0.25,
            "mid": 0.39,
            "senior": 0.24,
            "manager": 0.12,
        },
        "department_weights_by_seniority": {
            "junior": {
                "Engineering": 0.50,
                "Platform": 0.14,
                "QA": 0.16,
                "Security": 0.06,
                "SRE": 0.06,
                "Support": 0.08,
                "Product": 0.00,
            },
            "mid": {
                "Engineering": 0.45,
                "Platform": 0.14,
                "QA": 0.13,
                "Security": 0.08,
                "SRE": 0.08,
                "Support": 0.08,
                "Product": 0.04,
            },
            "senior": {
                "Engineering": 0.38,
                "Platform": 0.16,
                "QA": 0.10,
                "Security": 0.10,
                "SRE": 0.10,
                "Support": 0.04,
                "Product": 0.12,
            },
            "manager": {
                "Engineering": 0.30,
                "Platform": 0.12,
                "QA": 0.08,
                "Security": 0.08,
                "SRE": 0.08,
                "Support": 0.10,
                "Product": 0.24,
            },
        },
        "project_count_by_seniority": {
            "junior": [1, 2],
            "mid": [1, 3],
            "senior": [2, 4],
            "manager": [3, 6],
        },
        "hire_offset_days_by_seniority": {
            "junior": [60, 900],
            "mid": [240, 2200],
            "senior": [800, 3600],
            "manager": [900, 4300],
        },
        "skill_distribution_by_seniority": {
            "junior": [0.56, 0.09],
            "mid": [0.70, 0.08],
            "senior": [0.84, 0.07],
            "manager": [0.76, 0.08],
        },
    },
    "projects": {
        "business_domains": [
            "payments",
            "identity",
            "marketplace",
            "analytics",
            "logistics",
            "customer_support",
            "security",
            "billing",
            "mobile",
            "developer_platform",
        ],
        "name_prefixes": [
            "Atlas",
            "Beacon",
            "Cedar",
            "Delta",
            "Evergreen",
            "Forge",
            "Harbor",
            "Ion",
            "Lumen",
            "Nexus",
            "Orion",
            "Pioneer",
        ],
        "name_suffixes": [
            "Checkout",
            "Search",
            "Workflow",
            "Gateway",
            "Insights",
            "Console",
            "Risk",
            "Connect",
            "Ledger",
            "Ops",
        ],
        "priority_level_weights": {
            1: 0.08,
            2: 0.20,
            3: 0.34,
            4: 0.25,
            5: 0.13,
        },
    },
    "bottlenecks": {
        "n_bottleneck_employees": 12,
        "seniority_selection_weights": {
            "junior": 0.04,
            "mid": 0.22,
            "senior": 0.39,
            "manager": 0.35,
        },
        "reason_weights": {
            "overloaded": 0.62,
            "underperforming": 0.19,
            "overloaded_underperforming": 0.19,
        },
        "overload_response_multiplier_range": [4.7, 5.7],
        "underperformance_speed_multiplier_range": [0.15, 0.2],
        "routing_multiplier_range": [5.70, 6.70],
        "meeting_multiplier_range": [5.10, 6.10],
        "message_multiplier_range": [4.80, 5.80],
    },
    "activity": {
        "weekday_task_multipliers": [1.08, 1.04, 1.00, 1.03, 0.88, 0.18, 0.12],
        "weekday_meeting_multipliers": [1.12, 1.08, 1.00, 1.02, 0.78, 0.05, 0.03],
        "weekday_message_multipliers": [1.05, 1.03, 1.00, 1.04, 0.92, 0.25, 0.18],
        "base_meetings_per_weekday": 5.4,
        "base_messages_per_weekday": 42.0,
        "handoff_message_probability": 0.82,
        "meeting_participant_count_range": [3, 9],
        "channels": {
            "chat": 0.58,
            "email": 0.18,
            "ticket_comment": 0.18,
            "pager": 0.06,
        },
    },
    "pipelines": {
        "pipeline_mix": {
            "standard_delivery": 0.34,
            "bug_fix": 0.20,
            "feature_idea": 0.14,
            "large_feature": 0.10,
            "customer_complaint": 0.10,
            "security_vulnerability": 0.08,
            "maintenance": 0.04,
        },
        "weekend_multiplier_by_pipeline": {
            "standard_delivery": 0.22,
            "bug_fix": 0.85,
            "feature_idea": 0.08,
            "large_feature": 0.03,
            "customer_complaint": 1.85,
            "security_vulnerability": 1.70,
            "maintenance": 0.45,
        },
        "priority_weights_by_pipeline": {
            "standard_delivery": {"low": 0.16, "medium": 0.54, "high": 0.26, "critical": 0.04},
            "bug_fix": {"low": 0.06, "medium": 0.42, "high": 0.38, "critical": 0.14},
            "feature_idea": {"low": 0.20, "medium": 0.50, "high": 0.25, "critical": 0.05},
            "large_feature": {"low": 0.06, "medium": 0.46, "high": 0.40, "critical": 0.08},
            "customer_complaint": {"low": 0.02, "medium": 0.30, "high": 0.46, "critical": 0.22},
            "security_vulnerability": {"low": 0.00, "medium": 0.20, "high": 0.42, "critical": 0.38},
            "maintenance": {"low": 0.28, "medium": 0.58, "high": 0.13, "critical": 0.01},
        },
        "complexity_range_by_pipeline": {
            "standard_delivery": [3, 8],
            "bug_fix": [2, 7],
            "feature_idea": [5, 9],
            "large_feature": [7, 10],
            "customer_complaint": [4, 8],
            "security_vulnerability": [5, 10],
            "maintenance": [2, 6],
        },
        "risk_range_by_pipeline": {
            "standard_delivery": [2, 8],
            "bug_fix": [3, 9],
            "feature_idea": [3, 8],
            "large_feature": [5, 10],
            "customer_complaint": [5, 10],
            "security_vulnerability": [7, 10],
            "maintenance": [1, 5],
        },
        "qa_probability_by_pipeline": {
            "standard_delivery": 0.72,
            "bug_fix": 0.54,
            "feature_idea": 0.92,
            "maintenance": 0.34,
        },
        "requested_changes_base_probability": 0.16,
        "qa_failure_base_probability": 0.08,
        "large_feature_subtask_range": [3, 6],
    },
    "action_model": {
        "base_duration_hours": {
            "create": [0.10, 0.35],
            "assign": [0.12, 0.45],
            "triage": [0.20, 0.85],
            "investigate": [0.80, 3.20],
            "design": [3.40, 5.20],
            "decompose": [0.60, 1.80],
            "implement": [3.80, 7.20],
            "review": [0.45, 2.20],
            "qa": [1.70, 3.20],
            "approval": [0.40, 2.10],
            "deploy": [0.40, 2.15],
            "verify": [0.60, 2.20],
        },
        "response_delay_hours": {
            "create": [0.05, 0.50],
            "assign": [0.40, 3.50],
            "triage": [0.20, 2.00],
            "investigate": [0.30, 2.50],
            "design": [0.60, 5.00],
            "decompose": [0.35, 2.30],
            "implement": [0.20, 2.20],
            "review": [1.00, 8.00],
            "qa": [0.80, 5.00],
            "approval": [1.40, 10.00],
            "deploy": [0.20, 2.50],
            "verify": [0.25, 2.00],
        },
        "priority_queue_multiplier": {
            "low": 1.28,
            "medium": 1.00,
            "high": 0.72,
            "critical": 0.46,
        },
        "priority_duration_multiplier": {
            "low": 0.94,
            "medium": 1.00,
            "high": 1.08,
            "critical": 1.16,
        },
        "review_risk_sensitivity": 0.035,
        "qa_risk_sensitivity": 0.030,
        "rollback_probability_base": 0.018,
        "rollback_probability_per_risk": 0.010,
        "availability_routing": {
            "free_window_hours": 10.0,
            "half_life_hours": 12.0,
            "max_penalty_hours": 96.0,
        },
    },
    "actor_selection": {
        "creator": {
            "seniority": {"junior": 0.30, "mid": 1.15, "senior": 1.20, "manager": 1.20},
            "departments": {"Engineering": 1.30, "Product": 1.30, "Support": 0.80},
            "project_member_multiplier": 2.8,
            "non_project_multiplier": 0.35,
        },
        "product_creator": {
            "seniority": {"junior": 0.02, "mid": 0.30, "senior": 1.10, "manager": 2.30},
            "departments": {"Product": 3.20, "Engineering": 0.80},
            "project_member_multiplier": 3.0,
            "non_project_multiplier": 0.30,
        },
        "support_creator": {
            "seniority": {"junior": 0.40, "mid": 1.30, "senior": 1.10, "manager": 0.70},
            "departments": {"Support": 3.10, "Engineering": 0.70, "SRE": 0.70},
            "project_member_multiplier": 1.8,
            "non_project_multiplier": 0.70,
        },
        "security_creator": {
            "seniority": {"junior": 0.08, "mid": 0.80, "senior": 1.80, "manager": 1.10},
            "departments": {"Security": 3.40, "SRE": 1.20, "Platform": 1.10},
            "project_member_multiplier": 2.4,
            "non_project_multiplier": 0.45,
        },
        "assigner": {
            "seniority": {"junior": 0.02, "mid": 0.30, "senior": 1.15, "manager": 2.90},
            "departments": {"Engineering": 1.20, "Product": 1.10, "Platform": 1.00},
            "project_member_multiplier": 3.6,
            "non_project_multiplier": 0.28,
            "use_routing_multiplier": True,
        },
        "implementer": {
            "seniority": {"junior": 1.30, "mid": 1.45, "senior": 0.95, "manager": 0.04},
            "departments": {"Engineering": 2.20, "Platform": 1.55, "Security": 0.85, "SRE": 0.70},
            "project_member_multiplier": 4.2,
            "non_project_multiplier": 0.18,
            "skill_weight": 1.2,
        },
        "hotfix_implementer": {
            "seniority": {"junior": 0.25, "mid": 1.10, "senior": 1.80, "manager": 0.06},
            "departments": {"Engineering": 1.90, "Platform": 1.50, "SRE": 1.25},
            "project_member_multiplier": 3.6,
            "non_project_multiplier": 0.28,
            "skill_weight": 1.4,
        },
        "security_implementer": {
            "seniority": {"junior": 0.14, "mid": 0.85, "senior": 2.00, "manager": 0.05},
            "departments": {"Security": 2.80, "Platform": 1.35, "Engineering": 1.10},
            "project_member_multiplier": 3.2,
            "non_project_multiplier": 0.35,
            "skill_weight": 1.5,
        },
        "reviewer": {
            "seniority": {"junior": 0.03, "mid": 0.65, "senior": 2.20, "manager": 0.55},
            "departments": {"Engineering": 1.45, "Platform": 1.20, "Security": 1.10},
            "project_member_multiplier": 3.4,
            "non_project_multiplier": 0.32,
            "review_capacity_weight": 1.8,
            "use_routing_multiplier": True,
        },
        "security_reviewer": {
            "seniority": {"junior": 0.01, "mid": 0.45, "senior": 2.50, "manager": 0.70},
            "departments": {"Security": 3.40, "Platform": 1.00, "SRE": 0.90},
            "project_member_multiplier": 2.7,
            "non_project_multiplier": 0.45,
            "review_capacity_weight": 1.5,
            "use_routing_multiplier": True,
        },
        "architect": {
            "seniority": {"junior": 0.00, "mid": 0.25, "senior": 2.20, "manager": 1.20},
            "departments": {"Engineering": 1.40, "Platform": 1.55, "Security": 0.80},
            "project_member_multiplier": 3.2,
            "non_project_multiplier": 0.36,
            "skill_weight": 1.1,
            "use_routing_multiplier": True,
        },
        "qa": {
            "seniority": {"junior": 0.55, "mid": 1.35, "senior": 1.10, "manager": 0.05},
            "departments": {"QA": 3.20, "Engineering": 0.70, "Support": 0.55},
            "project_member_multiplier": 2.8,
            "non_project_multiplier": 0.42,
            "skill_weight": 0.8,
        },
        "approver": {
            "seniority": {"junior": 0.00, "mid": 0.22, "senior": 1.75, "manager": 2.60},
            "departments": {"Engineering": 1.25, "Product": 1.20, "Security": 1.20, "SRE": 1.10},
            "project_member_multiplier": 3.8,
            "non_project_multiplier": 0.25,
            "deployment_authority_weight": 1.4,
            "use_routing_multiplier": True,
        },
        "product_approver": {
            "seniority": {"junior": 0.00, "mid": 0.16, "senior": 1.00, "manager": 2.80},
            "departments": {"Product": 3.30, "Engineering": 0.80},
            "project_member_multiplier": 3.4,
            "non_project_multiplier": 0.30,
            "use_routing_multiplier": True,
        },
        "deployer": {
            "seniority": {"junior": 0.02, "mid": 0.55, "senior": 1.85, "manager": 0.80},
            "departments": {"SRE": 2.70, "Platform": 1.80, "Engineering": 0.80},
            "project_member_multiplier": 2.8,
            "non_project_multiplier": 0.40,
            "deployment_authority_weight": 1.8,
            "use_routing_multiplier": True,
        },
        "triager": {
            "seniority": {"junior": 0.12, "mid": 1.25, "senior": 1.45, "manager": 0.50},
            "departments": {"Support": 2.00, "Engineering": 1.15, "QA": 0.90},
            "project_member_multiplier": 2.2,
            "non_project_multiplier": 0.55,
        },
        "meeting_organizer": {
            "seniority": {"junior": 0.03, "mid": 0.45, "senior": 1.25, "manager": 2.60},
            "departments": {"Product": 1.25, "Engineering": 1.20, "Platform": 1.00},
            "project_member_multiplier": 3.0,
            "non_project_multiplier": 0.40,
            "use_routing_multiplier": True,
            "use_meeting_multiplier": True,
        },
        "meeting_participant": {
            "seniority": {"junior": 0.70, "mid": 1.10, "senior": 1.15, "manager": 0.95},
            "departments": {},
            "project_member_multiplier": 4.2,
            "non_project_multiplier": 0.22,
            "use_meeting_multiplier": True,
        },
    },
    "output": {
        "rows_per_file": 5000,
        "answer_path": "../tests/gt.json",
        "write_answer_file": False,
        "write_simulation_output": False,
        "float_rounding": 2,
        "cleanup_outputs": True,
    },
}


TABLE_SCHEMAS: dict[str, list[str]] = {
    "employee": [
        "employee_id",
        "role",
        "seniority_level",
        "department",
        "manager_id",
        "hire_date",
    ],
    "project": ["project_id", "project_name", "business_domain", "priority_level"],
    "task": [
        "task_id",
        "project_id",
        "task_type",
        "priority",
        "status",
        "complexity_score",
        "risk_score",
        "created_at",
        "completed_at",
    ],
    "task_assignment": [
        "assignment_id",
        "task_id",
        "employee_id",
        "assignment_role",
        "assigned_at",
        "unassigned_at",
    ],
    "task_event": ["event_id", "task_id", "employee_id", "event_type", "timestamp"],
    "code_review": [
        "review_id",
        "task_id",
        "reviewer_id",
        "author_id",
        "review_outcome",
        "requested_changes_count",
        "requested_at",
        "completed_at",
    ],
    "qa_test": ["qa_test_id", "task_id", "tester_id", "test_result", "bugs_found", "tested_at"],
    "deployment": [
        "deployment_id",
        "task_id",
        "approved_by",
        "deployment_type",
        "rollback_required",
        "deployed_at",
    ],
    "incident": ["incident_id", "related_task_id", "severity", "owner_id", "created_at", "resolved_at"],
    "approval": [
        "approval_id",
        "task_id",
        "approver_id",
        "approval_type",
        "approval_result",
        "requested_at",
        "resolved_at",
    ],
    "meeting": ["meeting_id", "meeting_type", "organizer_id", "start_time", "end_time"],
    "meeting_participant": ["meeting_id", "employee_id"],
    "message_metadata": ["message_id", "sender_id", "receiver_id", "channel_type", "timestamp"],
    "task_dependency": [
        "dependency_id",
        "blocked_task_id",
        "blocking_task_id",
        "created_at",
        "resolved_at",
    ],
}

TIMESTAMP_COLUMNS = {
    column
    for columns in TABLE_SCHEMAS.values()
    for column in columns
    if column == "timestamp" or column.endswith("_at") or column.endswith("_time")
}

TASK_TABLES = set(TABLE_SCHEMAS)
IMPLEMENTATION_CATEGORIES = {"implement", "investigate", "design", "decompose", "triage", "verify"}
REVIEW_EVENT_TYPES = {"code_review", "re_review", "architecture_review", "security_review"}
MEETING_TYPES = np.array(
    [
        "standup",
        "planning",
        "design_review",
        "incident_bridge",
        "release_readiness",
        "one_on_one",
        "retrospective",
    ],
    dtype=object,
)
MEETING_TYPE_WEIGHTS = np.array([0.26, 0.18, 0.15, 0.10, 0.13, 0.10, 0.08], dtype=float)


@dataclass(slots=True)
class EmployeeProfile:
    employee_id: int
    role: str
    seniority_level: str
    department: str
    manager_id: int
    skill_score: float
    review_capacity: float
    deployment_authority: float
    hire_date: str
    project_ids: tuple[int, ...]
    speed_multiplier: float
    response_multiplier: float
    routing_multiplier: float
    meeting_multiplier: float
    message_multiplier: float
    is_bottleneck: bool
    bottleneck_reason: str
    available_at: pd.Timestamp


def format_timestamp(value: Any) -> str:
    if value in {"", None}:
        return ""
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return ""
    return timestamp.round("s").isoformat()


def native_json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return format_timestamp(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def normalize_weights(weights: np.ndarray) -> np.ndarray:
    weights = np.asarray(weights, dtype=float)
    weights = np.where(np.isfinite(weights), weights, 0.0)
    total = float(weights.sum())
    if total <= 0:
        return np.full(len(weights), 1.0 / max(len(weights), 1))
    return weights / total


def weighted_choice(
    rng: np.random.Generator,
    labels: list[Any] | np.ndarray,
    weights: list[float] | np.ndarray,
) -> Any:
    labels_array = np.asarray(labels, dtype=object)
    probabilities = normalize_weights(np.asarray(weights, dtype=float))
    return labels_array[int(rng.choice(np.arange(len(labels_array)), p=probabilities))]


def inclusive_int(rng: np.random.Generator, low: int, high: int) -> int:
    return int(rng.integers(int(low), int(high) + 1))


def allocate_counts(total: int, shares_by_label: dict[str, float]) -> dict[str, int]:
    raw = {label: float(share) * total for label, share in shares_by_label.items()}
    counts = {label: int(math.floor(value)) for label, value in raw.items()}
    remainder = total - sum(counts.values())
    labels_by_fraction = sorted(raw, key=lambda label: (raw[label] - counts[label], label), reverse=True)
    for label in labels_by_fraction[:remainder]:
        counts[label] += 1
    return counts


def build_rng(config: dict[str, Any]) -> np.random.Generator:
    bit_generator = str(config.get("rng_bit_generator", "PCG64"))
    if bit_generator != "PCG64":
        raise ValueError(f"Unsupported rng_bit_generator={bit_generator!r}; expected 'PCG64'.")
    return np.random.Generator(np.random.PCG64(int(config["seed"])))


def validate_config(config: dict[str, Any]) -> None:
    if int(config["scale"]["n_employees"]) < 40:
        raise ValueError("At least 40 employees are required for cross-functional pipelines.")
    if int(config["scale"]["n_projects"]) < 6:
        raise ValueError("At least 6 projects are required.")
    if int(config["bottlenecks"]["n_bottleneck_employees"]) <= 0:
        raise ValueError("bottlenecks.n_bottleneck_employees must be positive.")
    if int(config["bottlenecks"]["n_bottleneck_employees"]) >= int(config["scale"]["n_employees"]):
        raise ValueError("Bottleneck employees must be a strict subset of employees.")
    if not math.isclose(sum(config["organization"]["seniority_mix"].values()), 1.0, abs_tol=1e-9):
        raise ValueError("organization.seniority_mix must sum to 1.0.")
    if int(config["output"]["rows_per_file"]) <= 0:
        raise ValueError("output.rows_per_file must be positive.")
    start_hour = int(config["calendar"]["workday_start_hour"])
    end_hour = int(config["calendar"]["workday_end_hour"])
    if not 0 <= start_hour < end_hour <= 24:
        raise ValueError("calendar workday hours must satisfy 0 <= start < end <= 24.")


class OutputManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.output_dir = Path(os.environ.get("BOTTLENECK_EMPLOYEES_OUTPUT_DIR", Path.cwd())).resolve()
        self.answer_path_env = os.environ.get("BOTTLENECK_EMPLOYEES_ANSWER_PATH", "").strip()
        self.rows_per_file = int(config["output"]["rows_per_file"])
        self.float_rounding = int(config["output"]["float_rounding"])
        self.write_answer_file = bool(config["output"].get("write_answer_file", True))
        self.answer_path = self.resolve_answer_path(config)
        self.write_simulation_output = bool(config["output"].get("write_simulation_output", False))
        self.output_file: Any | None = None
        self.chunk_file_index: dict[str, int] = defaultdict(lambda: 1)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if bool(config["output"].get("cleanup_outputs", True)):
            self.cleanup()
        if self.write_simulation_output:
            self.output_file = open(self.output_dir / "simulation_output.txt", "w", encoding="utf-8")

    def cleanup(self) -> None:
        for path in sorted(self.output_dir.glob("*.csv")):
            path.unlink()
        for filename in ["answer.txt", "simulation_output.txt"]:
            path = self.output_dir / filename
            if path.exists():
                path.unlink()
        if self.write_answer_file and self.answer_path.exists():
            self.answer_path.unlink()

    def resolve_answer_path(self, config: dict[str, Any]) -> Path:
        if self.answer_path_env:
            return Path(self.answer_path_env).resolve()
        answer_path = Path(str(config["output"].get("answer_path", "../tests/gt.json")))
        if not answer_path.is_absolute():
            answer_path = self.output_dir / answer_path
        return answer_path.resolve()

    def write_table(self, table_name: str, rows: list[dict[str, Any]] | pd.DataFrame) -> None:
        if table_name not in TABLE_SCHEMAS:
            raise KeyError(f"Unknown output table: {table_name!r}")
        if isinstance(rows, pd.DataFrame):
            records = rows.to_dict("records")
        else:
            records = rows
        if not records:
            self.write_record_chunk(table_name, [])
            return
        offset = 0
        while offset < len(records):
            chunk = records[offset : offset + self.rows_per_file]
            self.write_record_chunk(table_name, chunk)
            offset += len(chunk)

    def write_record_chunk(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        columns = TABLE_SCHEMAS[table_name]
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
            if column in TIMESTAMP_COLUMNS:
                value = format_timestamp(value)
            elif isinstance(value, np.integer):
                value = int(value)
            elif isinstance(value, np.floating):
                value = round(float(value), self.float_rounding)
            elif isinstance(value, float):
                value = round(value, self.float_rounding)
            elif isinstance(value, np.bool_):
                value = bool(value)
            elif isinstance(value, pd.Timestamp):
                value = format_timestamp(value)
            prepared[column] = value
        return prepared

    def write_output(self, line: str = "") -> None:
        if self.output_file is not None:
            self.output_file.write(line + "\n")

    def write_answer(self, bottleneck_ids: set[int]) -> None:
        if not self.write_answer_file:
            return
        payload = {"answer": sorted(int(employee_id) for employee_id in bottleneck_ids)}
        self.answer_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.answer_path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, sort_keys=True, separators=(",", ":"), default=native_json_default)
            file_handle.write("\n")

    def close(self) -> None:
        if self.output_file is not None:
            self.output_file.close()


def next_counter(counters: dict[str, int], name: str) -> int:
    counters[name] += 1
    return counters[name]


def workday_bounds(timestamp: pd.Timestamp, config: dict[str, Any]) -> tuple[pd.Timestamp, pd.Timestamp]:
    date = pd.Timestamp(timestamp).normalize()
    start = date + pd.Timedelta(hours=int(config["calendar"]["workday_start_hour"]))
    end = date + pd.Timedelta(hours=int(config["calendar"]["workday_end_hour"]))
    return start, end


def next_work_time(timestamp: pd.Timestamp, config: dict[str, Any]) -> pd.Timestamp:
    current = pd.Timestamp(timestamp)
    while current.weekday() >= 5:
        current = current.normalize() + pd.Timedelta(days=1, hours=int(config["calendar"]["workday_start_hour"]))
    start, end = workday_bounds(current, config)
    if current < start:
        return start
    if current >= end:
        return next_work_time(current.normalize() + pd.Timedelta(days=1), config)
    return current


def add_business_hours(timestamp: pd.Timestamp, hours: float, config: dict[str, Any]) -> pd.Timestamp:
    remaining = max(float(hours), 0.0)
    current = next_work_time(pd.Timestamp(timestamp), config)
    while remaining > 1e-9:
        _, end = workday_bounds(current, config)
        available_hours = max((end - current).total_seconds() / 3600.0, 0.0)
        if remaining <= available_hours:
            return current + pd.Timedelta(hours=remaining)
        remaining -= available_hours
        current = next_work_time(current.normalize() + pd.Timedelta(days=1), config)
    return current


def add_action_hours(
    timestamp: pd.Timestamp,
    hours: float,
    config: dict[str, Any],
    emergency: bool,
) -> pd.Timestamp:
    if emergency:
        return pd.Timestamp(timestamp) + pd.Timedelta(hours=max(float(hours), 0.0))
    return add_business_hours(timestamp, hours, config)


def role_for_employee(seniority: str, department: str) -> str:
    if seniority == "manager":
        return {
            "Engineering": "engineering_manager",
            "Platform": "platform_manager",
            "QA": "qa_manager",
            "Security": "security_manager",
            "SRE": "sre_manager",
            "Support": "support_manager",
            "Product": "product_manager",
        }.get(department, "engineering_manager")
    return {
        "Engineering": "software_engineer",
        "Platform": "platform_engineer",
        "QA": "qa_engineer",
        "Security": "security_engineer",
        "SRE": "site_reliability_engineer",
        "Support": "support_engineer",
        "Product": "product_manager",
    }.get(department, "software_engineer")


def build_projects(config: dict[str, Any], rng: np.random.Generator) -> pd.DataFrame:
    n_projects = int(config["scale"]["n_projects"])
    domains = np.array(config["projects"]["business_domains"], dtype=object)
    prefixes = np.array(config["projects"]["name_prefixes"], dtype=object)
    suffixes = np.array(config["projects"]["name_suffixes"], dtype=object)
    priority_labels = list(config["projects"]["priority_level_weights"])
    priority_weights = list(config["projects"]["priority_level_weights"].values())
    used_names: set[str] = set()
    rows: list[dict[str, Any]] = []
    for project_id in range(1, n_projects + 1):
        for _ in range(50):
            project_name = f"{rng.choice(prefixes)} {rng.choice(suffixes)}"
            if project_name not in used_names:
                used_names.add(project_name)
                break
        else:
            project_name = f"{rng.choice(prefixes)} {rng.choice(suffixes)} {project_id}"
        rows.append(
            {
                "project_id": project_id,
                "project_name": str(project_name),
                "business_domain": str(rng.choice(domains)),
                "priority_level": int(weighted_choice(rng, priority_labels, priority_weights)),
            }
        )
    return pd.DataFrame(rows)


def choose_department(config: dict[str, Any], rng: np.random.Generator, seniority: str) -> str:
    weights_by_department = config["organization"]["department_weights_by_seniority"][seniority]
    return str(weighted_choice(rng, list(weights_by_department), list(weights_by_department.values())))


def choose_project_ids(
    config: dict[str, Any],
    rng: np.random.Generator,
    seniority: str,
    projects: pd.DataFrame,
) -> tuple[int, ...]:
    count_low, count_high = config["organization"]["project_count_by_seniority"][seniority]
    project_count = min(inclusive_int(rng, int(count_low), int(count_high)), len(projects))
    project_ids = projects["project_id"].to_numpy(int)
    priority_weights = projects["priority_level"].to_numpy(float) ** 1.15
    chosen = rng.choice(project_ids, size=project_count, replace=False, p=normalize_weights(priority_weights))
    return tuple(sorted(int(project_id) for project_id in chosen))


def build_employees(
    config: dict[str, Any],
    rng: np.random.Generator,
    start_date: pd.Timestamp,
    projects: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[int, EmployeeProfile], set[int]]:
    n_employees = int(config["scale"]["n_employees"])
    seniority_counts = allocate_counts(n_employees, config["organization"]["seniority_mix"])
    seniority_levels: list[str] = []
    for seniority, count in seniority_counts.items():
        seniority_levels.extend([seniority] * count)
    seniority_array = np.array(seniority_levels, dtype=object)
    rng.shuffle(seniority_array)

    employee_rows: list[dict[str, Any]] = []
    for employee_index, seniority_value in enumerate(seniority_array, start=1):
        seniority = str(seniority_value)
        department = choose_department(config, rng, seniority)
        skill_mean, skill_std = config["organization"]["skill_distribution_by_seniority"][seniority]
        skill_score = float(np.clip(rng.normal(float(skill_mean), float(skill_std)), 0.30, 0.98))
        if seniority == "junior":
            review_capacity = float(np.clip(rng.normal(0.08, 0.04), 0.00, 0.22))
            deployment_authority = float(np.clip(rng.normal(0.04, 0.03), 0.00, 0.16))
        elif seniority == "mid":
            review_capacity = float(np.clip(0.30 + skill_score * 0.38 + rng.normal(0.0, 0.05), 0.10, 0.72))
            deployment_authority = float(np.clip(0.16 + skill_score * 0.25 + rng.normal(0.0, 0.05), 0.04, 0.55))
        elif seniority == "senior":
            review_capacity = float(np.clip(0.48 + skill_score * 0.50 + rng.normal(0.0, 0.04), 0.34, 0.98))
            deployment_authority = float(np.clip(0.38 + skill_score * 0.45 + rng.normal(0.0, 0.05), 0.25, 0.96))
        else:
            review_capacity = float(np.clip(0.36 + skill_score * 0.42 + rng.normal(0.0, 0.05), 0.24, 0.92))
            deployment_authority = float(np.clip(0.54 + skill_score * 0.38 + rng.normal(0.0, 0.04), 0.40, 0.98))

        if department == "QA":
            review_capacity *= 0.78
        if department in {"SRE", "Platform"}:
            deployment_authority = min(0.99, deployment_authority + 0.12)
        if department == "Security":
            review_capacity = min(0.99, review_capacity + 0.10)

        hire_low, hire_high = config["organization"]["hire_offset_days_by_seniority"][seniority]
        hire_date = (start_date - pd.Timedelta(days=inclusive_int(rng, int(hire_low), int(hire_high)))).date()
        employee_rows.append(
            {
                "employee_id": employee_index,
                "role": role_for_employee(seniority, department),
                "seniority_level": seniority,
                "department": department,
                "manager_id": 0,
                "skill_score": round(skill_score, 4),
                "review_capacity": round(review_capacity, 4),
                "deployment_authority": round(deployment_authority, 4),
                "hire_date": hire_date.isoformat(),
            }
        )

    manager_ids = [row["employee_id"] for row in employee_rows if row["seniority_level"] == "manager"]
    manager_ids_by_department: dict[str, list[int]] = defaultdict(list)
    for row in employee_rows:
        if row["seniority_level"] == "manager":
            manager_ids_by_department[str(row["department"])].append(int(row["employee_id"]))

    for row in employee_rows:
        if row["seniority_level"] == "manager":
            continue
        department_managers = manager_ids_by_department.get(str(row["department"]), [])
        candidates = department_managers if department_managers else manager_ids
        row["manager_id"] = int(rng.choice(np.array(candidates, dtype=int))) if candidates else 0

    selection_weights: list[float] = []
    for row in employee_rows:
        seniority = str(row["seniority_level"])
        base_weight = float(config["bottlenecks"]["seniority_selection_weights"].get(seniority, 0.0))
        centrality_bonus = 1.0
        if seniority in {"senior", "manager"}:
            centrality_bonus += 0.20 * float(row["review_capacity"]) + 0.20 * float(row["deployment_authority"])
        selection_weights.append(base_weight * centrality_bonus)
    selected = rng.choice(
        np.array([row["employee_id"] for row in employee_rows], dtype=int),
        size=int(config["bottlenecks"]["n_bottleneck_employees"]),
        replace=False,
        p=normalize_weights(np.array(selection_weights, dtype=float)),
    )
    bottleneck_ids = {int(employee_id) for employee_id in selected}

    profiles: dict[int, EmployeeProfile] = {}
    for row in employee_rows:
        employee_id = int(row["employee_id"])
        seniority = str(row["seniority_level"])
        skill_score = float(row["skill_score"])
        project_ids = choose_project_ids(config, rng, seniority, projects)
        base_speed = float(np.clip(rng.lognormal(mean=0.0, sigma=0.10) * (0.76 + 0.44 * skill_score), 0.56, 1.34))
        response_multiplier = float(np.clip(rng.lognormal(mean=0.0, sigma=0.18), 0.65, 1.55))
        routing_multiplier = 1.0
        meeting_multiplier = 1.0
        message_multiplier = 1.0
        reason = ""

        if employee_id in bottleneck_ids:
            reason = str(
                weighted_choice(
                    rng,
                    list(config["bottlenecks"]["reason_weights"]),
                    list(config["bottlenecks"]["reason_weights"].values()),
                )
            )
            if "overloaded" in reason:
                low, high = config["bottlenecks"]["overload_response_multiplier_range"]
                response_multiplier *= float(rng.uniform(float(low), float(high)))
                low, high = config["bottlenecks"]["routing_multiplier_range"]
                routing_multiplier = float(rng.uniform(float(low), float(high)))
                low, high = config["bottlenecks"]["meeting_multiplier_range"]
                meeting_multiplier = float(rng.uniform(float(low), float(high)))
                low, high = config["bottlenecks"]["message_multiplier_range"]
                message_multiplier = float(rng.uniform(float(low), float(high)))
            if "underperforming" in reason:
                low, high = config["bottlenecks"]["underperformance_speed_multiplier_range"]
                base_speed *= float(rng.uniform(float(low), float(high)))
                response_multiplier *= float(rng.uniform(1.18, 1.90))
            if reason == "overloaded":
                base_speed *= float(rng.uniform(0.82, 0.98))

        available_at = start_date + pd.Timedelta(
            hours=int(config["calendar"]["workday_start_hour"]),
            minutes=float(rng.uniform(0, 90)),
        )
        profiles[employee_id] = EmployeeProfile(
            employee_id=employee_id,
            role=str(row["role"]),
            seniority_level=seniority,
            department=str(row["department"]),
            manager_id=int(row["manager_id"]),
            skill_score=skill_score,
            review_capacity=float(row["review_capacity"]),
            deployment_authority=float(row["deployment_authority"]),
            hire_date=str(row["hire_date"]),
            project_ids=project_ids,
            speed_multiplier=max(base_speed, 0.20),
            response_multiplier=max(response_multiplier, 0.10),
            routing_multiplier=routing_multiplier,
            meeting_multiplier=meeting_multiplier,
            message_multiplier=message_multiplier,
            is_bottleneck=employee_id in bottleneck_ids,
            bottleneck_reason=reason,
            available_at=available_at,
        )

    public_employee_rows = [
        {
            key: value
            for key, value in row.items()
            if key not in {"skill_score", "review_capacity", "deployment_authority"}
        }
        for row in employee_rows
    ]
    return pd.DataFrame(public_employee_rows), profiles, bottleneck_ids


def employee_selection_weight(
    config: dict[str, Any],
    profile: EmployeeProfile,
    selector: str,
    project_id: int,
    ready_time: pd.Timestamp | None = None,
) -> float:
    selector_config = config["actor_selection"].get(selector, config["actor_selection"]["implementer"])
    seniority_weight = float(selector_config.get("seniority", {}).get(profile.seniority_level, 0.05))
    department_weights = selector_config.get("departments", {})
    department_weight = float(department_weights.get(profile.department, 1.0 if not department_weights else 0.45))
    if project_id in profile.project_ids:
        project_weight = float(selector_config.get("project_member_multiplier", 2.0))
    else:
        project_weight = float(selector_config.get("non_project_multiplier", 0.35))

    weight = seniority_weight * department_weight * project_weight
    if selector_config.get("skill_weight"):
        weight *= max(profile.skill_score, 0.05) ** float(selector_config["skill_weight"])
    if selector_config.get("review_capacity_weight"):
        weight *= max(profile.review_capacity, 0.03) ** float(selector_config["review_capacity_weight"])
    if selector_config.get("deployment_authority_weight"):
        weight *= max(profile.deployment_authority, 0.03) ** float(selector_config["deployment_authority_weight"])
    if selector_config.get("use_routing_multiplier", False):
        weight *= profile.routing_multiplier
    if selector_config.get("use_meeting_multiplier", False):
        weight *= profile.meeting_multiplier
    if ready_time is not None:
        availability_config = config["action_model"].get("availability_routing", {})
        backlog_hours = max((profile.available_at - pd.Timestamp(ready_time)).total_seconds() / 3600.0, 0.0)
        free_window_hours = float(availability_config.get("free_window_hours", 0.0))
        if backlog_hours > free_window_hours:
            half_life_hours = max(float(availability_config.get("half_life_hours", 24.0)), 1.0)
            max_penalty_hours = max(float(availability_config.get("max_penalty_hours", 168.0)), half_life_hours)
            penalized_hours = min(backlog_hours - free_window_hours, max_penalty_hours)
            weight *= 0.5 ** (penalized_hours / half_life_hours)
    return max(float(weight), 0.0)


def select_employee(
    config: dict[str, Any],
    rng: np.random.Generator,
    profiles: dict[int, EmployeeProfile],
    selector: str,
    project_id: int,
    exclude_ids: set[int] | None = None,
    ready_time: pd.Timestamp | None = None,
) -> int:
    excluded = exclude_ids or set()
    candidates = [profile for employee_id, profile in sorted(profiles.items()) if employee_id not in excluded]
    if not candidates:
        candidates = [profile for _, profile in sorted(profiles.items())]
    weights = np.array(
        [employee_selection_weight(config, profile, selector, project_id, ready_time) for profile in candidates],
        dtype=float,
    )
    return int(weighted_choice(rng, [profile.employee_id for profile in candidates], weights))


def choose_priority(config: dict[str, Any], rng: np.random.Generator, pipeline_name: str) -> str:
    weights = config["pipelines"]["priority_weights_by_pipeline"][pipeline_name]
    return str(weighted_choice(rng, list(weights), list(weights.values())))


def choose_pipeline(config: dict[str, Any], rng: np.random.Generator, weekday: int) -> str:
    weights_by_pipeline = dict(config["pipelines"]["pipeline_mix"])
    if weekday >= 5:
        for pipeline_name, multiplier in config["pipelines"]["weekend_multiplier_by_pipeline"].items():
            weights_by_pipeline[pipeline_name] = weights_by_pipeline.get(pipeline_name, 0.0) * float(multiplier)
    return str(weighted_choice(rng, list(weights_by_pipeline), list(weights_by_pipeline.values())))


def choose_project(config: dict[str, Any], rng: np.random.Generator, projects: pd.DataFrame) -> int:
    project_ids = projects["project_id"].to_numpy(int)
    weights = projects["priority_level"].to_numpy(float) ** 1.30
    return int(weighted_choice(rng, project_ids, weights))


def random_creation_time(
    config: dict[str, Any],
    rng: np.random.Generator,
    date: pd.Timestamp,
    pipeline_name: str,
    priority: str,
) -> pd.Timestamp:
    emergency_pipeline = pipeline_name in {"customer_complaint", "security_vulnerability", "bug_fix"}
    if emergency_pipeline and (priority == "critical" or rng.random() < 0.18):
        return date.normalize() + pd.Timedelta(hours=float(rng.uniform(0, 23.75)))
    return date.normalize() + pd.Timedelta(hours=float(rng.uniform(9.0, 16.4)))


def sample_action_duration(
    config: dict[str, Any],
    rng: np.random.Generator,
    category: str,
    complexity: int,
    risk: int,
    priority: str,
    profile: EmployeeProfile,
) -> float:
    low, high = config["action_model"]["base_duration_hours"][category]
    base = float(rng.uniform(float(low), float(high)))
    complexity_multiplier = 1.0 + max(int(complexity) - 4, 0) * 0.075
    risk_multiplier = 1.0 + max(int(risk) - 5, 0) * 0.045
    priority_multiplier = float(config["action_model"]["priority_duration_multiplier"][priority])
    return base * complexity_multiplier * risk_multiplier * priority_multiplier / max(profile.speed_multiplier, 0.10)


def schedule_action(
    config: dict[str, Any],
    rng: np.random.Generator,
    profile: EmployeeProfile,
    earliest_time: pd.Timestamp,
    category: str,
    complexity: int,
    risk: int,
    priority: str,
    emergency: bool,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = max(pd.Timestamp(earliest_time), profile.available_at)
    if not emergency:
        start = next_work_time(start, config)
    delay_low, delay_high = config["action_model"]["response_delay_hours"][category]
    delay = float(rng.uniform(float(delay_low), float(delay_high)))
    delay *= profile.response_multiplier
    delay *= float(config["action_model"]["priority_queue_multiplier"][priority])
    start = add_action_hours(start, delay, config, emergency)
    duration = sample_action_duration(config, rng, category, complexity, risk, priority, profile)
    end = add_action_hours(start, duration, config, emergency)
    profile.available_at = max(profile.available_at, end)
    return start, end


def add_task_event(
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    task_id: int,
    employee_id: int,
    event_type: str,
    timestamp: pd.Timestamp,
) -> None:
    records["task_event"].append(
        {
            "event_id": next_counter(counters, "event_id"),
            "task_id": task_id,
            "employee_id": employee_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
        }
    )


def add_assignment(
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    task_id: int,
    employee_id: int,
    assignment_role: str,
    assigned_at: pd.Timestamp,
    unassigned_at: pd.Timestamp,
) -> None:
    records["task_assignment"].append(
        {
            "assignment_id": next_counter(counters, "assignment_id"),
            "task_id": task_id,
            "employee_id": employee_id,
            "assignment_role": assignment_role,
            "assigned_at": assigned_at.isoformat(),
            "unassigned_at": unassigned_at.isoformat(),
        }
    )


def add_message(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    sender_id: int,
    receiver_id: int,
    timestamp: pd.Timestamp,
    channel_type: str | None = None,
) -> None:
    if sender_id == receiver_id:
        return
    channels = config["activity"]["channels"]
    channel = channel_type or str(weighted_choice(rng, list(channels), list(channels.values())))
    records["message_metadata"].append(
        {
            "message_id": next_counter(counters, "message_id"),
            "sender_id": int(sender_id),
            "receiver_id": int(receiver_id),
            "channel_type": channel,
            "timestamp": pd.Timestamp(timestamp).isoformat(),
        }
    )


def review_change_probability(config: dict[str, Any], complexity: int, risk: int) -> float:
    base = float(config["pipelines"]["requested_changes_base_probability"])
    return float(np.clip(base + 0.025 * max(complexity - 5, 0) + 0.020 * max(risk - 5, 0), 0.03, 0.58))


def qa_failure_probability(config: dict[str, Any], complexity: int, risk: int) -> float:
    base = float(config["pipelines"]["qa_failure_base_probability"])
    return float(np.clip(base + 0.018 * max(complexity - 5, 0) + 0.025 * max(risk - 5, 0), 0.02, 0.42))


def standard_steps(
    config: dict[str, Any],
    rng: np.random.Generator,
    pipeline_name: str,
    complexity: int,
    risk: int,
) -> list[dict[str, Any]]:
    if pipeline_name == "standard_delivery":
        steps: list[dict[str, Any]] = [
            {"event_type": "task_created", "selector": "creator", "category": "create"},
            {"event_type": "task_assigned", "selector": "assigner", "category": "assign"},
            {"event_type": "implementation", "selector": "implementer", "category": "implement"},
            {"event_type": "code_review", "selector": "reviewer", "category": "review", "review_type": "code"},
        ]
        if rng.random() < review_change_probability(config, complexity, risk):
            steps.extend(
                [
                    {"event_type": "requested_changes", "selector": "triager", "category": "triage"},
                    {"event_type": "rework_implementation", "selector": "implementer", "category": "implement"},
                    {"event_type": "re_review", "selector": "reviewer", "category": "review", "review_type": "code"},
                ]
            )
        if rng.random() < float(config["pipelines"]["qa_probability_by_pipeline"][pipeline_name]):
            steps.append({"event_type": "qa_testing", "selector": "qa", "category": "qa"})
            if rng.random() < qa_failure_probability(config, complexity, risk):
                steps.extend(
                    [
                        {"event_type": "qa_bug_fix", "selector": "implementer", "category": "implement"},
                        {"event_type": "qa_retest", "selector": "qa", "category": "qa", "retest": True},
                    ]
                )
        steps.extend(
            [
                {
                    "event_type": "deployment_approval",
                    "selector": "approver",
                    "category": "approval",
                    "approval_type": "deployment",
                },
                {
                    "event_type": "deployment",
                    "selector": "deployer",
                    "category": "deploy",
                    "deployment_type": "standard",
                },
            ]
        )
        return steps

    if pipeline_name == "maintenance":
        return [
            {"event_type": "maintenance_task_created", "selector": "creator", "category": "create"},
            {"event_type": "task_assigned", "selector": "assigner", "category": "assign"},
            {"event_type": "implementation", "selector": "implementer", "category": "implement"},
            {"event_type": "code_review", "selector": "reviewer", "category": "review", "review_type": "code"},
            {
                "event_type": "deployment_approval",
                "selector": "approver",
                "category": "approval",
                "approval_type": "maintenance",
            },
            {
                "event_type": "deployment",
                "selector": "deployer",
                "category": "deploy",
                "deployment_type": "scheduled",
            },
        ]

    if pipeline_name == "bug_fix":
        steps = [
            {"event_type": "bug_reported", "selector": "support_creator", "category": "create", "incident": True},
            {"event_type": "triage", "selector": "triager", "category": "triage"},
            {"event_type": "task_assigned", "selector": "assigner", "category": "assign"},
            {"event_type": "fix_implementation", "selector": "implementer", "category": "implement"},
            {"event_type": "code_review", "selector": "reviewer", "category": "review", "review_type": "code"},
        ]
        if rng.random() < review_change_probability(config, complexity, risk):
            steps.extend(
                [
                    {"event_type": "requested_changes", "selector": "triager", "category": "triage"},
                    {"event_type": "fix_rework", "selector": "implementer", "category": "implement"},
                    {"event_type": "re_review", "selector": "reviewer", "category": "review", "review_type": "code"},
                ]
            )
        steps.extend(
            [
                {
                    "event_type": "deployment",
                    "selector": "deployer",
                    "category": "deploy",
                    "deployment_type": "bugfix",
                },
                {"event_type": "incident_verification", "selector": "qa", "category": "verify"},
            ]
        )
        return steps

    if pipeline_name == "customer_complaint":
        return [
            {
                "event_type": "customer_complaint",
                "selector": "support_creator",
                "category": "create",
                "incident": True,
            },
            {"event_type": "support_escalation", "selector": "triager", "category": "triage"},
            {
                "event_type": "engineering_investigation",
                "selector": "hotfix_implementer",
                "category": "investigate",
            },
            {
                "event_type": "hotfix_implementation",
                "selector": "hotfix_implementer",
                "category": "implement",
            },
            {
                "event_type": "senior_approval",
                "selector": "approver",
                "category": "approval",
                "approval_type": "hotfix",
            },
            {
                "event_type": "emergency_deployment",
                "selector": "deployer",
                "category": "deploy",
                "deployment_type": "emergency",
                "emergency": True,
            },
        ]

    if pipeline_name == "security_vulnerability":
        return [
            {
                "event_type": "security_vulnerability_detected",
                "selector": "security_creator",
                "category": "create",
                "incident": True,
            },
            {
                "event_type": "severity_assessment",
                "selector": "security_reviewer",
                "category": "triage",
            },
            {
                "event_type": "patch_implementation",
                "selector": "security_implementer",
                "category": "implement",
            },
            {
                "event_type": "security_review",
                "selector": "security_reviewer",
                "category": "review",
                "review_type": "security",
            },
            {
                "event_type": "deployment_approval",
                "selector": "approver",
                "category": "approval",
                "approval_type": "security_deployment",
            },
            {
                "event_type": "emergency_deployment",
                "selector": "deployer",
                "category": "deploy",
                "deployment_type": "emergency",
                "emergency": True,
            },
        ]

    if pipeline_name == "feature_idea":
        steps = [
            {"event_type": "feature_idea", "selector": "product_creator", "category": "create"},
            {
                "event_type": "product_approval",
                "selector": "product_approver",
                "category": "approval",
                "approval_type": "product",
            },
            {"event_type": "technical_design", "selector": "architect", "category": "design"},
            {
                "event_type": "architecture_review",
                "selector": "architect",
                "category": "review",
                "review_type": "architecture",
            },
            {"event_type": "implementation", "selector": "implementer", "category": "implement"},
            {"event_type": "qa_testing", "selector": "qa", "category": "qa"},
            {
                "event_type": "canary_deployment",
                "selector": "deployer",
                "category": "deploy",
                "deployment_type": "canary",
            },
            {
                "event_type": "full_rollout",
                "selector": "deployer",
                "category": "deploy",
                "deployment_type": "full_rollout",
            },
        ]
        if rng.random() < qa_failure_probability(config, complexity, risk):
            steps.insert(-2, {"event_type": "qa_bug_fix", "selector": "implementer", "category": "implement"})
            steps.insert(-2, {"event_type": "qa_retest", "selector": "qa", "category": "qa", "retest": True})
        return steps

    raise ValueError(f"Unsupported pipeline: {pipeline_name!r}")


def has_future_implementation_step(steps: list[dict[str, Any]], current_index: int) -> bool:
    return any(
        str(step["category"]) in IMPLEMENTATION_CATEGORIES
        for step in steps[current_index + 1 :]
    )


def add_review_row(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    task_id: int,
    reviewer_id: int,
    author_id: int,
    review_type: str,
    event_type: str,
    requested_at: pd.Timestamp,
    completed_at: pd.Timestamp,
    complexity: int,
    risk: int,
) -> str:
    requested_changes = event_type == "code_review" and rng.random() < review_change_probability(config, complexity, risk)
    outcome = "changes_requested" if requested_changes else "approved"
    if event_type in {"re_review", "architecture_review", "security_review"}:
        outcome = "approved"
    if review_type == "security" and int(risk) >= 8 and rng.random() < 0.18:
        outcome = "approved_with_conditions"
    requested_changes_count = inclusive_int(rng, 1, 5) if outcome == "changes_requested" else 0
    records["code_review"].append(
        {
            "review_id": next_counter(counters, "review_id"),
            "task_id": task_id,
            "reviewer_id": reviewer_id,
            "author_id": author_id,
            "review_outcome": outcome,
            "requested_changes_count": requested_changes_count,
            "requested_at": requested_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }
    )
    return outcome


def severity_for_task(rng: np.random.Generator, pipeline_name: str, priority: str, risk: int) -> str:
    if pipeline_name == "security_vulnerability":
        labels = ["medium", "high", "critical"]
        weights = [0.20, 0.42, 0.38 + 0.05 * max(risk - 8, 0)]
    elif priority == "critical":
        labels = ["medium", "high", "critical"]
        weights = [0.15, 0.42, 0.43]
    else:
        labels = ["low", "medium", "high"]
        weights = [0.26, 0.52, 0.22 + 0.04 * max(risk - 7, 0)]
    return str(weighted_choice(rng, labels, weights))


def execute_steps_for_task(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    profiles: dict[int, EmployeeProfile],
    task_id: int,
    project_id: int,
    pipeline_name: str,
    priority: str,
    complexity: int,
    risk: int,
    earliest_time: pd.Timestamp,
    steps: list[dict[str, Any]],
) -> pd.Timestamp:
    current_time = pd.Timestamp(earliest_time)
    previous_actor_id: int | None = None
    last_author_id: int | None = None
    last_reviewer_id: int | None = None
    last_approver_id: int | None = None
    pending_assignment: tuple[str, pd.Timestamp] | None = None
    incident_row: dict[str, Any] | None = None
    used_actor_ids: set[int] = set()

    for step_index, step in enumerate(steps):
        actor_id = select_employee(
            config,
            rng,
            profiles,
            str(step["selector"]),
            project_id,
            used_actor_ids,
            current_time,
        )
        used_actor_ids.add(int(actor_id))
        profile = profiles[int(actor_id)]
        category = str(step["category"])
        emergency = bool(step.get("emergency", False))
        start, end = schedule_action(
            config,
            rng,
            profile,
            current_time,
            category,
            complexity,
            risk,
            priority,
            emergency,
        )
        if (
            previous_actor_id is not None
            and previous_actor_id != actor_id
            and rng.random() < float(config["activity"]["handoff_message_probability"])
        ):
            message_time = max(current_time, start - pd.Timedelta(minutes=float(rng.uniform(5, 75))))
            add_message(config, rng, records, counters, previous_actor_id, int(actor_id), message_time)

        event_type = str(step["event_type"])
        add_task_event(records, counters, task_id, int(actor_id), event_type, end)

        if step.get("incident") and incident_row is None:
            incident_row = {
                "incident_id": next_counter(counters, "incident_id"),
                "related_task_id": task_id,
                "severity": severity_for_task(rng, pipeline_name, priority, risk),
                "owner_id": int(actor_id),
                "created_at": end.isoformat(),
                "resolved_at": "",
            }
            records["incident"].append(incident_row)

        if category == "assign":
            if has_future_implementation_step(steps, step_index):
                pending_assignment = ("owner", end)
        elif category in IMPLEMENTATION_CATEGORIES:
            if pending_assignment:
                role, assigned_at = pending_assignment
                add_assignment(records, counters, task_id, int(actor_id), role, assigned_at, end)
                pending_assignment = None
            else:
                add_assignment(records, counters, task_id, int(actor_id), category, start, end)
            last_author_id = int(actor_id)
        elif category == "review":
            author_id = last_author_id or previous_actor_id or int(actor_id)
            if author_id == int(actor_id):
                author_id = select_employee(
                    config,
                    rng,
                    profiles,
                    "implementer",
                    project_id,
                    {int(actor_id)},
                    current_time,
                )
            review_type = str(step.get("review_type", "code"))
            add_assignment(records, counters, task_id, int(actor_id), f"{review_type}_reviewer", start, end)
            add_review_row(
                config,
                rng,
                records,
                counters,
                task_id,
                int(actor_id),
                int(author_id),
                review_type,
                event_type,
                start,
                end,
                complexity,
                risk,
            )
            last_reviewer_id = int(actor_id)
        elif category == "qa":
            is_retest = bool(step.get("retest", False))
            failed = (not is_retest) and rng.random() < qa_failure_probability(config, complexity, risk)
            bugs_found = inclusive_int(rng, 1, 6) if failed else max(0, int(rng.poisson(0.35 + 0.08 * risk)))
            test_result = "failed" if failed else "passed"
            add_assignment(records, counters, task_id, int(actor_id), "tester", start, end)
            records["qa_test"].append(
                {
                    "qa_test_id": next_counter(counters, "qa_test_id"),
                    "task_id": task_id,
                    "tester_id": int(actor_id),
                    "test_result": test_result,
                    "bugs_found": bugs_found,
                    "tested_at": end.isoformat(),
                }
            )
        elif category == "approval":
            approval_type = str(step.get("approval_type", "deployment"))
            approval_result = "approved"
            if int(risk) >= 8 and rng.random() < 0.10:
                approval_result = "approved_with_conditions"
            add_assignment(records, counters, task_id, int(actor_id), "approver", start, end)
            records["approval"].append(
                {
                    "approval_id": next_counter(counters, "approval_id"),
                    "task_id": task_id,
                    "approver_id": int(actor_id),
                    "approval_type": approval_type,
                    "approval_result": approval_result,
                    "requested_at": start.isoformat(),
                    "resolved_at": end.isoformat(),
                }
            )
            last_approver_id = int(actor_id)
        elif category == "deploy":
            approved_by = last_approver_id or last_reviewer_id or previous_actor_id or int(actor_id)
            rollback_probability = float(config["action_model"]["rollback_probability_base"]) + int(risk) * float(
                config["action_model"]["rollback_probability_per_risk"]
            )
            if str(step.get("deployment_type", "")) == "emergency":
                rollback_probability *= 1.45
            rollback_required = bool(rng.random() < min(0.35, rollback_probability))
            add_assignment(records, counters, task_id, int(actor_id), "deployer", start, end)
            records["deployment"].append(
                {
                    "deployment_id": next_counter(counters, "deployment_id"),
                    "task_id": task_id,
                    "approved_by": int(approved_by),
                    "deployment_type": str(step.get("deployment_type", "standard")),
                    "rollback_required": rollback_required,
                    "deployed_at": end.isoformat(),
                }
            )

        previous_actor_id = int(actor_id)
        current_time = end + pd.Timedelta(minutes=float(rng.uniform(8, 95)))

    if incident_row is not None:
        incident_row["resolved_at"] = current_time.isoformat()
    return current_time


def task_type_for_pipeline(pipeline_name: str) -> str:
    return {
        "standard_delivery": "feature",
        "bug_fix": "bug",
        "feature_idea": "feature",
        "large_feature": "large_feature",
        "customer_complaint": "hotfix",
        "security_vulnerability": "security_patch",
        "maintenance": "maintenance",
    }[pipeline_name]


def status_for_pipeline(pipeline_name: str) -> str:
    return {
        "standard_delivery": "deployed",
        "bug_fix": "verified",
        "feature_idea": "rolled_out",
        "large_feature": "deployed",
        "customer_complaint": "emergency_deployed",
        "security_vulnerability": "emergency_deployed",
        "maintenance": "deployed",
    }[pipeline_name]


def create_task_row(
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    project_id: int,
    pipeline_name: str,
    priority: str,
    complexity: int,
    risk: int,
    created_at: pd.Timestamp,
) -> dict[str, Any]:
    task_row = {
        "task_id": next_counter(counters, "task_id"),
        "project_id": project_id,
        "task_type": task_type_for_pipeline(pipeline_name),
        "priority": priority,
        "status": "in_progress",
        "complexity_score": complexity,
        "risk_score": risk,
        "created_at": pd.Timestamp(created_at).isoformat(),
        "completed_at": "",
    }
    records["task"].append(task_row)
    return task_row


def simulate_regular_pipeline(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    profiles: dict[int, EmployeeProfile],
    projects: pd.DataFrame,
    pipeline_name: str,
    created_at: pd.Timestamp,
) -> None:
    project_id = choose_project(config, rng, projects)
    priority = choose_priority(config, rng, pipeline_name)
    complexity_low, complexity_high = config["pipelines"]["complexity_range_by_pipeline"][pipeline_name]
    risk_low, risk_high = config["pipelines"]["risk_range_by_pipeline"][pipeline_name]
    complexity = inclusive_int(rng, int(complexity_low), int(complexity_high))
    risk = inclusive_int(rng, int(risk_low), int(risk_high))
    task_row = create_task_row(records, counters, project_id, pipeline_name, priority, complexity, risk, created_at)
    steps = standard_steps(config, rng, pipeline_name, complexity, risk)
    completed_at = execute_steps_for_task(
        config,
        rng,
        records,
        counters,
        profiles,
        int(task_row["task_id"]),
        project_id,
        pipeline_name,
        priority,
        complexity,
        risk,
        created_at,
        steps,
    )
    task_row["status"] = status_for_pipeline(pipeline_name)
    task_row["completed_at"] = completed_at.isoformat()


def simulate_large_feature(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    profiles: dict[int, EmployeeProfile],
    projects: pd.DataFrame,
    created_at: pd.Timestamp,
) -> None:
    pipeline_name = "large_feature"
    project_id = choose_project(config, rng, projects)
    priority = choose_priority(config, rng, pipeline_name)
    complexity_low, complexity_high = config["pipelines"]["complexity_range_by_pipeline"][pipeline_name]
    risk_low, risk_high = config["pipelines"]["risk_range_by_pipeline"][pipeline_name]
    complexity = inclusive_int(rng, int(complexity_low), int(complexity_high))
    risk = inclusive_int(rng, int(risk_low), int(risk_high))

    parent_task = create_task_row(records, counters, project_id, pipeline_name, priority, complexity, risk, created_at)
    parent_steps = [
        {"event_type": "feature_idea", "selector": "product_creator", "category": "create"},
        {
            "event_type": "product_approval",
            "selector": "product_approver",
            "category": "approval",
            "approval_type": "product",
        },
        {"event_type": "technical_design", "selector": "architect", "category": "design"},
        {
            "event_type": "architecture_review",
            "selector": "architect",
            "category": "review",
            "review_type": "architecture",
        },
        {"event_type": "subtask_decomposition", "selector": "architect", "category": "decompose"},
    ]
    decomposition_done_at = execute_steps_for_task(
        config,
        rng,
        records,
        counters,
        profiles,
        int(parent_task["task_id"]),
        project_id,
        pipeline_name,
        priority,
        complexity,
        risk,
        created_at,
        parent_steps,
    )

    subtask_low, subtask_high = config["pipelines"]["large_feature_subtask_range"]
    subtask_count = inclusive_int(rng, int(subtask_low), int(subtask_high))
    subtask_completed_at: list[pd.Timestamp] = []
    for subtask_index in range(1, subtask_count + 1):
        sub_complexity = max(2, int(round(complexity * float(rng.uniform(0.45, 0.78)))))
        sub_risk = max(1, int(round(risk * float(rng.uniform(0.45, 0.80)))))
        subtask_created = decomposition_done_at + pd.Timedelta(minutes=float(rng.uniform(15, 180)))
        subtask_row = create_task_row(
            records,
            counters,
            project_id,
            "standard_delivery",
            priority,
            sub_complexity,
            sub_risk,
            subtask_created,
        )
        subtask_row["task_type"] = "large_feature_subtask"
        sub_steps = [
            {"event_type": "task_assigned", "selector": "assigner", "category": "assign"},
            {
                "event_type": f"parallel_implementation_{subtask_index}",
                "selector": "implementer",
                "category": "implement",
            },
            {"event_type": "code_review", "selector": "reviewer", "category": "review", "review_type": "code"},
            {"event_type": "qa_testing", "selector": "qa", "category": "qa"},
        ]
        if rng.random() < review_change_probability(config, sub_complexity, sub_risk):
            sub_steps.insert(3, {"event_type": "rework_implementation", "selector": "implementer", "category": "implement"})
            sub_steps.insert(4, {"event_type": "re_review", "selector": "reviewer", "category": "review", "review_type": "code"})
        done_at = execute_steps_for_task(
            config,
            rng,
            records,
            counters,
            profiles,
            int(subtask_row["task_id"]),
            project_id,
            "standard_delivery",
            priority,
            sub_complexity,
            sub_risk,
            subtask_created,
            sub_steps,
        )
        subtask_row["status"] = "completed"
        subtask_row["completed_at"] = done_at.isoformat()
        subtask_completed_at.append(done_at)
        records["task_dependency"].append(
            {
                "dependency_id": next_counter(counters, "dependency_id"),
                "blocked_task_id": int(parent_task["task_id"]),
                "blocking_task_id": int(subtask_row["task_id"]),
                "created_at": subtask_created.isoformat(),
                "resolved_at": done_at.isoformat(),
            }
        )

    integration_start = max(subtask_completed_at) + pd.Timedelta(hours=float(rng.uniform(1.0, 8.0)))
    completion_steps = [
        {"event_type": "integration_testing", "selector": "qa", "category": "qa"},
        {
            "event_type": "release_approval",
            "selector": "approver",
            "category": "approval",
            "approval_type": "release",
        },
        {
            "event_type": "deployment",
            "selector": "deployer",
            "category": "deploy",
            "deployment_type": "major_release",
        },
    ]
    completed_at = execute_steps_for_task(
        config,
        rng,
        records,
        counters,
        profiles,
        int(parent_task["task_id"]),
        project_id,
        pipeline_name,
        priority,
        complexity,
        risk,
        integration_start,
        completion_steps,
    )
    parent_task["status"] = status_for_pipeline(pipeline_name)
    parent_task["completed_at"] = completed_at.isoformat()


def simulate_meetings_for_day(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    profiles: dict[int, EmployeeProfile],
    projects: pd.DataFrame,
    date: pd.Timestamp,
) -> None:
    weekday = pd.Timestamp(date).weekday()
    multiplier = float(config["activity"]["weekday_meeting_multipliers"][weekday])
    meeting_count = int(rng.poisson(float(config["activity"]["base_meetings_per_weekday"]) * multiplier))
    if weekday < 5:
        meeting_count = max(meeting_count, 1)
    project_ids = projects["project_id"].to_numpy(int)

    for _ in range(meeting_count):
        project_id = int(rng.choice(project_ids))
        meeting_type = str(weighted_choice(rng, MEETING_TYPES, MEETING_TYPE_WEIGHTS))
        start = next_work_time(date.normalize() + pd.Timedelta(hours=float(rng.uniform(9.0, 16.0))), config)
        organizer_id = select_employee(
            config,
            rng,
            profiles,
            "meeting_organizer",
            project_id,
            set(),
            start,
        )
        participant_low, participant_high = config["activity"]["meeting_participant_count_range"]
        participant_count = inclusive_int(rng, int(participant_low), int(participant_high))
        participants = {organizer_id}
        while len(participants) < participant_count:
            participants.add(
                select_employee(
                    config,
                    rng,
                    profiles,
                    "meeting_participant",
                    project_id,
                    participants,
                    start,
                )
            )

        if meeting_type == "standup":
            duration_hours = float(rng.uniform(0.20, 0.45))
        elif meeting_type == "incident_bridge":
            duration_hours = float(rng.uniform(0.75, 2.25))
        else:
            duration_hours = float(rng.uniform(0.45, 1.35))
        end = add_business_hours(start, duration_hours, config)

        records["meeting"].append(
            {
                "meeting_id": next_counter(counters, "meeting_id"),
                "meeting_type": meeting_type,
                "organizer_id": organizer_id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            }
        )
        meeting_id = int(records["meeting"][-1]["meeting_id"])
        for employee_id in sorted(participants):
            records["meeting_participant"].append({"meeting_id": meeting_id, "employee_id": int(employee_id)})
            if profiles[int(employee_id)].available_at <= start:
                profiles[int(employee_id)].available_at = end


def message_selection_weights(profiles: dict[int, EmployeeProfile], receive: bool = False) -> tuple[list[int], np.ndarray]:
    ids: list[int] = []
    weights: list[float] = []
    for employee_id, profile in sorted(profiles.items()):
        ids.append(int(employee_id))
        seniority_factor = {"junior": 0.70, "mid": 1.00, "senior": 1.22, "manager": 1.55}[profile.seniority_level]
        if receive:
            seniority_factor = {"junior": 0.85, "mid": 1.05, "senior": 1.28, "manager": 1.42}[profile.seniority_level]
        weights.append(seniority_factor * profile.message_multiplier)
    return ids, np.asarray(weights, dtype=float)


def simulate_background_messages_for_day(
    config: dict[str, Any],
    rng: np.random.Generator,
    records: dict[str, list[dict[str, Any]]],
    counters: dict[str, int],
    profiles: dict[int, EmployeeProfile],
    date: pd.Timestamp,
) -> None:
    weekday = pd.Timestamp(date).weekday()
    multiplier = float(config["activity"]["weekday_message_multipliers"][weekday])
    message_count = int(rng.poisson(float(config["activity"]["base_messages_per_weekday"]) * multiplier))
    sender_ids, sender_weights = message_selection_weights(profiles, receive=False)
    receiver_ids, receiver_weights = message_selection_weights(profiles, receive=True)
    channels = config["activity"]["channels"]

    for _ in range(message_count):
        sender_id = int(weighted_choice(rng, sender_ids, sender_weights))
        receiver_candidates = [employee_id for employee_id in receiver_ids if employee_id != sender_id]
        receiver_candidate_weights = np.array(
            [receiver_weights[receiver_ids.index(employee_id)] for employee_id in receiver_candidates],
            dtype=float,
        )
        receiver_id = int(weighted_choice(rng, receiver_candidates, receiver_candidate_weights))
        if weekday >= 5 and rng.random() < 0.40:
            hour = float(rng.uniform(8.0, 22.0))
        else:
            hour = float(rng.uniform(8.0, 18.8))
        timestamp = date.normalize() + pd.Timedelta(hours=hour)
        channel = str(weighted_choice(rng, list(channels), list(channels.values())))
        add_message(config, rng, records, counters, sender_id, receiver_id, timestamp, channel)


def validate_generated_outputs(
    config: dict[str, Any],
    records: dict[str, list[dict[str, Any]]],
    employees: pd.DataFrame,
    projects: pd.DataFrame,
    bottleneck_ids: set[int],
) -> None:
    employee_ids = set(int(value) for value in employees["employee_id"].tolist())
    project_ids = set(int(value) for value in projects["project_id"].tolist())
    task_ids = set(int(row["task_id"]) for row in records["task"])
    if not bottleneck_ids or not bottleneck_ids <= employee_ids:
        raise AssertionError("Bottleneck answer contains unknown employee IDs.")
    if len(records["task"]) < int(config["simulation_days"]) * int(config["scale"]["minimum_tasks_per_day"]):
        raise AssertionError("Generated too few tasks.")
    if not all(int(row["project_id"]) in project_ids for row in records["task"]):
        raise AssertionError("Task references an unknown project.")
    for table_name in TASK_TABLES - {"employee", "project"}:
        if table_name not in records:
            raise AssertionError(f"Missing output table rows for {table_name!r}.")
    for row in records["task_event"]:
        if int(row["task_id"]) not in task_ids:
            raise AssertionError("Task event references an unknown task.")
        if int(row["employee_id"]) not in employee_ids:
            raise AssertionError("Task event references an unknown employee.")
    for row in records["task_dependency"]:
        if int(row["blocked_task_id"]) not in task_ids or int(row["blocking_task_id"]) not in task_ids:
            raise AssertionError("Task dependency references an unknown task.")
    for row in records["code_review"]:
        if int(row["reviewer_id"]) == int(row["author_id"]):
            raise AssertionError("A code review has the same author and reviewer.")
    if len(records["deployment"]) < 100:
        raise AssertionError("Generated too few deployment records.")
    if len(records["meeting"]) < 100 or len(records["message_metadata"]) < 1000:
        raise AssertionError("Generated too little collaboration activity.")


def hours_between(start_value: Any, end_value: Any) -> float:
    if start_value in {"", None} or end_value in {"", None}:
        return 0.0
    start = pd.Timestamp(start_value)
    end = pd.Timestamp(end_value)
    if pd.isna(start) or pd.isna(end) or end < start:
        return 0.0
    return float((end - start).total_seconds() / 3600.0)


def sorted_id_sample(values: set[int], limit: int = 24) -> str:
    sorted_values = sorted(values)
    if not sorted_values:
        return "[]"
    sample = sorted_values[:limit]
    suffix = "" if len(sorted_values) <= limit else f", ... +{len(sorted_values) - limit} more"
    return "[" + ", ".join(str(value) for value in sample) + suffix + "]"


def count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row[key])] += 1
    return dict(sorted(counts.items()))


def format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "{}"
    return "{" + ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())) + "}"


def write_bottleneck_employee_report(
    writer: OutputManager,
    records: dict[str, list[dict[str, Any]]],
    profiles: dict[int, EmployeeProfile],
    bottleneck_ids: set[int],
) -> None:
    if writer.output_file is None:
        return

    task_by_id = {int(row["task_id"]): row for row in records["task"]}
    writer.write_output("")
    writer.write_output("== Bottleneck Employee Details ==")
    for employee_id in sorted(bottleneck_ids):
        profile = profiles[int(employee_id)]
        assignment_rows = [
            row for row in records["task_assignment"] if int(row["employee_id"]) == int(employee_id)
        ]
        event_rows = [row for row in records["task_event"] if int(row["employee_id"]) == int(employee_id)]
        review_rows = [row for row in records["code_review"] if int(row["reviewer_id"]) == int(employee_id)]
        authored_review_rows = [
            row for row in records["code_review"] if int(row["author_id"]) == int(employee_id)
        ]
        qa_rows = [row for row in records["qa_test"] if int(row["tester_id"]) == int(employee_id)]
        approval_rows = [row for row in records["approval"] if int(row["approver_id"]) == int(employee_id)]
        deployment_approval_rows = [
            row for row in records["deployment"] if int(row["approved_by"]) == int(employee_id)
        ]
        incident_rows = [row for row in records["incident"] if int(row["owner_id"]) == int(employee_id)]
        organized_meetings = [
            row for row in records["meeting"] if int(row["organizer_id"]) == int(employee_id)
        ]
        attended_meeting_ids = {
            int(row["meeting_id"])
            for row in records["meeting_participant"]
            if int(row["employee_id"]) == int(employee_id)
        }
        sent_messages = [
            row for row in records["message_metadata"] if int(row["sender_id"]) == int(employee_id)
        ]
        received_messages = [
            row for row in records["message_metadata"] if int(row["receiver_id"]) == int(employee_id)
        ]

        assigned_task_ids = {int(row["task_id"]) for row in assignment_rows}
        touched_task_ids = assigned_task_ids | {int(row["task_id"]) for row in event_rows}
        touched_task_ids |= {int(row["task_id"]) for row in review_rows}
        touched_task_ids |= {int(row["task_id"]) for row in authored_review_rows}
        touched_task_ids |= {int(row["task_id"]) for row in qa_rows}
        touched_task_ids |= {int(row["task_id"]) for row in approval_rows}
        touched_task_ids |= {int(row["related_task_id"]) for row in incident_rows}

        assignment_hours = [hours_between(row["assigned_at"], row["unassigned_at"]) for row in assignment_rows]
        avg_assignment_hours = sum(assignment_hours) / max(len(assignment_hours), 1)
        touched_task_durations = [
            hours_between(task_by_id[task_id]["created_at"], task_by_id[task_id]["completed_at"])
            for task_id in touched_task_ids
            if task_id in task_by_id
        ]
        avg_touched_task_hours = sum(touched_task_durations) / max(len(touched_task_durations), 1)

        writer.write_output(
            "BOTTLENECK "
            f"employee_id={employee_id} "
            f"role={profile.role} "
            f"seniority={profile.seniority_level} "
            f"department={profile.department} "
            f"manager_id={profile.manager_id} "
            f"reason={profile.bottleneck_reason}"
        )
        writer.write_output(
            "  hidden_profile "
            f"skill_score={profile.skill_score:.2f} "
            f"review_capacity={profile.review_capacity:.2f} "
            f"deployment_authority={profile.deployment_authority:.2f} "
            f"speed_multiplier={profile.speed_multiplier:.2f} "
            f"response_multiplier={profile.response_multiplier:.2f} "
            f"routing_multiplier={profile.routing_multiplier:.2f} "
            f"meeting_multiplier={profile.meeting_multiplier:.2f} "
            f"message_multiplier={profile.message_multiplier:.2f} "
            f"project_ids={sorted_id_sample(set(profile.project_ids), limit=12)}"
        )
        writer.write_output(
            "  work_stats "
            f"assigned_tasks={len(assigned_task_ids)} "
            f"touched_tasks={len(touched_task_ids)} "
            f"task_events={len(event_rows)} "
            f"assignment_rows={len(assignment_rows)} "
            f"avg_assignment_hours={avg_assignment_hours:.2f} "
            f"avg_touched_task_hours={avg_touched_task_hours:.2f} "
            f"assignment_roles={format_counts(count_by_key(assignment_rows, 'assignment_role'))}"
        )
        writer.write_output(
            "  activity_stats "
            f"reviews_completed={len(review_rows)} "
            f"reviews_authored={len(authored_review_rows)} "
            f"qa_tests={len(qa_rows)} "
            f"approvals={len(approval_rows)} "
            f"deployments_approved={len(deployment_approval_rows)} "
            f"incidents_owned={len(incident_rows)} "
            f"meetings_organized={len(organized_meetings)} "
            f"meetings_attended={len(attended_meeting_ids)} "
            f"messages_sent={len(sent_messages)} "
            f"messages_received={len(received_messages)}"
        )
        writer.write_output(f"  assigned_task_ids={sorted_id_sample(assigned_task_ids)}")
        writer.write_output(f"  touched_task_ids={sorted_id_sample(touched_task_ids)}")


def main() -> None:
    generation_started_at = time.perf_counter()
    validate_config(CONFIG)
    rng = build_rng(CONFIG)
    writer = OutputManager(CONFIG)

    start_date = pd.Timestamp(CONFIG["simulation_start_date"])
    dates = pd.date_range(start=start_date, periods=int(CONFIG["simulation_days"]), freq="D")
    projects = build_projects(CONFIG, rng)
    employees, profiles, bottleneck_ids = build_employees(CONFIG, rng, start_date, projects)
    records: dict[str, list[dict[str, Any]]] = {table_name: [] for table_name in TABLE_SCHEMAS}
    counters: dict[str, int] = defaultdict(int)

    writer.write_output("== Bottleneck Employee Simulation ==")
    writer.write_output(f"Project: {PROJECT_NAME}")
    writer.write_output(f"Seed: {CONFIG['seed']}")
    writer.write_output(f"Employees: {len(employees)}")
    writer.write_output(f"Projects: {len(projects)}")
    writer.write_output(f"Simulation days: {len(dates)}")

    for date in dates:
        simulate_meetings_for_day(CONFIG, rng, records, counters, profiles, projects, pd.Timestamp(date))
        simulate_background_messages_for_day(CONFIG, rng, records, counters, profiles, pd.Timestamp(date))

        weekday = pd.Timestamp(date).weekday()
        task_lambda = float(CONFIG["scale"]["base_tasks_per_weekday"]) * float(
            CONFIG["activity"]["weekday_task_multipliers"][weekday]
        )
        daily_task_count = max(int(CONFIG["scale"]["minimum_tasks_per_day"]), int(rng.poisson(task_lambda)))
        if weekday >= 5:
            daily_task_count = max(1, daily_task_count)

        for _ in range(daily_task_count):
            pipeline_name = choose_pipeline(CONFIG, rng, weekday)
            if pipeline_name == "large_feature":
                priority = choose_priority(CONFIG, rng, pipeline_name)
                created_at = random_creation_time(CONFIG, rng, pd.Timestamp(date), pipeline_name, priority)
                simulate_large_feature(CONFIG, rng, records, counters, profiles, projects, created_at)
            else:
                priority = choose_priority(CONFIG, rng, pipeline_name)
                created_at = random_creation_time(CONFIG, rng, pd.Timestamp(date), pipeline_name, priority)
                simulate_regular_pipeline(
                    CONFIG,
                    rng,
                    records,
                    counters,
                    profiles,
                    projects,
                    pipeline_name,
                    created_at,
                )

    validate_generated_outputs(CONFIG, records, employees, projects, bottleneck_ids)

    writer.write_table("employee", employees)
    writer.write_table("project", projects)
    for table_name in TABLE_SCHEMAS:
        if table_name in {"employee", "project"}:
            continue
        writer.write_table(table_name, records[table_name])
    writer.write_answer(bottleneck_ids)
    write_bottleneck_employee_report(writer, records, profiles, bottleneck_ids)

    writer.write_output("")
    writer.write_output("== Final Summary ==")
    for table_name in TABLE_SCHEMAS:
        if table_name == "employee":
            count = len(employees)
        elif table_name == "project":
            count = len(projects)
        else:
            count = len(records[table_name])
        writer.write_output(f"{table_name}: {count}")
    writer.write_output(f"Bottleneck employees: {', '.join(str(value) for value in sorted(bottleneck_ids))}")

    generation_seconds = time.perf_counter() - generation_started_at
    runtime_message = f"Total generation time: {generation_seconds:.2f} seconds"
    writer.write_output(runtime_message)
    print(runtime_message)
    writer.close()


if __name__ == "__main__":
    main()
