from typing import Dict, Any
from src.utils import get_logger
from src.blockchain_api import BlockchainAPIAdapter
from src.preprocessing import calculate_base_features
from src.graph_builder import build_transaction_graph, calculate_network_metrics

logger = get_logger()

def generate_all_features(address: str, chain: str, chains_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates the data collection, preprocessing, and network analysis
    to build a complete feature vector for the given wallet address.
    """
    logger.info(f"Generating features for {address} on chain {chain}...")
    
    # Initialize blockchain adapter
    chain_info = chains_config.get(chain, {})
    adapter = BlockchainAPIAdapter(chain, chain_info)
    
    # Fetch transactional data
    balance = adapter.get_wallet_balance(address)
    txs = adapter.get_transactions(address)
    token_txs = adapter.get_token_transfers(address)
    
    # Compute base tabular features
    features = calculate_base_features(address, txs, token_txs, balance)
    
    # Build wallet graph and compute network features
    G = build_transaction_graph(address, txs)
    centrality, cluster_risk, dist_to_blacklist = calculate_network_metrics(address, G)
    
    # Append network features
    features["graph_centrality"] = centrality
    features["cluster_risk_score"] = cluster_risk
    features["distance_to_blacklisted_wallet"] = dist_to_blacklist
    
    # Set default values for anomaly metrics to be updated later by models
    features["reconstruction_error"] = 0.0
    
    return features
