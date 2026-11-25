"""Explain, insider by insider, why the first-ever-USB rule did or did not fire."""

import pandas as pd

from src.evaluation.evaluate import train_threshold
from src.utils.config import ALERT_PERCENTILE


def explain(row: pd.Series) -> str:
    if row["usb_days_before_attack"] > 0:
        return "used USB before the attack, so 'first-ever' cannot fire"
    if pd.isna(row["first_usb_day"]):
        return "no first-ever USB day among scored days (cold start or no USB)"
    if not row["first_usb_after_hours"]:
        return "first USB day had no after-hours activity"
    if not row["first_usb_is_malicious_day"]:
        return "rule fired, but not on a labelled malicious day"
    return "rule fired on a malicious day"


def rule_diagnosis(
    scored: pd.DataFrame,
    scenario: str = "r4.2-1",
    percentile: float = ALERT_PERCENTILE,
) -> pd.DataFrame:
    """One row per insider of the scenario who has malicious days in the test period."""
    score_names = {
        "if_anomaly_score": "caught_daily",
        "user_risk_7d": "caught_7d_risk",
        "combined_score": "caught_combined",
    }
    thresholds = {
        col: train_threshold(scored, col, percentile)
        for col in score_names
        if col in scored.columns
    }

    test_bad = scored[
        (scored["split"] == "test")
        & (scored["is_malicious"] == 1)
        & (scored["scenario_group"] == scenario)
    ]

    rows = []
    for user, bad_days in test_bad.groupby("user"):
        history = scored[scored["user"] == user].sort_values("day")
        first_attack_day = history.loc[history["is_malicious"] == 1, "day"].min()

        usb_before = history[(history["day"] < first_attack_day) & (history["usb_connect_count"] > 0)]
        first_usb = history[history["first_usb_ever"] == 1]

        row = {
            "user": user,
            "malicious_test_days": len(bad_days),
            "usb_days_before_attack": len(usb_before),
            "first_usb_day": first_usb["day"].iloc[0] if len(first_usb) else None,
            "first_usb_after_hours": bool(len(first_usb)) and bool(first_usb["rule_alert"].iloc[0] == 1),
            "first_usb_is_malicious_day": bool(len(first_usb)) and bool(first_usb["is_malicious"].iloc[0] == 1),
        }
        for col, threshold in thresholds.items():
            row[score_names[col]] = bool((bad_days[col] >= threshold).any())
        row["why"] = explain(pd.Series(row))
        rows.append(row)

    return pd.DataFrame(rows)
