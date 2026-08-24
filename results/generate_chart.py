#!/usr/bin/env python3
"""Generate business-utility-score, mean-score and task-difficulty charts.

Usage:
    python generate_chart.py

Inputs:
    bus_results.csv:
        model,score,Coefficient of variation

    mean_results.csv:
        model,score

    tasks_results.csv:
        task,score
"""

import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

COLOR_MAIN = "#1b54ff"
COLOR_VARIATION = COLOR_MAIN
COLOR_TRACK = "#f1f1f3"
COLOR_DOT = "#202124"
COLOR_GRID = "#e5e7eb"
COLOR_TICKS = "#6b7280"
COLOR_LABELS = "#111827"
COLOR_XLABEL = "#374151"
COLOR_SUBTITLE = "#4b5563"
COLOR_FOOTER = "#9ca3af"

BADGE = "BU Eval"
BADGE_DATE = "15.07.2026"
FOOTER = "deepsense.ai · github.com/deepsense-ai/business-utility-evaluation"



def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate business-utility-score and mean-score charts."
        )
    )
    parser.add_argument(
        "--bus-csv",
        default="bus_results.csv",
        help="BUS results CSV path (default: bus_results.csv)",
    )
    parser.add_argument(
        "--mean-csv",
        default="mean_results.csv",
        help="Mean results CSV path (default: mean_results.csv)",
    )
    parser.add_argument(
        "--bus-output",
        default="bus_chart.png",
        help=(
            "Business-utility chart output "
            "(default: business_utility_score_chart.png)"
        ),
    )
    parser.add_argument(
        "--mean-output",
        default="mean_score_chart.png",
        help="Mean chart output (default: mean_score_chart.png)",
    )
    parser.add_argument(
        "--tasks-csv",
        default="tasks_results.csv",
        help="Per-task results CSV path (default: tasks_results.csv)",
    )
    parser.add_argument(
        "--tasks-output",
        default="tasks_difficulty.png",
        help="Task-difficulty chart output (default: tasks_difficulty.png)",
    )
    args = parser.parse_args()

    bus_results, mean_results = load_results(
        args.bus_csv,
        args.mean_csv,
    )
    tasks_results = load_task_results(args.tasks_csv)

    plot_business_utility_scores(
        bus_results,
        args.bus_output,
    )
    plot_mean_scores(
        mean_results,
        args.mean_output,
    )
    plot_task_difficulty(
        tasks_results,
        args.tasks_output,
    )


