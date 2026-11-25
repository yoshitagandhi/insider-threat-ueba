"""Two extra analyses for the report and viva.

1. Alert budget: if analysts can only review N alerts a day, how many
   insiders would they catch? Tried for several thresholds.
2. Ablation: refit Isolation Forest with one feature group removed at a time,
   to see which groups actually help.

Run after the pipeline:

    python -m src.evaluation.analysis

Tables (CSV) and charts (PNG) are written to the reports/ folder.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter, ScalarFormatter

from src.evaluation.evaluate import evaluate_scores
from src.evaluation.report import SCORES, insiders_caught, load_scored, train_threshold
from src.models.feature_selection import load_selected_columns
from src.models.isolation_forest_model import MODEL_COLS, fit_isolation_forest, score_isolation_forest
from src.models.user_risk import add_user_risk
from src.utils.config import ALERT_PERCENTILE, MODELS_DIR, ROOT_DIR

REPORTS_DIR = ROOT_DIR / "reports"

BUDGET_PERCENTILES = (95, 97, 98, 99, 99.5, 99.9)

FEATURE_GROUPS = {
    "Logon": ["logon_count", "after_hours_logon_count", "first_logon_hour", "distinct_pcs"],
    "USB / device": ["usb_connect_count", "after_hours_usb_count", "device_event_count"],
    "File": ["file_event_count", "unique_filenames", "after_hours_file_count"],
    "Email": ["email_count", "total_attachments", "external_recipient_ratio"],
    "New features (Nov 2026)": [
        "distinct_pcs", "first_logon_hour", "after_hours_usb_count", "after_hours_file_count",
    ],
}

COLORS = ["#257de0", "#f47230", "#00b894", "#f2a600"]
MARKERS = ["o", "s", "^", "D"]
TEXT = "#1f1f1f"
TEXT_SECONDARY = "#6b6b6b"
GRID = "#e7e7e7"


def model_columns(features: list[str]) -> list[str]:
    """Turn feature names into the z-score columns the model uses."""
    return [f"{feature}_zscore" for feature in features]


def alert_budget(scored: pd.DataFrame, score_col: str, percentiles=BUDGET_PERCENTILES) -> pd.DataFrame:
    test = scored[scored["split"] == "test"]
    n_test_days = test["day"].nunique()

    rows = []
    for percentile in percentiles:
        threshold = train_threshold(scored, score_col, percentile)
        metrics = evaluate_scores(test, score_col, threshold)
        people = insiders_caught(scored, score_col, percentile).iloc[-1]
        rows.append({
            "percentile": percentile,
            "alerts_per_day": metrics["n_flagged"] / n_test_days,
            "precision": metrics["precision"],
            "day_recall": metrics["recall"],
            "insiders_caught": int(people["caught"]),
            "insiders": int(people["insiders"]),
            "share_insiders_caught": people["share_caught"],
        })
    return pd.DataFrame(rows)


def ablation(
    scored: pd.DataFrame,
    base_columns: list[str] | None = None,
    percentile: float = ALERT_PERCENTILE,
) -> pd.DataFrame:
    """Refit the daily model without each feature group and compare with the base model.

    This looks at the TEST period, so it is a diagnostic only. It explains
    which groups matter; it is not used to choose the model (that is done on
    the validation window in src/models/feature_selection.py).
    """
    base_columns = base_columns or MODEL_COLS
    train = scored[scored["split"] == "train"]
    variants = {"Selected model": base_columns}
    for group, features in FEATURE_GROUPS.items():
        removed = set(model_columns(features))
        remaining = [c for c in base_columns if c not in removed]
        if 0 < len(remaining) < len(base_columns):
            variants[f"Without {group}"] = remaining

    rows = []
    for name, columns in variants.items():
        print(f"  fitting: {name} ({len(columns)} inputs)")
        model = fit_isolation_forest(train, columns=columns)
        rescored = score_isolation_forest(model, scored, columns=columns)

        test = rescored[rescored["split"] == "test"]
        threshold = train_threshold(rescored, "if_anomaly_score", percentile)
        metrics = evaluate_scores(test, "if_anomaly_score", threshold)
        people = insiders_caught(rescored, "if_anomaly_score", percentile).iloc[-1]
        risk_people = insiders_caught(add_user_risk(rescored), "user_risk_7d", percentile).iloc[-1]

        rows.append({
            "variant": name,
            "n_inputs": len(columns),
            "pr_auc": metrics["pr_auc"],
            "precision": metrics["precision"],
            "insiders_caught_daily": int(people["caught"]),
            "insiders_caught_7d_risk": int(risk_people["caught"]),
            "insiders": int(people["insiders"]),
        })
    return pd.DataFrame(rows)


def style_axes(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, length=0)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot_alert_budget(budgets: dict[str, pd.DataFrame]):
    fig, ax = plt.subplots(figsize=(8, 5))
    for (name, table), color, marker in zip(budgets.items(), COLORS, MARKERS):
        ax.plot(
            table["alerts_per_day"], table["share_insiders_caught"],
            color=color, linewidth=2, marker=marker, markersize=7,
            markeredgecolor="white", markeredgewidth=1.5, label=name,
        )
        last = table.iloc[0]
        ax.annotate(
            name, (last["alerts_per_day"], last["share_insiders_caught"]),
            xytext=(8, 0), textcoords="offset points", va="center",
            fontsize=9, color=TEXT,
        )

    ax.set_xscale("log")
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_xlabel("Alerts per day for the whole organisation (log scale)", color=TEXT_SECONDARY)
    ax.set_ylabel("Insiders with at least one alert", color=TEXT_SECONDARY)
    ax.set_title("Insiders caught vs analyst alert budget (test period)", color=TEXT, loc="left")
    ax.legend(frameon=False, loc="lower right", labelcolor=TEXT)
    style_axes(ax)
    fig.tight_layout()
    return fig


def plot_ablation(table: pd.DataFrame):
    table = table.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(table["variant"], table["insiders_caught_daily"], color=COLORS[0], height=0.6)
    ax.bar_label(
        bars,
        labels=[f"{c}/{n}" for c, n in zip(table["insiders_caught_daily"], table["insiders"])],
        padding=4, fontsize=9, color=TEXT,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1},
    )

    full_model = table.loc[table["variant"] == "Selected model", "insiders_caught_daily"].iloc[0]
    ax.axvline(full_model, color=TEXT_SECONDARY, linewidth=1, linestyle="--", zorder=0)

    ax.set_xlabel("Insiders caught by the daily score (train 99th-percentile threshold)", color=TEXT_SECONDARY)
    ax.set_title("What happens when a feature group is removed (test period, diagnostic only)", color=TEXT, loc="left", fontsize=11)
    ax.set_xlim(0, table["insiders"].max() + 3)
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    scored = load_scored()
    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.width", 200)

    budgets = {}
    for name, score_col in SCORES.items():
        budgets[name] = alert_budget(scored, score_col)
        print(f"Alert budget: {name}")
        print(budgets[name].to_string(index=False))
        print()

    all_budgets = pd.concat(
        [table.assign(model=name) for name, table in budgets.items()], ignore_index=True
    )
    all_budgets.to_csv(REPORTS_DIR / "alert_budget.csv", index=False)
    plot_alert_budget(budgets).savefig(REPORTS_DIR / "alert_budget.png", dpi=150)

    base_columns = load_selected_columns(MODELS_DIR / "selected_features.json") or MODEL_COLS
    missing = [c for c in base_columns if c not in scored.columns]
    if missing:
        print(f"Skipping ablation: re-run the pipeline first (missing {missing})")
        return

    print("Ablation (this refits the model several times, give it a minute):")
    ablation_table = ablation(scored, base_columns)
    print(ablation_table.to_string(index=False))
    ablation_table.to_csv(REPORTS_DIR / "ablation.csv", index=False)
    plot_ablation(ablation_table).savefig(REPORTS_DIR / "ablation.png", dpi=150)

    print(f"\nSaved tables and charts to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
