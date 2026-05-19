import re, json, requests, pandas as pd
import time, os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
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
# CUSTOM CSS — Flat Warm Tone UI
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
  /* Hide default Streamlit elements */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; background-color: #FAF8F5; }

  /* App container */
  .chat-wrapper {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 16px 100px 16px;
    font-family: 'Segoe UI', sans-serif;
  }

  /* Header - Custom Warm Flat Theme */
  .chat-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #8C6A5C;
    color: white;
    padding: 16px 32px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 12px rgba(140, 106, 92, 0.15);
  }
  .chat-header h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: white;
  }
  .chat-header p {
    margin: 0;
    font-size: 13px;
    opacity: 0.85;
  }
  .bu-badge {
    background: rgba(255, 255, 255, 0.15);
    color: #FFF5F0;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    margin-left: 6px;
    border: 1px solid rgba(255,255,255,0.1);
  }

  /* Chat Layout Elements */
  .msg-user {
    display: flex;
    justify-content: flex-end;
    margin: 14px 0;
  }
  .msg-user .bubble {
    background: #8C6A5C;
    color: white;
    padding: 12px 18px;
    border-radius: 18px 18px 4px 18px;
    max-width: 70%;
    font-size: 15px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  }

  .msg-bot {
    display: flex;
    gap: 12px;
    margin: 14px 0;
    align-items: flex-start;
  }
  .bot-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #EFEBE9;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }
  .msg-bot .bubble {
    background: #FFFFFF;
    border: 1px solid #E6E1DC;
    padding: 16px 20px;
    border-radius: 4px 18px 18px 18px;
    width: 100%;
    font-size: 15px;
    line-height: 1.7;
    color: #3E3835;
    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  }

  /* Welcome Screen */
  .welcome-box {
    text-align: center;
    padding: 60px 20px 30px;
    color: #555;
  }
  .welcome-box h2 {
    color: #6D4C41;
    font-size: 26px;
    margin-bottom: 10px;
  }
  .welcome-box p {
    font-size: 16px;
    color: #8A827E;
    margin-bottom: 30px;
  }
  
  /* Container for the dynamic charts */
  .dashboard-container {
    background: #FFFFFF;
    border: 1px solid #E6E1DC;
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.02);
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
# LOAD DATA (cached)
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
# HELPERS + TOOLS
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

# Modifying tools to optionally return structured data for charts
def search_knowledge_base(query: str):
    keywords = [w for w in re.split(r'[\s%,]+', query.lower()) if len(w) > 2]
    results  = []
    for sheet_name, df in DATA["knowledge_base"].items():
        for _, row in df.iterrows():
            text = " ".join(str(v) for v in row.values).lower()
            if any(k in text for k in keywords):
                results.append(f"[{sheet_name}] " + " | ".join(f"{c}: {v}" for c, v in row.items()))
    return "text", ("No matching records." if not results else f"Found {len(results)} records:\n\n" + "\n".join(results[:30]))

def get_doctor_performance(doctor_name: str, year: str = "all"):
    df = _filter_df(year=year, doctor=doctor_name)
    if df.empty: return "text", f"No data for '{doctor_name}'."
    matched = df["Doctor Name"].iloc[0]
    t_rev = df["Target Revenue"].sum(); a_rev = df["Total Revenue"].sum()
    t_cas = df["Target No. cases"].sum(); a_cas = df["No. Cases"].sum()
    rev_ach = a_rev / t_rev * 100 if t_rev else 0
    cas_ach = a_cas / t_cas * 100 if t_cas else 0
    pms = df["Doctor PMS %"].mean(); ns = df["No-Show %"].mean()
    
    out = f"**DOCTOR REPORT: Dr. {matched}**\n\n" \
          f"• **Actual Revenue:** {a_rev:,.0f} (Ach: {rev_ach:.1f}%)\n" \
          f"• **Actual Cases:** {a_cas:,.0f} (Ach: {cas_ach:.1f}%)\n" \
          f"• **Avg PMS:** {pms:.1f}% | **No-Show:** {ns:.1f}%"
    return "doctor_perf", {"text": out, "df": df, "doctor_name": matched}

def rank_doctors(metric: str = "Total Revenue", year: str = "all", bu: str = "all", order: str = "desc"):
    df  = _filter_df(year=year, bu=bu)
    if df.empty: return "text", "No data."
    col = _find_col(metric)
    agg = "mean" if "%" in col else "sum"
    grp = df.groupby("Doctor Name")[col].agg(agg).reset_index().sort_values(col, ascending=(order=="asc")).reset_index(drop=True)
    
    out = f"**Doctors Ranking by {col} ({year}):**\n"
    for i, r in grp.head(10).iterrows():
        out += f"{i+1}. Dr. {r['Doctor Name']}: {_fmt(r[col], col)}\n"
    return "bar_chart", {"text": out, "df": grp.head(10), "x": "Doctor Name", "y": col, "title": f"Top Doctors by {col}"}

