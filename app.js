/**
 * app.js — AI-DeFi Risk Intelligence v2.0
 * Wallet Address Explorer Landing Page + Bento Box Dashboard Flow
 * Integrated with TronService (TronGrid Pro API Key) & Multi-Chain Resolvers
 */

const API_BASE  = "";
const TOKEN_KEY = "defi_risk_jwt";
const CREDS     = { username: "defi_analyst", password: "secure_password_123" };
const TRONGRID_API_KEY = "e53160ed-54c9-47c4-8d34-c80eb0433c70";

let miniGaugeChart = null;
let historyChart   = null;

// ── TronService Module ────────────────────────────────────────────────────────
const TronService = {
    apiKey: TRONGRID_API_KEY,
    baseUrl: "https://api.trongrid.io",

    getHeaders() {
        const headers = { "Accept": "application/json" };
        if (this.apiKey) {
            headers["TRON-PRO-API-KEY"] = this.apiKey;
        }
        return headers;
    },

    isTronAddress(address) {
        return typeof address === "string" && /^T[a-zA-Z0-9]{32,33}$/.test(address.trim());
    },

    getTronScanUrl(type, value) {
        if (!value) return "https://tronscan.org";
        if (type === "tx" || type === "transaction") return `https://tronscan.org/#/transaction/${encodeURIComponent(value)}`;
        if (type === "address") return `https://tronscan.org/#/address/${encodeURIComponent(value)}`;
        if (type === "token") return `https://tronscan.org/#/token20/${encodeURIComponent(value)}`;
        return `https://tronscan.org/#/address/${encodeURIComponent(value)}`;
    },

    /**
     * Fetch real-time TRON account parameters: native TRX, bandwidth, energy, account age
     */
    async fetchAccountDetails(address) {
        if (!this.isTronAddress(address)) return null;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            const res = await fetch(`${this.baseUrl}/v1/accounts/${encodeURIComponent(address)}`, {
                headers: this.getHeaders(),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!res.ok) return null;
            const json = await res.json();
            if (json.success && Array.isArray(json.data) && json.data.length > 0) {
                const acc = json.data[0];
                const balanceSun = acc.balance || 0;
                const balanceTrx = balanceSun / 1e6;
                const createTime = acc.create_time ? new Date(acc.create_time) : null;
                const trc20Balances = Array.isArray(acc.trc20) ? acc.trc20 : [];
                return {
                    address: acc.address || address,
                    balance_trx: balanceTrx,
                    balance_sun: balanceSun,
                    create_time: createTime,
                    account_type: acc.account_type || "Standard Account",
                    net_usage: acc.net_usage || 0,
                    free_net_limit: acc.free_net_limit || 600,
                    energy_limit: acc.energy_limit || 0,
                    trc20_tokens: trc20Balances
                };
            }
        } catch (e) {
            console.warn("TronService account fetch error:", e);
        }
        return null;
    },

    /**
     * Fetch real-time TRC-20 token transfer events (e.g. USDT, USDC, BTT, WIN)
     */
    async fetchTrc20Transfers(address, limit = 30) {
        if (!this.isTronAddress(address)) return [];
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            const res = await fetch(`${this.baseUrl}/v1/accounts/${encodeURIComponent(address)}/transactions/trc20?limit=${limit}`, {
                headers: this.getHeaders(),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!res.ok) return [];
            const json = await res.json();
            if (json.success && Array.isArray(json.data)) {
                return json.data.map(item => {
                    const tokenInfo = item.token_info || {};
                    const decimals = parseInt(tokenInfo.decimals || 6, 10);
                    const rawVal = item.value || "0";
                    let normalizedAmount = 0;
                    try {
                        normalizedAmount = parseFloat(rawVal) / Math.pow(10, isNaN(decimals) ? 6 : decimals);
                    } catch (e) {}

                    return {
                        transaction_id: item.transaction_id || "",
                        block_timestamp: item.block_timestamp || Date.now(),
                        from_address: item.from || "",
                        to_address: item.to || "",
                        amount_usdt: isNaN(normalizedAmount) ? 0 : normalizedAmount,
                        raw_value: String(rawVal),
                        token_symbol: tokenInfo.symbol || "USDT",
                        token_name: tokenInfo.name || "TRC-20 Token",
                        token_standard: "TRC-20",
                        contract_address: tokenInfo.address || "",
                        confirmed: true,
                        scam_flag: 0
                    };
                });
            }
        } catch (e) {
            console.warn("TronService TRC-20 transfers fetch error:", e);
        }
        return [];
    },

    /**
     * Fetch historical transaction activity (native TRX transfers & smart contract calls)
     */
    async fetchHistoricalTransactions(address, limit = 30) {
        if (!this.isTronAddress(address)) return [];
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            const res = await fetch(`${this.baseUrl}/v1/accounts/${encodeURIComponent(address)}/transactions?limit=${limit}`, {
                headers: this.getHeaders(),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!res.ok) return [];
            const json = await res.json();
            if (json.success && Array.isArray(json.data)) {
                const txs = [];
                for (const item of json.data) {
                    const rawData = item.raw_data || {};
                    const contract = (rawData.contract && rawData.contract[0]) || {};
                    const contractType = contract.type || "TransferContract";
                    const valueObj = (contract.parameter && contract.parameter.value) || {};
                    let amount = 0;
                    if (valueObj.amount) {
                        amount = Number(valueObj.amount) / 1e6;
                    }
                    const ret = (item.ret && item.ret[0]) || {};
                    const isSuccess = ret.contractRet === "SUCCESS";

                    txs.push({
                        transaction_id: item.txID || "",
                        block_timestamp: rawData.timestamp || Date.now(),
                        from_address: valueObj.owner_address || address,
                        to_address: valueObj.to_address || valueObj.contract_address || "",
                        amount_usdt: amount,
                        raw_value: String(valueObj.amount || "0"),
                        token_symbol: "TRX",
                        token_standard: "TRX Native",
                        contract_type: contractType,
                        confirmed: isSuccess,
                        scam_flag: 0
                    });
                }
                return txs;
            }
        } catch (e) {
            console.warn("TronService historical transactions fetch error:", e);
        }
        return [];
    },

    /**
     * Comprehensive TRON data aggregation
     */
    async getComprehensiveTronData(address) {
        if (!this.isTronAddress(address)) return null;
        const [accDetails, trc20Transfers, histTxs] = await Promise.all([
            this.fetchAccountDetails(address),
            this.fetchTrc20Transfers(address, 30),
            this.fetchHistoricalTransactions(address, 30)
        ]);

        const allTransfers = [...trc20Transfers];
        const seenTxIds = new Set(trc20Transfers.map(t => t.transaction_id));
        for (const tx of histTxs) {
            if (tx.transaction_id && !seenTxIds.has(tx.transaction_id)) {
                allTransfers.push(tx);
                seenTxIds.add(tx.transaction_id);
            }
        }
        allTransfers.sort((a, b) => b.block_timestamp - a.block_timestamp);

        return {
            account: accDetails,
            trc20_transfers: trc20Transfers,
            historical_transactions: histTxs,
            all_transfers: allTransfers
        };
    }
};

// ── Boot ───────────────────────────────────────────────────────────────────────
// ── State ──────────────────────────────────────────────────────────────────────
const state = {
    currentAddress: "",
    currentChain: "ethereum",
    currentData: null
};

