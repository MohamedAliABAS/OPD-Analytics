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
# CUSTOM CSS — Chat UI
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
  /* Hide default Streamlit elements */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; }

  /* App container */
  .chat-wrapper {
    max-width: 820px;
    margin: 0 auto;
    padding: 0 16px 100px 16px;
    font-family: 'Segoe UI', sans-serif;
  }

  /* Header */
  .chat-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #185FA5;
    color: white;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 2px 12px rgba(24,95,165,0.3);
  }
  .chat-header h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: white;
  }
  .chat-header p {
    margin: 0;
    font-size: 12px;
    opacity: 0.8;
  }
  .bu-badge {
    background: rgba(255,255,255,0.2);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    margin-left: 4px;
  }

  /* User message */
  .msg-user {
    display: flex;
    justify-content: flex-end;
    margin: 10px 0;
  }
  .msg-user .bubble {
    background: #185FA5;
    color: white;
    padding: 10px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 70%;
    font-size: 15px;
    line-height: 1.5;
  }

  /* Assistant message */
  .msg-bot {
    display: flex;
    gap: 10px;
    margin: 10px 0;
    align-items: flex-start;
  }
  .bot-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #E6F1FB;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
  }
  .msg-bot .bubble {
    background: #F5F7FA;
    border: 1px solid #E8ECF0;
    padding: 14px 18px;
    border-radius: 4px 18px 18px 18px;
    max-width: 85%;
    font-size: 15px;
    line-height: 1.7;
    color: #1a1a2e;
  }

  /* KPI cards inside bot message */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin: 12px 0;
  }
  .kpi-card {
    background: white;
    border: 1px solid #E8ECF0;
    border-radius: 10px;
    padding: 10px 14px;
  }
  .kpi-label {
    font-size: 12px;
    color: #888;
    margin-bottom: 2px;
  }
  .kpi-value {
    font-size: 16px;
    font-weight: 600;
    color: #185FA5;
  }
  .kpi-value.green  { color: #0F6E56; }
  .kpi-value.red    { color: #A32D2D; }
  .kpi-value.orange { color: #BA7517; }

  /* Thinking indicator */
  .thinking {
    display: flex;
    gap: 10px;
    margin: 10px 0;
    align-items: center;
  }
  .thinking .bubble {
    background: #F5F7FA;
    border: 1px solid #E8ECF0;
    padding: 10px 16px;
    border-radius: 4px 18px 18px 18px;
    font-size: 14px;
    color: #888;
  }

  /* Suggested questions */
  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 16px 0 8px 42px;
  }

  /* Welcome */
  .welcome-box {
    text-align: center;
    padding: 40px 20px 20px;
    color: #555;
  }
  .welcome-box h2 {
    color: #185FA5;
    font-size: 22px;
    margin-bottom: 8px;
  }
  .welcome-box p {
    font-size: 15px;
    color: #888;
    margin-bottom: 24px;
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
# HELPERS + TOOLS  (same as before)
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
        f"  Achievement : {rev_ach:>17.1f}%  {'✅' if rev_ach>=100 else '⚠️' if rev_ach>=80 else '❌'}",
        f"  Gap         : {a_rev-t_rev:>18,.0f}",
        f"CASES",
        f"  Target      : {t_cas:>18,.0f}",
        f"  Actual      : {a_cas:>18,.0f}",
        f"  Achievement : {cas_ach:>17.1f}%  {'✅' if cas_ach>=100 else '⚠️' if cas_ach>=80 else '❌'}",
        f"  Charge/Case : {cpc:>18,.1f}",
        f"QUALITY KPIs",
        f"  PMS %          : {pms:>6.1f}%  {'✅' if pms>=80 else '⚠️' if pms>=60 else '❌'}",
        f"  No-Show %      : {ns:>6.1f}%  {'✅' if ns<10 else '⚠️' if ns<20 else '❌'}",
        f"  Leakage %      : {lk:>6.1f}%  {'✅' if lk<5 else '⚠️' if lk<8 else '❌'}",
        f"  Cross Referral : {xcr:>6.1f}%  {'✅' if xcr>=15 else '⚠️' if xcr>=10 else '❌'}",
        f"  Retention %    : {ret:>6.1f}%  {'✅' if ret>=70 else '⚠️' if ret>=50 else '❌'}",
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
        out.append(f"  {r['BU']:<5}  {_fmt(r[col], col)}{pct}")
    if total and len(res) > 1:
        out.append(f"  {'TOTAL':<5}  {total:,.0f}")
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
        f"  Achievement : {rev_ach:>17.1f}%  {'✅' if rev_ach>=100 else '⚠️' if rev_ach>=80 else '❌'}",
        f"  Gap         : {a_rev-t_rev:>18,.0f}",
        f"CASES",
        f"  Target      : {t_cas:>18,.0f}",
        f"  Actual      : {a_cas:>18,.0f}",
        f"  Achievement : {cas_ach:>17.1f}%  {'✅' if cas_ach>=100 else '⚠️' if cas_ach>=80 else '❌'}",
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
        out.append(f"  Dr. {r['Doctor Name']:<12}  {r['Ach']:>5.1f}%")
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
7. Do not call more than 3 tools per request."""

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
            key = (tc.get("function",{}).get("name",""),
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

# Welcome screen
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
        "🏥 Compare all BUs in 2024",
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

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg-user">
          <div class="bubble">{msg["content"]}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-bot">
          <div class="bot-avatar">🤖</div>
          <div class="bubble">{msg["content"]}</div>
        </div>""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input bar
user_input = st.chat_input("Ask about doctors, revenue, KPIs...")

# Handle suggestion click
if "pending_query" in st.session_state:
    user_input = st.session_state.pop("pending_query")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.rerun()

# Generate response if last message is from user
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
