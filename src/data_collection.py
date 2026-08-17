"""
src/data_collection.py
======================
Multi-chain blockchain data collector for the AI-DeFi Risk Prediction platform.

Purpose
-------
Fetches raw on-chain transaction and wallet data from multiple blockchain
explorer APIs (Etherscan, BscScan, PolygonScan, Arbiscan) and saves it to
the offline feature store (data/raw/ and data/datasets/).

Collected data feeds:
  - Tabular ML training    → data/datasets/tabular_dataset.csv
  - GNN training graph     → data/datasets/wallet_graph.json
  - Autoencoder baseline   → data/datasets/normal_wallets.csv

Datasets collected here supplement the public datasets:
  - Elliptic Bitcoin Transaction Dataset (for GNN pre-training)
  - Ethereum Fraud Detection Dataset     (for tabular ML training)
Both are downloaded from Kaggle and placed in data/datasets/ manually.

Usage
-----
    python src/data_collection.py --chain ethereum --limit 1000
    python src/data_collection.py --chain bsc      --limit 500  --label normal
"""

import os
import json
import time
import hashlib
import random
import argparse
import csv
from typing import Dict, Any, List, Optional

from src.utils import get_logger, load_yaml, ensure_dirs
from src.blockchain_api import BlockchainAPIAdapter
from src.preprocessing import calculate_base_features
from src.graph_builder import build_transaction_graph, calculate_network_metrics

logger = get_logger()

# ── Output paths ───────────────────────────────────────────────────────────────
RAW_DIR      = "data/raw"
DATASETS_DIR = "data/datasets"
TABULAR_CSV  = os.path.join(DATASETS_DIR, "tabular_dataset.csv")
NORMAL_CSV   = os.path.join(DATASETS_DIR, "normal_wallets.csv")
GRAPH_JSON   = os.path.join(DATASETS_DIR, "wallet_graph.json")

# ── Known fraud / safe seed addresses (used for deterministic demo collection) ─
KNOWN_FRAUD_ADDRESSES = [
    "0x0000000000000000000000000000000000000bad",
    "0xbadc0de1f111e111222333444555666777888999",
    "0xdeadbeefdeadbeefdeadbeefdeadbeefdead0000",
    "0xscam00000000000000000000000000000000bad1",
    "0xrugpull000000000000000000000000000000001",
]

KNOWN_SAFE_ADDRESSES = [
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43",
    "0x4675C7e5BaAFBFFbca748158bEcBA61ef3b0a263",
    "0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5",
    "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",
]

# ── CSV column order ───────────────────────────────────────────────────────────
TABULAR_COLUMNS = [
    "address", "chain",
    "wallet_balance", "transaction_amount", "transaction_frequency",
    "failed_transactions", "average_gas_fee", "wallet_age",
    "unique_counterparties", "smart_contract_calls",
    "rug_pull_token_interaction", "flash_loan_usage",
    "token_transfers", "nft_transfers", "burst_activity_score",
    "graph_centrality", "cluster_risk_score",
    "distance_to_blacklisted_wallet", "reconstruction_error",
    "label"   # 1 = fraud, 0 = normal
]


# ══════════════════════════════════════════════════════════════════════════════
# Core collection functions
# ══════════════════════════════════════════════════════════════════════════════

def collect_wallet_features(
    address: str,
    chain: str,
    chain_config: Dict[str, Any],
    label: int = -1
) -> Optional[Dict[str, Any]]:
    """
    Fetches all data for one wallet and computes its full feature vector.

    Parameters
    ----------
    address     : Wallet address (EVM hex or TRON base58)
    chain       : Chain name (ethereum | bsc | polygon | arbitrum | tron)
    chain_config: Chain config dict from config/chains.yaml
    label       : 1 = known fraud, 0 = known normal, -1 = unknown

    Returns
    -------
    Feature dict ready for CSV export, or None on error.
    """
    try:
        adapter = BlockchainAPIAdapter(chain, chain_config)

        balance    = adapter.get_wallet_balance(address)
        txs        = adapter.get_transactions(address, limit=50)
        token_txs  = adapter.get_token_transfers(address, limit=30)

        features = calculate_base_features(address, txs, token_txs, balance)

        G = build_transaction_graph(address, txs)
        centrality, cluster_risk, dist_blacklist = calculate_network_metrics(address, G)

        features["graph_centrality"]              = centrality
        features["cluster_risk_score"]            = cluster_risk
        features["distance_to_blacklisted_wallet"]= dist_blacklist
        features["reconstruction_error"]          = 0.0   # filled during model inference

        row = {"address": address, "chain": chain, "label": label}
        row.update(features)
        return row

    except Exception as e:
        logger.error(f"[DataCollection] Failed for {address} on {chain}: {e}")
        return None


