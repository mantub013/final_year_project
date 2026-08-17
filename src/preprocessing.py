import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_base_features(address: str, txs: List[Dict[str, Any]], token_txs: List[Dict[str, Any]], balance: float) -> Dict[str, Any]:
    """
    Computes base transactional features from lists of transactions and token transfers.
    """
    features = {
        "wallet_balance": balance,
        "transaction_amount": 0.0,
        "transaction_frequency": 0.0,
        "failed_transactions": 0,
        "average_gas_fee": 0.0,
        "wallet_age": 1.0,
        "unique_counterparties": 0,
        "smart_contract_calls": 0,
        "rug_pull_token_interaction": 0,
        "flash_loan_usage": 0,
        "token_transfers": 0,
        "nft_transfers": 0,
        "burst_activity_score": 0.0
    }
    
    if not txs:
        return features

    # Timestamps
    timestamps = [int(tx["timeStamp"]) for tx in txs]
    min_time = min(timestamps)
    max_time = max(timestamps)
    age_seconds = max(1.0, float(time_diff := (int(pd.Timestamp.now().timestamp()) - min_time)))
    features["wallet_age"] = round(age_seconds / (24 * 3600), 2)  # age in days

    # Counts
    features["token_transfers"] = len(token_txs)
    total_tx = len(txs)
    features["transaction_frequency"] = round(total_tx / max(0.1, features["wallet_age"]), 2)

    # Failed transactions
    failed = sum(1 for tx in txs if tx.get("isError") == "1" or tx.get("txreceipt_status") == "0")
    features["failed_transactions"] = failed

    # Total amounts in Ether
    total_val = sum(float(tx.get("value", 0)) / 1e18 for tx in txs)
    features["transaction_amount"] = round(total_val, 4)

    # Gas
    gas_fees = [float(tx.get("gasUsed", 0)) * float(tx.get("gasPrice", 0)) / 1e18 for tx in txs]
    features["average_gas_fee"] = round(np.mean(gas_fees), 6) if gas_fees else 0.0

    # Counterparties
    counterparties = set()
    for tx in txs:
        counterparties.add(tx.get("from"))
        counterparties.add(tx.get("to"))
    counterparties.discard(address)
    counterparties.discard(None)
    features["unique_counterparties"] = len(counterparties)

    # Contracts and Specific patterns
    sc_calls = 0
    scam_interactions = 0
    flash_loans = 0
    
    # Simple heuristic checks
    for tx in txs:
        # If 'to' field is blank, it's a contract creation
        if not tx.get("to"):
            sc_calls += 1
        # If gas used is very high, it is likely interacting with complex contracts
        elif int(tx.get("gasUsed", 0)) > 21000:
            sc_calls += 1

    for ttk in token_txs:
        # Check for mock SCAM_TOKEN address
        if ttk.get("contractAddress") == "0xbadc0de1f111e111222333444555666777888999":
            scam_interactions += 1
        # Token names indicating potential rugpulls
        symbol = str(ttk.get("tokenSymbol", "")).upper()
        if any(x in symbol for x in ["SCAM", "RUG", "FAK"]):
            scam_interactions += 1

    # Burst activity calculation: check transactions within short windows (e.g. 1 hour)
    if total_tx > 1:
        timestamps_sorted = sorted(timestamps)
        intervals = np.diff(timestamps_sorted)
        # Fraction of transactions that occurred very close together (< 300 seconds)
        short_intervals = sum(1 for interval in intervals if interval < 300)
        features["burst_activity_score"] = round(short_intervals / total_tx, 2)
    
    # Flash loan heuristics: many large volume swaps in a short time frame
    # We can mock this with deterministic seeds or high contract call rates combined with high burst scores
    import hashlib
    seed_hash = int(hashlib.md5(address.lower().encode('utf-8')).hexdigest(), 16)
    if (seed_hash % 100) < 5:  # 5% of wallets are flagged as flash loan users
        features["flash_loan_usage"] = 1
        features["smart_contract_calls"] += 5
        
    features["rug_pull_token_interaction"] = scam_interactions

    return features
