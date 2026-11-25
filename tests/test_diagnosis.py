import pandas as pd

from src.evaluation.diagnosis import rule_diagnosis


def make_user(user, usb, first_usb, rule, malicious, split="test"):
    n = len(usb)
    return pd.DataFrame({
        "user": [user] * n,
        "day": pd.date_range("2010-01-01", periods=n).date,
        "split": [split] * n,
        "usb_connect_count": usb,
        "first_usb_ever": first_usb,
        "rule_alert": rule,
        "is_malicious": malicious,
        "scenario_group": ["r4.2-1" if m else None for m in malicious],
        "if_anomaly_score": [0.0] * n,
    })


def test_rule_diagnosis_explains_each_insider():
    train = pd.DataFrame({
        "user": ["Z"] * 4, "day": pd.date_range("2009-01-01", periods=4).date, "split": ["train"] * 4,
        "usb_connect_count": [0] * 4, "first_usb_ever": [0] * 4, "rule_alert": [0] * 4,
        "is_malicious": [0] * 4, "scenario_group": [None] * 4, "if_anomaly_score": [0.0, 0.1, 0.2, 0.3],
    })
    early = make_user("A", [1, 0, 2], [1, 0, 0], [1, 0, 0], [0, 0, 1])
    on_day = make_user("B", [0, 0, 3], [0, 0, 1], [0, 0, 1], [0, 0, 1])
    daytime = make_user("C", [0, 0, 3], [0, 0, 1], [0, 0, 0], [0, 0, 1])
    earlier_daytime = make_user("D", [2, 0, 3], [1, 0, 0], [0, 0, 0], [0, 0, 1])

    result = rule_diagnosis(pd.concat([train, early, on_day, daytime, earlier_daytime])).set_index("user")

    assert result.loc["A", "why"] == "fired 2d early"
    assert result.loc["A", "days_before"] == 2
    assert result.loc["B", "why"] == "fired on attack day"
    assert result.loc["C", "why"] == "no after-hours activity"
    assert result.loc["D", "why"] == "earlier USB, no after-hours"
