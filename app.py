import re, json, requests, pandas as pd
import time, os
import streamlit as st

st.set_page_config(
    page_title="Andalusia OPD Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════
# GLOBAL CSS  (layout only — no component classes)
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "ضع_token_هنا")
GITHUB_BASE_URL = "https://models.inference.ai.azure.com"
GITHUB_MODEL    = "gpt-4o"
BU_COLORS       = {"ASH": "#185FA5", "SMH": "#0F6E56", "HJH": "#BA7517"}

# ══════════════════════════════════════════════════════
# INLINE STYLE HELPERS
# ══════════════════════════════════════════════════════
S = {
    "wrap":        "max-width:860px;margin:0 auto;padding:0 16px 120px;font-family:'Segoe UI',sans-serif;",
    "user_row":    "display:flex;justify-content:flex-end;margin:10px 0;",
    "user_bub":    "background:#185FA5;color:white;padding:10px 16px;border-radius:18px 18px 4px 18px;max-width:70%;font-size:14px;line-height:1.5;",
    "bot_row":     "display:flex;gap:10px;margin:10px 0;align-items:flex-start;",
    "bot_avatar":  "width:32px;height:32px;border-radius:50%;background:#E6F1FB;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;margin-top:4px;",
    "bot_bub":     "background:#F5F7FA;border:1px solid #E8ECF0;padding:14px 18px;border-radius:4px 18px 18px 18px;flex:1;font-size:14px;line-height:1.75;color:#1a1a2e;",
    "ctx_badge":   "display:inline-block;background:#E6F1FB;color:#0C447C;border-radius:20px;padding:3px 10px;font-size:11px;font-weight:600;margin-bottom:12px;",
    "kpi_grid":    "display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:14px;",
    "kpi_card":    "background:white;border:1px solid #E8ECF0;border-radius:10px;padding:10px 12px;",
    "kpi_name":    "font-size:10px;color:#888;margin-bottom:6px;",
    "bu_row":      "display:flex;align-items:center;gap:6px;margin-bottom:3px;",
    "bar_wrap":    "flex:1;height:5px;background:#E8ECF0;border-radius:3px;",
    "sec_title":   "font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em;margin:12px 0 6px;",
    "rank_row":    "display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #F0F2F5;font-size:12px;",
    "winner_row":  "display:flex;align-items:center;gap:8px;padding:6px 10px;background:white;border:1px solid #E8ECF0;border-radius:8px;margin-bottom:5px;font-size:12px;",
    "analysis":    "background:white;border-left:3px solid #185FA5;border-radius:0 8px 8px 0;padding:12px 14px;margin-top:12px;line-height:1.8;font-size:13px;color:#1a1a2e;",
    "chip_row":    "display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;",
    "chip":        "display:inline-block;border:1px solid #dde2ea;border-radius:20px;padding:5px 12px;font-size:11px;color:#555;background:white;text-decoration:none;",
    "spark_wrap":  "display:flex;align-items:flex-end;gap:3px;height:36px;margin:8px 0 2px;",
    "spark_labels":"display:flex;justify-content:space-between;font-size:9px;color:#aaa;margin-bottom:8px;",
    "divider":     "border:none;border-top:1px solid #F0F2F5;margin:12px 0;",
}

def tag(el, style_key, content, extra=""):
    return f"<{el} style='{S[style_key]}{extra}'>{content}</{el}>"

def bot_bubble(inner_html):
    avatar = f"<div style='{S['bot_avatar']}'>🤖</div>"
    bubble = f"<div style='{S['bot_bub']}'>{inner_html}</div>"
    return f"<div style='{S['bot_row']}'>{avatar}{bubble}</div>"

def ctx_badge(label):
    return f"<div style='{S['ctx_badge']}'>{label}</div>"

def sec_title(t):
    return f"<div style='{S['sec_title']}'>{t}</div>"

def divider():
    return f"<hr style='{S['divider']}'>"

def analysis_block(paragraphs):
    if not paragraphs:
        return ""
    ps = "".join(f"<p style='margin:0 0 8px;'>{p}</p>" for p in paragraphs)
    return f"<div style='{S['analysis']}'>{ps}</div>"

def suggest_chips(chips):
    items = "".join(
        f"<a style='{S['chip']}' href='?q={c[\"prompt\"]}'>{c['label']} ↗</a>"
        for c in chips
    )
    return f"<div style='{S['chip_row']}'>{items}</div>"

