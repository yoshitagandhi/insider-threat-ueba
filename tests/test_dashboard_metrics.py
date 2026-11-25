import pandas as pd

from dashboard import metrics
from dashboard.svg_charts import nice_ticks
from src.baselines.personal_baseline import FEATURE_COLS


def make_day(**values):
    row = {"day": pd.Timestamp("2010-07-20"), "rule_alert": 0}
    for col in FEATURE_COLS:
        row[col] = 0
        row[f"{col}_baseline_mean"] = 0.0
        row[f"{col}_zscore"] = 0.0
    row.update(values)
    return pd.Series(row)


def test_carry_bands_groups_consecutive_carry_over_days():
    days = pd.DataFrame({"alert_source": ["today's behaviour", "7-day carry-over", "7-day carry-over",
                                          "today's behaviour", "7-day carry-over"]})
    assert metrics.carry_bands(days) == [(1, 2), (4, 4)]


def test_risk_series_counts_people_above_the_line():
    data = pd.DataFrame({
        "day": pd.to_datetime(["2010-01-04", "2010-01-04", "2010-01-05"]),
        "risk_score": [0.999, 0.5, 0.998],
    })
    series = metrics.risk_series(data, "Daily", threshold=0.99)
    assert series["above"].tolist() == [1, 1]
    assert series["value"].tolist() == [0.999, 0.998]


def test_radar_values_are_scaled_per_axis():
    row = make_day(file_event_count=14, file_event_count_baseline_mean=0.0, logon_count=2, logon_count_baseline_mean=1.0)
    normal, today, labels = metrics.radar_values(row)
    files = [axis for axis, _ in metrics.RADAR_AXES].index("Files")
    logins = [axis for axis, _ in metrics.RADAR_AXES].index("Logins")
    assert today[files] == 1.0
    assert normal[files] == 0.04
    assert normal[logins] == 0.5
    assert labels[files] == "0.0 → 14"


def test_why_lines_mentions_the_rule_first():
    row = make_day(rule_alert=1, usb_connect_count=9, usb_connect_count_zscore=9.0)
    lines = metrics.why_lines(row, carry_days=3)
    assert "first time ever" in lines[0]
    assert "USB activity" in lines[1]
    assert "3 more days" in lines[-1]


def test_nice_ticks_round_the_axis():
    low, high, ticks = nice_ticks(0.19, 1.0)
    assert low == 0.0
    assert high == 1.0
    assert ticks == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_svgs_are_turned_into_images_for_st_html():
    import base64

    from dashboard.svg_charts import gauge, svgs_to_images

    html = f'<div class="card">{gauge(0.5, 1.0, "0.500", "")}</div>'
    converted = svgs_to_images(html)

    assert "<svg" not in converted
    assert 'src="data:image/svg+xml;base64,' in converted
    encoded = converted.split("base64,")[1].split('"')[0]
    svg = base64.b64decode(encoded).decode("utf-8")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "<style>" in svg
