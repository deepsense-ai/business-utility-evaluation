import argparse
from pathlib import Path

import numpy as np
import pandas as pd

OPENCODE_ALLOWED_MODELS = ["deepseek-reasoner"]


def load_results() -> pd.DataFrame:
    TASK_DIR = Path("../tasks")

    task_names: list[str] = [p.name for p in TASK_DIR.iterdir() if p.is_dir()]

    dfs: list[pd.DataFrame] = []
    for task_name in task_names:
        df: pd.DataFrame = pd.read_csv(TASK_DIR / task_name / "results.csv")
        df["task"] = task_name
        dfs.append(df)
        print(f"Found task: {task_name}")
    return pd.concat(dfs, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a CVS file with business utility metric per model.")
    parser.add_argument("-o", "--output", default="model_results.csv",
                        help="Output CSV path (default: model_results.csv)")
    parser.add_argument("-n", "--runs", type=int, default=5,
                        help="Expected number of runs per model + agent + task combination")
    args = parser.parse_args()

    results = load_results()

    # remove model name prefix
    results["model_name"] = results["model_name"].str.split("/").str[-1]

    # exclude opencode results, except for allowed models
    results: pd.DataFrame = results[
        (results.agent_name != "opencode") | (results.model_name.isin(OPENCODE_ALLOWED_MODELS))
        ].fillna(0)


    def agg_metrics(g: pd.DataFrame) -> pd.Series:
        ms: float = g["reward"].mean()
        cv: float = g["reward"].std() / ms if ms != 0 else np.nan
        return pd.Series({
            "n": len(g),
            "ms": ms,
            "cv": cv,
            "business_utility": ms * np.exp(-2.25 * cv ** 0.88),
            "mean_duration_sec": g["duration_sec"].mean(),
            "mean_cost_usd": g["cost_usd"].mean(),
        })

    results_grouped: pd.DataFrame = (
        results
        .groupby(["model_name", "agent_name", "reasoning_effort", "task"])
        .apply(agg_metrics, include_groups=False)
        .reset_index()
    )
    if results_grouped["n"].nunique() != 1 or results_grouped["n"].iloc[0] != args.runs:
        expected_n = args.runs
        missing = results_grouped[results_grouped["n"] != expected_n][
            ["model_name", "agent_name", "reasoning_effort", "task", "n"]
        ].copy()
        missing["missing_runs"] = expected_n - missing["n"]
        missing_str = missing.to_string(index=False)
        raise ValueError(
            f"Expected {expected_n} runs for each model + agent + task combination, "
            f"but the following are incomplete:\n{missing_str}"
        )

    results_per_model: pd.DataFrame = results_grouped.groupby(["model_name"])["business_utility"].mean().to_frame("business_utility")
    results_per_model.index.rename("model", inplace=True)
    results_per_model.rename(columns={"business_utility": "score"}, inplace=True)
    results_per_model["score"] = results_per_model["score"].round(2)
    results_per_model.sort_values("score", inplace=True, ascending=False)
    results_per_model.to_csv(args.output)
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
