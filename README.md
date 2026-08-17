# 🛡️ AI-Based Risk Prediction in Decentralized Finance (DeFi) — v2.0
## 📖 The Complete Beginner-to-Expert Guide

This guide is written so that **anyone, even with zero prior knowledge of blockchain or machine learning**, can fully understand what this project is, how it works, what datasets it uses, how the models are trained, and how to run it.

---

## 1. Introduction: The Problem & The Solution

### 🔍 What is Decentralized Finance (DeFi)?
Traditional finance relies on middlemen like banks (e.g., Chase, HSBC) to check transactions, hold assets, and verify identities. **DeFi** replaces these banks with **Smart Contracts**—automatic code running on public blockchains (like Ethereum or TRON). Anyone with an internet connection can trade, borrow, or lend money globally without opening a bank account.

### ⚠️ The Problem: Fraud, Exploiters, and Scams
Because DeFi is permissionless, anonymous, and instant, it has become a primary target for hackers, scammers, and money launderers:
*   **Rug Pulls**: Creators launch a token, convince people to buy it, and suddenly run away with all the funds, leaving the token valueless.
*   **Flash Loan Exploits**: Hackers borrow millions of dollars without collateral in a single blockchain block, manipulate market prices using smart contract bugs, and steal funds.
*   **Mixers (Tornado Cash)**: Smart contracts used by criminals to hide transaction trails by mixing dirty coins with clean ones.

### 🛡️ The Solution: AI-DeFi Risk Intelligence
This project is an **Artificial Intelligence (AI) watchdog**. It analyzes blockchain wallet addresses (like `0x742d...` or `TPYm...`) and transactions in real-time. By looking at a wallet's past transactions, it calculates a **Calibrated Risk Score (0 to 100)** to warn users and protocols before they interact with a dangerous wallet.

---

## 2. The Core Architecture (How the AI Works)

Instead of relying on a single simple rule, this platform combines **three separate AI models** (an Ensemble) to evaluate risk from different angles:

```
                            ┌─────────────────────────┐
                            │ Wallet Address Checked  │
                            └────────────┬────────────┘
                                         ▼
                   ┌─────────────────────┼─────────────────────┐
                   ▼                     ▼                     ▼
             [ MODEL 1 ]           [ MODEL 2 ]           [ MODEL 3 ]
             Tabular ML            Graph Neural        Autoencoder
              Ensemble               Network             Anomaly
         (Behavior Patterns)    (Social Relations)   (Novel Exploits)
                   │                     │                     │
                   └─────────────────────┼─────────────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  Ensemble Risk Fusion   │
                            │  (Weighted Calibration) │
                            └────────────┬────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  Explainable AI (XAI)   │
                            │ (Natural Lang Reasons)  │
                            └────────────┬────────────┘
                                         ▼
                            ┌─────────────────────────┐
                            │  Bento Box Dashboard    │
                            └─────────────────────────┘
```

### 🧠 Model 1: Tabular ML Ensemble (The Behavior Analyst)
*   **What it does**: It looks at the wallet's metadata (age, average balance, transaction frequency, gas fees, number of failed transactions).
*   **How it thinks**: If a wallet is 1 day old, has sent 100 transactions in 10 minutes, and has 8 failed contract calls, the model flags it as a bot or exploit attempt.
*   **Algorithms used**: XGBoost, Random Forest, and Gradient Boosting.

### 🕸️ Model 2: Graph Neural Network - GNN (The Network Inspector)
*   **What it does**: In blockchain, wallets transact with each other, forming a massive web (a graph). The GNN analyzes **who** the wallet is transacting with.
*   **How it thinks**: Even if a wallet looks clean, if it received money from a wallet that transacted with a known hacker 2 steps ago (2 hops), the GNN flags it. Risk propagates through networks.
*   **Algorithm used**: GraphSAGE (Graph Sample and Aggregate).

### 🔍 Model 3: Autoencoder (The Anomaly Detector)
*   **What it does**: Hackers invent new tricks every day (zero-day exploits). If a hack has never happened before, Models 1 and 2 won't catch it. The Autoencoder is trained **only on normal, safe wallets** to learn what normal behavior looks like.
*   **How it thinks**: When a query comes in, it tries to reconstruct the behavior. If it fails (high **Reconstruction Error**), it means the behavior is extremely strange and anomalous—flagging potential new exploit scripts.
*   **Algorithm used**: Deep Neural Network Autoencoder.

---

## 3. Datasets Used & Training Status

To train these models, public datasets and simulated real-world scenarios were combined:

### 📂 Dataset Table

| Model | Dataset Name | What's Inside? | Size & Details | Is it trained? |
|---|---|---|---|---|
| **Tabular ML** | **Ethereum Fraud Detection Dataset** | Wallet features labeled with `1` (fraudulent) or `0` (legitimate). | ~9,841 real wallets (from Etherscan data). | **Yes** (XGBoost saved in `models/tabular/best_model.pkl`) |
| **GNN** | **Elliptic Bitcoin Transaction Dataset** | The largest public blockchain graph dataset. Maps how funds flow between licit and illicit entities. | 203,769 transaction nodes and 234,355 directed flow edges. | **Yes** (GraphSAGE saved in `models/graph/gnn_model.pt`) |
| **Autoencoder** | **Normal Wallet Baseline Dataset** | An unlabeled subset of clean, active wallets. Used to establish the baseline of "standard" behaviour. | 1,000 clean wallets collected via `src/data_collection.py`. | **Yes** (Autoencoder saved in `models/anomaly/autoencoder.pt`) |

