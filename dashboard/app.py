"""Security operations dashboard UI rebuilt from the supplied visual reference.

The analytical/data layer is intentionally preserved from the existing app:
- scored_daily.parquet loading
- Isolation Forest anomaly scores and threshold
- user peak selection
- behavioral deviation calculations
- deep investigation/evidence table

Only the presentation layer is rebuilt around the supplied screenshots.
"""

import sys
from pathlib import Path
import base64

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import altair as alt
import pandas as pd
import streamlit as st

from src.baselines.personal_baseline import FEATURE_LABELS
from src.utils.config import ALERT_PERCENTILE, DATA_PROCESSED_DIR


BASELINE_FEATURES = ["logon_count", "file_event_count", "usb_connect_count", "email_count"]

st.set_page_config(page_title="Kestrel", page_icon=":material/shield:", layout="wide", initial_sidebar_state="collapsed")

st.html(
    """
    <style>
      :root {
        --ink: #17212b;
        --muted: #607482;
        --navy: #2f4157;
        --teal: #1f8195;
        --teal-dark: #116579;
        --blue-1: #dcecf2;
        --blue-2: #b9dce8;
        --blue-3: #82c0d1;
        --blue-4: #4da2ba;
        --blue-5: #1f7188;
        --line: #cbdde5;
        --page: #f4f7f9;
        --card: #ffffff;
        --hero: #e5f3f7;
      }

      .stApp { background: var(--page); color: var(--ink); }
      .block-container {
        width: 100%;
        max-width: none;
        padding: .18rem 1.35rem 2.75rem;
      }
      [data-testid="stHeader"] { background: transparent; }
      [data-testid="stToolbar"] { visibility: hidden; height: 0; }
      .stMarkdown p { margin-bottom: 0; font-size: 1.02rem; }

      /* Minimal product masthead — typography carries the Kestrel identity. */
      .topbar {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 76px;
        padding: 0;
        margin-bottom: 0;
      }
      .masthead-divider {
        width: 100%;
        height: 1px;
        background: #c6d8e0;
        margin: 0 0 .30rem;
      }
      .brand-lockup {
        display: flex;
        align-items: center;
        gap: 0.35rem;
       transform: translateX(-25px);}
      .brand-logo {
        width: 112px;
        height: 112px;
        flex: 0 0 58px;
        object-fit: contain;
        display: block;
      }
      .page-title {
        color: #142534;
        font-family: "Bitec", Inter, "Söhne", "Aktiv Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: clamp(2.45rem, 2.15rem + .95vw, 3.25rem);
        line-height: .98;
        font-weight: 700;
        letter-spacing: -0.025em;
        margin: 0;
      }
      .brand-subtitle {
        color: #617783;
        font-size: clamp(.74rem, .68rem + .12vw, .84rem);
        line-height: 1.25;
        font-weight: 680;
        letter-spacing: .035em;
        margin-top: .24rem;
        text-transform: uppercase;
      }

      /* Filter control/panel */
      [data-testid="stPopover"] > button {
        width: 100%;
        height: 43px;
        border: 1px solid #c9dbe4;
        border-radius: 13px;
        background: #ffffff;
        color: #304b62;
        font-size: clamp(.62rem, .57rem + .10vw, .74rem);
        font-weight: 780;
        letter-spacing: .055em;
        padding: 0 .65rem;
        white-space: nowrap;
      }
      [data-testid="stPopover"] > button:hover { border-color: var(--teal); color: var(--teal-dark); background:#f8fbfc; }
      [data-testid="stPopoverBody"] {
        width: min(700px, calc(100vw - 32px)) !important;
        border-radius: 20px !important;
        border: 0 !important;
        background: #f7fafb !important;
        box-shadow: 0 12px 30px rgba(35,58,73,.16) !important;
      }
      [data-testid="stPopoverBody"] label,
      [data-testid="stPopoverBody"] [data-testid="stWidgetLabel"] p {
        color: #3e566a !important;
        font-size: .77rem !important;
        font-weight: 600 !important;
      }
      [data-testid="stPopoverBody"] [data-baseweb="select"] > div {
        background: #e8f1f5;
        border: 1px solid #c3d7e1;
        border-radius: 12px;
      }
      [data-testid="stPopoverBody"] [data-baseweb="select"] * { color: #3b5266; }
      [data-testid="stPopoverBody"] .stSegmentedControl {
        border-radius: 12px;
        overflow: hidden;
      }
      [data-testid="stPopoverBody"] .stSegmentedControl button {
        color: #344d63;
        background: #f5f8fa;
        border-color: #c3d7e1;
        font-size: .76rem;
      }
      [data-testid="stPopoverBody"] .stSegmentedControl button[aria-pressed="true"] {
        background: #e0ebf0;
        color: #263e53;
      }

      /* Main reference row */
      .hero {
        background: var(--hero);
        border-radius: 20px;
        overflow: hidden;
        padding: 1.12rem 1.3rem .98rem;
      }
      .hero-head {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
      }
      .hero-title { color: #2d4c5d; font-size: clamp(.99rem, .84rem + .25vw, 1.22rem); font-weight: 760; }
      .hero-meta { color: #587180; font-size: clamp(.76rem, .68rem + .16vw, .92rem); margin-top: .3rem; }
      .hero-delta {
        background: #ffffff;
        color: #11677d;
        border-radius: 999px;
        padding: .34rem .72rem;
        font-size: .75rem;
        font-weight: 790;
        white-space: nowrap;
      }
      .hero-score {
        color: var(--ink);
        font-size: clamp(2.05rem, 1.75rem + .7vw, 2.85rem);
        font-weight: 790;
        line-height: 1;
        margin: .08rem 0 .25rem;
      }
      .hero-chart { margin: .35rem 0 .55rem; }
      .metric-tile {
        background: #fff;
        border-radius: 15px;
        padding: .9rem 1rem .82rem;
        min-height: 82px;
      }
      .metric-label { color: #587180; font-size: clamp(.65rem, .58rem + .15vw, .82rem); font-weight: 760; letter-spacing: .055em; }
      .metric-value { color: #1a2832; font-size: clamp(1rem, .9rem + .2vw, 1.25rem); font-weight: 790; margin-top: .22rem; }
      .metric-value.alert { color: #b63f3b; }

      .side-title { color: var(--ink); font-size: clamp(.98rem, .85rem + .22vw, 1.2rem); font-weight: 790; }
      .side-sub { color: #697b86; font-size: clamp(.72rem, .65rem + .14vw, .88rem); margin: .28rem 0 .85rem; }
      .risk-row {
        display: grid;
        grid-template-columns: 78px 1fr;
        gap: .52rem;
        align-items: center;
        min-height: 54px;
      }
      .risk-name { color: #1c2832; font-size: clamp(.75rem, .68rem + .14vw, .9rem); font-weight: 750; }
      .risk-track { display: flex; gap: 3px; align-items: stretch; height: 32px; }
      .risk-seg { flex: 1; min-width: 0; border-radius: 6px; background: var(--blue-1); }
      .risk-seg.s2 { background: var(--blue-2); }
      .risk-seg.s3 { background: var(--blue-3); }
      .risk-seg.s4 { background: var(--blue-4); }
      .risk-seg.s5 { background: var(--blue-5); }
      .risk-score { color: white; font-size: clamp(.69rem, .62rem + .12vw, .82rem); font-weight: 790; display: flex; align-items: center; justify-content: center; }

      .lower-title {
        color: var(--ink);
        font-size: clamp(.98rem, .85rem + .22vw, 1.2rem);
        font-weight: 790;
        margin-bottom: .62rem;
      }
      .table-head, .table-row {
        display: grid;
        grid-template-columns: 1fr 1.45fr .55fr;
        gap: 1rem;
        align-items: center;
      }
      .table-head {
        color: #667984;
        font-size: clamp(.65rem, .58rem + .13vw, .8rem);
        font-weight: 760;
        padding: 0 .1rem .42rem;
      }
      .table-row {
        color: #1b2730;
        font-size: clamp(.81rem, .73rem + .16vw, .96rem);
        min-height: 52px;
        border-top: 1px solid #d8e3e8;
      }
      .table-row span:first-child { font-weight: 560; }
      .table-row span:last-child { font-variant-numeric: tabular-nums; }

      .case-titlebar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: .58rem;
      }
      .week-label { color: #667984; font-size: clamp(.65rem, .58rem + .13vw, .8rem); font-weight: 760; }
      .case-card {
        background: #eef6f8;
        border-radius: 15px;
        padding: .78rem .88rem;
        margin-bottom: .55rem;
      }
      .case-top { display: flex; justify-content: space-between; align-items: center; }
      .case-user { color: #12677b; font-size: .75rem; font-weight: 790; }
      .case-pill { border-radius: 999px; padding: .2rem .55rem; font-size: clamp(.63rem, .57rem + .12vw, .78rem); font-weight: 790; }
      .case-high { color: #c24743; background: #fbe6e4; }
      .case-low { color: #5d7c2a; background: #e8f1dc; }
      .case-name { color: #1a2832; font-size: clamp(.82rem, .75rem + .15vw, .98rem); font-weight: 730; margin-top: .58rem; }
      .case-note { color: #687b86; font-size: clamp(.71rem, .64rem + .13vw, .86rem); margin-top: .28rem; }
      .case-action {
        background: #258397;
        color: #fff;
        border-radius: 11px;
        text-align: center;
        font-size: clamp(.8rem, .72rem + .15vw, .95rem);
        font-weight: 770;
        padding: .64rem;
        margin-top: .62rem;
      }

      /* Existing analytical content, presented as secondary investigation detail. */
      .detail-rule { height: 2px; background: #c7d9e1; margin: 1.45rem 0 .85rem; }
      .detail-label { color: #4e6d7c; font-size: clamp(.78rem, .70rem + .16vw, .94rem); font-weight: 820; letter-spacing: .105em; }
      /* The profile wrapper is layout-only; each section below is its own card. */
      .detail-card { background:transparent; border:0; border-radius:0; padding:0; }
      .detail-grid {
        display:grid;
        grid-template-columns:1.25fr .9fr 1.05fr;
        gap:1rem;
        align-items:stretch;
      }
      .detail-identity, .detail-score, .detail-state {
        background:#fff;
        border:1px solid #d6e2e8;
        border-radius:16px;
        min-height:154px;
        padding:1.35rem 1.45rem;
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:flex-start;
        box-sizing:border-box;
      }
      .detail-identity { justify-content:center; }
      .detail-score { justify-content:center; }
      .detail-state { justify-content:center; }
      .profile-meta { color:#5f7380; font-size:clamp(.82rem, .73rem + .16vw, .98rem); line-height:1.35; margin-top:.38rem; }
      .detail-score .detail-label { margin-bottom:.28rem; }
      .detail-score-value { color:#17212b; font-size:clamp(1.7rem, 1.45rem + .55vw, 2.35rem); line-height:1.05; font-weight:790; }
      .detail-action-title { color:#17212b; font-size:clamp(.78rem, .7rem + .14vw, .92rem); line-height:1.2; font-weight:780; letter-spacing:.035em; margin-top:.62rem; }
      .profile-id { color:#243746; font-size:clamp(1.48rem, 1.25rem + .5vw, 2rem); font-weight:790; }
      .risk-label,.neutral-label { display:inline-block; border-radius:999px; padding:.23rem .58rem; font-size:.64rem; font-weight:790; }
      .risk-label { background:#fbe6e4; color:#bd4843; }
      .neutral-label { background:#e7eef2; color:#496173; }
      .baseline-profile { background:#e9f3f6; border-radius:14px; padding:.9rem 1rem; }
      .baseline-head,.baseline-row { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:1rem; align-items:center; }
      .baseline-head { color:#5e7683; font-size:.72rem; font-weight:770; letter-spacing:.06em; padding-bottom:.45rem; }
      .baseline-row { border-top:1px solid #cfdee5; color:#344e60; font-size:.88rem; padding:.56rem 0; }
      .baseline-row .signal { font-weight:720; }
      .baseline-row .current { color:#17212b; font-weight:790; }

      .review-panel {
        background:#e9f3f6;
        border-radius:14px;
        padding:.75rem .95rem;
      }
      .review-panel .table-head { color:#5e7683; font-size:.72rem; padding-bottom:.48rem; }
      .review-panel .table-row { font-size:.88rem; min-height:48px; border-top-color:#cfdee5; }
      [data-testid="stExpander"] { border:1px solid #d1e0e6; border-radius:13px; background:#fff; }

      @media (max-width: 760px) {
        .block-container { padding-left:.75rem; padding-right:.75rem; }
        .page-title { font-size:2.05rem; }
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) { align-items:center; gap:.35rem; }
        .table-head,.table-row { grid-template-columns:.9fr 1.25fr .55fr; gap:.5rem; }
        .detail-grid { grid-template-columns:1fr; }
      }
    </style>
    """
)


