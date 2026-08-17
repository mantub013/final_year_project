"""
Wallet routes:
  GET  /api/wallet/check          — single wallet risk check
  POST /api/wallet/batch          — batch risk check (up to 50 wallets)
  GET  /api/wallet/history/{addr} — historical risk trend for a wallet
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any, List

from api.auth import get_current_user, User
from api.routes.health import increment_prediction_counter
from api.schemas import (
    WalletRiskResponse, BatchWalletRequest, BatchWalletResponse
)
from src.utils import load_yaml, is_valid_address
from src.prediction import predict_wallet_risk
from src.explainability import explain_prediction
from src.nl_reasoning import generate_natural_language_reasons
from feature_store.online_store import OnlineFeatureStore
from feature_store.offline_store import OfflineFeatureStore

router = APIRouter()

online_store  = OnlineFeatureStore()
offline_store = OfflineFeatureStore()
chains_config = load_yaml("config/chains.yaml")


# ── Helper ─────────────────────────────────────────────────────────────────────
def _evaluate_wallet(address: str, chain: str, use_cache: bool = True) -> Dict[str, Any]:
    """Core evaluation logic — shared by single + batch endpoints."""
    cache_key = f"{chain}:{address.lower()}"

    if use_cache:
        cached = online_store.get_cached_features(cache_key)
        if cached:
            cached["cached"] = True
            return cached

    result       = predict_wallet_risk(address, chain, chains_config)
    explanations = explain_prediction(result)
    reasons, recommendation = generate_natural_language_reasons(result, explanations)

    increment_prediction_counter()

    payload = {
        "address":        result["address"],
        "chain":          result["chain"],
        "risk_score":     result["risk_score"],
        "risk_level":     result["risk_level"],
        "breakdown":      result["breakdown"],
        "explanations":   explanations,
        "reasons":        reasons,
        "recommendation": recommendation,
        "features":       result.get("features", {}),
        "cached":         False,
    }

    # Write-through cache (5 min TTL)
    online_store.cache_features(cache_key, payload, ttl_seconds=300)
    # Persist to offline store
    offline_store.save_features(address, chain, result["features"])

    return payload


# ── Single wallet check ────────────────────────────────────────────────────────
@router.get(
    "/check",
    response_model=WalletRiskResponse,
    summary="Analyse a single wallet",
    description=(
        "Runs the full Tabular Ensemble + GNN + Autoencoder pipeline on one wallet. "
        "Results are cached for 5 minutes."
    ),
)
async def check_wallet(
    address: str = Query(..., description="EVM wallet address (0x… 42 chars)"),
    chain: str   = Query("ethereum", description="ethereum | bsc | polygon | arbitrum"),
    no_cache: bool = Query(False, description="Skip cache and force fresh evaluation"),
    current_user: User = Depends(get_current_user),
):
    if not is_valid_address(address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid EVM address: '{address}'. Must start with 0x and be 42 chars.",
        )

    chain = chain.lower()
    if chain not in chains_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain '{chain}'. Supported: {list(chains_config.keys())}",
        )

    try:
        payload = _evaluate_wallet(address, chain, use_cache=not no_cache)
        if chain == "tron":
            from src.blockchain_api_tron import TronDataFetcher
            fetcher = TronDataFetcher(chains_config)
            payload["recent_transfers"] = fetcher.get_recent_transfers(address, limit=10)
        else:
            from src.blockchain_api import BlockchainAPIAdapter
            adapter = BlockchainAPIAdapter(chain, chains_config.get(chain, {}))
            raw_txs = adapter.get_token_transfers(address, limit=10)
            transfers = []
            for tx in raw_txs:
                decimal = int(tx.get("tokenDecimal", 18))
                raw_v = int(tx.get("value", 0))
                transfers.append({
                    "transaction_id": tx.get("hash", ""),
                    "block_timestamp": int(tx.get("timeStamp", 0)) * 1000 if int(tx.get("timeStamp", 0)) < 1e11 else int(tx.get("timeStamp", 0)),
                    "from_address": tx.get("from", ""),
                    "to_address": tx.get("to", ""),
                    "amount_usdt": round(float(raw_v / (10 ** decimal)), 2),
                    "raw_value": str(raw_v),
                    "token_symbol": tx.get("tokenSymbol", "USDT"),
                    "contract_address": tx.get("contractAddress", ""),
                    "confirmed": True,
                })
            payload["recent_transfers"] = transfers
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk evaluation failed: {str(e)}",
        )


@router.get(
    "/{address}",
    summary="Analyse a single wallet (path parameter)",
    description="Runs prediction pipeline for wallet address passed in URL path.",
)
async def check_wallet_path(
    address: str,
    chain: str = Query("tron", description="ethereum | bsc | polygon | arbitrum | tron"),
    no_cache: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    if not is_valid_address(address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wallet address: '{address}'. Must be valid EVM (0x...) or TRON (T...) address.",
        )

    chain = chain.lower()
    if chain not in chains_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain '{chain}'. Supported: {list(chains_config.keys())}",
        )

    try:
        payload = _evaluate_wallet(address, chain, use_cache=not no_cache)
        if chain == "tron":
            from src.blockchain_api_tron import TronDataFetcher
            fetcher = TronDataFetcher(chains_config)
            payload["recent_transfers"] = fetcher.get_recent_transfers(address, limit=10)
        else:
            from src.blockchain_api import BlockchainAPIAdapter
            adapter = BlockchainAPIAdapter(chain, chains_config.get(chain, {}))
            raw_txs = adapter.get_token_transfers(address, limit=10)
            transfers = []
            for tx in raw_txs:
                decimal = int(tx.get("tokenDecimal", 18))
                raw_v = int(tx.get("value", 0))
                transfers.append({
                    "transaction_id": tx.get("hash", ""),
                    "block_timestamp": int(tx.get("timeStamp", 0)) * 1000 if int(tx.get("timeStamp", 0)) < 1e11 else int(tx.get("timeStamp", 0)),
                    "from_address": tx.get("from", ""),
                    "to_address": tx.get("to", ""),
                    "amount_usdt": round(float(raw_v / (10 ** decimal)), 2),
                    "raw_value": str(raw_v),
                    "token_symbol": tx.get("tokenSymbol", "USDT"),
                    "contract_address": tx.get("contractAddress", ""),
                    "confirmed": True,
                })
            payload["recent_transfers"] = transfers
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk evaluation failed: {str(e)}",
        )


# ── Batch wallet check ─────────────────────────────────────────────────────────
@router.post(
    "/batch",
    response_model=BatchWalletResponse,
    summary="Analyse up to 50 wallets in one request",
    description=(
        "Accepts a JSON body with a list of up to 50 EVM wallet addresses. "
        "Each wallet is evaluated independently. Invalid addresses are returned "
        "in the `errors` field without failing the whole batch."
    ),
)
async def batch_check_wallets(
    body: BatchWalletRequest,
    current_user: User = Depends(get_current_user),
):
    chain = body.chain.lower()
    if chain not in chains_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain '{chain}'. Supported: {list(chains_config.keys())}",
        )

    results = []
    errors  = []

    for addr in body.addresses:
        try:
            result = _evaluate_wallet(addr, chain, use_cache=True)
            results.append(WalletRiskResponse(**result))
        except Exception as e:
            errors.append({"address": addr, "error": str(e)})

    return BatchWalletResponse(
        chain=chain,
        total=len(results),
        results=results,
        errors=errors,
    )


# ── Historical trend ───────────────────────────────────────────────────────────
@router.get(
    "/history/{address}",
    summary="Get historical risk snapshots for a wallet",
    description="Returns past risk score snapshots stored in the offline feature store.",
)
async def wallet_history(
    address: str,
    current_user: User = Depends(get_current_user),
):
    if not is_valid_address(address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid EVM address: '{address}'",
        )

    history = offline_store.get_historical_features(address)
    return {
        "address": address,
        "snapshots": history,
        "count": len(history),
    }
