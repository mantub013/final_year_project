import os
import pickle
import torch
import numpy as np
import networkx as nx
from typing import Dict, Any, Tuple

from src.utils import get_logger, load_yaml, ensure_dirs
from src.models_def import SimpleGNN, Autoencoder
from src.feature_engineering import generate_all_features
from src.graph_builder import build_transaction_graph, BLACKLISTED_WALLETS, is_blacklisted
from src.risk_fusion import fuse_risk_scores

logger = get_logger()

# Global variables for models and configs
_CONFIG = None
_SCALER = None
_TAB_MODEL = None
_GNN_MODEL = None
_AUTOENCODER = None

def get_config():
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_yaml("config/model_config.yaml")
    return _CONFIG

def load_all_models():
    """Loads all models from files. Auto-trains them if missing."""
    global _SCALER, _TAB_MODEL, _GNN_MODEL, _AUTOENCODER
    
    scaler_path = "models/scaler.pkl"
    tab_path = "models/tabular/best_model.pkl"
    gnn_path = "models/graph/gnn_model.pt"
    anom_path = "models/anomaly/autoencoder.pt"
    
    models_missing = (
        not os.path.exists(scaler_path) or 
        not os.path.exists(tab_path) or 
        not os.path.exists(gnn_path) or 
        not os.path.exists(anom_path)
    )
    
    if models_missing:
        logger.info("Some model files are missing. Running auto-training pipeline...")
        from src.train_tabular import train_tabular_models
        from src.train_gnn import train_gnn
        from src.train_autoencoder import train_autoencoder
        
        train_tabular_models()
        train_gnn()
        train_autoencoder()
        logger.info("Auto-training pipeline completed successfully.")

    # Load Tabular model and scaler
    with open(scaler_path, "rb") as f:
        _SCALER = pickle.load(f)
    with open(tab_path, "rb") as f:
        _TAB_MODEL = pickle.load(f)
        
    # Load GNN
    _GNN_MODEL = SimpleGNN(in_features=5, hidden_dim=16, out_features=8)
    _GNN_MODEL.load_state_dict(torch.load(gnn_path))
    _GNN_MODEL.eval()
    
    # Load Autoencoder
    config = get_config()
    tab_features_len = len(config["features"]["tabular"])
    _AUTOENCODER = Autoencoder(input_dim=tab_features_len, latent_dim=4)
    _AUTOENCODER.load_state_dict(torch.load(anom_path))
    _AUTOENCODER.eval()

def predict_wallet_risk(address: str, chain: str, chains_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predicts the risk of a wallet address by combining tabular, graph, and anomaly models.
    """
    if _TAB_MODEL is None or _SCALER is None or _GNN_MODEL is None or _AUTOENCODER is None:
        load_all_models()
        
    # 1. Feature generation
    features = generate_all_features(address, chain, chains_config)
    
    # Get tabular feature list
    config = get_config()
    tab_cols = config["features"]["tabular"]
    tab_vector = np.array([[features[col] for col in tab_cols]])
    
    # Scale tabular vector
    tab_vector_scaled = _SCALER.transform(tab_vector)
    
    # 2. Tabular Prediction
    tabular_prob = float(_TAB_MODEL.predict_proba(tab_vector_scaled)[0, 1])
    
    # 3. Anomaly Prediction (Reconstruction error)
    tensor_tab = torch.tensor(tab_vector_scaled, dtype=torch.float32)
    with torch.no_grad():
        recon_err = float(_AUTOENCODER.compute_reconstruction_error(tensor_tab)[0].item())
    
    features["reconstruction_error"] = recon_err
    # Calibrate reconstruction error to 0-1 scale: standard error is ~0.01 - 0.05, above 0.1 is anomalous
    anomaly_score = min(1.0, recon_err / 0.15)
    
    # 4. GNN Prediction
    # Build local graph for GNN inference
    from src.blockchain_api import BlockchainAPIAdapter
    chain_info = chains_config.get(chain, {})
    adapter = BlockchainAPIAdapter(chain, chain_info)
    txs = adapter.get_transactions(address)
    G = build_transaction_graph(address, txs)
    
    # Create node features (5-dim) and adj matrix for the local subgraph
    nodes = list(G.nodes())
    num_nodes = len(nodes)
    target_idx = nodes.index(address)
    
    # Local Node feature matrix
    node_features = np.zeros((num_nodes, 5))
    for i, node in enumerate(nodes):
        node_balance = adapter.get_wallet_balance(node)
        node_features[i, 0] = min(1.0, node_balance / 100.0)
        node_features[i, 1] = min(1.0, len(txs) / 50.0)
        node_features[i, 2] = 1.0 if not node.startswith("0xbridge") and node != address and len(node) > 30 and is_blacklisted(node) else 0.0
        node_features[i, 3] = 0.5  # age placeholder
        # Check if node is blacklisted
        node_features[i, 4] = 1.0 if is_blacklisted(node) else 0.0
        
    # Adjacency matrix construction
    adj_matrix = nx.to_numpy_array(G, nodelist=nodes)
    adj_matrix = adj_matrix + np.eye(num_nodes)
    row_sum = adj_matrix.sum(axis=1)
    row_sum[row_sum == 0] = 1.0
    deg_inv = 1.0 / row_sum
    norm_adj = np.diag(deg_inv).dot(adj_matrix)
    
    # PyTorch tensors
    tensor_x = torch.tensor(node_features, dtype=torch.float32)
    tensor_adj = torch.tensor(norm_adj, dtype=torch.float32)
    
    with torch.no_grad():
        gnn_probs = _GNN_MODEL(tensor_x, tensor_adj)
        gnn_risk = float(gnn_probs[target_idx].item())
        
    # 5. Risk Fusion & Scoring
    final_score, risk_level = fuse_risk_scores(tabular_prob, gnn_risk, anomaly_score)
    
    # Compile response
    result = {
        "address": address,
        "chain": chain,
        "risk_score": final_score,
        "risk_level": risk_level,
        "breakdown": {
            "tabular_ensemble": round(tabular_prob, 4),
            "gnn_network_risk": round(gnn_risk, 4),
            "anomaly_score": round(anomaly_score, 4)
        },
        "features": features
    }
    
    return result
