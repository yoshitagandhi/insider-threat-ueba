"""Explain, insider by insider, whether and when the first-ever-USB rule fired."""

import pandas as pd

from src.evaluation.evaluate import train_threshold
from src.utils.config import ALERT_PERCENTILE

SCORE_NAMES = {
    "if_anomaly_score": "caught_daily",
    "user_risk_7d": "caught_7d",
    "combined_score": "caught_combined",
}


def explain(row: pd.Series) -> str:
    """A short reason. "days_before" is how many days the first USB came before the first attack day."""
    if pd.isna(row["first_usb_day"]):
        return "no first USB day in scored data"
    if row["rule_fired"]:
        if row["first_usb_is_malicious_day"]:
            return "fired on attack day"
        if row["days_before"] > 0:
            return f"fired {row['days_before']}d early"
        return "fired after attack began"
    if row["days_before"] > 0:
        return "earlier USB, no after-hours"
    return "no after-hours activity"


def rule_diagnosis(
    scored: pd.DataFrame,
    scenario: str = "r4.2-1",
    percentile: float = ALERT_PERCENTILE,
) -> pd.DataFrame:
    """One row per insider of the scenario who has malicious days in the test period."""
    thresholds = {
        col: train_threshold(scored, col, percentile)
        for col in SCORE_NAMES
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
        first_attack_day = pd.Timestamp(history.loc[history["is_malicious"] == 1, "day"].min())
        first_usb = history[history["first_usb_ever"] == 1]

        row = {
            "user": user,
            "attack_days": len(bad_days),
            "first_attack_day": first_attack_day.date(),
            "first_usb_day": None,
            "days_before": 0,
            "rule_fired": False,
            "first_usb_is_malicious_day": False,
        }
        if len(first_usb):
            usb_row = first_usb.iloc[0]
            usb_day = pd.Timestamp(usb_row["day"])
            row["first_usb_day"] = usb_day.date()
            row["days_before"] = (first_attack_day - usb_day).days
            row["rule_fired"] = bool(usb_row["rule_alert"] == 1)
            row["first_usb_is_malicious_day"] = bool(usb_row["is_malicious"] == 1)

        for col, threshold in thresholds.items():
            row[SCORE_NAMES[col]] = bool((bad_days[col] >= threshold).any())
        row["why"] = explain(pd.Series(row))
        rows.append(row)

    return pd.DataFrame(rows)
