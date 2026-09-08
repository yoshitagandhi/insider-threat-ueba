import pandas as pd
from src.baselines.personal_baseline import add_personal_baseline


def test_baseline_never_uses_current_or_future_day():
    daily = pd.DataFrame({
        "user": ["A"] * 5,
        "day": pd.date_range("2010-01-01", periods=5).date,
        "logon_count": [1, 1, 1, 1, 100],  # spike only on day 5
    })
    for col in ["after_hours_logon_count", "usb_connect_count", "device_event_count",
                "file_event_count", "unique_filenames", "email_count",
                "total_attachments", "external_recipient_ratio"]:
        daily[col] = 0

    result = add_personal_baseline(daily, window=4)
    day5_baseline = result[result["day"] == daily["day"].iloc[4]].iloc[0]["logon_count_baseline_mean"]

    # day 5's baseline must be built ONLY from days 1-4 (all value 1), never seeing the spike itself
    assert day5_baseline == 1.0


def test_cold_start_produces_nan_not_zero():
    daily = pd.DataFrame({
        "user": ["A", "A"],
        "day": pd.date_range("2010-01-01", periods=2).date,
        "logon_count": [3, 4],
    })
    for col in ["after_hours_logon_count", "usb_connect_count", "device_event_count",
                "file_event_count", "unique_filenames", "email_count",
                "total_attachments", "external_recipient_ratio"]:
        daily[col] = 0

    result = add_personal_baseline(daily)
    # min_periods=3 means day 1 and day 2 (a brand-new user) should have NO baseline yet
    assert result["logon_count_baseline_mean"].isna().all()