def kpi_card_simple(label, value, color="#185FA5"):
    return (
        f"<div style='{S['kpi_card']}'>"
        f"<div style='{S['kpi_name']}'>{label}</div>"
        f"<div style='font-size:16px;font-weight:700;color:{color};'>{value}</div>"
        f"</div>"
    )

def kpi_card_bu(label, bu_values):
    """bu_values = [{"bu":"ASH","val":94,"display":"94%","color":"#185FA5"}, ...]"""
    rows = ""
    max_v = max((b["val"] for b in bu_values), default=1) or 1
    for b in bu_values:
        pct = int(b["val"] / max_v * 100)
        rows += (
            f"<div style='{S['bu_row']}'>"
            f"<span style='font-size:10px;font-weight:700;width:28px;color:{b['color']};'>{b['bu']}</span>"
            f"<div style='{S['bar_wrap']}'>"
            f"<div style='height:100%;border-radius:3px;width:{pct}%;background:{b['color']};'></div>"
            f"</div>"
            f"<span style='font-size:11px;font-weight:600;min-width:38px;text-align:right;color:{b['color']};'>{b['display']}</span>"
            f"</div>"
        )
    return (
        f"<div style='{S['kpi_card']}'>"
        f"<div style='{S['kpi_name']}'>{label}</div>"
        f"{rows}"
        f"</div>"
    )

def rank_rows(doctors):
    """doctors=[{"rank":1,"name":"Dr. X","pct":94.2,"color":"#0F6E56"}]"""
    rows = ""
    max_p = doctors[0]["pct"] if doctors else 1
    for d in doctors:
        bar_w = int(d["pct"] / max_p * 100) if max_p else 0
        rows += (
            f"<div style='{S['rank_row']}'>"
            f"<span style='color:#aaa;font-size:10px;width:18px;'>#{d['rank']}</span>"
            f"<span style='flex:1;color:#1a1a2e;'>{d['name']}</span>"
            f"<div style='{S['bar_wrap']}max-width:120px;'>"
            f"<div style='height:100%;border-radius:3px;width:{bar_w}%;background:{d['color']};'></div>"
            f"</div>"
            f"<span style='font-weight:700;min-width:42px;text-align:right;color:{d['color']};'>{d['pct']:.1f}%</span>"
            f"</div>"
        )
    return rows

def winner_rows(winners):
    rows = ""
    for w in winners:
        color = BU_COLORS.get(w["bu"], "#888")
        rows += (
            f"<div style='{S['winner_row']}'>"
            f"<span style='font-size:14px;color:{color};'>★</span>"
            f"<span style='font-weight:700;min-width:32px;color:{color};'>{w['bu']}</span>"
            f"<span style='color:#666;flex:1;'>{w['desc']}</span>"
            f"<span style='font-weight:600;color:{color};'>{w['kpis']} KPIs</span>"
            f"</div>"
        )
    return rows

