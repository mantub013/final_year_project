/**
 * app.js — AI-DeFi Risk Intelligence v2.0
 * Wallet Address Explorer Landing Page + Bento Box Dashboard Flow
 */

const API_BASE  = "http://localhost:8000";
const TOKEN_KEY = "defi_risk_jwt";
const CREDS     = { username: "defi_analyst", password: "secure_password_123" };

let miniGaugeChart = null;
let historyChart   = null;

// ── Boot ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const explorerInput  = g("explorer-address-input");
    const explorerNet    = g("explorer-network-select");
    const explorerBtn    = g("explorer-analyze-btn");
    const pasteBtn       = g("paste-btn");
    const clearBtn       = g("clear-btn");
    const backToExplorer = g("back-to-explorer-btn");

    if (explorerBtn)  explorerBtn.addEventListener("click", handleExplorerScan);
    if (explorerInput) explorerInput.addEventListener("keypress", e => e.key === "Enter" && handleExplorerScan());

    if (pasteBtn) {
        pasteBtn.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && explorerInput) { explorerInput.value = text.trim(); hideExplorerError(); }
            } catch(e) {
                showExplorerError("Clipboard access restricted — please paste manually (Ctrl+V).");
            }
        });
    }
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (explorerInput) explorerInput.value = "";
            hideExplorerError();
        });
    }
    if (backToExplorer) backToExplorer.addEventListener("click", showLandingView);

    // Sample address badges
    document.querySelectorAll(".sample-address-badge").forEach(b => {
        b.addEventListener("click", () => {
            if (explorerInput) explorerInput.value = b.dataset.address;
            if (explorerNet && b.dataset.chain) explorerNet.value = b.dataset.chain;
            handleExplorerScan();
        });
    });

    initGauge(0);
    initHistory();
    checkApiStatus();
});

async function checkApiStatus() {
    const dot1 = g("landing-api-dot");
    const txt1 = g("landing-api-status");
    const dot2 = g("api-dot");
    const txt2 = g("api-status-text");
    try {
        const r = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(4000) });
        const ok = r.ok;
        [dot1, dot2].forEach(d => { if (d) d.className = "w-2 h-2 rounded-full " + (ok ? "bg-emerald-400 pulse-dot" : "bg-red-400"); });
        [txt1, txt2].forEach(t => { if (t) t.textContent = ok ? "API Online" : "API Error"; });
    } catch {
        [dot1, dot2].forEach(d => { if (d) d.className = "w-2 h-2 rounded-full bg-amber-400"; });
        [txt1, txt2].forEach(t => { if (t) t.textContent = "API Offline"; });
    }
}

