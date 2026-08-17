import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "predictions_served" in data

def test_unauthenticated_wallet_check():
    # Calling the wallet check route without credentials should return 401 Unauthorized
    response = client.get("/api/wallet/check?address=0x7A5D8F3A22904838493028304920492039203920")
    assert response.status_code == 401

def test_full_auth_and_wallet_check():
    # 1. Login to retrieve token
    login_response = client.post(
        "/api/token",
        data={"username": "defi_analyst", "password": "secure_password_123"}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    token = token_data["access_token"]
    
    # 2. Make authenticated request to wallet checker
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(
        "/api/wallet/check?address=0x7A5D8F3A22904838493028304920492039203920&chain=ethereum",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["address"] == "0x7A5D8F3A22904838493028304920492039203920"
    assert "risk_score" in data
    assert "risk_level" in data
    assert "breakdown" in data
    assert "explanations" in data

def test_static_dashboard_endpoints():
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert "html" in res_dash.headers.get("content-type", "")

    res_js = client.get("/app.js")
    assert res_js.status_code == 200
    assert "javascript" in res_js.headers.get("content-type", "")

def test_tron_wallet_path_endpoint():
    login_response = client.post(
        "/api/token",
        data={"username": "defi_analyst", "password": "secure_password_123"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/wallet/TNPeeaaTK7v3QGiBBWnWNFUzhMHucEjm84?chain=tron", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["address"] == "TNPeeaaTK7v3QGiBBWnWNFUzhMHucEjm84"
    assert data["chain"] == "tron"
    assert "risk_score" in data
    assert "reasons" in data
