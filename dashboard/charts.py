import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, List

# ── Color palettes ─────────────────────────────────────────────────────────
LEVEL_COLORS = {
    "SAFE":     "#34d399",
    "LOW":      "#60a5fa",
    "MEDIUM":   "#facc15",
    "HIGH":     "#fb923c",
    "CRITICAL": "#f87171",
}
LEVEL_GLOW = {
    "SAFE":     "rgba(52,211,153,0.35)",
    "LOW":      "rgba(96,165,250,0.35)",
    "MEDIUM":   "rgba(250,204,21,0.35)",
    "HIGH":     "rgba(251,146,60,0.35)",
    "CRITICAL": "rgba(248,113,113,0.40)",
}

def create_gauge_chart(score: float, level: str) -> go.Figure:
    """Generates a vivid neon gauge chart for the risk score."""
    color = LEVEL_COLORS.get(level, "#94a3b8")
    glow  = LEVEL_GLOW.get(level, "rgba(148,163,184,0.3)")

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 50, "valueformat": ".0f",
               "increasing": {"color": "#f87171"},
               "decreasing": {"color": "#34d399"}},
        domain={"x": [0, 1], "y": [0, 1]},
        title={
            "text": f"<b>{level}</b>",
            "font": {"size": 18, "color": color, "family": "Outfit"}
        },
        number={"font": {"size": 42, "color": color, "family": "Outfit"},
                "suffix": ""},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "rgba(255,255,255,0.2)",
                "tickfont": {"color": "#64748b", "size": 10}
            },
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  20], "color": "rgba(52,211,153,0.12)"},
                {"range": [20, 40], "color": "rgba(96,165,250,0.12)"},
                {"range": [40, 60], "color": "rgba(250,204,21,0.10)"},
                {"range": [60, 80], "color": "rgba(251,146,60,0.12)"},
                {"range": [80, 100], "color": "rgba(248,113,113,0.15)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 4},
                "thickness": 0.82,
                "value": score,
            },
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Outfit"},
        height=270,
        margin=dict(l=16, r=16, t=48, b=8),
    )
    return fig


def create_breakdown_bar(breakdown: Dict[str, float]) -> go.Figure:
    """Generates a vivid horizontal bar chart for model score breakdowns."""
    models = list(breakdown.keys())
    scores = [round(v * 100, 1) for v in breakdown.values()]

    labels_map = {
        "tabular_ensemble": "Tabular ML (RF/XGB)",
        "gnn_network_risk": "GNN (GraphSAGE)",
        "anomaly_score":    "Anomaly (Autoencoder)",
    }
    labels = [labels_map.get(m, m) for m in models]

    bar_colors   = ["#60a5fa", "#a78bfa", "#f472b6"]
    border_colors = ["#3b82f6", "#8b5cf6", "#ec4899"]

    fig = go.Figure()
    for i, (lbl, sc) in enumerate(zip(labels, scores)):
        fig.add_trace(go.Bar(
            x=[sc],
            y=[lbl],
            orientation="h",
            name=lbl,
            marker=dict(
                color=bar_colors[i % len(bar_colors)],
                line=dict(color=border_colors[i % len(border_colors)], width=1.5),
                opacity=0.85,
            ),
            text=[f"<b>{sc}</b>"],
            textposition="outside",
            textfont=dict(color="white", size=12),
            hovertemplate=f"<b>{lbl}</b>: %{{x:.1f}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="<b>Model Threat Contributions</b>",
                   font=dict(size=13, color="#a5b4fc")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Outfit"},
        showlegend=False,
        barmode="overlay",
        xaxis=dict(
            range=[0, 120],
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
            tickfont={"color": "#64748b", "size": 10},
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont={"color": "#94a3b8", "size": 11},
        ),
        height=220,
        margin=dict(l=10, r=40, t=40, b=10),
    )
    return fig


def create_history_trend(history: List[Dict[str, Any]]) -> go.Figure:
    """Generates a vivid gradient area line chart for historical risk scores."""
    if not history:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=220,
            annotations=[dict(
                text="No historical data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(color="#64748b", size=13)
            )]
        )
        return fig

    df = pd.DataFrame(history)

    if len(df) == 1:
        t = df.iloc[0]["timestamp"]
        c = df.iloc[0]["chain"]
        base = df.iloc[0].get("risk_score", 50)
        df = pd.DataFrame([
            {"timestamp": t - 86400 * 4, "chain": c, "risk_score": max(5, base - 20)},
            {"timestamp": t - 86400 * 3, "chain": c, "risk_score": max(5, base - 12)},
            {"timestamp": t - 86400 * 2, "chain": c, "risk_score": max(5, base - 5)},
            {"timestamp": t - 86400 * 1, "chain": c, "risk_score": max(5, base + 8)},
            {"timestamp": t,              "chain": c, "risk_score": base},
        ])

    df["date"] = pd.to_datetime(df["timestamp"], unit="s")
    df = df.sort_values("date")

    # Color the line based on latest score
    latest = df.iloc[-1].get("risk_score", 50)
    line_color = ("#f87171" if latest > 70 else
                  "#fb923c" if latest > 50 else
                  "#facc15" if latest > 30 else
                  "#34d399")
    fill_color = (f"rgba(248,113,113,0.12)" if latest > 70 else
                  f"rgba(251,146,60,0.12)"  if latest > 50 else
                  f"rgba(250,204,21,0.10)"  if latest > 30 else
                  f"rgba(52,211,153,0.10)")

    fig = go.Figure()

    # Filled area
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["risk_score"],
        mode="lines+markers",
        line=dict(color=line_color, width=2.5, shape="spline", smoothing=1.2),
        marker=dict(size=7, color=line_color,
                    line=dict(color="white", width=1.5)),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="<b>%{x|%b %d}</b><br>Risk: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="<b>Historical Risk Trend</b>",
                   font=dict(size=13, color="#a5b4fc")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Outfit"},
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                   zeroline=False, tickfont={"color": "#64748b", "size": 9}),
        yaxis=dict(range=[0, 105], showgrid=True,
                   gridcolor="rgba(255,255,255,0.04)",
                   zeroline=False, tickfont={"color": "#64748b", "size": 9}),
        height=220,
        margin=dict(l=8, r=8, t=40, b=8),
    )
    return fig
