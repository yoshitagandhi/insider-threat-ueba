"""Pandas helpers that turn the scored file into the numbers each card shows."""

import pandas as pd

from src.baselines.personal_baseline import FEATURE_COLS, FEATURE_LABELS
from src.models.combined import add_alert_source, add_combined_score, add_risk_score
from src.utils.config import ALERT_PERCENTILE

SOURCE_SHORT = {"rule": "Rule", "today's behaviour": "Today", "7-day carry-over": "Carry-over"}

RADAR_AXES = [
    ("Logins", "logon_count"),
    ("After-hours", "after_hours_logon_count"),
    ("USB", "usb_connect_count"),
    ("Devices", "device_event_count"),
    ("Files", "file_event_count"),
    ("Email", "email_count"),
]


def prepare(data: pd.DataFrame) -> pd.DataFrame:
    """Add the combined score, alert source and risk score if the file does not have them yet."""
    data = data.copy()
    if "split" in data.columns and "combined_score" not in data.columns and "rule_alert" in data.columns:
        data = add_combined_score(data)
    if "combined_score" in data.columns and "alert_source" not in data.columns:
        data = add_alert_source(data)
    if "alert_source" not in data.columns:
        data["alert_source"] = "today's behaviour"
    data = add_risk_score(data)
    data["day"] = pd.to_datetime(data["day"])
    return data


def threshold_for(data: pd.DataFrame, column: str) -> float:
    """The alert line: the 99th percentile of the training period's scores."""
    source = data[data["split"] == "train"] if "split" in data.columns else data
    return float(source[column].quantile(ALERT_PERCENTILE / 100))


def apply_dates(data: pd.DataFrame, scope: str, custom: tuple | None) -> pd.DataFrame:
    end = data["day"].max()
    if scope == "Last 30 days":
        return data[data["day"] > end - pd.Timedelta(days=30)]
    if scope == "Last 90 days":
        return data[data["day"] > end - pd.Timedelta(days=90)]
    if scope == "Custom" and custom and len(custom) == 2:
        start, stop = pd.Timestamp(custom[0]), pd.Timestamp(custom[1])
        return data[(data["day"] >= start) & (data["day"] <= stop)]
    return data


def apply_review(data: pd.DataFrame, review: str, threshold: float) -> pd.DataFrame:
    if review == "Needs review":
        return data[data["risk_score"] >= threshold]
    if review == "Below the line":
        return data[data["risk_score"] < threshold]
    return data


def latest_by_user(data: pd.DataFrame) -> pd.DataFrame:
    return data.sort_values("day").groupby("user").tail(1)


def user_peaks(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    peaks = data.loc[data.groupby("user")["risk_score"].idxmax()]
    return peaks.sort_values(["risk_score", "if_anomaly_score"], ascending=False)


def largest_driver(row: pd.Series) -> tuple[str, float]:
    """The feature whose z-score is furthest from zero on this day."""
    best_col, best_z = FEATURE_COLS[0], 0.0
    for col in FEATURE_COLS:
        z = row.get(f"{col}_zscore")
        if pd.notna(z) and abs(z) > abs(best_z):
            best_col, best_z = col, float(z)
    return FEATURE_LABELS[best_col], best_z


def trigger_text(row: pd.Series) -> str:
    if row.get("rule_alert", 0) == 1:
        return "First-ever USB use after hours"
    label, z = largest_driver(row)
    return f"{label} {z:+.1f}σ"


def short_source(row: pd.Series) -> str:
    return SOURCE_SHORT.get(row.get("alert_source", ""), "Today")


def month_labels(days: pd.Series, count: int = 7) -> list[str]:
    days = pd.Series(pd.to_datetime(days)).reset_index(drop=True)
    if days.empty:
        return []
    count = min(count, len(days))
    picks = [days.iloc[round(k * (len(days) - 1) / max(count - 1, 1))] for k in range(count)]
    span_days = (days.iloc[-1] - days.iloc[0]).days
    fmt = "%b %y" if span_days > 330 else ("%b" if span_days > 60 else "%d %b")
    return [d.strftime(fmt) for d in picks]


def risk_series(data: pd.DataFrame, period: str, threshold: float, column: str = "risk_score") -> pd.DataFrame:
    """Highest score per day, week or month, plus how many people were above the line."""
    freq = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}[period]
    grouped = data.set_index("day").groupby(pd.Grouper(freq=freq))
    out = pd.DataFrame({
        "value": grouped[column].max(),
        "above": grouped[column].apply(lambda s: int((s >= threshold).sum())),
    }).dropna().reset_index()
    return out


