"""Insider-threat analyst dashboard.

Three pages share one top bar: Overview (who needs attention), Investigate
(one person in depth) and Model performance (offline evaluation with CERT
labels). Charts are drawn as SVG by svg_charts.py so they match the approved
black-and-white design exactly.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import math

import pandas as pd
import streamlit as st

import metrics as m
import svg_charts as ch
import ui
from src.utils.config import DATA_PROCESSED_DIR, ROOT_DIR

PAGES = ["Overview", "Investigate", "Model performance"]
DATE_SCOPES = ["All dates", "Last 30 days", "Last 90 days", "Custom"]
REVIEW_STATES = ["All signals", "Needs review", "Below the line"]
INK, MID, SOFT = "#111111", "#9b9b9b", "#d9d9d9"
SHORT_NAMES = {
    "Isolation Forest (daily)": "Daily model",
    "Hybrid: IF + USB rule": "Hybrid",
    "7-day user risk (max)": "7-day risk",
    "Combined: daily OR 7-day + rule": "Combined",
    "Max |z| baseline": "Baseline",
}
SCENARIO_TEXT = {
    "r4.2-1": "short USB theft before leaving",
    "r4.2-2": "slow data theft over weeks",
    "r4.2-3": "admin sabotage with a keylogger",
}

st.set_page_config(page_title="Dashboard", page_icon=":material/shield:", layout="wide", initial_sidebar_state="collapsed")
st.html(ui.CSS)


@st.cache_data(show_spinner="Loading behaviour data…")
def load(path: str, modified: float) -> pd.DataFrame:
    return m.prepare(pd.read_parquet(path))


@st.cache_data(show_spinner="Scoring the test period…")
def performance_data(path: str, modified: float) -> dict:
    from src.evaluation.analysis import alert_budget
    from src.evaluation.report import (SCORES, benign_window_alert_rate, build_report, insider_outcomes,
                                       insiders_caught)

    scored = load(path, modified)
    scores = {name: col for name, col in SCORES.items() if col in scored.columns}
    test = scored[scored["split"] == "test"]
    result = {
        "report": build_report(scored),
        "test_days": int(test["day"].nunique()),
        "test_rows": len(test),
        "attack_days": int(test["is_malicious"].sum()),
        "base_rate": float(test["is_malicious"].mean()),
        "start": test["day"].min(),
        "end": test["day"].max(),
        "early": [],
        "budgets": {},
        "scenarios": {},
    }
    for name, col in scores.items():
        outcomes = insider_outcomes(scored, col)
        result["early"].append((SHORT_NAMES.get(name, name), int(outcomes["caught_during"].sum()),
                                int(outcomes["caught_early"].sum()), benign_window_alert_rate(scored, col)))
        result["budgets"][SHORT_NAMES.get(name, name)] = alert_budget(scored, col)
        result["scenarios"][SHORT_NAMES.get(name, name)] = insiders_caught(scored, col)
        if col == scores.get("Hybrid: IF + USB rule", scores.get("Isolation Forest (daily)")):
            result["outcomes"] = outcomes
            result["outcomes_name"] = SHORT_NAMES.get(name, name)
    result["insiders"] = len(result["outcomes"])
    ablation_path = ROOT_DIR / "reports" / "ablation.csv"
    result["ablation"] = pd.read_csv(ablation_path) if ablation_path.exists() else None
    return result


def html(content: str) -> None:
    st.html(ch.svgs_to_images(content))


def fmt_day(day) -> str:
    return pd.Timestamp(day).strftime("%d %b %Y")


data_path = DATA_PROCESSED_DIR / "scored_daily.parquet"
if not data_path.exists():
    st.error("No scored data yet. Run the pipeline first: `python -m src.pipeline`", icon=":material/error:")
    st.stop()

scored = load(str(data_path), data_path.stat().st_mtime)
threshold = m.threshold_for(scored, "risk_score")
daily_threshold = m.threshold_for(scored, "if_anomaly_score")
train_scores = scored.loc[scored["split"] == "train", "risk_score"] if "split" in scored.columns else scored["risk_score"]

for key, default in [("page_choice", "Overview"), ("date_scope", "All dates"), ("review_state", "All signals"), ("user_choice", "All users")]:
    st.session_state.setdefault(key, default)


def go_to(name: str) -> None:
    st.session_state["page_choice"] = name


scope = st.session_state["date_scope"] or "All dates"
custom = st.session_state.get("custom_dates")
dated = m.apply_dates(scored, scope, custom)
if dated.empty:
    dated = scored
reviewed = m.apply_review(dated, st.session_state["review_state"], threshold)
user_options = ["All users"] + m.user_peaks(dated)["user"].tolist()
if st.session_state["user_choice"] not in user_options:
    st.session_state["user_choice"] = "All users"

date_label = f"{dated['day'].min():%d %b %Y} – {dated['day'].max():%d %b %Y}"
needs_now = int((m.latest_by_user(dated)["risk_score"] >= threshold).sum())

with st.container(key="topbar"):
    nav, dates_col, review_col, user_col, bell_col = st.columns([3.1, 2.2, 1.35, 1.35, 0.35], vertical_alignment="center")
    with nav:
        with st.container(horizontal=True, key="nav", gap="small"):
            for name, symbol in zip(PAGES, [":material/grid_view:", ":material/search:", ":material/bar_chart:"]):
                st.button(name, icon=symbol, key=f"nav_{name}", on_click=go_to, args=(name,),
                          type="primary" if st.session_state["page_choice"] == name else "tertiary")
    with dates_col:
        with st.popover(f"Dates · {date_label}", icon=":material/calendar_month:", width="stretch"):
            st.radio("Date range", DATE_SCOPES, key="date_scope", horizontal=True)
            if st.session_state["date_scope"] == "Custom":
                st.date_input("Choose dates", value=(scored["day"].min().date(), scored["day"].max().date()),
                              min_value=scored["day"].min().date(), max_value=scored["day"].max().date(), key="custom_dates")
            st.caption("Only the Overview and Investigate pages use this range.")
    with review_col:
        with st.popover(f"Review · {st.session_state['review_state']}", icon=":material/shield:", width="stretch"):
            st.radio("Review state", REVIEW_STATES, key="review_state")
            st.caption("Needs review = above the alert line (top 1% of normal days).")
    with user_col:
        with st.popover(f"User · {st.session_state['user_choice']}", icon=":material/person:", width="stretch"):
            st.selectbox("Person", user_options, key="user_choice")
            st.caption("People are sorted by their highest risk in the chosen dates.")
    with bell_col:
        html(f'<div class="bellwrap"><div class="round" title="People above the line on their latest day">{ui.icon("bell", 18, "#ffffff")}<span class="dot">{needs_now}</span></div></div>')

page = st.session_state["page_choice"]
user = st.session_state["user_choice"]


def overview() -> None:
    view = reviewed if user == "All users" else reviewed[reviewed["user"] == user]
    html(ui.page_head(
        "Overview",
        "Who needs attention, and why. Every score compares a person with their <b>own</b> past behaviour, not with everyone else.",
        f"Latest data · {fmt_day(dated['day'].max())}<br>Alert line = top 1% of normal days",
    ))
    if view.empty:
        html('<div class="card"><div class="empty">No days match the current filters. Try a wider date range or "All signals".</div></div>')
        return

    alerts = view[view["risk_score"] >= threshold]
    latest = m.latest_by_user(view)
    people = view["user"].nunique()
    need_now = int((latest["risk_score"] >= threshold).sum())
    days = max(view["day"].nunique(), 1)
    flagged = alerts["user"].nunique()
    weekly = alerts.set_index("day").resample("W-MON").size().reindex(
        pd.date_range(view["day"].min(), view["day"].max(), freq="W-MON"), fill_value=0)
    recent = (weekly.tail(10).tolist() or [0]) + [0] * max(0, 2 - len(weekly))

    cols = st.columns(5)
    cards = [
        ui.kpi_card("users", f"{people:,}", "People monitored", "Everyone with at least 3 days of history, so a personal baseline exists."),
        ui.kpi_card("alert", f"{need_now}", "Need review now", "People whose latest day is above the alert line. Start with these.",
                    ui.chip(f"{need_now / max(people, 1):.0%} of people"), dark=True),
        ui.kpi_card("bell", f"{len(alerts):,}", "Alerts in range", "Days, across all people, that crossed the alert line in the chosen dates.",
                    ch.mini_bars(recent)),
        ui.kpi_card("clock", f"{len(alerts) / days:.1f}", "Alerts per day", "Average daily workload for an analyst in the chosen dates.",
                    ch.sparkline([v / 7 for v in recent], 90) if len(recent) > 1 else ""),
        ui.kpi_card("target", f"{flagged:,}", "People flagged", "People with at least one alert in the chosen dates.",
                    ui.chip(f"{flagged / max(people, 1):.0%} of people")),
    ]
    for col, card in zip(cols, cards):
        with col:
            html(card)

    left, right = st.columns([2.05, 1])
    with left:
        with st.container(key="card_trend"):
            html(ui.card_header("Alerts over time", "How many people crossed the alert line in each period. The dashed line is the average; dots mark busy periods."))
            period = st.segmented_control("Period", ["Daily", "Weekly", "Monthly"], default="Weekly", key="trend_period",
                                          label_visibility="collapsed") or "Weekly"
            series = m.risk_series(view, period, threshold)
            if len(series) < 2:
                html('<div class="empty">Not enough days in this range to draw a trend.</div>')
            else:
                values = series["above"].astype(float).tolist()
                average = sum(values) / len(values)
                peak = int(series["above"].idxmax())
                ymin, ymax, ticks = ch.nice_ticks(0, max(values) * 1.15 or 1)
                titles = {i: f"{fmt_day(d)}: {int(v)} people above the line" for i, (d, v) in enumerate(zip(series["day"], values))}
                html(ch.area_chart(values, m.month_labels(series["day"]), average, width=860, height=300,
                                   ymin=ymin, ymax=ymax, gid="trend", titles=titles, line_label=f"average {average:.1f}",
                                   dot_min=max(average * 2, sorted(values)[-min(6, len(values))]), yfmt="{:g}", yticks=ticks,
                                   tooltip=(peak, fmt_day(series["day"][peak]), f"{int(values[peak])} people above the line")))
    with right:
        counts = alerts["alert_source"].value_counts()
        parts = [("today's behaviour", "Today's behaviour", "The day itself was unusual for that person.", INK),
                 ("7-day carry-over", "7-day carry-over", "A strong spike earlier in the week keeps them on the list.", MID),
                 ("rule", "USB rule", "First-ever USB use, after hours.", SOFT)]
        total = int(counts.sum())
        if total == 0:
            body = '<div class="empty">No alerts in the chosen dates.</div>'
        else:
            legend = "".join(
                f'<div class="row"><div class="sw" style="background:{color}"></div><div><div class="t">{title} '
                f'<span>{counts.get(key, 0) / total:.0%}</span></div><div class="d">{desc}</div></div></div>'
                for key, title, desc, color in parts)
            donut = ch.donut([(k, int(counts.get(k, 0)), c) for k, _, _, c in parts if counts.get(k, 0) > 0], size=210, thickness=24,
                             center_top=f"{total:,}", center_bottom="alerts")
            rule_days = int(view["rule_alert"].sum()) if "rule_alert" in view.columns else 0
            body = (f'<div style="display:flex;gap:20px;align-items:center;margin-top:16px">{donut}<div class="legend">{legend}</div></div>'
                    + ui.note(f"The USB rule fired on {rule_days} day{'s' if rule_days != 1 else ''} in this range. It is rare by design, so each one is worth a look."))
        html(f'<div class="card" style="min-height:452px">{ui.card_header("Why people were flagged", "Where each alert came from in the chosen dates.")}{body}</div>')

    left, right = st.columns([1.45, 1])
    with left:
        buckets, index, bucket_name = m.volume_buckets(alerts, view["day"].min(), view["day"].max())
        biggest = max([a + b for a, b in buckets] + [1])
        per_square = max(1, math.ceil(biggest / 12))
        squares = [(min(12, math.ceil(a / per_square)) if a else 0, min(12, math.ceil(b / per_square)) if b else 0) for a, b in buckets]
        grid = ch.heat_grid(squares, rows=12, width=760, labels=m.month_labels(pd.Series(index)))
        html(f'''<div class="card" style="min-height:430px">{ui.card_header(f"{bucket_name.title()}ly alert volume",
             f"Each column is one {bucket_name}. Every square is about {per_square} alert{'s' if per_square > 1 else ''}.",
             ui.inline_legend([("New alerts", INK), ("Carry-over", "#bdbdbd")]))}<div style="margin-top:14px">{grid}</div></div>''')
    with right:
        counts_by_user = alerts.groupby("user").size().rename("alert_days")
        top = m.user_peaks(alerts).join(counts_by_user, on="user").sort_values(["alert_days", "risk_score"], ascending=False).head(5)
        most = int(top["alert_days"].max()) if not top.empty else 1
        rows = "".join(
            f'''<div class="urow"><div class="av {'dark' if i == 0 else ''}">{r.user[:2]}</div>
            <div><div class="uname">{r.user}</div><div class="umeta">Worst day {r.day:%d %b}: {m.trigger_text(r)}</div>
            <div class="ubar"><div style="width:{max(4, r.alert_days / most * 100):.0f}%"></div></div></div>
            <div class="uscore">{r.alert_days} days</div></div>''' for i, (_, r) in enumerate(top.iterrows()))
        html(f'''<div class="card" style="min-height:430px">{ui.card_header("Top risk people",
             "People with the most days above the alert line in the chosen dates.", ui.chip(f"Top {len(top)}"))}
             <div class="ulist">{rows or '<div class="empty">No people in range.</div>'}</div></div>''')

    left, right = st.columns([2.05, 1])
    with left:
        recent_alerts = alerts.sort_values(["day", "risk_score"], ascending=False).head(6)
        rows = "".join(
            f'<tr><td>{r.user}</td><td>{fmt_day(r.day)}</td><td>{m.trigger_text(r)}</td>'
            f'<td>{ui.chip(m.short_source(r), "solid" if r.get("rule_alert", 0) == 1 else "")}</td>'
            f'<td class="score">{r.risk_score:.3f}</td></tr>' for _, r in recent_alerts.iterrows())
        table = (f'<table class="tbl"><tr><th>Person</th><th>Date</th><th>Primary trigger</th><th>Alert source</th><th>Risk</th></tr>{rows}</table>'
                 if rows else '<div class="empty">No alerts in the chosen dates.</div>')
        html(f'''<div class="card" style="min-height:420px">{ui.card_header("Recent alerts",
             "The latest days that crossed the alert line. The primary trigger is the behaviour that changed the most.",
             ui.chip(f"{need_now} need review now"))}{table}</div>''')
    with right:
        cases = m.user_peaks(alerts).head(3)
        items = ""
        for _, r in cases.iterrows():
            person = alerts[alerts["user"] == r.user]
            level = ui.chip("High", "solid") if r.risk_score >= 0.999 else ui.chip("Medium")
            title = "First-ever USB use after hours" if r.get("rule_alert", 0) == 1 else f"{m.largest_driver(r)[0]} spike"
            items += (f'<div class="case"><div class="r1"><span class="who">{r.user}</span>{level}</div><div class="what">{title}</div>'
                      f'<div class="meta">First alert {person["day"].min():%d %b} · {len(person)} alert day{"s" if len(person) != 1 else ""}</div></div>')
        html(f'''<div class="card" style="min-height:420px">{ui.card_header("Case queue", "The highest-risk people with alerts in this range.",
             ui.chip("Priority"))}{items or '<div class="empty">No open cases.</div>'}</div>''')


def investigate() -> None:
    chosen = user
    auto = chosen == "All users"
    if auto:
        peaks = m.user_peaks(dated)
        if peaks.empty:
            html('<div class="card"><div class="empty">No people in the chosen dates.</div></div>')
            return
        chosen = peaks["user"].iloc[0]
    days = dated[dated["user"] == chosen].sort_values("day").reset_index(drop=True)
    latest = days.iloc[-1]
    peak_index = int(days["risk_score"].idxmax())
    peak = days.loc[peak_index]
    alert_days = days[days["risk_score"] >= threshold]
    week_after = (days["day"] > peak["day"]) & (days["day"] <= peak["day"] + pd.Timedelta(days=7))
    carry_after = int((week_after & days["alert_source"].eq("7-day carry-over")).sum())

    html(ui.page_head(
        "Investigate",
        "One person's behaviour compared with their own normal. Choose a person from <b>User</b> in the top bar.",
        f"Showing · {chosen}{' (highest risk)' if auto else ''}<br>Latest observation {fmt_day(latest['day'])}",
    ))

    above_now = latest["risk_score"] >= threshold
    action = f"Review {peak['day']:%d %b} evidence" if peak["risk_score"] >= threshold else "No action needed"
    source = m.short_source(peak) if peak["risk_score"] >= threshold else "No alerts"
    percent = float((train_scores <= latest["risk_score"]).mean())
    marker = float((train_scores <= threshold).mean())
    driver, z = m.largest_driver(peak)
    monthly = m.monthly_user(days, threshold)

    cols = st.columns([1.3, 1.1, 1, 1])
    with cols[0]:
        html(f'''<div class="card dark kpi"><div class="card-top"><div><div class="uid">{chosen}</div>
            <div class="hint">Latest observation · {fmt_day(latest['day'])}</div></div>
            {ui.chip("Above the line today" if above_now else "Below the line today")}</div>
            <div class="facts"><div><span>Peak risk</span><b>{peak['risk_score']:.3f} · {peak['day']:%d %b}</b></div>
            <div><span>Alert source</span><b>{source}</b></div><div><span>Recommended action</span><b>{action}</b></div></div></div>''')
    with cols[1]:
        gauge = ch.gauge(percent, 1.0, f"{latest['risk_score']:.3f}", "", marker=marker, width=320)
        html(f'''<div class="card kpi">{ui.card_header("Risk today", "The tick marks the alert line.")}
            <div>{gauge}<div class="hint" style="text-align:center;margin-top:-2px">More unusual than {percent:.0%} of normal days</div></div></div>''')
    with cols[2]:
        html(ui.kpi_card("bell", f"{len(alert_days)}", "Alert days", "Days this person was above the alert line in the chosen dates.",
                         ch.mini_bars(monthly["alerts"].tail(7).tolist() or [0]) if len(monthly) > 1 else ""))
    with cols[3]:
        html(ui.kpi_card("usb", f"{z:+.1f}σ", "Biggest change", f"{driver} on {fmt_day(peak['day'])}, compared with their usual day."))

    left, right = st.columns([2.05, 1])
    with left:
        with st.container(key="card_timeline"):
            html(ui.card_header("Risk timeline", "This person's score each day. Shaded days stay high because of an earlier spike (7-day carry-over)."))
            metric = st.segmented_control("Metric", ["Risk score", "Daily model"], default="Risk score", key="timeline_metric",
                                          label_visibility="collapsed") or "Risk score"
            if len(days) < 2:
                html('<div class="empty">Only one day of data for this person.</div>')
            else:
                column, line = ("risk_score", threshold) if metric == "Risk score" else ("if_anomaly_score", daily_threshold)
                values = days[column].tolist()
                low, high = min(values + [line]), max(values + [line])
                ymin, ymax, ticks = ch.nice_ticks(low, 1.0 if column == "risk_score" else high)
                ymin = max(0.0, ymin) if column == "risk_score" else ymin
                titles = {i: f"{fmt_day(r.day)}: {m.trigger_text(r)}" for i, r in days.iterrows() if r[column] >= line}
                html(ch.area_chart(values, m.month_labels(days["day"]), line, width=860, height=380, ymin=ymin, ymax=ymax,
                                   tooltip=(peak_index, fmt_day(peak["day"]), f"{metric} {peak[column]:.3f}"),
                                   bands=m.carry_bands(days) if column == "risk_score" else None, titles=titles, gid="timeline",
                                   yticks=[t for t in ticks if t >= ymin]))
    with right:
        normal, today, labels = m.radar_values(peak)
        radar = ch.radar([a for a, _ in m.RADAR_AXES], normal, today, size=400, labels_extra=labels)
        html(f'''<div class="card" style="min-height:540px">{ui.card_header("Behaviour shape",
             f"Each corner is one kind of activity: usual day vs {peak['day']:%d %b}. A bigger shape means more unusual.")}
             <div style="margin-top:10px">{ui.inline_legend([("Usual day", "#d6d6d6"), (f"{peak['day']:%d %b}", INK)])}</div>{radar}</div>''')

    left, right = st.columns([1.4, 1])
    with left:
        with st.container(key="card_monthly"):
            html(ui.card_header("Risk per month", "Taller bars mean a more unusual month. The darkest bar is the most unusual one."))
            kind = st.segmented_control("Monthly", ["Average", "Alerts"], default="Average", key="monthly_metric",
                                        label_visibility="collapsed") or "Average"
            if monthly.empty:
                html('<div class="empty">No monthly data.</div>')
            else:
                values = monthly["avg"].tolist() if kind == "Average" else monthly["alerts"].astype(float).tolist()
                vmax = max(1.0, max(values)) if kind == "Average" else max(1.0, max(values) * 1.1)
                values = [max(v, 0.0) for v in values]
                hi = int(pd.Series(values).idxmax())
                tip = (monthly["day"].iloc[hi].strftime("%B %Y"), f"avg {monthly['avg'].iloc[hi]:.2f} · {monthly['alerts'].iloc[hi]} alerts")
                titles = [f"{d:%b %Y}: avg {a:.2f}, {n} alerts" for d, a, n in zip(monthly["day"], monthly["avg"], monthly["alerts"])]
                html(ch.hatched_bars(values, [d.strftime("%b") for d in monthly["day"]], hi, tip, width=660, height=270,
                                     vmax=vmax, titles=titles))
    with right:
        devs = m.top_deviations(peak)
        top = max([abs(v) for _, v in devs] + [3.0])
        html(f'''<div class="card" style="min-height:400px">{ui.card_header("What changed on the worst day",
             f"How far {peak['day']:%d %b} was from this person's normal. σ means 'times their usual variation'.")}
             <div style="margin-top:16px">{ch.diverging_bars(devs, width=430, maxv=top * 1.1)}</div></div>''')

    left, right = st.columns(2)
    with left:
        lines = "".join(f'<div class="w"><div class="n">{i + 1}</div><div>{t}</div></div>' for i, t in enumerate(m.why_lines(peak, carry_after)))
        todo = "".join(f'<div>{ui.icon("check", 15, "#111111")} {t}</div>' for t in [
            f"Check what was copied or sent on {peak['day']:%d %b}",
            "Confirm whether any after-hours work was approved",
            "Close or escalate the case and note the outcome"])
        html(f'''<div class="card" style="min-height:520px">{ui.card_header("Why this person was flagged", "Plain-language summary of the strongest evidence.")}
             <div class="why">{lines}</div><div class="steps-title">Suggested next steps</div><div class="todo">{todo}</div>
             {ui.note("An alert is a lead for review, not proof of wrongdoing. Check the evidence below before taking any action.")}</div>''')
    with right:
        counts = m.trigger_counts(alert_days)
        shades = [INK, "#4a4a4a", "#8a8a8a", "#bdbdbd", "#dcdcdc"]
        body = (f'<div style="max-width:600px;margin:0 auto">{ch.rose([(n, c, shades[i]) for i, (n, c) in enumerate(counts)], size=420)}</div>'
                if counts else '<div class="empty">No alert days for this person in the chosen dates.</div>')
        html(f'''<div class="card" style="min-height:520px">{ui.card_header("What triggered the alerts",
             f"The main reason on each of this person's {len(alert_days)} alert days. Bigger slice = more days.",
             ui.chip(f"{len(alert_days)} days"))}{body}</div>''')

    with st.expander(f"Deep investigation / evidence — the {min(12, len(days))} most unusual days for {chosen}", icon=":material/manage_search:"):
        st.dataframe(m.evidence_table(days, threshold), hide_index=True, width="stretch",
                     column_config={"Risk": st.column_config.NumberColumn(format="%.3f"),
                                    "Why it was flagged": st.column_config.TextColumn(width="large")})


def performance() -> None:
    if "is_malicious" not in scored.columns or "split" not in scored.columns:
        html(ui.page_head("Model performance", "This page needs the CERT answer labels and a train/test split.", ""))
        html('<div class="card"><div class="empty">Run <code>python -m src.pipeline</code> with the answer files in data/answers/r4.2.</div></div>')
        return
    perf = performance_data(str(data_path), data_path.stat().st_mtime)
    report = perf["report"].set_index("model")
    total = perf["insiders"]

    def row(name: str, fallback: str = "Isolation Forest (daily)") -> pd.Series:
        return report.loc[name] if name in report.index else report.loc[fallback]

    combined = row("Combined: daily OR 7-day + rule")
    hybrid_name = perf["outcomes_name"]
    early = {name: (during, caught, chance) for name, during, caught, chance in perf["early"]}
    hybrid_during, hybrid_early, hybrid_chance = early.get(hybrid_name, (0, 0, 0))
    caught_now = int(str(combined["insiders_caught"]).split("/")[0])
    lift = combined["precision"] / perf["base_rate"] if perf["base_rate"] else 0

    html(ui.page_head(
        "Model performance",
        f"How well the system would have worked on {perf['test_days']} days it never saw ({fmt_day(perf['start'])} – {fmt_day(perf['end'])}). "
        "This page uses CERT's answer labels, so it is for evaluation, not daily use. The top-bar filters do not apply here.",
        f"{total} insiders · {perf['attack_days']} attack days<br>{perf['test_rows']:,} person-days tested",
    ))

    cols = st.columns(4)
    cards = [
        ui.kpi_card("target", f"{caught_now} / {total}", "Insiders caught",
                    "Got at least one alert during their attack (combined queue).", ui.chip(f"{caught_now / total:.0%}")),
        ui.kpi_card("zap", f"{hybrid_early} / {total}", "Early warning",
                    f"Alerted during the attack or up to 7 days before it ({hybrid_name.lower()}). A random week: {hybrid_chance:.0%}.",
                    ui.chip(f"{hybrid_early / total:.0%}"), dark=True),
        ui.kpi_card("check", f"{combined['precision']:.3f}", "Precision",
                    f"Share of alert days that were real attack days. {lift:.0f}× better than random guessing.", ui.chip(f"{lift:.0f}× random")),
        ui.kpi_card("clock", f"{combined['n_flagged'] / perf['test_days']:.1f}", "Alerts per day",
                    "Daily workload at the chosen alert line (top 1% of normal days)."),
    ]
    for col, card in zip(cols, cards):
        with col:
            html(card)

    outcomes = perf["outcomes"]
    left, mid, right = st.columns([1, 1.25, 1])
    with left:
        gauge = ch.gauge(hybrid_early, total, f"{hybrid_early}/{total}", "", width=320)
        rows = (f'<div><span>Alerted during the attack</span><b>{hybrid_during}</b><em>{ui.chip("Caught", "solid")}</em></div>'
                f'<div><span>Alerted only in the week before</span><b>{hybrid_early - hybrid_during}</b><em>{ui.chip("Early")}</em></div>'
                f'<div><span>Not alerted</span><b>{total - hybrid_early}</b><em>{ui.chip("Missed", "outline")}</em></div>')
        html(f'''<div class="card" style="min-height:500px">{ui.card_header("Early warning coverage",
             f"{hybrid_name}: alerted during the attack or in the week before it.")}<div style="margin-top:8px">{gauge}</div>
             <div class="hint" style="text-align:center;margin-top:-2px">insiders warned in time</div><div class="rows">{rows}</div></div>''')
    with mid:
        groups = []
        for scenario, part in outcomes.groupby("scenario_group"):
            during = int(part["caught_during"].sum())
            early_only = int((part["caught_early"] & ~part["caught_during"]).sum())
            groups.append((scenario, SCENARIO_TEXT.get(scenario, ""), during, early_only, len(part) - during - early_only))
        legend = ui.inline_legend([("Alerted during attack", INK), ("Week before only", "#a6a6a6"), ("Missed", "#eeeeee")])
        html(f'''<div class="card" style="min-height:500px">{ui.card_header("Every insider, one dot",
             f"All {total} insiders in the test period, grouped by attack type.")}<div style="margin:12px 0 6px">{legend}</div>
             {ch.dot_matrix(groups, per_row=8, width=430)}</div>''')
    with right:
        bars = ch.early_bars([(n, d, c, f"{p:.1%}") for n, d, c, p in perf["early"]], width=430, total=total)
        html(f'''<div class="card" style="min-height:500px">{ui.card_header("Early warning vs chance",
             "Black = caught during or up to 7 days before. Grey = during the attack only.")}<div style="margin-top:16px">{bars}</div>
             {ui.note("<b>Chance</b> is how often a random normal person's week contains an alert. Each model should beat it by a wide margin.")}</div>''')

    left, right = st.columns([2.05, 1])
    with left:
        styles = {"Combined": (INK, "", "circle"), "Hybrid": ("#555", "", "square"),
                  "7-day risk": ("#9b9b9b", "6 4", "circle"), "Baseline": ("#c4c4c4", "2 4", "square")}
        series, xs = [], []
        for name, (color, dash, marker) in styles.items():
            table = perf["budgets"].get(name)
            if table is None:
                continue
            pts = [(a, s) for a, s in zip(table["alerts_per_day"], table["share_insiders_caught"]) if a > 0]
            xs += [a for a, _ in pts]
            series.append((name, pts, color, dash, marker))
        chart = ch.budget_lines(series, width=860, height=300, xmin=min(xs) * 0.8, xmax=max(xs) * 1.25) if xs else ""
        legend = ui.inline_legend([(n, styles[n][0]) for n, *_ in series])
        html(f'''<div class="card" style="min-height:470px">{ui.card_header("Insiders caught vs daily workload",
             "Each point is a different alert line. Further right = more alerts to review; higher = more insiders caught.", legend)}
             <div style="margin-top:10px">{chart}</div><div class="hint" style="text-align:center;margin-top:-4px">Alerts per day for the whole organisation (log scale)</div></div>''')
    with right:
        hybrid_caught = int(str(row("Hybrid: IF + USB rule")["insiders_caught"]).split("/")[0])
        _, step_top, step_ticks = ch.nice_ticks(0, max(total, 24))
        steps = ch.step_area([18, 12, hybrid_caught, caught_now],
                             [("v2", "fixes + split"), ("v3", "extra features"), ("v4", "hybrid"), ("v4+", "combined")],
                             width=440, height=330, vmax=step_top, ticks=tuple(step_ticks))
        html(f'''<div class="card" style="min-height:470px">{ui.card_header("Progress across versions",
             f"Insiders caught during the attack, out of {total}. v2 and v3 are from earlier runs; v4 is live.")}
             <div style="margin-top:14px">{steps}</div></div>''')

    left, right = st.columns([1.4, 1])
    with left:
        names = [n for n in ["Daily model", "7-day risk", "Combined"] if n in perf["scenarios"]]
        colors = ["#c4c4c4", "#7a7a7a", INK][:len(names)]
        base = perf["scenarios"][names[0]]
        scen = base[base["scenario_group"] != "all"]
        groups = []
        for _, srow in scen.iterrows():
            vals = []
            for n in names:
                t = perf["scenarios"][n]
                vals.append(int(t.loc[t["scenario_group"] == srow["scenario_group"], "caught"].iloc[0]))
            groups.append((srow["scenario_group"], int(srow["insiders"]), vals))
        maxv = int(math.ceil(max(g[1] for g in groups) / 4) * 4) if groups else 4
        chart = ch.grouped_bars(groups, names, colors, width=760, height=330, maxv=maxv, bw=30)
        html(f'''<div class="card" style="min-height:470px">{ui.card_header("Insiders caught by scenario",
             "The daily model catches slow, long attacks; the 7-day risk catches short bursts. Combined uses both.",
             ui.inline_legend(list(zip(names, colors))))}<div style="margin-top:12px">{chart}</div></div>''')
    with right:
        abl = perf["ablation"]
        if abl is None or abl.empty:
            body = '<div class="empty">Run <code>python -m src.evaluation.analysis</code> to add this chart.</div>'
        else:
            ref = int(abl.iloc[0]["insiders_caught_daily"])
            items = [(r.variant.replace("Without New features (Nov 2026)", "Without new features"), int(r.insiders_caught_daily), i == 0)
                     for i, r in enumerate(abl.itertuples())]
            body = (ch.diamond_pills(items, width=470, vmax=max(v for _, v, _ in items) + 4, ref=ref, total=int(abl.iloc[0]["insiders"]))
                    + ui.note("Explains the results only. The model itself was chosen on earlier data, never on this test period."))
        html(f'''<div class="card" style="min-height:470px">{ui.card_header("What each feature group adds",
             "Insiders caught by the daily model when one group of behaviours is removed. Shorter bar = that group mattered more.")}
             <div style="margin-top:18px">{body}</div></div>''')


if page == "Overview":
    overview()
elif page == "Investigate":
    investigate()
else:
    performance()

html('<div class="foot">ANALYST REVIEW REQUIRED FOR ALL SIGNALS · AN ALERT IS A LEAD, NOT PROOF</div>')
