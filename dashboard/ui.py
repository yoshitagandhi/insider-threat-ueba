"""Small HTML helpers and the stylesheet for the dashboard.

Cards that only show HTML are built here as strings. Cards that also hold a
Streamlit widget (for example a Daily / Weekly switch) are Streamlit
containers whose key starts with "card", and the CSS below styles them the
same way.
"""

ICONS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    "chart": '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c1-3.5 3.5-5 6.5-5s5.5 1.5 6.5 5"/><circle cx="17" cy="9" r="2.8"/><path d="M17 14c2.5 0 4 1.5 4.8 4"/>',
    "alert": '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17.5v.5"/>',
    "bell": '<path d="M6 16V11a6 6 0 0112 0v5l2 2H4z"/><path d="M10 21h4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "activity": '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
    "zap": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
    "usb": '<path d="M12 2v14"/><circle cx="12" cy="19" r="2.5"/><path d="M12 8l-4-2v3"/><path d="M12 11l4-2V6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
}


def icon(name: str, size: int = 18, stroke: float = 1.8) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def kpi_card(ic: str, value: str, label: str, explanation: str, extra: str = "", dark: bool = False) -> str:
    return f"""
<div class="card kpi {'dark' if dark else ''}">
  <div class="card-top"><div class="ic">{icon(ic)}</div>{extra}</div>
  <div><div class="val">{value}</div><div class="lab">{label}</div><div class="exp">{explanation}</div></div>
</div>"""


def card_header(title: str, hint: str, right: str = "") -> str:
    return f'<div class="card-top"><div><h3>{title}</h3><div class="hint">{hint}</div></div>{right}</div>'


def chip(text: str, kind: str = "") -> str:
    return f'<span class="chip {kind}">{text}</span>'


def note(text: str) -> str:
    return f'<div class="note">{icon("info", 16)}<div>{text}</div></div>'


def inline_legend(items: list[tuple[str, str]]) -> str:
    spans = "".join(f'<span><i style="background:{color}"></i>{label}</span>' for label, color in items)
    return f'<div class="inline-legend">{spans}</div>'


def page_head(title: str, subtitle: str, stamp: str) -> str:
    return f'<div class="head"><div><h1>{title}</h1><div class="sub">{subtitle}</div></div><div class="stamp">{stamp}</div></div>'


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp { background: radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, rgba(255,255,255,0) 60%), #ebebeb; color: #111; }
.stApp, .stApp button, .stApp input { font-family: Inter, "Segoe UI", system-ui, sans-serif; font-feature-settings: "tnum" 1; }
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
.block-container { max-width: 1480px; padding: 1.1rem 2rem 2.5rem; }
[data-testid="stVerticalBlock"] { gap: .9rem; }
[data-testid="stHorizontalBlock"] { gap: 1.1rem; }

.st-key-topbar { background: rgba(255,255,255,.85); border-radius: 999px; padding: 8px 10px;
  box-shadow: 0 10px 30px rgba(0,0,0,.06); border: 1px solid rgba(0,0,0,.04); }
