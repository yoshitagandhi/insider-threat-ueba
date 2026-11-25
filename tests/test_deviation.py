import numpy as np
import pandas as pd

from src.baselines.deviation import add_deviation_features, statistical_anomaly_score, top_reasons
from src.baselines.personal_baseline import FEATURE_COLS

ZSCORE_COLS = [f"{c}_zscore" for c in FEATURE_COLS]


def make_row(value, mean, std):
    row = {"user": "A", "day": pd.Timestamp("2010-01-05").date()}
    for col in FEATURE_COLS:
        row[col] = value
        row[f"{col}_baseline_mean"] = mean
        row[f"{col}_baseline_std"] = std
    return pd.DataFrame([row])


def test_zero_std_and_no_change_gives_zero_deviation():
    result = add_deviation_features(make_row(value=5, mean=5, std=0))
    assert (result[ZSCORE_COLS] == 0).all().all()


def test_zero_std_but_new_behaviour_is_not_hidden():
    daily = make_row(value=0, mean=0, std=0)
    daily["usb_connect_count"] = 4

    result = add_deviation_features(daily)

    assert result.iloc[0]["usb_connect_count_zscore"] == 4.0
    assert np.isfinite(result[ZSCORE_COLS].to_numpy()).all()


def test_cold_start_rows_stay_unscored():
    daily = make_row(value=5, mean=np.nan, std=np.nan)

    result = add_deviation_features(daily)
    result["stat_anomaly_score"] = statistical_anomaly_score(result)

    assert result[ZSCORE_COLS].isna().all().all()
    assert pd.isna(result.iloc[0]["stat_anomaly_score"])


def test_top_reasons_lists_biggest_deviations_first():
    row = pd.Series({f"{c}_zscore": 0.0 for c in FEATURE_COLS})
    row["usb_connect_count_zscore"] = 4.2
    row["file_event_count_zscore"] = -3.1
    row["email_count_zscore"] = 1.0

    assert top_reasons(row, n=2) == "USB activity (+4.2σ), File activity (-3.1σ)"
