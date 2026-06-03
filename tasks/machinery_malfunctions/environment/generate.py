import json
import os
import shutil
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    missing = exc.name or "pandas/numpy"
    raise SystemExit(
        f"Missing dependency {missing!r}. Install project dependencies with `uv sync` "
        "or run this generator with `uv run python harbor/tasks/machinery_malfunctions/environment/generate.py`."
    ) from exc


PROJECT_NAME = "machinery malfunctions"
OUTPUT_DIR_ENV = "MACHINERY_MALFUNCTIONS_OUTPUT_DIR"
ANSWER_PATH_ENV = "MACHINERY_MALFUNCTIONS_ANSWER_PATH"


CONFIG: dict[str, Any] = {
    "seed": 1,
    "max_generation_attempts": 20,
    "n_days": 365,
    "n_products": 30,
    "n_machine_types": 7,
    "n_machines": 56,
    "n_technicians": 42,
    "n_operators": 84,
    "n_fault_classes": 12,
    "n_defect_codes": 14,
    "jobs_per_day_min": 95,
    "jobs_per_day_max": 145,
    "batch_size_min": 250,
    "batch_size_max": 950,
    "inspection_delay_min": 0,
    "inspection_delay_max": 10,
    "maintenance_per_day_min": 6,
    "maintenance_per_day_max": 11,
    "maintenance_window_start_minute": 0,
    "maintenance_window_end_minute": 330,
    "maintenance_setup_gap_minutes": 5,
    "production_window_start_minute": 360,
    "production_window_end_minute": 1320,
    "production_setup_gap_min": 8,
    "production_setup_gap_max": 22,
    "runtime_service_threshold_min": 32,
    "runtime_service_threshold_max": 62,
    # Tiered technician structure: obvious / moderate / borderline / decoy / normal.
    "n_obvious_risky_technicians": 4,
    "n_moderate_risky_technicians": 4,
    "n_borderline_risky_technicians": 3,
    "n_decoy_technicians": 5,
    "obvious_intro_base_min": 0.055,
    "obvious_intro_base_max": 0.085,
    "obvious_risk_boost": 0.45,
    "obvious_n_risky_faults_min": 3,
    "obvious_n_risky_faults_max": 4,
    "obvious_n_risky_machine_types_min": 2,
    "obvious_n_risky_machine_types_max": 3,
    "obvious_removal_base_min": 0.30,
    "obvious_removal_base_max": 0.55,
    "moderate_intro_base_min": 0.022,
    "moderate_intro_base_max": 0.042,
    "moderate_risk_boost": 0.24,
    "moderate_n_risky_faults_min": 1,
    "moderate_n_risky_faults_max": 2,
    "moderate_n_risky_machine_types_min": 1,
    "moderate_n_risky_machine_types_max": 2,
    "moderate_removal_base_min": 0.40,
    "moderate_removal_base_max": 0.65,
    "borderline_intro_base_min": 0.013,
    "borderline_intro_base_max": 0.022,
    "borderline_risk_boost": 0.17,
    "borderline_n_risky_faults_min": 1,
    "borderline_n_risky_faults_max": 1,
    "borderline_n_risky_machine_types_min": 1,
    "borderline_n_risky_machine_types_max": 1,
    "borderline_removal_base_min": 0.48,
    "borderline_removal_base_max": 0.72,
    "normal_intro_base_min": 0.001,
    "normal_intro_base_max": 0.008,
    "normal_removal_base_min": 0.55,
    "normal_removal_base_max": 0.85,
    # Decoy technicians never introduce faults; they only look suspicious
    # because their assignment is biased toward high-load production days.
    "decoy_intro_base": 0.0,
    "decoy_load_excess_weight_boost": 10.0,
    "affected_products_per_fault_min": 2,
    "affected_products_per_fault_max": 5,
    "minimum_fault_age_before_random_removal": 4,
    "corrective_fault_removal_bonus": 0.22,
    "partial_repair_severity_multiplier": 0.58,
    "base_defect_rate_min": 0.006,
    "base_defect_rate_max": 0.020,
    "product_rejection_threshold_min": 0.045,
    "product_rejection_threshold_max": 0.075,
    "fault_effect_min": 0.045,
    "fault_effect_max": 0.140,
    "fault_intro_probability_cap": 0.55,
    "confirmed_technician_min_fault_caused_rejections": 3,
    "confirmed_technician_min_distinct_fault_work_orders": 2,
    "quality_gate_min_fault_caused_rejections": 90,
    "quality_gate_min_natural_rejections": 100,
    "quality_gate_min_confirmed_technicians": 8,
    "quality_gate_max_confirmed_technicians": 13,
    "quality_gate_min_products_with_responsible": 12,
    "quality_gate_max_products_with_responsible": 22,
    "quality_gate_min_responsible_pairs": 22,
    "quality_gate_min_single_evidence_pairs": 3,
    "quality_gate_min_high_evidence_pairs": 3,
    "quality_gate_high_evidence_threshold": 5,
    "quality_gate_min_decoy_suspicious_technicians": 2,
    "quality_gate_max_off_target_confirmed_technicians": 0,
    "decoy_suspicious_min_post_maintenance_rejections": 4,
    # When True, also write debug / ground-truth artifacts into ./debug/
    # relative to the current working directory.
    "write_debug_outputs": False,
    # When True, write seed_info.json into ./debug/ when running on host.
    "write_seed_info": False,
}


def main() -> None:
    generation_result = generate_until_quality_gate_passes()

    output_dir = Path(os.environ.get(OUTPUT_DIR_ENV, Path.cwd())).resolve()
    answer_path_raw = os.environ.get(ANSWER_PATH_ENV, "").strip()
    answer_path = Path(answer_path_raw).resolve() if answer_path_raw else None
    write_debug_outputs = bool(CONFIG["write_debug_outputs"])
    write_seed_info = bool(CONFIG["write_seed_info"])
    debug_dir = Path.cwd() / "debug" if (write_debug_outputs or write_seed_info) else None

    prepare_output_dir(output_dir)
    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)

    write_public_outputs(
        output_dir=output_dir,
        frames=generation_result["for_llm_frames"],
        raw_reports=generation_result["simulation"]["raw_reports"],
    )
    write_answer(answer_path, generation_result["answer"])
    write_additional_outputs(
        additional_dir=debug_dir,
        entities=generation_result["entities"],
        simulation=generation_result["simulation"],
        additional_frames=generation_result["additional_frames"],
        answer=generation_result["answer"],
        quality_summary=generation_result["quality_summary"],
        effective_seed=generation_result["effective_seed"],
        write_debug_outputs=write_debug_outputs,
        write_seed_info=write_seed_info,
    )
    validate_outputs(
        output_dir=output_dir,
        answer_path=answer_path,
        additional_dir=debug_dir,
        write_debug_outputs=write_debug_outputs,
        write_seed_info=write_seed_info,
        for_llm_frames=generation_result["for_llm_frames"],
        additional_frames=generation_result["additional_frames"],
        answer=generation_result["answer"],
        quality_summary=generation_result["quality_summary"],
    )


def generate_until_quality_gate_passes() -> dict[str, Any]:
    last_result = None

    for attempt in range(CONFIG["max_generation_attempts"]):
        effective_seed = CONFIG["seed"] + attempt
        rng = np.random.default_rng(effective_seed)

        entities = generate_entities(rng)
        simulation = run_simulation(rng, entities)

        for_llm_frames = build_for_llm_frames(entities, simulation)
        additional_frames = build_additional_frames(entities, simulation)
        answer = build_answer(additional_frames["batch_truth"])
        quality_summary = build_quality_summary(
            batch_truth=additional_frames["batch_truth"],
            answer=answer,
            full_maintenance=additional_frames["full_maintenance_work_orders"],
            technicians_hidden=entities["technicians_hidden"],
        )

        result = {
            "effective_seed": effective_seed,
            "entities": entities,
            "simulation": simulation,
            "for_llm_frames": for_llm_frames,
            "additional_frames": additional_frames,
            "answer": answer,
            "quality_summary": quality_summary,
        }
        last_result = result

        if quality_gate_passes(quality_summary):
            return result

    raise RuntimeError(
        "Unable to generate a dataset satisfying the quality gates. "
        f"Last quality summary: {json.dumps(last_result['quality_summary'], sort_keys=True)}"
    )


def prepare_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_reports_dir = output_dir / "raw_service_reports"
    if raw_reports_dir.exists():
        shutil.rmtree(raw_reports_dir)
    raw_reports_dir.mkdir(parents=True, exist_ok=True)


def generate_entities(rng: np.random.Generator) -> dict[str, Any]:
    product_ids = make_ids("P", CONFIG["n_products"], width=3)
    machine_type_ids = make_ids("MT", CONFIG["n_machine_types"], width=2)
    machine_ids = make_ids("M", CONFIG["n_machines"], width=3)
    technician_ids = make_ids("TECH", CONFIG["n_technicians"], width=3)
    operator_ids = make_ids("OP", CONFIG["n_operators"], width=3)
    fault_class_ids = make_ids("FAULT", CONFIG["n_fault_classes"], width=3)
    defect_codes = make_ids("D", CONFIG["n_defect_codes"], width=3)

    products_public, products_hidden, product_machine_type = generate_products(
        rng=rng,
        product_ids=product_ids,
        machine_type_ids=machine_type_ids,
    )
    machines_public, machines_hidden = generate_machines(
        rng=rng,
        machine_ids=machine_ids,
        machine_type_ids=machine_type_ids,
    )
    technicians_public, technicians_hidden = generate_technicians(
        rng=rng,
        technician_ids=technician_ids,
        machine_type_ids=machine_type_ids,
        fault_class_ids=fault_class_ids,
    )
    operators_public, operators_hidden = generate_operators(
        rng=rng,
        operator_ids=operator_ids,
    )
    fault_classes_hidden, fault_product_rows = generate_fault_classes(
        rng=rng,
        fault_class_ids=fault_class_ids,
        product_ids=product_ids,
        machine_type_ids=machine_type_ids,
        defect_codes=defect_codes,
    )

    return {
        "product_ids": product_ids,
        "machine_type_ids": machine_type_ids,
        "machine_ids": machine_ids,
        "technician_ids": technician_ids,
        "operator_ids": operator_ids,
        "fault_class_ids": fault_class_ids,
        "defect_codes": defect_codes,
        "products_public": products_public,
        "products_hidden": products_hidden,
        "machines_public": machines_public,
        "machines_hidden": machines_hidden,
        "technicians_public": technicians_public,
        "technicians_hidden": technicians_hidden,
        "operators_public": operators_public,
        "operators_hidden": operators_hidden,
        "fault_classes_hidden": fault_classes_hidden,
        "fault_product_rows": fault_product_rows,
        "product_machine_type": product_machine_type,
    }