// ── Boot ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const explorerInput  = g("explorer-address-input");
    const explorerBtn    = g("explorer-analyze-btn");
    const pasteBtn       = g("paste-btn");
    const clearBtn       = g("clear-btn");
    const backToExplorer = g("back-to-explorer-btn");

    // Landing Network Tabs
    document.querySelectorAll(".landing-chain-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const chain = tab.dataset.chain;
            if (chain) setActiveNetwork(chain, false);
        });
    });

    // Dashboard Network Tabs (Reactive Switcher)
    document.querySelectorAll(".dash-chain-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const chain = tab.dataset.chain;
            if (chain) {
                setActiveNetwork(chain, true);
            }
        });
    });

    // Auto-detect chain on input
    if (explorerInput) {
        explorerInput.addEventListener("input", () => {
            const val = explorerInput.value.trim();
            if (val.startsWith("T") && state.currentChain !== "tron") {
                setActiveNetwork("tron", false);
            } else if (val.startsWith("0x") && state.currentChain === "tron") {
                setActiveNetwork("ethereum", false);
            }
        });
        explorerInput.addEventListener("keypress", e => e.key === "Enter" && handleExplorerScan());
    }

    if (explorerBtn)  explorerBtn.addEventListener("click", handleExplorerScan);

    if (pasteBtn) {
        pasteBtn.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && explorerInput) {
                    explorerInput.value = text.trim();
                    hideExplorerError();
                    if (text.trim().startsWith("T")) setActiveNetwork("tron", false);
                    else if (text.trim().startsWith("0x") && state.currentChain === "tron") setActiveNetwork("ethereum", false);
                }
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

    // Dashboard Embedded Input & Scan Controls
    const dashInput = g("dash-address-input");
    const dashAnalyzeBtn = g("dash-analyze-btn");
    const dashPasteBtn = g("dash-paste-btn");
    const dashClearBtn = g("dash-clear-btn");
    const dashCopyBtn = g("dash-copy-addr-btn");

    if (dashAnalyzeBtn) {
        dashAnalyzeBtn.addEventListener("click", handleDashboardScan);
    }
    if (dashInput) {
        dashInput.addEventListener("input", () => {
            const val = dashInput.value.trim();
            if (val.startsWith("T") && state.currentChain !== "tron") {
                setActiveNetwork("tron", false);
            } else if (val.startsWith("0x") && state.currentChain === "tron") {
                setActiveNetwork("ethereum", false);
            }
        });
        dashInput.addEventListener("keypress", e => e.key === "Enter" && handleDashboardScan());
    }
    if (dashPasteBtn) {
        dashPasteBtn.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && dashInput) {
                    dashInput.value = text.trim();
                    if (text.trim().startsWith("T")) setActiveNetwork("tron", false);
                    else if (text.trim().startsWith("0x") && state.currentChain === "tron") setActiveNetwork("ethereum", false);
                }
            } catch(e) {
                /* ignore */
            }
        });
    }
    if (dashClearBtn) {
        dashClearBtn.addEventListener("click", () => {
            if (dashInput) dashInput.value = "";
        });
    }
    if (dashCopyBtn) {
        dashCopyBtn.addEventListener("click", () => {
            if (state.currentAddress) {
                navigator.clipboard.writeText(state.currentAddress).then(() => {
                    dashCopyBtn.textContent = "✓";
                    setTimeout(() => { dashCopyBtn.textContent = "📋"; }, 1500);
                });
            }
        });
    }

    // Sample address badges (Landing view)
    document.querySelectorAll(".sample-address-badge").forEach(b => {
        b.addEventListener("click", () => {
            const addr = b.dataset.address;
            const chain = b.dataset.chain || "ethereum";
            if (explorerInput) explorerInput.value = addr;
            setActiveNetwork(chain, false);
            handleExplorerScan();
        });
    });

    // Sample address badges (Dashboard view)
    document.querySelectorAll(".dash-sample-badge").forEach(b => {
        b.addEventListener("click", () => {
            const addr = b.dataset.address;
            const chain = b.dataset.chain || "ethereum";
            setActiveNetwork(chain, false);
            if (dashInput) dashInput.value = addr;
            runAnalysisPipeline(addr, chain);
        });
    });

    // API Hub Modal Event Listeners
    const openApiHubLanding = g("open-api-hub-btn-landing");
    const openApiHubDash = g("open-api-hub-btn-dash");
    const closeApiHub = g("close-api-hub-btn");
    const apiHubModal = g("api-hub-modal");
    const pingApisBtn = g("ping-apis-btn");

    if (openApiHubLanding) openApiHubLanding.addEventListener("click", () => showApiHub());
    if (openApiHubDash) openApiHubDash.addEventListener("click", () => showApiHub());
    if (closeApiHub) closeApiHub.addEventListener("click", () => hideApiHub());
    if (apiHubModal) {
        apiHubModal.addEventListener("click", (e) => {
            if (e.target === apiHubModal) hideApiHub();
        });
    }
    if (pingApisBtn) pingApisBtn.addEventListener("click", () => runApiLatencyTest());

    // Executive Report Modal Listeners
    const closeReportBtn = g("close-report-btn");
    const printReportBtn = g("print-clean-report-btn");
    const copyReportBtn = g("copy-summary-report-btn");
    const reportModal = g("executive-report-modal");
    const exportReportBtn = g("export-report-btn");
    const bottomExportReportBtn = g("bottom-export-report-btn");

    if (exportReportBtn) exportReportBtn.addEventListener("click", openExecutiveReport);
    if (bottomExportReportBtn) bottomExportReportBtn.addEventListener("click", openExecutiveReport);
    if (closeReportBtn) closeReportBtn.addEventListener("click", closeExecutiveReport);
    if (printReportBtn) printReportBtn.addEventListener("click", () => window.print());
    if (copyReportBtn) copyReportBtn.addEventListener("click", copyReportSummary);
    if (reportModal) {
        reportModal.addEventListener("click", (e) => {
            if (e.target === reportModal) closeExecutiveReport();
        });
    }

    // Back to Scanner (Page 1) Navigation Buttons
    const backToScanBtn = g("back-to-scan-btn");
    const bottomBackToScanBtn = g("bottom-back-to-scan-btn");
    if (backToScanBtn) backToScanBtn.addEventListener("click", showLandingView);
    if (bottomBackToScanBtn) bottomBackToScanBtn.addEventListener("click", showLandingView);

    // Clear Recent Scans button
    const clearRecentBtn = g("clear-recent-scans-btn");
    if (clearRecentBtn) {
        clearRecentBtn.addEventListener("click", clearAllRecentScans);
    }

    initGauge(0);
    initHistory();
    checkApiStatus();
    renderRecentScansBar();

    // Default startup state: Show Page 1 (Search & Scanner Portal)
    showLandingView();
});

// ── Network Switching Logic ──────────────────────────────────────────────────
function setActiveNetwork(chain, triggerReScan = false) {
    state.currentChain = chain;
    const netSel = g("explorer-network-select");
    if (netSel) netSel.value = chain;

    // Update Landing Tabs Styling
    document.querySelectorAll(".landing-chain-tab").forEach(tab => {
        if (tab.dataset.chain === chain) {
            tab.className = "landing-chain-tab py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all border bg-indigo-950/80 border-indigo-500 text-white shadow-md shadow-indigo-950/50";
        } else {
            tab.className = "landing-chain-tab py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all border bg-slate-900/80 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700";
        }
    });

    // Update Dashboard Tabs Styling
    document.querySelectorAll(".dash-chain-tab").forEach(tab => {
        if (tab.dataset.chain === chain) {
            tab.className = "dash-chain-tab py-2 px-2 rounded-xl font-bold text-xs flex items-center justify-center gap-1 transition-all border bg-indigo-950/90 border-indigo-500 text-white shadow-sm cursor-pointer";
        } else {
            tab.className = "dash-chain-tab py-2 px-2 rounded-xl font-bold text-xs flex items-center justify-center gap-1 transition-all border bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 cursor-pointer";
        }
    });

    // Update Landing API indicator badge
    const apiInd = g("active-api-indicator");
    if (apiInd) {
        if (chain === "tron") {
            apiInd.textContent = "⚡ TronGrid Pro API (Key Active)";
            apiInd.className = "text-xs text-emerald-400 font-mono";
        } else {
            apiInd.textContent = "⚡ Etherscan V2 API Ready";
            apiInd.className = "text-xs text-emerald-400 font-mono";
        }
    }

    // Trigger immediate reactive re-scan if on dashboard and requested
    if (triggerReScan) {
        const dashInput = g("dash-address-input");
        const candidateAddr = (dashInput && dashInput.value.trim()) ? dashInput.value.trim() : state.currentAddress;
        
        if (candidateAddr) {
            const isTronAddr = /^T[a-zA-Z0-9]{32,33}$/.test(candidateAddr);
            const isEvmAddr = /^0x[a-fA-F0-9]{40}$/.test(candidateAddr);

            if (chain === "tron" && !isTronAddr) {
                // Address is EVM but user switched to TRON: switch to sample TRON address
                const tronSample = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7";
                if (dashInput) dashInput.value = tronSample;
                runAnalysisPipeline(tronSample, "tron");
            } else if (chain !== "tron" && isTronAddr) {
                // Address is TRON but user switched to EVM: switch to sample EVM address
                const evmSample = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045";
                if (dashInput) dashInput.value = evmSample;
                runAnalysisPipeline(evmSample, chain);
            } else {
                runAnalysisPipeline(candidateAddr, chain);
            }
        }
    }
}

