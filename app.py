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
# CUSTOM CSS — Gold/Beige Theme
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&family=Source+Sans+3:wght@300;400;500;600&display=swap');

  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; }

  body, .stApp {
    background: #F9F5ED !important;
    font-family: 'Source Sans 3', sans-serif;
  }

  /* ── Header ── */
  .chat-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: linear-gradient(135deg, #2C1A0E 0%, #5C3A1E 100%);
    color: #F5E6C8;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 24px;
    border-bottom: 2px solid #C9A84C;
    box-shadow: 0 3px 20px rgba(44,26,14,0.25);
  }
  .chat-header h1 {
    margin: 0;
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 600;
    color: #F5E6C8;
    letter-spacing: 0.3px;
  }
  .chat-header p {
    margin: 0;
    font-size: 12px;
    color: #C9A84C;
    font-weight: 300;
    letter-spacing: 0.5px;
  }
  .bu-badge {
    background: rgba(201,168,76,0.2);
    border: 1px solid #C9A84C;
    color: #F5E6C8;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
  }

  /* ── Wrapper ── */
  .chat-wrapper {
    max-width: 860px;
    margin: 0 auto;
    padding: 0 20px 120px 20px;
  }

  /* ── User bubble ── */
  .msg-user {
    display: flex;
    justify-content: flex-end;
    margin: 12px 0;
  }
  .msg-user .bubble {
    background: #5C3A1E;
    color: #F5E6C8;
    padding: 11px 18px;
    border-radius: 20px 20px 4px 20px;
    max-width: 68%;
    font-size: 15px;
    line-height: 1.55;
    font-family: 'Source Sans 3', sans-serif;
  }

  /* ── Bot bubble ── */
  .msg-bot {
    display: flex;
    gap: 12px;
    margin: 12px 0;
    align-items: flex-start;
  }
  .bot-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #F0E0B0;
    border: 1.5px solid #C9A84C;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
  }
  .msg-bot .bubble {
    background: #FFFDF7;
    border: 1px solid #E8D9B0;
    padding: 16px 20px;
    border-radius: 4px 20px 20px 20px;
    max-width: 88%;
    font-size: 15px;
    line-height: 1.75;
    color: #2C1A0E;
    font-family: 'Source Sans 3', sans-serif;
    box-shadow: 0 1px 6px rgba(92,58,30,0.06);
  }

  /* ── KPI Cards grid (inside bot bubble) ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
    margin: 14px 0 8px;
  }
  .kpi-card {
    background: #FBF5E6;
    border: 1px solid #E0C97A;
    border-radius: 10px;
    padding: 12px 14px;
    position: relative;
    overflow: hidden;
  }
  .kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: #C9A84C;
    border-radius: 2px 0 0 2px;
  }
  .kpi-label {
    font-size: 11px;
    color: #8B6D3E;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
    font-weight: 500;
  }
  .kpi-value {
    font-size: 18px;
    font-weight: 600;
    color: #5C3A1E;
    font-family: 'Playfair Display', serif;
  }
  .kpi-value.green  { color: #2E6B3E; }
  .kpi-value.red    { color: #8B1A1A; }
  .kpi-value.orange { color: #8B5A00; }
  .kpi-value.gold   { color: #8B6D00; }
  .kpi-sub {
    font-size: 11px;
    color: #A08050;
    margin-top: 2px;
  }

  /* ── Section header inside bubble ── */
  .section-title {
    font-family: 'Playfair Display', serif;
    font-size: 14px;
    font-weight: 600;
    color: #5C3A1E;
    border-bottom: 1px solid #E0C97A;
    padding-bottom: 6px;
    margin: 16px 0 10px;
    letter-spacing: 0.3px;
  }

  /* ── Doctor row ── */
  .doctor-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid #F0E5C5;
  }
  .rank-badge {
    background: #5C3A1E;
    color: #F5E6C8;
    font-size: 11px;
    font-weight: 600;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .rank-badge.gold { background: #C9A84C; color: #2C1A0E; }
  .doctor-name { font-size: 14px; color: #2C1A0E; flex: 1; font-weight: 500; }
  .ach-bar-wrap { flex: 1; height: 6px; background: #EDE0C0; border-radius: 3px; }
  .ach-bar { height: 100%; border-radius: 3px; background: #C9A84C; }
  .ach-pct { font-size: 13px; font-weight: 600; color: #5C3A1E; min-width: 44px; text-align: right; }

  /* ── Status pill ── */
  .pill {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 20px;
    letter-spacing: 0.3px;
  }
  .pill.green  { background: #D6F0DC; color: #1A5C2A; }
  .pill.red    { background: #F5D5D5; color: #7A1A1A; }
  .pill.orange { background: #FAEAC8; color: #7A5000; }

  /* ── Welcome screen ── */
  .welcome-box {
    text-align: center;
    padding: 48px 20px 28px;
  }
  .welcome-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }
  .welcome-box h2 {
    font-family: 'Playfair Display', serif;
    color: #2C1A0E;
    font-size: 26px;
    margin-bottom: 8px;
    font-weight: 600;
  }
  .welcome-box p {
    font-size: 15px;
    color: #8B6D3E;
    margin-bottom: 0;
    font-weight: 300;
  }

  /* ── Suggestion buttons ── */
  .stButton > button {
    background: #FFFDF7 !important;
    border: 1px solid #D4B96A !important;
    color: #5C3A1E !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    padding: 10px 14px !important;
    transition: all 0.2s ease !important;
    text-align: left !important;
    font-weight: 400 !important;
  }
  .stButton > button:hover {
    background: #F5E6C8 !important;
    border-color: #C9A84C !important;
    color: #2C1A0E !important;
    transform: translateY(-1px);
    box-shadow: 0 3px 10px rgba(92,58,30,0.12) !important;
  }

  /* ── Chat input ── */
  .stChatInput textarea, .stChatInput input {
    background: #FFFDF7 !important;
    border: 1.5px solid #D4B96A !important;
    border-radius: 12px !important;
    color: #2C1A0E !important;
    font-family: 'Source Sans 3', sans-serif !important;
  }
  .stChatInput textarea:focus, .stChatInput input:focus {
    border-color: #C9A84C !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.15) !important;
  }

  /* ── Spinner ── */
  .stSpinner > div { border-top-color: #C9A84C !important; }

  /* ── Code / preformatted inside bubble ── */
  .msg-bot .bubble pre, .msg-bot .bubble code {
    background: #F5EDD5;
    border: 1px solid #E0C97A;
    border-radius: 6px;
    font-size: 13px;
    color: #3A2000;
    padding: 2px 6px;
  }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "ضع_token_هنا")
GITHUB_BASE_URL = "https://models.inference.ai.azure.com"
GITHUB_MODEL    = "gpt-4o"

# ══════════════════════════════════════════════════════
# LOAD DATA  (cached)
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
# RICH HTML RENDERER
# Converts raw text output → styled HTML with KPI cards
# ══════════════════════════════════════════════════════
def _pct_color(label: str, val_str: str) -> str:
    """Return CSS class based on KPI direction."""
    try:
        v = float(val_str.replace("%","").replace(",",""))
    except:
        return ""
    low_is_good = any(x in label.lower() for x in ["no-show","leakage","cancel","missed"])
    if low_is_good:
        if v < 10: return "green"
        if v < 20: return "orange"
        return "red"
    else:
        if v >= 100: return "green"
        if v >= 80:  return "orange"
        return "red"

def _ach_color(ach: float) -> str:
    if ach >= 100: return "green"
    if ach >= 80:  return "orange"
    return "red"

def render_response(text: str) -> str:
    """
    Parse structured text output and convert to rich HTML.
    Detects:
      - DOCTOR REPORT → KPI cards + ranking rows
      - YEAR SUMMARY → KPI cards
      - RANKING → doctor rows with bars
      - ALL DOCTORS → table-style comparison
      - MONTHLY TREND → formatted month list
      - BU COMPARISON → cards per BU
      - Plain text → lightly formatted
    """
    lines = text.strip().split("\n")
    if not lines:
        return f'<span>{text}</span>'

    header = lines[0].upper()

    # ── DOCTOR REPORT ──────────────────────────────────────
    if "DOCTOR REPORT" in header:
        return _render_doctor_report(lines)

    # ── YEAR SUMMARY ───────────────────────────────────────
    if "YEAR SUMMARY" in header:
        return _render_year_summary(lines)

    # ── RANKING ────────────────────────────────────────────
    if header.startswith("RANKING:"):
        return _render_ranking(lines)

    # ── ALL DOCTORS ────────────────────────────────────────
    if "ALL DOCTORS" in header:
        return _render_all_doctors(lines)

    # ── MONTHLY TREND ──────────────────────────────────────
    if "MONTHLY TREND" in header:
        return _render_monthly(lines)

    # ── BU COMPARISON ──────────────────────────────────────
    if "BU COMPARISON" in header:
        return _render_bu(lines)

    # ── ROOT CAUSE ─────────────────────────────────────────
    if "ROOT CAUSE" in header:
        return _render_generic_with_cards(lines)

    # ── Fallback: nicely formatted text ───────────────────
    return _render_plain(lines)


def _kpi_card(label: str, value: str, sub: str = "", color_class: str = "") -> str:
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value {color_class}">{value}</div>
      {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
    </div>"""

def _section(title: str) -> str:
    return f'<div class="section-title">{title}</div>'

def _pill(text: str, color: str) -> str:
    return f'<span class="pill {color}">{text}</span>'

def _parse_kv(line: str):
    """Extract label: value pairs from indented lines like '  Target      : 1,234,567'"""
    m = re.match(r'\s+(.+?)\s*:\s*(.+)', line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None

def _render_doctor_report(lines: list) -> str:
    html = []
    # Title
    title_line = lines[0].replace("DOCTOR REPORT:", "").strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:17px;font-weight:600;color:#2C1A0E;margin-bottom:4px">{title_line}</div>')

    section = None
    rev_cards = []
    cas_cards = []
    kpi_cards = []
    other_cards = []
    ranking_rows = []
    in_ranking = False

    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue

        # Section headers
        if re.match(r'^(REVENUE|CASES|QUALITY KPIs|OTHER|OVERALL RANKING|ALL DOCTORS RANKING)', stripped):
            section = stripped.split(":")[0].strip()
            in_ranking = section == "ALL DOCTORS RANKING"
            continue

        if in_ranking:
            # Lines like: #  1  Dr. Name    85.3%  ← THIS DOCTOR
            m = re.match(r'#\s*(\d+)\s+Dr\.\s+(.+?)\s+([\d.]+%)(.*)', stripped)
            if m:
                rank, name, pct, marker = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
                is_this = "THIS DOCTOR" in marker
                try: ach = float(pct.replace("%",""))
                except: ach = 0
                bar_w = min(100, ach)
                row_style = "background:#FFF8E8;border-radius:6px;padding:4px 6px;" if is_this else ""
                rank_cls = "gold" if rank == "1" else ""
                ranking_rows.append(f"""
                <div class="doctor-row" style="{row_style}">
                  <div class="rank-badge {rank_cls}">#{rank}</div>
                  <div class="doctor-name">Dr. {name}{'&nbsp;★' if is_this else ''}</div>
                  <div class="ach-bar-wrap"><div class="ach-bar" style="width:{bar_w}%"></div></div>
                  <div class="ach-pct">{pct}</div>
                </div>""")
            continue

        label, val = _parse_kv(line)
        if not label: continue

        # Classify into cards
        if section == "REVENUE":
            color = ""
            if label == "Achievement":
                try: ach = float(val.replace("%","").replace("✅","").replace("⚠️","").replace("❌","").strip())
                except: ach = 0
                color = _ach_color(ach)
                val = val.replace("✅","").replace("⚠️","").replace("❌","").strip()
            rev_cards.append(_kpi_card(f"Revenue {label}", val, "", color))

        elif section == "CASES":
            color = ""
            if label == "Achievement":
                try: ach = float(val.replace("%","").replace("✅","").replace("⚠️","").replace("❌","").strip())
                except: ach = 0
                color = _ach_color(ach)
                val = val.replace("✅","").replace("⚠️","").replace("❌","").strip()
            cas_cards.append(_kpi_card(f"Cases {label}", val, "", color))

        elif section == "QUALITY KPIs":
            val_clean = val.replace("✅","").replace("⚠️","").replace("❌","").strip()
            color = _pct_color(label, val_clean)
            kpi_cards.append(_kpi_card(label, val_clean, "", color))

        elif section == "OTHER":
            other_cards.append(_kpi_card(label, val))

        elif section and "RANKING" in section:
            pass  # handled above

    # Assemble
    if rev_cards:
        html.append(_section("💰 Revenue"))
        html.append(f'<div class="kpi-grid">{"".join(rev_cards)}</div>')
    if cas_cards:
        html.append(_section("🏥 Cases"))
        html.append(f'<div class="kpi-grid">{"".join(cas_cards)}</div>')
    if kpi_cards:
        html.append(_section("📊 Quality KPIs"))
        html.append(f'<div class="kpi-grid">{"".join(kpi_cards)}</div>')
    if other_cards:
        html.append(_section("📋 Other Metrics"))
        html.append(f'<div class="kpi-grid">{"".join(other_cards)}</div>')
    if ranking_rows:
        html.append(_section("🏆 All Doctors Ranking"))
        html.append("".join(ranking_rows))

    return "".join(html)


def _render_year_summary(lines: list) -> str:
    html = []
    title_line = lines[0].replace("YEAR SUMMARY:", "").strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:17px;font-weight:600;color:#2C1A0E;margin-bottom:4px">{title_line}</div>')

    section = None
    rev_cards = []
    cas_cards = []
    kpi_cards = []
    ranking_rows = []
    doc_info = []
    in_ranking = False

    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue

        if re.match(r'^(REVENUE|CASES|AVERAGE KPIs|DOCTORS|RANKING)', stripped):
            section = stripped.split(":")[0].strip()
            in_ranking = section == "RANKING"
            continue

        if in_ranking:
            m = re.match(r'Dr\.\s+(.+?)\s+([\d.]+%)', stripped)
            if m:
                name, pct = m.group(1).strip(), m.group(2)
                try: ach = float(pct.replace("%",""))
                except: ach = 0
                bar_w = min(100, ach)
                ranking_rows.append(f"""
                <div class="doctor-row">
                  <div class="doctor-name">Dr. {name}</div>
                  <div class="ach-bar-wrap"><div class="ach-bar" style="width:{bar_w}%"></div></div>
                  <div class="ach-pct">{pct}</div>
                </div>""")
            continue

        label, val = _parse_kv(line)
        if not label: continue

        if section == "REVENUE":
            color = ""
            if label == "Achievement":
                try: ach = float(val.replace("%","").replace("✅","").replace("⚠️","").replace("❌","").strip())
                except: ach = 0
                color = _ach_color(ach)
                val = val.replace("✅","").replace("⚠️","").replace("❌","").strip()
            rev_cards.append(_kpi_card(f"Revenue {label}", val, "", color))
        elif section == "CASES":
            color = ""
            if label == "Achievement":
                try: ach = float(val.replace("%","").replace("✅","").replace("⚠️","").replace("❌","").strip())
                except: ach = 0
                color = _ach_color(ach)
                val = val.replace("✅","").replace("⚠️","").replace("❌","").strip()
            cas_cards.append(_kpi_card(f"Cases {label}", val, "", color))
        elif section == "AVERAGE KPIs":
            val_clean = val.strip()
            color = _pct_color(label, val_clean)
            kpi_cards.append(_kpi_card(label, val_clean, "", color))
        elif section == "DOCTORS":
            doc_info.append(f'<div style="font-size:14px;color:#5C3A1E;padding:4px 0">{"🥇" if "Top" in label else "🔻"} <b>{label}:</b> {val}</div>')

    if rev_cards:
        html.append(_section("💰 Revenue"))
        html.append(f'<div class="kpi-grid">{"".join(rev_cards)}</div>')
    if cas_cards:
        html.append(_section("🏥 Cases"))
        html.append(f'<div class="kpi-grid">{"".join(cas_cards)}</div>')
    if kpi_cards:
        html.append(_section("📊 Average KPIs"))
        html.append(f'<div class="kpi-grid">{"".join(kpi_cards)}</div>')
    if doc_info:
        html.append(_section("👨‍⚕️ Doctors"))
        html.append("".join(doc_info))
    if ranking_rows:
        html.append(_section("🏆 Ranking"))
        html.append("".join(ranking_rows))

    return "".join(html)


def _render_ranking(lines: list) -> str:
    html = []
    title = lines[0].replace("RANKING:", "").strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:16px;font-weight:600;color:#2C1A0E;margin-bottom:12px">🏆 {title}</div>')

    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue
        m = re.match(r'#\s*(\d+)\s+Dr\.\s+(.+?)\s+([\S,%.]+)\s*$', stripped)
        if m:
            rank, name, val = m.group(1), m.group(2).strip(), m.group(3)
            try:
                num = float(val.replace("%","").replace(",",""))
                bar_pct = min(100, (num / 100)) if "%" not in val else min(100, num)
            except:
                bar_pct = 50
            rank_cls = "gold" if rank == "1" else ""
            html.append(f"""
            <div class="doctor-row">
              <div class="rank-badge {rank_cls}">#{rank}</div>
              <div class="doctor-name">Dr. {name}</div>
              <div class="ach-bar-wrap"><div class="ach-bar" style="width:{bar_pct}%"></div></div>
              <div class="ach-pct">{val}</div>
            </div>""")

    return "".join(html)


def _render_all_doctors(lines: list) -> str:
    html = []
    title = lines[0].strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:16px;font-weight:600;color:#2C1A0E;margin-bottom:12px">👨‍⚕️ {title}</div>')

    # Table header + rows
    table_rows = []
    header_row = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue
        if stripped.startswith("Doctor"):
            # Header
            cols = stripped.split()
            header_row = cols
            continue
        if stripped.startswith("-"): continue
        if re.match(r'\w', stripped) and stripped != lines[0].strip():
            # Data row: Name RevAch% CasAch% PMS% NoShow% Leak% XRef% Ret%
            parts = stripped.split()
            if len(parts) >= 5:
                table_rows.append(parts)

    if table_rows:
        headers = ["Doctor","RevAch%","CasAch%","PMS%","NoShow%","Leak%","XRef%","Ret%"]
        th_style = "padding:7px 10px;font-size:11px;color:#8B6D3E;text-transform:uppercase;letter-spacing:0.4px;font-weight:600;border-bottom:2px solid #E0C97A;white-space:nowrap"
        td_style = "padding:7px 10px;font-size:13px;color:#2C1A0E;border-bottom:1px solid #F0E5C5"

        thead = f'<tr>{"".join(f"<th style=\"{th_style}\">{h}</th>" for h in headers)}</tr>'
        tbody_rows = []
        for parts in table_rows:
            cells = f'<td style="{td_style};font-weight:500">{parts[0]}</td>'
            for p in parts[1:8]:
                try: v = float(p.replace("%",""))
                except: v = 0
                color = "#2E6B3E" if v >= 100 else "#8B5A00" if v >= 80 else "#8B1A1A"
                cells += f'<td style="{td_style};color:{color};font-weight:500">{p}</td>'
            tbody_rows.append(f"<tr>{cells}</tr>")

        html.append(f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;background:#FFFDF7;border-radius:10px;overflow:hidden"><thead style="background:#FBF5E6">{thead}</thead><tbody>{"".join(tbody_rows)}</tbody></table></div>')
    else:
        html.append(_render_plain(lines[1:]))

    return "".join(html)


def _render_monthly(lines: list) -> str:
    html = []
    title = lines[0].replace("MONTHLY TREND:", "").strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:16px;font-weight:600;color:#2C1A0E;margin-bottom:12px">📅 {title}</div>')

    year_block = []
    current_year = None

    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue
        # Year header
        m_yr = re.match(r'── (\d{4}) ──', stripped)
        if m_yr:
            if year_block and current_year:
                html.append(_month_block(current_year, year_block))
                year_block = []
            current_year = m_yr.group(1)
            continue
        year_block.append(stripped)

    if year_block and current_year:
        html.append(_month_block(current_year, year_block))

    return "".join(html)


def _month_block(year: str, lines: list) -> str:
    html = [f'<div style="font-size:13px;font-weight:600;color:#8B6D3E;text-transform:uppercase;letter-spacing:0.5px;margin:12px 0 6px">{year}</div>']
    cards = []
    summary = []
    for line in lines:
        # Month row: Jan  1,234,567
        m = re.match(r'([A-Za-z]{3,4})\s+([\d,%.]+)', line)
        if m:
            mon, val = m.group(1), m.group(2)
            cards.append(f'<div class="kpi-card"><div class="kpi-label">{mon}</div><div class="kpi-value" style="font-size:14px">{val}</div></div>')
        elif line.startswith("Avg") or line.startswith("Best") or line.startswith("Low"):
            label, val = line.split(":")[0].strip(), line.split(":",1)[1].strip() if ":" in line else ""
            icon = "📈" if "Best" in label else "📉" if "Low" in label else "≈"
            summary.append(f'<span style="font-size:13px;color:#8B6D3E;margin-right:16px">{icon} <b>{label}:</b> {val}</span>')

    if cards:
        html.append(f'<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(80px,1fr))">{"".join(cards)}</div>')
    if summary:
        html.append(f'<div style="margin-top:8px;padding:8px 0">{"".join(summary)}</div>')

    return "".join(html)


def _render_bu(lines: list) -> str:
    html = []
    title = lines[0].replace("BU COMPARISON:", "").strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:16px;font-weight:600;color:#2C1A0E;margin-bottom:12px">🏥 {title}</div>')

    cards = []
    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue
        label, val = _parse_kv(line)
        if label:
            pct_m = re.search(r'\((.+?)\)', val)
            sub = pct_m.group(1) if pct_m else ""
            val_clean = val.split("(")[0].strip()
            cards.append(_kpi_card(label, val_clean, sub))

    if cards:
        html.append(f'<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr))">{"".join(cards)}</div>')

    return "".join(html)


def _render_generic_with_cards(lines: list) -> str:
    html = []
    title = lines[0].strip()
    html.append(f'<div style="font-family:\'Playfair Display\',serif;font-size:16px;font-weight:600;color:#2C1A0E;margin-bottom:10px">{title}</div>')
    cards = []
    other = []
    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("="): continue
        label, val = _parse_kv(line)
        if label and val:
            color = _pct_color(label, val)
            cards.append(_kpi_card(label, val, "", color))
        else:
            other.append(f'<div style="font-size:14px;color:#5C3A1E;line-height:1.7">{stripped}</div>')

    if cards:
        html.append(f'<div class="kpi-grid">{"".join(cards)}</div>')
    if other:
        html.append("".join(other))
    return "".join(html)


def _render_plain(lines) -> str:
    """Lightly format plain text — convert key:value lines to small cards, rest as prose."""
    html = []
    cards = []
    prose = []

    for line in lines:
        if not line.strip(): continue
        label, val = _parse_kv(line)
        if label and val:
            color = _pct_color(label, val)
            cards.append(_kpi_card(label, val, "", color))
        else:
            if cards:
                html.append(f'<div class="kpi-grid">{"".join(cards)}</div>')
                cards = []
            clean = line.strip().replace("=","").strip()
            if clean:
                if re.match(r'^[A-Z][A-Z\s]+:?$', clean):
                    if prose:
                        html.append(f'<p style="font-size:15px;color:#2C1A0E;line-height:1.7;margin:0 0 8px">{"".join(prose)}</p>')
                        prose = []
                    html.append(_section(clean.rstrip(":")))
                else:
                    prose.append(f'{clean} ')

    if cards:
        html.append(f'<div class="kpi-grid">{"".join(cards)}</div>')
    if prose:
        html.append(f'<p style="font-size:15px;color:#2C1A0E;line-height:1.7;margin:0">{" ".join(prose)}</p>')

    return "".join(html) if html else f'<p style="font-size:15px;color:#2C1A0E;line-height:1.7">{" ".join(l.strip() for l in lines if l.strip())}</p>'


# ══════════════════════════════════════════════════════
# HELPERS + TOOLS  (unchanged logic)
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
        if matched:
            df = df[df["Doctor Name"] == matched]
    return df

def _find_col(metric: str) -> str:
    key = metric.strip().lower()
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
    if df.empty: return f"No data for '{doctor_name}'. Available: {DATA['doctors']}"
    matched = df["Doctor Name"].iloc[0]
    t_rev = df["Target Revenue"].sum(); a_rev = df["Total Revenue"].sum()
    t_cas = df["Target No. cases"].sum(); a_cas = df["No. Cases"].sum()
    rev_ach = a_rev / t_rev * 100 if t_rev else 0
    cas_ach = a_cas / t_cas * 100 if t_cas else 0
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
        f"{'='*55}",
        "ALL DOCTORS RANKING:",
    ]
    for _, r in all_docs.iterrows():
        marker = "  ← THIS DOCTOR" if r["Doctor Name"] == matched else ""
        out.append(f"  #{int(r['Rank']):2}  Dr. {r['Doctor Name']:<12}  {r['Ach%']:>5.1f}%{marker}")
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
    header = f"  {'Doctor':<12} {'RevAch%':>8} {'CasAch%':>8} {'PMS%':>6} {'NoShow%':>8} {'Leak%':>6} {'XRef%':>7} {'Ret%':>6}"
    out = [f"ALL DOCTORS | Year: {year} | BU: {bu}", "="*72, header, "  "+"-"*68]
    for _, r in g.iterrows():
        out.append(f"  {r['Doctor Name']:<12} {r['RevAch']:>7.1f}% {r['CasAch']:>7.1f}% "
                   f"{r['PMS']:>5.1f}% {r['NS']:>7.1f}% {r['LK']:>5.1f}% "
                   f"{r['XR']:>6.1f}% {r['RT']:>5.1f}%")
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
    out = [f"BU COMPARISON: {col} | Year:{year}", "="*50]
    for _, r in res.iterrows():
        pct = f"  ({r[col]/total*100:.1f}% of total)" if total else ""
        out.append(f"  {r['BU']:<5}  : {_fmt(r[col], col)}{pct}")
    if total and len(res) > 1:
        out.append(f"  {'TOTAL':<5}  : {total:,.0f}")
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
        "RANKING:",
    ]
    for _, r in doc_rev.iterrows():
        out.append(f"Dr. {r['Doctor Name']:<12}  {r['Ach']:>5.1f}%")
    return "\n".join(out)

def get_root_causes_analysis(kpi_name: str, bu: str = "all", year: str = "all") -> str:
    df = _filter_df(year=year, bu=bu); col = _find_col(kpi_name)
    kb = search_knowledge_base(kpi_name)
    out = [f"ROOT CAUSE ANALYSIS: {kpi_name} | BU:{bu} | Year:{year}", "="*55]
    if col in df.columns:
        val = df[col].mean() if "%" in col else df[col].sum()
        out.append(f"  Current value : {_fmt(val, col)}")
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
    df = DATA["opd_main_df"]
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
5. Format your answers clearly with sections and bullet points when presenting data.
6. Use EXACT column names: "Total Revenue", "No. Cases", "No-Show %", "Service Leakage %", "Doctor PMS %", "Patient Retention %", "Cross Referral %".
7. Do not call more than 3 tools per request.
8. Return the raw tool output directly without modifying it — the UI will render it."""

# ══════════════════════════════════════════════════════
# AGENT CALL
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

    last_tool_output = ""

    for _ in range(6):
        resp       = call_github(messages)
        msg        = resp.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            # If model produced final text AND we have a tool output, prefer tool output
            final_text = msg.get("content", "No response.")
            return last_tool_output if last_tool_output else final_text

        assistant_msg = {"role": "assistant", "content": msg.get("content") or ""}
        assistant_msg["tool_calls"] = [
            {"id": tc.get("id", f"call_{i}"), "type": "function", "function": tc["function"]}
            for i, tc in enumerate(tool_calls)
        ]
        messages.append(assistant_msg)

        seen = set()
        for idx, tc in enumerate(tool_calls):
            key = (tc.get("function",{}).get("name",""),
                   json.dumps(tc.get("function",{}).get("arguments",{}), sort_keys=True))
            result = "Already executed." if key in seen else execute_tool(tc)
            if key not in seen:
                seen.add(key)
                last_tool_output = result  # store last real tool result
            messages.append({"role": "tool", "tool_call_id": tc.get("id","call_0"),
                              "name": tc.get("function",{}).get("name","tool"),
                              "content": result[:3000]})
            if idx < len(tool_calls) - 1: time.sleep(1)

    return last_tool_output or "Reached max steps."

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
  <div style="font-size:26px">🏥</div>
  <div>
    <h1>Andalusia OPD Analytics</h1>
    <p>AI-powered KPI Intelligence Dashboard</p>
  </div>
  <div style="margin-left:auto;display:flex;gap:6px">
    <span class="bu-badge">ASH</span>
    <span class="bu-badge">SMH</span>
    <span class="bu-badge">HJH</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

# Welcome screen
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-box">
      <div class="welcome-icon">📊</div>
      <h2>Welcome to OPD Analytics</h2>
      <p>Ask me anything about doctors, revenue, KPIs, or performance trends across all business units.</p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    suggestions = [
        ("📈", "Top doctor by revenue"),
        ("🏥", "Compare all BUs in 2024"),
        ("👨‍⚕️", "Show all doctors KPIs"),
        ("📅", "Monthly revenue trend 2024"),
        ("🔍", "Why is no-show % high?"),
        ("📊", "Year summary for 2024"),
    ]
    for i, (icon, label) in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(f"{icon} {label}", use_container_width=True, key=f"sug_{i}"):
                st.session_state.pending_query = label
                st.rerun()

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg-user">
          <div class="bubble">{msg["content"]}</div>
        </div>""", unsafe_allow_html=True)
    else:
        rendered = render_response(msg["content"])
        st.markdown(f"""
        <div class="msg-bot">
          <div class="bot-avatar">✦</div>
          <div class="bubble">{rendered}</div>
        </div>""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input bar
user_input = st.chat_input("Ask about doctors, revenue, KPIs...")

if "pending_query" in st.session_state:
    user_input = st.session_state.pop("pending_query")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]
    with st.spinner("Analyzing data..."):
        answer = run_agent(last_query, st.session_state.chat_history)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.chat_history.append(("user", last_query))
    st.session_state.chat_history.append(("assistant", answer[:400]))
    if len(st.session_state.chat_history) > 8:
        st.session_state.chat_history = st.session_state.chat_history[-8:]
    st.rerun()
