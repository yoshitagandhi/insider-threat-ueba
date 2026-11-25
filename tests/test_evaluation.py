import pandas as pd
from sklearn.ensemble import IsolationForest
from unittest.mock import patch
from pathlib import Path

from src.evaluation.error_analysis import categorize_errors
from src.evaluation.evaluate import evaluate_scores
from src.evaluation.plots import threshold_sensitivity
from src.evaluation.report import build_report, insiders_caught, train_threshold
from src.models.user_risk import add_user_risk
from src.models.isolation_forest_model import save_isolation_forest, split_by_date


def test_evaluation_metrics_and_error_categories():
    scored = pd.DataFrame({
        "is_malicious": [0, 1, 1, 0],
        "if_anomaly_score": [0.1, 0.9, 0.2, 0.8],
    })
    metrics = evaluate_scores(scored, "if_anomaly_score", threshold=0.75)
    errors = categorize_errors(scored, "if_anomaly_score", threshold=0.75)

    assert metrics["n_flagged"] == 2
    assert metrics["n_malicious_days"] == 2
    assert set(errors["error_type"]) == {"true_negative", "true_positive", "false_negative", "false_positive"}


def test_threshold_sensitivity_returns_requested_percentiles():
    scored = pd.DataFrame({
        "is_malicious": [0, 1, 0, 1, 0],
        "if_anomaly_score": [0.1, 0.9, 0.2, 0.8, 0.3],
    })
    result = threshold_sensitivity(scored, "if_anomaly_score", percentiles=(50, 90))
    assert result["percentile"].tolist() == [50, 90]
    assert result["threshold"].is_monotonic_increasing


def test_fitted_model_is_sent_to_joblib_with_requested_path():
    model = IsolationForest(random_state=42).fit([[0], [1], [2]])
    output = Path("models/isolation_forest.joblib")
    with patch("src.models.isolation_forest_model.joblib.dump") as dump:
        save_isolation_forest(model, output)
    dump.assert_called_once_with(model, output)


def test_split_by_date_puts_earlier_days_in_train():
    daily = pd.DataFrame({"day": pd.date_range("2010-01-01", periods=10).date})
    train, test, cutoff = split_by_date(daily, train_fraction=0.6)

    assert len(train) == 6
    assert len(test) == 4
    assert train["day"].max() < cutoff <= test["day"].min()


def test_report_threshold_comes_from_train_rows_only():
    scored = pd.DataFrame({
        "split": ["train"] * 4 + ["test"] * 4,
        "day": pd.date_range("2010-01-01", periods=8).date,
        "user": ["X", "X", "X", "X", "Y", "A", "Y", "B"],
        "scenario_group": [None, None, None, None, None, "r4.2-1", None, "r4.2-2"],
        "is_malicious": [0, 0, 0, 0, 0, 1, 0, 1],
        "if_anomaly_score": [0.1, 0.2, 0.3, 0.4, 0.1, 0.9, 0.2, 0.8],
        "stat_anomaly_score": [1, 2, 3, 4, 1, 9, 2, 8],
    })

    assert train_threshold(scored, "if_anomaly_score", percentile=100) == 0.4

    report = build_report(scored, percentile=100)
    iforest = report[report["model"] == "Isolation Forest (daily)"].iloc[0]
    assert iforest["recall"] == 1.0
    assert iforest["precision"] == 1.0
    assert iforest["insiders_caught"] == "2/2"
    assert iforest["incl_7d_early"] == "2/2"


def test_insiders_caught_counts_people_not_days():
    scored = pd.DataFrame({
        "split": ["train"] * 4 + ["test"] * 5,
        "user": ["X", "X", "X", "X", "A", "A", "A", "B", "B"],
        "scenario_group": [None] * 4 + ["r4.2-2"] * 5,
        "is_malicious": [0, 0, 0, 0, 1, 1, 1, 1, 1],
        "if_anomaly_score": [0.1, 0.2, 0.3, 0.4, 0.1, 0.1, 0.9, 0.1, 0.2],
    })

    result = insiders_caught(scored).set_index("scenario_group")

    assert result.loc["r4.2-2", "insiders"] == 2
    assert result.loc["r4.2-2", "caught"] == 1
    assert result.loc["all", "share_caught"] == 0.5


def test_user_risk_is_a_backward_looking_max():
    scored = pd.DataFrame({
        "user": ["A"] * 4,
        "day": pd.date_range("2010-01-01", periods=4).date,
        "if_anomaly_score": [0.0, 0.0, 0.9, 0.3],
    })

    result = add_user_risk(scored, window=2)

    assert result["user_risk_7d"].round(2).tolist() == [0.0, 0.0, 0.9, 0.9]


def test_early_warning_counts_alerts_just_before_the_attack():
    from src.evaluation.report import insiders_caught, insiders_caught_early

    days = pd.date_range("2010-01-01", periods=10)
    scored = pd.DataFrame({
        "user": ["T"] * 4 + ["A"] * 3,
        "day": list(days[:4]) + list(days[5:8]),
        "split": ["train"] * 4 + ["test"] * 3,
        "is_malicious": [0, 0, 0, 0, 0, 0, 1],
        "scenario_group": [None] * 6 + ["r4.2-1"],
        "if_anomaly_score": [0.1, 0.2, 0.3, 0.4, 0.9, 0.0, 0.0],
    })

    assert insiders_caught(scored, percentile=100).iloc[-1]["caught"] == 0
    assert insiders_caught_early(scored, percentile=100, lookback_days=7).iloc[-1]["caught"] == 1
    assert insiders_caught_early(scored, percentile=100, lookback_days=1).iloc[-1]["caught"] == 0


def test_risk_score_is_capped_combined_score():
    from src.models.combined import add_risk_score

    scored = pd.DataFrame({"combined_score": [0.5, 0.999, 10.4], "if_anomaly_score": [0.0, 0.0, 0.0]})
    assert add_risk_score(scored)["risk_score"].tolist() == [0.5, 0.999, 1.0]
