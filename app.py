import re, json, requests, pandas as pd
import time, os
import streamlit as st
from datetime import datetime

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="Andalusia OPD Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; }

  .chat-wrapper {
    max-width: 860px;
    margin: 0 auto;
    padding: 0 16px 120px 16px;
    font-family: 'Segoe UI', sans-serif;
  }

  /* ── Header ── */
  .chat-header {
    position: sticky; top: 0; z-index: 100;
    background: #185FA5; color: white;
    padding: 14px 24px;
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 2px 12px rgba(24,95,165,0.3);
  }
  .chat-header h1 { margin:0; font-size:18px; font-weight:600; color:white; }
  .chat-header p  { margin:0; font-size:12px; opacity:.8; }
  .bu-badge {
    background: rgba(255,255,255,0.2);
    padding: 3px 10px; border-radius:20px; font-size:12px;
  }

  /* ── Bubbles ── */
  .msg-user { display:flex; justify-content:flex-end; margin:10px 0; }
  .msg-user .bubble {
    background:#185FA5; color:white;
    padding:10px 16px;
    border-radius:18px 18px 4px 18px;
    max-width:70%; font-size:15px; line-height:1.5;
  }
  .msg-bot { display:flex; gap:10px; margin:10px 0; align-items:flex-start; }
  .bot-avatar {
    width:32px; height:32px; border-radius:50%;
    background:#E6F1FB;
    display:flex; align-items:center; justify-content:center;
    font-size:16px; flex-shrink:0; margin-top:4px;
  }
  .msg-bot .bubble {
    background:#F5F7FA; border:1px solid #E8ECF0;
    padding:14px 18px;
    border-radius:4px 18px 18px 18px;
    max-width:90%; font-size:14px; line-height:1.75;
    color:#1a1a2e;
  }

  /* ── Context badge ── */
  .ctx-badge {
    display:inline-block;
    background:#E6F1FB; color:#0C447C;
    border-radius:20px; padding:3px 10px;
    font-size:11px; font-weight:600;
    margin-bottom:12px;
  }

  /* ── KPI grid ── */
  .kpi-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(140px,1fr));
    gap:8px; margin-bottom:14px;
  }
  .kpi-card {
    background:white; border:1px solid #E8ECF0;
    border-radius:10px; padding:10px 12px;
  }
  .kpi-name { font-size:10px; color:#888; margin-bottom:6px; }
  .bu-row   { display:flex; align-items:center; gap:6px; margin-bottom:3px; }
  .bu-tag   { font-size:10px; font-weight:700; width:28px; }
  .bar-wrap { flex:1; height:5px; background:#E8ECF0; border-radius:3px; }
  .bar-fill { height:100%; border-radius:3px; }
  .bu-num   { font-size:11px; font-weight:600; min-width:38px; text-align:right; }

  /* ── Ranking ── */
  .rank-section { margin-bottom:10px; }
  .rank-row {
    display:flex; align-items:center; gap:8px;
    padding:5px 0; border-bottom:1px solid #F0F2F5;
    font-size:12px;
  }
  .rank-num  { color:#aaa; font-size:10px; width:18px; }
  .rank-name { flex:1; color:#1a1a2e; }
  .rank-pct  { font-weight:600; min-width:38px; text-align:right; }

  /* ── Sparkline ── */
  .spark-wrap {
    display:flex; align-items:flex-end; gap:3px;
    height:32px; margin:8px 0 2px;
  }
  .spark-bar { flex:1; border-radius:2px 2px 0 0; }
  .spark-labels {
    display:flex; justify-content:space-between;
    font-size:9px; color:#aaa; margin-bottom:8px;
  }

  /* ── Winner summary ── */
  .winner-row {
    display:flex; align-items:center; gap:8px;
    padding:6px 10px; background:white;
    border:1px solid #E8ECF0; border-radius:8px;
    margin-bottom:5px; font-size:12px;
  }
  .winner-bu   { font-weight:700; min-width:32px; }
  .winner-desc { color:#666; flex:1; }
  .winner-val  { font-weight:600; }

  /* ── Analysis block ── */
  .analysis-block {
    background:white;
    border-left:3px solid #185FA5;
    border-radius:0 8px 8px 0;
    padding:12px 14px; margin-top:12px;
    line-height:1.8; font-size:13px; color:#1a1a2e;
  }
  .analysis-block p { margin:0 0 8px; }
  .analysis-block p:last-child { margin:0; }

  /* ── Tags inside analysis ── */
  .tag-green { background:#E1F5EE; color:#085041; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:600; }
  .tag-red   { background:#FCEBEB; color:#791F1F; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:600; }
  .tag-amber { background:#FAEEDA; color:#633806; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:600; }

  /* ── Section title ── */
  .section-title {
    font-size:10px; font-weight:700; color:#888;
    text-transform:uppercase; letter-spacing:.06em;
    margin:12px 0 6px;
  }

  /* ── Suggest chips ── */
  .suggest-row { display:flex; flex-wrap:wrap; gap:6px; margin-top:12px; }
  .chip {
    border:1px solid #dde2ea; border-radius:20px;
    padding:5px 12px; font-size:11px; color:#555;
    cursor:pointer; background:white;
    text-decoration:none; display:inline-block;
  }

  /* ── Welcome ── */
  .welcome-box { text-align:center; padding:40px 20px 20px; color:#555; }
  .welcome-box h2 { color:#185FA5; font-size:22px; margin-bottom:8px; }
  .welcome-box p  { font-size:15px; color:#888; margin-bottom:24px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "ضع_token_هنا")
GITHUB_BASE_URL = "https://models.inference.ai.azure.com"
GITHUB_MODEL    = "gpt-4o"

BU_COLORS = {"ASH": "#185FA5", "SMH": "#0F6E56", "HJH": "#BA7517"}

# ══════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════
@st.cache_resource(show_spinner="Loading data...")
def load_data():
    kb_sheets  = pd.read_excel("Knowledge_base.xlsx", sheet_name=None)
    opd_sheets = pd.read_excel("OPD_dataset.xlsx",    sheet_name=None)
    opd_main   = opd_sheets[list(opd_sheets.keys())[0]].copy()

    if "Month" in opd_main.columns and not pd.api.types.is_datetime64_any_dtype(opd_main["Month"]):
        try: opd_main["Month"] = pd.to_datetime(opd_main["Month"])
        except: pass

    pct_cols = ["Doctor PMS %","No-Show %","Service Leakage %","Cross Referral %",
                "Patient Retention %","Patient Acquisition %","Actual COE Compliance %",
                "Digital Actual CR%","Digital Target CR%"]
    for c in pct_cols:
        if c in opd_main.columns and opd_main[c].max() <= 1.5:
            opd_main[c] = (opd_main[c] * 100).round(2)

    if "Year" in opd_main.columns and "Month No" in opd_main.columns:
        opd_main["Month_Year"] = (opd_main["Year"].astype(str) + "-" +
                                  opd_main["Month No"].astype(str).str.zfill(2))
    return {
        "knowledge_base": kb_sheets,
        "opd_main_df":    opd_main,
        "doctors":        opd_main["Doctor Name"].unique().tolist(),
        "years":          sorted(opd_main["Year"].unique().tolist()),
        "bus":            opd_main["BU"].unique().tolist(),
    }

DATA = load_data()

# ══════════════════════════════════════════════════════
# RESPONSE TYPE DETECTION
# ══════════════════════════════════════════════════════
VISUAL_KEYWORDS = [
    "rank", "top", "bottom", "best", "worst", "compare", "comparison",
    "summary", "trend", "monthly", "yearly", "year summary", "vs",
    "performance", "achievement", "revenue", "cases", "kpi", "dashboard",
    "all doctors", "all bus", "leakage", "no-show", "pms", "retention"
]
TEXT_KEYWORDS = [
    "why", "what does", "what is", "how", "explain", "definition",
    "ليه", "يعني", "كيف", "ما هو", "ما معنى"
]

def detect_response_type(query: str) -> str:
    q = query.lower()
    text_score   = sum(1 for k in TEXT_KEYWORDS   if k in q)
    visual_score = sum(1 for k in VISUAL_KEYWORDS if k in q)
    if text_score > visual_score:
        return "TEXT"
    if visual_score > 0:
        return "VISUAL"
    return "TEXT"


# ══════════════════════════════════════════════════════
# HTML RENDERERS
# ══════════════════════════════════════════════════════

def make_context_badge(label: str) -> str:
    return f'<div class="ctx-badge">{label}</div>'


def make_kpi_card(title: str, bu_values: dict, is_lower_better: bool = False) -> str:
    """bu_values = {"ASH": (value, max_value, display_str), ...}"""
    rows = ""
    for bu, (val, max_val, display) in bu_values.items():
        color  = BU_COLORS.get(bu, "#888")
        pct    = int(val / max_val * 100) if max_val else 0
        rows += f"""
        <div class="bu-row">
          <span class="bu-tag" style="color:{color}">{bu}</span>
          <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
          <span class="bu-num" style="color:{color}">{display}</span>
        </div>"""
    return f"""
    <div class="kpi-card">
      <div class="kpi-name">{title}</div>
      {rows}
    </div>"""


def make_rank_rows(doctors: list) -> str:
    """doctors = [{"rank":1,"name":"Ahmed","pct":94.2,"color":"#0F6E56"}, ...]"""
    rows = ""
    for d in doctors:
        color   = d.get("color", "#185FA5")
        max_pct = doctors[0]["pct"] if doctors else 100
        bar_w   = int(d["pct"] / max_pct * 100) if max_pct else 0
        rows += f"""
        <div class="rank-row">
          <span class="rank-num">#{d['rank']}</span>
          <span class="rank-name">{d['name']}</span>
          <div class="bar-wrap" style="max-width:120px">
            <div class="bar-fill" style="width:{bar_w}%;background:{color}"></div>
          </div>
          <span class="rank-pct" style="color:{color}">{d['pct']:.1f}%</span>
        </div>"""
    return f'<div class="rank-section">{rows}</div>'


def make_sparkline(monthly_values: list, labels: list = None) -> str:
    if not monthly_values:
        return ""
    mx = max(monthly_values) or 1
    bars = ""
    for v in monthly_values:
        h   = max(10, int(v / mx * 32))
        col = "#185FA5" if v == mx else "#B5D4F4"
        bars += f'<div class="spark-bar" style="height:{h}px;background:{col}"></div>'

    lbl_html = ""
    if labels:
        step     = max(1, len(labels)//4)
        selected = [labels[i] for i in range(0, len(labels), step)]
        lbl_html = (
            '<div class="spark-labels">'
            + "".join(f"<span>{l}</span>" for l in selected)
            + "</div>"
        )
    return f'<div class="spark-wrap">{bars}</div>{lbl_html}'


def make_winner_rows(winners: list) -> str:
    """winners = [{"bu":"ASH","desc":"Revenue, Retention","kpis":3}, ...]"""
    rows = ""
    for w in winners:
        color = BU_COLORS.get(w["bu"], "#888")
        rows += f"""
        <div class="winner-row">
          <span style="font-size:14px;color:{color}">★</span>
          <span class="winner-bu" style="color:{color}">{w['bu']}</span>
          <span class="winner-desc">{w['desc']}</span>
          <span class="winner-val" style="color:{color}">{w['kpis']} KPIs</span>
        </div>"""
    return rows


def make_analysis_block(paragraphs: list) -> str:
    content = "".join(f"<p>{p}</p>" for p in paragraphs)
    return f'<div class="analysis-block">{content}</div>'


def make_suggest_chips(chips: list) -> str:
    """chips = [{"label":"...", "prompt":"..."}, ...]"""
    items = "".join(
        f'<a class="chip" href="?q={c["prompt"]}">{c["label"]} ↗</a>'
        for c in chips
    )
    return f'<div class="suggest-row">{items}</div>'


# ══════════════════════════════════════════════════════
# SMART FORMAT — parses LLM raw text → HTML
# ══════════════════════════════════════════════════════

def _parse_number(s: str) -> float:
    s = s.replace(",", "").replace("%", "").strip()
    try:    return float(s)
    except: return 0.0


def _pct_color(pct: float, lower_better: bool = False) -> str:
    if lower_better:
        return "#0F6E56" if pct < 10 else ("#BA7517" if pct < 20 else "#A32D2D")
    return "#0F6E56" if pct >= 90 else ("#BA7517" if pct >= 75 else "#A32D2D")


def format_response(raw: str, query: str, tool_results: dict = None) -> str:
    """
    Decides whether to render a visual dashboard or plain chat bubble.
    tool_results: dict of tool_name -> raw result string (optional, for richer rendering)
    """
    resp_type = detect_response_type(query)

    # ── TEXT response ─────────────────────────────────
    if resp_type == "TEXT":
        clean = raw.strip()
        # light markdown: bold → <b>, newlines → <br>
        clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean)
        clean = clean.replace("\n", "<br>")
        return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{clean}</div></div>'

    # ── VISUAL response ───────────────────────────────
    q_lower = query.lower()

    # ── COMPARE / BU comparison ───────────────────────
    if any(k in q_lower for k in ["compare", "vs", "comparison", "all bus", "ash", "smh", "hjh"]):
        return _render_compare_dashboard(raw, query)

    # ── RANKING / top / bottom ────────────────────────
    if any(k in q_lower for k in ["rank", "top", "best", "worst", "bottom"]):
        return _render_ranking(raw, query)

    # ── TREND / monthly ───────────────────────────────
    if any(k in q_lower for k in ["trend", "monthly", "month"]):
        return _render_trend(raw, query)

    # ── YEAR SUMMARY ──────────────────────────────────
    if any(k in q_lower for k in ["year summary", "summary", "overview"]):
        return _render_year_summary(raw, query)

    # ── DOCTOR PERFORMANCE ────────────────────────────
    if any(k in q_lower for k in ["doctor", "dr.", "performance", "dr "]):
        return _render_doctor(raw, query)

    # fallback: plain bubble
    return _plain_bubble(raw)


# ══════════════════════════════════════════════════════
# VISUAL RENDERERS
# ══════════════════════════════════════════════════════

def _plain_bubble(text: str) -> str:
    clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text.strip())
    clean = clean.replace("\n", "<br>")
    return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{clean}</div></div>'


def _render_compare_dashboard(raw: str, query: str) -> str:
    """Parses BU comparison text → multi-KPI dashboard + analysis."""

    # ── extract KPI values per BU from raw text ──────
    kpi_patterns = {
        "Revenue achievement": (r'(?:revenue|rev).{0,30}?(\d[\d,.]+)%', False),
        "No-show %":           (r'no.?show.{0,20}?(\d[\d,.]+)%', True),
        "Cross referral %":    (r'cross.{0,20}?(\d[\d,.]+)%', False),
        "Patient retention %": (r'retention.{0,20}?(\d[\d,.]+)%', False),
        "Service leakage %":   (r'leakage.{0,20}?(\d[\d,.]+)%', True),
        "Doctor PMS %":        (r'pms.{0,20}?(\d[\d,.]+)%', False),
    }

    # split raw by BU sections
    bu_sections = {}
    for bu in ["ASH", "SMH", "HJH"]:
        pattern = rf'{bu}.*?(?=ASH|SMH|HJH|RANKING|ALL DOCTORS|$)'
        match   = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match:
            bu_sections[bu] = match.group(0)

    # fallback: just show analysis from LLM text
    kpi_cards_html = ""
    if bu_sections:
        kpi_cards = []
        for kpi_name, (pat, lower_better) in kpi_patterns.items():
            bu_vals = {}
            for bu, section in bu_sections.items():
                m = re.search(pat, section, re.IGNORECASE)
                if m:
                    val = _parse_number(m.group(1))
                    bu_vals[bu] = val
            if len(bu_vals) >= 2:
                max_v = max(bu_vals.values()) or 1
                entries = {}
                for bu, v in bu_vals.items():
                    entries[bu] = (v, max_v, f"{v:.1f}%")
                kpi_cards.append(make_kpi_card(kpi_name, entries, lower_better))

        if kpi_cards:
            kpi_cards_html = f'<div class="kpi-grid">{"".join(kpi_cards)}</div>'

    # ── winners ───────────────────────────────────────
    # simple heuristic: count mentions of each BU near positive words
    winners_html = ""
    win_counts = {"ASH": [], "SMH": [], "HJH": []}
    positive_words = ["best", "highest", "top", "أفضل", "أعلى"]
    lines = raw.split("\n")
    for line in lines:
        ll = line.lower()
        for bu in ["ASH", "SMH", "HJH"]:
            if bu.lower() in ll and any(pw in ll for pw in positive_words):
                win_counts[bu].append(line.strip())

    winner_data = [
        {"bu": bu, "desc": f"leads in {len(v)} area(s)", "kpis": len(v)}
        for bu, v in win_counts.items() if v
    ]
    if winner_data:
        winner_data.sort(key=lambda x: -x["kpis"])
        winners_html = f"""
        <div class="section-title">Winner per KPI</div>
        {make_winner_rows(winner_data)}"""

    # ── analysis: strip structured data, keep explanatory text ──
    analysis_lines = []
    skip_patterns  = re.compile(
        r'(={3,}|RANKING|BU COMPARISON|Target|Actual|#\d+|\|\s)', re.IGNORECASE)
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) > 30 and not skip_patterns.search(stripped):
            # convert inline bold + numbers to tags
            stripped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
            stripped = re.sub(r'(\d+\.?\d*%)',
                lambda m: f'<span class="tag-green">{m.group(1)}</span>'
                          if float(m.group(1).replace('%','')) >= 80
                          else (f'<span class="tag-red">{m.group(1)}</span>'
                                if float(m.group(1).replace('%','')) < 50
                                else f'<span class="tag-amber">{m.group(1)}</span>'),
                stripped)
            analysis_lines.append(stripped)

    analysis_html = ""
    if analysis_lines:
        analysis_html = make_analysis_block(analysis_lines[:6])

    # ── suggest chips ─────────────────────────────────
    chips = [
        {"label": "ASH doctors breakdown", "prompt": "Show ASH doctors performance"},
        {"label": "SMH no-show details",   "prompt": "Why is SMH no-show % high?"},
        {"label": "HJH improvement plan",  "prompt": "How to improve HJH revenue achievement?"},
    ]
    chips_html = make_suggest_chips(chips)

    # ── assemble ──────────────────────────────────────
    inner = f"""
    {make_context_badge("comparison · " + query.replace("compare","").strip()[:40])}
    {kpi_cards_html}
    {winners_html}
    {analysis_html}
    {chips_html}
    """
    return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{inner}</div></div>'


def _render_ranking(raw: str, query: str) -> str:
    """Parses ranking text → bar chart ranking + analysis."""
    lines   = raw.split("\n")
    doctors = []

    for line in lines:
        m = re.search(r'#\s*(\d+)\s+Dr\.?\s*([\w\s]+?)\s+([\d,]+\.?\d*)', line)
        if m:
            rank = int(m.group(1))
            name = m.group(2).strip()
            val  = _parse_number(m.group(3))
            doctors.append({"rank": rank, "name": f"Dr. {name}", "raw": val})

    # if values are revenues, convert to achievement % if possible
    if doctors:
        max_val = max(d["raw"] for d in doctors) or 1
        for d in doctors:
            pct = d["raw"] / max_val * 100
            d["pct"]   = pct
            d["color"] = _pct_color(pct)
        ranking_html = make_rank_rows(doctors[:10])
    else:
        ranking_html = f"<pre style='font-size:12px'>{raw[:600]}</pre>"

    # extract metric name from raw
    metric_match = re.search(r'RANKING:\s*(.+?)[\|\n]', raw)
    metric       = metric_match.group(1).strip() if metric_match else "metric"

    # analysis lines
    analysis_lines = [
        l.strip() for l in lines
        if len(l.strip()) > 40 and not re.search(r'(={3,}|#\d+|RANKING)', l)
    ]
    analysis_html = make_analysis_block(analysis_lines[:4]) if analysis_lines else ""

    chips = [
        {"label": "Doctor details", "prompt": f"Show performance of {doctors[0]['name']}" if doctors else "Show doctor performance"},
        {"label": "Compare by BU",  "prompt": "Compare all BUs"},
    ]

    inner = f"""
    {make_context_badge(metric + " · ranking")}
    {ranking_html}
    {analysis_html}
    {make_suggest_chips(chips)}
    """
    return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{inner}</div></div>'


def _render_trend(raw: str, query: str) -> str:
    """Parses monthly trend text → sparkline + KPI cards + analysis."""
    MONTH_MAP = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                 "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    monthly = {}
    for abbr, num in MONTH_MAP.items():
        m = re.search(rf'{abbr}\s+([\d,]+\.?\d*)', raw)
        if m:
            monthly[num] = _parse_number(m.group(1))

    sorted_months = sorted(monthly.keys())
    values = [monthly[k] for k in sorted_months]
    labels = [list(MONTH_MAP.keys())[k-1] for k in sorted_months]

    spark_html = make_sparkline(values, labels) if values else ""

    # summary KPI cards
    kpi_html = ""
    if values:
        avg   = sum(values)/len(values)
        best  = max(values)
        worst = min(values)
        bi    = values.index(best);  best_m  = labels[bi]  if bi < len(labels)  else ""
        wi    = values.index(worst); worst_m = labels[wi]  if wi < len(labels)  else ""

        def fmt(v):
            return f"{v/1_000_000:.2f}M" if v >= 1_000_000 else f"{v/1_000:.0f}K" if v >= 1_000 else f"{v:.0f}"

        kpi_html = f"""
        <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr)">
          <div class="kpi-card"><div class="kpi-name">Best month</div>
            <div style="font-size:14px;font-weight:600;color:#185FA5">{best_m} · {fmt(best)}</div></div>
          <div class="kpi-card"><div class="kpi-name">Worst month</div>
            <div style="font-size:14px;font-weight:600;color:#A32D2D">{worst_m} · {fmt(worst)}</div></div>
          <div class="kpi-card"><div class="kpi-name">Monthly avg</div>
            <div style="font-size:14px;font-weight:600">{fmt(avg)}</div></div>
          <div class="kpi-card"><div class="kpi-name">Months tracked</div>
            <div style="font-size:14px;font-weight:600">{len(values)}</div></div>
        </div>"""

    analysis_lines = [
        l.strip() for l in raw.split("\n")
        if len(l.strip()) > 40 and not re.search(r'(={3,}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Avg|Best|Low)', l)
    ]
    analysis_html = make_analysis_block(analysis_lines[:3]) if analysis_lines else ""

    metric_m = re.search(r'MONTHLY TREND:\s*(.+?)[\|\n]', raw)
    metric   = metric_m.group(1).strip() if metric_m else "metric"

    chips = [
        {"label": "Compare with target",  "prompt": f"Compare {metric} actual vs target"},
        {"label": "Doctor breakdown",     "prompt": f"Which doctor drove the best month?"},
    ]

    inner = f"""
    {make_context_badge(metric + " · monthly trend")}
    {kpi_html}
    <div class="section-title">Monthly breakdown</div>
    {spark_html}
    {analysis_html}
    {make_suggest_chips(chips)}
    """
    return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{inner}</div></div>'


def _render_year_summary(raw: str, query: str) -> str:
    """Parses year summary text → KPI cards grid + analysis."""
    def extract_pct(pattern):
        m = re.search(pattern, raw, re.IGNORECASE)
        return _parse_number(m.group(1)) if m else None

    rev_ach  = extract_pct(r'revenue.*?achievement.*?([\d.]+)%')
    cas_ach  = extract_pct(r'cases.*?achievement.*?([\d.]+)%')
    no_show  = extract_pct(r'no.?show.*?([\d.]+)%')
    leakage  = extract_pct(r'leakage.*?([\d.]+)%')
    pms      = extract_pct(r'pms.*?([\d.]+)%')
    retention= extract_pct(r'retention.*?([\d.]+)%')

    def card(label, val, lower_better=False):
        if val is None: return ""
        if lower_better:
            color = "#0F6E56" if val < 10 else ("#BA7517" if val < 20 else "#A32D2D")
        else:
            color = "#0F6E56" if val >= 90 else ("#BA7517" if val >= 75 else "#A32D2D")
        return f"""
        <div class="kpi-card">
          <div class="kpi-name">{label}</div>
          <div style="font-size:16px;font-weight:700;color:{color}">{val:.1f}%</div>
        </div>"""

    kpi_html = f"""
    <div class="kpi-grid">
      {card("Revenue achievement", rev_ach)}
      {card("Cases achievement", cas_ach)}
      {card("No-show %", no_show, lower_better=True)}
      {card("Service leakage %", leakage, lower_better=True)}
      {card("Doctor PMS %", pms)}
      {card("Patient retention %", retention)}
    </div>"""

    # top / bottom doctor
    top_m    = re.search(r'[Tt]op\s*:?\s*Dr\.?\s*([\w\s]+?)\s*\(([\d.]+)%\)', raw)
    bottom_m = re.search(r'[Bb]ottom\s*:?\s*Dr\.?\s*([\w\s]+?)\s*\(([\d.]+)%\)', raw)
    doctors_html = ""
    if top_m or bottom_m:
        doctors_html = '<div class="section-title">Doctor highlights</div>'
        if top_m:
            doctors_html += f"""
            <div class="winner-row">
              <span style="color:#0F6E56;font-size:14px">↑</span>
              <span class="winner-bu" style="color:#0F6E56">Top</span>
              <span class="winner-desc">Dr. {top_m.group(1).strip()}</span>
              <span class="winner-val" style="color:#0F6E56">{top_m.group(2)}%</span>
            </div>"""
        if bottom_m:
            doctors_html += f"""
            <div class="winner-row">
              <span style="color:#A32D2D;font-size:14px">↓</span>
              <span class="winner-bu" style="color:#A32D2D">Low</span>
              <span class="winner-desc">Dr. {bottom_m.group(1).strip()}</span>
              <span class="winner-val" style="color:#A32D2D">{bottom_m.group(2)}%</span>
            </div>"""

    analysis_lines = [
        l.strip() for l in raw.split("\n")
        if len(l.strip()) > 40 and not re.search(
            r'(={3,}|Target|Actual|Achievement|YEAR SUMMARY|REVENUE|CASES|AVERAGE|DOCTORS|RANKING)', l)
    ]
    analysis_html = make_analysis_block(analysis_lines[:4]) if analysis_lines else ""

    year_m = re.search(r'YEAR SUMMARY:\s*(\d{4})', raw)
    year   = year_m.group(1) if year_m else "year"

    chips = [
        {"label": "Monthly breakdown",   "prompt": f"Monthly revenue trend {year}"},
        {"label": "Doctor rankings",     "prompt": f"Rank all doctors by revenue {year}"},
        {"label": "Compare BUs",         "prompt": f"Compare ASH vs SMH vs HJH in {year}"},
    ]

    inner = f"""
    {make_context_badge(f"year summary · {year}")}
    {kpi_html}
    {doctors_html}
    {analysis_html}
    {make_suggest_chips(chips)}
    """
    return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{inner}</div></div>'


def _render_doctor(raw: str, query: str) -> str:
    """Parses single-doctor report → KPI cards + ranking badge + analysis."""
    def extract_pct(pattern):
        m = re.search(pattern, raw, re.IGNORECASE)
        return _parse_number(m.group(1)) if m else None

    def extract_num(pattern):
        m = re.search(pattern, raw, re.IGNORECASE)
        return _parse_number(m.group(1)) if m else None

    rev_ach  = extract_pct(r'[Aa]chievement\s*:\s*([\d.]+)%')
    cas_ach  = extract_pct(r'[Cc]ases.*?[Aa]chievement\s*:\s*([\d.]+)%')
    pms      = extract_pct(r'PMS.*?([\d.]+)%')
    no_show  = extract_pct(r'[Nn]o.?[Ss]how.*?([\d.]+)%')
    leakage  = extract_pct(r'[Ll]eakage\s*%?\s*:\s*([\d.]+)%')
    retention= extract_pct(r'[Rr]etention.*?([\d.]+)%')

    def card(label, val, lower_better=False, suffix="%"):
        if val is None: return ""
        if lower_better:
            color = "#0F6E56" if val < 10 else ("#BA7517" if val < 20 else "#A32D2D")
        else:
            color = "#0F6E56" if val >= 90 else ("#BA7517" if val >= 75 else "#A32D2D")
        return f"""
        <div class="kpi-card">
          <div class="kpi-name">{label}</div>
          <div style="font-size:16px;font-weight:700;color:{color}">{val:.1f}{suffix}</div>
        </div>"""

    kpi_html = f"""
    <div class="kpi-grid">
      {card("Revenue achievement", rev_ach)}
      {card("Cases achievement", cas_ach)}
      {card("Doctor PMS %", pms)}
      {card("No-show %", no_show, lower_better=True)}
      {card("Service leakage %", leakage, lower_better=True)}
      {card("Patient retention %", retention)}
    </div>"""

    rank_m       = re.search(r'OVERALL RANKING:\s*#?(\d+)\s*of\s*(\d+)', raw)
    rank_html    = ""
    if rank_m:
        r, total = int(rank_m.group(1)), int(rank_m.group(2))
        r_color  = "#0F6E56" if r <= 3 else ("#BA7517" if r <= total//2 else "#A32D2D")
        rank_html = f"""
        <div class="section-title">Overall ranking</div>
        <div class="winner-row">
          <span style="font-size:20px;color:{r_color};font-weight:700">#{r}</span>
          <span class="winner-desc">out of {total} doctors</span>
        </div>"""

    # doctor name
    doc_m    = re.search(r'DOCTOR REPORT:\s*Dr\.?\s*([\w\s]+?)\s*\|', raw)
    doc_name = f"Dr. {doc_m.group(1).strip()}" if doc_m else "Doctor"

    analysis_lines = [
        l.strip() for l in raw.split("\n")
        if len(l.strip()) > 40 and not re.search(
            r'(={3,}|Target|Actual|Achievement|DOCTOR REPORT|REVENUE|CASES|QUALITY|OTHER|OVERALL|#\d+)', l)
    ]
    analysis_html = make_analysis_block(analysis_lines[:4]) if analysis_lines else ""

    chips = [
        {"label": "Monthly trend",      "prompt": f"Monthly revenue trend for {doc_name}"},
        {"label": "Compare with peers", "prompt": f"Compare all doctors by revenue"},
        {"label": "Root cause analysis","prompt": f"Why is no-show % high for {doc_name}?"},
    ]

    inner = f"""
    {make_context_badge(doc_name + " · performance")}
    {kpi_html}
    {rank_html}
    {analysis_html}
    {make_suggest_chips(chips)}
    """
    return f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">{inner}</div></div>'


# ══════════════════════════════════════════════════════
# TOOLS (unchanged from original)
# ══════════════════════════════════════════════════════
METRIC_ALIASES = {
    "revenue":"Total Revenue","total revenue":"Total Revenue",
    "actual revenue":"Total Revenue","target revenue":"Target Revenue",
    "cases":"No. Cases","no. cases":"No. Cases","total cases":"No. Cases",
    "target cases":"Target No. cases","services":"No. Services",
    "charge":"Charge per case","charge per case":"Charge per case",
    "booking":"No. Booking","bookings":"No. Booking",
    "pms":"Doctor PMS %","doctor pms":"Doctor PMS %","doctor pms %":"Doctor PMS %",
    "no show":"No-Show %","no-show":"No-Show %","no-show %":"No-Show %",
    "leakage":"Service Leakage %","service leakage":"Service Leakage %",
    "cross referral":"Cross Referral %","cross referral %":"Cross Referral %",
    "referral":"Cross Referral %","retention":"Patient Retention %",
    "patient retention":"Patient Retention %","acquisition":"Patient Acquisition %",
    "coe":"Actual COE Compliance %","coe compliance":"Actual COE Compliance %",
    "digital cr":"Digital Actual CR%","missed":"No. Missed Opportunity",
    "cancelled":"No. Cancelled Clinics","leakage revenue":"Total Leakage Revenue Losses",
    "total leakage":"Total Leakage Revenue Losses",
}

def _filter_df(year="all", bu="all", doctor="all"):
    df = DATA["opd_main_df"].copy()
    if year != "all":
        try: df = df[df["Year"] == int(year)]
        except: pass
    if bu != "all":
        df = df[df["BU"] == bu.upper()]
    if doctor != "all":
        matched = next((d for d in DATA["doctors"]
                        if d.lower() == doctor.lower() or doctor.lower() in d.lower()), None)
        if matched: df = df[df["Doctor Name"] == matched]
    return df

def _find_col(metric: str) -> str:
    key  = metric.strip().lower()
    if key in METRIC_ALIASES: return METRIC_ALIASES[key]
    skip = {"Year","Month No","Month","Month_Year","BU","Doctor Name"}
    cols = [c for c in DATA["opd_main_df"].columns if c not in skip]
    for c in cols:
        if c.lower() == key: return c
    preferred = [c for c in cols if key in c.lower() and not c.lower().startswith("target")]
    if preferred: return preferred[0]
    for c in cols:
        if key in c.lower(): return c
    return "Total Revenue"

def _fmt(val, col):
    return f"{val:.1f}%" if "%" in col else f"{val:,.0f}"

def search_knowledge_base(query: str) -> str:
    keywords = [w for w in re.split(r'[\s%,]+', query.lower()) if len(w) > 2]
    results  = []
    for sheet_name, df in DATA["knowledge_base"].items():
        for _, row in df.iterrows():
            text = " ".join(str(v) for v in row.values).lower()
            if any(k in text for k in keywords):
                results.append(f"[{sheet_name}] " + " | ".join(f"{c}: {v}" for c, v in row.items()))
    return ("No matching records." if not results
            else f"Found {len(results)} records:\n\n" + "\n".join(results[:30]))

def get_doctor_performance(doctor_name: str, year: str = "all") -> str:
    df = _filter_df(year=year, doctor=doctor_name)
    if df.empty: return f"No data for '{doctor_name}'."
    matched  = df["Doctor Name"].iloc[0]
    t_rev    = df["Target Revenue"].sum(); a_rev = df["Total Revenue"].sum()
    t_cas    = df["Target No. cases"].sum(); a_cas = df["No. Cases"].sum()
    rev_ach  = a_rev / t_rev * 100 if t_rev else 0
    cas_ach  = a_cas / t_cas * 100 if t_cas else 0
    pms = df["Doctor PMS %"].mean(); ns = df["No-Show %"].mean()
    lk  = df["Service Leakage %"].mean(); xcr = df["Cross Referral %"].mean()
    ret = df["Patient Retention %"].mean()
    cpc = df["Charge per case"].mean() if "Charge per case" in df.columns else 0
    cancelled   = df["No. Cancelled Clinics"].sum() if "No. Cancelled Clinics" in df.columns else 0
    leakage_rev = df["Total Leakage Revenue Losses"].sum() if "Total Leakage Revenue Losses" in df.columns else 0
    all_df   = _filter_df(year=year)
    all_docs = all_df.groupby("Doctor Name").agg(A=("Total Revenue","sum"),T=("Target Revenue","sum")).reset_index()
    all_docs["Ach%"] = (all_docs["A"] / all_docs["T"] * 100).round(1)
    all_docs = all_docs.sort_values("Ach%", ascending=False).reset_index(drop=True)
    all_docs["Rank"] = all_docs.index + 1
    my_rank  = all_docs.loc[all_docs["Doctor Name"] == matched, "Rank"].values
    rank_str = f"#{int(my_rank[0])} of {len(all_docs)}" if len(my_rank) else "N/A"
    out = [
        f"DOCTOR REPORT: Dr. {matched} | Period: {'All Years' if year=='all' else year}",
        f"{'='*55}",
        f"REVENUE",
        f"  Target      : {t_rev:>18,.0f}",
        f"  Actual      : {a_rev:>18,.0f}",
        f"  Achievement : {rev_ach:>17.1f}%",
        f"  Gap         : {a_rev-t_rev:>18,.0f}",
        f"CASES",
        f"  Target      : {t_cas:>18,.0f}",
        f"  Actual      : {a_cas:>18,.0f}",
        f"  Achievement : {cas_ach:>17.1f}%",
        f"  Charge/Case : {cpc:>18,.1f}",
        f"QUALITY KPIs",
        f"  PMS %          : {pms:>6.1f}%",
        f"  No-Show %      : {ns:>6.1f}%",
        f"  Leakage %      : {lk:>6.1f}%",
        f"  Cross Referral : {xcr:>6.1f}%",
        f"  Retention %    : {ret:>6.1f}%",
        f"OTHER",
        f"  Cancelled Clinics   : {cancelled:>8,.0f}",
        f"  Leakage Rev Losses  : {leakage_rev:>8,.0f}",
        f"OVERALL RANKING: {rank_str}",
    ]
    return "\n".join(out)

def rank_doctors(metric: str = "Total Revenue", year: str = "all", bu: str = "all", order: str = "desc") -> str:
    df  = _filter_df(year=year, bu=bu)
    if df.empty: return "No data."
    col = _find_col(metric)
    agg = "mean" if "%" in col else "sum"
    grp = (df.groupby("Doctor Name")[col].agg(agg)
             .reset_index().sort_values(col, ascending=(order=="asc")).reset_index(drop=True))
    grp["Rank"] = grp.index + 1
    out = [f"RANKING: {col} | Year: {year} | BU: {bu}", "="*50]
    for _, r in grp.iterrows():
        out.append(f"  #{int(r['Rank']):2}  Dr. {r['Doctor Name']:<12}  {_fmt(r[col], col)}")
    return "\n".join(out)

def compare_all_doctors(year: str = "all", bu: str = "all") -> str:
    df = _filter_df(year=year, bu=bu)
    if df.empty: return "No data."
    g = df.groupby("Doctor Name").agg(
        TR=("Target Revenue","sum"), AR=("Total Revenue","sum"),
        TC=("Target No. cases","sum"), AC=("No. Cases","sum"),
        PMS=("Doctor PMS %","mean"), NS=("No-Show %","mean"),
        LK=("Service Leakage %","mean"), XR=("Cross Referral %","mean"),
        RT=("Patient Retention %","mean")).reset_index()
    g["RevAch"] = (g["AR"] / g["TR"] * 100).round(1)
    g["CasAch"] = (g["AC"] / g["TC"] * 100).round(1)
    g = g.sort_values("RevAch", ascending=False)
    out = [f"ALL DOCTORS | Year: {year} | BU: {bu}", "="*72]
    for _, r in g.iterrows():
        out.append(f"  {r['Doctor Name']:<12} RevAch:{r['RevAch']:.1f}% CasAch:{r['CasAch']:.1f}% "
                   f"PMS:{r['PMS']:.1f}% NoShow:{r['NS']:.1f}% Leak:{r['LK']:.1f}% "
                   f"XRef:{r['XR']:.1f}% Ret:{r['RT']:.1f}%")
    return "\n".join(out)

def get_monthly_trend(metric: str, year: str = "all", bu: str = "all", doctor: str = "all") -> str:
    col = _find_col(metric); agg = "mean" if "%" in col else "sum"
    MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
              7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    years_to_show = DATA["years"] if year == "all" else [int(year)]
    out = [f"MONTHLY TREND: {col} | BU:{bu} | Doctor:{doctor}", "="*55]
    for yr in years_to_show:
        df = _filter_df(year=str(yr), bu=bu, doctor=doctor)
        if df.empty: continue
        monthly = df.groupby("Month No")[col].agg(agg).reset_index().sort_values("Month No")
        out.append(f"\n── {yr} ──")
        vals = []
        for _, row in monthly.iterrows():
            v = row[col]; vals.append(v)
            out.append(f"  {MONTHS.get(int(row['Month No']),'?'):<4}  {_fmt(v, col)}")
        if vals:
            avg = sum(vals)/len(vals); mx = max(vals); mn = min(vals)
            mx_m = MONTHS.get(int(monthly.loc[monthly[col]==mx,"Month No"].iloc[0]),"?")
            mn_m = MONTHS.get(int(monthly.loc[monthly[col]==mn,"Month No"].iloc[0]),"?")
            out += [f"  Avg : {_fmt(avg, col)}", f"  Best: {_fmt(mx, col)} ({mx_m})", f"  Low : {_fmt(mn, col)} ({mn_m})"]
    return "\n".join(out) if len(out) > 2 else "No data."

def compare_business_units(metric: str, year: str, month: int = None) -> str:
    df = _filter_df(year=year)
    if month:
        try: df = df[df["Month No"] == int(month)]
        except: pass
    if df.empty: return "No data."
    col = _find_col(metric); agg = "mean" if "%" in col else "sum"
    res = df.groupby("BU")[col].agg(agg).reset_index().sort_values(col, ascending=False)
    total = res[col].sum() if "%" not in col else None
    out   = [f"BU COMPARISON: {col} | Year:{year}", "="*50]
    for _, r in res.iterrows():
        pct = f"  ({r[col]/total*100:.1f}%)" if total else ""
        out.append(f"  {r['BU']:<5}  {_fmt(r[col], col)}{pct}")
    return "\n".join(out)

def get_year_summary(year: str, bu: str = "all") -> str:
    df = _filter_df(year=year, bu=bu)
    if df.empty: return f"No data for year={year}."
    t_rev = df["Target Revenue"].sum(); a_rev = df["Total Revenue"].sum()
    t_cas = df["Target No. cases"].sum(); a_cas = df["No. Cases"].sum()
    rev_ach = a_rev / t_rev * 100 if t_rev else 0
    cas_ach = a_cas / t_cas * 100 if t_cas else 0
    doc_rev = df.groupby("Doctor Name").agg(AR=("Total Revenue","sum"), TR=("Target Revenue","sum")).reset_index()
    doc_rev["Ach"] = (doc_rev["AR"] / doc_rev["TR"] * 100).round(1)
    doc_rev = doc_rev.sort_values("Ach", ascending=False)
    top = doc_rev.iloc[0]; bottom = doc_rev.iloc[-1]
    out = [
        f"YEAR SUMMARY: {year} | BU: {bu}", "="*50,
        f"REVENUE",
        f"  Target      : {t_rev:>18,.0f}",
        f"  Actual      : {a_rev:>18,.0f}",
        f"  Achievement : {rev_ach:>17.1f}%",
        f"  Gap         : {a_rev-t_rev:>18,.0f}",
        f"CASES",
        f"  Target      : {t_cas:>18,.0f}",
        f"  Actual      : {a_cas:>18,.0f}",
        f"  Achievement : {cas_ach:>17.1f}%",
        f"AVERAGE KPIs",
        f"  PMS %          : {df['Doctor PMS %'].mean():.1f}%",
        f"  No-Show %      : {df['No-Show %'].mean():.1f}%",
        f"  Leakage %      : {df['Service Leakage %'].mean():.1f}%",
        f"  Cross Referral : {df['Cross Referral %'].mean():.1f}%",
        f"  Retention %    : {df['Patient Retention %'].mean():.1f}%",
        f"DOCTORS",
        f"  Top    : Dr. {top['Doctor Name']} ({top['Ach']:.1f}%)",
        f"  Bottom : Dr. {bottom['Doctor Name']} ({bottom['Ach']:.1f}%)",
    ]
    return "\n".join(out)

def get_root_causes_analysis(kpi_name: str, bu: str = "all", year: str = "all") -> str:
    df = _filter_df(year=year, bu=bu); col = _find_col(kpi_name)
    kb = search_knowledge_base(kpi_name)
    out = [f"ROOT CAUSE ANALYSIS: {kpi_name} | BU:{bu} | Year:{year}", "="*55]
    if col in df.columns:
        val = df[col].mean() if "%" in col else df[col].sum()
        out.append(f"Current value: {_fmt(val, col)}")
        by_doc = df.groupby("Doctor Name")[col].agg("mean" if "%" in col else "sum").sort_values(ascending=False)
        out.append("By Doctor:")
        for doc, v in by_doc.items(): out.append(f"  Dr. {doc:<12}  {_fmt(v, col)}")
        if bu == "all":
            by_bu = df.groupby("BU")[col].agg("mean" if "%" in col else "sum").sort_values(ascending=False)
            out.append("By BU:")
            for b, v in by_bu.items(): out.append(f"  {b:<5}  {_fmt(v, col)}")
    out.append(f"\nKnowledge Base:\n{kb[:2000]}")
    return "\n".join(out)

def get_data_summary(query: str = "") -> str:
    df   = DATA["opd_main_df"]
    skip = {"Year","Month No","Month","Month_Year","BU","Doctor Name"}
    kpis = [c for c in df.columns if c not in skip]
    return (f"OPD dataset: {len(df)} rows | Years: {DATA['years']} | BUs: {DATA['bus']}\n"
            f"Doctors: {DATA['doctors']}\nKPIs:\n" +
            "\n".join(f"  {i:2}. {c}" for i, c in enumerate(kpis, 1)))

def list_kpis(query: str = "") -> str:
    skip = {"Year","Month No","Month","Month_Year","BU","Doctor Name"}
    kpis = [c for c in DATA["opd_main_df"].columns if c not in skip]
    return "KPIs:\n" + "\n".join(f"  {i:2}. {c}" for i, c in enumerate(kpis, 1))

TOOL_REGISTRY = {
    "search_knowledge_base":    search_knowledge_base,
    "get_doctor_performance":   get_doctor_performance,
    "rank_doctors":             rank_doctors,
    "compare_all_doctors":      compare_all_doctors,
    "get_monthly_trend":        get_monthly_trend,
    "compare_business_units":   compare_business_units,
    "get_year_summary":         get_year_summary,
    "get_root_causes_analysis": get_root_causes_analysis,
    "get_data_summary":         get_data_summary,
    "list_kpis":                list_kpis,
}

TOOLS_SCHEMA = [
    {"type":"function","function":{"name":"search_knowledge_base","description":"Search KPI definitions, formulas, investigation steps.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"get_doctor_performance","description":"Full performance report for ONE doctor.","parameters":{"type":"object","properties":{"doctor_name":{"type":"string"},"year":{"type":"string"}},"required":["doctor_name"]}}},
    {"type":"function","function":{"name":"rank_doctors","description":"Rank ALL doctors by any KPI.","parameters":{"type":"object","properties":{"metric":{"type":"string"},"year":{"type":"string"},"bu":{"type":"string"},"order":{"type":"string","enum":["desc","asc"]}},"required":[]}}},
    {"type":"function","function":{"name":"compare_all_doctors","description":"Compare ALL doctors side by side.","parameters":{"type":"object","properties":{"year":{"type":"string"},"bu":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"get_monthly_trend","description":"Monthly breakdown of any metric.","parameters":{"type":"object","properties":{"metric":{"type":"string"},"year":{"type":"string"},"bu":{"type":"string"},"doctor":{"type":"string"}},"required":["metric","year"]}}},
    {"type":"function","function":{"name":"compare_business_units","description":"Compare ASH vs SMH vs HJH for any metric.","parameters":{"type":"object","properties":{"metric":{"type":"string"},"year":{"type":"string"},"month":{"type":"integer"}},"required":["metric","year"]}}},
    {"type":"function","function":{"name":"get_year_summary","description":"Full year summary.","parameters":{"type":"object","properties":{"year":{"type":"string"},"bu":{"type":"string"}},"required":["year"]}}},
    {"type":"function","function":{"name":"get_root_causes_analysis","description":"Root cause analysis for a KPI.","parameters":{"type":"object","properties":{"kpi_name":{"type":"string"},"bu":{"type":"string"},"year":{"type":"string"}},"required":["kpi_name"]}}},
    {"type":"function","function":{"name":"get_data_summary","description":"Show available data.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"list_kpis","description":"List all KPI names.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":[]}}},
]

SYSTEM_PROMPT = """You are an expert OPD KPI Analytics Assistant for Andalusia hospital system.
Data covers years 2023, 2024, 2025 across BUs: ASH, SMH, HJH.
Doctors: """ + str(DATA["doctors"]) + """

CRITICAL RULES:
1. ALWAYS call a tool before answering — never guess or invent numbers.
2. When user asks about "top doctor" or "best/worst" WITHOUT specifying a year → use year="all".
3. All percentages are already in % form (e.g. 73.5% not 0.735).
4. Be concise — give exact numbers. Do NOT hallucinate.
5. After the data, write 2-3 sentences of analysis explaining what the numbers mean and what action to take.
6. Use EXACT column names: "Total Revenue", "No. Cases", "No-Show %", "Service Leakage %", "Doctor PMS %", "Patient Retention %", "Cross Referral %".
7. Do not call more than 3 tools per request.
8. Always end your response with 1-2 actionable insights starting with 'Insight:'"""

# ══════════════════════════════════════════════════════
# AGENT
# ══════════════════════════════════════════════════════
def call_github(messages: list) -> dict:
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
    payload = {"model": GITHUB_MODEL, "messages": messages, "tools": TOOLS_SCHEMA,
               "tool_choice": "auto", "temperature": 0, "max_tokens": 1500}
    for attempt in range(1, 4):
        try:
            r = requests.post(f"{GITHUB_BASE_URL}/chat/completions",
                              headers=headers, json=payload, timeout=120)
            if r.status_code == 429:
                time.sleep(min(60, 15 * attempt)); continue
            r.raise_for_status()
            data    = r.json()
            message = data["choices"][0]["message"]
            result  = {"message": {"content": message.get("content") or "", "tool_calls": []}}
            for tc in (message.get("tool_calls") or []):
                result["message"]["tool_calls"].append({
                    "id": tc.get("id",""),
                    "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
                })
            return result
        except Exception as e:
            if attempt == 3:
                return {"message": {"content": f"Error: {e}", "tool_calls": []}}
            time.sleep(5)
    return {"message": {"content": "Max retries.", "tool_calls": []}}

def execute_tool(tool_call: dict) -> str:
    name = tool_call.get("function", {}).get("name", "")
    args = tool_call.get("function", {}).get("arguments", {})
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {}
    func = TOOL_REGISTRY.get(name)
    if not func: return f"Unknown tool: '{name}'"
    try: return func(**args)
    except Exception as e: return f"Tool error: {e}"

def run_agent(user_query: str, chat_history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content in chat_history[-4:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_query})
    for _ in range(6):
        resp       = call_github(messages)
        msg        = resp.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            return msg.get("content", "No response.")
        assistant_msg = {"role": "assistant", "content": msg.get("content") or ""}
        assistant_msg["tool_calls"] = [
            {"id": tc.get("id", f"call_{i}"), "type": "function", "function": tc["function"]}
            for i, tc in enumerate(tool_calls)
        ]
        messages.append(assistant_msg)
        seen = set()
        for idx, tc in enumerate(tool_calls):
            key    = (tc.get("function",{}).get("name",""),
                      json.dumps(tc.get("function",{}).get("arguments",{}), sort_keys=True))
            result = "Already executed." if key in seen else execute_tool(tc)
            if key not in seen: seen.add(key)
            messages.append({"role": "tool", "tool_call_id": tc.get("id","call_0"),
                              "name": tc.get("function",{}).get("name","tool"),
                              "content": result[:3000]})
            if idx < len(tool_calls) - 1: time.sleep(1)
    return "Reached max steps."

# ══════════════════════════════════════════════════════
# STREAMLIT UI
# ══════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Header
st.markdown("""
<div class="chat-header">
  <div style="font-size:28px">📊</div>
  <div>
    <h1>Andalusia OPD Analytics</h1>
    <p>AI-powered KPI Assistant</p>
  </div>
  <div style="margin-left:auto">
    <span class="bu-badge">ASH</span>
    <span class="bu-badge">SMH</span>
    <span class="bu-badge">HJH</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

# Welcome
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-box">
      <h2>Welcome to OPD Analytics 👋</h2>
      <p>Ask me anything about doctors, revenue, KPIs, or performance trends.</p>
    </div>
    """, unsafe_allow_html=True)
    cols = st.columns(2)
    suggestions = [
        "📈 Top doctor by revenue",
        "🏥 Compare ASH vs SMH vs HJH in 2024",
        "👨‍⚕️ Show all doctors KPIs",
        "📅 Monthly revenue trend 2024",
        "🔍 Why is no-show % high?",
        "📊 Year summary for 2024",
    ]
    for i, s in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(s, use_container_width=True, key=f"sug_{i}"):
                st.session_state.pending_query = s.split(" ", 1)[1]
                st.rerun()

# Render history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg-user"><div class="bubble">{msg["content"]}</div></div>',
            unsafe_allow_html=True)
    else:
        # already formatted HTML stored
        st.markdown(msg["content"], unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

user_input = st.chat_input("Ask about doctors, revenue, KPIs...")
if "pending_query" in st.session_state:
    user_input = st.session_state.pop("pending_query")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.rerun()

# Generate response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]
    with st.spinner("Analyzing data..."):
        raw_answer = run_agent(last_query, st.session_state.chat_history)

    # ── format the response smartly ──
    formatted = format_response(raw_answer, last_query)

    st.session_state.messages.append({"role": "assistant", "content": formatted})
    st.session_state.chat_history.append(("user", last_query))
    st.session_state.chat_history.append(("assistant", raw_answer[:400]))
    if len(st.session_state.chat_history) > 8:
        st.session_state.chat_history = st.session_state.chat_history[-8:]
    st.rerun()
