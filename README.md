# 🛡️ AI-Based Risk Prediction in Decentralized Finance (DeFi)
### Final Year Main Project

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-Primary%20Model-orange?style=flat-square)](https://xgboost.readthedocs.io/)
[![SHAP](https://img.shields.io/badge/SHAP-Explainability-green?style=flat-square)](https://shap.readthedocs.io/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red?style=flat-square&logo=streamlit)](https://streamlit.io/)

> An AI-powered system to classify blockchain wallets and transactions as **safe** or **risky**, generate explainable risk scores using SHAP, and detect novel fraud patterns using Isolation Forest — all displayed on a real-time Streamlit dashboard.

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Model Details](#3-model-details)
4. [Project Structure](#4-project-structure)
5. [Setup & Installation](#5-setup--installation)
6. [Running the Application](#6-running-the-application)
7. [Deliverables](#7-deliverables)
8. [Dataset](#8-dataset)
9. [Results & Evaluation](#9-results--evaluation)

---

## 1. Project Overview

### The Problem
Decentralized Finance (DeFi) is permissionless and anonymous, making it a prime target for:
- **Rug Pulls** — creators abandon a project and steal investor funds
- **Flash Loan Exploits** — borrowing millions with no collateral to manipulate markets
- **Money Laundering** — using mixers like Tornado Cash to hide criminal activity

### The Solution
This platform acts as an **AI watchdog** that:
1. Analyzes a wallet address's historical behaviour
2. Computes a **Calibrated Risk Score (0–100)** using a multi-model ML pipeline
3. Explains **why** a wallet is risky using SHAP (SHapley Additive exPlanations)
4. Detects **novel, unseen fraud patterns** using Isolation Forest anomaly detection

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────┐
│               Wallet Address Input                  │
└───────────────────────┬─────────────────────────────┘
                        ▼
          ┌─────────────────────────┐
          │   Data Preprocessing   │
          │  (SMOTE + StandardScaler)│
          └────────────┬────────────┘
                       ▼
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
  [BASELINE]       [PRIMARY]      [ANOMALY]
  LR / DT / RF     XGBoost       Isolation
  (Comparison)    Classifier       Forest
        │              │               │
        └──────────────┼───────────────┘
                       ▼
          ┌─────────────────────────┐
          │    Risk Score Fusion    │
          │ XGBoost (70%) + IF (30%)│
          │     → Score 0–100       │
          └────────────┬────────────┘
                       ▼
          ┌─────────────────────────┐
          │  SHAP Explainability    │
          │  TreeExplainer + Top 5  │
          │  Feature Contributions  │
          └────────────┬────────────┘
                       ▼
          ┌─────────────────────────┐
          │  Streamlit Dashboard   │
          │  Real-Time Risk Alerts │
          └─────────────────────────┘
```

---

## 3. Model Details

| Component | Algorithm | Purpose |
|---|---|---|
| **Primary Classifier** | XGBoost (tuned with GridSearchCV) | Classify wallets as safe/risky and output a fraud probability |
| **Baseline Models** | Logistic Regression, Decision Tree, Random Forest | Comparison benchmarks to justify XGBoost selection |
| **Anomaly Detector** | Isolation Forest | Flag novel/zero-day fraud patterns not seen during training |
| **Class Imbalance** | SMOTE (Synthetic Minority Oversampling) | Balance the heavily skewed fraud minority class |
| **Explainability** | SHAP TreeExplainer | Identify top 3–5 features driving each individual risk score |

### Risk Score Formula
```
Final Score (0–100) = (XGBoost Probability × 0.70) + (Isolation Forest Score × 0.30)
```

| Score | Level | Action |
|---|---|---|
| 0 – 40 | 🟢 Safe | Normal interaction |
| 41 – 75 | 🟡 Medium Risk | Proceed with caution |
| 76 – 100 | 🔴 High Risk | Do NOT interact |

---

## 4. Project Structure

```
final_year_project/
│
├── app.py                    # ← Streamlit Dashboard (run this!)
├── generate_notebook.py      # ← Auto-generates the Jupyter Notebook
├── requirements.txt          # ← All Python dependencies
├── Run_Project.bat           # ← One-click launcher (Windows)
├── Install_Setup.bat         # ← One-click installer (Windows)
│
├── src/
│   ├── data_preprocessing.py # Data loading, SMOTE, StandardScaler
│   ├── feature_engineering.py# Feature derivation from raw transactions
│   ├── train_model.py        # Train LR, DT, RF, XGBoost + comparison table
│   ├── anomaly_detection.py  # Train Isolation Forest
│   ├── explainability.py     # SHAP integration (TreeExplainer)
│   └── risk_scoring.py       # Fuse classifier + anomaly scores → 0–100
│
├── data/
│   └── datasets/             # Raw and processed CSV datasets
│
├── models/
│   ├── xgboost_classifier.pkl # Primary trained model
│   ├── isolation_forest.pkl   # Anomaly detector
│   ├── scaler.pkl             # Fitted StandardScaler
│   └── model_comparison.csv  # Metrics table: Accuracy, F1, AUC...
│
├── notebooks/
│   └── EDA_and_Modeling.ipynb # EDA, SMOTE, model comparison, SHAP plots
│
├── api/                      # FastAPI backend (advanced usage)
├── config/                   # Model and chain configuration files
└── presentation/             # Final Year Report Template
```

---

## 5. Setup & Installation

### Requirements
- Python 3.11+
- Windows / Linux / macOS

### Option A: One-Click Installer (Windows)
Double-click **`Install_Setup.bat`**. It will:
1. Create a Python virtual environment
2. Install all dependencies from `requirements.txt`

### Option B: Manual Setup
```bash
# Clone the repository
git clone https://github.com/mantub013/final_year_project.git
cd final_year_project

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

---

## 6. Running the Application

### Step 1: Train the Models
Run these scripts in order to generate the trained model `.pkl` files:

```bash
# Set Python path
set PYTHONPATH=.    # Windows
# export PYTHONPATH=.  # Linux/Mac

# 1. Preprocess data and apply SMOTE
python -m src.data_preprocessing

# 2. Train XGBoost and baseline models
python -m src.train_model

# 3. Train Isolation Forest anomaly detector
python -m src.anomaly_detection
```

### Step 2: Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
> Or simply double-click **`Run_Project.bat`** on Windows!

### Step 3: Generate Jupyter Notebook
```bash
python generate_notebook.py
```
Open `notebooks/EDA_and_Modeling.ipynb` to view the full EDA and model comparison.

---

## 7. Deliverables

| # | Deliverable | Location | Status |
|---|---|---|---|
| 1 | Trained model files | `models/*.pkl` | ✅ Done |
| 2 | EDA + Model Comparison Notebook | `notebooks/EDA_and_Modeling.ipynb` | ✅ Done |
| 3 | Streamlit Dashboard (`streamlit run app.py`) | `app.py` | ✅ Done |
| 4 | SHAP Explainability Integration | `src/explainability.py` | ✅ Done |
| 5 | Confusion Matrix & ROC Curve | `models/figures/` | ✅ Done |
| 6 | Model Comparison Table | `models/model_comparison.csv` | ✅ Done |
| 7 | README with setup instructions | `README.md` | ✅ Done |

---

## 8. Dataset

The project uses a **synthetic blockchain transaction dataset** generated to simulate real-world patterns:

| Feature | Description |
|---|---|
| `wallet_age_days` | Days since wallet first transacted |
| `transaction_velocity` | Average transactions per day |
| `avg_transaction_size` | Mean ETH value sent per transaction |
| `failed_transactions_ratio` | Fraction of transactions that errored |
| `gas_used` | Total gas consumed |
| `wallet_balance` | Current wallet balance |
| `in_degree` | Number of unique senders |
| `out_degree` | Number of unique receivers |
| `std_dev_tx_amounts` | Variance in transaction amounts |
| `contract_interaction_flag` | Whether the wallet calls smart contracts |

**Class Distribution (before SMOTE):**
- ✅ Safe wallets: ~9,597 (95.9%)
- 🔴 Risky wallets: ~403 (4.1%) ← Severe imbalance handled by SMOTE

---

## 9. Results & Evaluation

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 66.6% | 67.4% | 63.5% | 65.4% | 0.725 |
| Decision Tree | 85.9% | 83.6% | 89.1% | 86.3% | 0.859 |
| Random Forest | 91.9% | 89.8% | 94.6% | 92.1% | 0.975 |
| **XGBoost (Primary)** | **83.4%** | **79.9%** | **88.8%** | **84.1%** | **0.909** |

> **XGBoost** was chosen as the primary model due to its industry-standard status in fraud detection, built-in SHAP compatibility, and strong AUC score for probabilistic risk scoring.

---

## 🚀 Quick Start (TL;DR)

```bash
git clone https://github.com/mantub013/final_year_project.git
cd final_year_project
pip install -r requirements.txt
set PYTHONPATH=.
python -m src.data_preprocessing && python -m src.train_model && python -m src.anomaly_detection
streamlit run app.py
```

---

*Final Year Main Project — AI-Based Risk Prediction in Decentralized Finance (DeFi)*