def generate_products(
    rng: np.random.Generator,
    product_ids: list[str],
    machine_type_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    products_public = []
    products_hidden = {}
    product_machine_type = {}
    product_family_count = max(4, CONFIG["n_products"] // 5)

    for product_id in product_ids:
        nominal_batch_size = int(
            rng.integers(CONFIG["batch_size_min"], CONFIG["batch_size_max"] + 1)
        )
        threshold = float(
            rng.uniform(
                CONFIG["product_rejection_threshold_min"],
                CONFIG["product_rejection_threshold_max"],
            )
        )
        base_rate = float(
            rng.uniform(
                CONFIG["base_defect_rate_min"],
                CONFIG["base_defect_rate_max"],
            )
        )
        required_type = str(rng.choice(machine_type_ids))
        product_machine_type[product_id] = required_type

        products_public.append(
            {
                "product_id": product_id,
                "product_family": f"PF_{int(rng.integers(1, product_family_count + 1)):02d}",
                "nominal_batch_size": nominal_batch_size,
                "quality_rejection_threshold_pct": round_float(threshold, 5),
            }
        )
        products_hidden[product_id] = {
            "base_defect_rate": base_rate,
            "required_machine_type": required_type,
        }

    return products_public, products_hidden, product_machine_type


def generate_machines(
    rng: np.random.Generator,
    machine_ids: list[str],
    machine_type_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    machine_type_base_effect = {
        machine_type: float(rng.uniform(-0.003, 0.006))
        for machine_type in machine_type_ids
    }

    machines_public = []
    machines_hidden = {}

    for idx, machine_id in enumerate(machine_ids):
        machine_type = machine_type_ids[idx % len(machine_type_ids)]
        installation_group = f"LINE_{chr(65 + (idx % 6))}"
        base_capacity = int(rng.integers(5, 12))
        runtime_threshold = int(
            rng.integers(
                CONFIG["runtime_service_threshold_min"],
                CONFIG["runtime_service_threshold_max"] + 1,
            )
        )

        machines_public.append(
            {
                "machine_id": machine_id,
                "machine_type": machine_type,
                "installation_group": installation_group,
                "base_capacity_per_day": base_capacity,
            }
        )
        machines_hidden[machine_id] = {
            "machine_type": machine_type,
            "runtime_service_threshold": runtime_threshold,
            "base_effect": machine_type_base_effect[machine_type],
        }

    return machines_public, machines_hidden


def generate_technicians(
    rng: np.random.Generator,
    technician_ids: list[str],
    machine_type_ids: list[str],
    fault_class_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    technicians_public = []
    technicians_hidden = {}

    tier_assignment = assign_technician_tiers(rng, technician_ids)

    for technician_id in technician_ids:
        tier = tier_assignment[technician_id]
        team_id = f"TM_{chr(65 + int(rng.integers(0, 6)))}"
        technicians_public.append(
            {
                "technician_id": technician_id,
                "team_id": team_id,
            }
        )

        tier_params = TECHNICIAN_TIER_PARAMS[tier]
        intro_base = float(
            rng.uniform(tier_params["intro_base_min"], tier_params["intro_base_max"])
        )
        removal_base = float(
            rng.uniform(
                tier_params["removal_base_min"], tier_params["removal_base_max"]
            )
        )

        risky_faults: list[str] = []
        risky_machine_types: list[str] = []
        if tier_params["n_risky_faults_max"] > 0:
            n_risky_faults = int(
                rng.integers(
                    tier_params["n_risky_faults_min"],
                    tier_params["n_risky_faults_max"] + 1,
                )
            )
            n_risky_machine_types = int(
                rng.integers(
                    tier_params["n_risky_machine_types_min"],
                    tier_params["n_risky_machine_types_max"] + 1,
                )
            )
            risky_faults = rng.choice(
                fault_class_ids,
                size=n_risky_faults,
                replace=False,
            ).tolist()
            risky_machine_types = rng.choice(
                machine_type_ids,
                size=n_risky_machine_types,
                replace=False,
            ).tolist()

        technicians_hidden[technician_id] = {
            "tier": tier,
            "intro_base": intro_base,
            "removal_base": removal_base,
            "risky_faults": risky_faults,
            "risky_machine_types": risky_machine_types,
            "risk_boost": float(tier_params["risk_boost"]),
            "is_risky": tier in {"obvious", "moderate", "borderline"},
            "is_decoy": tier == "decoy",
        }

    return technicians_public, technicians_hidden


TECHNICIAN_TIER_ORDER: list[str] = ["obvious", "moderate", "borderline", "decoy"]


def assign_technician_tiers(
    rng: np.random.Generator,
    technician_ids: list[str],
) -> dict[str, str]:
    tier_counts = {
        "obvious": int(CONFIG["n_obvious_risky_technicians"]),
        "moderate": int(CONFIG["n_moderate_risky_technicians"]),
        "borderline": int(CONFIG["n_borderline_risky_technicians"]),
        "decoy": int(CONFIG["n_decoy_technicians"]),
    }
    total_special = sum(tier_counts.values())
    if total_special > len(technician_ids):
        raise ValueError(
            f"Tiered technician count {total_special} exceeds "
            f"available technicians ({len(technician_ids)})."
        )

    shuffled_ids = list(technician_ids)
    rng.shuffle(shuffled_ids)

    tier_assignment: dict[str, str] = {}
    cursor = 0
    for tier_name in TECHNICIAN_TIER_ORDER:
        count = tier_counts[tier_name]
        for tid in shuffled_ids[cursor : cursor + count]:
            tier_assignment[tid] = tier_name
        cursor += count

    for tid in shuffled_ids[cursor:]:
        tier_assignment[tid] = "normal"

    return tier_assignment


def _build_technician_tier_params() -> dict[str, dict[str, float]]:
    params: dict[str, dict[str, float]] = {}
    for tier_name in TECHNICIAN_TIER_ORDER:
        if tier_name == "decoy":
            decoy_intro = float(CONFIG["decoy_intro_base"])
            params[tier_name] = {
                "intro_base_min": decoy_intro,
                "intro_base_max": decoy_intro,
                "risk_boost": 0.0,
                "n_risky_faults_min": 0,
                "n_risky_faults_max": 0,
                "n_risky_machine_types_min": 0,
                "n_risky_machine_types_max": 0,
                "removal_base_min": CONFIG["normal_removal_base_min"],
                "removal_base_max": CONFIG["normal_removal_base_max"],
            }
            continue
        params[tier_name] = {
            "intro_base_min": CONFIG[f"{tier_name}_intro_base_min"],
            "intro_base_max": CONFIG[f"{tier_name}_intro_base_max"],
            "risk_boost": CONFIG[f"{tier_name}_risk_boost"],
            "n_risky_faults_min": CONFIG[f"{tier_name}_n_risky_faults_min"],
            "n_risky_faults_max": CONFIG[f"{tier_name}_n_risky_faults_max"],
            "n_risky_machine_types_min": CONFIG[
                f"{tier_name}_n_risky_machine_types_min"
            ],
            "n_risky_machine_types_max": CONFIG[
                f"{tier_name}_n_risky_machine_types_max"
            ],
            "removal_base_min": CONFIG[f"{tier_name}_removal_base_min"],
            "removal_base_max": CONFIG[f"{tier_name}_removal_base_max"],
        }
    params["normal"] = {
        "intro_base_min": CONFIG["normal_intro_base_min"],
        "intro_base_max": CONFIG["normal_intro_base_max"],
        "risk_boost": 0.0,
        "n_risky_faults_min": 0,
        "n_risky_faults_max": 0,
        "n_risky_machine_types_min": 0,
        "n_risky_machine_types_max": 0,
        "removal_base_min": CONFIG["normal_removal_base_min"],
        "removal_base_max": CONFIG["normal_removal_base_max"],
    }
    return params


TECHNICIAN_TIER_PARAMS: dict[str, dict[str, float]] = _build_technician_tier_params()


def generate_operators(
    rng: np.random.Generator,
    operator_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    operators_public = []
    operators_hidden = {}

    experience_bands = np.array(["LOW", "MEDIUM", "HIGH"])
    experience_probs = np.array([0.25, 0.55, 0.20])

    for operator_id in operator_ids:
        experience = str(rng.choice(experience_bands, p=experience_probs))
        shift_group = f"SHIFT_{chr(65 + int(rng.integers(0, 4)))}"

        operators_public.append(
            {
                "operator_id": operator_id,
                "shift_group": shift_group,
                "experience_band": experience,
            }
        )

        if experience == "HIGH":
            modifier = float(rng.uniform(-0.004, 0.001))
        elif experience == "MEDIUM":
            modifier = float(rng.uniform(-0.0015, 0.0035))
        else:
            modifier = float(rng.uniform(0.0015, 0.0070))

        operators_hidden[operator_id] = {
            "quality_modifier": modifier,
        }

    return operators_public, operators_hidden


def generate_fault_classes(
    rng: np.random.Generator,
    fault_class_ids: list[str],
    product_ids: list[str],
    machine_type_ids: list[str],
    defect_codes: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fault_classes_hidden = {}
    fault_product_rows = []

    for fault_class in fault_class_ids:
        n_affected_products = int(
            rng.integers(
                CONFIG["affected_products_per_fault_min"],
                CONFIG["affected_products_per_fault_max"] + 1,
            )
        )
        n_machine_types = int(rng.integers(2, min(5, len(machine_type_ids)) + 1))

        affected_products = rng.choice(
            product_ids,
            size=n_affected_products,
            replace=False,
        ).tolist()
        compatible_machine_types = rng.choice(
            machine_type_ids,
            size=n_machine_types,
            replace=False,
        ).tolist()

        primary_codes = rng.choice(defect_codes, size=2, replace=False).tolist()
        secondary_codes = rng.choice(defect_codes, size=3, replace=False).tolist()

        product_effects = {}
        for product_id in affected_products:
            effect_strength = float(
                rng.uniform(CONFIG["fault_effect_min"], CONFIG["fault_effect_max"])
            )
            product_effects[product_id] = effect_strength
            fault_product_rows.append(
                {
                    "fault_class": fault_class,
                    "product_id": product_id,
                    "fault_effect_strength": round_float(effect_strength, 5),
                    "primary_defect_code": primary_codes[0],
                }
            )

        fault_classes_hidden[fault_class] = {
            "affected_products": affected_products,
            "compatible_machine_types": compatible_machine_types,
            "product_effects": product_effects,
            "primary_defect_codes": primary_codes,
            "secondary_defect_codes": secondary_codes,
            "base_persistence": float(rng.uniform(0.45, 0.92)),
        }

    return fault_classes_hidden, fault_product_rows


def run_simulation(
    rng: np.random.Generator,
    entities: dict[str, Any],
) -> dict[str, Any]:
    maintenance_index_rows = []
    full_maintenance_rows = []
    production_job_rows = []
    assignment_rows = []
    batch_rows = []
    inspection_rows = []
    operator_shift_rows = []
    daily_condition_rows = []

    hidden_fault_intervals = []
    batch_truth_rows = []
    simulation_events = []
    simulation_output_lines = []
    raw_reports = []

    machine_state = initialize_machine_state(entities["machine_ids"])
    runtime_since_service = {machine_id: 0 for machine_id in entities["machine_ids"]}
    recent_rejection_score = {machine_id: 0.0 for machine_id in entities["machine_ids"]}

    pending_inspections_by_day: dict[int, list[dict[str, Any]]] = {
        day: [] for day in range(1, CONFIG["n_days"] + 1)
    }

    counters = {
        "work_order": 0,
        "job": 0,
        "batch": 0,
        "interval": 0,
    }

    daily_conditions = generate_daily_conditions(rng)

    for day in range(1, CONFIG["n_days"] + 1):
        condition = daily_conditions[day]
        daily_condition_rows.append(condition)

        day_operator_map = assign_daily_operators(
            rng=rng,
            day=day,
            entities=entities,
            operator_shift_rows=operator_shift_rows,
        )

        perform_daily_maintenance(
            rng=rng,
            day=day,
            entities=entities,
            condition=condition,
            machine_state=machine_state,
            runtime_since_service=runtime_since_service,
            recent_rejection_score=recent_rejection_score,
            counters=counters,
            maintenance_index_rows=maintenance_index_rows,
            full_maintenance_rows=full_maintenance_rows,
            hidden_fault_intervals=hidden_fault_intervals,
            simulation_events=simulation_events,
            simulation_output_lines=simulation_output_lines,
            raw_reports=raw_reports,
        )

        daily_machine_plan = {
            machine_id: {
                "count": 0,
                "next_available_minute": CONFIG["production_window_start_minute"],
            }
            for machine_id in entities["machine_ids"]
        }

        n_jobs = int(
            rng.integers(CONFIG["jobs_per_day_min"], CONFIG["jobs_per_day_max"] + 1)
        )

        for _ in range(n_jobs):
            job = create_production_job(rng, day, entities, counters)
            production_job_rows.append(job)

            assignment = assign_job_to_machine(
                rng=rng,
                day=day,
                job=job,
                entities=entities,
                daily_machine_plan=daily_machine_plan,
            )
            assignment_rows.append(assignment)

            batch, pending_inspection = produce_batch(
                rng=rng,
                day=day,
                job=job,
                assignment=assignment,
                entities=entities,
                condition=condition,
                machine_state=machine_state,
                day_operator_map=day_operator_map,
                counters=counters,
                simulation_events=simulation_events,
            )
            batch_rows.append(batch)
            pending_inspections_by_day[pending_inspection["inspection_day"]].append(
                pending_inspection
            )
            runtime_since_service[assignment["machine_id"]] += 1

        for inspection in pending_inspections_by_day[day]:
            public_row, truth_row = inspect_batch(inspection)
            inspection_rows.append(public_row)
            batch_truth_rows.append(truth_row)

            if public_row["inspection_result"] == "REJECTED":
                machine_id = inspection["machine_id"]
                recent_rejection_score[machine_id] += 2.0

                if truth_row["fault_caused_rejection"]:
                    recent_rejection_score[machine_id] += 2.8
                    simulation_output_lines.append(
                        (
                            f"Day {day:03d}: {inspection['batch_id']} "
                            f"for {inspection['product_id']} was rejected; "
                            f"fault contribution was necessary. "
                            f"Responsible technician: "
                            f"{truth_row['responsible_technician_id']}."
                        )
                    )
                    simulation_events.append(
                        {
                            "day": day,
                            "event_type": "fault_caused_rejection",
                            "batch_id": inspection["batch_id"],
                            "product_id": inspection["product_id"],
                            "machine_id": inspection["machine_id"],
                            "fault_class": truth_row["fault_class"],
                            "responsible_technician_id": (
                                truth_row["responsible_technician_id"]
                            ),
                            "responsible_work_order_id": (
                                truth_row["responsible_work_order_id"]
                            ),
                        }
                    )

        pending_inspections_by_day[day] = []
        decay_priority_scores(recent_rejection_score, multiplier=0.72)

    close_open_fault_intervals(
        hidden_fault_intervals=hidden_fault_intervals,
        machine_state=machine_state,
    )

    remaining_pending = sum(len(items) for items in pending_inspections_by_day.values())
    if remaining_pending:
        raise RuntimeError(f"{remaining_pending} inspections were not processed.")

    return {
        "maintenance_index_rows": maintenance_index_rows,
        "full_maintenance_rows": full_maintenance_rows,
        "production_job_rows": production_job_rows,
        "assignment_rows": assignment_rows,
        "batch_rows": batch_rows,
        "inspection_rows": inspection_rows,
        "operator_shift_rows": operator_shift_rows,
        "daily_condition_rows": daily_condition_rows,
        "hidden_fault_intervals": hidden_fault_intervals,
        "batch_truth_rows": batch_truth_rows,
        "simulation_events": simulation_events,
        "simulation_output_lines": simulation_output_lines,
        "raw_reports": raw_reports,
    }


def initialize_machine_state(machine_ids: list[str]) -> dict[str, dict[str, Any]]:
    return {
        machine_id: {
            "active_fault_class": None,
            "fault_severity": 0.0,
            "fault_origin_technician_id": None,
            "fault_origin_work_order_id": None,
            "fault_start_day": None,
            "fault_interval_id": None,
        }
        for machine_id in machine_ids
    }


def generate_daily_conditions(rng: np.random.Generator) -> dict[int, dict[str, Any]]:
    rows = {}

    for day in range(1, CONFIG["n_days"] + 1):
        seasonal = np.sin(2 * np.pi * day / 365.0)
        load_index = float(
            np.clip(rng.normal(1.0 + 0.12 * seasonal, 0.08), 0.75, 1.35)
        )
        humidity_index = float(
            np.clip(rng.normal(1.0 - 0.08 * seasonal, 0.07), 0.75, 1.30)
        )
        material_variation_index = float(np.clip(rng.normal(1.0, 0.09), 0.70, 1.35))
        power_stability_index = float(np.clip(rng.normal(1.0, 0.06), 0.80, 1.20))

        rows[day] = {
            "day": day,
            "load_index": round_float(load_index, 5),
            "humidity_index": round_float(humidity_index, 5),
            "material_variation_index": round_float(material_variation_index, 5),
            "power_stability_index": round_float(power_stability_index, 5),
        }

    return rows


def assign_daily_operators(
    rng: np.random.Generator,
    day: int,
    entities: dict[str, Any],
    operator_shift_rows: list[dict[str, Any]],
) -> dict[str, str]:
    result = {}

    for machine_id in entities["machine_ids"]:
        operator_id = str(rng.choice(entities["operator_ids"]))
        result[machine_id] = operator_id
        operator_shift_rows.append(
            {
                "day": day,
                "shift_id": f"SHIFT_{1 + ((day + int(machine_id[-3:])) % 3)}",
                "machine_id": machine_id,
                "operator_id": operator_id,
            }
        )

    return result


def perform_daily_maintenance(
    rng: np.random.Generator,
    day: int,
    entities: dict[str, Any],
    condition: dict[str, Any],
    machine_state: dict[str, dict[str, Any]],
    runtime_since_service: dict[str, int],
    recent_rejection_score: dict[str, float],
    counters: dict[str, int],
    maintenance_index_rows: list[dict[str, Any]],
    full_maintenance_rows: list[dict[str, Any]],
    hidden_fault_intervals: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    simulation_output_lines: list[str],
    raw_reports: list[dict[str, str]],
) -> None:
    n_maintenance = int(
        rng.integers(
            CONFIG["maintenance_per_day_min"],
            CONFIG["maintenance_per_day_max"] + 1,
        )
    )
    machines_to_service = select_machines_for_maintenance(
        rng=rng,
        entities=entities,
        runtime_since_service=runtime_since_service,
        recent_rejection_score=recent_rejection_score,
        n_maintenance=n_maintenance,
    )

    technician_available_after = {
        technician_id: CONFIG["maintenance_window_start_minute"]
        for technician_id in entities["technician_ids"]
    }

    for machine_id in machines_to_service:
        duration_minutes = int(rng.integers(35, 155))
        latest_start_minute = CONFIG["maintenance_window_end_minute"] - duration_minutes
        if latest_start_minute < CONFIG["maintenance_window_start_minute"]:
            continue

        technician_id = choose_available_technician(
            rng=rng,
            entities=entities,
            technician_available_after=technician_available_after,
            latest_start_minute=latest_start_minute,
            condition=condition,
        )

        earliest_start_minute = max(
            CONFIG["maintenance_window_start_minute"],
            technician_available_after[technician_id],
        )
        if earliest_start_minute > latest_start_minute:
            continue

        start_total_minutes = int(
            rng.integers(earliest_start_minute, latest_start_minute + 1)
        )
        completed_total_minutes = start_total_minutes + duration_minutes
        technician_available_after[technician_id] = (
            completed_total_minutes + CONFIG["maintenance_setup_gap_minutes"]
        )

        counters["work_order"] += 1
        work_order_id = f"WO_{counters['work_order']:06d}"

        maintenance_type, reported_reason = classify_maintenance_reason(
            machine_id=machine_id,
            runtime_since_service=runtime_since_service,
            recent_rejection_score=recent_rejection_score,
            rng=rng,
        )

        started_at = minutes_to_time(start_total_minutes)
        completed_at = minutes_to_time(completed_total_minutes)

        report_path = (
            f"raw_service_reports/day_{day:03d}/"
            f"day_{day:03d}_{work_order_id}_service.txt"
        )

        maintenance_index_rows.append(
            {
                "day": day,
                "work_order_id": work_order_id,
                "report_path": report_path,
                "document_type": "SERVICE_REPORT",
                "status": "CLOSED",
            }
        )

        full_maintenance_rows.append(
            {
                "day": day,
                "work_order_id": work_order_id,
                "machine_id": machine_id,
                "technician_id": technician_id,
                "maintenance_type": maintenance_type,
                "reported_reason": reported_reason,
                "started_at": started_at,
                "completed_at": completed_at,
                "status": "CLOSED",
                "report_path": report_path,
            }
        )

        raw_reports.append(
            {
                "relative_path": (
                    f"day_{day:03d}/day_{day:03d}_{work_order_id}_service.txt"
                ),
                "content": build_raw_service_report(
                    day=day,
                    work_order_id=work_order_id,
                    machine_id=machine_id,
                    technician_id=technician_id,
                    maintenance_type=maintenance_type,
                    reported_reason=reported_reason,
                    started_at=started_at,
                    completed_at=completed_at,
                ),
            }
        )

        apply_maintenance_effect(
            rng=rng,
            day=day,
            machine_id=machine_id,
            technician_id=technician_id,
            work_order_id=work_order_id,
            maintenance_type=maintenance_type,
            reported_reason=reported_reason,
            entities=entities,
            condition=condition,
            machine_state=machine_state,
            hidden_fault_intervals=hidden_fault_intervals,
            counters=counters,
            simulation_events=simulation_events,
            simulation_output_lines=simulation_output_lines,
        )

        runtime_since_service[machine_id] = 0
        recent_rejection_score[machine_id] = 0.0


def select_machines_for_maintenance(
    rng: np.random.Generator,
    entities: dict[str, Any],
    runtime_since_service: dict[str, int],
    recent_rejection_score: dict[str, float],
    n_maintenance: int,
) -> list[str]:
    scores = []

    for machine_id in entities["machine_ids"]:
        threshold = entities["machines_hidden"][machine_id]["runtime_service_threshold"]
        runtime_score = max(0.0, runtime_since_service[machine_id] / threshold - 0.7)
        score = (
            2.7 * recent_rejection_score[machine_id]
            + runtime_score
            + float(rng.uniform(0.0, 0.35))
        )
        scores.append((machine_id, score))

    scores = sorted(scores, key=lambda item: (-item[1], item[0]))
    return [machine_id for machine_id, _ in scores[:n_maintenance]]


def choose_available_technician(
    rng: np.random.Generator,
    entities: dict[str, Any],
    technician_available_after: dict[str, int],
    latest_start_minute: int,
    condition: dict[str, Any] | None = None,
) -> str:
    eligible = [
        technician_id
        for technician_id in entities["technician_ids"]
        if technician_available_after[technician_id] <= latest_start_minute
    ]

    if not eligible:
        eligible = sorted(
            entities["technician_ids"],
            key=lambda technician_id: (
                technician_available_after[technician_id],
                technician_id,
            ),
        )[:1]

    return choose_technician(
        rng=rng,
        entities=entities,
        eligible_technician_ids=eligible,
        condition=condition,
    )


def choose_technician(
    rng: np.random.Generator,
    entities: dict[str, Any],
    eligible_technician_ids: list[str] | None = None,
    condition: dict[str, Any] | None = None,
) -> str:
    technician_ids = eligible_technician_ids or entities["technician_ids"]
    weights = []

    load_excess = 0.0
    if condition is not None:
        load_excess = max(0.0, float(condition["load_index"]) - 1.0)
    decoy_load_boost = float(CONFIG["decoy_load_excess_weight_boost"]) * load_excess

    for technician_id in technician_ids:
        hidden = entities["technicians_hidden"][technician_id]
        base = 1.0
        if hidden.get("is_risky"):
            base += 0.10
        if hidden.get("is_decoy") and decoy_load_boost > 0.0:
            base += decoy_load_boost
        weights.append(base)

    weights_array = np.array(weights, dtype=float)
    weights_array = weights_array / weights_array.sum()

    return str(rng.choice(technician_ids, p=weights_array))


def classify_maintenance_reason(
    machine_id: str,
    runtime_since_service: dict[str, int],
    recent_rejection_score: dict[str, float],
    rng: np.random.Generator,
) -> tuple[str, str]:
    if recent_rejection_score[machine_id] >= 2.0:
        return "CORRECTIVE", "RECENT_REJECTIONS"

    if runtime_since_service[machine_id] > CONFIG["runtime_service_threshold_min"]:
        if rng.uniform() < 0.60:
            return "PREVENTIVE", "HIGH_RUNTIME"

    maintenance_types = np.array(["PREVENTIVE", "CALIBRATION", "INSPECTION", "RESET"])
    probabilities = np.array([0.35, 0.34, 0.23, 0.08])
    maintenance_type = str(rng.choice(maintenance_types, p=probabilities))

    if maintenance_type == "PREVENTIVE":
        reason = "SCHEDULED"
    elif maintenance_type == "CALIBRATION":
        reason = "SCHEDULED_CALIBRATION"
    elif maintenance_type == "RESET":
        reason = "PROCESS_RESET"
    else:
        reason = "RANDOM_CHECK"

    return maintenance_type, reason


def build_raw_service_report(
    day: int,
    work_order_id: str,
    machine_id: str,
    technician_id: str,
    maintenance_type: str,
    reported_reason: str,
    started_at: str,
    completed_at: str,
) -> str:
    return (
        "MAINTENANCE NOTE\n"
        f"DAY: {day}\n"
        f"WORK ORDER: {work_order_id}\n"
        f"MACHINE: {machine_id}\n"
        f"TECHNICIAN: {technician_id}\n"
        f"WORK TYPE: {maintenance_type}\n"
        f"REPORTED REASON: {reported_reason}\n"
        f"STARTED: {started_at}\n"
        f"COMPLETED: {completed_at}\n"
        "FINAL STATUS: CLOSED\n"
    )


def apply_maintenance_effect(
    rng: np.random.Generator,
    day: int,
    machine_id: str,
    technician_id: str,
    work_order_id: str,
    maintenance_type: str,
    reported_reason: str,
    entities: dict[str, Any],
    condition: dict[str, Any],
    machine_state: dict[str, dict[str, Any]],
    hidden_fault_intervals: list[dict[str, Any]],
    counters: dict[str, int],
    simulation_events: list[dict[str, Any]],
    simulation_output_lines: list[str],
) -> None:
    state = machine_state[machine_id]
    technician_hidden = entities["technicians_hidden"][technician_id]
    machine_type = entities["machines_hidden"][machine_id]["machine_type"]

    if state["active_fault_class"] is not None:
        handled = try_repair_existing_fault(
            rng=rng,
            day=day,
            machine_id=machine_id,
            technician_id=technician_id,
            work_order_id=work_order_id,
            maintenance_type=maintenance_type,
            reported_reason=reported_reason,
            technician_hidden=technician_hidden,
            machine_state=machine_state,
            hidden_fault_intervals=hidden_fault_intervals,
            simulation_events=simulation_events,
            simulation_output_lines=simulation_output_lines,
            entities=entities,
        )
        if handled:
            return

    intro_probability = compute_fault_intro_probability(
        technician_hidden=technician_hidden,
        machine_type=machine_type,
        condition=condition,
        maintenance_type=maintenance_type,
    )

    if rng.uniform() >= intro_probability:
        return

    possible_faults = [
        fault_class
        for fault_class, fault_data in entities["fault_classes_hidden"].items()
        if machine_type in fault_data["compatible_machine_types"]
    ]
    if not possible_faults:
        return

    boosted_faults = [
        fault_class
        for fault_class in possible_faults
        if fault_class in technician_hidden["risky_faults"]
    ]

    if boosted_faults and rng.uniform() < 0.78:
        fault_class = str(rng.choice(boosted_faults))
    else:
        fault_class = str(rng.choice(possible_faults))

    if state["active_fault_class"] is not None:
        close_fault_interval(
            hidden_fault_intervals=hidden_fault_intervals,
            interval_id=state["fault_interval_id"],
            removed_day=day,
            removed_by_work_order_id=work_order_id,
        )

    counters["interval"] += 1
    interval_id = f"FI_{counters['interval']:06d}"
    severity = float(rng.uniform(0.82, 1.42))

    state["active_fault_class"] = fault_class
    state["fault_severity"] = round_float(severity, 5)
    state["fault_origin_technician_id"] = technician_id
    state["fault_origin_work_order_id"] = work_order_id
    state["fault_start_day"] = day
    state["fault_interval_id"] = interval_id

    hidden_fault_intervals.append(
        {
            "fault_interval_id": interval_id,
            "machine_id": machine_id,
            "fault_class": fault_class,
            "introduced_day": day,
            "removed_day": None,
            "introduced_by_work_order_id": work_order_id,
            "introduced_by_technician_id": technician_id,
            "removed_by_work_order_id": None,
            "severity": round_float(severity, 5),
        }
    )

    simulation_events.append(
        {
            "day": day,
            "event_type": "fault_introduced",
            "machine_id": machine_id,
            "technician_id": technician_id,
            "work_order_id": work_order_id,
            "fault_class": fault_class,
            "severity": round_float(severity, 5),
        }
    )
    simulation_output_lines.append(
        f"Day {day:03d}: {technician_id} introduced {fault_class} on {machine_id}."
    )


def try_repair_existing_fault(
    rng: np.random.Generator,
    day: int,
    machine_id: str,
    technician_id: str,
    work_order_id: str,
    maintenance_type: str,
    reported_reason: str,
    technician_hidden: dict[str, Any],
    machine_state: dict[str, dict[str, Any]],
    hidden_fault_intervals: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    simulation_output_lines: list[str],
    entities: dict[str, Any],
) -> bool:
    state = machine_state[machine_id]
    fault_age = day - int(state["fault_start_day"])
    fault_class = state["active_fault_class"]
    fault_data = entities["fault_classes_hidden"][fault_class]

    removal_prob = technician_hidden["removal_base"]

    if maintenance_type == "CORRECTIVE":
        removal_prob += CONFIG["corrective_fault_removal_bonus"]
    if reported_reason in {"RECENT_REJECTIONS", "DOWNTIME"}:
        removal_prob += 0.10

    persistence = float(fault_data["base_persistence"])
    removal_prob *= 1.08 - (persistence * 0.35)

    if (
        fault_age < CONFIG["minimum_fault_age_before_random_removal"]
        and maintenance_type != "CORRECTIVE"
    ):
        removal_prob *= 0.12

    removal_prob = float(np.clip(removal_prob, 0.03, 0.96))
    draw = float(rng.uniform())

    if draw < removal_prob:
        close_fault_interval(
            hidden_fault_intervals=hidden_fault_intervals,
            interval_id=state["fault_interval_id"],
            removed_day=day,
            removed_by_work_order_id=work_order_id,
        )
        simulation_events.append(
            {
                "day": day,
                "event_type": "fault_removed",
                "machine_id": machine_id,
                "technician_id": technician_id,
                "work_order_id": work_order_id,
                "removed_fault_class": state["active_fault_class"],
            }
        )
        simulation_output_lines.append(
            (
                f"Day {day:03d}: {technician_id} removed "
                f"{state['active_fault_class']} from {machine_id}."
            )
        )
        reset_machine_fault_state(state)
        return True

    if draw < removal_prob + 0.16:
        state["fault_severity"] = round_float(
            state["fault_severity"] * CONFIG["partial_repair_severity_multiplier"],
            5,
        )
        simulation_events.append(
            {
                "day": day,
                "event_type": "fault_partially_repaired",
                "machine_id": machine_id,
                "technician_id": technician_id,
                "work_order_id": work_order_id,
                "fault_class": state["active_fault_class"],
                "remaining_severity": state["fault_severity"],
            }
        )
        return True

    return False


def compute_fault_intro_probability(
    technician_hidden: dict[str, Any],
    machine_type: str,
    condition: dict[str, Any],
    maintenance_type: str,
) -> float:
    probability = technician_hidden["intro_base"]

    if (
        technician_hidden["is_risky"]
        and machine_type in technician_hidden["risky_machine_types"]
    ):
        probability = max(probability, float(technician_hidden["risk_boost"]))

    if maintenance_type == "CALIBRATION":
        probability *= 1.35
    elif maintenance_type == "RESET":
        probability *= 1.15
    elif maintenance_type == "INSPECTION":
        probability *= 0.70
    elif maintenance_type == "CORRECTIVE":
        probability *= 0.82

    probability *= 1.0 + max(0.0, float(condition["load_index"]) - 1.0) * 0.75
    return float(np.clip(probability, 0.0, CONFIG["fault_intro_probability_cap"]))


def close_fault_interval(
    hidden_fault_intervals: list[dict[str, Any]],
    interval_id: str,
    removed_day: int,
    removed_by_work_order_id: str,
) -> None:
    for row in hidden_fault_intervals:
        if row["fault_interval_id"] == interval_id:
            row["removed_day"] = removed_day
            row["removed_by_work_order_id"] = removed_by_work_order_id
            return


def reset_machine_fault_state(state: dict[str, Any]) -> None:
    state["active_fault_class"] = None
    state["fault_severity"] = 0.0
    state["fault_origin_technician_id"] = None
    state["fault_origin_work_order_id"] = None
    state["fault_start_day"] = None
    state["fault_interval_id"] = None


def create_production_job(
    rng: np.random.Generator,
    day: int,
    entities: dict[str, Any],
    counters: dict[str, int],
) -> dict[str, Any]:
    counters["job"] += 1
    job_id = f"JOB_{counters['job']:06d}"
    product_id = str(rng.choice(entities["product_ids"]))
    product_hidden = entities["products_hidden"][product_id]

    nominal = next(
        item["nominal_batch_size"]
        for item in entities["products_public"]
        if item["product_id"] == product_id
    )
    planned_quantity = int(
        np.clip(
            rng.normal(nominal, nominal * 0.18),
            CONFIG["batch_size_min"],
            CONFIG["batch_size_max"],
        )
    )

    difficulty = int(rng.choice([1, 2, 3, 4, 5], p=[0.18, 0.30, 0.28, 0.17, 0.07]))
    priority = str(
        rng.choice(
            np.array(["LOW", "NORMAL", "HIGH"]),
            p=np.array([0.18, 0.68, 0.14]),
        )
    )

    return {
        "day": day,
        "job_id": job_id,
        "product_id": product_id,
        "required_machine_type": product_hidden["required_machine_type"],
        "planned_quantity": planned_quantity,
        "job_difficulty": difficulty,
        "priority": priority,
    }


def assign_job_to_machine(
    rng: np.random.Generator,
    day: int,
    job: dict[str, Any],
    entities: dict[str, Any],
    daily_machine_plan: dict[str, dict[str, int]],
) -> dict[str, Any]:
    candidate_machines = [
        machine_id
        for machine_id in entities["machine_ids"]
        if entities["machines_hidden"][machine_id]["machine_type"]
        == job["required_machine_type"]
    ]
    candidate_machines = sorted(candidate_machines)

    public_machine_by_id = {
        item["machine_id"]: item for item in entities["machines_public"]
    }

    duration_minutes = int(rng.integers(35, 115))

    feasible = []
    for machine_id in candidate_machines:
        count = daily_machine_plan[machine_id]["count"]
        min_setup_gap = 0 if count == 0 else CONFIG["production_setup_gap_min"]
        earliest_start = max(
            CONFIG["production_window_start_minute"],
            daily_machine_plan[machine_id]["next_available_minute"] + min_setup_gap,
        )
        if earliest_start + duration_minutes <= CONFIG["production_window_end_minute"]:
            feasible.append(machine_id)

    if not feasible:
        raise RuntimeError(
            f"No feasible machine for job {job['job_id']} on day {day}: "
            f"all candidates would exceed the production window "
            f"(duration={duration_minutes} min)."
        )

    candidate_machines = feasible

    def assignment_score(machine_id: str) -> tuple[float, int, str]:
        count = daily_machine_plan[machine_id]["count"]
        capacity = max(1, int(public_machine_by_id[machine_id]["base_capacity_per_day"]))
        load_ratio = count / capacity
        next_available = daily_machine_plan[machine_id]["next_available_minute"]
        return (
            load_ratio + float(rng.uniform(0.0, 0.025)),
            next_available,
            machine_id,
        )

    machine_id = min(candidate_machines, key=assignment_score)

    current_count = daily_machine_plan[machine_id]["count"]
    sequence = current_count + 1

    if current_count > 0:
        max_gap_allowed = max(
            CONFIG["production_setup_gap_min"],
            CONFIG["production_window_end_minute"]
            - daily_machine_plan[machine_id]["next_available_minute"]
            - duration_minutes,
        )
        setup_gap_high = min(CONFIG["production_setup_gap_max"], max_gap_allowed)
        setup_gap = int(
            rng.integers(CONFIG["production_setup_gap_min"], setup_gap_high + 1)
        )
    else:
        setup_gap = 0

    jitter_max = 7
    latest_start = CONFIG["production_window_end_minute"] - duration_minutes
    base_start = max(
        CONFIG["production_window_start_minute"],
        daily_machine_plan[machine_id]["next_available_minute"] + setup_gap,
    )
    jitter = int(rng.integers(0, jitter_max + 1))
    start_total_minutes = min(base_start + jitter, latest_start)
    end_total_minutes = start_total_minutes + duration_minutes

    daily_machine_plan[machine_id]["count"] = sequence
    daily_machine_plan[machine_id]["next_available_minute"] = end_total_minutes

    return {
        "day": day,
        "job_id": job["job_id"],
        "machine_id": machine_id,
        "sequence_on_machine": sequence,
        "start_time": minutes_to_time(start_total_minutes),
        "end_time": minutes_to_time(end_total_minutes),
    }


def produce_batch(
    rng: np.random.Generator,
    day: int,
    job: dict[str, Any],
    assignment: dict[str, Any],
    entities: dict[str, Any],
    condition: dict[str, Any],
    machine_state: dict[str, dict[str, Any]],
    day_operator_map: dict[str, str],
    counters: dict[str, int],
    simulation_events: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    counters["batch"] += 1
    batch_id = f"BATCH_{counters['batch']:06d}"
    product_id = job["product_id"]
    machine_id = assignment["machine_id"]
    quantity = int(job["planned_quantity"])
    operator_id = day_operator_map[machine_id]

    natural_rate = compute_natural_defect_rate(
        product_id=product_id,
        machine_id=machine_id,
        operator_id=operator_id,
        job=job,
        entities=entities,
        condition=condition,
    )
    natural_rejected = int(rng.binomial(quantity, natural_rate))

    fault_rate, fault_class, responsible_technician, responsible_work_order = (
        compute_fault_defect_rate(
            product_id=product_id,
            machine_id=machine_id,
            entities=entities,
            machine_state=machine_state,
            condition=condition,
        )
    )

    remaining_quantity = max(0, quantity - natural_rejected)
    fault_rejected = int(rng.binomial(remaining_quantity, fault_rate))
    total_rejected = min(quantity, natural_rejected + fault_rejected)
    rejected_pct = total_rejected / quantity if quantity else 0.0

    threshold = get_product_threshold(product_id, entities)
    natural_pct = natural_rejected / quantity if quantity else 0.0

    inspection_result = "REJECTED" if rejected_pct >= threshold else "ACCEPTED"
    fault_caused_rejection = (
        natural_pct < threshold
        and rejected_pct >= threshold
        and fault_rejected > 0
        and responsible_technician is not None
    )

    defect_code = choose_defect_code(
        rng=rng,
        entities=entities,
        fault_class=fault_class,
        fault_rejected=fault_rejected,
    )

    delay = int(
        rng.integers(
            CONFIG["inspection_delay_min"],
            CONFIG["inspection_delay_max"] + 1,
        )
    )
    inspection_day = min(CONFIG["n_days"], day + delay)

    public_batch = {
        "production_day": day,
        "batch_id": batch_id,
        "job_id": job["job_id"],
        "machine_id": machine_id,
        "product_id": product_id,
        "produced_quantity": quantity,
    }

    pending_inspection = {
        "inspection_day": inspection_day,
        "batch_id": batch_id,
        "product_id": product_id,
        "machine_id": machine_id,
        "inspected_quantity": quantity,
        "rejected_quantity": total_rejected,
        "rejected_pct": round_float(rejected_pct, 5),
        "defect_code": defect_code,
        "inspection_result": inspection_result,
        "production_day": day,
        "natural_rejected_quantity": natural_rejected,
        "fault_rejected_quantity": fault_rejected,
        "total_rejected_quantity": total_rejected,
        "fault_caused_rejection": fault_caused_rejection,
        "responsible_technician_id": responsible_technician,
        "responsible_work_order_id": responsible_work_order,
        "fault_class": fault_class,
    }

    simulation_events.append(
        {
            "day": day,
            "event_type": "production",
            "batch_id": batch_id,
            "job_id": job["job_id"],
            "machine_id": machine_id,
            "product_id": product_id,
            "active_fault_class": fault_class,
            "fault_rejected_quantity": fault_rejected,
            "natural_rejected_quantity": natural_rejected,
        }
    )

    return public_batch, pending_inspection


def compute_natural_defect_rate(
    product_id: str,
    machine_id: str,
    operator_id: str,
    job: dict[str, Any],
    entities: dict[str, Any],
    condition: dict[str, Any],
) -> float:
    product_base = entities["products_hidden"][product_id]["base_defect_rate"]
    machine_type_effect = entities["machines_hidden"][machine_id]["base_effect"]
    operator_effect = entities["operators_hidden"][operator_id]["quality_modifier"]

    difficulty_effect = 0.0026 * (int(job["job_difficulty"]) - 1)
    load_effect = max(0.0, float(condition["load_index"]) - 1.0) * 0.018
    humidity_effect = abs(float(condition["humidity_index"]) - 1.0) * 0.008
    material_effect = max(0.0, float(condition["material_variation_index"]) - 1.0) * 0.024
    power_effect = max(0.0, 1.0 - float(condition["power_stability_index"])) * 0.016

    rate = (
        product_base
        + machine_type_effect
        + operator_effect
        + difficulty_effect
        + load_effect
        + humidity_effect
        + material_effect
        + power_effect
    )
    return float(np.clip(rate, 0.0005, 0.080))


def compute_fault_defect_rate(
    product_id: str,
    machine_id: str,
    entities: dict[str, Any],
    machine_state: dict[str, dict[str, Any]],
    condition: dict[str, Any],
) -> tuple[float, str | None, str | None, str | None]:
    state = machine_state[machine_id]
    fault_class = state["active_fault_class"]

    if fault_class is None:
        return 0.0, None, None, None

    fault_data = entities["fault_classes_hidden"][fault_class]
    if product_id not in fault_data["affected_products"]:
        return 0.0, fault_class, None, None

    base_effect = fault_data["product_effects"][product_id]
    severity = float(state["fault_severity"])
    load_multiplier = 1.0 + max(0.0, float(condition["load_index"]) - 1.0) * 0.35
    rate = base_effect * severity * load_multiplier

    return (
        float(np.clip(rate, 0.0, 0.42)),
        fault_class,
        state["fault_origin_technician_id"],
        state["fault_origin_work_order_id"],
    )


def choose_defect_code(
    rng: np.random.Generator,
    entities: dict[str, Any],
    fault_class: str | None,
    fault_rejected: int,
) -> str:
    if fault_class is not None and fault_rejected > 0:
        fault_data = entities["fault_classes_hidden"][fault_class]
        codes = (
            fault_data["primary_defect_codes"]
            + fault_data["secondary_defect_codes"]
            + entities["defect_codes"]
        )
        weights = (
            [0.28, 0.22]
            + [0.09, 0.08, 0.06]
            + [0.27 / len(entities["defect_codes"])] * len(entities["defect_codes"])
        )
        weights_array = np.array(weights, dtype=float)
        weights_array = weights_array / weights_array.sum()
        return str(rng.choice(np.array(codes), p=weights_array))

    return str(rng.choice(entities["defect_codes"]))


def get_product_threshold(product_id: str, entities: dict[str, Any]) -> float:
    for product in entities["products_public"]:
        if product["product_id"] == product_id:
            return float(product["quality_rejection_threshold_pct"])
    raise ValueError(f"Unknown product_id: {product_id}")


def inspect_batch(
    pending_inspection: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    public_row = {
        "inspection_day": pending_inspection["inspection_day"],
        "batch_id": pending_inspection["batch_id"],
        "product_id": pending_inspection["product_id"],
        "inspected_quantity": pending_inspection["inspected_quantity"],
        "rejected_quantity": pending_inspection["rejected_quantity"],
        "rejected_pct": pending_inspection["rejected_pct"],
        "defect_code": pending_inspection["defect_code"],
        "inspection_result": pending_inspection["inspection_result"],
    }

    truth_row = {
        "batch_id": pending_inspection["batch_id"],
        "product_id": pending_inspection["product_id"],
        "machine_id": pending_inspection["machine_id"],
        "production_day": pending_inspection["production_day"],
        "inspection_day": pending_inspection["inspection_day"],
        "inspection_result": pending_inspection["inspection_result"],
        "natural_rejected_quantity": pending_inspection["natural_rejected_quantity"],
        "fault_rejected_quantity": pending_inspection["fault_rejected_quantity"],
        "total_rejected_quantity": pending_inspection["total_rejected_quantity"],
        "fault_caused_rejection": pending_inspection["fault_caused_rejection"],
        "responsible_technician_id": pending_inspection["responsible_technician_id"],
        "responsible_work_order_id": pending_inspection["responsible_work_order_id"],
        "fault_class": pending_inspection["fault_class"],
    }

    return public_row, truth_row


def decay_priority_scores(scores: dict[str, float], multiplier: float) -> None:
    for key in list(scores.keys()):
        scores[key] = round_float(scores[key] * multiplier, 5)
        if scores[key] < 0.05:
            scores[key] = 0.0


def close_open_fault_intervals(
    hidden_fault_intervals: list[dict[str, Any]],
    machine_state: dict[str, dict[str, Any]],
) -> None:
    for state in machine_state.values():
        if state["active_fault_class"] is not None:
            close_fault_interval(
                hidden_fault_intervals=hidden_fault_intervals,
                interval_id=state["fault_interval_id"],
                removed_day=CONFIG["n_days"] + 1,
                removed_by_work_order_id="NOT_REMOVED_DURING_SIMULATION",
            )


def build_for_llm_frames(
    entities: dict[str, Any],
    simulation: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    frames = {
        "products": pd.DataFrame(entities["products_public"]),
        "machines": pd.DataFrame(entities["machines_public"]),
        "technicians": pd.DataFrame(entities["technicians_public"]),
        "operators": pd.DataFrame(entities["operators_public"]),
        "maintenance_work_orders": pd.DataFrame(simulation["maintenance_index_rows"]),
        "production_jobs": pd.DataFrame(simulation["production_job_rows"]),
        "machine_assignment_log": pd.DataFrame(simulation["assignment_rows"]),
        "production_batches": pd.DataFrame(simulation["batch_rows"]),
        "quality_inspections": pd.DataFrame(simulation["inspection_rows"]),
        "operator_shift_log": pd.DataFrame(simulation["operator_shift_rows"]),
        "daily_factory_conditions": pd.DataFrame(simulation["daily_condition_rows"]),
    }
    return {name: normalize_frame(frame) for name, frame in frames.items()}


def build_additional_frames(
    entities: dict[str, Any],
    simulation: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    frames = {
        "full_maintenance_work_orders": pd.DataFrame(
            simulation["full_maintenance_rows"]
        ),
        "hidden_fault_intervals": pd.DataFrame(simulation["hidden_fault_intervals"]),
        "fault_product_map": pd.DataFrame(entities["fault_product_rows"]),
        "batch_truth": pd.DataFrame(simulation["batch_truth_rows"]),
    }
    return {name: normalize_frame(frame) for name, frame in frames.items()}


def get_fault_caused_evidence(batch_truth: pd.DataFrame) -> pd.DataFrame:
    if batch_truth.empty:
        return batch_truth.copy()

    return batch_truth[
        batch_truth["fault_caused_rejection"].astype(bool)
        & batch_truth["responsible_technician_id"].notna()
        & batch_truth["responsible_work_order_id"].notna()
    ].copy()


def build_confirmed_technicians(batch_truth: pd.DataFrame) -> set[str]:
    evidence = get_fault_caused_evidence(batch_truth)
    if evidence.empty:
        return set()

    technician_summary = (
        evidence.groupby("responsible_technician_id", dropna=True)
        .agg(
            fault_caused_rejections=("batch_id", "count"),
            distinct_fault_work_orders=("responsible_work_order_id", "nunique"),
        )
        .reset_index()
    )

    confirmed = technician_summary[
        (
            technician_summary["fault_caused_rejections"]
            >= CONFIG["confirmed_technician_min_fault_caused_rejections"]
        )
        & (
            technician_summary["distinct_fault_work_orders"]
            >= CONFIG["confirmed_technician_min_distinct_fault_work_orders"]
        )
    ]

    return set(confirmed["responsible_technician_id"].astype(str))


def build_answer(batch_truth: pd.DataFrame) -> dict[str, list[str]]:
    answer: dict[str, list[str]] = {}

    evidence = get_fault_caused_evidence(batch_truth)
    if evidence.empty:
        return answer

    confirmed_technicians = build_confirmed_technicians(batch_truth)
    if not confirmed_technicians:
        return answer

    confirmed_evidence = evidence[
        evidence["responsible_technician_id"].astype(str).isin(confirmed_technicians)
    ]

    grouped = confirmed_evidence.groupby("product_id")["responsible_technician_id"].apply(
        lambda values: sorted(set(str(value) for value in values))
    )

    for product_id, technicians in grouped.items():
        if technicians:
            answer[str(product_id)] = sorted(technicians)

    return dict(sorted(answer.items()))


def write_public_outputs(
    output_dir: Path,
    frames: dict[str, pd.DataFrame],
    raw_reports: list[dict[str, str]],
) -> None:
    file_map = {
        "products": "products.csv",
        "machines": "machines.csv",
        "technicians": "technicians.csv",
        "operators": "operators.csv",
        "maintenance_work_orders": "maintenance_work_orders.csv",
        "production_jobs": "production_jobs.csv",
        "machine_assignment_log": "machine_assignment_log.csv",
        "production_batches": "production_batches.csv",
        "quality_inspections": "quality_inspections.csv",
        "operator_shift_log": "operator_shift_log.csv",
        "daily_factory_conditions": "daily_factory_conditions.csv",
    }

    for frame_name, file_name in file_map.items():
        write_csv(frames[frame_name], output_dir / file_name)

    raw_dir = output_dir / "raw_service_reports"
    for report in sorted(raw_reports, key=lambda item: item["relative_path"]):
        path = raw_dir / report["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report["content"], encoding="utf-8", newline="\n")


def write_answer(answer_path: Path | None, answer: dict[str, list[str]]) -> None:
    if answer_path is None:
        return

    answer_path.parent.mkdir(parents=True, exist_ok=True)
    answer_path.write_text(
        json.dumps(answer, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def write_additional_outputs(
    additional_dir: Path | None,
    entities: dict[str, Any],
    simulation: dict[str, Any],
    additional_frames: dict[str, pd.DataFrame],
    answer: dict[str, list[str]],
    quality_summary: dict[str, Any],
    effective_seed: int,
    write_debug_outputs: bool,
    write_seed_info: bool,
) -> None:
    if additional_dir is None:
        return

    (additional_dir / "answer.txt").write_text(
        json.dumps(answer, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    if write_seed_info:
        seed_info = {
            "seed": CONFIG["seed"],
            "effective_seed": effective_seed,
            "attempt": effective_seed - CONFIG["seed"],
        }
        (additional_dir / "seed_info.json").write_text(
            json.dumps(seed_info, indent=2, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )

    if not write_debug_outputs:
        return

    write_csv(
        additional_frames["full_maintenance_work_orders"],
        additional_dir / "full_maintenance_work_orders.csv",
    )
    write_csv(
        additional_frames["hidden_fault_intervals"],
        additional_dir / "hidden_fault_intervals.csv",
    )
    write_csv(
        additional_frames["fault_product_map"],
        additional_dir / "fault_product_map.csv",
    )
    write_csv(
        additional_frames["batch_truth"],
        additional_dir / "batch_truth.csv",
    )

    meta = build_simulation_meta(entities, effective_seed)
    (additional_dir / "simulation_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    event_lines = [
        json.dumps(event, sort_keys=True)
        for event in sorted(
            simulation["simulation_events"],
            key=lambda item: (
                item.get("day", 0),
                item.get("event_type", ""),
                item.get("batch_id", ""),
                item.get("work_order_id", ""),
                item.get("machine_id", ""),
            ),
        )
    ]
    (additional_dir / "simulation_events.jsonl").write_text(
        "\n".join(event_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    output_text = "\n".join(simulation["simulation_output_lines"]) + "\n"
    (additional_dir / "simulation_output.txt").write_text(
        output_text,
        encoding="utf-8",
        newline="\n",
    )

    evidence_md = build_evidence_markdown(additional_frames["batch_truth"], answer)
    (additional_dir / "technician_product_evidence.md").write_text(
        evidence_md,
        encoding="utf-8",
        newline="\n",
    )

    (additional_dir / "quality_summary.json").write_text(
        json.dumps(quality_summary, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def build_simulation_meta(
    entities: dict[str, Any],
    effective_seed: int,
) -> dict[str, Any]:
    return {
        "config": CONFIG,
        "effective_seed": effective_seed,
        "products_hidden": entities["products_hidden"],
        "machines_hidden": entities["machines_hidden"],
        "technicians_hidden": entities["technicians_hidden"],
        "operators_hidden": entities["operators_hidden"],
        "fault_classes_hidden": entities["fault_classes_hidden"],
        "product_machine_type": entities["product_machine_type"],
    }


def build_evidence_markdown(
    batch_truth: pd.DataFrame,
    answer: dict[str, list[str]],
) -> str:
    lines = ["# Technician Product Evidence", ""]

    if batch_truth.empty:
        lines.append("No batch truth records generated.")
        return "\n".join(lines) + "\n"

    evidence = get_fault_caused_evidence(batch_truth)

    if evidence.empty:
        lines.append("No fault-caused rejection evidence generated.")
        return "\n".join(lines) + "\n"

    evidence = evidence.sort_values(
        ["product_id", "responsible_technician_id", "production_day", "batch_id"],
        kind="mergesort",
    )

    confirmed_technicians = build_confirmed_technicians(batch_truth)

    lines.append("## Confirmed technicians")
    lines.append("")
    if confirmed_technicians:
        for technician_id in sorted(confirmed_technicians):
            subset = evidence[
                evidence["responsible_technician_id"].astype(str) == technician_id
            ]
            distinct_work_orders = subset["responsible_work_order_id"].nunique()
            lines.append(
                f"- {technician_id}: {len(subset)} fault-caused rejected batches, "
                f"{distinct_work_orders} distinct responsible work orders."
            )
    else:
        lines.append("No confirmed technicians.")
    lines.append("")

    for product_id in sorted(answer.keys()):
        lines.append(f"## {product_id}")
        technicians = answer[product_id]

        for technician_id in technicians:
            subset = evidence[
                (evidence["product_id"].astype(str) == product_id)
                & (evidence["responsible_technician_id"].astype(str) == technician_id)
            ]
            lines.append("")
            lines.append(f"### {technician_id}")
            for _, row in subset.head(12).iterrows():
                lines.append(
                    (
                        f"- {row['batch_id']} on {row['machine_id']}: "
                        f"produced day {int(row['production_day'])}, "
                        f"inspected day {int(row['inspection_day'])}, "
                        f"fault {row['fault_class']}, "
                        f"work order {row['responsible_work_order_id']}."
                    )
                )
            if len(subset) > 12:
                lines.append(f"- ... {len(subset) - 12} more evidence batches.")
            lines.append("")

    return "\n".join(lines) + "\n"


def build_quality_summary(
    batch_truth: pd.DataFrame,
    answer: dict[str, list[str]],
    full_maintenance: pd.DataFrame | None = None,
    technicians_hidden: dict[str, Any] | None = None,
) -> dict[str, Any]:
    empty_summary = {
        "n_batches": 0,
        "n_rejected_batches": 0,
        "n_fault_caused_rejections": 0,
        "n_fault_caused_rejections_by_confirmed_technicians": 0,
        "n_fault_caused_rejections_by_unconfirmed_technicians": 0,
        "n_natural_or_confounded_rejections": 0,
        "n_confirmed_technicians": 0,
        "min_fault_caused_rejections_per_confirmed_technician": 0,
        "median_fault_caused_rejections_per_confirmed_technician": 0.0,
        "mean_fault_caused_rejections_per_confirmed_technician": 0.0,
        "max_fault_caused_rejections_per_confirmed_technician": 0,
        "min_distinct_fault_work_orders_per_confirmed_technician": 0,
        "n_products_with_responsible_technicians": 0,
        "n_responsible_product_technician_pairs": 0,
        "min_evidence_batches_per_answer_pair": 0,
        "median_evidence_batches_per_answer_pair": 0.0,
        "mean_evidence_batches_per_answer_pair": 0.0,
        "max_evidence_batches_per_answer_pair": 0,
        "n_answer_pairs_with_single_evidence_batch": 0,
        "n_high_evidence_answer_pairs": 0,
        "high_evidence_threshold": int(CONFIG["quality_gate_high_evidence_threshold"]),
        "n_decoy_suspicious_technicians": 0,
        "n_confirmed_off_target_technicians": 0,
        "confirmed_technician_tier_counts": {
            tier: 0
            for tier in TECHNICIAN_TIER_ORDER + ["normal"]
        },
    }

    if batch_truth.empty:
        return empty_summary

    rejected = batch_truth[batch_truth["inspection_result"] == "REJECTED"]
    fault_caused = get_fault_caused_evidence(batch_truth)
    confirmed_technicians = build_confirmed_technicians(batch_truth)

    if confirmed_technicians:
        confirmed_fault_caused = fault_caused[
            fault_caused["responsible_technician_id"].astype(str).isin(
                confirmed_technicians
            )
        ]
    else:
        confirmed_fault_caused = fault_caused.iloc[0:0].copy()

    technician_counts = []
    technician_work_order_counts = []
    if not confirmed_fault_caused.empty:
        technician_grouped = confirmed_fault_caused.groupby(
            "responsible_technician_id",
            dropna=True,
        ).agg(
            fault_caused_rejections=("batch_id", "count"),
            distinct_fault_work_orders=("responsible_work_order_id", "nunique"),
        )

        technician_counts = [
            int(value) for value in technician_grouped["fault_caused_rejections"].values
        ]
        technician_work_order_counts = [
            int(value) for value in technician_grouped["distinct_fault_work_orders"].values
        ]

    evidence_counts = []
    if not confirmed_fault_caused.empty:
        answer_pair_grouped = confirmed_fault_caused.groupby(
            ["product_id", "responsible_technician_id"],
            dropna=True,
        ).size()
        evidence_counts = [int(value) for value in answer_pair_grouped.values]

    high_evidence_threshold = int(CONFIG["quality_gate_high_evidence_threshold"])
    if evidence_counts:
        min_evidence = min(evidence_counts)
        median_evidence = float(np.median(evidence_counts))
        mean_evidence = float(np.mean(evidence_counts))
        max_evidence = max(evidence_counts)
        single_evidence = sum(1 for value in evidence_counts if value == 1)
        high_evidence = sum(
            1 for value in evidence_counts if value >= high_evidence_threshold
        )
    else:
        min_evidence = 0
        median_evidence = 0.0
        mean_evidence = 0.0
        max_evidence = 0
        single_evidence = 0
        high_evidence = 0

    if technician_counts:
        min_technician_evidence = min(technician_counts)
        median_technician_evidence = float(np.median(technician_counts))
        mean_technician_evidence = float(np.mean(technician_counts))
        max_technician_evidence = max(technician_counts)
    else:
        min_technician_evidence = 0
        median_technician_evidence = 0.0
        mean_technician_evidence = 0.0
        max_technician_evidence = 0

    return {
        "n_batches": int(len(batch_truth)),
        "n_rejected_batches": int(len(rejected)),
        "n_fault_caused_rejections": int(len(fault_caused)),
        "n_fault_caused_rejections_by_confirmed_technicians": int(
            len(confirmed_fault_caused)
        ),
        "n_fault_caused_rejections_by_unconfirmed_technicians": int(
            len(fault_caused) - len(confirmed_fault_caused)
        ),
        "n_natural_or_confounded_rejections": int(len(rejected) - len(fault_caused)),
        "n_confirmed_technicians": int(len(confirmed_technicians)),
        "min_fault_caused_rejections_per_confirmed_technician": int(
            min_technician_evidence
        ),
        "median_fault_caused_rejections_per_confirmed_technician": round_float(
            median_technician_evidence, 5
        ),
        "mean_fault_caused_rejections_per_confirmed_technician": round_float(
            mean_technician_evidence, 5
        ),
        "max_fault_caused_rejections_per_confirmed_technician": int(
            max_technician_evidence
        ),
        "min_distinct_fault_work_orders_per_confirmed_technician": int(
            min(technician_work_order_counts) if technician_work_order_counts else 0
        ),
        "n_products_with_responsible_technicians": int(len(answer)),
        "n_responsible_product_technician_pairs": int(
            sum(len(technicians) for technicians in answer.values())
        ),
        "min_evidence_batches_per_answer_pair": int(min_evidence),
        "median_evidence_batches_per_answer_pair": round_float(median_evidence, 5),
        "mean_evidence_batches_per_answer_pair": round_float(mean_evidence, 5),
        "max_evidence_batches_per_answer_pair": int(max_evidence),
        "n_answer_pairs_with_single_evidence_batch": int(single_evidence),
        "n_high_evidence_answer_pairs": int(high_evidence),
        "high_evidence_threshold": int(high_evidence_threshold),
        "n_decoy_suspicious_technicians": count_decoy_suspicious_technicians(
            batch_truth=batch_truth,
            full_maintenance=full_maintenance,
            confirmed_technicians=confirmed_technicians,
        ),
        "n_confirmed_off_target_technicians": count_confirmed_off_target_technicians(
            confirmed_technicians=confirmed_technicians,
            technicians_hidden=technicians_hidden,
        ),
        "confirmed_technician_tier_counts": count_confirmed_by_tier(
            confirmed_technicians=confirmed_technicians,
            technicians_hidden=technicians_hidden,
        ),
    }


def count_confirmed_off_target_technicians(
    confirmed_technicians: set[str],
    technicians_hidden: dict[str, Any] | None,
) -> int:
    if technicians_hidden is None:
        return 0
    off_target_tiers = {"normal", "decoy"}
    count = 0
    for technician_id in confirmed_technicians:
        tier = technicians_hidden.get(technician_id, {}).get("tier")
        if tier in off_target_tiers:
            count += 1
    return count


def count_confirmed_by_tier(
    confirmed_technicians: set[str],
    technicians_hidden: dict[str, Any] | None,
) -> dict[str, int]:
    tier_counts: dict[str, int] = {
        tier: 0 for tier in TECHNICIAN_TIER_ORDER + ["normal"]
    }
    if technicians_hidden is None:
        return tier_counts
    for technician_id in confirmed_technicians:
        tier = technicians_hidden.get(technician_id, {}).get("tier")
        if tier in tier_counts:
            tier_counts[tier] += 1
    return tier_counts


def count_decoy_suspicious_technicians(
    batch_truth: pd.DataFrame,
    full_maintenance: pd.DataFrame | None,
    confirmed_technicians: set[str],
) -> int:
    if full_maintenance is None or full_maintenance.empty or batch_truth.empty:
        return 0

    rejected = batch_truth[batch_truth["inspection_result"] == "REJECTED"].copy()
    if rejected.empty:
        return 0

    maintenance = full_maintenance[
        ["day", "machine_id", "technician_id", "work_order_id"]
    ].copy()
    maintenance["day"] = maintenance["day"].astype(int)

    rejected = rejected[["batch_id", "machine_id", "production_day"]].copy()
    rejected["production_day"] = rejected["production_day"].astype(int)

    per_tech_counts: dict[str, set[str]] = {}

    for machine_id, machine_rejected in rejected.groupby("machine_id"):
        machine_maint = maintenance[maintenance["machine_id"] == machine_id]
        if machine_maint.empty:
            continue
        machine_maint_sorted = machine_maint.sort_values("day").reset_index(drop=True)
        days = machine_maint_sorted["day"].to_numpy()
        techs = machine_maint_sorted["technician_id"].to_numpy()

        for _, batch_row in machine_rejected.iterrows():
            production_day = int(batch_row["production_day"])
            idx = int(np.searchsorted(days, production_day, side="right")) - 1
            if idx < 0:
                continue
            attributed_tech = str(techs[idx])
            per_tech_counts.setdefault(attributed_tech, set()).add(
                str(batch_row["batch_id"])
            )

    threshold = int(CONFIG["decoy_suspicious_min_post_maintenance_rejections"])
    n_suspicious = 0
    for tech_id, batch_ids in per_tech_counts.items():
        if tech_id in confirmed_technicians:
            continue
        if len(batch_ids) >= threshold:
            n_suspicious += 1

    return n_suspicious


def quality_gate_passes(summary: dict[str, Any]) -> bool:
    return (
        summary["n_fault_caused_rejections"]
        >= CONFIG["quality_gate_min_fault_caused_rejections"]
        and summary["n_fault_caused_rejections_by_confirmed_technicians"]
        >= int(CONFIG["quality_gate_min_fault_caused_rejections"] * 0.55)
        and summary["n_natural_or_confounded_rejections"]
        >= CONFIG["quality_gate_min_natural_rejections"]
        and CONFIG["quality_gate_min_confirmed_technicians"]
        <= summary["n_confirmed_technicians"]
        <= CONFIG["quality_gate_max_confirmed_technicians"]
        and summary["min_fault_caused_rejections_per_confirmed_technician"]
        >= CONFIG["confirmed_technician_min_fault_caused_rejections"]
        and summary["min_distinct_fault_work_orders_per_confirmed_technician"]
        >= CONFIG["confirmed_technician_min_distinct_fault_work_orders"]
        and CONFIG["quality_gate_min_products_with_responsible"]
        <= summary["n_products_with_responsible_technicians"]
        <= CONFIG["quality_gate_max_products_with_responsible"]
        and summary["n_responsible_product_technician_pairs"]
        >= CONFIG["quality_gate_min_responsible_pairs"]
        and summary["n_answer_pairs_with_single_evidence_batch"]
        >= CONFIG["quality_gate_min_single_evidence_pairs"]
        and summary["n_high_evidence_answer_pairs"]
        >= CONFIG["quality_gate_min_high_evidence_pairs"]
        and summary.get("n_decoy_suspicious_technicians", 0)
        >= CONFIG["quality_gate_min_decoy_suspicious_technicians"]
        and summary.get("n_confirmed_off_target_technicians", 0)
        <= CONFIG["quality_gate_max_off_target_confirmed_technicians"]
    )


def validate_outputs(
    output_dir: Path,
    answer_path: Path | None,
    additional_dir: Path | None,
    write_debug_outputs: bool,
    write_seed_info: bool,
    for_llm_frames: dict[str, pd.DataFrame],
    additional_frames: dict[str, pd.DataFrame],
    answer: dict[str, list[str]],
    quality_summary: dict[str, Any],
) -> None:
    required_public = [
        "products.csv",
        "machines.csv",
        "technicians.csv",
        "operators.csv",
        "maintenance_work_orders.csv",
        "production_jobs.csv",
        "machine_assignment_log.csv",
        "production_batches.csv",
        "quality_inspections.csv",
        "operator_shift_log.csv",
        "daily_factory_conditions.csv",
    ]

    for file_name in required_public:
        if not (output_dir / file_name).exists():
            raise FileNotFoundError(f"Missing public output: {file_name}")

    raw_reports_dir = output_dir / "raw_service_reports"
    if not raw_reports_dir.exists():
        raise FileNotFoundError("Missing public output directory: raw_service_reports")

    if answer_path is not None and not answer_path.exists():
        raise FileNotFoundError(f"Missing answer output: {answer_path}")

    if additional_dir is not None:
        required_additional = ["answer.txt"]
        if write_seed_info:
            required_additional.append("seed_info.json")
        if write_debug_outputs:
            required_additional.extend(
                [
                    "simulation_meta.json",
                    "simulation_events.jsonl",
                    "simulation_output.txt",
                    "full_maintenance_work_orders.csv",
                    "hidden_fault_intervals.csv",
                    "fault_product_map.csv",
                    "batch_truth.csv",
                    "technician_product_evidence.md",
                    "quality_summary.json",
                ]
            )

        for file_name in required_additional:
            if not (additional_dir / file_name).exists():
                raise FileNotFoundError(f"Missing additional output: {file_name}")

    validate_public_columns(for_llm_frames)
    validate_relational_integrity(for_llm_frames, additional_frames)
    validate_answer_consistency(for_llm_frames, additional_frames, answer)
    validate_schedule_time_windows(for_llm_frames, additional_frames)

    if not quality_gate_passes(quality_summary):
        raise ValueError(
            "Generated dataset does not satisfy quality gates: "
            f"{json.dumps(quality_summary, sort_keys=True)}"
        )


def validate_public_columns(for_llm_frames: dict[str, pd.DataFrame]) -> None:
    hidden_column_fragments = [
        "fault_class",
        "active_fault",
        "responsible_technician",
        "fault_caused",
        "natural_rejected",
        "fault_rejected",
    ]

    for frame_name, frame in for_llm_frames.items():
        for column in frame.columns:
            lowered = column.lower()
            if any(fragment in lowered for fragment in hidden_column_fragments):
                raise ValueError(
                    f"Hidden column '{column}' found in public frame '{frame_name}'"
                )

    public_maintenance_columns = set(for_llm_frames["maintenance_work_orders"].columns)
    forbidden_maintenance_columns = {
        "machine_id",
        "technician_id",
        "maintenance_type",
        "reported_reason",
        "started_at",
        "completed_at",
    }
    leaked = public_maintenance_columns.intersection(forbidden_maintenance_columns)
    if leaked:
        raise ValueError(
            "maintenance_work_orders.csv leaks service details: "
            f"{sorted(leaked)}"
        )


def validate_relational_integrity(
    for_llm_frames: dict[str, pd.DataFrame],
    additional_frames: dict[str, pd.DataFrame],
) -> None:
    machines = for_llm_frames["machines"]
    jobs = for_llm_frames["production_jobs"]
    assignments = for_llm_frames["machine_assignment_log"]
    batches = for_llm_frames["production_batches"]
    inspections = for_llm_frames["quality_inspections"]
    batch_truth = additional_frames["batch_truth"]
    full_maintenance = additional_frames["full_maintenance_work_orders"]
    hidden_intervals = additional_frames["hidden_fault_intervals"]

    require_unique(batches, "batch_id", "production_batches")
    require_unique(inspections, "batch_id", "quality_inspections")
    require_unique(batch_truth, "batch_id", "batch_truth")
    require_unique(jobs, "job_id", "production_jobs")
    require_unique(assignments, "job_id", "machine_assignment_log")
    require_unique(full_maintenance, "work_order_id", "full_maintenance_work_orders")

    batch_ids = set(batches["batch_id"].astype(str))
    inspection_ids = set(inspections["batch_id"].astype(str))
    truth_ids = set(batch_truth["batch_id"].astype(str))

    if batch_ids != inspection_ids:
        missing = sorted(batch_ids - inspection_ids)[:5]
        extra = sorted(inspection_ids - batch_ids)[:5]
        raise ValueError(
            "quality_inspections batch IDs do not match production_batches. "
            f"Missing sample: {missing}; extra sample: {extra}"
        )

    if batch_ids != truth_ids:
        missing = sorted(batch_ids - truth_ids)[:5]
        extra = sorted(truth_ids - batch_ids)[:5]
        raise ValueError(
            "batch_truth batch IDs do not match production_batches. "
            f"Missing sample: {missing}; extra sample: {extra}"
        )

    if len(batch_truth) != len(batches):
        raise ValueError(
            f"batch_truth row count {len(batch_truth)} does not match "
            f"production_batches row count {len(batches)}."
        )

    truth_with_batch = batch_truth.merge(
        batches[
            [
                "batch_id",
                "production_day",
                "job_id",
                "machine_id",
                "product_id",
                "produced_quantity",
            ]
        ],
        on="batch_id",
        how="left",
        suffixes=("_truth", "_batch"),
    )

    if truth_with_batch["job_id"].isna().any():
        raise ValueError("Some batch_truth rows do not match production_batches.")

    mismatch = truth_with_batch[
        (
            truth_with_batch["production_day_truth"]
            != truth_with_batch["production_day_batch"]
        )
        | (
            truth_with_batch["machine_id_truth"].astype(str)
            != truth_with_batch["machine_id_batch"].astype(str)
        )
        | (
            truth_with_batch["product_id_truth"].astype(str)
            != truth_with_batch["product_id_batch"].astype(str)
        )
    ]
    if not mismatch.empty:
        raise ValueError(
            f"batch_truth is inconsistent with production_batches: "
            f"{mismatch.iloc[0].to_dict()}"
        )

    invalid_inspection_dates = batch_truth[
        batch_truth["inspection_day"].astype(int)
        < batch_truth["production_day"].astype(int)
    ]
    if not invalid_inspection_dates.empty:
        raise ValueError(
            f"Inspection before production: {invalid_inspection_dates.iloc[0].to_dict()}"
        )

    job_ids = set(jobs["job_id"].astype(str))
    assignment_job_ids = set(assignments["job_id"].astype(str))
    batch_job_ids = set(batches["job_id"].astype(str))

    if job_ids != assignment_job_ids:
        raise ValueError("production_jobs and machine_assignment_log job IDs differ.")
    if job_ids != batch_job_ids:
        raise ValueError("production_jobs and production_batches job IDs differ.")

    machine_type = dict(
        zip(machines["machine_id"].astype(str), machines["machine_type"].astype(str))
    )

    jobs_with_assignment = jobs.merge(assignments, on=["day", "job_id"], how="inner")
    for _, row in jobs_with_assignment.iterrows():
        if str(row["required_machine_type"]) != machine_type[str(row["machine_id"])]:
            raise ValueError(
                f"Job assigned to incompatible machine type: {row.to_dict()}"
            )

    if not hidden_intervals.empty:
        invalid_intervals = hidden_intervals[
            hidden_intervals["removed_day"].astype(int)
            <= hidden_intervals["introduced_day"].astype(int)
        ]
        if not invalid_intervals.empty:
            raise ValueError(
                f"Invalid hidden fault interval: {invalid_intervals.iloc[0].to_dict()}"
            )


def require_unique(frame: pd.DataFrame, column: str, frame_name: str) -> None:
    if frame[column].duplicated().any():
        duplicate = frame[frame[column].duplicated()][column].iloc[0]
        raise ValueError(f"{frame_name}.{column} contains duplicate value: {duplicate}")


def validate_answer_consistency(
    for_llm_frames: dict[str, pd.DataFrame],
    additional_frames: dict[str, pd.DataFrame],
    answer: dict[str, list[str]],
) -> None:
    all_technicians = set(for_llm_frames["technicians"]["technician_id"].astype(str))
    all_products = set(for_llm_frames["products"]["product_id"].astype(str))

    unknown_products = set(answer.keys()) - all_products
    if unknown_products:
        raise ValueError(
            f"Answer contains unknown product IDs: {sorted(unknown_products)}"
        )

    for product_id, technicians in answer.items():
        if not technicians:
            raise ValueError(
                f"Answer contains product with no responsible technicians: {product_id}"
            )
        if technicians != sorted(technicians):
            raise ValueError(f"Technicians for {product_id} are not sorted.")
        for technician_id in technicians:
            if technician_id not in all_technicians:
                raise ValueError(f"Unknown technician in answer: {technician_id}")

    batch_truth = additional_frames["batch_truth"]
    if batch_truth.empty:
        raise ValueError("batch_truth is empty.")

    rejected = batch_truth[batch_truth["inspection_result"] == "REJECTED"]
    fault_caused = get_fault_caused_evidence(batch_truth)
    confirmed_technicians = build_confirmed_technicians(batch_truth)

    if rejected.empty:
        raise ValueError("No rejected batches generated.")
    if fault_caused.empty:
        raise ValueError("No fault-caused rejections generated.")
    if len(rejected) == len(fault_caused):
        raise ValueError("All rejections are fault-caused; add natural rejections.")

    for product_id, technicians in answer.items():
        for technician_id in technicians:
            if technician_id not in confirmed_technicians:
                raise ValueError(
                    f"Answer contains technician that is not confirmed: {technician_id}"
                )

            subset = fault_caused[
                (fault_caused["product_id"].astype(str) == product_id)
                & (
                    fault_caused["responsible_technician_id"].astype(str)
                    == technician_id
                )
            ]
            if subset.empty:
                raise ValueError(
                    f"Answer pair has no supporting truth row: "
                    f"{product_id}, {technician_id}"
                )


def validate_schedule_time_windows(
    for_llm_frames: dict[str, pd.DataFrame],
    additional_frames: dict[str, pd.DataFrame],
) -> None:
    assignments = for_llm_frames["machine_assignment_log"].copy()
    maintenance = additional_frames["full_maintenance_work_orders"].copy()

    if assignments.empty or maintenance.empty:
        return

    assignments["start_minute"] = assignments["start_time"].map(parse_time_to_minutes)
    assignments["end_minute"] = assignments["end_time"].map(parse_time_to_minutes)
    maintenance["started_minute"] = maintenance["started_at"].map(parse_time_to_minutes)
    maintenance["completed_minute"] = maintenance["completed_at"].map(
        parse_time_to_minutes
    )

    invalid_production_times = assignments[
        assignments["end_minute"] <= assignments["start_minute"]
    ]
    if not invalid_production_times.empty:
        raise ValueError(
            f"Invalid production time interval: {invalid_production_times.iloc[0].to_dict()}"
        )

    invalid_maintenance_times = maintenance[
        maintenance["completed_minute"] <= maintenance["started_minute"]
    ]
    if not invalid_maintenance_times.empty:
        raise ValueError(
            f"Invalid maintenance time interval: {invalid_maintenance_times.iloc[0].to_dict()}"
        )

    too_early_production = assignments[
        assignments["start_minute"] < CONFIG["production_window_start_minute"]
    ]
    if not too_early_production.empty:
        sample = too_early_production.iloc[0].to_dict()
        raise ValueError(f"Production starts before production window: {sample}")

    too_late_production = assignments[
        assignments["end_minute"] > CONFIG["production_window_end_minute"]
    ]
    if not too_late_production.empty:
        sample = too_late_production.iloc[0].to_dict()
        raise ValueError(f"Production ends after production window: {sample}")

    late_maintenance = maintenance[
        maintenance["completed_minute"] > CONFIG["maintenance_window_end_minute"]
    ]
    if not late_maintenance.empty:
        sample = late_maintenance.iloc[0].to_dict()
        raise ValueError(f"Maintenance ends after maintenance window: {sample}")

    same_machine_day = assignments.merge(
        maintenance,
        on=["day", "machine_id"],
        how="inner",
        suffixes=("_production", "_maintenance"),
    )
    overlaps = same_machine_day[
        (same_machine_day["start_minute"] < same_machine_day["completed_minute"])
        & (same_machine_day["end_minute"] > same_machine_day["started_minute"])
    ]
    if not overlaps.empty:
        sample = overlaps.iloc[0].to_dict()
        raise ValueError(f"Maintenance overlaps production: {sample}")

    validate_no_interval_overlap(
        frame=assignments,
        group_columns=["day", "machine_id"],
        start_column="start_minute",
        end_column="end_minute",
        label="production on same machine",
    )
    validate_no_interval_overlap(
        frame=maintenance,
        group_columns=["day", "machine_id"],
        start_column="started_minute",
        end_column="completed_minute",
        label="maintenance on same machine",
    )
    validate_no_interval_overlap(
        frame=maintenance,
        group_columns=["day", "technician_id"],
        start_column="started_minute",
        end_column="completed_minute",
        label="maintenance by same technician",
    )


def validate_no_interval_overlap(
    frame: pd.DataFrame,
    group_columns: list[str],
    start_column: str,
    end_column: str,
    label: str,
) -> None:
    for _, group in frame.sort_values(group_columns + [start_column]).groupby(
        group_columns, dropna=False
    ):
        previous_end = None
        previous_row = None

        for _, row in group.iterrows():
            current_start = int(row[start_column])
            current_end = int(row[end_column])

            if previous_end is not None and current_start < previous_end:
                raise ValueError(
                    f"Overlapping {label}: previous={previous_row.to_dict()}, "
                    f"current={row.to_dict()}"
                )

            previous_end = current_end
            previous_row = row


def parse_time_to_minutes(value: str) -> int:
    hour_text, minute_text = str(value).split(":")
    return int(hour_text) * 60 + int(minute_text)


def minutes_to_time(value: int) -> str:
    hour = value // 60
    minute = value % 60
    return f"{hour:02d}:{minute:02d}"


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    frame = frame.copy()

    for column in frame.columns:
        if pd.api.types.is_float_dtype(frame[column]):
            frame[column] = frame[column].round(5)

    sort_columns = [column for column in frame.columns if column.endswith("_id")]
    if "day" in frame.columns:
        sort_columns = ["day"] + sort_columns
    elif "production_day" in frame.columns:
        sort_columns = ["production_day"] + sort_columns
    elif "inspection_day" in frame.columns:
        sort_columns = ["inspection_day"] + sort_columns

    sort_columns = list(dict.fromkeys(sort_columns))

    if sort_columns:
        frame = frame.sort_values(sort_columns, kind="mergesort")

    return frame.reset_index(drop=True)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def make_ids(prefix: str, count: int, width: int) -> list[str]:
    return [f"{prefix}_{idx:0{width}d}" for idx in range(1, count + 1)]


def round_float(value: float, digits: int = 5) -> float:
    return float(np.round(value, digits))


if __name__ == "__main__":
    main()