@st.cache_data(show_spinner="Loading behavioral signals…")
def load_scored_data(path: str) -> pd.DataFrame:
    data = pd.read_parquet(path).copy()
    data["day"] = pd.to_datetime(data["day"])
    return data


def largest_driver(row) -> tuple[str, float]:
    """Return the strongest behavioural driver for a pandas Series or
    a namedtuple returned by DataFrame.itertuples()."""
    def get_value(column: str, default=0):
        if hasattr(row, "get"):
            value = row.get(column, default)
        else:
            value = getattr(row, column, default)
        return default if pd.isna(value) else value

    values = {
        label: abs(float(get_value(f"{feature}_zscore", 0) or 0))
        for feature, label in FEATURE_LABELS.items()
    }
    return max(values.items(), key=lambda item: item[1])


def user_peaks(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    peaks = data.loc[data.groupby("user")["if_anomaly_score"].idxmax()].copy()
    return peaks.sort_values("if_anomaly_score", ascending=False)


def apply_scope(data: pd.DataFrame, scope: str, custom_range: tuple | list | None) -> pd.DataFrame:
    if scope == "Last 30 days":
        start = data["day"].max() - pd.DateOffset(days=29)
        return data[data["day"] >= start]
    if scope == "Last 90 days":
        start = data["day"].max() - pd.DateOffset(days=89)
        return data[data["day"] >= start]
    if scope == "Custom range" and custom_range and len(custom_range) == 2:
        start, end = pd.Timestamp(custom_range[0]), pd.Timestamp(custom_range[1])
        return data[(data["day"] >= start) & (data["day"] <= end)]
    return data


def trend_state(daily: pd.DataFrame) -> str:
    if len(daily) < 8:
        return "LIMITED HISTORY"
    window = max(3, min(14, len(daily) // 5))
    early = float(daily["if_anomaly_score"].iloc[:window].median())
    recent = float(daily["if_anomaly_score"].iloc[-window:].median())
    if early and recent > early * 1.15:
        return "INCREASING"
    if early and recent < early * 0.85:
        return "DECREASING"
    return "STABLE"


def line_chart(daily: pd.DataFrame, threshold: float) -> alt.Chart:
    """Restrained hero trend matching the reference rather than a report chart."""
    base = alt.Chart(daily).encode(
        x=alt.X("day:T", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False, grid=False)),
        y=alt.Y("if_anomaly_score:Q", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False, grid=False)),
        tooltip=[
            alt.Tooltip("day:T", title="Date", format="%d %b %Y"),
            alt.Tooltip("user:N", title="User"),
            alt.Tooltip("if_anomaly_score:Q", title="Anomaly score", format=".3f"),
            alt.Tooltip("primary_trigger:N", title="Primary trigger"),
        ],
    )
    area = base.mark_area(color="#c7e1e8", opacity=.82, line=False)
    line = base.mark_line(color="#177b91", strokeWidth=2.35)
    points = base.transform_filter(alt.datum.if_anomaly_score >= threshold).mark_point(color="#177b91", size=42)
    return (area + line + points).properties(height=220).configure_view(stroke=None)


def section_label(text: str) -> None:
    st.markdown(f'<div class="detail-rule"></div><div class="detail-label">{text}</div>', unsafe_allow_html=True)


data_path = DATA_PROCESSED_DIR / "scored_daily.parquet"
if not data_path.exists():
    st.error("Scored data is not available yet. Run the pipeline first: `python -m src.pipeline`", icon=":material/error:")
    st.stop()
try:
    scored = load_scored_data(str(data_path))
except (OSError, ValueError) as error:
    st.error(f"Could not load scored data: {error}", icon=":material/error:")
    st.stop()

if "split" in scored.columns:
    threshold_source = scored[scored["split"] == "train"]
else:
    threshold_source = scored
threshold = float(threshold_source["if_anomaly_score"].quantile(ALERT_PERCENTILE / 100))

header_col, filter_col = st.columns([7.35, 2.65], vertical_alignment="center")
with header_col:
    st.markdown(
        '<div class="topbar"><div class="brand-lockup"><img class="brand-logo" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABDgAAAQ4CAYAAADsEGyPAAAWfmNhQlgAABZ+anVtYgAAAB5qdW1kYzJwYQARABCAAACqADibcQNjMnBhAAAAFlhqdW1iAAAAR2p1bWRjMm1hABEAEIAAAKoAOJtxA3VybjpjMnBhOjBhNzc1OTk2LTIzMjQtNDhhYS05ZDkzLTllNmExNjg4NDU0YgAAAAOTanVtYgAAAClqdW1kYzJhcwARABCAAACqADibcQNjMnBhLmFzc2VydGlvbnMAAAAAuGp1bWIAAABEanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5pbmdyZWRpZW50LnYzAAAAABhjMnNon6VODFoV8Ol/TJgn+hst7wAAAGxjYm9yo2lkYzpmb3JtYXRpaW1hZ2UvcG5namluc3RhbmNlSUR4LHhtcDppaWQ6ZjQ5M2UxZDItYTE1Zi00NjRiLWE5YmMtN2E5Y2E4ODU0NTZhbHJlbGF0aW9uc2hpcGhwYXJlbnRPZgAAAeJqdW1iAAAAQWp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuYWN0aW9ucy52MgAAAAAYYzJzaH2aD1TfhPwKMfW5sv+J/PQAAAGZY2JvcqJnYWN0aW9uc4KiZmFjdGlvbmtjMnBhLm9wZW5lZGpwYXJhbWV0ZXJzoWtpbmdyZWRpZW50c4GiY3VybHgtc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5pbmdyZWRpZW50LnYzZGhhc2hYID6tEQMODMRltntVejKfn4Fsg3X34ceCO3pEv7aIza5OpGZhY3Rpb254HWNvbS5hbnRocm9waWMuY2xhdWRlLnByb3ZpZGVkanBhcmFtZXRlcnOheB9jb20uYW50aHJvcGljLm9yaWdpbi1jb25maWRlbmNlZ3Vua25vd25rZGVzY3JpcHRpb254ZkNsYXVkZSBwcm92aWRlZCB0aGlzIGZpbGUgYXQgdGhlIHJlcXVlc3Qgb2YgYSB1c2VyIGFuZCBtYXkgaGF2ZSBjcmVhdGVkIG9yIG1vZGlmaWVkIHRoZSBmaWxlIGNvbnRlbnRzLm1zb2Z0d2FyZUFnZW50oWRuYW1lZkNsYXVkZXJhbGxBY3Rpb25zSW5jbHVkZWT1AAAAyGp1bWIAAABAanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5oYXNoLmRhdGEAAAAAGGMyc2g8y0uHNUCZaNqyldedimdbAAAAgGNib3KlY2FsZ2ZzaGEyNTZjcGFkTQAAAAAAAAAAAAAAAABkaGFzaFgg/KXkp6grKbi3oUObetrReprdxRkw3MTFbte1NCHQPXFkbmFtZW5qdW1iZiBtYW5pZmVzdGpleGNsdXNpb25zgaJlc3RhcnQYIWZsZW5ndGgZFooAAAI+anVtYgAAACdqdW1kYzJjbAARABCAAACqADibcQNjMnBhLmNsYWltLnYyAAAAAg9jYm9ypWNhbGdmc2hhMjU2aXNpZ25hdHVyZXhNc2VsZiNqdW1iZj0vYzJwYS91cm46YzJwYTowYTc3NTk5Ni0yMzI0LTQ4YWEtOWQ5My05ZTZhMTY4ODQ1NGIvYzJwYS5zaWduYXR1cmVqaW5zdGFuY2VJRHgseG1wOmlpZDo5MDE0NTBjMC0xMmJjLTQzNDctOTA2My01NDU2OWRkMWZjOTJyY3JlYXRlZF9hc3NlcnRpb25zg6JjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggPq0RAw4MxGW2e1V6Mp+fgWyDdffhx4I7ekS/tojNrk6iY3VybHgqc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5hY3Rpb25zLnYyZGhhc2hYIN2ZeyWKaYgCn8ZLaGCukGBAdF+mdYnoEdQfw3gHlvhyomN1cmx4KXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaGFzaC5kYXRhZGhhc2hYIPO+mob82GHAdHMQA0I2curYFHZluiGXQIASnvuxB2JadGNsYWltX2dlbmVyYXRvcl9pbmZvo2RuYW1lb0FudGhyb3BpYyBGaWxlc2d2ZXJzaW9uZTEuMC4wa3NwZWNWZXJzaW9uZTIuNC4wAAAQOGp1bWIAAAAoanVtZGMyY3MAEQAQgAAAqgA4m3EDYzJwYS5zaWduYXR1cmUAAAAQCGNib3LShFkCEqIBJhghWQIKMIICBjCCAY2gAwIBAgIUQOWgCu7COdC+uIP6BkIFPWdVEwAwCgYIKoZIzj0EAwMwSTEXMBUGA1UEChMOQW50aHJvcGljLCBQQkMxLjAsBgNVBAMTJUFudGhyb3BpYyBDb250ZW50IENyZWRlbnRpYWxzIFJvb3QgQ0EwHhcNMjYwODA3MTg0MzU2WhcNMjgwODA2MTk0MzU2WjBEMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEpMCcGA1UEAxMgQW50aHJvcGljIENsYXVkZSBDb250ZW50IFNpZ25pbmcwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAASYegpry1AYBRTVNL1CpTlbROnY3dey+UrsF9C3phYrATN3ZHf93Mo8RQN0KOUuOn19P4oWNFWe5n2/She9N7eTo1gwVjAOBgNVHQ8BAf8EBAMCB4AwFQYDVR0lBA4wDAYKKwYBBAGD6F4CATAMBgNVHRMBAf8EAjAAMB8GA1UdIwQYMBaAFM5R4gSBTmRbI/jjxM+aPpzB11zCMAoGCCqGSM49BAMDA2cAMGQCMDFzHRSeAXrSy1WOzkbhPZ6Km2wGTmZ/2gK18k8BQGXyqz88Rdrz6CTX9flAnYNVxgIwcF9c3fVhqmJKpi+UhasNUMko69cyX6STPfta3Q8EjyzDjzoyrol46FP6VFHhvUcJoWNwYWRZDZ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD2WEBCJ1hY2A1IgjBCXeNO65drP1kL7xz08C8nPyiGTbc8wpU1s23SSQEqeePYwaOEhtyQ8JbmIlltYes8T/4V/UAF78w7kwAANw9JREFUeJzt3dGV2zySBlD1HOfg1ByKQ3AoTs1R9D7417otSy1RIoj6Cvc+7c6ZMyZRIBv1EaTe3t/fTwAAAADJ/jf7AAAAAABeJeAAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMAAACIJ+AAAAAA4gk4AAAAgHgCDgAAACCegAMA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T8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQT8ABAAAAxBNwAAAAAPEEHAAAAEA8AQcAAAAQ7/8ANPPs7xV6N7QAAAAASUVORK5CYII=" alt="Kestrel logo"><div><div class="page-title">Kestrel</div><div class="brand-subtitle">Behavioral Security Intelligence</div></div></div></div>',
        unsafe_allow_html=True,
    )

with filter_col:
    time_btn, review_btn, user_btn = st.columns([1.12, 1.28, .88], gap="small")

    with time_btn:
        with st.popover("TIME RANGE", width="stretch"):
            scope = st.segmented_control(
                "Time range",
                ["All available", "Last 30 days", "Last 90 days", "Custom range"],
                default=st.session_state.get("time_scope", "All available"),
                key="time_scope",
            )
            custom_dates = None
            if scope == "Custom range":
                custom_dates = st.date_input(
                    "Custom range",
                    value=(scored["day"].min().date(), scored["day"].max().date()),
                    min_value=scored["day"].min().date(),
                    max_value=scored["day"].max().date(),
                    key="time_scope_custom_dates",
                )

    scope = st.session_state.get("time_scope", "All available")
    custom_dates = st.session_state.get("time_scope_custom_dates")
    if scope == "Custom range":
        custom_dates = custom_dates
    else:
        custom_dates = None

    with review_btn:
        with st.popover("REVIEW STATE", width="stretch"):
            risk_filter = st.selectbox(
                "Review state",
                ["All signals", "Needs review", "Below threshold"],
                key="risk_filter",
            )

    risk_filter = st.session_state.get("risk_filter", "All signals")

    scoped_for_state = apply_scope(scored, scope or "All available", custom_dates)
    if risk_filter == "Needs review":
        filter_scope = scoped_for_state[scoped_for_state["if_anomaly_score"] >= threshold]
    elif risk_filter == "Below threshold":
        filter_scope = scoped_for_state[scoped_for_state["if_anomaly_score"] < threshold]
    else:
        filter_scope = scoped_for_state

    choices = ["All users"] + user_peaks(filter_scope)["user"].tolist()
    if st.session_state.get("selected_user") not in choices:
        st.session_state.selected_user = "All users"

    with user_btn:
        with st.popover("USER", width="stretch"):
            selected_user = st.selectbox("User", choices, key="selected_user")

selected_user = st.session_state.get("selected_user", "All users")
scoped = apply_scope(scored, scope or "All available", custom_dates)
if risk_filter == "Needs review":
    scoped = scoped[scoped["if_anomaly_score"] >= threshold]
elif risk_filter == "Below threshold":
    scoped = scoped[scoped["if_anomaly_score"] < threshold]

if selected_user != "All users":
    working = scoped[scoped["user"] == selected_user].copy()
else:
    working = scoped.copy()

if working.empty:
    st.warning("No scored behavior matches the current filters. Adjust Filter to continue.", icon=":material/filter_alt_off:")
    st.stop()

latest_by_user = working.sort_values("day").groupby("user", as_index=False).tail(1)
high_risk_users = int((user_peaks(working)["if_anomaly_score"] >= threshold).sum())
active_alerts = int((latest_by_user["if_anomaly_score"] >= threshold).sum())
anomalies_detected = int((working["if_anomaly_score"] >= threshold).sum())

focus_row = working.loc[working["if_anomaly_score"].idxmax()]
latest_day = pd.Timestamp(focus_row["day"])
latest_score = float(focus_row["if_anomaly_score"])
latest_user = focus_row["user"]
first_score = float(working.sort_values("day").iloc[0]["if_anomaly_score"])
delta_pct = ((latest_score - first_score) / first_score * 100) if first_score else 0

daily_idx = working.groupby("day")["if_anomaly_score"].idxmax()
daily = working.loc[daily_idx, ["day", "user", "if_anomaly_score"]].sort_values("day").copy()
daily["primary_trigger"] = [largest_driver(working.loc[index])[0] for index in daily_idx]

st.markdown('<div class="masthead-divider"></div>', unsafe_allow_html=True)

hero_col, risk_col = st.columns([2.22, 1.0], gap="large", vertical_alignment="top")

with hero_col:
    st.markdown(
        f'''
        <div class="hero">
          <div class="hero-head">
            <div>
              <div class="hero-title">Current risk score</div>
              <div class="hero-meta">User {latest_user} · last observed {latest_day:%d %b}</div>
            </div>
            <div class="hero-delta">{delta_pct:+.0f}%</div>
          </div>
          <div class="hero-score">{latest_score:.3f}</div>
        ''',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hero-chart">', unsafe_allow_html=True)
    st.altair_chart(line_chart(daily, threshold), width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    tile_values = [
        ("✉", "EMAIL", float(focus_row.get("email_count", 0) or 0), True),
        ("□", "FILE", float(focus_row.get("file_event_count", 0) or 0), False),
        ("▣", "UNIQUE", float(focus_row.get("unique_filenames", 0) or 0), False),
        ("↕", "USB", float(focus_row.get("usb_connect_count", 0) or 0), False),
    ]
    tile_cols = st.columns(4, gap="small")
    for col, (icon, label, value, alert) in zip(tile_cols, tile_values):
        with col:
            st.markdown(
                f'<div class="metric-tile"><div class="metric-label">{icon}&nbsp; {label}</div><div class="metric-value {"alert" if alert else ""}">{value:.1f}σ</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)

with risk_col:
    st.markdown('<div class="side-title">Top risk users</div><div class="side-sub">By anomaly score, selected range</div>', unsafe_allow_html=True)
    top_users = user_peaks(working).head(4)[["user", "if_anomaly_score"]]
    max_score = max(float(top_users["if_anomaly_score"].max()), 0.001) if not top_users.empty else 1
    for row in top_users.itertuples(index=False):
        ratio = max(0.12, min(1.0, float(row.if_anomaly_score) / max_score))
        filled = max(1, min(4, round(ratio * 4)))
        segments = "".join(f'<span class="risk-seg {"s" + str(i + 1) if i < filled else ""}"></span>' for i in range(4))
        st.markdown(
            f'<div class="risk-row"><div class="risk-name">{row.user}</div><div class="risk-track">{segments}<span class="risk-seg s5 risk-score">{row.if_anomaly_score:.3f}</span></div></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div style="height:.72rem"></div>', unsafe_allow_html=True)
review_col, case_col = st.columns([1.72, 1.0], gap="large", vertical_alignment="top")

with review_col:
    st.markdown('<div class="lower-title">Users under review</div>', unsafe_allow_html=True)
    review_users = user_peaks(working).head(6)
    review_html = '<div class="review-panel"><div class="table-head"><span>USER</span><span>PRIMARY TRIGGER</span><span>SCORE</span></div>'
    for row in review_users.itertuples(index=False):
        driver, deviation = largest_driver(row)
        review_html += f'<div class="table-row"><span>{row.user}</span><span>{driver.replace(" activity", "").title()} · {deviation:.1f}σ</span><span>{float(row.if_anomaly_score):.3f}</span></div>'
    review_html += '</div>'
    st.markdown(review_html, unsafe_allow_html=True)

with case_col:
    st.markdown('<div class="case-titlebar"><div class="lower-title" style="margin:0">Case queue</div><div class="week-label">THIS WEEK</div></div>', unsafe_allow_html=True)
    queue = user_peaks(working).head(2)
    for row in queue.itertuples(index=False):
        driver, _ = largest_driver(row)
        high = float(row.if_anomaly_score) >= threshold
        state = "High" if high else "Low"
        note = "Analyst review pending" if high else "Awaiting evidence"
        st.markdown(
            f'''
            <div class="case-card">
              <div class="case-top"><span class="case-user">{row.user}</span><span class="case-pill {"case-high" if high else "case-low"}">{state}</span></div>
              <div class="case-name">{driver} spike</div>
              <div class="case-note">{note}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

if selected_user != "All users":
    user_data = working.sort_values("day").copy()
    latest = user_data.iloc[-1]
    status = "HIGH RISK" if latest["if_anomaly_score"] >= threshold else "BELOW THRESHOLD"
    label_class = "risk-label" if status == "HIGH RISK" else "neutral-label"

    section_label("USER THREAT PROFILE")
    st.markdown(
        f"""
        <div class="detail-card">
          <div class="detail-grid">
            <div class="detail-identity">
              <div class="profile-id">{selected_user}</div>
              <div class="profile-meta">Latest observation · {latest['day']:%d %b %Y}</div>
            </div>
            <div class="detail-score">
              <div class="detail-label">RISK SCORE</div>
              <div class="detail-score-value">{latest['if_anomaly_score']:.3f}</div>
            </div>
            <div class="detail-state">
              <span class="{label_class}">{status}</span>
              <div class="detail-action-title">RECOMMENDED ACTION</div>
              <div class="profile-meta">Analyst review</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_label("BEHAVIORAL DEVIATION")
    baseline_rows = []
    for feature in BASELINE_FEATURES:
        baseline = latest.get(f"{feature}_baseline_mean")
        if pd.notna(baseline):
            baseline_rows.append((FEATURE_LABELS[feature], float(baseline), float(latest[feature])))
    if baseline_rows:
        profile_rows = "".join(
            f'<div class="baseline-row"><div class="signal">{label}</div><div>{baseline:.1f}</div><div class="current">{current:.1f}</div></div>'
            for label, baseline, current in baseline_rows
        )
        st.markdown(
            f'<div class="baseline-profile"><div class="baseline-head"><div>BEHAVIORAL SIGNAL</div><div>BASELINE</div><div>CURRENT</div></div>{profile_rows}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("There is not enough baseline history to compare the selected user's latest activity.")

    with st.expander("Deep investigation / evidence", icon=":material/manage_search:"):
        evidence = user_data.nlargest(min(12, len(user_data)), "if_anomaly_score").copy()
        driver_info = evidence.apply(largest_driver, axis=1)
        evidence["Primary trigger"] = [f"{name} ({value:.1f}σ)" for name, value in driver_info]
        needs_review = evidence["if_anomaly_score"].ge(threshold)
        if "rule_alert" in evidence.columns:
            needs_review = needs_review | evidence["rule_alert"].eq(1)
        evidence["Review state"] = needs_review.map({True: "Needs review", False: "Below threshold"})
        evidence_columns = ["day", "Review state", "if_anomaly_score", "Primary trigger"]
        if "user_risk_7d" in evidence.columns:
            evidence_columns.append("user_risk_7d")
        if "top_reasons" in evidence.columns:
            evidence_columns.append("top_reasons")
        evidence_columns += ["logon_count", "file_event_count", "usb_connect_count", "email_count"]
        st.dataframe(
            evidence[evidence_columns],
            column_config={
                "top_reasons": st.column_config.TextColumn("Why it was flagged", width="large"),
                "user_risk_7d": st.column_config.NumberColumn("7-day risk", format="%.3f"),
                "day": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "if_anomaly_score": st.column_config.NumberColumn("Anomaly score", format="%.3f"),
                "logon_count": st.column_config.NumberColumn("Logins"),
                "file_event_count": st.column_config.NumberColumn("File actions"),
                "usb_connect_count": st.column_config.NumberColumn("USB events"),
                "email_count": st.column_config.NumberColumn("Emails"),
            },
            hide_index=True,
            width="stretch",
            height=335,
        )

st.caption("SYSTEM / ISOLATION FOREST · PER-USER BASELINES · ANALYST REVIEW REQUIRED FOR ALL SIGNALS")
