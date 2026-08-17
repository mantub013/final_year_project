import networkx as nx
import plotly.graph_objects as go
from typing import Dict, Any, List

from src.graph_builder import build_transaction_graph, is_blacklisted

# ── Node colour palette ─────────────────────────────────────────────────────
_NODE_TARGET     = "#34d399"   # teal-green  — target wallet
_NODE_BLACKLIST  = "#f87171"   # red         — blacklisted
_NODE_BRIDGE     = "#fb923c"   # orange      — bridge / high-exposure
_NODE_PEER       = "#60a5fa"   # blue        — normal peer
_NODE_SIZES = {
    "target":    22,
    "blacklist": 18,
    "bridge":    15,
    "peer":      11,
}


def render_plotly_graph(address: str, txs: List[Dict[str, Any]]) -> go.Figure:
    """
    Builds the NetworkX transaction graph and renders it as an interactive
    Plotly node-link figure with neon colour coding.
    """
    G = build_transaction_graph(address, txs)
    pos = nx.spring_layout(G, seed=42)

    # ── Edges ──────────────────────────────────────────────────────────────
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.2, color="rgba(99,102,241,0.3)"),
        hoverinfo="none",
        mode="lines",
    )

    # ── Nodes ──────────────────────────────────────────────────────────────
    node_x, node_y = [], []
    node_color, node_size, node_text, node_hover = [], [], [], []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        label = node[:6] + "…" + node[-4:] if len(node) > 12 else node

        if node == address:
            node_color.append(_NODE_TARGET)
            node_size.append(_NODE_SIZES["target"])
            node_text.append(f"<b>YOU</b>")
            node_hover.append(f"<b>🎯 TARGET WALLET</b><br>{node}")
        elif is_blacklisted(node) or "bad" in node:
            node_color.append(_NODE_BLACKLIST)
            node_size.append(_NODE_SIZES["blacklist"])
            node_text.append("⛔")
            node_hover.append(f"<b>🚫 BLACKLISTED</b><br>{node}")
        elif "bridge" in node:
            node_color.append(_NODE_BRIDGE)
            node_size.append(_NODE_SIZES["bridge"])
            node_text.append("🌉")
            node_hover.append(f"<b>⚠️ HIGH-EXPOSURE BRIDGE</b><br>{node}")
        else:
            node_color.append(_NODE_PEER)
            node_size.append(_NODE_SIZES["peer"])
            node_text.append(label)
            node_hover.append(f"<b>👤 PEER WALLET</b><br>{node}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        hoverinfo="text",
        hovertext=node_hover,
        text=node_text,
        textposition="bottom center",
        textfont=dict(size=9, color="rgba(255,255,255,0.7)"),
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=2, color="rgba(255,255,255,0.15)"),
            opacity=0.92,
        ),
    )

    # ── Legend traces (invisible, for colour key) ───────────────────────────
    legend_traces = []
    for name, color in [
        ("Target Wallet",   _NODE_TARGET),
        ("Blacklisted",     _NODE_BLACKLIST),
        ("Bridge Node",     _NODE_BRIDGE),
        ("Peer Wallet",     _NODE_PEER),
    ]:
        legend_traces.append(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            name=name,
            marker=dict(color=color, size=10),
            showlegend=True,
        ))

    fig = go.Figure(
        data=[edge_trace, node_trace] + legend_traces,
        layout=go.Layout(
            title=dict(
                text="<b>Wallet Transaction Exposure Graph</b>",
                font=dict(size=14, color="#a5b4fc", family="Outfit"),
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                x=0, y=-0.05,
                font=dict(color="#94a3b8", size=10),
                bgcolor="rgba(0,0,0,0)",
            ),
            hovermode="closest",
            margin=dict(b=30, l=10, r=10, t=44),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            font=dict(color="white", family="Outfit"),
            height=400,
        )
    )

    return fig