def sparkline(values, labels=None):
    if not values:
        return ""
    mx = max(values) or 1
    bars = ""
    for v in values:
        h   = max(8, int(v / mx * 36))
        col = "#185FA5" if v == mx else "#B5D4F4"
        bars += f"<div style='flex:1;height:{h}px;background:{col};border-radius:2px 2px 0 0;'></div>"
    lbl_html = ""
    if labels:
        step     = max(1, len(labels)//4)
        selected = [labels[i] for i in range(0, len(labels), step)]
        lbl_html = (
            f"<div style='{S['spark_labels']}'>"
            + "".join(f"<span>{l}</span>" for l in selected)
            + "</div>"
        )
    return f"<div style='{S['spark_wrap']}'>{bars}</div>{lbl_html}"

# ══════════════════════════════════════════════════════
# RESPONSE TYPE DETECTION
# ══════════════════════════════════════════════════════
VISUAL_KW = ["rank","top","bottom","best","worst","compare","comparison",
             "summary","trend","monthly","yearly","year summary","vs",
             "performance","achievement","revenue","cases","kpi","dashboard",
             "all doctors","all bus","leakage","no-show","pms","retention"]
TEXT_KW   = ["why","what does","what is","how","explain","definition",
             "ليه","يعني","كيف","ما هو","ما معنى"]

def detect_type(query):
    q  = query.lower()
    ts = sum(1 for k in TEXT_KW   if k in q)
    vs = sum(1 for k in VISUAL_KW if k in q)
    return "TEXT" if ts > vs else ("VISUAL" if vs > 0 else "TEXT")

# ══════════════════════════════════════════════════════
# NUMBER HELPERS
# ══════════════════════════════════════════════════════
def parse_num(s):
    try:    return float(str(s).replace(",","").replace("%","").strip())
    except: return 0.0

def pct_color(v, lower_better=False):
    if lower_better:
        return "#0F6E56" if v < 10 else ("#BA7517" if v < 20 else "#A32D2D")
    return "#0F6E56" if v >= 90 else ("#BA7517" if v >= 75 else "#A32D2D")

def fmt_big(v):
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"{v/1_000:.0f}K"
    return f"{v:.0f}"

# ══════════════════════════════════════════════════════
# FORMAT RESPONSE  → HTML string
# ══════════════════════════════════════════════════════
def format_response(raw, query):
    if detect_type(query) == "TEXT":
        clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', raw.strip())
        clean = clean.replace("\n", "<br>")
        return bot_bubble(clean)

    q = query.lower()
    if any(k in q for k in ["compare","vs"," ash"," smh"," hjh","all bus","business unit"]):
        return _render_compare(raw, query)
    if any(k in q for k in ["rank","top","best","worst","bottom"]):
        return _render_ranking(raw, query)
    if any(k in q for k in ["trend","monthly","month"]):
        return _render_trend(raw, query)
    if any(k in q for k in ["year summary","summary","overview"]):
        return _render_year_summary(raw, query)
    if any(k in q for k in ["doctor","dr.","dr ","performance"]):
        return _render_doctor(raw, query)
    return _render_plain(raw)

def _render_plain(raw):
    clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', raw.strip())
    clean = clean.replace("\n","<br>")
    return bot_bubble(clean)

# ── COMPARE ──────────────────────────────────────────
def _render_compare(raw, query):
    KPIs = [
        ("Revenue achievement", r'(?:revenue|rev).{0,40}?([\d.]+)%', False),
        ("No-show %",           r'no.?show.{0,25}?([\d.]+)%',        True),
        ("Cross referral %",    r'cross.{0,25}?([\d.]+)%',           False),
        ("Patient retention %", r'retention.{0,25}?([\d.]+)%',       False),
        ("Service leakage %",   r'leakage.{0,25}?([\d.]+)%',         True),
        ("Doctor PMS %",        r'pms.{0,25}?([\d.]+)%',             False),
    ]

    # split raw into per-BU sections
    bu_sections = {}
    for bu in ["ASH","SMH","HJH"]:
        m = re.search(rf'\b{bu}\b.*?(?=\bASH\b|\bSMH\b|\bHJH\b|RANKING|ALL DOCTORS|$)',
                      raw, re.DOTALL|re.IGNORECASE)
        if m: bu_sections[bu] = m.group(0)

    cards_html = ""
    win_counts = {bu: 0 for bu in ["ASH","SMH","HJH"]}

    for kpi_name, pat, lower_better in KPIs:
        bu_data = []
        for bu in ["ASH","SMH","HJH"]:
            section = bu_sections.get(bu, raw)
            m       = re.search(pat, section, re.IGNORECASE)
            if m:
                v = parse_num(m.group(1))
                bu_data.append({"bu": bu, "val": v,
                                 "display": f"{v:.1f}%",
                                 "color": BU_COLORS[bu]})
        if len(bu_data) >= 2:
            # find winner
            winner = min(bu_data, key=lambda x: x["val"]) if lower_better \
                     else max(bu_data, key=lambda x: x["val"])
            win_counts[winner["bu"]] += 1
            cards_html += kpi_card_bu(kpi_name, bu_data)

    grid_html = f"<div style='{S['kpi_grid']}'>{cards_html}</div>" if cards_html else ""

    # winners summary
    winner_data = [
        {"bu": bu, "desc": "leads in performance", "kpis": cnt}
        for bu, cnt in win_counts.items() if cnt > 0
    ]
    winner_data.sort(key=lambda x: -x["kpis"])
    winners_html = ""
    if winner_data:
        winners_html = sec_title("Winner per KPI") + winner_rows(winner_data)

    # analysis lines from LLM
    skip_pat = re.compile(r'(={3,}|RANKING|BU COMPARISON|Target|Actual|#\d+)', re.IGNORECASE)
    a_lines  = [l.strip() for l in raw.split("\n")
                if len(l.strip()) > 35 and not skip_pat.search(l)]
    a_lines  = _tag_pcts(a_lines[:5])

    label = "comparison · " + re.sub(r'compare|in\s*\d{4}','',query,flags=re.IGNORECASE).strip()[:40]

    chips = [
        {"label":"ASH doctors", "prompt":"Show ASH doctors performance"},
        {"label":"SMH no-show", "prompt":"Why is SMH no-show % high?"},
        {"label":"HJH revenue", "prompt":"How to improve HJH revenue achievement?"},
    ]

    inner = (ctx_badge(label) + grid_html + winners_html
             + analysis_block(a_lines) + suggest_chips(chips))
    return bot_bubble(inner)

# ── RANKING ───────────────────────────────────────────
def _render_ranking(raw, query):
    doctors = []
    for line in raw.split("\n"):
        m = re.search(r'#\s*(\d+)\s+Dr\.?\s*([\w\s]+?)\s+([\d,.]+)', line)
        if m:
            rank = int(m.group(1))
            name = m.group(2).strip()
            val  = parse_num(m.group(3))
            doctors.append({"rank": rank, "name": f"Dr. {name}", "raw": val})

    rows_html = ""
    if doctors:
        max_v = max(d["raw"] for d in doctors) or 1
        for d in doctors:
            d["pct"]   = d["raw"] / max_v * 100
            d["color"] = pct_color(d["pct"])
        rows_html = rank_rows(doctors[:10])
    else:
        rows_html = f"<pre style='font-size:11px;overflow:auto'>{raw[:500]}</pre>"

    metric_m = re.search(r'RANKING:\s*(.+?)[\|\n]', raw)
    metric   = metric_m.group(1).strip() if metric_m else "metric"

    skip_pat = re.compile(r'(={3,}|#\d+|RANKING)', re.IGNORECASE)
    a_lines  = [l.strip() for l in raw.split("\n")
                if len(l.strip()) > 35 and not skip_pat.search(l)]
    a_lines  = _tag_pcts(a_lines[:3])

    chips = [
        {"label": "Doctor details",  "prompt": f"Show performance of {doctors[0]['name']}" if doctors else "Show doctor performance"},
        {"label": "Compare by BU",   "prompt": "Compare all BUs"},
    ]

    inner = (ctx_badge(metric + " · ranking")
             + rows_html + analysis_block(a_lines) + suggest_chips(chips))
    return bot_bubble(inner)

# ── TREND ─────────────────────────────────────────────
def _render_trend(raw, query):
    MONTH_MAP = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                 "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    monthly = {}
    for abbr, num in MONTH_MAP.items():
        m = re.search(rf'{abbr}\s+([\d,]+\.?\d*)', raw)
        if m: monthly[num] = parse_num(m.group(1))

    sorted_m = sorted(monthly.keys())
    values   = [monthly[k] for k in sorted_m]
    labels   = [list(MONTH_MAP.keys())[k-1] for k in sorted_m]

    spark_html = sparkline(values, labels)

    kpi_html = ""
    if values:
        avg   = sum(values)/len(values)
        best  = max(values); bi = values.index(best); bm = labels[bi] if bi < len(labels) else ""
        worst = min(values); wi = values.index(worst); wm = labels[wi] if wi < len(labels) else ""
        kpi_html = (
            f"<div style='{S['kpi_grid']}grid-template-columns:repeat(4,1fr);'>"
            + kpi_card_simple("Best month",     f"{bm} · {fmt_big(best)}",  "#185FA5")
            + kpi_card_simple("Worst month",    f"{wm} · {fmt_big(worst)}", "#A32D2D")
            + kpi_card_simple("Monthly avg",    fmt_big(avg))
            + kpi_card_simple("Months tracked", str(len(values)))
            + "</div>"
        )

    metric_m = re.search(r'MONTHLY TREND:\s*(.+?)[\|\n]', raw)
    metric   = metric_m.group(1).strip() if metric_m else "metric"

    skip_pat = re.compile(r'(={3,}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Avg|Best|Low)', re.IGNORECASE)
    a_lines  = [l.strip() for l in raw.split("\n")
                if len(l.strip()) > 35 and not skip_pat.search(l)]
    a_lines  = _tag_pcts(a_lines[:3])

    chips = [
        {"label": "vs target",       "prompt": f"Compare {metric} actual vs target"},
        {"label": "Doctor breakdown", "prompt": "Which doctor drove the best month?"},
    ]

    inner = (ctx_badge(metric + " · monthly trend")
             + kpi_html + sec_title("Monthly breakdown") + spark_html
             + analysis_block(a_lines) + suggest_chips(chips))
    return bot_bubble(inner)

# ── YEAR SUMMARY ──────────────────────────────────────
def _render_year_summary(raw, query):
    def epct(pat):
        m = re.search(pat, raw, re.IGNORECASE)
        return parse_num(m.group(1)) if m else None

    metrics = [
        ("Revenue achievement", epct(r'revenue.*?achievement.*?([\d.]+)%'), False),
        ("Cases achievement",   epct(r'cases.*?achievement.*?([\d.]+)%'),   False),
        ("No-show %",           epct(r'no.?show.*?([\d.]+)%'),              True),
        ("Service leakage %",   epct(r'leakage.*?([\d.]+)%'),               True),
        ("Doctor PMS %",        epct(r'pms.*?([\d.]+)%'),                   False),
        ("Patient retention %", epct(r'retention.*?([\d.]+)%'),             False),
    ]

    cards = "".join(
        kpi_card_simple(lbl, f"{val:.1f}%", pct_color(val, lb))
        for lbl, val, lb in metrics if val is not None
    )
    kpi_html = f"<div style='{S['kpi_grid']}'>{cards}</div>" if cards else ""

    top_m    = re.search(r'[Tt]op\s*:?\s*Dr\.?\s*([\w\s]+?)\s*\(([\d.]+)%\)', raw)
    bot_m    = re.search(r'[Bb]ottom\s*:?\s*Dr\.?\s*([\w\s]+?)\s*\(([\d.]+)%\)', raw)
    doc_html = ""
    if top_m or bot_m:
        doc_html = sec_title("Doctor highlights")
        if top_m:
            doc_html += (
                f"<div style='{S['winner_row']}'>"
                f"<span style='color:#0F6E56;font-size:16px;'>↑</span>"
                f"<span style='font-weight:700;min-width:36px;color:#0F6E56;'>Top</span>"
                f"<span style='color:#666;flex:1;'>Dr. {top_m.group(1).strip()}</span>"
                f"<span style='font-weight:700;color:#0F6E56;'>{top_m.group(2)}%</span>"
                f"</div>"
            )
        if bot_m:
            doc_html += (
                f"<div style='{S['winner_row']}'>"
                f"<span style='color:#A32D2D;font-size:16px;'>↓</span>"
                f"<span style='font-weight:700;min-width:36px;color:#A32D2D;'>Low</span>"
                f"<span style='color:#666;flex:1;'>Dr. {bot_m.group(1).strip()}</span>"
                f"<span style='font-weight:700;color:#A32D2D;'>{bot_m.group(2)}%</span>"
                f"</div>"
            )

    skip_pat = re.compile(r'(={3,}|Target|Actual|Achievement|YEAR SUMMARY|REVENUE|CASES|AVERAGE|DOCTORS|RANKING)', re.IGNORECASE)
    a_lines  = [l.strip() for l in raw.split("\n")
                if len(l.strip()) > 35 and not skip_pat.search(l)]
    a_lines  = _tag_pcts(a_lines[:4])

    year_m = re.search(r'YEAR SUMMARY:\s*(\d{4})', raw)
    year   = year_m.group(1) if year_m else "year"

    chips = [
        {"label": "Monthly breakdown", "prompt": f"Monthly revenue trend {year}"},
        {"label": "Doctor rankings",   "prompt": f"Rank all doctors by revenue {year}"},
        {"label": "Compare BUs",       "prompt": f"Compare ASH vs SMH vs HJH in {year}"},
    ]

    inner = (ctx_badge(f"year summary · {year}")
             + kpi_html + doc_html + analysis_block(a_lines) + suggest_chips(chips))
    return bot_bubble(inner)

# ── DOCTOR ────────────────────────────────────────────
def _render_doctor(raw, query):
    def epct(pat):
        m = re.search(pat, raw, re.IGNORECASE)
        return parse_num(m.group(1)) if m else None

    metrics = [
        ("Revenue achievement", epct(r'[Aa]chievement\s*:\s*([\d.]+)%'),       False),
        ("Cases achievement",   epct(r'[Cc]ases.*?[Aa]chievement\s*:\s*([\d.]+)%'), False),
        ("Doctor PMS %",        epct(r'PMS.*?([\d.]+)%'),                       False),
        ("No-show %",           epct(r'[Nn]o.?[Ss]how.*?([\d.]+)%'),           True),
        ("Service leakage %",   epct(r'[Ll]eakage\s*%?\s*:\s*([\d.]+)%'),      True),
        ("Patient retention %", epct(r'[Rr]etention.*?([\d.]+)%'),              False),
    ]

    cards = "".join(
        kpi_card_simple(lbl, f"{val:.1f}%", pct_color(val, lb))
        for lbl, val, lb in metrics if val is not None
    )
    kpi_html = f"<div style='{S['kpi_grid']}'>{cards}</div>" if cards else ""

    rank_m   = re.search(r'OVERALL RANKING:\s*#?(\d+)\s*of\s*(\d+)', raw)
    rank_html = ""
    if rank_m:
        r, total = int(rank_m.group(1)), int(rank_m.group(2))
        rc       = pct_color((total - r) / total * 100)
        rank_html = (
            sec_title("Overall ranking")
            + f"<div style='{S['winner_row']}'>"
            f"<span style='font-size:22px;font-weight:700;color:{rc};'>#{r}</span>"
            f"<span style='color:#666;flex:1;'>out of {total} doctors</span>"
            f"</div>"
        )

    doc_m    = re.search(r'DOCTOR REPORT:\s*Dr\.?\s*([\w\s]+?)\s*\|', raw)
    doc_name = f"Dr. {doc_m.group(1).strip()}" if doc_m else "Doctor"

    skip_pat = re.compile(r'(={3,}|Target|Actual|Achievement|DOCTOR REPORT|REVENUE|CASES|QUALITY|OTHER|OVERALL|#\d+)', re.IGNORECASE)
    a_lines  = [l.strip() for l in raw.split("\n")
                if len(l.strip()) > 35 and not skip_pat.search(l)]
    a_lines  = _tag_pcts(a_lines[:4])

    chips = [
        {"label": "Monthly trend",       "prompt": f"Monthly revenue trend for {doc_name}"},
        {"label": "Compare with peers",  "prompt": "Compare all doctors by revenue"},
        {"label": "Root cause analysis", "prompt": f"Why is no-show % high for {doc_name}?"},
    ]

    inner = (ctx_badge(doc_name + " · performance")
             + kpi_html + rank_html + analysis_block(a_lines) + suggest_chips(chips))
    return bot_bubble(inner)

# ── TAG PERCENTAGES in analysis lines ────────────────
def _tag_pcts(lines):
    result = []
    for line in lines:
        def color_pct(m):
            v = float(m.group(1))
            if v >= 80:   return f"<span style='background:#E1F5EE;color:#085041;border-radius:4px;padding:1px 5px;font-size:11px;font-weight:600;'>{m.group(0)}</span>"
            if v >= 50:   return f"<span style='background:#FAEEDA;color:#633806;border-radius:4px;padding:1px 5px;font-size:11px;font-weight:600;'>{m.group(0)}</span>"
            return         f"<span style='background:#FCEBEB;color:#791F1F;border-radius:4px;padding:1px 5px;font-size:11px;font-weight:600;'>{m.group(0)}</span>"
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'(\d+\.?\d*)%', color_pct, line)
        result.append(line)
    return result

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
# TOOLS
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

