import os
import json
import streamlit as st
import datetime
from typing import List, Dict, Any

# ── Level config ────────────────────────────────────────────────────────────
_LEVEL_CFG = {
    "CRITICAL": {
        "icon": "🔴", "emoji": "💀",
        "color": "#f87171",
        "bg":    "rgba(239,68,68,0.08)",
        "border":"rgba(239,68,68,0.45)",
        "pill_bg": "rgba(239,68,68,0.2)",
        "glow":  "0 0 16px rgba(239,68,68,0.2)",
    },
    "HIGH": {
        "icon": "🟠", "emoji": "⚠️",
        "color": "#fb923c",
        "bg":    "rgba(251,146,60,0.08)",
        "border":"rgba(251,146,60,0.45)",
        "pill_bg": "rgba(251,146,60,0.2)",
        "glow":  "0 0 16px rgba(251,146,60,0.18)",
    },
    "MEDIUM": {
        "icon": "🟡", "emoji": "🔶",
        "color": "#facc15",
        "bg":    "rgba(250,204,21,0.06)",
        "border":"rgba(250,204,21,0.35)",
        "pill_bg": "rgba(250,204,21,0.18)",
        "glow":  "0 0 12px rgba(250,204,21,0.15)",
    },
}
_DEFAULT_CFG = {
    "icon": "🟢", "emoji": "✅",
    "color": "#34d399",
    "bg":    "rgba(52,211,153,0.06)",
    "border":"rgba(52,211,153,0.3)",
    "pill_bg": "rgba(52,211,153,0.18)",
    "glow":  "0 0 10px rgba(52,211,153,0.12)",
}


def render_alert_feed():
    """Renders the real-time high-risk transaction alert feed."""
    alerts_file = "data/alerts.json"

    st.markdown("""
    <div style='display:flex; align-items:center; gap:10px; margin-bottom:16px;'>
        <span style='font-size:1.4rem;'>🚨</span>
        <span style='font-size:1.1rem; font-weight:700; color:#f87171;
            letter-spacing:0.5px;'>Live Threat Alert Feed</span>
        <span style='background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.35);
            border-radius:999px; padding:2px 10px; font-size:0.7rem; font-weight:700;
            color:#f87171; letter-spacing:1px;'>LIVE</span>
    </div>
    """, unsafe_allow_html=True)

    if not os.path.exists(alerts_file):
        st.markdown("""
        <div style='background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.25);
            border-radius:10px; padding:16px; color:#a5b4fc; text-align:center;'>
            📡 No alerts yet — stream is initializing...
        </div>
        """, unsafe_allow_html=True)
        return

    try:
        with open(alerts_file, "r") as f:
            alerts = json.load(f)
    except Exception:
        st.error("⚠️ Error reading alert stream database.")
        return

    if not alerts:
        st.markdown("""
        <div style='background:rgba(52,211,153,0.08); border:1px solid rgba(52,211,153,0.3);
            border-radius:10px; padding:16px; color:#34d399; text-align:center;'>
            ✅ No active threats detected in current blocks.
        </div>
        """, unsafe_allow_html=True)
        return

    for alert in alerts[:10]:
        dt    = datetime.datetime.fromtimestamp(alert.get("timestamp", 0))
        time_str = dt.strftime("%H:%M:%S")
        level = alert.get("risk_level", "SAFE")
        score = alert.get("risk_score", 0)
        cfg   = _LEVEL_CFG.get(level, _DEFAULT_CFG)

        addr  = alert.get("address", "—")
        short = addr[:10] + "..." + addr[-6:] if len(addr) > 18 else addr
        chain = str(alert.get("chain", "—")).upper()

        st.markdown(f"""
        <div style="
            background:{cfg['bg']};
            border:1px solid {cfg['border']};
            border-left:4px solid {cfg['color']};
            border-radius:10px;
            padding:14px 16px;
            margin-bottom:10px;
            box-shadow:{cfg['glow']};
            transition: transform 0.2s ease;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;
                margin-bottom:6px;">
                <span style="font-size:0.75rem; color:#64748b;">
                    {cfg['emoji']} &nbsp;<code style="background:rgba(255,255,255,0.05);
                    padding:2px 6px; border-radius:4px; font-size:0.72rem;
                    color:#94a3b8;">{time_str}</code>
                    &nbsp;·&nbsp;
                    <code style="background:rgba(255,255,255,0.05); padding:2px 6px;
                    border-radius:4px; font-size:0.72rem; color:#94a3b8;">
                    {alert.get('alert_id', '—')}</code>
                </span>
                <span style="background:{cfg['pill_bg']}; border:1px solid {cfg['border']};
                    border-radius:999px; padding:2px 10px; font-size:0.7rem; font-weight:700;
                    color:{cfg['color']}; letter-spacing:1px;">
                    {level} · {score}
                </span>
            </div>
            <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:baseline;">
                <span style="font-size:0.85rem; color:#94a3b8;">
                    <b style='color:#cbd5e1;'>Wallet:</b>
                    <code style='color:{cfg['color']}; font-size:0.82rem;
                        background:rgba(255,255,255,0.04); padding:2px 6px;
                        border-radius:4px;'>{short}</code>
                </span>
                <span style="font-size:0.85rem; color:#94a3b8;">
                    <b style='color:#cbd5e1;'>Chain:</b>
                    <span style='color:#60a5fa;'>{chain}</span>
                </span>
            </div>
            <div style="margin-top:6px; font-size:0.82rem; color:#94a3b8; line-height:1.5;">
                {alert.get('reason', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)
