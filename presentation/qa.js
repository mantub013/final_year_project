const QA = [
  // ── CONCEPT ──
  {cat:"concept", q:"What problem does this project solve?",
   a:"DeFi (Decentralised Finance) operates on public blockchains without central gatekeepers, making it a target for fraud, rug pulls, flash-loan exploits, and wash trading. Traditional fraud detection is designed for closed banking systems and cannot interpret on-chain graph structures or novel attack patterns. This project builds a <strong>multi-signal risk intelligence engine</strong> that combines tabular ML, Graph Neural Networks, and unsupervised anomaly detection to score any blockchain wallet 0–100 in real time, explaining <em>why</em> it is risky in plain language."},

  {cat:"concept", q:"What is a rug pull and how does your system detect it?",
   a:"A <strong>rug pull</strong> is when developers of a token project suddenly drain liquidity, crashing the token price to zero. Detection signals used: <ul><li>Interaction with contracts previously flagged as rug-pull distributors (stored in the blacklist)</li><li>GNN: proximity (hops) to known bad-actor wallets in the transaction graph</li><li>Sudden spike in token outflows or sell pressure (burst activity score)</li><li>Autoencoder: the pattern of interactions is behaviorally abnormal vs. the training baseline</li></ul>"},

  {cat:"concept", q:"What is a flash-loan exploit and how is it detected?",
   a:"A <strong>flash loan</strong> allows a borrower to take an uncollateralised loan and repay it within the same transaction block. Exploits manipulate oracle prices within that single block. Detection: <ul><li>Feature: <code>flash_loan_usage</code> — counts calls to known flash-loan provider contracts (Aave, dYdX) in the same session</li><li>Very high transaction amounts followed by immediate repayment in one block is flagged</li><li>The autoencoder reconstruction error spikes because this pattern is far from normal wallet behaviour</li></ul>"},

  {cat:"concept", q:"Why is risk prediction in DeFi harder than in traditional finance?",
   a:"<ul><li><strong>No identity</strong> — wallets are pseudonymous; no KYC data available</li><li><strong>Speed</strong> — attacks complete in a single block (~12 seconds on Ethereum)</li><li><strong>Novel attack vectors</strong> — attackers constantly invent new patterns; labeled fraud data is scarce</li><li><strong>Graph nature</strong> — risk propagates across wallet networks, not just individual accounts</li><li><strong>Multi-chain</strong> — funds move across Ethereum, BSC, Polygon, TRON; a siloed analysis misses cross-chain laundering</li></ul>"},

  {cat:"concept", q:"What is wash trading and does your system detect it?",
   a:"<strong>Wash trading</strong> is artificially inflating volume by repeatedly buying and selling between wallets under the same control. Indicators: <ul><li>High transaction frequency with a small, recurring set of counterparties (<code>unique_counterparties</code> is low vs. volume)</li><li>GNN detects tightly-coupled clusters of wallets (fan-in/fan-out patterns)</li><li>Token transfer amounts are suspiciously round or identical across cycles</li></ul>"},

  // ── ML/DL ──
  {cat:"ml", q:"Why did you choose an ensemble of three model types instead of one?",
   a:"No single model captures all risk signals: <ul><li><strong>Tabular ML</strong> excels at structured features (gas, balance, frequency) but ignores wallet relationships</li><li><strong>GNN</strong> captures network propagation (guilt-by-association) but needs graph structure, not raw numbers</li><li><strong>Autoencoder</strong> detects zero-day anomalies without requiring fraud labels — critical because attackers constantly evolve</li></ul> The calibrated fusion (50/30/20) produces a score that is more robust than any single branch, especially under class imbalance."},

  {cat:"ml", q:"Explain GraphSAGE. Why not standard GCN?",
   a:"A standard <strong>GCN (Graph Convolutional Network)</strong> requires the full adjacency matrix at inference time — impractical for a blockchain graph with millions of nodes. <strong>GraphSAGE</strong> uses inductive learning: it samples a fixed-size neighbourhood and aggregates neighbour embeddings, so it generalises to <em>unseen wallets</em> at inference without retraining. This is essential because new wallets appear on-chain every second."},

  {cat:"ml", q:"How does the Autoencoder detect anomalies?",
   a:"The Autoencoder is trained <em>only on normal wallet behaviour</em>. It learns to compress and reconstruct normal feature vectors with low error. When a fraudulent or unusual wallet is fed in, the reconstruction fails — the <strong>reconstruction error</strong> is high. We calibrate: <code>anomaly_score = min(1.0, recon_err / 0.15)</code>. Threshold 0.15 was chosen so wallets in the top 1% error percentile are flagged. This is unsupervised — no fraud labels needed."},

  {cat:"ml", q:"Why use Platt scaling / calibration in the fusion layer?",
   a:"Raw model outputs (probabilities from sklearn, logits from PyTorch) are <strong>not well-calibrated</strong> — a 0.8 probability from XGBoost does not mean 80% chance of fraud. Platt scaling fits a logistic regression on held-out predictions to map raw scores to true probabilities. Without calibration, the 50/30/20 weighted sum would be a meaningless blend of differently-scaled numbers."},

  {cat:"ml", q:"How do you handle class imbalance in DeFi fraud data?",
   a:"Fraud events are rare (~1–5% of wallets). Strategies used: <ul><li><strong>SMOTE</strong> (Synthetic Minority Over-sampling) during tabular model training</li><li><strong>Class-weight balancing</strong> in sklearn models (<code>class_weight='balanced'</code>)</li><li><strong>F1/AUC as primary metrics</strong> — not accuracy, which is misleading under imbalance</li><li>The Autoencoder is trained only on the majority (normal) class — inherently handles imbalance</li></ul>"},

  {cat:"ml", q:"What evaluation metrics do you use and why not just accuracy?",
   a:"<ul><li><strong>AUC-ROC</strong> — measures ranking ability across all thresholds; threshold-independent</li><li><strong>F1-Score</strong> — harmonic mean of precision and recall; punishes both false positives and false negatives</li><li><strong>Precision-Recall AUC</strong> — better for highly imbalanced datasets than ROC-AUC</li><li>Accuracy is misleading: a model that predicts 'safe' for every wallet gets 95%+ accuracy but misses all fraud</li></ul>"},

  {cat:"ml", q:"How is the GNN trained? What is the training data?",
   a:"The GNN (SimpleGNN / GraphSAGE-style) is trained on a <strong>wallet transaction graph</strong> where nodes are wallets and directed edges are token transfers. Node features include balance, tx count, blacklist flag, and age. Ground-truth labels come from the <strong>Elliptic Bitcoin Dataset</strong> (graph fraud benchmark) supplemented with on-chain blacklist annotations from Etherscan/Forta. Training uses cross-entropy loss on node classification (risky vs. safe)."},

  {cat:"ml", q:"What is SHAP and how is it used here?",
   a:"<strong>SHAP (SHapley Additive exPlanations)</strong> assigns each feature a contribution value to the model's output, grounded in cooperative game theory. For each wallet prediction, SHAP tells us: 'flash_loan_usage contributed +0.23 to the risk score; wallet_age contributed −0.15'. These values are then passed to the NL reasoning module which converts them into plain-English sentences shown on the dashboard."},

  {cat:"ml", q:"Can you explain GNNExplainer?",
   a:"<strong>GNNExplainer</strong> (Ying et al., 2019) finds the minimal subgraph and set of node features that maximise the GNN's prediction for a target node. For a high-risk wallet, it highlights which specific neighbour wallets (edges) are responsible for the high network risk score. This is essential for auditors who need to trace: 'this wallet is risky <em>because</em> it sent funds to wallet X which is 1 hop from a known scammer'."},

  {cat:"ml", q:"Why XGBoost alongside Random Forest?",
   a:"<strong>Random Forest</strong> averages many uncorrelated trees — low variance, robust to noise. <strong>XGBoost</strong> builds trees sequentially, correcting previous errors — typically higher accuracy but more prone to overfitting. The best model is selected by cross-validated F1-AUC so neither is hardcoded. Using both means the auto-selection has a wider hypothesis space to search."},

  {cat:"ml", q:"What is model drift monitoring and why does it matter?",
   a:"<strong>Model drift</strong> occurs when the live data distribution diverges from what the model was trained on — common in DeFi as attackers adapt. The system monitors <strong>feature distribution shift</strong> using statistical tests (KS-test or PSI — Population Stability Index). When drift exceeds a threshold, an alert fires and retraining is triggered. Without this, model accuracy silently degrades over time."},

  // ── TECH STACK ──
  {cat:"tech", q:"Why FastAPI instead of Flask?",
   a:"<ul><li><strong>Async-native</strong> — FastAPI uses Python's <code>asyncio</code>; blockchain API calls are I/O-bound, so async dramatically improves throughput</li><li><strong>Automatic OpenAPI docs</strong> — /docs and /redoc out-of-the-box</li><li><strong>Pydantic validation</strong> — request/response schemas are validated at the type level; invalid wallet addresses are rejected before hitting the model</li><li><strong>Performance</strong> — benchmarks show FastAPI 2–3× faster than Flask for async workloads</li></ul>"},

  {cat:"tech", q:"Why Redis for the feature store?",
   a:"Redis is an in-memory key-value store with sub-millisecond latency. Blockchain API calls (Etherscan, Alchemy) take 200–1000 ms each. By caching computed feature vectors for recently-queried wallets in Redis with a configurable TTL, repeated lookups are served in &lt;1 ms. PostgreSQL (offline store) handles historical features for model training where latency matters less."},

  {cat:"tech", q:"What does Kafka do in this system?",
   a:"<strong>Kafka</strong> is a distributed message broker. New block events (transactions, token transfers) from blockchain nodes are published to a Kafka topic by a <code>stream_listener.py</code> producer. Multiple consumers can process these in parallel — re-scoring affected wallets, updating feature store entries, and triggering alerts — without blocking the REST API. This enables near-real-time alert latency (&lt;30 s) vs. polling-based approaches (~minutes)."},

  {cat:"tech", q:"What is Docker Compose doing here?",
   a:"Docker Compose orchestrates the full stack with one command (<code>docker-compose up --build</code>): FastAPI, Redis, PostgreSQL, Prometheus, and Grafana each run in isolated containers with defined networking and volume mounts. Benefits: <ul><li>Reproducible environment — eliminates 'works on my machine'</li><li>Service dependency ordering (API waits for Redis/Postgres to be healthy)</li><li>Easy teardown and reset for demos</li></ul>"},

  {cat:"tech", q:"What is MLflow used for?",
   a:"<strong>MLflow</strong> provides the <strong>model registry</strong>: every trained model is logged with its training metrics (F1, AUC), hyperparameters, and a timestamp. The API loads the model tagged 'production'. If a new model underperforms after deployment, one command rolls back to the previous version. MLflow also tracks experiments — comparing RF vs. XGBoost vs. GBM runs in a UI."},

  {cat:"tech", q:"What does Prometheus + Grafana monitor?",
   a:"<ul><li><strong>Prometheus</strong> scrapes metrics exposed by FastAPI at <code>/metrics</code>: request latency (p50/p95/p99), model inference time, error rate, cache hit rate</li><li><strong>Grafana</strong> visualises these as live dashboards with alerting rules (e.g., alert if p95 latency &gt; 2 s)</li><li>Model drift metrics (feature mean/std vs. training baseline) are also exposed and plotted</li></ul>"},

  {cat:"tech", q:"Why PyTorch Geometric (PyG) for the GNN?",
   a:"PyG provides efficient, GPU-accelerated sparse message-passing layers (including GraphSAGE, GCN, GAT) with batching support for variable-size graphs — essential because different wallet subgraphs have different numbers of nodes. Implementing message-passing from scratch in NumPy would be orders of magnitude slower and error-prone."},

  {cat:"tech", q:"How does the CI/CD pipeline work?",
   a:"GitHub Actions (<code>.github/workflows/ci-cd.yml</code>) runs on every push/PR: <ul><li><strong>Lint</strong> — flake8/black code style checks</li><li><strong>Unit tests</strong> — pytest runs test_preprocessing, test_models, test_api, test_data_quality</li><li><strong>Build Docker image</strong> — ensures the container builds successfully</li><li><strong>Deploy</strong> (on merge to main) — pushes image to registry and restarts the service</li></ul> This prevents regressions and automates deployments."},

  // ── DEFI / BLOCKCHAIN ──
  {cat:"defi", q:"What is DeFi and how does it differ from CeFi?",
   a:"<strong>DeFi (Decentralised Finance)</strong> runs on smart contracts — self-executing code on a blockchain — with no intermediary (bank, exchange) controlling funds. <strong>CeFi (Centralised Finance)</strong> relies on trusted institutions. DeFi is permissionless (anyone can interact), transparent (all transactions are public), and non-custodial (users control their own keys). The lack of a gatekeeper is both its strength (open access) and weakness (no fraud prevention layer)."},

  {cat:"defi", q:"Why support multiple chains (Ethereum, BSC, Polygon, TRON)?",
   a:"Fraudsters routinely bridge funds across chains to obscure trails — a technique called <strong>chain hopping</strong>. Analysing only Ethereum misses 40–60% of DeFi activity that occurs on BSC, Polygon, and TRON. Chain support is pluggable via <code>config/chains.yaml</code>: adding a new chain means adding an API adapter, not rewriting the pipeline."},

  {cat:"defi", q:"What is a smart contract and why is contract interaction a risk signal?",
   a:"A <strong>smart contract</strong> is immutable code deployed on-chain that executes automatically when called. Risk signals: <ul><li>Interactions with <em>unverified</em> contracts (source code not published)</li><li>Calls to contracts flagged in threat intelligence databases as rug-pull or phishing contracts</li><li>High volume of unique contract calls in short time — may indicate bot/MEV activity</li></ul>"},

  {cat:"defi", q:"How do you get real blockchain data? What APIs are used?",
   a:"<ul><li><strong>Etherscan / BscScan / PolygonScan / Arbiscan</strong> — REST APIs for transaction history, token transfers, contract ABI</li><li><strong>Alchemy / Infura</strong> — full archive node RPC access for balance queries and raw block data via Web3.py</li><li><strong>TronScan</strong> — TRON chain data</li><li><strong>Fallback mocks</strong> — when API rate limits or network issues occur, deterministic mock data ensures the system stays demonstrable</li></ul>"},

  {cat:"defi", q:"What are gas fees and why are they a feature?",
   a:"<strong>Gas</strong> is the computational fee paid to Ethereum miners/validators per operation. <strong>High average gas fee</strong> can indicate: MEV bots willing to pay premium for front-running, complex contract interactions (flash loans), or urgency to get transactions confirmed ahead of others. Abnormally high or low gas patterns are behavioural signals used in the tabular feature set."},

  {cat:"defi", q:"What is the Elliptic dataset?",
   a:"The <strong>Elliptic Bitcoin Transaction Dataset</strong> is a publicly available graph dataset of 203,769 Bitcoin transactions labelled as licit, illicit, or unknown, with 166 features per node. It is widely used as the benchmark for blockchain fraud detection graph models. We use it for <strong>GNN pre-training</strong> because labeled on-chain Ethereum fraud data is scarce — transfer learning from Bitcoin graph patterns improves GNN initialisation."},

  // ── SECURITY ──
  {cat:"security", q:"How is the API secured?",
   a:"<ul><li><strong>JWT (JSON Web Tokens)</strong> — all endpoints require a valid Bearer token in the Authorization header. Tokens are signed with a secret key and have a configurable expiry</li><li><strong>Rate limiting</strong> — SlowAPI enforces per-key request limits (e.g., 100 req/min) to prevent abuse and API scraping</li><li><strong>Input validation</strong> — wallet addresses are checksum-validated (EIP-55) before any processing</li><li><strong>Audit logging</strong> — every prediction is written to a structured log (wallet, requester IP, score, timestamp) for forensic tracing</li></ul>"},

  {cat:"security", q:"Why validate wallet address checksums?",
   a:"EIP-55 defines a <strong>mixed-case checksum encoding</strong> for Ethereum addresses. Validating this before lookup prevents: injection-style attacks using malformed addresses, accidental typos that would waste API credits on invalid lookups, and potential bypass attempts using addresses that look valid but are not. Web3.py's <code>Web3.isChecksumAddress()</code> performs this check."},

  {cat:"security", q:"Can the system be adversarially evaded?",
   a:"Yes — any ML system can be gamed. Known evasion vectors: <ul><li><strong>Gradual warming</strong> — attacker slowly builds wallet history to appear legitimate before striking</li><li><strong>Sybil attack</strong> — splitting activity across many fresh wallets each below thresholds</li></ul> Mitigations: <ul><li>GNN makes Sybil harder — the <em>cluster</em> as a whole gets flagged even if individual wallets are clean</li><li>Autoencoder detects novel behavioural patterns even if individual features are within normal range</li><li>Model drift monitoring triggers retraining when attacker populations shift the distribution</li></ul>"},

  // ── DESIGN ──
  {cat:"design", q:"Why a custom Bento dashboard instead of Streamlit?",
   a:"Streamlit re-renders the entire Python script on every user interaction — this causes noticeable lag when re-querying blockchain APIs. The custom <strong>Bento Station</strong> dashboard (vanilla JS + FastAPI backend) gives: <ul><li>True async data fetching — UI never blocks</li><li>Smooth animated gauge and chart updates without full-page reload</li><li>Full control over layout, animations, and interactivity</li><li>Served directly from FastAPI's static files — single deployment unit, no separate Streamlit server</li></ul>"},

  {cat:"design", q:"What is the feature store pattern and why use it?",
   a:"A <strong>feature store</strong> separates feature computation from model training and serving: <ul><li><strong>Offline store</strong> (PostgreSQL/Parquet) — point-in-time correct historical features for training reproducibility</li><li><strong>Online store</strong> (Redis) — latest pre-computed features for low-latency serving</li></ul> Without it, every prediction call would re-fetch and recompute all blockchain data (~2–5 seconds). With it, cached features make re-scoring &lt;100 ms."},

  {cat:"design", q:"How does the model registry enable safe deployments?",
   a:"Every trained model is saved with a version tag (timestamp + metrics). The API loads the model tagged <code>production</code>. When a new model is trained: <ol><li>It is staged and shadow-tested against live traffic</li><li>If F1/AUC improves, it is promoted to production</li><li>If it regresses, one CLI command points the tag back to the previous version</li></ol>This avoids the need to redeploy code to roll back a bad model."},

  {cat:"design", q:"How does the system scale to millions of wallets?",
   a:"<ul><li><strong>Kafka</strong> allows horizontal scaling of consumers — add more workers to process more events per second</li><li><strong>Redis</strong> TTL-based caching eliminates redundant API calls for recently-active wallets</li><li><strong>GraphSAGE inductive inference</strong> — scores new wallets without rebuilding the full graph</li><li><strong>Docker</strong> allows running multiple FastAPI replicas behind a load balancer</li><li>The feature store precomputes features offline for batch re-scoring during off-peak hours</li></ul>"},

  // ── FUTURE ──
  {cat:"future", q:"What are the limitations of the current system?",
   a:"<ul><li><strong>Graph scale</strong> — the in-memory NetworkX graph is limited to ~10K nodes; production needs a distributed graph DB (Neo4j or TigerGraph)</li><li><strong>Labelled data scarcity</strong> — tabular models rely on limited ground-truth fraud labels; the Elliptic dataset is Bitcoin, not Ethereum</li><li><strong>Cross-chain bridge detection</strong> — funds moving through bridges (like Hop or Stargate) partially obscure trails</li><li><strong>Latency</strong> — full GNN inference on a large subgraph takes 1–3 seconds; needs optimisation for real-time alerting at scale</li></ul>"},

  {cat:"future", q:"What future enhancements are planned?",
   a:"<ul><li><strong>Federated learning</strong> — train across multiple DeFi protocols without sharing raw wallet data, preserving privacy</li><li><strong>Cross-chain bridge exploit detection</strong> — track funds hopping across chains via bridge contracts</li><li><strong>Reinforcement learning</strong> — adaptive alert thresholds that learn from analyst feedback (true/false positive labels)</li><li><strong>AI chatbot</strong> — natural-language querying of risk reports ('Why is wallet X risky?')</li><li><strong>DAO governance risk</strong> — detect manipulation of on-chain voting (whale coordination, bribery patterns)</li></ul>"},

  {cat:"future", q:"How would you deploy this to production at a DeFi protocol?",
   a:"<ol><li>Replace mock fallbacks with production-grade Alchemy/Infura connections with dedicated API keys</li><li>Deploy on Kubernetes (K8s) with horizontal pod autoscaling on the FastAPI and Kafka consumer deployments</li><li>Use a managed Redis cluster (AWS ElastiCache) and PostgreSQL (AWS RDS) for the feature store</li><li>Integrate with a threat intelligence feed (Chainalysis, Forta Network) for real-time blacklist updates</li><li>Set up PagerDuty alerting on Prometheus alert rules for SLA breaches</li><li>Conduct a security audit of the JWT implementation and rate-limiting configuration</li></ol>"}
];

