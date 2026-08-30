import networkx as nx
import random
import hashlib
from typing import Dict, Any, List, Tuple

# Deterministic list of bad actors (mixers, phishers, rugpull contracts)
BLACKLISTED_WALLETS = [
    "0x0000000000000000000000000000000000000bad",  # Mock Blacklisted Mixer
    "0xbadc0de1f111e111222333444555666777888999",  # Mock Rugpull Creator
    "0xdeadbeefdeadbeefdeadbeefdeadbeefdead0000"   # Mock Phishing Address
]

def is_blacklisted(address: str) -> bool:
    return address.lower() in [a.lower() for a in BLACKLISTED_WALLETS] or address.lower().endswith("bad")

def build_transaction_graph(address: str, txs: List[Dict[str, Any]]) -> nx.DiGraph:
    """
    Constructs a directed transaction network graph centered around the wallet.
    Includes edges for transactions and injects connections to blacklisted nodes
    to model threat propagation.
    """
    G = nx.DiGraph()
    G.add_node(address, type="target", label=address[:8] + "...", risk_level="target")

    # Seed for reproducibility
    seed = int(hashlib.md5(address.lower().encode('utf-8')).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    # Add transaction edges
    for tx in txs[:30]:
        f = tx.get("from")
        t = tx.get("to")
        if f and t:
            if not G.has_node(f):
                is_bl = is_blacklisted(f)
                G.add_node(f, type="wallet", label=f[:8] + "...", risk_level="blacklisted" if is_bl else "normal")
            if not G.has_node(t):
                is_bl = is_blacklisted(t)
                G.add_node(t, type="wallet", label=t[:8] + "...", risk_level="blacklisted" if is_bl else "normal")
            
            # Weighted by value
            val = float(tx.get("value", 0)) / 1e18
            G.add_edge(f, t, value=round(val, 4), hash=tx.get("hash"))

    return G

def calculate_network_metrics(address: str, G: nx.DiGraph) -> Tuple[float, float, int]:
    """
    Calculates network metrics for the target address:
    - graph_centrality (Degree Centrality)
    - distance_to_blacklisted_wallet (number of hops; 99 if unreachable)
    - cluster_risk_score (aggregate of neighboring nodes' risk levels)
    """
    if len(G) <= 1:
        return 0.0, 0.0, 99

    # 1. Centrality
    deg_centrality = nx.degree_centrality(G)
    target_centrality = float(deg_centrality.get(address, 0.0))

    # Clustering Coefficient
    clustering_coeff = 0.0
    try:
        clustering_dict = nx.clustering(undirected_G)
        clustering_coeff = float(clustering_dict.get(address, 0.0))
    except Exception:
        clustering_coeff = 0.0

    # 2. Distance to blacklisted node
    shortest_path = 99
    undirected_G = G.to_undirected()
    
    # Check all blacklisted nodes in graph
    for node in undirected_G.nodes():
        if is_blacklisted(node) or "bad" in node:
            try:
                path_len = nx.shortest_path_length(undirected_G, source=address, target=node)
                if path_len < shortest_path:
                    shortest_path = path_len
            except nx.NetworkXNoPath:
                continue

    # 3. Cluster risk score
    # Count how many nodes in the 2-hop neighborhood are blacklisted or medium risk
    subgraph_nodes = nx.single_source_shortest_path_length(undirected_G, address, cutoff=2)
    risk_points = 0
    total_neighbors = len(subgraph_nodes) - 1  # exclude target node itself
    
    for neighbor in subgraph_nodes:
        if neighbor == address:
            continue
        if is_blacklisted(neighbor) or "bad" in neighbor:
            risk_points += 1.0
        elif "bridge" in neighbor or undirected_G.nodes[neighbor].get("risk_level") == "medium_risk":
            risk_points += 0.5

    cluster_risk = float(risk_points / total_neighbors) if total_neighbors > 0 else 0.0

    return round(target_centrality, 4), round(cluster_risk, 4), int(shortest_path)
