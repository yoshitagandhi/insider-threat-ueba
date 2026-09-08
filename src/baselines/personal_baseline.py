import pandas as pd

FEATURE_COLS = [
    "logon_count",
    "after_hours_logon_count",
    "usb_connect_count",
    "device_event_count",
    "file_event_count",
    "unique_filenames",
    "email_count",
    "total_attachments",
    "external_recipient_ratio",
]

BASELINE_WINDOW = 14


def merge_daily_features(lf, df_, ff, ef) -> pd.DataFrame:
    merged = lf.merge(df_, on=["user", "day"], how="outer")
    merged = merged.merge(ff, on=["user", "day"], how="outer")
    merged = merged.merge(ef, on=["user", "day"], how="outer")
    merged[FEATURE_COLS] = merged[FEATURE_COLS].fillna(0)
    return merged.sort_values(["user", "day"]).reset_index(drop=True)


def add_personal_baseline(daily: pd.DataFrame, window: int = BASELINE_WINDOW) -> pd.DataFrame:
    daily = daily.sort_values(["user", "day"]).copy()
    grouped = daily.groupby("user")

    for col in FEATURE_COLS:
        shifted = grouped[col].shift(1)
        daily[f"{col}_baseline_mean"] = shifted.groupby(daily["user"]).rolling(window, min_periods=3).mean().reset_index(level=0, drop=True)
        daily[f"{col}_baseline_std"] = shifted.groupby(daily["user"]).rolling(window, min_periods=3).std().reset_index(level=0, drop=True)

    return daily