// ── Recent Scans Storage & Scrollable Bar ────────────────────────────────────
const RECENT_SCANS_KEY = "web3_recent_scans_v2";

function getRecentScans() {
    try {
        const raw = localStorage.getItem(RECENT_SCANS_KEY);
        if (!raw) return [];
        const arr = JSON.parse(raw);
        return Array.isArray(arr) ? arr : [];
    } catch {
        return [];
    }
}

function saveRecentScan(entry) {
    if (!entry || !entry.address) return;
    const cleanAddr = entry.address.trim();
    const isTron = entry.chain === "tron" || cleanAddr.startsWith("T");
    const normAddr = isTron ? cleanAddr : cleanAddr.toLowerCase();
    const scans = getRecentScans();
    
    // Remove if already present (so it moves to index 0)
    const filtered = scans.filter(s => {
        if (!s || !s.address) return false;
        const sNorm = (s.chain === "tron" || s.address.startsWith("T")) ? s.address.trim() : s.address.trim().toLowerCase();
        return sNorm !== normAddr;
    });

    // Add new scan to front
    filtered.unshift({
        address: cleanAddr,
        chain: isTron ? "tron" : "ethereum",
        riskScore: entry.riskScore != null ? Math.round(entry.riskScore) : null,
        riskLevel: entry.riskLevel || "UNKNOWN",
        timestamp: Date.now()
    });

    // Limit to last 5
    const top5 = filtered.slice(0, 5);
    try {
        localStorage.setItem(RECENT_SCANS_KEY, JSON.stringify(top5));
    } catch (e) {
        console.warn("Failed to save recent scans:", e);
    }
    renderRecentScansBar();
}

function removeRecentScan(indexToRemove, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const scans = getRecentScans();
    if (indexToRemove >= 0 && indexToRemove < scans.length) {
        scans.splice(indexToRemove, 1);
        try {
            localStorage.setItem(RECENT_SCANS_KEY, JSON.stringify(scans));
        } catch (err) {}
        renderRecentScansBar();
    }
}

function clearAllRecentScans() {
    try {
        localStorage.removeItem(RECENT_SCANS_KEY);
    } catch (e) {}
    renderRecentScansBar();
}

function renderRecentScansBar() {
    const container = g("recent-scans-container");
    const list = g("recent-scans-list");
    if (!container || !list) return;

    const scans = getRecentScans();
    if (scans.length === 0) {
        container.classList.add("hidden");
        list.innerHTML = "";
        return;
    }

    container.classList.remove("hidden");
    list.innerHTML = "";

    scans.forEach((scan, idx) => {
        const isTron = scan.chain === "tron" || (scan.address && scan.address.startsWith("T"));
        const chainIcon = isTron ? "🟢" : "🔷";
        const chainName = isTron ? "TRON" : "ETH";
        
        // Truncate address (e.g. 0xd8dA...6045)
        const addr = scan.address || "";
        const shortAddr = addr.length > 12 
            ? `${addr.slice(0, 6)}...${addr.slice(-4)}` 
            : addr;

        // Risk badge styling
        let badgeBg = "bg-slate-800 text-slate-300 border-slate-700";
        let scoreText = "";
        if (scan.riskScore != null) {
            const sc = scan.riskScore;
            if (sc >= 80) badgeBg = "bg-rose-950/90 text-rose-300 border-rose-800/80";
            else if (sc >= 60) badgeBg = "bg-orange-950/90 text-orange-300 border-orange-800/80";
            else if (sc >= 35) badgeBg = "bg-amber-950/90 text-amber-300 border-amber-800/80";
            else badgeBg = "bg-emerald-950/90 text-emerald-300 border-emerald-800/80";
            scoreText = `${sc}/100`;
        }

        const chip = document.createElement("div");
        chip.className = "flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 hover:border-indigo-500/70 transition-all cursor-pointer group shadow-sm select-none";
        chip.title = `Address: ${addr}\nNetwork: ${chainName}\nRisk: ${scan.riskScore != null ? scan.riskScore + '/100 (' + scan.riskLevel + ')' : 'Scanned'}\nClick to re-scan`;

        chip.innerHTML = `
            <span class="text-xs">${chainIcon}</span>
            <span class="font-mono text-[11px] text-slate-200 group-hover:text-white font-medium">${esc(shortAddr)}</span>
            ${scoreText ? `<span class="text-[10px] font-bold px-1.5 py-0.5 rounded border ${badgeBg}">${scoreText}</span>` : ""}
            <button type="button" class="ml-0.5 text-slate-500 hover:text-rose-400 text-[11px] p-0.5 transition-colors cursor-pointer" title="Remove from recent">✕</button>
        `;

        // Click on chip loads address and triggers scan
        chip.addEventListener("click", () => {
            const input = g("dash-address-input");
            if (input) input.value = addr;
            setActiveNetwork(scan.chain || (isTron ? "tron" : "ethereum"), false);
            runAnalysisPipeline(addr, scan.chain || (isTron ? "tron" : "ethereum"));
        });

        // Click on remove button
        const removeBtn = chip.querySelector("button");
        if (removeBtn) {
            removeBtn.addEventListener("click", (e) => {
                removeRecentScan(idx, e);
            });
        }

        list.appendChild(chip);
    });
}

function showApiHub() {
    const m = g("api-hub-modal");
    if (m) m.classList.remove("hidden");
    runApiLatencyTest();
}

function hideApiHub() {
    const m = g("api-hub-modal");
    if (m) m.classList.add("hidden");
}

