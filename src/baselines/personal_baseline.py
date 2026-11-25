import pandas as pd

FEATURE_COLS = [
    "logon_count",
    "after_hours_logon_count",
    "first_logon_hour",
    "distinct_pcs",
    "usb_connect_count",
    "after_hours_usb_count",
    "device_event_count",
    "file_event_count",
    "unique_filenames",
    "after_hours_file_count",
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
    "after_hours_usb_count": "After-hours USB",
    "device_event_count": "Device activity",
    "file_event_count": "File activity",
    "unique_filenames": "Unique files",
    "after_hours_file_count": "After-hours file activity",
    "email_count": "Email activity",
    "total_attachments": "Email attachments",
    "external_recipient_ratio": "External recipients",
}

NOVELTY_COLS = ["first_usb_ever"]
NOVELTY_LABELS = {"first_usb_ever": "First-ever USB use"}

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

    merged[FEATURE_COLS] = merged[FEATURE_COLS].fillna(0).astype(float)
    return add_novelty_flags(merged)


def add_novelty_flags(daily: pd.DataFrame) -> pd.DataFrame:
    """Flag behaviour the user has never shown before.

    first_usb_ever is 1 on the first day a user ever connects a USB drive.
    It only counts earlier days (cumulative sum minus today), so it never
    looks into the future. A z-score cannot capture this well: a user with no
    USB history has a flat baseline, so the flag is passed to the model as is.
    """
    daily = daily.sort_values(["user", "day"]).copy()
    usb_before_today = daily.groupby("user")["usb_connect_count"].cumsum() - daily["usb_connect_count"]
    daily["first_usb_ever"] = ((usb_before_today == 0) & (daily["usb_connect_count"] > 0)).astype(int)
    return daily


def add_personal_baseline(daily: pd.DataFrame, window: int = BASELINE_WINDOW) -> pd.DataFrame:
    daily = daily.sort_values(["user", "day"]).copy()
    grouped = daily.groupby("user")

    for col in FEATURE_COLS:
        shifted = grouped[col].shift(1)
        rolling = shifted.groupby(daily["user"]).rolling(window, min_periods=MIN_HISTORY_DAYS)
        daily[f"{col}_baseline_mean"] = rolling.mean().reset_index(level=0, drop=True)
        daily[f"{col}_baseline_std"] = rolling.std().reset_index(level=0, drop=True)

    return daily
