"""
Alerts route — GET /api/alerts
Returns latest high-risk alerts from the streaming pipeline.
"""
import os
import json
import time
from fastapi import APIRouter, Depends, Query
from typing import Optional

from api.auth import get_current_user, User
from api.schemas import AlertsResponse, AlertItem

router = APIRouter()

ALERTS_FILE = "data/alerts.json"


@router.get("/", response_model=AlertsResponse, summary="Get live threat alerts")
async def get_alerts(
    limit: int = Query(20, ge=1, le=100, description="Max number of alerts to return"),
    chain: Optional[str] = Query(None, description="Filter by chain (ethereum, bsc, polygon, arbitrum)"),
    min_score: float = Query(0.0, ge=0, le=100, description="Minimum risk score filter"),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the latest high-risk wallet/transaction alerts captured
    by the streaming pipeline. Supports filtering by chain and minimum score.
    """
    if not os.path.exists(ALERTS_FILE):
        return AlertsResponse(total=0, alerts=[])

    try:
        with open(ALERTS_FILE, "r") as f:
            raw = json.load(f)
    except Exception:
        return AlertsResponse(total=0, alerts=[])

    # Apply filters
    filtered = []
    for a in raw:
        if chain and a.get("chain", "").lower() != chain.lower():
            continue
        if a.get("risk_score", 0) < min_score:
            continue
        filtered.append(AlertItem(
            alert_id=str(a.get("alert_id", "")),
            timestamp=int(a.get("timestamp", 0)),
            address=str(a.get("address", "")),
            chain=str(a.get("chain", "")),
            risk_score=float(a.get("risk_score", 0)),
            risk_level=str(a.get("risk_level", "SAFE")),
            reason=str(a.get("reason", "")),
        ))

    # Sort newest first
    filtered.sort(key=lambda x: x.timestamp, reverse=True)
    sliced = filtered[:limit]

    return AlertsResponse(total=len(filtered), alerts=sliced)
