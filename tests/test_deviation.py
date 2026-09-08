import pandas as pd
from src.baselines.deviation import add_deviation_features
from src.baselines.personal_baseline import FEATURE_COLS


def test_zero_std_does_not_crash_or_produce_inf():
    row = {"user": "A", "day": pd.Timestamp("2010-01-05").date()}
    for col in FEATURE_COLS:
        row[col] = 5
        row[f"{col}_baseline_mean"] = 5
        row[f"{col}_baseline_std"] = 0  # user with zero historical variance
    daily = pd.DataFrame([row])

    result = add_deviation_features(daily)
    zscore_cols = [f"{c}_zscore" for c in FEATURE_COLS]
    assert (result[zscore_cols] == 0).all().all()  # no value change → 0 deviation, not NaN/inf