def _find_col(metric):
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

def search_knowledge_base(query):
    keywords = [w for w in re.split(r'[\s%,]+', query.lower()) if len(w) > 2]
    results  = []
    for sheet_name, df in DATA["knowledge_base"].items():
        for _, row in df.iterrows():
            text = " ".join(str(v) for v in row.values).lower()
            if any(k in text for k in keywords):
                results.append(f"[{sheet_name}] " + " | ".join(f"{c}: {v}" for c, v in row.items()))
    return "No matching records." if not results else f"Found {len(results)} records:\n\n" + "\n".join(results[:30])

def get_doctor_performance(doctor_name, year="all"):
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
    return "\n".join([
        f"DOCTOR REPORT: Dr. {matched} | Period: {'All Years' if year=='all' else year}",
        "="*55,
        f"REVENUE",
        f"  Target      : {t_rev:>18,.0f}",
        f"  Actual      : {a_rev:>18,.0f}",
        f"  Achievement : {rev_ach:>17.1f}%",
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
    ])

def rank_doctors(metric="Total Revenue", year="all", bu="all", order="desc"):
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

def compare_all_doctors(year="all", bu="all"):
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

def get_monthly_trend(metric, year="all", bu="all", doctor="all"):
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

def compare_business_units(metric, year, month=None):
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

