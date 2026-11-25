"""Print an honest, forward-looking evaluation of the scored data.

Run after the pipeline:

    python -m src.pipeline
    python -m src.evaluation.report

The alert threshold is picked from the TRAIN period only (its 99th percentile)
and then applied to the TEST period, so no test labels or test scores are used
to choose it.
"""

import pandas as pd

from src.evaluation.diagnosis import rule_diagnosis
from src.evaluation.evaluate import evaluate_scores, train_threshold
from src.models.combined import add_combined_score
from src.models.user_risk import add_user_risk
from src.utils.config import ALERT_PERCENTILE, DATA_PROCESSED_DIR

SCORES = {
    "Isolation Forest (daily)": "if_anomaly_score",
    "Hybrid: IF + USB rule": "hybrid_score",
    "7-day user risk (max)": "user_risk_7d",
    "Combined: daily OR 7-day + rule": "combined_score",
    "Max |z| baseline": "stat_anomaly_score",
}


def load_scored() -> pd.DataFrame:
    """Read the pipeline output. Older files without user_risk_7d get it added here."""
    scored = pd.read_parquet(DATA_PROCESSED_DIR / "scored_daily.parquet")
    if "split" not in scored.columns:
        raise SystemExit("This parquet has no 'split' column. Re-run: python -m src.pipeline")
    if "user_risk_7d" not in scored.columns:
        scored = add_user_risk(scored)
    if "combined_score" not in scored.columns and "rule_alert" in scored.columns:
        scored = add_combined_score(scored)
    return scored


def malicious_test_days(scored: pd.DataFrame, score_col: str, percentile: float) -> pd.DataFrame:
    """Malicious test rows with a True/False "caught" column."""
    threshold = train_threshold(scored, score_col, percentile)
    test = scored[(scored["split"] == "test") & (scored["is_malicious"] == 1)].copy()
    test["caught"] = test[score_col] >= threshold
    return test


def scenario_recall(
    scored: pd.DataFrame,
    score_col: str = "if_anomaly_score",
    percentile: float = ALERT_PERCENTILE,
) -> pd.DataFrame:
    """Share of malicious test days caught, broken down by CERT scenario."""
    test = malicious_test_days(scored, score_col, percentile)
    return (
        test.groupby("scenario_group")["caught"]
        .agg(malicious_days="count", caught="sum")
        .assign(recall=lambda df: df["caught"] / df["malicious_days"])
        .reset_index()
    )


def insiders_caught(
    scored: pd.DataFrame,
    score_col: str = "if_anomaly_score",
    percentile: float = ALERT_PERCENTILE,
) -> pd.DataFrame:
    """How many malicious users got at least one alert on one of their malicious test days.

    Day-level recall can look low because an insider may be active for many days.
    An analyst only needs one good alert to open an investigation, so this
    counts people instead of days.
    """
    test = malicious_test_days(scored, score_col, percentile)

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


def build_report(scored: pd.DataFrame, percentile: float = ALERT_PERCENTILE) -> pd.DataFrame:
    test = scored[scored["split"] == "test"]
    rows = []
    for name, score_col in SCORES.items():
        if score_col not in scored.columns:
            continue
        threshold = train_threshold(scored, score_col, percentile)
        metrics = evaluate_scores(test, score_col, threshold)
        people = insiders_caught(scored, score_col, percentile).iloc[-1]
        rows.append({
            "model": name,
            "threshold": threshold,
            **metrics,
            "insiders_caught": f"{people['caught']}/{people['insiders']}",
        })
    return pd.DataFrame(rows)


def insiders_by_scenario(scored: pd.DataFrame, percentile: float = ALERT_PERCENTILE) -> pd.DataFrame:
    """One row per scenario, one "caught/insiders" column per model."""
    table = None
    for name, score_col in SCORES.items():
        if score_col not in scored.columns:
            continue
        result = insiders_caught(scored, score_col, percentile)
        result[name] = result["caught"].astype(str) + "/" + result["insiders"].astype(str)
        result = result[["scenario_group", name]]
        table = result if table is None else table.merge(result, on="scenario_group")
    return table


def main() -> None:
    scored = load_scored()

    counts = scored.groupby("split")["is_malicious"].agg(user_days="count", malicious_days="sum")
    print("Rows per period:")
    print(counts.to_string())
    print()

    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.width", 200)
    print(f"Test-period results (threshold = train {ALERT_PERCENTILE}th percentile):")
    print(build_report(scored).to_string(index=False))
    print()
    print("Daily Isolation Forest recall per scenario (test period):")
    print(scenario_recall(scored).to_string(index=False))
    print()
    print("Insiders with at least one alert on a malicious test day:")
    print(insiders_by_scenario(scored).to_string(index=False))

    if "rule_alert" in scored.columns:
        print()
        print("Why the first-ever-USB rule did or did not catch each r4.2-1 insider (test period):")
        print(rule_diagnosis(scored).to_string(index=False))


if __name__ == "__main__":
    main()