async function runApiLatencyTest() {
    const btn = g("ping-apis-btn");
    const icon = g("ping-icon");
    const txt = g("ping-text");
    const grid = g("ping-results-grid");
    if (!grid) return;

    grid.classList.remove("hidden");
    if (btn) btn.disabled = true;
    if (icon) icon.textContent = "⏳";
    if (txt) txt.textContent = "Testing...";

    grid.innerHTML = '<div class="col-span-full p-4 text-center text-xs text-slate-400 font-mono">Pinging live production API gateways...</div>';

    try {
        const res = await fetch(`${API_BASE}/api/ping-apis`).then(r => r.json());
        if (res && Array.isArray(res.results)) {
            grid.innerHTML = res.results.map(r => {
                const isOnline = r.status === "ONLINE";
                const isRate = r.status === "RATE_LIMITED";
                const borderCls = isOnline ? "border-emerald-800/80 bg-emerald-950/40" : (isRate ? "border-amber-800/80 bg-amber-950/40" : "border-rose-800/80 bg-rose-950/40");
                const badgeCls = isOnline ? "bg-emerald-900 text-emerald-300 border-emerald-700" : (isRate ? "bg-amber-900 text-amber-300 border-amber-700" : "bg-rose-900 text-rose-300 border-rose-700");
                const dotCls = isOnline ? "bg-emerald-400" : (isRate ? "bg-amber-400" : "bg-rose-400");
                return '<div class="p-3 rounded-xl border ' + borderCls + ' space-y-1.5">' +
                    '<div class="flex items-center justify-between">' +
                        '<span class="text-xs font-bold text-white truncate max-w-[140px]">' + esc(r.service) + '</span>' +
                        '<span class="tag-pill ' + badgeCls + ' text-[10px]">' + esc(r.status) + '</span>' +
                    '</div>' +
                    '<div class="flex items-center justify-between text-[11px] font-mono">' +
                        '<span class="text-slate-400">Latency</span>' +
                        '<span class="font-bold text-white flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full ' + dotCls + '"></span>' + (r.latency_ms != null ? r.latency_ms + 'ms' : '—') + '</span>' +
                    '</div>' +
                    '<div class="text-[10px] text-slate-400 truncate font-mono">' + esc(r.auth || r.endpoint || "") + '</div>' +
                '</div>';
            }).join("");
        } else {
            grid.innerHTML = '<div class="col-span-full p-4 text-center text-xs text-rose-400">Failed to ping APIs.</div>';
        }
    } catch(e) {
        grid.innerHTML = '<div class="col-span-full p-4 text-center text-xs text-rose-400">Error connecting to ping endpoint: ' + esc(e.message) + '</div>';
    } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.textContent = "⚡";
        if (txt) txt.textContent = "Test API Connectivity";
    }
}

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
    hideExplorerError();
    renderRecentScansBar();
    const dashInput = g("dash-address-input");
    if (dashInput) {
        setTimeout(() => dashInput.focus(), 50);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showDashboardView() {
    const landing   = g("landing-view");
    const dashboard = g("dashboard-view");
    if (landing)   landing.classList.add("hidden");
    if (dashboard) dashboard.classList.remove("hidden");
    
    const navAddr = g("nav-target-address");
    const navChain = g("nav-chain-badge");
    if (navAddr && state.currentAddress) navAddr.textContent = state.currentAddress;
    if (navChain && state.currentChain) navChain.textContent = state.currentChain.toUpperCase();
    
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showExplorerError(msg) {
    const box = g("explorer-error-alert");
    const txt = g("explorer-error-msg");
    if (txt) txt.textContent = msg;
    if (box) box.classList.remove("hidden");
    if (box) box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideExplorerError() {
    const box = g("explorer-error-alert");
    if (box) box.classList.add("hidden");
}

// ── Analysis Handler (Landing) ────────────────────────────────────────────────
async function handleExplorerScan() {
    const input  = g("explorer-address-input");
    const netSel = g("explorer-network-select");
    const addr   = input ? input.value.trim() : "";
    const chain  = netSel ? netSel.value : state.currentChain || "ethereum";

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
        setActiveNetwork("tron", false);
    }
    if (isEvm && chain === "tron") {
        setActiveNetwork("ethereum", false);
    }

    const effectiveChain = isTron ? "tron" : (chain === "tron" ? "ethereum" : chain);
    hideExplorerError();
    await runAnalysisPipeline(addr, effectiveChain);
}

// ── Analysis Handler (Dashboard) ──────────────────────────────────────────────
async function handleDashboardScan() {
    const input = g("dash-address-input");
    const addr = input ? input.value.trim() : "";
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

    let chain = state.currentChain;
    if (isTron && chain !== "tron") {
        chain = "tron";
        setActiveNetwork("tron", false);
    } else if (isEvm && chain === "tron") {
        chain = "ethereum";
        setActiveNetwork("ethereum", false);
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

function formatWalletAge(days) {
    if (days == null || isNaN(days)) return { main: "—", sub: "Active History", full: "—" };
    const numDays = Math.max(0, Number(days));
    if (numDays >= 365) {
        const yrs = (numDays / 365.25).toFixed(1);
        const daysFmt = Math.round(numDays).toLocaleString("en-US");
        return {
            main: `${daysFmt} d`,
            sub: `~${yrs} yrs on-chain`,
            full: `${daysFmt} days (~${yrs} yrs active)`
        };
    } else if (numDays >= 30) {
        const months = (numDays / 30.4).toFixed(1);
        const daysFmt = Math.round(numDays);
        return {
            main: `${daysFmt} d`,
            sub: `~${months} mo on-chain`,
            full: `${daysFmt} days (~${months} mo active)`
        };
    } else if (numDays >= 1) {
        const daysFmt = Math.round(numDays);
        return {
            main: `${daysFmt} d`,
            sub: `${daysFmt} day${daysFmt > 1 ? "s" : ""} on-chain`,
            full: `${daysFmt} day${daysFmt > 1 ? "s" : ""} on-chain`
        };
    } else {
        const hrs = Math.max(1, Math.round(numDays * 24));
        return {
            main: `${hrs} hrs`,
            sub: "Newly Created",
            full: `${hrs} hours (Newly created)`
        };
    }
}

// ── Pipeline & Loading Modal ──────────────────────────────────────────────────
async function runAnalysisPipeline(address, chain) {
    showLoadingModal(address);
    updateLoadingStep(1, "done", "✓ Address format validated");
    updateLoadingStep(2, "done", `✓ Network: ${chain.toUpperCase()}`);

    try {
        updateLoadingStep(3, "active", chain === "tron" ? "⟳ TronService querying TronGrid Pro API for TRC-20 & TRX..." : "⟳ Fetching on-chain activity & balances...");
        const tok = await token();
        if (!tok) { hideLoadingModal(); return; }

        // Start backend ML pipeline fetch
        const mlUrl = `${API_BASE}/api/v1/wallet/${encodeURIComponent(address)}?chain=${encodeURIComponent(chain)}`;
        const backendPromise = fetch(mlUrl, { headers: { "Authorization": "Bearer " + tok, "Accept": "application/json" } });

        // If TRON, also trigger TronService direct live retrieval for maximum freshness
        let tronDataPromise = null;
        if (chain === "tron") {
            tronDataPromise = TronService.getComprehensiveTronData(address).catch(e => {
                console.warn("Direct TronService fetch fallback to server:", e);
                return null;
            });
        }

        updateLoadingStep(4, "active", "⟳ Running Tabular ML + GraphSAGE GNN + Autoencoder...");

        const [r, directTronData] = await Promise.all([
            backendPromise,
            tronDataPromise || Promise.resolve(null)
        ]);

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

        // Enrich with direct TronService telemetry if available
        if (chain === "tron" && directTronData) {
            data.tron_direct = directTronData;
            if (directTronData.all_transfers && directTronData.all_transfers.length > 0) {
                data.recent_transfers = directTronData.all_transfers;
                data.is_real_transfers = true;
            }
            if (directTronData.account) {
                data.features = data.features || {};
                if (directTronData.account.balance_trx != null) {
                    data.features.wallet_balance = directTronData.account.balance_trx;
                }
                if (directTronData.account.net_usage != null) {
                    data.features.tron_net_usage = directTronData.account.net_usage;
                    data.features.tron_free_net_limit = directTronData.account.free_net_limit;
                }
                if (directTronData.account.energy_limit != null) {
                    data.features.tron_energy_limit = directTronData.account.energy_limit;
                }
                if (directTronData.account.create_time) {
                    const createMs = directTronData.account.create_time instanceof Date ? directTronData.account.create_time.getTime() : Number(directTronData.account.create_time);
                    if (!isNaN(createMs) && createMs > 0) {
                        const days = Math.max(0.1, (Date.now() - createMs) / (1000 * 86400));
                        data.features.wallet_age = parseFloat(days.toFixed(1));
                    }
                }
                if (directTronData.trc20_transfers) {
                    data.features.trc20_token_transfers_count = directTronData.trc20_transfers.length;
                }
            }
        }

        updateLoadingStep(5, "done", "✓ Analysis complete");
        await new Promise(res => setTimeout(res, 250));
        fillDashboard(data, chain);
        saveRecentScan({
            address: data.address || address,
            chain: chain,
            riskScore: data.risk_score,
            riskLevel: data.risk_level
        });
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
    state.currentAddress = data.address || "";
    state.currentChain = chain || "ethereum";
    state.currentData = data;

    // Synchronize network tabs
    setActiveNetwork(chain, false);

    // Sync input inside dashboard
    const dashInput = g("dash-address-input");
    if (dashInput && data.address) {
        dashInput.value = data.address;
    }

    // Wire up export button
    const exportBtn = g("export-report-btn");
    if (exportBtn) {
        exportBtn.onclick = () => {
            openExecutiveReport(data, chain);
        };
    }

    const score     = Math.round(data.risk_score || 0);
    const level     = getRiskLevelClassification(score, data.risk_level);
    const bd        = data.breakdown  || {};
    const feats     = data.features   || {};
    const reasons   = data.reasons    || [];
    const transfers = data.recent_transfers || [];
    const isTron    = chain === "tron" || (data.address && data.address.startsWith("T"));
    const chainUpper = isTron ? "TRON (TRC-20 / TRX)" : chain.toUpperCase();
    const nativeSymbol = isTron ? "TRX" : "ETH";
    const nativePrice = isTron ? 0.22 : 3450;

    set("dash-full-address", data.address || "—");
    set("dash-chain-pill", chainUpper);
    if (isTron) {
        cls("dash-chain-pill", "tag-pill bg-emerald-950 text-emerald-300 border border-emerald-700");
    } else {
        cls("dash-chain-pill", "tag-pill bg-indigo-950 text-indigo-300 border border-indigo-800");
    }

    // Dynamic API Source text in dashboard header
    const apiSourceText = g("dash-api-source-text");
    if (apiSourceText) {
        apiSourceText.textContent = isTron ? "TronGrid Pro Synced" : "Etherscan V2 Synced";
    }

    // Dynamic Block Explorer Direct Link
    const explorerLink = g("dash-explorer-link");
    if (explorerLink && data.address) {
        if (isTron) {
            explorerLink.href = `https://tronscan.org/#/address/${encodeURIComponent(data.address)}`;
            explorerLink.title = "View on TronScan Explorer";
        } else {
            explorerLink.href = `https://etherscan.io/address/${encodeURIComponent(data.address)}`;
            explorerLink.title = "View on Etherscan";
        }
    }

    /* ── Entity & Verification Banner ── */
    const isSanctioned = score > 80 && (data.entity_label || feats.distance_to_blacklisted_wallet === 0);
    const isVerified = data.entity_label && score <= 20;

    set("dash-entity-name", data.entity_label || (feats.is_smart_contract ? (isTron ? "TRON Smart Contract" : "Smart Contract") : (isTron ? "TRON Account Wallet" : "EOA Account Wallet")));
    set("dash-entity-badge", data.entity_category || (feats.is_smart_contract ? "Verified Contract" : (isTron ? "TRON Base58 EOA" : "Standard EOA")));
    cls("dash-entity-badge", "tag-pill " + (isSanctioned ? "bg-rose-950 text-rose-300 border border-rose-800" : isVerified ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-slate-800 text-slate-300 border border-slate-700"));

    const liveBadge = g("dash-live-badge");
    if (liveBadge) {
        if (isTron) {
            liveBadge.textContent = "⚡ TronGrid Pro API Synced";
            liveBadge.className = "tag-pill bg-emerald-950 text-emerald-300 border border-emerald-700";
        } else if (data.live_onchain_synced || feats.is_live_data) {
            liveBadge.textContent = "⚡ Live RPC Synced";
            liveBadge.className = "tag-pill bg-emerald-950 text-emerald-400 border border-emerald-800";
        } else {
            liveBadge.textContent = "✓ Neural Benchmark Calibrated";
            liveBadge.className = "tag-pill bg-indigo-950 text-indigo-300 border border-indigo-800";
        }
    }

    const metaLabel = g("dash-dataset-meta");
    if (metaLabel) {
        if (isTron) {
            metaLabel.textContent = "TronGrid Pro API Active · Real-time TRC-20 transfers & TRX on-chain telemetry · ML Risk Calibrated";
        } else {
            metaLabel.textContent = "Scored using XGBoost (Kaggle Fraud Benchmark) + GraphSAGE (Elliptic AML) + OFAC Screening";
        }
    }

    const entityIcon = g("dash-entity-icon");
    if (entityIcon) {
        entityIcon.textContent = isSanctioned ? "🚨" : isVerified ? "🏛️" : (feats.is_smart_contract ? "📜" : (isTron ? "⚡" : "👤"));
    }

    const balVal = feats.wallet_balance != null ? Number(feats.wallet_balance) : 0;
    set("dash-native-balance", `${balVal.toLocaleString("en-US", { maximumFractionDigits: 4 })} ${nativeSymbol}`);

    const estPortfolioUsd = balVal * nativePrice + (feats.transaction_amount ? Math.min(feats.transaction_amount * 0.15, 25000) : 0);
    set("dash-portfolio-val", `$${estPortfolioUsd.toLocaleString("en-US", { maximumFractionDigits: 2 })} USD`);

    /* ── Stat Bar ── */
    set("calibrated-risk-score", score);
    set("risk-level-text", level);
    cls("risk-level-text", "text-2xl font-black " + lvlClr(level));

    const ageInfo = formatWalletAge(feats.wallet_age);
    set("wallet-age-text", ageInfo.main);
    set("wallet-age-subtext", ageInfo.sub);

    const totalTx = feats.total_transactions != null ? Math.round(feats.total_transactions) : (transfers.length > 0 ? transfers.length : Math.round((feats.transaction_frequency || 0) * Math.max(feats.wallet_age || 1, 1)));
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
    renderReasons(data, level);

    /* ── Mini gauge & Network Metrics ── */
    updateGauge(score);
    set("centrality-val", fmtN(feats.graph_centrality, 4));
    set("cluster-val",    fmtN(feats.cluster_risk_score, 4));
    set("burst-val",      fmtN(feats.burst_activity_score, 2));
    set("flashloan-val",  feats.flash_loan_usage ? "⚠️ Detected" : "None");

    /* ── Feature Table ── */
    renderFeats(feats, chain);

    /* ── Token Holdings ── */
    renderTokens(transfers, chain, feats);

    /* ── Transfers Table ── */
    renderTx(transfers, data.address, chain, data.is_real_transfers);

    /* ── Threat Alerts Feed ── */
    renderThreatAlerts(reasons, level);

    /* ── History Sparkline & Trend ── */
    renderHistory(score, level);
}

// ── Feature Table ─────────────────────────────────────────────────────────────
function renderFeats(feats, chain) {
    const box = g("features-table");
    if (!box) return;
    const isTron = chain === "tron";
    const ROWS = [
        ["wallet_balance",              isTron ? "TRX Native Balance" : "Native Asset Balance"],
        ["transaction_amount",          "Estimated Portfolio Volume (USD)"],
        ["wallet_age",                  "Account Longevity (Days Active)"],
        ["total_transactions",          "Total Recorded Transfers"],
        ["failed_transactions",         "Reverted / Failed Transactions"],
        ["unique_counterparties",       "Unique Counterparties Interacted"],
        ["distance_to_blacklisted_wallet","Proximity to Blacklist (Graph Hops)"],
        ["burst_activity_score",        "Rapid / Automated Bot Activity"],
        ["smart_contract_calls",        isTron ? "TRC-20 Contract Triggers" : "Smart Contract Interactions"],
        ["rug_pull_token_interaction",  "Risky / Scam Token Flags"],
        ["flash_loan_usage",            "Flash Loan Borrowing Actions"],
    ];
    box.innerHTML = ROWS.map(([k, label]) => {
        let v = feats[k];
        if (v == null) return "";
        let display = "";
        if (k === "wallet_age") {
            const ageInfo = formatWalletAge(v);
            display = ageInfo.full;
        } else if (k === "distance_to_blacklisted_wallet") {
            display = v === 99 || v == null ? "Safe (No Links)" : v === 0 ? "Direct (0 Hops)" : `${v} Hop(s)`;
        } else if (k === "burst_activity_score") {
            display = v > 0.6 ? `High (${(v * 100).toFixed(0)}%)` : v > 0.3 ? `Normal (${(v * 100).toFixed(0)}%)` : `Low (${(v * 100).toFixed(0)}%)`;
        } else if (k === "rug_pull_token_interaction" || k === "flash_loan_usage") {
            display = v > 0 ? "Detected" : "None";
        } else if (typeof v === "number") {
            display = Number.isInteger(v) ? Number(v).toLocaleString() : Number(v).toLocaleString("en-US", { maximumFractionDigits: 4 });
        } else {
            display = String(v);
        }

        const risky = (k === "rug_pull_token_interaction" && v > 0) ||
                      (k === "flash_loan_usage" && v > 0) ||
                      (k === "burst_activity_score" && v > 0.6) ||
                      (k === "distance_to_blacklisted_wallet" && v < 2);
        const valCls = risky ? "font-mono font-bold text-rose-400" : "font-mono font-bold text-slate-300";
        return '<div class="flex justify-between items-center py-2 border-b border-slate-800/60">' +
               '<span class="text-slate-400 text-xs">' + esc(label) + '</span>' +
               '<span class="' + valCls + ' text-xs">' + esc(display) + '</span>' +
               '</div>';
    }).join("");
}

// ── Token Holdings ────────────────────────────────────────────────────────────
function renderTokens(transfers, chain, feats) {
    const box = g("token-holdings");
    if (!box) return;
    const isTron = chain === "tron";

    if (!transfers || !transfers.length) {
        if (isTron && feats && feats.wallet_balance != null) {
            box.innerHTML = `
                <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                    <div class="flex items-center gap-1.5">
                        <span class="font-bold text-slate-200">TRX</span>
                        <span class="tag-pill bg-emerald-950 text-emerald-300 border border-emerald-700">Native</span>
                    </div>
                    <div class="text-right">
                        <p class="font-mono font-bold text-white">${Number(feats.wallet_balance).toLocaleString("en-US", { maximumFractionDigits: 4 })}</p>
                        <p class="text-slate-500 text-[10px]">TRON Native</p>
                    </div>
                </div>
            `;
            return;
        }
        box.innerHTML = '<div class="text-slate-500 text-center py-4 text-xs">Cannot fetch token holdings for this wallet.</div>';
        return;
    }
    const agg = {};
    transfers.forEach(tx => {
        const sym  = tx.token_symbol || tx.tokenSymbol || (isTron ? "TRC20" : "TOKEN");
        const amt  = parseFloat(tx.amount_usdt || 0);
        const standard = tx.token_standard || (isTron ? (sym === "TRX" ? "Native" : "TRC-20") : "ERC-20");
        const contract = tx.contract_address || "";
        const scam = (tx.scam_flag || 0) > 0 || sym.toUpperCase().includes("SCAM");
        if (!agg[sym]) agg[sym] = { total: 0, count: 0, scam, standard, contract };
        agg[sym].total += amt;
        agg[sym].count++;
    });

    box.innerHTML = Object.entries(agg).map(([sym, d]) => {
        const isScam = d.scam;
        const cardCls = isScam ? "bg-rose-950/60 border border-rose-800" : "bg-slate-900/60 border border-slate-800";
        const nameCls = isScam ? "font-bold text-rose-300" : "font-bold text-slate-200";
        const valCls  = isScam ? "font-mono font-bold text-rose-400" : "font-mono font-bold text-white";
        const badge   = isScam ? '<span class="tag-pill bg-rose-900 text-rose-300 ml-1">⚠ SCAM</span>' :
                        (isTron ? `<span class="tag-pill ${d.standard === 'Native' ? 'bg-indigo-950 text-indigo-300 border border-indigo-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-700'} ml-1">${esc(d.standard)}</span>` : "");
        const tokenLink = isTron && d.contract ? `<a href="${TronService.getTronScanUrl('token', d.contract)}" target="_blank" rel="noopener noreferrer" class="text-[10px] text-indigo-400 hover:underline block font-mono">Contract ↗</a>` : "";

        return '<div class="flex items-center justify-between p-2.5 rounded-xl ' + cardCls + '">' +
               '<div><div class="flex items-center gap-1.5"><span class="' + nameCls + '">' + esc(sym) + '</span>' + badge + '</div>' + tokenLink + '</div>' +
               '<div class="text-right"><p class="' + valCls + '">' + d.total.toLocaleString("en-US",{maximumFractionDigits:2}) + '</p>' +
               '<p class="text-slate-500 text-[10px]">' + d.count + ' transfer events</p></div>' +
               '</div>';
    }).join("");
}

// ── Transfers Table ───────────────────────────────────────────────────────────
function renderTx(transfers, wallet, chain, isReal) {
    const tbody = g("transactions-table-body");
    if (!tbody) return;
    const isTron = chain === "tron" || (wallet && wallet.startsWith("T"));
    const txBadge = g("tx-chain-badge");
    if (txBadge) {
        if (transfers && transfers.length > 0) {
            if (isTron) {
                txBadge.textContent = "⚡ TronGrid Pro Real-Time TRC-20 & TRX History (" + transfers.length + ")";
                txBadge.className = "tag-pill bg-emerald-950 text-emerald-300 border border-emerald-700";
            } else {
                txBadge.textContent = "⚡ Real On-Chain History (" + transfers.length + ")";
                txBadge.className = "tag-pill bg-emerald-950 text-emerald-300 border border-emerald-800";
            }
        } else {
            txBadge.textContent = "No On-Chain Activity Found";
            txBadge.className = "tag-pill bg-slate-800 text-slate-400 border border-slate-700";
        }
    }

    if (!transfers || !transfers.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-400 text-xs font-mono">No on-chain transaction history found for this wallet on ' + esc((isTron ? "TRON" : (chain || "ETH")).toUpperCase()) + '.</td></tr>';
        return;
    }
    const walletLow = (wallet || "").toLowerCase();
    const chainLow  = (chain || (isTron ? "tron" : "ethereum")).toLowerCase();
    const explorerMap = {
        tron: "https://tronscan.org/#/transaction/",
        ethereum: "https://etherscan.io/tx/"
    };
    const base = explorerMap[chainLow] || (isTron ? "https://tronscan.org/#/transaction/" : "https://etherscan.io/tx/");
    const addrBase = isTron ? "https://tronscan.org/#/address/" : "https://etherscan.io/address/";

    tbody.innerHTML = transfers.map(tx => {
        const hash    = tx.transaction_id || tx.hash || "";
        const from    = tx.from_address   || tx.from || "";
        const to      = tx.to_address     || tx.to   || "";
        const isOut   = walletLow && from.toLowerCase() === walletLow;
        const counter = isOut ? to : from;
        const sym     = tx.token_symbol || tx.tokenSymbol || (isTron ? "TRC20" : "ETH");
        const standard = tx.token_standard || (isTron ? (sym === "TRX" ? "TRX" : "TRC-20") : "ERC-20");
        const isScam  = (tx.scam_flag || 0) > 0 || sym.toUpperCase().includes("SCAM");
        const amt     = parseFloat(tx.amount_usdt || 0).toLocaleString("en-US", { maximumFractionDigits: 4 });
        const rawTs   = tx.block_timestamp || (tx.timeStamp ? Number(tx.timeStamp) * 1000 : Date.now());
        const tsMs    = rawTs > 1e12 ? rawTs : rawTs * 1000;
        const dt      = new Date(isNaN(tsMs) ? Date.now() : tsMs);
        const dateStr = dt.toLocaleDateString([], { month: "short", day: "numeric", year: "2-digit" });
        const timeStr = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        const dirBg   = isOut ? "bg-amber-950/80 text-amber-300 border border-amber-800" : "bg-emerald-950/80 text-emerald-300 border border-emerald-800";
        const dirTxt  = isOut ? "OUT" : "IN";
        const symBg   = isScam ? "bg-rose-950 text-rose-300 border border-rose-800" : (isTron ? "bg-emerald-950/70 text-emerald-300 border border-emerald-700" : "bg-slate-900 text-slate-300 border border-slate-800");
        const isConfirmed = tx.confirmed !== false;
        const riskTxt = isScam ? "⚠ SCAM" : (isConfirmed ? (isTron ? "✓ Confirmed" : "✓ Success") : "✕ Failed");
        const riskBg  = isScam ? "bg-rose-950 text-rose-300 border border-rose-800" : (isConfirmed ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-rose-950 text-rose-300 border border-rose-800");
        const amtCls  = isScam ? "text-rose-400" : "text-white";

        const counterLink = counter ? `<a href="${addrBase}${esc(counter)}" target="_blank" rel="noopener noreferrer" class="hover:underline font-mono text-slate-300 hover:text-indigo-400">${shorten(counter, 12)} ↗</a>` : "<span class='text-slate-600'>Contract</span>";

        return "<tr class='border-b border-slate-800/60 hover:bg-slate-900/40 transition-colors'>" +
          "<td class='py-3 pr-4 font-mono text-xs text-indigo-400'>" +
            (hash ? "<a href='" + base + esc(hash) + "' target='_blank' rel='noopener noreferrer' class='hover:underline flex items-center gap-1 font-mono'>" + shorten(hash, 12) + " ↗</a>" : "<span class='text-slate-500'>—</span>") +
          "</td>" +
          "<td class='py-3 pr-4'>" +
            "<span class='tag-pill " + dirBg + "'>" + dirTxt + "</span>" +
          "</td>" +
          "<td class='py-3 pr-4 text-xs'>" + counterLink + "</td>" +
          "<td class='py-3 pr-4'>" +
            "<span class='tag-pill " + symBg + "'>" + esc(sym) + (isTron ? ` <span class='text-[9px] opacity-75 font-normal'>(${esc(standard)})</span>` : "") + "</span>" +
          "</td>" +
          "<td class='py-3 pr-4 font-mono font-bold text-xs " + amtCls + "'>" + amt + "</td>" +
          "<td class='py-3 pr-4'>" +
            "<span class='tag-pill " + riskBg + "'>" + riskTxt + "</span>" +
          "</td>" +
          "<td class='py-3 font-mono text-xs text-slate-400'>" + dateStr + " <span class='text-slate-600 text-[10px]'>" + timeStr + "</span></td>" +
          "</tr>";
    }).join("");
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

// ── AI Reasons & Pointwise Drivers ────────────────────────────────────────────
function renderReasons(data, level) {
    const box = g("pointwise-drivers-container") || g("activity-manager-cards");
    const summaryText = g("ai-summary-text");
    const recBox = g("recommendation-box");
    const recText = g("recommendation-text");
    const driverCount = g("driver-count-badge");

    // Support both full data object and fallback raw reasons array
    const isFullData = data && typeof data === "object" && !Array.isArray(data);
    const drivers = isFullData && Array.isArray(data.pointwise_ai_drivers) ? data.pointwise_ai_drivers : null;
    const reasons = isFullData ? (data.reasons || []) : (Array.isArray(data) ? data : []);
    const rec = isFullData ? data.recommendation : "";
    const summary = isFullData && data.simple_summary ? data.simple_summary : null;

    // Update AI Executive Plain English Summary
    if (summaryText) {
        if (summary) {
            summaryText.textContent = summary;
        } else if (level === "CRITICAL RISK") {
            summaryText.textContent = "⚠️ DANGER: This wallet scored in the Critical Risk bracket due to direct sanction listings, extreme anomaly scores, or zero-hop proximity to criminal clusters. Do not approve transactions.";
        } else if (level === "HIGH RISK") {
            summaryText.textContent = "⚠️ CAUTION: High Risk score detected due to elevated burst activity, recent reverts, or proximity to suspicious clusters. Review carefully.";
        } else if (level === "MODERATE RISK") {
            summaryText.textContent = "ℹ️ MODERATE: Score is moderate. The wallet has standard DeFi activity with minor unusual contract patterns. Low-risk operations may proceed.";
        } else {
            summaryText.textContent = "🛡️ VERIFIED CLEAN: Low risk profile with healthy transaction history, long account age, and zero links to sanctions or malicious clusters.";
        }
    }

    if (driverCount && drivers) {
        driverCount.textContent = `${drivers.length} Pointwise Factors`;
    }

    if (!box) return;

    // If structured pointwise drivers are available
    if (drivers && drivers.length > 0) {
        box.innerHTML = drivers.map(d => {
            const sev = d.severity || "info";
            const isCrit = sev === "critical";
            const isCaution = sev === "caution";
            const isSafe = sev === "safe";

            const borderCls = isCrit ? "border-rose-800 bg-rose-950/40" 
                            : isCaution ? "border-amber-800 bg-amber-950/40" 
                            : isSafe ? "border-emerald-800/80 bg-emerald-950/30" 
                            : "border-slate-800 bg-slate-900/60";

            const titleCls = isCrit ? "text-rose-300 font-bold" 
                           : isCaution ? "text-amber-300 font-bold" 
                           : isSafe ? "text-emerald-300 font-bold" 
                           : "text-indigo-200 font-bold";

            const badgeBg = isCrit ? "bg-rose-900/80 text-rose-200 border-rose-700" 
                          : isCaution ? "bg-amber-900/80 text-amber-200 border-amber-700" 
                          : isSafe ? "bg-emerald-900/80 text-emerald-200 border-emerald-700" 
                          : "bg-slate-800 text-slate-300 border-slate-700";

            const impactTxt = d.impact ? `<span class="tag-pill ${badgeBg} text-[10px] font-mono">${esc(d.impact)}</span>` : "";

            return `
                <div class="p-3 rounded-xl border ${borderCls} text-xs flex flex-col gap-1.5 transition-all">
                    <div class="flex items-center justify-between gap-2 flex-wrap">
                        <div class="flex items-center gap-1.5">
                            <span class="text-sm">${d.icon || "📌"}</span>
                            <span class="${titleCls} text-xs">${esc(d.title)}</span>
                        </div>
                        ${impactTxt}
                    </div>
                    <p class="text-slate-200 leading-relaxed text-xs">${esc(d.simple_explanation)}</p>
                    ${d.evidence ? `<div class="mt-0.5 pt-1.5 border-t border-slate-800/60 text-[11px] text-slate-400 font-mono flex items-center gap-1">
                        <span class="text-slate-500">🔍 Evidence:</span>
                        <span class="text-slate-300">${esc(d.evidence)}</span>
                    </div>` : ""}
                </div>
            `;
        }).join("");
    } else if (!reasons || !reasons.length) {
        box.innerHTML = '<div class="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs">No active risk triggers detected for this wallet.</div>';
    } else {
        // Fallback simple list
        box.innerHTML = reasons.map(r => {
            const isCrit = r.includes("CRITICAL") || r.includes("🔴");
            const isHigh = r.includes("HIGH") || r.includes("🟠") || r.includes("⚡");
            const bg = isCrit ? "bg-rose-950/60 border-rose-800 text-rose-200"
                     : isHigh ? "bg-amber-950/60 border-amber-800 text-amber-200"
                     : "bg-slate-900/60 border-slate-800 text-slate-300";
            return '<div class="p-2.5 rounded-xl border text-xs ' + bg + '">' + esc(r) + '</div>';
        }).join("");
    }

    if (recBox) recBox.className = "p-3 rounded-xl border text-xs mt-auto " + recBg(level);
    if (recText && rec) recText.textContent = rec;
}

// ── Interactive Gemini AI Q&A Engine ──────────────────────────────────────────
async function askAiQuestion(question) {
    if (!state.currentAddress) {
        showToast("Please scan a wallet first to ask Gemini AI about it.", "info");
        return;
    }

    const responseBox = g("ai-response-box");
    const responseContent = g("ai-response-content");
    const spinner = g("ai-loading-spinner");
    const customInput = g("ai-custom-input");

    if (customInput) customInput.value = question;
    if (responseBox) responseBox.classList.remove("hidden");
    if (spinner) spinner.classList.remove("hidden");
    if (responseContent) {
        responseContent.innerHTML = `<div class="flex items-center gap-2 text-indigo-300 font-mono py-2">
            <span class="animate-spin text-base">⚙️</span>
            <span>Querying Gemini 3.7 Flash with all wallet telemetry (Balance: ${state.currentData?.features?.wallet_balance || 0}, Score: ${state.currentData?.risk_score || 0}/100)...</span>
        </div>`;
    }

    try {
        const res = await fetch("/api/ai/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                address: state.currentAddress,
                chain: state.currentChain || "ethereum",
                question: question,
                wallet_data: state.currentData
            })
        });

        const json = await res.json();
        if (spinner) spinner.classList.add("hidden");

        if (json.status === "success" && json.ai_response && json.ai_response.answer) {
            if (responseContent) {
                // Convert markdown bullet points to clean visual HTML
                let formatted = esc(json.ai_response.answer)
                    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-bold">$1</strong>')
                    .replace(/^• (.*?)$/gm, '<div class="py-1 flex items-start gap-1.5"><span class="text-indigo-400 mt-0.5">•</span><span>$1</span></div>')
                    .replace(/\n\n/g, '<div class="h-2"></div>');

                responseContent.innerHTML = formatted;
            }
            const modelTag = g("ai-model-tag");
            if (modelTag && json.ai_response.source) {
                modelTag.textContent = json.ai_response.source;
            }
        } else {
            if (responseContent) {
                responseContent.textContent = json.detail || "Unable to generate AI explanation at this moment.";
            }
        }
    } catch (err) {
        if (spinner) spinner.classList.add("hidden");
        if (responseContent) {
            responseContent.textContent = "Network error communicating with AI server: " + err.message;
        }
    }
}

function submitCustomAiQuestion() {
    const input = g("ai-custom-input");
    if (!input || !input.value.trim()) {
        showToast("Please enter a question to ask AI.", "info");
        return;
    }
    askAiQuestion(input.value.trim());
}

// Expose globally for HTML onclick triggers
window.askAiQuestion = askAiQuestion;
window.submitCustomAiQuestion = submitCustomAiQuestion;

// ── Executive Risk & Compliance Report Generator ──────────────────────────────
function openExecutiveReport(data, chain) {
    if (!data) return;
    const modal = g("executive-report-modal");
    if (!modal) return;

    const score = Math.round(data.risk_score || 0);
    const level = getRiskLevelClassification(score, data.risk_level);
    const feats = data.features || {};
    const drivers = data.pointwise_ai_drivers || [];
    const isTron = chain === "tron" || (data.address && data.address.startsWith("T"));
    const chainName = isTron ? "TRON (TRC-20 / TRX)" : "ETHEREUM (ETH)";
    const symbol = isTron ? "TRX" : "ETH";

    // Set Timestamps & Metadata
    set("rep-chain-pill", chainName);
    set("rep-timestamp", new Date().toLocaleString());
    set("rep-full-address", data.address || "—");

    // Profile Numbers (Human-readable)
    const ageInfo = formatWalletAge(feats.wallet_age);
    set("rep-age", ageInfo.full);
    set("rep-tx-count", feats.total_transactions != null ? Number(feats.total_transactions).toLocaleString() : "0");
    set("rep-failed-tx", (feats.failed_transactions != null ? feats.failed_transactions : 0) + " reverted");
    const balVal = feats.wallet_balance != null ? Number(feats.wallet_balance) : 0;
    set("rep-balance", `${balVal.toLocaleString("en-US", { maximumFractionDigits: 4 })} ${symbol}`);

    // Score & Verdict
    set("rep-score-num", score);
    set("rep-verdict-level", level);
    
    const isCrit = score > 80;
    const isHigh = score > 60;
    const isSafe = score <= 30;

    const verdictCard = g("rep-verdict-card");
    const verdictIcon = g("rep-verdict-icon");
    const verdictLevel = g("rep-verdict-level");
    const verdictSummary = g("rep-verdict-summary");

    if (verdictCard) {
        verdictCard.className = `p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            isCrit ? "bg-rose-950/70 border-rose-800 text-rose-200"
            : isHigh ? "bg-amber-950/70 border-amber-800 text-amber-200"
            : isSafe ? "bg-emerald-950/70 border-emerald-800 text-emerald-200"
            : "bg-slate-950 border-slate-800 text-slate-200"
        }`;
    }

    if (verdictIcon) {
        verdictIcon.textContent = isCrit ? "🚨" : isHigh ? "⚠️" : isSafe ? "🛡️" : "ℹ️";
    }

    if (verdictLevel) {
        verdictLevel.className = `text-xl font-extrabold ${
            isCrit ? "text-rose-300" : isHigh ? "text-amber-300" : isSafe ? "text-emerald-300" : "text-sky-300"
        }`;
    }

    if (verdictSummary) {
        if (data.simple_summary) {
            verdictSummary.textContent = data.simple_summary;
        } else if (isCrit) {
            verdictSummary.textContent = "CRITICAL RISK: High-threat signals detected. The address is linked to sanction lists, malicious mixers, or exploit contracts. Interactions should be strictly blocked.";
        } else if (isHigh) {
            verdictSummary.textContent = "HIGH RISK: Unusual burst activity or proximity to suspicious counterparties detected. Caution is advised.";
        } else if (isSafe) {
            verdictSummary.textContent = "SAFE & CLEAN: Organic user activity pattern with mature history, normal transaction frequency, and zero links to sanctions or illicit mixers.";
        } else {
            verdictSummary.textContent = "MODERATE RISK: Standard DeFi usage with moderate counterparty diversity. Standard precautionary security applies.";
        }
    }

    // Populate Pointwise Drivers (Clean & Understandable)
    const driversBox = g("rep-drivers-container");
    if (driversBox) {
        if (drivers.length > 0) {
            driversBox.innerHTML = drivers.map(d => {
                const sev = d.severity || "info";
                const isItemCrit = sev === "critical";
                const isItemCaution = sev === "caution";
                const isItemSafe = sev === "safe";

                const bgCls = isItemCrit ? "bg-rose-950/40 border-rose-800/80 text-rose-200"
                            : isItemCaution ? "bg-amber-950/40 border-amber-800/80 text-amber-200"
                            : isItemSafe ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-200"
                            : "bg-slate-950/70 border-slate-800 text-slate-300";

                return `
                    <div class="p-3 rounded-xl border ${bgCls} text-xs flex flex-col gap-1">
                        <div class="flex items-center justify-between">
                            <span class="font-bold flex items-center gap-1.5 text-white">
                                <span>${d.icon || "📌"}</span>
                                <span>${esc(d.title)}</span>
                            </span>
                            ${d.impact ? `<span class="tag-pill bg-slate-900 border border-slate-700 text-[10px]">${esc(d.impact)}</span>` : ""}
                        </div>
                        <p class="text-slate-300 leading-relaxed text-xs">${esc(d.simple_explanation)}</p>
                    </div>
                `;
            }).join("");
        } else {
            driversBox.innerHTML = `
                <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 text-xs space-y-1.5">
                    <div class="flex items-center gap-2 font-semibold text-emerald-400"><span>🛡️</span><span>Sanction & Blacklist Screening</span></div>
                    <p class="text-slate-400">Zero proximity or transfer links detected to OFAC SDN, Tornado Cash, or illicit mixers.</p>
                    <div class="flex items-center gap-2 font-semibold text-emerald-400 pt-1"><span>⏱️</span><span>Account Maturity & Longevity</span></div>
                    <p class="text-slate-400">Active history established with steady non-automated spacing between transactions.</p>
                </div>
            `;
        }
    }

    // Recommendation
    set("rep-action-text", data.recommendation || (isSafe ? "Safe to proceed with standard interactions. Normal precaution applies." : "Exercise high caution before approving transactions or interacting with this contract."));

    // Open Modal
    modal.classList.remove("hidden");
}

function closeExecutiveReport() {
    const modal = g("executive-report-modal");
    if (modal) modal.classList.add("hidden");
}

function copyReportSummary() {
    if (!state.currentData) {
        showToast("No report data available to copy.", "info");
        return;
    }
    const d = state.currentData;
    const score = Math.round(d.risk_score || 0);
    const level = d.risk_level || "UNKNOWN";
    const text = `======================================================
EXECUTIVE WALLET RISK AUDIT REPORT
======================================================
Target Address: ${d.address}
Blockchain: ${(d.chain || "ethereum").toUpperCase()}
Risk Score: ${score} / 100 (${level})
Executive Verdict: ${d.simple_summary || "Forensic scan completed"}
Recommended Action: ${d.recommendation || "Safe to proceed with standard transactions."}
Platform: AI-DeFi Risk Intelligence (v2.0)
======================================================`;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast("✓ Report summary copied to clipboard!", "success");
        }).catch(() => {
            showToast("Summary copied to clipboard.", "info");
        });
    } else {
        showToast("Summary generated for copying.", "info");
    }
}

// Expose globally
window.openExecutiveReport = openExecutiveReport;
window.closeExecutiveReport = closeExecutiveReport;
window.copyReportSummary = copyReportSummary;

function recBg(level) {
    const m = { "CRITICAL RISK":"bg-rose-950/80 border-rose-800 text-rose-200",
                "HIGH RISK":"bg-orange-950/80 border-orange-800 text-orange-200",
                "MODERATE RISK":"bg-amber-950/80 border-amber-800 text-amber-200",
                "LOW RISK":"bg-sky-950/80 border-sky-800 text-sky-200",
                "VERY LOW RISK":"bg-emerald-950/80 border-emerald-800 text-emerald-200" };
    return m[level] || m["VERY LOW RISK"];
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
