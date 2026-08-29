import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def get_auth_token():
    login_response = client.post(
        "/api/token",
        data={"username": "defi_analyst", "password": "secure_password_123"}
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]

def test_valid_ethereum_address():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/0x7A5D8F3A22904838493028304920492039203920?chain=ethereum", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["address"] == "0x7A5D8F3A22904838493028304920492039203920"
    assert data["chain"] == "ethereum"
    assert "risk_score" in data

def test_valid_bsc_address():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/0x8894E0a0c962CB723c1976a4421c95949bE2D4E3?chain=bsc", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["chain"] == "bsc"
    assert "risk_score" in data

def test_valid_polygon_address():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270?chain=polygon", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["chain"] == "polygon"
    assert "risk_score" in data

def test_valid_arbitrum_address():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/0x912CE59144191C1204E64559FE8253a0e49E6548?chain=arbitrum", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["chain"] == "arbitrum"
    assert "risk_score" in data

def test_valid_tron_address():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn?chain=tron", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["chain"] == "tron"
    assert data["address"] == "TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn"
    assert "risk_score" in data

def test_invalid_wallet_address_format():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/invalid_address_123?chain=ethereum", headers=headers)
    assert res.status_code == 400

def test_unsupported_chain_selection():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/wallet/0x7A5D8F3A22904838493028304920492039203920?chain=unsupported_chain", headers=headers)
    assert res.status_code == 400
