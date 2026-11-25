import pandas as pd

FEATURE_COLS = [
    "logon_count",
    "after_hours_logon_count",
    "first_logon_hour",
    "distinct_pcs",
    "usb_connect_count",
    "device_event_count",
    "file_event_count",
    "unique_filenames",
    "email_count",
    "total_attachments",
    "external_recipient_ratio",
]

FEATURE_LABELS = {
    "logon_count": "Login frequency",
    "after_hours_logon_count": "After-hours logins",
    "first_logon_hour": "First login hour",
    "distinct_pcs": "Distinct PCs used",
    "usb_connect_count": "USB activity",
    "device_event_count": "Device activity",
    "file_event_count": "File activity",
    "unique_filenames": "Unique files",
    "email_count": "Email activity",
    "total_attachments": "Email attachments",
    "external_recipient_ratio": "External recipients",
}

BASELINE_WINDOW = 14
MIN_HISTORY_DAYS = 3


def merge_daily_features(lf, df_, ff, ef) -> pd.DataFrame:
    """Join the four daily feature tables into one row per user per day.

    A day with file or email activity but no logon has no "first logon hour".
    Filling it with 0 would look like a midnight login, so the user's previous
    known value is carried forward instead (this only looks backwards in time).
    """
    merged = lf.merge(df_, on=["user", "day"], how="outer")
    merged = merged.merge(ff, on=["user", "day"], how="outer")
    merged = merged.merge(ef, on=["user", "day"], how="outer")
    merged = merged.sort_values(["user", "day"]).reset_index(drop=True)

    merged["first_logon_hour"] = merged.groupby("user")["first_logon_hour"].ffill()

    merged[FEATURE_COLS] = merged[FEATURE_COLS].fillna(0)
    return merged


def add_personal_baseline(daily: pd.DataFrame, window: int = BASELINE_WINDOW) -> pd.DataFrame:
    daily = daily.sort_values(["user", "day"]).copy()
    grouped = daily.groupby("user")

    for col in FEATURE_COLS:
        shifted = grouped[col].shift(1)
        rolling = shifted.groupby(daily["user"]).rolling(window, min_periods=MIN_HISTORY_DAYS)
        daily[f"{col}_baseline_mean"] = rolling.mean().reset_index(level=0, drop=True)
        daily[f"{col}_baseline_std"] = rolling.std().reset_index(level=0, drop=True)

    return daily