// ── Render ──
function renderQA(items){
  const list = document.getElementById('qa-list');
  list.innerHTML = '';
  items.forEach((qa,i)=>{
    const d = document.createElement('div');
    d.className = 'qa-item';
    d.dataset.cat = qa.cat;
    d.innerHTML = `
      <div class="qa-q" onclick="toggle(${i})">
        <div class="qa-q-text">${qa.q}</div>
        <div class="qa-q-meta">
          <span class="qa-cat-badge cat-${qa.cat}">${qa.cat}</span>
          <span class="qa-toggle">+</span>
        </div>
      </div>
      <div class="qa-a">${qa.a}</div>`;
    list.appendChild(d);
  });
}

function toggle(i){
  const items = document.querySelectorAll('.qa-item:not(.hidden)');
  const el = items[i];
  if(!el) return;
  el.classList.toggle('open');
}

// Tabs
document.querySelectorAll('.qa-tab').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.qa-tab').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const cat = btn.dataset.cat;
    const filtered = cat==='all' ? QA : QA.filter(q=>q.cat===cat);
    renderQA(filtered);
  });
});

// Search
document.getElementById('qa-search').addEventListener('input',function(){
  const q = this.value.toLowerCase();
  const cat = document.querySelector('.qa-tab.active').dataset.cat;
  const base = cat==='all' ? QA : QA.filter(x=>x.cat===cat);
  const filtered = q ? base.filter(x=>x.q.toLowerCase().includes(q)||x.a.toLowerCase().includes(q)) : base;
  renderQA(filtered);
});

renderQA(QA);
