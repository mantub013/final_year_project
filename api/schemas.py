"""
API Schemas — Pydantic request/response models for all endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any


# ── Auth ─────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # seconds


# ── Wallet ────────────────────────────────────────────────────────────────────
class WalletRiskResponse(BaseModel):
    address: str
    chain: str
    risk_score: float = Field(..., ge=0, le=100, description="Fused risk score 0–100")
    risk_level: str = Field(..., description="SAFE | LOW | MEDIUM | HIGH | CRITICAL")
    breakdown: Dict[str, float]
    explanations: Any = Field(default_factory=dict, description="SHAP feature explanations")
    reasons: List[str]
    recommendation: str
    cached: bool = False


class BatchWalletRequest(BaseModel):
    addresses: List[str] = Field(..., min_length=1, max_length=50,
                                  description="Up to 50 wallet addresses")
    chain: str = Field("ethereum", description="Chain: ethereum | bsc | polygon | arbitrum | tron")

    @field_validator("addresses", mode="before")
    @classmethod
    def validate_addresses_list(cls, addresses: List[str]) -> List[str]:
        validated = []
        for v in addresses:
            if not isinstance(v, str):
                raise ValueError(f"Invalid wallet address type: {type(v)}")
            # EVM check (0x...) or TRON check (T...)
            if (v.startswith("0x") and len(v) == 42) or (v.startswith("T") and len(v) == 34):
                validated.append(v)
            else:
                raise ValueError(f"Invalid address format: {v}")
        return validated


class BatchWalletResponse(BaseModel):
    chain: str
    total: int
    results: List[WalletRiskResponse]
    errors: List[Dict[str, str]] = []


# ── Transaction ───────────────────────────────────────────────────────────────
class TransactionRiskResponse(BaseModel):
    tx_hash: str
    chain: str
    sender_address: str
    receiver_address: str
    value: float
    combined_risk_score: float
    risk_level: str
    breakdown: Dict[str, float]
    recommendation: str


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertItem(BaseModel):
    alert_id: str
    timestamp: int
    address: str
    chain: str
    risk_score: float
    risk_level: str
    reason: str


class AlertsResponse(BaseModel):
    total: int
    alerts: List[AlertItem]


# ── Health ────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    timestamp: int
    version: str
    predictions_served: int
    active_models: List[str]
    chains_supported: List[str]
    uptime_seconds: Optional[float] = None
