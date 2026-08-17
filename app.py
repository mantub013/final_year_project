import os
import json
import streamlit as st
import pandas as pd
import time
import random
import threading

# Import dashboard components
from src.utils import load_yaml, is_valid_address
from src.prediction import predict_wallet_risk
from src.explainability import explain_prediction
from src.nl_reasoning import generate_natural_language_reasons
from feature_store.online_store import OnlineFeatureStore
from feature_store.offline_store import OfflineFeatureStore

from dashboard.charts import create_gauge_chart, create_breakdown_bar, create_history_trend
from dashboard.graph_view import render_plotly_graph
from dashboard.alerts import render_alert_feed

# 1. Page Configuration & Premium CSS
st.set_page_config(
    page_title="AI-DeFi Risk Intelligence v2.0",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Premium Neon-Glassmorphism CSS ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
}

/* ── Animated Background ── */
.stApp {
    background: linear-gradient(135deg, #050b18 0%, #0d1b2a 40%, #0a1628 70%, #0b1120 100%);
    min-height: 100vh;
}

/* ── Sidebar Premium Style ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #111827 100%) !important;
    border-right: 1px solid rgba(99, 179, 237, 0.15);
}

[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* ── Tab styling ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(13, 27, 42, 0.8);
    border-radius: 12px;
    padding: 6px;
    border: 1px solid rgba(99, 179, 237, 0.1);
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 20px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #8b949e !important;
    background: transparent !important;
    transition: all 0.3s ease !important;
}

[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #1a56db 0%, #6c3fd5 100%) !important;
    color: white !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
}

/* ── Glass Cards ── */
.glass-card {
    background: rgba(17, 25, 40, 0.75);
    border: 1px solid rgba(99, 179, 237, 0.15);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    backdrop-filter: blur(12px);
    margin-bottom: 20px;
    transition: box-shadow 0.3s ease, border-color 0.3s ease;
}

.glass-card:hover {
    border-color: rgba(99, 179, 237, 0.3);
    box-shadow: 0 12px 40px rgba(26, 86, 219, 0.2), inset 0 1px 0 rgba(255,255,255,0.08);
}

/* ── Neon Glow Cards by Severity ── */
.card-critical {
    background: rgba(17, 25, 40, 0.85);
    border: 1px solid rgba(239, 68, 68, 0.5);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 24px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255,255,255,0.04);
}
.card-high {
    background: rgba(17, 25, 40, 0.85);
    border: 1px solid rgba(251, 146, 60, 0.5);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 24px rgba(251, 146, 60, 0.2);
}
.card-medium {
    background: rgba(17, 25, 40, 0.85);
    border: 1px solid rgba(250, 204, 21, 0.5);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 24px rgba(250, 204, 21, 0.15);
}
.card-safe {
    background: rgba(17, 25, 40, 0.85);
    border: 1px solid rgba(52, 211, 153, 0.5);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 24px rgba(52, 211, 153, 0.15);
}