def load_results(
        bus_path: str,
        mean_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bus = pd.read_csv(bus_path)
    means = pd.read_csv(mean_path)

    required_bus_columns = {
        "model",
        "score",
        "Coefficient of variation",
    }
    required_mean_columns = {"model", "score"}

    missing_bus = required_bus_columns - set(bus.columns)
    if missing_bus:
        raise ValueError(
            f"{bus_path} is missing columns: {sorted(missing_bus)}"
        )

    missing_mean = required_mean_columns - set(means.columns)
    if missing_mean:
        raise ValueError(
            f"{mean_path} is missing columns: {sorted(missing_mean)}"
        )

    bus = bus[
        ["model", "score", "Coefficient of variation"]
    ].copy()
    means = means[["model", "score"]].copy()

    bus["score"] = pd.to_numeric(bus["score"], errors="raise")
    bus["Coefficient of variation"] = pd.to_numeric(
        bus["Coefficient of variation"],
        errors="raise",
    )
    means["score"] = pd.to_numeric(means["score"], errors="raise")

    if bus["model"].duplicated().any() or means["model"].duplicated().any():
        raise ValueError("Each CSV must contain only one row per model")

    if not bus["score"].between(0, 1).all():
        raise ValueError("Business-utility scores must be between 0 and 1")

    if not means["score"].between(0, 1).all():
        raise ValueError("Mean scores must be between 0 and 1")

    if (bus["Coefficient of variation"] < 0).any():
        raise ValueError("Coefficient of variation cannot be negative")

    bus_models = set(bus["model"])
    mean_models = set(means["model"])
    if bus_models != mean_models:
        raise ValueError(
            "The CSV files contain different models. "
            f"Only in {bus_path}: {sorted(bus_models - mean_models)}; "
            f"only in {mean_path}: {sorted(mean_models - bus_models)}"
        )

    means = means.merge(
        bus[["model", "Coefficient of variation"]],
        on="model",
        validate="one_to_one",
    )

    standard_deviation = (
            means["score"] * means["Coefficient of variation"]
    )
    means["interval_left"] = (
            means["score"] - standard_deviation
    ).clip(lower=0)
    means["interval_right"] = (
            means["score"] + standard_deviation
    ).clip(upper=1)

    bus = bus.sort_values("score", ascending=False).reset_index(drop=True)
    means = means.sort_values("score", ascending=False).reset_index(drop=True)

    return bus, means


def load_task_results(tasks_path: str) -> pd.DataFrame:
    tasks = pd.read_csv(tasks_path)

    required_task_columns = {"task", "score"}
    missing_tasks = required_task_columns - set(tasks.columns)
    if missing_tasks:
        raise ValueError(
            f"{tasks_path} is missing columns: {sorted(missing_tasks)}"
        )

    tasks = tasks[["task", "score"]].copy()
    tasks["score"] = pd.to_numeric(tasks["score"], errors="raise")

    if tasks["task"].duplicated().any():
        raise ValueError(f"{tasks_path} must contain only one row per task")

    if not tasks["score"].between(0, 1).all():
        raise ValueError("Task scores must be between 0 and 1")

    return tasks.sort_values("score", ascending=True).reset_index(drop=True)


def style_axis(
        axis: plt.Axes,
        models: pd.Series,
        xlabel: str,
) -> None:
    axis.invert_yaxis()
    axis.set_xlim(0.0, 1.0)
    axis.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    axis.set_yticks(range(len(models)))
    axis.set_yticklabels(
        models,
        fontsize=12,
        color=COLOR_LABELS,
    )
    axis.tick_params(
        axis="x",
        length=0,
        labelsize=11,
        colors=COLOR_TICKS,
    )
    axis.tick_params(axis="y", length=0)
    axis.set_xlabel(
        xlabel,
        fontsize=12,
        color=COLOR_XLABEL,
        labelpad=12,
    )
    axis.grid(
        axis="x",
        color=COLOR_GRID,
        linewidth=0.8,
        zorder=0,
    )
    axis.set_axisbelow(True)

    for spine in axis.spines.values():
        spine.set_visible(False)


def add_figure_text(
        figure: plt.Figure,
        title: str,
        subtitle: str,
        color: str,
) -> None:
    figure.text(
        0.008,
        0.985,
        title,
        fontsize=24,
        fontweight="bold",
        color=COLOR_LABELS,
        ha="left",
        va="top",
    )
    figure.text(
        0.008,
        0.925,
        subtitle,
        fontsize=12.5,
        color=COLOR_SUBTITLE,
        ha="left",
        va="top",
    )
    figure.text(
        0.992,
        0.965,
        BADGE,
        fontsize=13,
        fontweight="bold",
        color=color,
        ha="right",
        va="top",
    )
    figure.text(
        0.992,
        0.925,
        BADGE_DATE,
        fontsize=9,
        fontweight="bold",
        color=color,
        ha="right",
        va="top",
    )
    figure.text(
        0.5,
        0.0,
        FOOTER,
        fontsize=9,
        color=COLOR_FOOTER,
        ha="center",
        va="bottom",
    )


def save_figure(
        figure: plt.Figure,
        output: str,
        right: float = 0.982,
) -> None:
    figure.subplots_adjust(
        left=0.245,
        right=right,
        top=0.84,
        bottom=0.135,
    )
    figure.savefig(
        output,
        format="png",
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(figure)
    print(f"Saved chart to {output}")


def plot_business_utility_scores(
        results: pd.DataFrame,
        output: str,
) -> None:
    figure, axis = plt.subplots(
        figsize=(12.5, 6.5),
        dpi=150,
    )

    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")

    number_of_results = len(results)
    y_positions = range(number_of_results)
    colors = sns.light_palette(
        COLOR_MAIN,
        n_colors=number_of_results + 1,
        reverse=True,
    )[:number_of_results]

    axis.barh(
        y_positions,
        results["score"],
        height=0.53,
        color=colors,
        zorder=3,
    )

    for position, score in enumerate(results["score"]):
        axis.text(
            score + 0.018,
            position,
            f"{score:.2f}",
            va="center",
            ha="left",
            fontsize=13,
            color=COLOR_LABELS,
            fontweight="bold" if position == 0 else "normal",
            )

    style_axis(
        axis,
        results["model"],
        "Mean business utility score, scale: 0–1",
    )
    axis.set_yticklabels(
        results["model"],
        fontsize=13,
        color=COLOR_LABELS,
    )

    add_figure_text(
        figure,
        "Mean business utility score per model",
        "Scale: 0–1. Higher is better.",
        COLOR_MAIN,
    )
    save_figure(figure, output)


def plot_mean_scores(
        results: pd.DataFrame,
        output: str,
) -> None:
    figure_height = max(5.0, 1.0 + len(results) * 0.72)
    figure, axis = plt.subplots(
        figsize=(12.5, figure_height),
        dpi=150,
    )

    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")

    for position, row in enumerate(results.itertuples(index=False)):
        axis.plot(
            [0.0, 1.0],
            [position, position],
            color=COLOR_TRACK,
            linewidth=8,
            solid_capstyle="round",
            zorder=1,
        )
        axis.plot(
            [row.interval_left, row.interval_right],
            [position, position],
            color=COLOR_VARIATION,
            linewidth=8,
            solid_capstyle="round",
            zorder=2,
        )
        axis.scatter(
            row.score,
            position,
            s=55,
            color=COLOR_DOT,
            edgecolors="white",
            linewidths=1.4,
            zorder=3,
        )
        axis.text(
            1.025,
            position,
            (
                f"{row.score:.2f}"
                #                f"({row.interval_left:.2f}–{row.interval_right:.2f})"
            ),
            va="center",
            ha="left",
            fontsize=11,
            color=COLOR_LABELS,
            transform=axis.get_yaxis_transform(),
            clip_on=False,
        )

    style_axis(
        axis,
        results["model"],
        "Mean score, scale: 0–1",
    )
    add_figure_text(
        figure,
        "Mean score per model",
        (
            "The dot shows the mean. The interval spans ± 1 standard deviation."
        ),
        COLOR_VARIATION,
    )
    save_figure(figure, output, right=0.79)


def plot_task_difficulty(
        results: pd.DataFrame,
        output: str,
) -> None:
    figure, axis = plt.subplots(
        figsize=(12.5, 6.5),
        dpi=150,
    )

    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")

    number_of_results = len(results)
    y_positions = range(number_of_results)
    colors = sns.light_palette(
        COLOR_MAIN,
        n_colors=number_of_results + 1,
        reverse=True,
    )[:number_of_results]

    axis.barh(
        y_positions,
        results["score"],
        height=0.53,
        color=colors,
        zorder=3,
    )

    for position, score in enumerate(results["score"]):
        axis.text(
            score + 0.018,
            position,
            f"{score:.2f}",
            va="center",
            ha="left",
            fontsize=13,
            color=COLOR_LABELS,
            fontweight="bold" if position == 0 else "normal",
            )

    style_axis(
        axis,
        results["task"],
        "Mean score across all models, scale: 0–1",
    )
    axis.set_yticklabels(
        results["task"],
        fontsize=13,
        color=COLOR_LABELS,
    )

    add_figure_text(
        figure,
        "Task difficulty",
        "Mean score across all models per task. Lower means harder.",
        COLOR_MAIN,
    )
    save_figure(figure, output)


if __name__ == "__main__":
    main()