---

## 4. Understanding the 15 Wallet Features (Inputs)

When you scan a wallet, the system automatically calculates **15 mathematical values** (features) to feed into the models. Here is what they mean in simple terms:

1.  **Wallet Age (`wallet_age`)**: Number of days since this wallet made its first transaction. Freshly created wallets are higher risk.
2.  **Wallet Balance (`wallet_balance`)**: Current amount of native cryptocurrency (ETH, TRX, BNB) held in the wallet.
3.  **Transaction Amount (`transaction_amount`)**: Total volume of funds sent by this wallet.
4.  **Transaction Frequency (`transaction_frequency`)**: Average number of transactions sent per day. Spikes indicate automated bots.
5.  **Failed Transactions (`failed_transactions`)**: Count of transactions that errored out. Hackers probing a smart contract for bugs trigger many failures.
6.  **Average Gas Fee (`average_gas_fee`)**: Gas is the transaction fee. High gas fees mean complex smart contract executions.
7.  **Unique Counterparties (`unique_counterparties`)**: How many distinct people/wallets this account has interacted with.
8.  **Smart Contract Calls (`smart_contract_calls`)**: How many times this wallet triggered contract code.
9.  **Rug Pull Token Interaction (`rug_pull_token_interaction`)**: How many times the wallet traded or held scam tokens flagged for exit scams.
10. **Flash Loan Usage (`flash_loan_usage`)**: A binary flag (`1` or `0`) showing if the wallet has executed single-block flash loan borrows.
11. **Burst Activity Score (`burst_activity_score`)**: A decimal between 0 and 1. If it's close to 1, most transactions were sent in one sudden cluster (bot-like).
12. **Graph Centrality (`graph_centrality`)**: How important this wallet is in its local network. Mixers and bridges have high centrality.
13. **Cluster Risk Score (`cluster_risk_score`)**: The percentage of surrounding peer wallets in its network that are high-risk.
14. **Distance to Blacklisted Wallet (`distance_to_blacklisted_wallet`)**: Network hops to a known malicious wallet. `1` means direct contact (very bad).
15. **Reconstruction Error (`reconstruction_error`)**: The deviation score from normal wallets calculated by the Autoencoder.

---

## 5. Scoring & Explainable AI (XAI)

### 📊 How the 0-100 Score is Fused
The models don't vote independently; their predictions are calibrated and combined using a weighted formula config:
```
Final Score = (Tabular Ensemble × 0.5) + (GNN Network Risk × 0.3) + (Autoencoder Anomaly × 0.2)
```

| Score Range | Risk Level | Dashboard Color | Recommended Action |
|---|---|---|---|
| **0 – 20** | **SAFE** | Green (🟢) | Safe to transact normally. |
| **21 – 40** | **LOW** | Cyan (🔵) | Standard interaction; monitor periodically. |
| **41 – 60** | **MEDIUM** | Amber (🟡) | Limit exposure; require multisig approvals. |
| **61 – 80** | **HIGH** | Orange (🟠) | Avoid contract approvals; flag for review. |
| **81 – 100** | **CRITICAL** | Red (🔴) | Do not interact. Immediate alert triggered. |

### 🧠 Explainable AI: Translating Math to English
Machine learning models output decimals (like `0.942`). To make this readable for human auditors, the **Explainable AI (XAI)** layer converts feature parameters and SHAP values into readable cards:
*   Instead of saying: `failed_transactions = 12`
*   The UI displays: `🔴 12 failed transactions — suggests repeated exploit attempts or broken automated scripts.`

---

## 6. How to Run & Experience the App

### Launching the Dashboard (Simplest Way)
1.  Locate the folder: `e:\.aa axi`
2.  Double-click the file named **`Run_Project.bat`**.
3.  This script automatically starts the FastAPI Python server in the background and opens the **Bento Station Dashboard** in your web browser.

### Using the Bento Station Dashboard
*   **Quick Scan**: Click any of the coloured quick-test buttons (like `🟢 TRON Safe Wallet` or `🔴 Known Blacklisted`) to test real-world scenarios.
*   **Search Address**: Paste any EVM (0x...) or TRON (T...) address in the search box, select the chain, and click **Scan Wallet**.
*   **Explore panels**: Check the five top stat cards, review the animated Calibrated Score ring, inspect the Model Ensemble Breakdown bars, read the AI Explainability cards, and view the Recent Token Transfers table at the bottom.

---

## 📁 Core Folder Map

*   `api/app.py`: The FastAPI server that handles routing, serving pages, rate limiting, and JWT authentication.
*   `src/blockchain_api.py`: Connects to nodes and fetches transactions. Uses a seeded system to produce realistic, deterministic test profiles for clean demo environments.
*   `src/nl_reasoning.py`: Generates the friendly text reasons and action recommendations.
*   `app.js` & `index.html`: The fast, premium Bento Box user interface.
*   `presentation/`: Contains an interactive presentation deck and a searchable Viva Q&A engine for examiner evaluations.