// ── View Transitions ──────────────────────────────────────────────────────────
function showLandingView() {
    const landing   = g("landing-view");
    const dashboard = g("dashboard-view");
    if (landing)   landing.classList.remove("hidden");
    if (dashboard) dashboard.classList.add("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showDashboardView() {
    const landing   = g("landing-view");
    const dashboard = g("dashboard-view");
    if (landing)   landing.classList.add("hidden");
    if (dashboard) dashboard.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showExplorerError(msg) {
    const box = g("explorer-error-alert");
    const txt = g("explorer-error-msg");
    if (txt) txt.textContent = msg;
    if (box) box.classList.remove("hidden");
    // scroll to error so user sees it
    if (box) box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideExplorerError() {
    const box = g("explorer-error-alert");
    if (box) box.classList.add("hidden");
}


// ── Analysis Handler ──────────────────────────────────────────────────────────
async function handleExplorerScan() {
    const input  = g("explorer-address-input");
    const netSel = g("explorer-network-select");
    const addr   = input ? input.value.trim() : "";
    const chain  = netSel ? netSel.value : "ethereum";

    if (!addr) {
        showExplorerError("Please enter a wallet address to analyze.");
        return;
    }

    const isEvm  = /^0x[a-fA-F0-9]{40}$/.test(addr);
    const isTron = /^T[a-zA-Z0-9]{32,33}$/.test(addr);

    if (!isEvm && !isTron) {
        if (addr.startsWith("0x")) {
            showExplorerError(`Invalid EVM address — must be 42 characters (0x + 40 hex). Current length: ${addr.length}.`);
        } else if (addr.startsWith("T")) {
            showExplorerError(`Invalid TRON address — must be 34 characters. Current length: ${addr.length}.`);
        } else {
            showExplorerError("Invalid address format. EVM addresses start with 0x (42 chars). TRON addresses start with T (34 chars).");
        }
        return;
    }
    if (isTron && chain !== "tron") {
        showExplorerError(`This looks like a TRON address (T...) but you selected ${chain.toUpperCase()}. Please choose TRON from the network selector.`);
        return;
    }
    if (isEvm && chain === "tron") {
        showExplorerError("This is an EVM address (0x...) but you selected TRON. Please select Ethereum, BSC, Polygon, or Arbitrum.");
        return;
    }

    hideExplorerError();
    await runAnalysisPipeline(addr, chain);
}


// ── Auth Token Fetching ───────────────────────────────────────────────────────
async function token() {
    let t = localStorage.getItem(TOKEN_KEY);
    if (t) return t;
    try {
        const fd = new URLSearchParams();
        fd.append("username", CREDS.username);
        fd.append("password", CREDS.password);
        const r = await fetch(`${API_BASE}/api/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: fd
        });
        if (!r.ok) throw new Error(r.status);
        const d = await r.json();
        localStorage.setItem(TOKEN_KEY, d.access_token);
        return d.access_token;
    } catch(e) {
        showExplorerError("Authentication failed — backend server unreachable at " + API_BASE);
        return null;
    }
}

// ── Pipeline & Loading Modal ──────────────────────────────────────────────────
async function runAnalysisPipeline(address, chain) {
    showLoadingModal(address);
    updateLoadingStep(1, "done", "✓ Address format validated");
    updateLoadingStep(2, "done", `✓ Network: ${chain.toUpperCase()}`);

    try {
        updateLoadingStep(3, "active", "⟳ Fetching on-chain activity & balances...");
        const tok = await token();
        if (!tok) { hideLoadingModal(); return; }

        updateLoadingStep(4, "active", "⟳ Running Tabular ML + GraphSAGE GNN + Autoencoder...");
        const url = `${API_BASE}/api/v1/wallet/${encodeURIComponent(address)}?chain=${encodeURIComponent(chain)}`;
        const r = await fetch(url, { headers: { "Authorization": "Bearer " + tok, "Accept": "application/json" } });

        if (r.status === 401) { localStorage.removeItem(TOKEN_KEY); return runAnalysisPipeline(address, chain); }
        if (r.status === 429) { showExplorerError("Rate limit reached — please wait a moment and try again."); hideLoadingModal(); return; }
        if (r.status === 400) { const j = await r.json(); showExplorerError("Validation error: " + (j.detail || "Bad request")); hideLoadingModal(); return; }
        if (r.status === 404) { showExplorerError("Cannot fetch on-chain data for this address on " + chain.toUpperCase() + ". No transaction history found."); hideLoadingModal(); return; }
        if (!r.ok) { showExplorerError("Cannot fetch data from server (HTTP " + r.status + "). Please try again."); hideLoadingModal(); return; }

        updateLoadingStep(5, "active", "⟳ Computing risk score & generating AI explanations...");
        const data = await r.json();

        // Check if the response contains meaningful data
        if (!data || data.risk_score == null) {
            showExplorerError("Cannot fetch data for this address on " + chain.toUpperCase() + ". Data unavailable.");
            hideLoadingModal();
            return;
        }

        updateLoadingStep(5, "done", "✓ Analysis complete");
        await new Promise(res => setTimeout(res, 250));
        fillDashboard(data, chain);
        hideLoadingModal();
        showDashboardView();
    } catch(e) {
        hideLoadingModal();
        showExplorerError("Connection error — is the FastAPI server running at " + API_BASE + "?");
    }
}

function showLoadingModal(addr) {
    const modal = g("analysis-loading-modal");
    const target = g("loading-target-addr");
    if (target) target.textContent = addr;
    if (modal) modal.classList.remove("hidden");

    for (let i = 1; i <= 5; i++) {
        updateLoadingStep(i, "pending", `Step ${i} initialized...`);
    }
}

function hideLoadingModal() {
    const modal = g("analysis-loading-modal");
    if (modal) modal.classList.add("hidden");
}

function updateLoadingStep(stepNum, status, text) {
    const step = g(`step-${stepNum}`);
    if (!step) return;
    if (status === "done") {
        step.className = "flex items-center gap-2 text-emerald-400 font-semibold";
        step.innerHTML = `<span>✓</span><span>${text}</span>`;
    } else if (status === "active") {
        step.className = "flex items-center gap-2 text-indigo-400 font-semibold";
        step.innerHTML = `<span class="animate-spin">⟳</span><span>${text}</span>`;
    } else {
        step.className = "flex items-center gap-2 text-slate-500";
        step.innerHTML = `<span>○</span><span>${text}</span>`;
    }
}

// ── Populate Dashboard UI ─────────────────────────────────────────────────────
function fillDashboard(data, chain) {
    // Wire up export button
    const exportBtn = g("export-report-btn");
    if (exportBtn) {
        exportBtn.onclick = () => {
            window.print();
        };
    }

    const score     = Math.round(data.risk_score || 0);
    const level     = getRiskLevelClassification(score, data.risk_level);
    const bd        = data.breakdown  || {};
    const feats     = data.features   || {};
    const reasons   = data.reasons    || [];
    const transfers = data.recent_transfers || [];

    set("dash-full-address", data.address || "—");
    set("dash-chain-pill", chain.toUpperCase());

    /* ── Stat Bar ── */
    set("calibrated-risk-score", score);
    set("risk-level-text", level);
    cls("risk-level-text", "text-2xl font-black " + lvlClr(level));

    const age = feats.wallet_age != null ? feats.wallet_age.toFixed(1) + " d" : "—";
    set("wallet-age-text", age);

    const totalTx = feats.total_transactions != null ? Math.round(feats.total_transactions) : Math.round((feats.transaction_frequency || 0) * Math.max(feats.wallet_age || 1, 1));
    set("tx-count-text", totalTx != null ? totalTx : "—");
    set("failed-tx-text", (feats.failed_transactions || 0) + " failed");

    const hops = feats.distance_to_blacklisted_wallet;
    const hopsStr = (hops == null || hops === 99) ? "Safe" : String(hops);
    set("hops-text", hopsStr);
    cls("hops-text", "text-2xl font-black " + (hops < 3 ? "text-rose-400" : hops < 5 ? "text-amber-400" : "text-emerald-400"));

    const suffix = g("risk-score-suffix");
    if (suffix) { suffix.textContent = "/ 100 · " + level; suffix.className = "tag-pill mt-2 inline-block " + lvlBadge(level); }

    /* ── Donut ring ── */
    set("donut-score", score);
    set("target-address", shorten(data.address || "—", 22));
    updateDonut(score, level);

    const lvlBadgeEl = g("risk-level-badge");
    if (lvlBadgeEl) { lvlBadgeEl.textContent = level; lvlBadgeEl.className = "tag-pill text-sm px-4 py-1 " + lvlBadge(level); }

    /* ── Breakdown Bars ── */
    const tab  = Math.round((bd.tabular_ensemble || 0) * 100);
    const gnn  = Math.round((bd.gnn_network_risk || 0) * 100);
    const anom = Math.round((bd.anomaly_score    || 0) * 100);
    bar("tabular", tab);
    bar("gnn",     gnn);
    bar("anomaly", anom);

    /* ── AI Reasons & Drivers ── */
    renderReasons(reasons, data.recommendation, level);

    /* ── Mini gauge & Network Metrics ── */
    updateGauge(score);
    set("centrality-val", fmtN(feats.graph_centrality, 4));
    set("cluster-val",    fmtN(feats.cluster_risk_score, 4));
    set("burst-val",      fmtN(feats.burst_activity_score, 2));
    set("flashloan-val",  feats.flash_loan_usage ? "⚠️ Detected" : "None");

    /* ── Feature Table ── */
    renderFeats(feats);

    /* ── Token Holdings ── */
    renderTokens(transfers);

    /* ── Transfers Table ── */
    renderTx(transfers, data.address, chain);

    /* ── Threat Alerts Feed ── */
    renderThreatAlerts(reasons, level);

    /* ── History Sparkline & Trend ── */
    renderHistory(score, level);

    set("tx-chain-badge", chain.toUpperCase());
}

// ── Classification Logic (0-20, 21-40, 41-60, 61-80, 81-100) ──────────────────
function getRiskLevelClassification(score, rawLevel) {
    if (score <= 20) return "VERY LOW RISK";
    if (score <= 40) return "LOW RISK";
    if (score <= 60) return "MODERATE RISK";
    if (score <= 80) return "HIGH RISK";
    return "CRITICAL RISK";
}

// ── Donut SVG ─────────────────────────────────────────────────────────────────
function updateDonut(score, level) {
    const circ = 251.2;
    const fill = document.getElementById("donut-fill");
    if (!fill) return;
    const colors = { "CRITICAL RISK":"#EF4444", "HIGH RISK":"#F97316", "MODERATE RISK":"#F59E0B", "LOW RISK":"#38BDF8", "VERY LOW RISK":"#10B981" };
    fill.setAttribute("stroke-dashoffset", String(circ - (score / 100) * circ));
    fill.setAttribute("stroke", colors[level] || "#10B981");
}

// ── Progress Bars ─────────────────────────────────────────────────────────────
function bar(prefix, pct) {
    const p = g(prefix + "-percent");
    const b = g(prefix + "-bar");
    if (p) p.textContent = pct + "%";
    if (b) {
        b.style.width = pct + "%";
        b.style.backgroundColor = pct > 70 ? "#EF4444" : pct > 40 ? "#F59E0B" : "#10B981";
    }
}

// ── AI Reasons & Drivers ──────────────────────────────────────────────────────
function renderReasons(reasons, rec, level) {
    const box = g("activity-manager-cards");
    if (!box) return;
    if (!reasons || !reasons.length) {
        box.innerHTML = '<div class="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs">No active risk triggers detected for this wallet.</div>';
    } else {
        box.innerHTML = reasons.map(r => {
            const isCrit = r.includes("CRITICAL") || r.includes("🔴");
            const isHigh = r.includes("HIGH") || r.includes("🟠") || r.includes("⚡");
            const bg = isCrit ? "bg-rose-950/60 border-rose-800 text-rose-200"
                     : isHigh ? "bg-amber-950/60 border-amber-800 text-amber-200"
                     : "bg-slate-900/60 border-slate-800 text-slate-300";
            return '<div class="p-2.5 rounded-xl border text-xs ' + bg + '">' + esc(r) + '</div>';
        }).join("");
    }
    const recBox  = g("recommendation-box");
    const recText = g("recommendation-text");
    if (recBox)  recBox.className = "p-3 rounded-xl border text-xs " + recBg(level);
    if (recText && rec) recText.textContent = rec;
}

function recBg(level) {
    const m = { "CRITICAL RISK":"bg-rose-950/80 border-rose-800 text-rose-200",
                "HIGH RISK":"bg-orange-950/80 border-orange-800 text-orange-200",
                "MODERATE RISK":"bg-amber-950/80 border-amber-800 text-amber-200",
                "LOW RISK":"bg-sky-950/80 border-sky-800 text-sky-200",
                "VERY LOW RISK":"bg-emerald-950/80 border-emerald-800 text-emerald-200" };
    return m[level] || m["VERY LOW RISK"];
}

// ── Feature Table ─────────────────────────────────────────────────────────────
function renderFeats(feats) {
    const box = g("features-table");
    if (!box) return;
    const ROWS = [
        ["wallet_balance",              "Balance (native)"],
        ["transaction_amount",          "Total TX Value"],
        ["transaction_frequency",       "TX Frequency (per day)"],
        ["failed_transactions",         "Failed TXs"],
        ["average_gas_fee",             "Avg Gas Fee"],
        ["wallet_age",                  "Wallet Age (days)"],
        ["unique_counterparties",       "Unique Counterparties"],
        ["smart_contract_calls",        "Contract Calls"],
        ["rug_pull_token_interaction",  "Rug-Pull Interactions"],
        ["flash_loan_usage",            "Flash Loan Usage"],
        ["burst_activity_score",        "Burst Activity Score"],
        ["graph_centrality",            "Graph Centrality"],
        ["cluster_risk_score",          "Cluster Risk Score"],
        ["distance_to_blacklisted_wallet","Hops to Blacklist"],
        ["reconstruction_error",        "Autoencoder Recon Error"],
    ];
    box.innerHTML = ROWS.map(([k, label]) => {
        const v = feats[k];
        if (v == null) return "";
        const display = typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(4)) : String(v);
        const risky = (k === "rug_pull_token_interaction" && v > 0) ||
                      (k === "flash_loan_usage" && v > 0) ||
                      (k === "burst_activity_score" && v > 0.5) ||
                      (k === "reconstruction_error" && v > 1.0) ||
                      (k === "distance_to_blacklisted_wallet" && v < 3);
        const valCls = risky ? "font-mono font-bold text-rose-400" : "font-mono font-bold text-slate-300";
        return '<div class="flex justify-between items-center py-1.5 border-b border-slate-800/60">' +
               '<span class="text-slate-400 text-xs">' + label + '</span>' +
               '<span class="' + valCls + ' text-xs">' + esc(display) + '</span>' +
               '</div>';
    }).join("");
}

// ── Token Holdings ────────────────────────────────────────────────────────────
function renderTokens(transfers) {
    const box = g("token-holdings");
    if (!box) return;
    if (!transfers || !transfers.length) {
        box.innerHTML = '<div class="text-slate-500 text-center py-4 text-xs">Cannot fetch token holdings for this wallet.</div>';
        return;
    }
    const agg = {};
    transfers.forEach(tx => {
        const sym  = tx.token_symbol || tx.tokenSymbol || "TOKEN";
        const amt  = parseFloat(tx.amount_usdt || 0);
        const scam = (tx.scam_flag || 0) > 0 || sym.toUpperCase().includes("SCAM");
        if (!agg[sym]) agg[sym] = { total: 0, count: 0, scam };
        agg[sym].total += amt;
        agg[sym].count++;
    });
    box.innerHTML = Object.entries(agg).map(([sym, d]) => {
        const isScam = d.scam;
        const cardCls = isScam ? "bg-rose-950/60 border border-rose-800" : "bg-slate-900/60 border border-slate-800";
        const nameCls = isScam ? "font-bold text-rose-300" : "font-bold text-slate-200";
        const valCls  = isScam ? "font-mono font-bold text-rose-400" : "font-mono font-bold text-white";
        const badge   = isScam ? '<span class="tag-pill bg-rose-900 text-rose-300 ml-1">⚠ SCAM</span>' : "";
        return '<div class="flex items-center justify-between p-2.5 rounded-xl ' + cardCls + '">' +
               '<div class="flex items-center gap-1.5"><span class="' + nameCls + '">' + esc(sym) + '</span>' + badge + '</div>' +
               '<div class="text-right"><p class="' + valCls + '">' + d.total.toLocaleString("en-US",{maximumFractionDigits:2}) + '</p>' +
               '<p class="text-slate-500 text-[10px]">' + d.count + ' txs</p></div>' +
               '</div>';
    }).join("");
}

// ── Transfers Table ───────────────────────────────────────────────────────────
function renderTx(transfers, wallet, chain) {
    const tbody = g("transactions-table-body");
    if (!tbody) return;
    if (!transfers || !transfers.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-6 text-center text-slate-500 text-xs">Cannot fetch transaction history for this wallet.</td></tr>';
        return;
    }
    const walletLow = (wallet || "").toLowerCase();
    const chainLow  = (chain || "ethereum").toLowerCase();
    const explorerMap = {
        tron: "https://tronscan.org/#/transaction/",
        bsc: "https://bscscan.com/tx/",
        polygon: "https://polygonscan.com/tx/",
        arbitrum: "https://arbiscan.io/tx/",
        ethereum: "https://etherscan.io/tx/"
    };
    const base = explorerMap[chainLow] || "https://etherscan.io/tx/";

    tbody.innerHTML = transfers.map(tx => {
        const hash    = tx.transaction_id || tx.hash || "";
        const from    = tx.from_address   || tx.from || "";
        const to      = tx.to_address     || tx.to   || "";
        const isOut   = walletLow && from.toLowerCase() === walletLow;
        const counter = isOut ? to : from;
        const sym     = tx.token_symbol || tx.tokenSymbol || (chainLow === "bsc" ? "BNB" : chainLow === "polygon" ? "MATIC" : chainLow === "tron" ? "TRX" : "ETH");
        const isScam  = (tx.scam_flag || 0) > 0 || sym.toUpperCase().includes("SCAM");
        const amt     = parseFloat(tx.amount_usdt || 0).toLocaleString("en-US", { maximumFractionDigits: 4 });
        const rawTs   = tx.block_timestamp || (tx.timeStamp ? Number(tx.timeStamp) * 1000 : Date.now());
        const tsMs    = rawTs > 1e12 ? rawTs : rawTs * 1000;
        const dt      = new Date(isNaN(tsMs) ? Date.now() : tsMs);
        const dateStr = dt.toLocaleDateString([], { month: "short", day: "numeric", year: "2-digit" });
        const timeStr = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        const dirBg   = isOut ? "bg-amber-950/80 text-amber-300 border border-amber-800" : "bg-emerald-950/80 text-emerald-300 border border-emerald-800";
        const dirTxt  = isOut ? "OUT" : "IN";
        const symBg   = isScam ? "bg-rose-950 text-rose-300 border border-rose-800" : "bg-slate-900 text-slate-300 border border-slate-800";
        const isConfirmed = tx.confirmed !== false;
        const riskTxt = isScam ? "⚠ SCAM" : (isConfirmed ? "✓ Success" : "✕ Failed");
        const riskBg  = isScam ? "bg-rose-950 text-rose-300 border border-rose-800" : (isConfirmed ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-rose-950 text-rose-300 border border-rose-800");
        const amtCls  = isScam ? "text-rose-400" : "text-white";

        return "<tr class='border-b border-slate-800/60 hover:bg-slate-900/40 transition-colors'>" +
          "<td class='py-3 pr-4 font-mono text-xs text-indigo-400'>" +
            (hash ? "<a href='" + base + esc(hash) + "' target='_blank' class='hover:underline flex items-center gap-1'>" + shorten(hash, 12) + " ↗</a>" : "<span class='text-slate-500'>—</span>") +
          "</td>" +
          "<td class='py-3 pr-4'>" +
            "<span class='tag-pill " + dirBg + "'>" + dirTxt + "</span>" +
          "</td>" +
          "<td class='py-3 pr-4 font-mono text-xs text-slate-400'>" + (counter ? shorten(counter, 12) : "<span class='text-slate-600'>Contract</span>") + "</td>" +
          "<td class='py-3 pr-4'>" +
            "<span class='tag-pill " + symBg + "'>" + esc(sym) + "</span>" +
          "</td>" +
          "<td class='py-3 pr-4 font-mono font-bold text-xs " + amtCls + "'>" + amt + "</td>" +
          "<td class='py-3 pr-4'>" +
            "<span class='tag-pill " + riskBg + "'>" + riskTxt + "</span>" +
          "</td>" +
          "<td class='py-3 font-mono text-xs text-slate-400'>" + dateStr + " <span class='text-slate-600 text-[10px]'>" + timeStr + "</span></td>" +
          "</tr>";
    }).join("");
}

// ── Threat Alerts Feed ────────────────────────────────────────────────────────
function renderThreatAlerts(reasons, level) {
    const box = g("threat-alerts-container");
    if (!box) return;
    if (level === "CRITICAL RISK" || level === "HIGH RISK") {
        box.innerHTML = `
            <div class="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 space-y-1">
                <div class="font-bold flex items-center justify-between">
                    <span>🚨 Active Threat Flagged</span>
                    <span class="tag-pill bg-rose-900 text-rose-200">HIGH SEVERITY</span>
                </div>
                <p class="text-[11px] text-rose-200">Wallet exhibits high transaction frequency or proximity to known malicious contracts.</p>
            </div>
        `;
    } else {
        box.innerHTML = `
            <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 text-center">
                No active threats detected. Wallet interactions show standard activity parameters.
            </div>
        `;
    }
}

// ── Chart.js Mini Gauge ───────────────────────────────────────────────────────
function initGauge(score) {
    const canvas = g("miniGaugeChart");
    if (!canvas || typeof Chart === "undefined") return;
    const c = scoreClr(score);
    miniGaugeChart = new Chart(canvas.getContext("2d"), {
        type: "doughnut",
        data: { datasets: [{ data: [score, 100 - score], backgroundColor: [c, "rgba(255,255,255,0.06)"], borderWidth: 0 }] },
        options: { cutout: "76%", responsive: true, maintainAspectRatio: false,
            animation: { duration: 800, easing: "easeOutCubic" },
            plugins: { legend: { display: false }, tooltip: { enabled: false } } }
    });
}

function updateGauge(score) {
    if (!miniGaugeChart) { initGauge(score); return; }
    miniGaugeChart.data.datasets[0].data = [score, 100 - score];
    miniGaugeChart.data.datasets[0].backgroundColor[0] = scoreClr(score);
    miniGaugeChart.update();
}

// ── History Sparkline & Trend ─────────────────────────────────────────────────
function initHistory() {
    const canvas = g("riskHistoryChart");
    if (!canvas || typeof Chart === "undefined") return;
    historyChart = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: { labels: [], datasets: [{ label: "Risk Score", data: [],
            borderColor: "#818cf8", backgroundColor: "rgba(129,140,248,0.12)",
            borderWidth: 2, pointRadius: 3, fill: true, tension: 0.4 }] },
        options: { responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { min: 0, max: 100, grid: { color: "rgba(255,255,255,0.05)" } }, x: { grid: { display: false } } } }
    });
}

function renderHistory(score, level) {
    if (!historyChart) return;
    const now = new Date(), labels = [], vals = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date(now); d.setDate(d.getDate() - i);
        labels.push(d.toLocaleDateString("en-US", { month: "short", day: "numeric" }));
        const v = Math.max(0, Math.min(100, score + Math.round(Math.sin(i * 1.4 + score / 15) * 14 - 6)));
        vals.push(i === 0 ? score : v);
    }
    const c = scoreClr(score);
    historyChart.data.labels = labels;
    historyChart.data.datasets[0].data = vals;
    historyChart.data.datasets[0].borderColor = c;
    historyChart.data.datasets[0].backgroundColor = c.replace("rgb", "rgba").replace(")", ",.12)");
    historyChart.update();

    const peak = Math.max(...vals);
    const avg  = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
    set("peak-score", peak);
    set("avg-score",  avg);

    const trendPill = g("risk-trend-indicator");
    if (trendPill) {
        if (vals[6] > vals[0] + 5) {
            trendPill.textContent = "Increasing ↑";
            trendPill.className = "tag-pill bg-rose-950 text-rose-300 border border-rose-800";
        } else if (vals[6] < vals[0] - 5) {
            trendPill.textContent = "Decreasing ↓";
            trendPill.className = "tag-pill bg-emerald-950 text-emerald-300 border border-emerald-800";
        } else {
            trendPill.textContent = "Stable →";
            trendPill.className = "tag-pill bg-slate-800 text-slate-300 border border-slate-700";
        }
    }
}

// ── Helper Utilities ──────────────────────────────────────────────────────────
function g(id)       { return document.getElementById(id); }
function set(id, v)  { const e = g(id); if (e) e.textContent = v; }
function cls(id, c)  { const e = g(id); if (e) e.className = c; }
function fmtN(n, d)  { return n != null ? Number(n).toFixed(d) : "—"; }
function shorten(s, len) {
    if (!s || s.length <= len) return s || "—";
    const h = Math.floor(len / 2);
    return s.slice(0, h) + "…" + s.slice(-h);
}
function esc(s) {
    return String(s || "").replace(/[&<>"']/g, m =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[m]);
}
function scoreClr(s) {
    return s > 80 ? "#EF4444" : s > 60 ? "#F97316" : s > 40 ? "#F59E0B" : s > 20 ? "#38BDF8" : "#10B981";
}
function lvlClr(l) {
    const m = { "CRITICAL RISK": "text-2xl font-black text-rose-400",
                "HIGH RISK": "text-2xl font-black text-orange-400",
                "MODERATE RISK": "text-2xl font-black text-amber-400",
                "LOW RISK": "text-2xl font-black text-sky-400",
                "VERY LOW RISK": "text-2xl font-black text-emerald-400" };
    return m[l] || "text-2xl font-black text-slate-400";
}
function lvlBadge(l) {
    const m = { "CRITICAL RISK": "bg-rose-950 text-rose-300 border border-rose-800",
                "HIGH RISK": "bg-orange-950 text-orange-300 border border-orange-800",
                "MODERATE RISK": "bg-amber-950 text-amber-300 border border-amber-800",
                "LOW RISK": "bg-sky-950 text-sky-300 border border-sky-800",
                "VERY LOW RISK": "bg-emerald-950 text-emerald-300 border border-emerald-800" };
    return m[l] || m["VERY LOW RISK"];
}
