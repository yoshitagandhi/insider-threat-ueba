"""Print an honest, forward-looking evaluation of the scored data.

Run after the pipeline:

    python -m src.pipeline
    python -m src.evaluation.report

The alert threshold is picked from the TRAIN period only (its 99th percentile)
and then applied to the TEST period, so no test labels or test scores are used
to choose it.
"""

import numpy as np
import pandas as pd

from src.evaluation.evaluate import evaluate_scores
from src.utils.config import ALERT_PERCENTILE, DATA_PROCESSED_DIR

SCORES = {
    "Isolation Forest": "if_anomaly_score",
    "Max |z| baseline": "stat_anomaly_score",
}


def train_threshold(scored: pd.DataFrame, score_col: str, percentile: float = ALERT_PERCENTILE) -> float:
    train_scores = scored.loc[scored["split"] == "train", score_col]
    return float(np.percentile(train_scores, percentile))


def build_report(scored: pd.DataFrame, percentile: float = ALERT_PERCENTILE) -> pd.DataFrame:
    test = scored[scored["split"] == "test"]
    rows = []
    for name, score_col in SCORES.items():
        threshold = train_threshold(scored, score_col, percentile)
        metrics = evaluate_scores(test, score_col, threshold)
        rows.append({"model": name, "threshold": threshold, **metrics})
    return pd.DataFrame(rows)


def scenario_recall(scored: pd.DataFrame, score_col: str = "if_anomaly_score") -> pd.DataFrame:
    """Share of malicious test days caught, broken down by CERT scenario."""
    threshold = train_threshold(scored, score_col)
    test = scored[(scored["split"] == "test") & (scored["is_malicious"] == 1)].copy()
    test["caught"] = test[score_col] >= threshold
    return (
        test.groupby("scenario_group")["caught"]
        .agg(malicious_days="count", caught="sum")
        .assign(recall=lambda df: df["caught"] / df["malicious_days"])
        .reset_index()
    )


def insiders_caught(scored: pd.DataFrame, score_col: str = "if_anomaly_score") -> pd.DataFrame:
    """How many malicious users got at least one alert on one of their malicious test days.

    Day-level recall can look low because an insider may be active for many days.
    An analyst only needs one good alert to open an investigation, so this
    counts people instead of days.
    """
    threshold = train_threshold(scored, score_col)
    test = scored[(scored["split"] == "test") & (scored["is_malicious"] == 1)].copy()
    test["caught"] = test[score_col] >= threshold

    per_user = test.groupby(["scenario_group", "user"])["caught"].any().reset_index()
    summary = (
        per_user.groupby("scenario_group")["caught"]
        .agg(insiders="count", caught="sum")
        .reset_index()
    )

    total = pd.DataFrame([{
        "scenario_group": "all",
        "insiders": summary["insiders"].sum(),
        "caught": summary["caught"].sum(),
    }])
    summary = pd.concat([summary, total], ignore_index=True)
    summary["share_caught"] = summary["caught"] / summary["insiders"]
    return summary


def main() -> None:
    scored = pd.read_parquet(DATA_PROCESSED_DIR / "scored_daily.parquet")
    if "split" not in scored.columns:
        raise SystemExit("This parquet has no 'split' column. Re-run: python -m src.pipeline")

    counts = scored.groupby("split")["is_malicious"].agg(user_days="count", malicious_days="sum")
    print("Rows per period:")
    print(counts.to_string())
    print()

    pd.set_option("display.float_format", "{:.4f}".format)
    print(f"Test-period results (threshold = train {ALERT_PERCENTILE}th percentile):")
    print(build_report(scored).to_string(index=False))
    print()
    print("Isolation Forest recall per scenario (test period):")
    print(scenario_recall(scored).to_string(index=False))
    print()
    print("Insiders with at least one alert on a malicious test day:")
    print(insiders_caught(scored).to_string(index=False))


if __name__ == "__main__":
    main()