.st-key-topbar [data-testid="stHorizontalBlock"] { align-items: center; gap: .5rem; }
.st-key-page [data-testid="stButtonGroup"] { gap: 4px; }
.st-key-page button { border: none !important; background: transparent !important; border-radius: 999px !important;
  padding: 9px 18px !important; color: #555 !important; font-weight: 550; min-height: 0; }
.st-key-page button[data-testid="stBaseButton-segmented_controlActive"],
.st-key-page button[kind="segmented_controlActive"] { background: #111 !important; color: #fff !important;
  box-shadow: 0 6px 16px rgba(0,0,0,.18); }
.st-key-topbar [data-testid="stPopover"] button { border-radius: 999px; background: #f4f4f4; border: 1px solid #e8e8e8;
  font-size: 13px; font-weight: 600; color: #222; min-height: 40px; }
.st-key-topbar [data-testid="stPopover"] button:hover { border-color: #111; color: #111; }

div[class*="st-key-card"] { background: #fff; border-radius: 28px; padding: 22px 24px;
  box-shadow: 0 14px 34px rgba(0,0,0,.06), 0 2px 6px rgba(0,0,0,.03); border: 1px solid rgba(0,0,0,.035); }
div[class*="st-key-card"] [data-testid="stVerticalBlock"] { gap: .55rem; }
div[class*="st-key-card"] [data-testid="stButtonGroup"] button { border-radius: 999px; font-size: 12.5px; padding: 4px 12px; min-height: 0; }
div[class*="st-key-card"] [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]) { display: flex; justify-content: flex-end; }

[data-testid="stExpander"] details { background: #fff; border-radius: 24px; border: 1px solid rgba(0,0,0,.035);
  box-shadow: 0 14px 34px rgba(0,0,0,.06); }
[data-testid="stExpander"] summary { padding: 18px 24px; font-weight: 640; font-size: 15px; }
[data-testid="stExpander"] summary:hover { color: #111; }

.card { background: #fff; border-radius: 28px; padding: 22px 24px; box-shadow: 0 14px 34px rgba(0,0,0,.06), 0 2px 6px rgba(0,0,0,.03);
  border: 1px solid rgba(0,0,0,.035); color: #111; }
.card.dark { background: #111; color: #fff; box-shadow: 0 18px 40px rgba(0,0,0,.25); }
h3, .card h3 { margin: 0; padding: 0; font-size: 17px; font-weight: 620; letter-spacing: -0.01em; color: inherit; }
.hint { color: #7a7a7a; font-size: 13px; margin-top: 6px; line-height: 1.5; }
.card.dark .hint { color: #a9a9a9; }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.kpi { min-height: 188px; display: flex; flex-direction: column; justify-content: space-between; }
.kpi .ic, .ic { width: 40px; height: 40px; border-radius: 50%; background: #f2f2f2; display: grid; place-items: center; color: #111; }
.card.dark .ic { background: #262626; color: #fff; }
.kpi .val { font-size: 34px; font-weight: 640; letter-spacing: -0.035em; margin-top: 14px; line-height: 1; }
.kpi .lab { font-size: 13px; font-weight: 600; margin-top: 6px; }
.kpi .exp { font-size: 12.3px; color: #7d7d7d; line-height: 1.45; margin-top: 6px; }
.card.dark .kpi .exp { color: #a5a5a5; }
.chip { font-size: 11.5px; font-weight: 600; padding: 5px 10px; border-radius: 999px; background: #f2f2f2; color: #333; white-space: nowrap; }
.card.dark .chip { background: #262626; color: #ddd; }
.chip.solid { background: #111; color: #fff; }
.chip.outline { background: transparent; border: 1px solid #ddd; }
.head { display: flex; align-items: flex-end; justify-content: space-between; margin: 14px 4px 4px; }
.head h1 { font-size: 40px; line-height: 1.05; letter-spacing: -0.035em; font-weight: 620; margin: 0; padding: 0; color: #111; }
.head .sub { color: #6f6f6f; font-size: 14.5px; margin-top: 10px; max-width: 760px; line-height: 1.5; }
.head .stamp { font-size: 12px; color: #8a8a8a; text-align: right; line-height: 1.6; }
.chart { display: block; }
.tick { font-size: 11px; fill: #9a9a9a; font-family: Inter, sans-serif; }
.tick.strong { fill: #444; font-weight: 600; }
.lbl { font-size: 12.5px; fill: #333; font-family: Inter, sans-serif; }
.lbl.strong { font-weight: 650; fill: #111; }
.tt1 { font-size: 11px; fill: #bbb; font-family: Inter, sans-serif; }
.tt2 { font-size: 13px; fill: #fff; font-weight: 650; font-family: Inter, sans-serif; }
.donut-big { font-size: 26px; font-weight: 680; fill: #111; font-family: Inter, sans-serif; letter-spacing: -0.03em; }
.legend { display: flex; flex-direction: column; gap: 14px; }
.legend .row { display: flex; gap: 12px; align-items: flex-start; }
.sw { width: 12px; height: 12px; border-radius: 4px; flex: 0 0 12px; margin-top: 3px; }
.legend .t { font-size: 13px; font-weight: 600; display: flex; gap: 8px; }
.legend .t span { color: #8a8a8a; font-weight: 500; }
.legend .d { font-size: 12px; color: #7a7a7a; margin-top: 2px; line-height: 1.4; }
.inline-legend { white-space: nowrap; display: flex; gap: 16px; font-size: 12px; color: #666; align-items: center; }
.inline-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.ulist { display: flex; flex-direction: column; gap: 14px; margin-top: 18px; }
.urow { display: grid; grid-template-columns: 38px 1fr 64px; gap: 12px; align-items: center; }
.av { width: 38px; height: 38px; border-radius: 50%; background: #efefef; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.av.dark { background: #111; color: #fff; }
.uname { font-size: 13px; font-weight: 620; }
.umeta { font-size: 11.5px; color: #8a8a8a; margin-top: 2px; }
.ubar { height: 8px; border-radius: 99px; background: #f0f0f0; margin-top: 6px; overflow: hidden; }
.ubar > div { height: 100%; border-radius: 99px; background: #111; }
.uscore { text-align: right; font-weight: 650; font-size: 13.5px; }
table.tbl { width: 100%; border-collapse: separate; border-spacing: 0 8px; margin-top: 8px; }
table.tbl th { text-align: left; font-size: 11.5px; color: #8a8a8a; font-weight: 600; padding: 4px 14px; border: none; background: none; }
table.tbl td { font-size: 13.3px; padding: 13px 14px; background: #f7f7f7; border: none; }
table.tbl td:first-child { border-radius: 14px 0 0 14px; font-weight: 600; }
table.tbl td:last-child { border-radius: 0 14px 14px 0; }
.score { font-weight: 680; }
.case { border-radius: 20px; background: #f6f6f6; padding: 14px 16px; margin-top: 12px; }
.case .r1 { display: flex; justify-content: space-between; align-items: center; }
.case .who { font-size: 12.5px; font-weight: 650; }
.case .what { font-size: 14px; font-weight: 620; margin-top: 8px; }
.case .meta { font-size: 12px; color: #7d7d7d; margin-top: 4px; }
.uid { font-size: 26px; font-weight: 640; letter-spacing: -0.02em; }
.facts { display: flex; flex-direction: column; gap: 12px; margin-top: 26px; }
.facts div { display: flex; justify-content: space-between; gap: 12px; border-top: 1px solid #262626; padding-top: 12px; font-size: 13px; }
.facts span { color: #a5a5a5; }
.facts b { font-weight: 620; text-align: right; }
.why { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.why .w { display: flex; gap: 12px; align-items: flex-start; font-size: 13.5px; line-height: 1.45; }
.why .w .n { width: 26px; height: 26px; border-radius: 50%; background: #111; color: #fff; font-size: 12px; display: grid; place-items: center; flex: 0 0 26px; font-weight: 650; }
.why .w b { font-weight: 650; }
.steps-title { font-size: 12px; font-weight: 650; color: #8a8a8a; text-transform: uppercase; letter-spacing: .05em; margin-top: 20px; }
.todo { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
.todo div { display: flex; gap: 10px; align-items: center; font-size: 13px; color: #333; background: #f7f7f7; border-radius: 12px; padding: 10px 12px; }
.rows { display: flex; flex-direction: column; margin-top: 10px; }
.rows div { display: grid; grid-template-columns: 1fr 34px 72px; align-items: center; gap: 8px; padding: 12px 0; border-top: 1px solid #efefef; font-size: 13px; }
.rows span { color: #555; }
.rows b { text-align: right; font-weight: 680; }
.rows em { font-style: normal; text-align: center; }
.note { display: flex; gap: 10px; align-items: flex-start; font-size: 12.5px; color: #6f6f6f; line-height: 1.5; background: #f6f6f6; border-radius: 16px; padding: 12px 14px; margin-top: 16px; }
.empty { color: #8a8a8a; font-size: 13px; padding: 30px 0; text-align: center; }
.bellwrap { display: flex; justify-content: flex-end; }
.round { width: 42px; height: 42px; border-radius: 50%; background: #111; color: #fff; display: grid; place-items: center; position: relative; }
.round .dot { position: absolute; top: -3px; right: -3px; background: #fff; color: #111; font-size: 10px; font-weight: 700;
  border-radius: 999px; padding: 2px 6px; box-shadow: 0 2px 6px rgba(0,0,0,.15); }
.foot { text-align: center; color: #9a9a9a; font-size: 11.5px; margin-top: 18px; letter-spacing: .04em; }
</style>
"""
