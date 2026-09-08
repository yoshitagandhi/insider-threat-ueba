import pandas as pd

from src.baselines.anchor_baseline import add_anchor_baseline
from src.baselines.personal_baseline import FEATURE_COLS


def test_anchor_baseline_is_frozen_after_calibration_period():
    daily = pd.DataFrame({"user": ["A"] * 5, "day": pd.date_range("2010-01-01", periods=5).date})
    for column in FEATURE_COLS:
        daily[column] = [1, 2, 3, 4, 100] if column == "logon_count" else 0

    result = add_anchor_baseline(daily, anchor_days=3)
    assert result["logon_count_anchor_mean"].iloc[:3].isna().all()
    assert result["logon_count_anchor_mean"].iloc[3] == 2
    assert result["logon_count_anchor_mean"].iloc[4] == 2