/* ── Metric Pill ── */
.metric-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}
.pill-critical { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4); }
.pill-high     { background: rgba(251,146,60,0.2); color: #fb923c; border: 1px solid rgba(251,146,60,0.4); }
.pill-medium   { background: rgba(250,204,21,0.2); color: #facc15; border: 1px solid rgba(250,204,21,0.4); }
.pill-safe     { background: rgba(52,211,153,0.2); color: #34d399; border: 1px solid rgba(52,211,153,0.4); }

/* ── Metric Titles ── */
.metric-title {
    color: #64748b;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
}
.metric-value {
    font-size: 2.4rem;
    font-weight: 900;
    margin-top: 6px;
    line-height: 1;
}

/* ── Hero Header ── */
.hero-title {
    text-align: center;
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(135deg, #63b3ed 0%, #a78bfa 50%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
    line-height: 1.1;
}
.hero-sub {
    text-align: center;
    color: #64748b;
    font-size: 1.05rem;
    margin-bottom: 32px;
    font-weight: 400;
}

/* ── Alert Feed Items ── */
.alert-item {
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    font-size: 0.9rem;
    transition: transform 0.2s ease;
}
.alert-item:hover { transform: translateX(4px); }

/* ── Recommendation Box ── */
.recommendation-box {
    background: rgba(231, 76, 60, 0.12);
    border: 1px solid rgba(231, 76, 60, 0.45);
    padding: 16px 20px;
    border-radius: 10px;
    color: #fc8181;
    font-weight: 600;
    margin-top: 16px;
    line-height: 1.6;
}

/* ── Stat Cards ── */
.stat-card {
    background: linear-gradient(135deg, rgba(26,86,219,0.15) 0%, rgba(108,63,213,0.15) 100%);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    margin-bottom: 12px;
}

/* ── Buttons ── */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #1a56db 0%, #6c3fd5 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 1.4rem !important;
    color: white !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
    transition: all 0.25s ease !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(99, 102, 241, 0.55) !important;
}

/* ── Input fields ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: rgba(17, 25, 40, 0.9) !important;
    border: 1px solid rgba(99, 179, 237, 0.2) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] > div {
    background: rgba(17, 25, 40, 0.9) !important;
    border: 1px solid rgba(99, 179, 237, 0.2) !important;
    border-radius: 8px !important;
}

/* ── Section divider ── */
.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: #a5b4fc;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(99, 102, 241, 0.2);
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d1b2a; }
::-webkit-scrollbar-thumb { background: #1a56db; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# Initialize chains config
chains_config = load_yaml("config/chains.yaml")
online_store = OnlineFeatureStore()
offline_store = OfflineFeatureStore()

# Sidebar controls
st.sidebar.markdown(
    """
    <div style='text-align: center; margin-bottom: 24px; padding: 16px;'>
        <div style='font-size: 2.4rem; margin-bottom: 4px;'>🛡️</div>
        <div style='font-size: 1.3rem; font-weight: 900;
            background: linear-gradient(135deg, #63b3ed, #a78bfa);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;'>DeFi Risk v2.0</div>
        <div style='color: #64748b; font-size: 0.8rem; margin-top: 4px;
            letter-spacing: 1px; text-transform: uppercase;'>Threat Intelligence</div>
        <div style='margin-top: 12px; height: 2px;
            background: linear-gradient(90deg, transparent, #6366f1, transparent);'></div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

# Session State for Live Stream simulation
if "stream_running" not in st.session_state:
    st.session_state.stream_running = False

def bg_stream_worker():
    from src.stream_listener import run_stream_listener
    run_stream_listener(chains_config)

# Toggle Stream Simulation in Sidebar
st.sidebar.markdown("### 📡 Real-Time Pipeline")
stream_toggle = st.sidebar.toggle("Start Live Stream Sim", value=st.session_state.stream_running)

if stream_toggle and not st.session_state.stream_running:
    st.session_state.stream_running = True
    # Start the stream in a background thread
    t = threading.Thread(target=bg_stream_worker, daemon=True)
    t.start()
    st.sidebar.success("Stream simulation running!")
elif not stream_toggle and st.session_state.stream_running:
    st.session_state.stream_running = False
    # Will stop when thread terminates (needs restart or standard exit)
    st.sidebar.warning("Stream stop requested.")

# Autorefresh if stream is running to pull new alerts
if st.session_state.stream_running:
    # Trigger refresh every 5 seconds
    time.sleep(1.0)
    st.sidebar.caption("🔄 Auto-refreshing feed...")

# Sidebar credentials indicator
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔐 API Access Credentials")
st.sidebar.code("Username: defi_analyst\nPassword: secure_password_123", language="text")

# Main Page Layout — Premium Hero
st.markdown("""
<div style='text-align:center; padding: 12px 0 8px 0;'>
    <div class='hero-title'>🛡️ AI-DeFi Risk Intelligence</div>
    <div style='font-size:0.7rem; font-weight:700; letter-spacing:3px;
        color:#6366f1; text-transform:uppercase; margin-bottom:6px;'>v2.0 · MULTI-CHAIN PLATFORM</div>
    <div class='hero-sub'>Tabular Ensembles · GNN Exposure Analysis · Autoencoder Anomaly Detection</div>
    <div style='display:flex; justify-content:center; gap:24px; margin-bottom:20px; flex-wrap:wrap;'>
        <span style='background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3);
            border-radius:999px; padding:4px 16px; font-size:0.8rem; color:#a5b4fc;'>⚡ Real-Time Monitoring</span>
        <span style='background:rgba(236,72,153,0.15); border:1px solid rgba(236,72,153,0.3);
            border-radius:999px; padding:4px 16px; font-size:0.8rem; color:#f9a8d4;'>🧠 Explainable AI</span>
        <span style='background:rgba(20,184,166,0.15); border:1px solid rgba(20,184,166,0.3);
            border-radius:999px; padding:4px 16px; font-size:0.8rem; color:#5eead4;'>🔗 Multi-Chain</span>
        <span style='background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.3);
            border-radius:999px; padding:4px 16px; font-size:0.8rem; color:#fcd34d;'>🔒 GNN Graph Risk</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🛡️ Wallet Analyzer",
    "📈 Live Monitor Feed",
    "💸 Transaction Investigator",
    "🧠 Model Diagnostics"
])

# ================= TAB 1: WALLET ANALYZER =================
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        <div class="glass-card">
            <div class="section-header">🔍 Wallet Scanner</div>
        </div>
        """, unsafe_allow_html=True)
        
        search_addr = st.text_input(
            "EVM Wallet Address",
            value="0x7A5D8F3A22904838493028304920492039203920",
            help="Enter a valid EVM-compatible hex address (42 characters)",
            placeholder="0x..."
        )
        
        chain_select = st.selectbox(
            "🔗 Target Blockchain Network",
            options=list(chains_config.keys()),
            format_func=lambda x: chains_config[x].get("name", x)
        )
        
        analyze_btn = st.button("⚡ Analyze Threat Exposure", type="primary", use_container_width=True)
        
        # Sample test addresses with colorful badges
        st.markdown("""
        <div style='margin-top:16px; padding:14px; background:rgba(99,102,241,0.08);
            border:1px solid rgba(99,102,241,0.2); border-radius:10px;'>
            <div style='font-size:0.78rem; font-weight:700; color:#a5b4fc;
                text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>💡 Sample Addresses</div>
            <div style='font-size:0.78rem; color:#64748b; margin-bottom:4px;'>
                <span style='color:#34d399;'>●</span> <b style='color:#94a3b8;'>Safe:</b> 0x71c7...976f
            </div>
            <div style='font-size:0.78rem; color:#64748b; margin-bottom:4px;'>
                <span style='color:#fb923c;'>●</span> <b style='color:#94a3b8;'>High-Risk:</b> 0x7A5D...3920
            </div>
            <div style='font-size:0.78rem; color:#64748b;'>
                <span style='color:#f87171;'>●</span> <b style='color:#94a3b8;'>Critical:</b> 0x0000...0bad
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Analyze Execution
    if analyze_btn or search_addr:
        if not is_valid_address(search_addr):
            st.error("Invalid address format! Must start with '0x' followed by 40 hexadecimal characters.")
        else:
            with st.spinner("Executing risk models (Tabular + GNN + Autoencoder)..."):
                try:
                    # Ingest and predict
                    result = predict_wallet_risk(search_addr, chain_select, chains_config)
                    explanations = explain_prediction(result)
                    reasons, recommendation = generate_natural_language_reasons(result, explanations)
                    
                    # Fetch history from Offline Feature Store
                    history = offline_store.get_historical_features(search_addr)
                    
                    # Layout analysis results
                    with col2:
                        # Top Metrics row
                        mcol1, mcol2, mcol3 = st.columns(3)
                        
                        # Gauge Chart
                        with mcol1:
                            st.plotly_chart(create_gauge_chart(result["risk_score"], result["risk_level"]), use_container_width=True)
                            
                        with mcol2:
                            _lvl = result['risk_level']
                            _score = result['risk_score']
                            _c = ("#f87171" if _lvl == "CRITICAL" else
                                  "#fb923c" if _lvl == "HIGH" else
                                  "#facc15" if _lvl == "MEDIUM" else
                                  "#34d399")
                            _bg = ("rgba(239,68,68,0.12)" if _lvl == "CRITICAL" else
                                   "rgba(251,146,60,0.12)" if _lvl == "HIGH" else
                                   "rgba(250,204,21,0.10)" if _lvl == "MEDIUM" else
                                   "rgba(52,211,153,0.10)")
                            _border = ("rgba(239,68,68,0.5)" if _lvl == "CRITICAL" else
                                       "rgba(251,146,60,0.5)" if _lvl == "HIGH" else
                                       "rgba(250,204,21,0.5)" if _lvl == "MEDIUM" else
                                       "rgba(52,211,153,0.5)")
                            _glow = ("0 0 30px rgba(239,68,68,0.3)" if _lvl == "CRITICAL" else
                                     "0 0 30px rgba(251,146,60,0.25)" if _lvl == "HIGH" else
                                     "0 0 30px rgba(250,204,21,0.2)" if _lvl == "MEDIUM" else
                                     "0 0 30px rgba(52,211,153,0.2)")
                            st.markdown(
                                f"""
                                <div style="
                                    background:{_bg};
                                    border:1px solid {_border};
                                    border-radius:16px;
                                    padding:24px 16px;
                                    text-align:center;
                                    box-shadow:{_glow};
                                    height:260px;
                                    display:flex; flex-direction:column;
                                    justify-content:center; align-items:center; gap:8px;
                                ">
                                    <div style="font-size:0.7rem; font-weight:700; letter-spacing:2px;
                                        color:#64748b; text-transform:uppercase;">Risk Classification</div>
                                    <div style="font-size:2rem; font-weight:900; color:{_c};
                                        text-shadow: 0 0 20px {_c}; line-height:1.1;">{_lvl}</div>
                                    <div style="width:48px; height:2px;
                                        background:linear-gradient(90deg,transparent,{_c},transparent);
                                        margin:4px auto;"></div>
                                    <div style="font-size:0.7rem; font-weight:700; letter-spacing:2px;
                                        color:#64748b; text-transform:uppercase;">Fusion Score</div>
                                    <div style="font-size:2.4rem; font-weight:900; color:white;
                                        line-height:1;">{_score}<span style="font-size:1rem;
                                        color:#64748b;">/100</span></div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            
                        with mcol3:
                            # Breakdown Chart
                            st.plotly_chart(create_breakdown_bar(result["breakdown"]), use_container_width=True)
                            
                        # Second Section: Reasons and graph
                        gcol1, gcol2 = st.columns([1, 1])
                        
                        with gcol1:
                            st.subheader("🔍 Explainable AI reasoning")
                            for reason in reasons:
                                st.markdown(f"• {reason}")
                                
                            # Action recommendation box
                            rec_color = "#E74C3C" if result["risk_level"] in ["CRITICAL", "HIGH"] else "#F39C12" if result["risk_level"] == "MEDIUM" else "#2ECC71"
                            rec_bg = "rgba(231, 76, 60, 0.15)" if result["risk_level"] in ["CRITICAL", "HIGH"] else "rgba(243, 156, 18, 0.15)" if result["risk_level"] == "MEDIUM" else "rgba(46, 204, 113, 0.15)"
                            
                            st.markdown(
                                f"""
                                <div style="
                                    background: {rec_bg};
                                    border: 1px solid {rec_color};
                                    padding: 16px;
                                    border-radius: 8px;
                                    color: {rec_color};
                                    margin-top: 20px;
                                ">
                                    <b>RECONSTRUCTION RECOMMENDATION:</b><br/>
                                    {recommendation}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            
                            # Show historical trends if available
                            st.plotly_chart(create_history_trend(history), use_container_width=True)
                            
                        with gcol2:
                            # Render interactive Plotly network graph
                            from src.blockchain_api import BlockchainAPIAdapter
                            adapter = BlockchainAPIAdapter(chain_select, chains_config[chain_select])
                            txs = adapter.get_transactions(search_addr)
                            
                            st.plotly_chart(render_plotly_graph(search_addr, txs), use_container_width=True)
                            
                            # Features breakdown list
                            with st.expander("📊 View Engineered Features"):
                                st.dataframe(pd.Series(result["features"]), use_container_width=True)
                                
                except Exception as e:
                    st.error(f"Error during risk processing: {str(e)}")

# ================= TAB 2: LIVE MONITOR FEED =================
with tab2:
    lcol, rcol = st.columns([2, 1])
    
    with lcol:
        render_alert_feed()
        
    with rcol:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Streaming Analytics")
        st.write("The platform actively monitors incoming blocks using a Kafka listener proxy. When a high risk transaction occurs, an event is logged in the alert system.")
        
        # Display aggregate stats from alerts
        alerts_file = "data/alerts.json"
        if os.path.exists(alerts_file):
            try:
                with open(alerts_file, "r") as f:
                    alerts = json.load(f)
                st.metric("Total Alerts Flags Today", len(alerts))
                
                # Show breakdown of chains
                df_alerts = pd.DataFrame(alerts)
                if not df_alerts.empty:
                    st.write("Alerts by Chain Network:")
                    st.bar_chart(df_alerts["chain"].value_counts())
            except Exception:
                pass
        st.markdown('</div>', unsafe_allow_html=True)

# ================= TAB 3: TRANSACTION INVESTIGATOR =================
with tab3:
    st.subheader("Evaluate Transfer Risk")
    st.write("Analyze individual transfers by looking up the combined sender-receiver risk profile.")
    
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        tx_hash = st.text_input("Transaction Hash", value="0x111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000")
        tx_from = st.text_input("Sender Wallet (from)", value="0x7A5D8F3A22904838493028304920492039203920")
        tx_to = st.text_input("Receiver Address (to)", value="0x0000000000000000000000000000000000000bad")
        tx_val = st.number_input("Value (ETH / Native)", min_value=0.0, value=1.5)
        tx_chain = st.selectbox("Chain Network", options=list(chains_config.keys()), key="tx_chain_select")
        
        tx_btn = st.button("Evaluate Transaction Risk", type="primary")
        
    with tcol2:
        if tx_btn:
            if not is_valid_address(tx_from) or not is_valid_address(tx_to):
                st.error("Invalid address inputs!")
            else:
                with st.spinner("Analyzing transaction path..."):
                    # Calculate combined risk
                    sender_res = predict_wallet_risk(tx_from, tx_chain, chains_config)
                    sender_score = sender_res["risk_score"]
                    
                    from src.graph_builder import is_blacklisted
                    receiver_is_bad = is_blacklisted(tx_to)
                    receiver_score = 100 if receiver_is_bad else 15
                    
                    volume_penalty = min(20.0, tx_val * 2.0) if sender_score > 40 else 0.0
                    combined_score = round(min(100.0, (0.6 * sender_score) + (0.4 * receiver_score) + volume_penalty))
                    
                    # Colors
                    t_color = "#E74C3C" if combined_score > 60 else "#F39C12" if combined_score > 40 else "#2ECC71"
                    
                    st.markdown(
                        f"""
                        <div class="glass-card" style="text-align: center;">
                            <h3>Combined Transaction Risk</h3>
                            <div style="font-size: 3rem; font-weight: bold; color: {t_color};">
                                {combined_score} / 100
                            </div>
                            <p><b>Recommendation:</b> <span style="color: {t_color};">{'BLOCK TRANSACTION' if combined_score > 60 else 'ALLOW TRANSACTION'}</span></p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Details
                    st.markdown("#### Risk Analysis Breakdown")
                    st.markdown(f"• **Sender Wallet Risk:** {sender_score} / 100")
                    st.markdown(f"• **Receiver Address Blacklisted:** {'YES (Critical Threat)' if receiver_is_bad else 'NO'}")
                    st.markdown(f"• **Volume Penalty Added:** {volume_penalty} points")

# ================= TAB 4: MODEL DIAGNOSTICS =================
with tab4:
    st.subheader("Model Registry and System Configurations")
    
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📁 Registry Information")
        st.write("**MLflow Registry Path:** `models/registry/`")
        st.write("**Model Version:** `v2.0` (Active)")
        st.write("**Last Training Update:** August 2026")
        st.write("**Validation Standard:** Pytest + Great Expectations verified")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Model Hyperparameters")
        st.json({
            "Random Forest": {"n_estimators": 100, "max_depth": None, "criterion": "gini"},
            "XGBoost": {"learning_rate": 0.1, "max_depth": 6, "eval_metric": "logloss"},
            "SimpleGNN": {"layers": 2, "in_feats": 5, "hidden": 16, "out": 8, "lr": 0.01},
            "Autoencoder": {"layers": 4, "in_feats": 12, "latent_dim": 4, "optimizer": "Adam"}
        })
        st.markdown('</div>', unsafe_allow_html=True)
        
    with dcol2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Fusion Weights")
        cfg = load_yaml("config/model_config.yaml")
        st.write("These coefficients weight the models into the final score:")
        st.json(cfg["fusion"]["weights"])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🛡️ System Resources")
        st.write("**Environment:** Python 3.11 (Windows)")
        st.write("**Device Acceleration:** CPU (PyTorch default)")
        st.write("**Redis cache:** Connected" if online_store.use_redis else "**Redis cache:** Disconnected (using file-based cache fallback)")
        st.markdown('</div>', unsafe_allow_html=True)

