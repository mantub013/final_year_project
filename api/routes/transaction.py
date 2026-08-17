from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, Any

from api.auth import get_current_user, User
from src.utils import is_valid_address
from src.prediction import predict_wallet_risk
from src.graph_builder import is_blacklisted

router = APIRouter()

@router.get("/check")
async def check_transaction(
    tx_hash: str = Query(..., description="Transaction hash"),
    from_address: str = Query(..., description="Sender wallet address"),
    to_address: str = Query(..., description="Receiver address (wallet or contract)"),
    value: float = Query(0.0, description="Transaction value in Ether/native token"),
    chain: str = Query("ethereum"),
    current_user: User = Depends(get_current_user)
):
    """
    Checks the risk of a single transaction by evaluating the sender's behavior,
    the receiver's blacklisted status, and transaction volume.
    """
    if not is_valid_address(from_address) or not is_valid_address(to_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid EVM sender or receiver address"
        )
        
    try:
        # Load chains config
        from src.utils import load_yaml
        chains_config = load_yaml("config/chains.yaml")
        
        # 1. Fetch sender risk
        sender_result = predict_wallet_risk(from_address, chain, chains_config)
        sender_score = sender_result["risk_score"]
        
        # 2. Check receiver risk
        receiver_is_bad = is_blacklisted(to_address)
        receiver_score = 100 if receiver_is_bad else 15
        
        # 3. Combine risk scores (transaction volume penalty if sender is already medium/high risk)
        volume_penalty = min(20.0, value * 2.0) if sender_score > 40 else 0.0
        
        combined_score = round(min(100.0, (0.6 * sender_score) + (0.4 * receiver_score) + volume_penalty))
        
        level = "SAFE"
        if combined_score > 80:
            level = "CRITICAL"
        elif combined_score > 60:
            level = "HIGH"
        elif combined_score > 40:
            level = "MEDIUM"
        elif combined_score > 20:
            level = "LOW"
            
        return {
            "tx_hash": tx_hash,
            "chain": chain,
            "sender_address": from_address,
            "receiver_address": to_address,
            "value": value,
            "combined_risk_score": combined_score,
            "risk_level": level,
            "breakdown": {
                "sender_wallet_risk": sender_score,
                "receiver_address_risk": receiver_score,
                "volume_penalty": round(volume_penalty, 2)
            },
            "recommendation": "BLOCK TRANSACTION" if level in ["CRITICAL", "HIGH"] else "ALLOW TRANSACTION"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction risk calculation error: {str(e)}"
        )
