"""
DeFi Risk Intelligence Platform — FastAPI Application Entry Point
Run with:  uvicorn api.app:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
import os
import time
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.auth import create_access_token, verify_password, MOCK_USER
from api.schemas import TokenResponse
from api.rate_limit import limiter
from api.routes import wallet, transaction, health, alerts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── App definition ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="🛡️ DeFi Risk Intelligence API",
    description="""
## AI-Powered Multi-Chain Wallet & Transaction Risk Platform

This API exposes the DeFi Risk Intelligence Platform, combining:
- **Tabular ML Ensemble** (Random Forest + XGBoost)
- **GNN Network Exposure** (GraphSAGE)
- **Autoencoder Anomaly Detection**

### Authentication
All endpoints (except `/api/health` and `/api/token`) require a **Bearer JWT token**.

1. Call `POST /api/token` with `username=defi_analyst` and `password=secure_password_123`
2. Copy the `access_token` and pass it as `Authorization: Bearer <token>`

### Supported Chains
`ethereum` · `bsc` · `polygon` · `arbitrum`
""",
    version="2.0.0",
    contact={"name": "DeFi Risk Team", "url": "https://github.com/your-org/defi-risk"},
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "Authentication",            "description": "JWT token management"},
        {"name": "System Health",             "description": "Platform status and diagnostics"},
        {"name": "Wallet Risk Analysis",      "description": "Single and batch wallet risk scoring"},
        {"name": "Transaction Risk Analysis", "description": "Transaction-level risk evaluation"},
        {"name": "Live Alerts",               "description": "Streaming threat alert feed"},
    ],
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request timing middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = str(round((time.time() - t0) * 1000, 2))
    return response

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router,      prefix="/api",              tags=["System Health"])
app.include_router(wallet.router,      prefix="/api/wallet",       tags=["Wallet Risk Analysis"])
app.include_router(wallet.router,      prefix="/api/v1/wallet",    tags=["Wallet Risk Analysis"])
app.include_router(transaction.router, prefix="/api/transaction",  tags=["Transaction Risk Analysis"])
app.include_router(alerts.router,      prefix="/api/alerts",       tags=["Live Alerts"])

# ── Direct Endpoints as required by SRS ────────────────────────────────────────
@app.get("/predict", tags=["Wallet Risk Analysis"], summary="Predict wallet risk with SHAP explanations")
async def predict_endpoint(
    address: str = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
    chain: str = "ethereum"
):
    """Direct alias for wallet risk prediction with SHAP values & explainability."""
    from api.routes.wallet import _evaluate_wallet, _format_transfers, chains_config
    payload = _evaluate_wallet(address, chain, use_cache=False)
    payload["recent_transfers"] = _format_transfers(address, chain, chains_config)
    return payload

@app.get("/live-feed", tags=["Live Alerts"], summary="Live streaming blockchain transaction feed")
async def live_feed_endpoint(chain: str = "ethereum"):
    """Returns streaming recent transactions and active threat alerts."""
    from api.routes.alerts import threat_store
    from src.ingestion.live_poller import LiveBlockchainPoller
    poller = LiveBlockchainPoller(chain=chain)
    txs = poller.fetch_recent_transactions("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", limit=10)
    alerts = threat_store.get_active_alerts(limit=10)
    return {
        "chain": chain,
        "live_transactions": txs,
        "active_alerts": alerts,
        "timestamp": time.time()
    }

# ── Auth endpoint ──────────────────────────────────────────────────────────────
@app.post(
    "/api/token",
    response_model=TokenResponse,
    tags=["Authentication"],
    summary="Login and get JWT access token",
    description=(
        "Use OAuth2 password flow to authenticate. "
        "Default credentials: `defi_analyst` / `secure_password_123`"
    ),
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if (form_data.username != MOCK_USER["username"] or
            not verify_password(form_data.password, MOCK_USER["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": form_data.username})
    return TokenResponse(access_token=token)


# ── Static Dashboard & Explorer Files ────────────────────────────────────────
@app.get("/app.js", include_in_schema=False)
def serve_app_js():
    js_path = os.path.join(BASE_DIR, "app.js")
    if not os.path.exists(js_path):
        raise HTTPException(status_code=404, detail="app.js not found")
    return FileResponse(js_path, media_type="application/javascript", headers={
        "Cache-Control": "no-cache"
    })


def _serve_index():
    html_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(html_path, media_type="text/html")


# All of these paths serve the same Wallet Explorer landing page
@app.get("/dashboard",  include_in_schema=False)
@app.get("/explorer",   include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def serve_dashboard():
    return _serve_index()


@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon():
    ico_path = os.path.join(BASE_DIR, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    # Return 204 so browsers don't keep retrying with a 404 in the console
    from fastapi.responses import Response
    return Response(status_code=204)

# ── Root — redirect to Wallet Explorer landing page ───────────────────────────
@app.get("/", include_in_schema=False)
def root():
    """Browser root always redirects to the Wallet Address Explorer."""
    return RedirectResponse(url="/dashboard", status_code=302)