def get_monthly_trend(metric: str, year: str = "all", bu: str = "all", doctor: str = "all"):
    col = _find_col(metric); agg = "mean" if "%" in col else "sum"
    df = _filter_df(year=year, bu=bu, doctor=doctor)
    if df.empty: return "text", "No data available."
    
    monthly = df.groupby(["Year", "Month No"])[col].agg(agg).reset_index().sort_values(["Year", "Month No"])
    monthly["Month"] = monthly["Year"].astype(str) + "-" + monthly["Month No"].astype(str).str.zfill(2)
    
    out = f"**Monthly Trend for {col}:**\n"
    for _, r in monthly.tail(12).iterrows():
        out += f"• {r['Month']}: {_fmt(r[col], col)}\n"
    return "line_chart", {"text": out, "df": monthly, "x": "Month", "y": col, "title": f"Monthly Trend - {col}"}

def compare_business_units(metric: str, year: str, month: int = None):
    df = _filter_df(year=year)
    if month: df = df[df["Month No"] == int(month)]
    if df.empty: return "text", "No data."
    col = _find_col(metric); agg = "mean" if "%" in col else "sum"
    res = df.groupby("BU")[col].agg(agg).reset_index().sort_values(col, ascending=False)
    
    out = f"**BU Comparison for {col} ({year}):**\n"
    for _, r in res.iterrows():
        out += f"• **{r['BU']}:** {_fmt(r[col], col)}\n"
    return "bu_chart", {"text": out, "df": res, "x": "BU", "y": col, "title": f"BU Comparison: {col}"}

def get_year_summary(year: str, bu: str = "all"):
    df = _filter_df(year=year, bu=bu)
    if df.empty: return "text", f"No data for year {year}."
    a_rev = df["Total Revenue"].sum()
    a_cas = df["No. Cases"].sum()
    out = f"**Year Summary for {year} (BU: {bu}):**\n" \
          f"• **Total Revenue:** {a_rev:,.0f}\n" \
          f"• **Total Cases:** {a_cas:,.0f}\n" \
          f"• **Avg No-Show:** {df['No-Show %'].mean():.1f}%"
    return "text", out

def get_root_causes_analysis(kpi_name: str, bu: str = "all", year: str = "all"):
    _, res = search_knowledge_base(kpi_name)
    return "text", f"**Root Cause Investigation for {kpi_name}:**\n\n{res}"

def get_data_summary(query: str = ""): return "text", "OPD Dataset Summary Active."
def list_kpis(query: str = ""):
    skip = {"Year","Month No","Month","Month_Year","BU","Doctor Name"}
    kpis = [c for c in DATA["opd_main_df"].columns if c not in skip]
    return "text", "Available KPIs:\n" + "\n".join(f"• {c}" for c in kpis)

TOOL_REGISTRY = {
    "search_knowledge_base": search_knowledge_base, "get_doctor_performance": get_doctor_performance,
    "rank_doctors": rank_doctors, "get_monthly_trend": get_monthly_trend,
    "compare_business_units": compare_business_units, "get_year_summary": get_year_summary,
    "get_root_causes_analysis": get_root_causes_analysis, "get_data_summary": get_data_summary, "list_kpis": list_kpis
}

