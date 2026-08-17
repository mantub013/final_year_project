from typing import Dict, Any, List, Tuple


def generate_natural_language_reasons(
    prediction_result: Dict[str, Any],
    explanation_result: Dict[str, Any]
) -> Tuple[List[str], str]:
    """
    Translates model predictions, feature values, and local SHAP explanations
    into granular plain-language risk reasons and a structured recommendation.
    """
    score    = prediction_result["risk_score"]
    level    = prediction_result["risk_level"]
    features = prediction_result["features"]
    breakdown= prediction_result.get("breakdown", {})
    reasons  = []

    # ── 1. Graph / Network signals ─────────────────────────────────────────────
    dist = features.get("distance_to_blacklisted_wallet", 99)
    if dist == 1:
        reasons.append(
            "🔴 CRITICAL: Wallet has a direct (1-hop) transaction to a known blacklisted "
            "address — likely mixer, rug-pull deployer, or phishing contract."
        )
    elif dist == 2:
        reasons.append(
            "🟠 HIGH: Wallet is 2 hops from a blacklisted actor via an intermediary address, "
            "indicating potential layering / money-mule pattern."
        )
    elif dist < 5:
        reasons.append(
            f"🟡 MEDIUM: Wallet is {dist} hops from a known malicious node in the "
            "transaction graph — elevated network exposure."
        )

    cluster = features.get("cluster_risk_score", 0.0)
    if cluster > 0.6:
        reasons.append(
            f"🔴 HIGH CLUSTER RISK: {int(cluster*100)}% of neighbouring wallets in the "
            "2-hop subgraph are classified as risky or blacklisted — probable coordinated cluster."
        )
    elif cluster > 0.3:
        reasons.append(
            f"🟡 Elevated cluster risk ({int(cluster*100)}%): Several peer wallets share risk "
            "indicators — possible wash-trading or Sybil network."
        )

    centrality = features.get("graph_centrality", 0.0)
    if centrality > 0.5:
        reasons.append(
            f"⚡ High graph centrality ({centrality:.2f}): Wallet acts as a major hub in the "
            "transaction network — consistent with mixing, bridging, or orchestration roles."
        )

    # ── 2. Tabular ML signals ──────────────────────────────────────────────────
    if features.get("flash_loan_usage", 0) > 0:
        reasons.append(
            "🔴 Flash-loan contract calls detected in active session. Flash loans are the "
            "primary mechanism for price-oracle manipulation and single-block exploits."
        )

    rug = features.get("rug_pull_token_interaction", 0)
    if rug > 0:
        reasons.append(
            f"🔴 Interacted with {rug} flagged rug-pull or scam token contract(s). "
            "These tokens are associated with known exit-scam deployer wallets."
        )

    age = features.get("wallet_age", 99.0)
    if age < 1.0:
        reasons.append(
            f"🔴 Wallet is only {age:.1f} days old — burner/throwaway wallet pattern. "
            "Attackers routinely create fresh wallets per exploit to avoid tracking."
        )
    elif age < 7.0:
        reasons.append(
            f"🟠 Wallet age is {age:.1f} days — very new account. Low transaction history "
            "limits trust baseline for this wallet."
        )

    failed = features.get("failed_transactions", 0)
    if failed > 10:
        reasons.append(
            f"🔴 {failed} failed transactions detected. High failure rates suggest repeated "
            "exploit attempts, broken automated scripts, or front-running bot activity."
        )
    elif failed > 5:
        reasons.append(
            f"🟡 {failed} failed transactions — above normal baseline. May indicate "
            "smart contract probing or failed arbitrage attempts."
        )

    burst = features.get("burst_activity_score", 0.0)
    if burst > 0.7:
        reasons.append(
            f"🔴 Burst activity score {burst:.2f}: {int(burst*100)}% of transactions sent "
            "within extremely short windows — strong indicator of bot automation or coordinated attack."
        )
    elif burst > 0.4:
        reasons.append(
            f"🟡 Moderate burst activity ({int(burst*100)}%): Unusual transaction clustering "
            "detected — possible MEV bot or high-frequency arbitrage."
        )

    freq = features.get("transaction_frequency", 0.0)
    if freq > 20:
        reasons.append(
            f"⚡ Transaction frequency: {freq:.1f} txs/day — far above the typical wallet "
            "average (~3/day). Consistent with automated trading bot or drain script."
        )

    # ── 3. Anomaly detection signal ────────────────────────────────────────────
    recon = features.get("reconstruction_error", 0.0)
    if recon > 0.12:
        reasons.append(
            f"🔴 Autoencoder reconstruction error: {recon:.4f} — places this wallet in the "
            "top 1% most anomalous patterns vs. the training baseline. Novel or zero-day behaviour."
        )
    elif recon > 0.07:
        reasons.append(
            f"🟡 Anomaly score elevated (recon error {recon:.4f}): Behavioural patterns "
            "deviate from 'normal' wallet baseline — warrants monitoring."
        )

    # ── 4. GNN-specific signal ─────────────────────────────────────────────────
    gnn = breakdown.get("gnn_network_risk", 0.0)
    if gnn > 0.75:
        reasons.append(
            f"🔴 GNN network risk score {gnn:.2f}: GraphSAGE embeddings strongly associate "
            "this wallet with known high-risk clusters in the transaction graph."
        )

    # ── 5. Safe path ───────────────────────────────────────────────────────────
    if not reasons:
        reasons.append(
            "✅ No high-risk triggers detected. Transaction frequency, balance, gas usage, "
            "and peer relationships are all within normal baseline ranges."
        )
        reasons.append(
            "✅ Wallet shows no connections to blacklisted contracts, mixers, or rug-pull deployers "
            "within 5 hops of the transaction graph."
        )
        reasons.append(
            "✅ Autoencoder reconstruction error is within normal bounds — "
            "no novel or anomalous behavioural patterns flagged."
        )

    # ── 6. Recommendation ──────────────────────────────────────────────────────
    if level == "CRITICAL":
        recommendation = (
            "🚨 DO NOT INTERACT. Immediately flag this address for manual security audit. "
            "Block all smart-contract approvals, token transfers, and bridge transactions "
            "involving this wallet. Alert connected protocol security teams."
        )
    elif level == "HIGH":
        recommendation = (
            "⚠️ AVOID INTERACTION. Do not approve token spending or contract interactions "
            "with this wallet. Submit address to on-chain threat intelligence registries "
            "(Forta, Chainalysis). Monitor associated cluster for new activity."
        )
    elif level == "MEDIUM":
        recommendation = (
            "🔶 PROCEED WITH CAUTION. Limit asset exposure. Require multisig approval "
            "for any contract interaction. Set transaction value caps and enable real-time "
            "alerts for this wallet. Re-evaluate after 24 hours of monitoring."
        )
    elif level == "LOW":
        recommendation = (
            "🟡 MONITOR. Wallet shows minor elevated signals. Safe for small interactions "
            "but maintain watchlist status. Re-score after next significant transaction."
        )
    else:
        recommendation = (
            "✅ SAFE TO INTERACT. No active threat vectors detected across all model branches. "
            "Standard DeFi interaction approved. Continue periodic re-scoring every 24 hours."
        )

    return reasons, recommendation
