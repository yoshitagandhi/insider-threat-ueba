import pandas as pd
from sklearn.ensemble import IsolationForest
from unittest.mock import patch
from pathlib import Path

from src.evaluation.error_analysis import categorize_errors
from src.evaluation.evaluate import evaluate_scores
from src.evaluation.plots import threshold_sensitivity
from src.models.isolation_forest_model import save_isolation_forest


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
