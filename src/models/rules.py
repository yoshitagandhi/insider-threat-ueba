import pandas as pd

RULE_BOOST = 10.0


def first_usb_after_hours_rule(daily: pd.DataFrame) -> pd.Series:
    """True on a user's first-ever USB day if they were also active after hours.

    This is the textbook CERT r4.2-1 pattern: someone who never used removable
    media suddenly logs in at night and copies data to a USB drive.
    """
    after_hours = (
        (daily["after_hours_logon_count"] > 0)
        | (daily["after_hours_usb_count"] > 0)
        | (daily["after_hours_file_count"] > 0)
    )
    return (daily["first_usb_ever"] == 1) & after_hours


def add_hybrid_score(scored: pd.DataFrame) -> pd.DataFrame:
    """Combine the model with one hand-written rule.

    hybrid_score is the Isolation Forest score, plus RULE_BOOST when the rule
    fires. Model scores are always far below 10, so rule days rank above every
    model-only day. The rule fires on very few days, so it barely uses up the
    alert budget that the model needs for other scenarios.
    """
    scored = scored.copy()
    scored["rule_alert"] = first_usb_after_hours_rule(scored).astype(int)
    scored["hybrid_score"] = scored["if_anomaly_score"] + RULE_BOOST * scored["rule_alert"]
    return scored