# ══════════════════════════════════════════════════════
# AGENT INTERACTION ENGINE
# ══════════════════════════════════════════════════════
# (The schema logic remains same, but we intercept structured results)
TOOLS_SCHEMA = [
    {"type":"function","function":{"name":"search_knowledge_base","description":"Search KPI definitions.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"get_doctor_performance","description":"Full performance report for ONE doctor.","parameters":{"type":"object","properties":{"doctor_name":{"type":"string"},"year":{"type":"string"}},"required":["doctor_name"]}}},
    {"type":"function","function":{"name":"rank_doctors","description":"Rank ALL doctors by any KPI.","parameters":{"type":"object","properties":{"metric":{"type":"string"},"year":{"type":"string"},"bu":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"get_monthly_trend","description":"Monthly breakdown of any metric.","parameters":{"type":"object","properties":{"metric":{"type":"string"},"year":{"type":"string"},"bu":{"type":"string"},"doctor":{"type":"string"}},"required":["metric","year"]}}},
    {"type":"function","function":{"name":"compare_business_units","description":"Compare ASH vs SMH vs HJH.","parameters":{"type":"object","properties":{"metric":{"type":"string"},"year":{"type":"string"}},"required":["metric","year"]}}},
    {"type":"function","function":{"name":"get_year_summary","description":"Full year summary.","parameters":{"type":"object","properties":{"year":{"type":"string"},"bu":{"type":"string"}},"required":["year"]}}},
    {"type":"function","function":{"name":"get_root_causes_analysis","description":"Root cause analysis for a KPI.","parameters":{"type":"object","properties":{"kpi_name":{"type":"string"}},"required":["kpi_name"]}}},
]

SYSTEM_PROMPT = f"""You are an expert OPD KPI Analytics Assistant for Andalusia hospital system.
Data covers years 2023, 2024, 2025 across BUs: ASH, SMH, HJH. Doctors: {str(DATA["doctors"][:10])}...
ALWAYS call a tool before answering. Be short, factual and use markdown formatting."""

def call_github(messages: list) -> dict:
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
    payload = {"model": GITHUB_MODEL, "messages": messages, "tools": TOOLS_SCHEMA, "tool_choice": "auto", "temperature": 0}
    try:
        r = requests.post(f"{GITHUB_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            msg = r.json()["choices"][0]["message"]
            return {"content": msg.get("content") or "", "tool_calls": msg.get("tool_calls") or []}
    except: pass
    return {"content": "Sorry, I encountered a connection issue.", "tool_calls": []}

def run_agent_pipeline(user_query: str, chat_history: list):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content in chat_history[-4:]: messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_query})
    
    response = call_github(messages)
    
    if response["tool_calls"]:
        tc = response["tool_calls"][0]
        name = tc["function"]["name"]
        args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
        
        if name in TOOL_REGISTRY:
            type_of_res, structure = TOOL_REGISTRY[name](**args)
            return type_of_res, structure
            
    return "text", response["content"]

# ══════════════════════════════════════════════════════
# STREAMLIT FLAT THEME UI RENDER
# ══════════════════════════════════════════════════════
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# Main Flat Header
st.markdown("""
<div class="chat-header">
  <div style="font-size:26px">📊</div>
  <div>
    <h1>Andalusia OPD Analytics</h1>
    <p>Data-Driven Hospital Insights & KPI Assistant</p>
  </div>
  <div style="margin-left:auto">
    <span class="bu-badge">ASH</span>
    <span class="bu-badge">SMH</span>
    <span class="bu-badge">HJH</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

# Welcome Screen
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-box">
      <h2>Welcome to your OPD Analytics Dashboard 👋</h2>
      <p>Ask deep analytic queries or monitor hospital metrics instantly.</p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    suggestions = [
        "📈 Rank doctors by Total Revenue",
        "🏥 Compare business units for No-Show % in 2024",
        "📅 Get monthly trend for Total Revenue in 2025",
        "📊 Show doctor performance for Dr. Aly Abbas",
    ]
    for i, s in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(s, use_container_width=True, key=f"sug_{i}"):
                st.session_state.pending_query = s.split(" ", 1)[1]
                st.rerun()

# Render Chat and Dynamic Dashboards
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="msg-user"><div class="bubble">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="msg-bot"><div class="bot-avatar">🤖</div><div class="bubble">', unsafe_allow_html=True)
        st.markdown(msg["content"])
        
        # Inject dynamic charts if available in the custom key
        if "visual_data" in msg:
            vis = msg["visual_data"]
            st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
            
            # Palette matching our Earthy/Flat design
            flat_colors = ['#8C6A5C', '#B09A8F', '#D3C5BC', '#A8897C']
            
            if vis["type"] == "bar_chart":
                fig = px.bar(vis["df"], x=vis["x"], y=vis["y"], title=vis["title"], color_discrete_sequence=flat_colors)
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#3E3835")
                st.plotly_chart(fig, use_container_width=True)
                
            elif vis["type"] == "line_chart":
                fig = px.line(vis["df"], x=vis["x"], y=vis["y"], title=vis["title"], markers=True, color_discrete_sequence=flat_colors)
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#3E3835")
                st.plotly_chart(fig, use_container_width=True)
                
            elif vis["type"] == "bu_chart":
                fig = px.pie(vis["df"], names=vis["x"], values=vis["y"], title=vis["title"], color_discrete_sequence=flat_colors, hole=0.4)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#3E3835")
                st.plotly_chart(fig, use_container_width=True)
                
            elif vis["type"] == "doctor_perf":
                # Render a direct 2-column KPI card grid block
                df_doc = vis["df"]
                k1, k2 = st.columns(2)
                k1.metric("Total Rev (Sum)", f"{df_doc['Total Revenue'].sum():,.0f}")
                k2.metric("Avg No-Show %", f"{df_doc['No-Show %'].mean():.1f}%")
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input Bar
user_input = st.chat_input("Ask about doctors, revenue, KPIs...")
if "pending_query" in st.session_state: user_input = st.session_state.pop("pending_query")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.rerun()

# Run Pipeline on User Message
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]
    
    with st.spinner("Generating Insights..."):
        res_type, res_data = run_agent_pipeline(last_query, st.session_state.chat_history)
        
    new_msg = {"role": "assistant"}
    if res_type == "text":
        new_msg["content"] = res_data
    else:
        new_msg["content"] = res_data["text"]
        new_msg["visual_data"] = {"type": res_type, "df": res_data.get("df"), "x": res_data.get("x"), "y": res_data.get("y"), "title": res_data.get("title")}
        
    st.session_state.messages.append(new_msg)
    st.session_state.chat_history.append(("user", last_query))
    st.session_state.chat_history.append(("assistant", new_msg["content"][:200]))
    st.rerun()
