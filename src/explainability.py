import numpy as np
from typing import Dict, Any, List

def explain_prediction(prediction_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes explainability metrics for a wallet risk prediction, simulating 
    local feature attributions (SHAP/LIME) and network influence (GNNExplainer).
    """
    features = prediction_result["features"]
    breakdown = prediction_result["breakdown"]
    
    # 1. Tabular feature attributions (Simulated SHAP/LIME values)
    # Define reference "normal" baseline values
    baselines = {
        "wallet_age": 90.0,             # newer is riskier
        "transaction_frequency": 2.0,    # higher is riskier
        "failed_transactions": 0.1,      # higher is riskier
        "average_gas_fee": 0.001,
        "wallet_balance": 5.0,
        "unique_counterparties": 10.0,
        "smart_contract_calls": 1.0,
        "rug_pull_token_interaction": 0.0,
        "flash_loan_usage": 0.0,
        "token_transfers": 5.0,
        "nft_transfers": 1.0,
        "burst_activity_score": 0.05
    }
    
    contributions = []
    
    # Calculate simple local deviations weighted by feature importance
    importances = {
        "flash_loan_usage": 0.35,
        "rug_pull_token_interaction": 0.25,
        "failed_transactions": 0.15,
        "wallet_age": 0.10,
        "burst_activity_score": 0.10,
        "transaction_frequency": 0.05
    }
    
    for feat, imp in importances.items():
        val = features.get(feat, 0.0)
        base = baselines.get(feat, 0.0)
        
        if feat == "wallet_age":
            # Younger age increases risk
            deviation = max(0.0, (3.0 - val) / 3.0) if val < 3.0 else 0.0
        elif feat == "flash_loan_usage":
            deviation = float(val)
        elif feat == "rug_pull_token_interaction":
            deviation = min(1.0, val / 2.0)
        elif feat == "failed_transactions":
            deviation = min(1.0, val / 5.0)
        elif feat == "burst_activity_score":
            deviation = max(0.0, val - base)
        elif feat == "transaction_frequency":
            deviation = min(1.0, max(0.0, val - base) / 20.0)
        else:
            deviation = 0.0
            
        contrib = deviation * imp
        if contrib > 0.01:
            contributions.append({
                "feature": feat,
                "value": val,
                "contribution": round(contrib, 4)
            })
            
    # Sort contributions by impact
    contributions.sort(key=lambda x: x["contribution"], reverse=True)
    
    # 2. Graph/Network Explanation (Simulated GNNExplainer)
    dist_to_bad = features.get("distance_to_blacklisted_wallet", 99)
    graph_expl = {
        "critical_path_hops": dist_to_bad,
        "influential_nodes": []
    }
    
    if dist_to_bad == 1:
        graph_expl["influential_nodes"].append({
            "address": "0x0000000000000000000000000000000000000bad",
            "relationship": "Direct transaction to blacklisted mixer"
        })
    elif dist_to_bad == 2:
        graph_expl["influential_nodes"].append({
            "address": "0xbridge...bad",
            "relationship": "Connected via intermediary high-risk wallet"
        })
        graph_expl["influential_nodes"].append({
            "address": "0xbadc0de1f111e111222333444555666777888999",
            "relationship": "Target blacklisted wallet"
        })
        
    return {
        "tabular_explanations": contributions,
        "graph_explanation": graph_expl,
        "anomaly_explanation": {
            "reconstruction_error": features.get("reconstruction_error", 0.0),
            "anomaly_contribution": breakdown.get("anomaly_score", 0.0)
        }
    }
