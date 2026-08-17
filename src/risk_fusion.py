from typing import Dict, Any, Tuple
from src.utils import load_yaml

def fuse_risk_scores(
    tabular_prob: float, 
    gnn_risk: float, 
    anomaly_score: float, 
    config_path: str = "config/model_config.yaml"
) -> Tuple[float, str]:
    """
    Fuses multiple risk scores using configured weights and maps the result
    to calibrated 0-100 risk score and level.
    """
    config = load_yaml(config_path)
    weights = config["fusion"]["weights"]
    
    w_tab = weights.get("tabular", 0.5)
    w_gnn = weights.get("gnn", 0.3)
    w_anom = weights.get("anomaly", 0.2)
    
    # Combined score (between 0.0 and 1.0)
    combined = (w_tab * tabular_prob) + (w_gnn * gnn_risk) + (w_anom * anomaly_score)
    
    # Scale to 0 - 100
    scaled_score = round(combined * 100)
    
    # Determine Risk Level
    levels = config["risk_levels"]
    risk_level = "SAFE"
    
    for level, range_val in levels.items():
        if range_val["min"] <= scaled_score <= range_val["max"]:
            risk_level = level.upper()
            break
            
    return scaled_score, risk_level