def volume_buckets(alerts: pd.DataFrame, start, end) -> tuple[list[tuple[int, int]], list, str]:
    """Alert counts per week (or month if the range is long), split into new and carry-over."""
    weeks = max(1, (pd.Timestamp(end) - pd.Timestamp(start)).days // 7)
    freq, name = ("W-MON", "week") if weeks <= 36 else ("MS", "month")
    alerts = alerts.copy()
    alerts["carry"] = alerts["alert_source"].eq("7-day carry-over")
    index = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end), freq=freq)
    if len(index) == 0:
        index = pd.DatetimeIndex([pd.Timestamp(start)])
    grouped = alerts.set_index("day").groupby(pd.Grouper(freq=freq))
    new = grouped["carry"].apply(lambda s: int((~s).sum())).reindex(index, fill_value=0)
    carry = grouped["carry"].apply(lambda s: int(s.sum())).reindex(index, fill_value=0)
    return list(zip(new.tolist(), carry.tolist())), list(index), name


def carry_bands(user_days: pd.DataFrame) -> list[tuple[int, int]]:
    """Index ranges of consecutive 7-day carry-over days, for shading the timeline."""
    flags = user_days["alert_source"].eq("7-day carry-over").tolist()
    bands, start = [], None
    for i, flag in enumerate(flags + [False]):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            bands.append((start, i - 1))
            start = None
    return bands


def radar_values(row: pd.Series) -> tuple[list[float], list[float], list[str]]:
    """Usual day (baseline mean) vs this day for six activities, scaled 0-1 per axis."""
    normal, today, labels = [], [], []
    for _, col in RADAR_AXES:
        base = row.get(f"{col}_baseline_mean")
        base = 0.0 if pd.isna(base) else float(base)
        now = float(row.get(col, 0) or 0)
        scale = max(base, now, 1.0)
        normal.append(max(base / scale, 0.04))
        today.append(max(now / scale, 0.04))
        labels.append(f"{base:.1f} → {now:.0f}")
    return normal, today, labels


def monthly_user(user_days: pd.DataFrame, threshold: float, months: int = 12) -> pd.DataFrame:
    grouped = user_days.set_index("day").groupby(pd.Grouper(freq="MS"))
    out = pd.DataFrame({
        "avg": grouped["risk_score"].mean(),
        "alerts": grouped["risk_score"].apply(lambda s: int((s >= threshold).sum())),
    }).dropna().reset_index()
    return out.tail(months)


def top_deviations(row: pd.Series, n: int = 6) -> list[tuple[str, float]]:
    items = []
    for col in FEATURE_COLS:
        z = row.get(f"{col}_zscore")
        if pd.notna(z):
            items.append((FEATURE_LABELS[col], float(z)))
    return sorted(items, key=lambda item: abs(item[1]), reverse=True)[:n]


def trigger_counts(alert_days: pd.DataFrame, top: int = 5) -> list[tuple[str, int]]:
    names = []
    for _, row in alert_days.iterrows():
        names.append("USB rule" if row.get("rule_alert", 0) == 1 else largest_driver(row)[0])
    counts = pd.Series(names).value_counts()
    return list(counts.head(top).items())


def why_lines(row: pd.Series, carry_days: int) -> list[str]:
    """Plain-language reasons for the worst day, strongest first."""
    lines = []
    day = row["day"].strftime("%d %b")
    if row.get("rule_alert", 0) == 1:
        lines.append(f"<b>Plugged in a USB drive for the first time ever, after working hours</b> on {day}. This matches a known data-theft pattern.")
    shown = 0
    for col in sorted(FEATURE_COLS, key=lambda c: -abs(row.get(f"{c}_zscore", 0) or 0)):
        z = row.get(f"{col}_zscore")
        if pd.isna(z) or z <= 1.5 or shown == 3:
            continue
        base = row.get(f"{col}_baseline_mean")
        base = 0.0 if pd.isna(base) else float(base)
        now = row.get(col, 0)
        value = f"{now:.0%}" if col == "external_recipient_ratio" else f"{now:.0f}"
        usual = f"{base:.0%}" if col == "external_recipient_ratio" else f"{base:.1f}"
        lines.append(f"<b>{FEATURE_LABELS[col]}: {value} that day</b>, when their usual is {usual} ({z:+.1f}σ).")
        shown += 1
    if carry_days:
        lines.append(f"<b>Stayed on the list for {carry_days} more day{'s' if carry_days != 1 else ''}</b> afterwards because of the 7-day carry-over.")
    if not lines:
        lines.append("No single behaviour stood out strongly. The score comes from several small changes at once.")
    return lines


def evidence_table(user_days: pd.DataFrame, threshold: float, n: int = 12) -> pd.DataFrame:
    top = user_days.nlargest(min(n, len(user_days)), "risk_score").copy()
    table = pd.DataFrame({
        "Date": top["day"].dt.strftime("%d %b %Y"),
        "State": top["risk_score"].ge(threshold).map({True: "Needs review", False: "Below the line"}),
        "Source": top.apply(short_source, axis=1),
        "Risk": top["risk_score"].round(3),
        "Why it was flagged": top["top_reasons"] if "top_reasons" in top.columns else top.apply(trigger_text, axis=1),
        "Logins": top["logon_count"].astype(int),
        "Files": top["file_event_count"].astype(int),
        "USB": top["usb_connect_count"].astype(int),
        "Emails": top["email_count"].astype(int),
    })
    return table
