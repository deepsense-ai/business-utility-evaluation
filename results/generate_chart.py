#!/usr/bin/env python3
"""Render a horizontal bar chart of mean business utility per model.

Usage:
    python generate_chart.py input.csv -o chart.png

Expected CSV format (header required):
    model,score
    claude-opus-4-8,0.42
    gpt-5.5,0.23
    ...
"""

import argparse
import csv
import sys

import matplotlib.pyplot as plt
import seaborn as sns

# Color palette taken from the reference figure
COLOR_MAIN = "#1b54ff"
COLOR_GRID = "#e5e7eb"
COLOR_TICKS = "#6b7280"
COLOR_LABELS = "#111827"
COLOR_XLABEL = "#374151"
COLOR_SUBTITLE = "#4b5563"
COLOR_FOOTER = "#9ca3af"

TITLE = "Mean business utility per model"
SUBTITLE = ("Scale: 0\u20131. Higher is better. Even top models leave substantial "
            "room for improvement on realistic business tasks.")
BADGE = "BU Eval"
XLABEL = "Mean business utility, scale: 0\u20131"
FOOTER = "deepsense.ai \u00b7 github.com/deepsense-ai/business-utility-evaluation"


def read_csv(path: str) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or len(reader.fieldnames) < 2:
            sys.exit("CSV must have at least two columns: model,score")
        model_col, score_col = reader.fieldnames[0], reader.fieldnames[1]
        for line in reader:
            try:
                rows.append((line[model_col].strip(), float(line[score_col])))
            except (TypeError, ValueError):
                sys.exit(f"Invalid score value in row: {line}")
    if not rows:
        sys.exit("CSV contains no data rows")
    return rows


def plot(data: list[tuple[str, float]], output: str) -> None:
    # Sort descending so the best model is on top
    data = sorted(data, key=lambda r: r[1], reverse=True)
    models = [r[0] for r in data]
    scores = [r[1] for r in data]
    n = len(data)

    fig, ax = plt.subplots(figsize=(12.5, 6.5), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Bar colors: faded from the main blue
    colors = sns.light_palette(COLOR_MAIN, n_colors=n+1, reverse=True)[:n]

    y_pos = range(n)
    ax.barh(y_pos, scores, height=0.53, color=colors, zorder=3)
    ax.invert_yaxis()  # best model on top

    # Value labels at the end of each bar (best one in bold)
    for i, value in enumerate(scores):
        ax.text(value + 0.018, i, f"{value:.2f}",
                va="center", ha="left",
                fontsize=13, color=COLOR_LABELS,
                fontweight="bold" if i == 0 else "normal")

    # Axes styling
    ax.set_xlim(0, 1)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.tick_params(axis="x", length=0, labelsize=11, colors=COLOR_TICKS)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(models, fontsize=13, color=COLOR_LABELS)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(XLABEL, fontsize=12, color=COLOR_XLABEL, labelpad=12)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color=COLOR_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    # Title, subtitle, badge and footer (figure-level text)
    fig.text(0.008, 0.985, TITLE, fontsize=24, fontweight="bold", color=COLOR_LABELS, ha="left", va="top")
    fig.text(0.008, 0.915, SUBTITLE, fontsize=12.5, color=COLOR_SUBTITLE, ha="left", va="top")
    fig.text(0.992, 0.965, BADGE, fontsize=13, fontweight="bold", color=COLOR_MAIN, ha="right", va="top")
    fig.text(0.5, 0.0, FOOTER, fontsize=8.5, color=COLOR_FOOTER, ha="center", va="bottom")

    fig.subplots_adjust(left=0.245, right=0.982, top=0.83, bottom=0.135)
    fig.savefig(output, format="png", facecolor="white")
    plt.close(fig)
    print(f"Saved chart to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a mean-business-utility bar chart from a CSV file.")
    parser.add_argument("csv_file", help="Input CSV with columns: model,score")
    parser.add_argument("-o", "--output", default="chart.png",
                        help="Output PNG path (default: chart.png)")
    args = parser.parse_args()

    plot(read_csv(args.csv_file), args.output)


if __name__ == "__main__":
    main()