def collect_batch(
    addresses: List[str],
    chain: str,
    chain_config: Dict[str, Any],
    label: int,
    output_csv: str,
    delay: float = 0.2
) -> int:
    """
    Collects features for a list of addresses and appends to a CSV file.

    Returns the number of successfully collected rows.
    """
    ensure_dirs([RAW_DIR, DATASETS_DIR])
    file_exists = os.path.exists(output_csv)
    collected   = 0

    with open(output_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TABULAR_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
            logger.info(f"[DataCollection] Created {output_csv} with headers.")

        for addr in addresses:
            row = collect_wallet_features(addr, chain, chain_config, label)
            if row:
                writer.writerow(row)
                f.flush()
                collected += 1
                logger.info(f"[DataCollection] ✓ {addr[:14]}… [{chain}] label={label}")
            time.sleep(delay)   # rate-limit API calls

    return collected


def generate_synthetic_addresses(
    n: int,
    risk_tier: str = "normal",
    seed: int = 42
) -> List[str]:
    """
    Generates deterministic synthetic EVM addresses for demo/testing.

    risk_tier:  'normal' | 'high' | 'mixed'
    """
    rng = random.Random(seed)
    addrs = []
    for _ in range(n):
        if risk_tier == "high":
            suffix = rng.choice(["bad", "dead", "scam", "rug", "hack"])
            body   = rng.getrandbits(120)
            addr   = f"0x{body:030x}{suffix}"[:42]
        else:
            addr = f"0x{rng.getrandbits(160):040x}"
        addrs.append(addr)
    return addrs


def build_wallet_graph_json(
    addresses: List[str],
    chain: str,
    chain_config: Dict[str, Any],
    output_path: str = GRAPH_JSON
) -> None:
    """
    Builds a JSON graph file (nodes + edges) from collected transaction data.
    This feeds the GNN training pipeline (src/train_gnn.py).

    Format
    ------
    {
      "nodes": [{"id": "0x...", "label": 1}],
      "edges": [{"source": "0x...", "target": "0x...", "value": 1.5}]
    }
    """
    ensure_dirs([DATASETS_DIR])
    nodes, edges = [], []
    seen_nodes = set()

    for address in addresses:
        adapter = BlockchainAPIAdapter(chain, chain_config)
        txs     = adapter.get_transactions(address, limit=30)
        label   = 1 if any(p in address.lower() for p in ["bad","dead","scam","rug"]) else 0

        if address not in seen_nodes:
            nodes.append({"id": address, "label": label})
            seen_nodes.add(address)

        for tx in txs[:20]:
            frm = tx.get("from", "")
            to  = tx.get("to",   "")
            val = float(tx.get("value", 0)) / 1e18
            if frm and to:
                edges.append({"source": frm, "target": to, "value": round(val, 4)})
                for a in [frm, to]:
                    if a not in seen_nodes:
                        lbl = 1 if any(p in a.lower() for p in ["bad","dead","scam"]) else 0
                        nodes.append({"id": a, "label": lbl})
                        seen_nodes.add(a)

    graph = {"nodes": nodes, "edges": edges,
             "meta": {"chain": chain, "collected_at": int(time.time()),
                      "total_nodes": len(nodes), "total_edges": len(edges)}}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    logger.info(f"[DataCollection] Graph saved → {output_path} "
                f"({len(nodes)} nodes, {len(edges)} edges)")


# ══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Collect multi-chain blockchain data for ML training."
    )
    parser.add_argument("--chain",  default="ethereum",
                        choices=["ethereum","bsc","polygon","arbitrum","tron"],
                        help="Blockchain network to collect from")
    parser.add_argument("--limit",  type=int, default=100,
                        help="Number of addresses to collect")
    parser.add_argument("--label",  default="mixed",
                        choices=["fraud","normal","mixed"],
                        help="Label type for collected wallets")
    parser.add_argument("--graph",  action="store_true",
                        help="Also build wallet graph JSON for GNN training")
    parser.add_argument("--delay",  type=float, default=0.3,
                        help="Delay (seconds) between API calls to avoid rate limiting")
    args = parser.parse_args()

    chains_config = load_yaml("config/chains.yaml")
    chain_cfg     = chains_config.get(args.chain, {})

    logger.info(f"[DataCollection] Starting — chain={args.chain}, limit={args.limit}, label={args.label}")

    # ── Build address list ──────────────────────────────────────────────────────
    if args.label == "fraud":
        fraud_addrs  = KNOWN_FRAUD_ADDRESSES
        synth_fraud  = generate_synthetic_addresses(max(0, args.limit - len(fraud_addrs)), "high", seed=1)
        addresses    = (fraud_addrs + synth_fraud)[:args.limit]
        label        = 1
        output_csv   = TABULAR_CSV

    elif args.label == "normal":
        normal_addrs = KNOWN_SAFE_ADDRESSES
        synth_normal = generate_synthetic_addresses(max(0, args.limit - len(normal_addrs)), "normal", seed=2)
        addresses    = (normal_addrs + synth_normal)[:args.limit]
        label        = 0
        output_csv   = NORMAL_CSV

    else:  # mixed
        n_fraud  = args.limit // 3
        n_normal = args.limit - n_fraud
        fraud_a  = (KNOWN_FRAUD_ADDRESSES + generate_synthetic_addresses(n_fraud,  "high",   seed=3))[:n_fraud]
        normal_a = (KNOWN_SAFE_ADDRESSES  + generate_synthetic_addresses(n_normal, "normal", seed=4))[:n_normal]

        # Collect fraud
        f = collect_batch(fraud_a,  args.chain, chain_cfg, label=1, output_csv=TABULAR_CSV, delay=args.delay)
        # Collect normal
        n = collect_batch(normal_a, args.chain, chain_cfg, label=0, output_csv=TABULAR_CSV, delay=args.delay)
        logger.info(f"[DataCollection] Mixed collection done — {f} fraud + {n} normal rows.")

        if args.graph:
            build_wallet_graph_json(fraud_a + normal_a, args.chain, chain_cfg)
        return

    collected = collect_batch(addresses, args.chain, chain_cfg, label=label,
                              output_csv=output_csv, delay=args.delay)
    logger.info(f"[DataCollection] Done — {collected}/{args.limit} rows saved to {output_csv}")

    if args.graph:
        build_wallet_graph_json(addresses, args.chain, chain_cfg)


if __name__ == "__main__":
    main()
