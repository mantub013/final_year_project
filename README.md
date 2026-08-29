# 🛡️ AI-Based Risk Prediction in Decentralized Finance (DeFi)
### Final Year Main Project — Version 2.0 (Premium Release)

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-Tabular%20Ensemble-orange?style=flat-square)](https://xgboost.readthedocs.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-GNN%20%2B%20Autoencoder-red?style=flat-square&logo=pytorch)](https://pytorch.org/)
[![Dashboard](https://img.shields.io/badge/Dashboard-Bento%20Station%20v2-purple?style=flat-square)](#)

> An enterprise-grade AI-powered platform to classify multi-chain blockchain wallets and transactions as **safe** or **risky**, compute fused risk scores using a **Three-Tier Machine Learning Pipeline** (Tabular Ensemble + GraphSAGE GNN + MLP Autoencoder), and provide natural language explainability on an interactive **Bento Station Glassmorphic Dashboard**.

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture (v2.0)](#2-system-architecture-v20)
3. [Three-Tier Model Architecture](#3-three-tier-model-architecture)
4. [Project Structure](#4-project-structure)
5. [Setup & Installation](#5-setup--installation)
6. [Running the Application (v2.0)](#6-running-the-application-v20)
7. [Desktop Shortcut Creation](#7-desktop-shortcut-creation)
8. [Testing & Quality Assurance](#8-testing--quality-assurance)
9. [API Reference & cURL Usage](#9-api-reference--curl-usage)

---

## 1. Project Overview

### The Problem
Decentralized Finance (DeFi) is permissionless and anonymous, creating systemic vulnerability to:
- **Rug Pulls & Sybil Attacks** — fraudulent wallet networks draining pool liquidity.
- **Flash Loan Exploits** — multi-step price manipulation schemes.
- **Money Laundering** — privacy-preserving mixers and cross-chain laundering rings.

### The Solution (Version 2.0)
This platform serves as an automated **AI DeFi Risk Watchdog**:
1. Multi-Chain Data Ingestion: Evaluates wallets on **Ethereum, TRON, BSC, Polygon, and Arbitrum**.
2. Fused Risk Score (0–100): Combines Tabular ML, Graph Network Analysis, and Autoencoder Anomaly Detection.
3. Natural Language & SHAP Explainability: Pinpoints exact risk factors (e.g. 1-hop distance to blacklist mixer, burst transaction frequency).
4. Real-Time Bento Station Interface: Modern high-performance dashboard with risk gauge rings, token transfer tables, and interactive chain selectors.

---

## 2. System Architecture (v2.0)

```
                       ┌─────────────────────────────────────┐
                       │ Wallet Address / Tx Hash Ingestion  │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │      Multi-Chain Data Adapter       │
                       │  (TRON, ETH, BSC, Polygon, Arbitrum) │
                       └──────────────────┬──────────────────┘
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
       ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
       │   Tier 1: Tabular   │ │     Tier 2: GNN     │ │ Tier 3: Autoencoder │
       │ Ensemble (XGB+RF)   │ │   (GraphSAGE Net)   │ │  (Anomaly Detector) │
       └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                  │                       │                       │
                  └───────────────────────┼───────────────────────┘
                                          ▼
                       ┌─────────────────────────────────────┐
                       │     Calibrated Risk Fusion Engine   │
                       │     Score = 0.5T + 0.3G + 0.2A      │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │         FastAPI REST Backend        │
                       │        (JWT Auth + Rate-Limit)      │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │    Bento Station Web Dashboard      │
                       │     http://localhost:8000/dashboard │
                       └─────────────────────────────────────┘
```

---

## 3. Three-Tier Model Architecture

| Tier | Component | Algorithm / Framework | Purpose |
|---|---|---|---|
| **Tier 1** | Primary Tabular Ensemble | XGBoost + Random Forest | Wallet behavioural classification and fraud probability output |
| **Tier 2** | Network Graph Exposure | GraphSAGE PyTorch GNN | Sybil network analysis and multi-hop graph proximity detection |
| **Tier 3** | Anomaly Detection | MLP Autoencoder | Unsupervised reconstruction error scoring for novel/zero-day exploits |
| **Explainability** | SHAP & NL Reasoning | SHAP TreeExplainer + Natural Language Engine | Top feature attribution and human-readable risk drivers |

### Risk Score Fusion Formula
$$\text{Score} = (0.50 \times P_{\text{tabular}} + 0.30 \times P_{\text{gnn}} + 0.20 \times P_{\text{anomaly}}) \times 100$$

| Score | Level | Color | Recommended Action |
|---|---|---|---|
| 0 – 30 | 🟢 SAFE | Green | Normal interaction safe |
| 31 – 50 | 🟡 LOW | Blue/Green | Low risk signals present |
| 51 – 70 | 🟧 MEDIUM | Yellow/Orange | Elevated signals, proceed with caution |
| 71 – 85 | 🔴 HIGH | Red | High threat risk, flag transaction |
| 86 – 100 | 🚨 CRITICAL | Bright Red | Severe exploit risk, block immediately |

---

## 4. Project Structure

```
final_year_project/
│
├── Run_Project.bat           # ← Primary v2.0 Launcher (FastAPI + Bento Dashboard)
├── Create_Desktop_Shortcut.bat# ← Desktop Shortcut Generator
├── create_shortcut.ps1        # ← PowerShell Shortcut Helper
├── Install_Setup.bat         # ← One-Click Environment Installer
├── Run_Tests.bat             # ← Complete Pytest Suite Executable
│
├── api/                      # FastAPI v2.0 REST Backend
│   ├── app.py                # Server entry point (serving API + Bento UI)
│   ├── auth.py               # JWT authentication & security
│   ├── schemas.py            # Pydantic request/response models
│   └── routes/               # Modular routes (wallet, transaction, health, alerts)
│
├── index.html                # Bento Station Dashboard UI
├── app.js                    # Interactive frontend logic & chart bindings
│
├── src/                      # Core AI Machine Learning Modules
│   ├── train_tabular.py      # Tier 1 ML training pipeline
│   ├── train_gnn.py          # Tier 2 Graph Neural Network training
│   ├── train_autoencoder.py  # Tier 3 Autoencoder training
│   ├── prediction.py         # Multi-model risk score predictor
│   ├── risk_fusion.py        # Score calibration and weighting
│   ├── explainability.py     # SHAP explanations engine
│   └── nl_reasoning.py       # Natural language threat descriptor
│
├── models/                   # Saved ML weights (.pkl, .pt)
├── config/                   # System and chain YAML configurations
├── feature_store/            # Online (Redis/Dict) & Offline Feature Stores
├── tests/                    # 100% passing Pytest integration test suite
└── PROJECT_GUIDE.md          # Full operational & theoretical documentation
```

---

## 5. Setup & Installation

### Requirements
- **Python**: Version 3.11+
- **OS**: Windows 10/11, Linux, or macOS

### Automated Installation (Windows)
Double-click **`Install_Setup.bat`**. It will create the Python virtual environment and install all required libraries.

---

## 6. Running the Application (v2.0)

### Option 1: Double-Click Launcher (Recommended)
Double-click **`Run_Project.bat`**. 
This will start the FastAPI backend server on `http://127.0.0.1:8000` and launch the **Bento Station Dashboard** in your default web browser at `http://localhost:8000/dashboard`.

### Option 2: Command Line (CLI)
```bash
# Activate environment
venv\Scripts\activate

# Start FastAPI Uvicorn Server
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

---

## 7. Desktop Shortcut Creation

To easily launch the v2 project from your Desktop at any time:
1. Double-click **`Create_Desktop_Shortcut.bat`**.
2. A shortcut named **`AI-DeFi Risk Intelligence v2`** will be created directly on your Desktop.

---

## 8. Testing & Quality Assurance

To verify that all backend routes, ML models, TRON integrations, and schemas are fully functional:

Double-click **`Run_Tests.bat`** or run:
```bash
venv\Scripts\python.exe -m pytest tests/ -v
```
All **15 unit and integration tests** will execute and report passing status.

---

## 9. API Reference & cURL Usage

- **Swagger Documentation**: `http://localhost:8000/docs`
- **Health Check**: `GET http://localhost:8000/api/health`
- **Authenticate**: `POST http://localhost:8000/api/token`
- **Scan Wallet**: `GET http://localhost:8000/api/v1/wallet/{address}?chain=tron`

---

*Final Year Main Project — AI-Based Risk Prediction in Decentralized Finance (DeFi) v2.0*
