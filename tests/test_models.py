import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS
from src.models.feature_selection import CANDIDATE_FEATURE_SETS, DEFAULT_SET, choose_best
from src.models.rules import RULE_BOOST, add_hybrid_score


def test_rule_needs_first_usb_and_after_hours_activity():
    scored = pd.DataFrame({
        "first_usb_ever": [1, 1, 0],
        "after_hours_logon_count": [1, 0, 3],
        "after_hours_usb_count": [0, 0, 1],
        "after_hours_file_count": [0, 0, 0],
        "if_anomaly_score": [0.1, 0.2, 0.3],
    })

    result = add_hybrid_score(scored)

    assert result["rule_alert"].tolist() == [1, 0, 0]
    assert result["hybrid_score"].iloc[0] == 0.1 + RULE_BOOST
    assert result["hybrid_score"].iloc[1] == 0.2


def test_candidate_feature_sets_only_use_known_features():
    for features in CANDIDATE_FEATURE_SETS.values():
        assert set(features) <= set(FEATURE_COLS)
    assert DEFAULT_SET in CANDIDATE_FEATURE_SETS


def test_choose_best_prefers_insiders_then_pr_auc():
    table = pd.DataFrame({
        "candidate": ["a", "b", "c"],
        "val_insiders_caught": [3, 5, 5],
        "val_insiders": [8, 8, 8],
        "val_pr_auc": [0.9, 0.01, 0.02],
    })
    assert choose_best(table) == "c"


def test_choose_best_falls_back_when_validation_has_no_insiders():
    table = pd.DataFrame({
        "candidate": ["a"], "val_insiders_caught": [0], "val_insiders": [0], "val_pr_auc": [0.0],
    })
    assert choose_best(table) == DEFAULT_SET


def test_combined_score_flags_either_score_and_keeps_rule_on_top():
    from src.models.combined import add_combined_score

    scored = pd.DataFrame({
        "split": ["train"] * 4 + ["test"] * 3,
        "if_anomaly_score": [0.1, 0.2, 0.3, 0.4, 0.5, 0.1, 0.1],
        "user_risk_7d": [1.0, 2.0, 3.0, 4.0, 1.0, 5.0, 1.0],
        "rule_alert": [0, 0, 0, 0, 0, 0, 1],
    })

    result = add_combined_score(scored)["combined_score"].tolist()

    assert result[4] == 1.0
    assert result[5] == 1.0
    assert result[6] == 0.25 + RULE_BOOST


def test_alert_source_separates_rule_today_and_carry_over():
    from src.models.combined import add_alert_source

    scored = pd.DataFrame({
        "split": ["train"] * 4 + ["test"] * 3,
        "if_anomaly_score": [0.1, 0.2, 0.3, 0.4, 0.5, 0.1, 0.1],
        "user_risk_7d": [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.5],
        "rule_alert": [0, 0, 0, 0, 0, 0, 1],
    })

    sources = add_alert_source(scored)["alert_source"].tolist()

    assert sources[4] == "today's behaviour"
    assert sources[5] == "7-day carry-over"
    assert sources[6] == "rule"
