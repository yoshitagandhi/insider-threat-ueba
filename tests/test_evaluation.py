import pandas as pd
from sklearn.ensemble import IsolationForest
from unittest.mock import patch
from pathlib import Path

from src.evaluation.error_analysis import categorize_errors
from src.evaluation.evaluate import evaluate_scores
from src.evaluation.plots import threshold_sensitivity
from src.evaluation.report import build_report, train_threshold
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
        "is_malicious": [0, 0, 0, 0, 0, 1, 0, 1],
        "if_anomaly_score": [0.1, 0.2, 0.3, 0.4, 0.1, 0.9, 0.2, 0.8],
        "stat_anomaly_score": [1, 2, 3, 4, 1, 9, 2, 8],
    })

    assert train_threshold(scored, "if_anomaly_score", percentile=100) == 0.4

    report = build_report(scored, percentile=100)
    iforest = report[report["model"] == "Isolation Forest"].iloc[0]
    assert iforest["recall"] == 1.0
    assert iforest["precision"] == 1.0
