import pandas as pd

from src.baselines.personal_baseline import (
    FEATURE_COLS,
    add_novelty_flags,
    add_personal_baseline,
    merge_daily_features,
)


def make_daily(logon_counts):
    daily = pd.DataFrame({
        "user": ["A"] * len(logon_counts),
        "day": pd.date_range("2010-01-01", periods=len(logon_counts)).date,
    })
    for col in FEATURE_COLS:
        daily[col] = 0
    daily["logon_count"] = logon_counts
    return daily


def test_baseline_never_uses_current_or_future_day():
    daily = make_daily([1, 1, 1, 1, 100])

    result = add_personal_baseline(daily, window=4)
    day5_baseline = result.iloc[4]["logon_count_baseline_mean"]

    assert day5_baseline == 1.0


def test_cold_start_produces_nan_not_zero():
    daily = make_daily([3, 4])

    result = add_personal_baseline(daily)

    assert result["logon_count_baseline_mean"].isna().all()


def test_missing_first_logon_hour_is_carried_forward_not_zero():
    days = pd.date_range("2010-01-01", periods=2).date
    logon = pd.DataFrame({
        "user": ["A"], "day": [days[0]], "logon_count": [1], "after_hours_logon_count": [0],
        "first_logon_hour": [9], "last_logon_hour": [9], "distinct_pcs": [1],
    })
    device = pd.DataFrame(columns=["user", "day", "device_event_count", "usb_connect_count", "after_hours_usb_count"])
    files = pd.DataFrame({
        "user": ["A", "A"], "day": days, "file_event_count": [2, 3],
        "unique_filenames": [2, 3], "after_hours_file_count": [0, 1],
    })
    email = pd.DataFrame(columns=["user", "day", "email_count", "total_attachments", "avg_size", "external_recipient_ratio"])

    merged = merge_daily_features(logon, device, files, email)

    assert merged["first_logon_hour"].tolist() == [9, 9]
    assert merged["logon_count"].tolist() == [1, 0]


def test_first_usb_ever_flags_only_the_first_usb_day():
    daily = make_daily([1, 1, 1, 1, 1])
    daily["usb_connect_count"] = [0, 0, 2, 0, 3]

    result = add_novelty_flags(daily)

    assert result["first_usb_ever"].tolist() == [0, 0, 1, 0, 0]
