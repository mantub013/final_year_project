def compute_final_risk_score(xgb_prob: float, isolation_score: float) -> dict:
    """
    Final risk score = weighted blend of classifier probability and anomaly score,
    scaled to 0-100.
    
    IsolationForest score ranges from -1 (anomaly) to 1 (normal).
    We map it so that 1 is high anomaly risk, 0 is low anomaly risk.
    """
    # Map IF score: 1 -> 0 (safe), -1 -> 1 (anomaly)
    anomaly_risk = (1.0 - isolation_score) / 2.0
    
    # XGBoost Probability is 0.0 to 1.0
    
    # Weighted Blend (70% XGBoost, 30% Anomaly)
    final_score_raw = (0.7 * xgb_prob) + (0.3 * anomaly_risk)
    final_score = int(final_score_raw * 100)
    
    if final_score > 75:
        level = "High Risk"
    elif final_score > 40:
        level = "Medium Risk"
    else:
        level = "Safe"
        
    return {
        "score": final_score,
        "level": level,
        "xgb_prob": xgb_prob,
        "anomaly_risk": anomaly_risk
    }