def get_year_summary(year, bu="all"):
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
    return "\n".join([
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
    ])

def get_root_causes_analysis(kpi_name, bu="all", year="all"):
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

def get_data_summary(query=""):
    df   = DATA["opd_main_df"]
    skip = {"Year","Month No","Month","Month_Year","BU","Doctor Name"}
    kpis = [c for c in df.columns if c not in skip]
    return (f"OPD dataset: {len(df)} rows | Years: {DATA['years']} | BUs: {DATA['bus']}\n"
            f"Doctors: {DATA['doctors']}\nKPIs:\n" +
            "\n".join(f"  {i:2}. {c}" for i, c in enumerate(kpis, 1)))

def list_kpis(query=""):
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
7. Do not call more than 3 tools per request."""

# ══════════════════════════════════════════════════════
# AGENT
# ══════════════════════════════════════════════════════
def call_github(messages):
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

def execute_tool(tool_call):
    name = tool_call.get("function", {}).get("name", "")
    args = tool_call.get("function", {}).get("arguments", {})
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {}
    func = TOOL_REGISTRY.get(name)
    if not func: return f"Unknown tool: '{name}'"
    try: return func(**args)
    except Exception as e: return f"Tool error: {e}"

def run_agent(user_query, chat_history):
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

# ── Header ────────────────────────────────────────────
st.markdown(f"""
<div style='position:sticky;top:0;z-index:100;background:#185FA5;color:white;
     padding:14px 24px;display:flex;align-items:center;gap:12px;
     margin-bottom:20px;border-radius:0 0 16px 16px;
     box-shadow:0 2px 12px rgba(24,95,165,0.3);'>
  <div style='font-size:28px;'>📊</div>
  <div>
    <div style='font-size:18px;font-weight:600;'>Andalusia OPD Analytics</div>
    <div style='font-size:12px;opacity:.8;'>AI-powered KPI Assistant</div>
  </div>
  <div style='margin-left:auto;display:flex;gap:6px;'>
    {''.join(f"<span style='background:rgba(255,255,255,0.2);padding:3px 10px;border-radius:20px;font-size:12px;'>{b}</span>" for b in ['ASH','SMH','HJH'])}
  </div>
