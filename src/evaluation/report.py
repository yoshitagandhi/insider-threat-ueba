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

EARLY_WARNING_DAYS = 7

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
    return summarise_insiders(per_user)


def insiders_caught_early(
    scored: pd.DataFrame,
    score_col: str = "if_anomaly_score",
    percentile: float = ALERT_PERCENTILE,
    lookback_days: int = EARLY_WARNING_DAYS,
) -> pd.DataFrame:
    """Like insiders_caught, but an alert in the days just BEFORE the attack also counts.

    CERT labels only the attack days themselves. A warning a few days earlier
    (for example on the insider's first-ever USB day) is just as useful to an
    analyst, but the day-level labels count it as a false positive. Every score
    is measured the same way, so the comparison stays fair.
    """
    threshold = train_threshold(scored, score_col, percentile)
    attack_days = scored[(scored["split"] == "test") & (scored["is_malicious"] == 1)]

    rows = []
    for (scenario, user), bad in attack_days.groupby(["scenario_group", "user"]):
        first_attack = pd.to_datetime(bad["day"]).min()
        history = scored[scored["user"] == user]
        days_before_attack = (first_attack - pd.to_datetime(history["day"])).dt.days
        before = history[(days_before_attack >= 1) & (days_before_attack <= lookback_days)]
        caught = (bad[score_col] >= threshold).any() or (before[score_col] >= threshold).any()
        rows.append({"scenario_group": scenario, "user": user, "caught": bool(caught)})

    return summarise_insiders(pd.DataFrame(rows))


def benign_window_alert_rate(
    scored: pd.DataFrame,
    score_col: str,
    percentile: float = ALERT_PERCENTILE,
    window_days: int = EARLY_WARNING_DAYS + 1,
) -> float:
    """Chance check for the early-warning count.

    Cuts each benign user's test period into blocks of window_days and returns
    the share of blocks that contain at least one alert. If insiders were
    caught at about this rate, the early-warning result would be luck.
    """
    threshold = train_threshold(scored, score_col, percentile)
    malicious_users = set(scored.loc[scored["is_malicious"] == 1, "user"])
    benign = scored[(scored["split"] == "test") & ~scored["user"].isin(malicious_users)].copy()
    days = pd.to_datetime(benign["day"])
    benign["block"] = (days - days.min()).dt.days // window_days
    benign["alert"] = benign[score_col] >= threshold
    return float(benign.groupby(["user", "block"])["alert"].any().mean())


def summarise_insiders(per_user: pd.DataFrame) -> pd.DataFrame:
    """Count caught insiders per scenario, plus an "all" row."""
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
        early = insiders_caught_early(scored, score_col, percentile).iloc[-1]
        rows.append({
            "model": name,
            "threshold": threshold,
            **metrics,
            "insiders_caught": f"{people['caught']}/{people['insiders']}",
            "incl_7d_early": f"{early['caught']}/{early['insiders']}",
        })
    return pd.DataFrame(rows)


def insiders_by_scenario(
    scored: pd.DataFrame,
    percentile: float = ALERT_PERCENTILE,
    early: bool = False,
) -> pd.DataFrame:
    """One row per scenario, one "caught/insiders" column per model."""
    count = insiders_caught_early if early else insiders_caught
    table = None
    for name, score_col in SCORES.items():
        if score_col not in scored.columns:
            continue
        result = count(scored, score_col, percentile)
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
    print()
    print(f"Insiders alerted during the attack OR in the {EARLY_WARNING_DAYS} days before it:")
    print(insiders_by_scenario(scored, early=True).to_string(index=False))
    print()
    print(f"Chance check: share of random {EARLY_WARNING_DAYS + 1}-day windows of benign users with an alert:")
    for name, score_col in SCORES.items():
        if score_col in scored.columns:
            print(f"  {name}: {benign_window_alert_rate(scored, score_col):.1%}")

    if "rule_alert" in scored.columns:
        print()
        print("Why the first-ever-USB rule did or did not catch each r4.2-1 insider (test period):")
        print(rule_diagnosis(scored).to_string(index=False))


if __name__ == "__main__":
    main()