</div>
<div style='{S["wrap"]}'>
""", unsafe_allow_html=True)

# ── Welcome ───────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div style='text-align:center;padding:40px 20px 20px;color:#555;'>
      <div style='color:#185FA5;font-size:22px;font-weight:600;margin-bottom:8px;'>Welcome to OPD Analytics 👋</div>
      <div style='font-size:15px;color:#888;'>Ask me anything about doctors, revenue, KPIs, or performance trends.</div>
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

# ── Chat history ──────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='{S['user_row']}'><div style='{S['user_bub']}'>{msg['content']}</div></div>",
            unsafe_allow_html=True)
    else:
        st.markdown(msg["content"], unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────
user_input = st.chat_input("Ask about doctors, revenue, KPIs...")
if "pending_query" in st.session_state:
    user_input = st.session_state.pop("pending_query")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.rerun()

# ── Generate ──────────────────────────────────────────
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]
    with st.spinner("Analyzing data..."):
        raw_answer = run_agent(last_query, st.session_state.chat_history)
    formatted = format_response(raw_answer, last_query)
    st.session_state.messages.append({"role": "assistant", "content": formatted})
    st.session_state.chat_history.append(("user", last_query))
    st.session_state.chat_history.append(("assistant", raw_answer[:400]))
    if len(st.session_state.chat_history) > 8:
        st.session_state.chat_history = st.session_state.chat_history[-8:]
    st.rerun()
