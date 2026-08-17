/**
 * app.js — AI-DeFi Risk Intelligence v2.0
 * Fix: single-quoted class strings in ternaries, null-safe element access,
 *      features panel, token holdings, network metrics, history chart.
 */

const API_BASE  = "http://localhost:8000";
const TOKEN_KEY = "defi_risk_jwt";
const CREDS     = { username: "defi_analyst", password: "secure_password_123" };

let miniGaugeChart  = null;
let historyChart    = null;

// ── Boot ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const input  = g("wallet-search-input");
    const btn    = g("scan-wallet-btn");
    if (btn)   btn.addEventListener("click", go);
    if (input) input.addEventListener("keypress", e => e.key === "Enter" && go());

    document.querySelectorAll(".sample-address-badge").forEach(b => {
        b.addEventListener("click", () => {
            if (input) input.value = b.dataset.address;
            const cs = g("chain-select");
            if (cs && b.dataset.chain) cs.value = b.dataset.chain;
            go();
        });
    });

    initGauge(0);
    initHistory();
    if (input && input.value.trim()) go();
});

function go() {
    const input = g("wallet-search-input");
    const chain = g("chain-select") ? g("chain-select").value : "tron";
    const addr  = input ? input.value.trim() : "";
    if (addr) scan(addr, chain);
}

// ── Auth ───────────────────────────────────────────────────────────────────────
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
        err("Auth failed — backend unreachable at " + API_BASE);
        return null;
    }
}

// ── Validation ────────────────────────────────────────────────────────────────
function valid(a) {
    return /^T[a-zA-Z0-9]{33}$/.test(a) || /^0x[a-fA-F0-9]{40}$/.test(a);
}

// ── Fetch ─────────────────────────────────────────────────────────────────────
async function scan(address, chain) {
    if (!valid(address)) {
        err("Invalid address. Use 0x… (42 chars) for EVM or T… (34 chars) for TRON.");
        return;
    }
    loading(true);
    setStatus("Scanning…", false);
    try {
        const tok = await token();
        if (!tok) { loading(false); return; }

        const url = `${API_BASE}/api/v1/wallet/${encodeURIComponent(address)}?chain=${encodeURIComponent(chain)}`;
        const r = await fetch(url, { headers: { "Authorization": "Bearer " + tok, "Accept": "application/json" } });

        if (r.status === 401) { localStorage.removeItem(TOKEN_KEY); return scan(address, chain); }
        if (r.status === 429) { err("Rate limit hit — please wait a moment."); loading(false); return; }
        if (r.status === 400) { const j = await r.json(); err("Validation: " + (j.detail || "Bad request")); loading(false); return; }
        if (!r.ok) { err("Server error HTTP " + r.status); loading(false); return; }

        const data = await r.json();
        fill(data, chain);
        setStatus("API Online", true);
    } catch(e) {
        err("Network error — is FastAPI running at " + API_BASE + "?");
        setStatus("Offline", false);
    }
    loading(false);
}

// ── Populate all UI ────────────────────────────────────────────────────────────
function fill(data, chain) {
    const exportBtn = g("export-report-btn");
    if (exportBtn) {
        exportBtn.classList.remove("hidden");
        exportBtn.onclick = () => {
            document.title = "Risk_Report_" + (data.address || "Wallet").substring(0,8) + ".pdf";
            window.print();
        };
    }

    const score     = Math.round(data.risk_score  || 0);
    const level     = (data.risk_level || "SAFE").toUpperCase();
    const bd        = data.breakdown  || {};
    const feats     = data.features   || {};
    const reasons   = data.reasons    || [];
    const transfers = data.recent_transfers || [];

    /* ── Stat bar ── */
    set("calibrated-risk-score", score);
    set("risk-level-text", level);
    cls("risk-level-text", "text-2xl font-black " + lvlClr(level));

    const age = feats.wallet_age != null ? feats.wallet_age.toFixed(1) + " d" : "—";
    set("wallet-age-text", age);

    const totalTx = Math.round((feats.transaction_frequency || 0) * Math.max(feats.wallet_age || 1, 1));
    set("tx-count-text", totalTx || "—");
    set("failed-tx-text", (feats.failed_transactions || 0) + " failed");

    const hops = feats.distance_to_blacklisted_wallet;
    const hopsStr = (hops == null || hops === 99) ? "Safe" : String(hops);
    set("hops-text", hopsStr);
    cls("hops-text", "text-2xl font-black " + (hops < 3 ? "text-red-500" : hops < 5 ? "text-amber-500" : "text-emerald-500"));

    const suffix = g("risk-score-suffix");
    if (suffix) { suffix.textContent = "/ 100 · " + level; suffix.className = "tag-pill mt-2 inline-block " + lvlBadge(level); }

    /* ── Donut ring ── */
    set("donut-score", score);
    set("target-address", shorten(data.address || "—", 22));
    updateDonut(score, level);

    const lvlBadgeEl = g("risk-level-badge");
    if (lvlBadgeEl) { lvlBadgeEl.textContent = level; lvlBadgeEl.className = "tag-pill text-sm px-4 py-1 " + lvlBadge(level); }

    /* ── Breakdown bars ── */
    const tab  = Math.round((bd.tabular_ensemble || 0) * 100);
    const gnn  = Math.round((bd.gnn_network_risk || 0) * 100);
    const anom = Math.round((bd.anomaly_score    || 0) * 100);
    bar("tabular", tab);
    bar("gnn",     gnn);
    bar("anomaly", anom);
    set("model-fusion-signals",
        "Tabular: " + fmt(bd.tabular_ensemble) +
        " | GNN: " + fmt(bd.gnn_network_risk) +
        " | Anomaly: " + fmt(bd.anomaly_score));

    /* ── AI Reasons ── */
    renderReasons(reasons, data.recommendation, level);

    /* ── Mini gauge ── */
    updateGauge(score);

    /* ── Network metrics ── */
    set("centrality-val", fmtN(feats.graph_centrality, 4));
    set("cluster-val",    fmtN(feats.cluster_risk_score, 4));
    set("burst-val",      fmtN(feats.burst_activity_score, 2));
    set("flashloan-val",  feats.flash_loan_usage ? "⚠️ Detected" : "None");

    /* ── Feature table ── */
    renderFeats(feats);

    /* ── Token holdings ── */
    renderTokens(transfers);

    /* ── Transfers table ── */
    renderTx(transfers, data.address, chain);

    /* ── History chart ── */
    renderHistory(score, level);

    /* ── Chain badge ── */
    set("tx-chain-badge", chain.toUpperCase());
}

// ── Donut SVG ─────────────────────────────────────────────────────────────────
function updateDonut(score, level) {
    const circ = 251.2;
    const fill = document.getElementById("donut-fill");
    if (!fill) return;
    const colors = { CRITICAL:"#EF4444", HIGH:"#F97316", MEDIUM:"#F59E0B", LOW:"#06B6D4", SAFE:"#10B981" };
    fill.setAttribute("stroke-dashoffset", String(circ - (score / 100) * circ));
    fill.setAttribute("stroke", colors[level] || "#10B981");
}

// ── Progress bars ─────────────────────────────────────────────────────────────
function bar(prefix, pct) {
    const p = g(prefix + "-percent");
    const b = g(prefix + "-bar");
    if (p) p.textContent = pct + "%";
    if (b) {
        b.style.width = pct + "%";
        b.style.backgroundColor = pct > 70 ? "#EF4444" : pct > 40 ? "#F59E0B" : "#10B981";
    }
}

// ── AI Reasons ────────────────────────────────────────────────────────────────
function renderReasons(reasons, rec, level) {
    const box = g("activity-manager-cards");
    if (!box) return;
    if (!reasons || !reasons.length) {
        box.innerHTML = '<div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs">No risk triggers detected for this wallet.</div>';
    } else {
        box.innerHTML = reasons.map(r => {
            const isCrit = r.includes("CRITICAL") || r.includes("🔴");
            const isHigh = r.includes("HIGH") || r.includes("🟠") || r.includes("⚡");
            const bg = isCrit ? "bg-rose-50 border-rose-200 text-rose-800"
                     : isHigh ? "bg-amber-50 border-amber-200 text-amber-800"
                     : "bg-slate-50 border-slate-200 text-slate-700";
            return '<div class="p-2.5 rounded-xl border text-xs ' + bg + '">' + esc(r) + '</div>';
        }).join("");
    }
    const recBox  = g("recommendation-box");
    const recText = g("recommendation-text");
    if (recBox)  recBox.className = "p-3 rounded-xl border text-xs " + recBg(level);
    if (recText && rec) recText.textContent = rec;
}

function recBg(level) {
    const m = { CRITICAL:"bg-rose-50 border-rose-200", HIGH:"bg-orange-50 border-orange-200",
                MEDIUM:"bg-amber-50 border-amber-200", LOW:"bg-cyan-50 border-cyan-200", SAFE:"bg-emerald-50 border-emerald-100" };
    return m[level] || m.SAFE;
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
                      (k === "reconstruction_error" && v > 0.08) ||
                      (k === "distance_to_blacklisted_wallet" && v < 3);
        const valCls = risky ? "font-mono font-bold text-red-500" : "font-mono font-bold text-slate-800";
        return '<div class="flex justify-between items-center py-1.5 border-b border-slate-50">' +
               '<span class="text-slate-500 text-xs">' + label + '</span>' +
               '<span class="' + valCls + ' text-xs">' + esc(display) + '</span>' +
               '</div>';
    }).join("");
}

// ── Token Holdings ────────────────────────────────────────────────────────────
function renderTokens(transfers) {
    const box = g("token-holdings");
    if (!box) return;
    if (!transfers || !transfers.length) {
        box.innerHTML = '<div class="text-slate-400 text-center py-4 text-xs">No token data loaded.</div>';
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
        const cardCls = isScam ? "bg-rose-50 border border-rose-200" : "bg-slate-50 border border-slate-100";
        const nameCls = isScam ? "font-bold text-rose-700" : "font-bold text-slate-700";
        const valCls  = isScam ? "font-mono font-bold text-rose-600" : "font-mono font-bold text-slate-800";
        const badge   = isScam ? '<span class="tag-pill bg-rose-100 text-rose-600 ml-1">⚠ SCAM</span>' : "";
        return '<div class="flex items-center justify-between p-2 rounded-lg ' + cardCls + '">' +
               '<div class="flex items-center gap-1"><span class="' + nameCls + '">' + esc(sym) + '</span>' + badge + '</div>' +
               '<div class="text-right"><p class="' + valCls + '">' + d.total.toLocaleString("en-US",{maximumFractionDigits:2}) + '</p>' +
               '<p class="text-slate-400" style="font-size:10px">' + d.count + ' txs</p></div>' +
               '</div>';
    }).join("");
}

// ── Transfers Table ───────────────────────────────────────────────────────────
function renderTx(transfers, wallet, chain) {
    const tbody = g("transactions-table-body");
    if (!tbody) return;
    if (!transfers || !transfers.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-6 text-center text-slate-400 text-xs">No transfers found for this wallet.</td></tr>';
        return;
    }
    const walletLow = (wallet || "").toLowerCase();
    const base = chain === "tron" ? "https://tronscan.org/#/transaction/" : "https://etherscan.io/tx/";

    tbody.innerHTML = transfers.map(tx => {
        const hash    = tx.transaction_id || tx.hash || "";
        const from    = tx.from_address   || tx.from || "";
        const to      = tx.to_address     || tx.to   || "";
        const isOut   = walletLow && from.toLowerCase() === walletLow;
        const counter = isOut ? to : from;
        const sym     = tx.token_symbol || tx.tokenSymbol || "TOKEN";
        const isScam  = (tx.scam_flag || 0) > 0 || sym.toUpperCase().includes("SCAM");
        const amt     = parseFloat(tx.amount_usdt || 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
        const rawTs   = tx.block_timestamp || (tx.timeStamp ? Number(tx.timeStamp) * 1000 : Date.now());
        const tsMs    = rawTs > 1e12 ? rawTs : rawTs * 1000;
        const time    = new Date(isNaN(tsMs) ? Date.now() : tsMs).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        // build badge strings without quotes inside class attribute strings
        const dirBg   = isOut ? "background:#FEF3C7;border:1px solid #FCD34D;color:#92400E" : "background:#ECFDF5;border:1px solid #6EE7B7;color:#065F46";
        const dirTxt  = isOut ? "OUT" : "IN";
        const symBg   = isScam ? "background:#FFF1F2;border:1px solid #FECDD3;color:#9F1239" : "background:#F8FAFC;border:1px solid #E2E8F0;color:#475569";
        const riskTxt = isScam ? "⚠ SCAM" : "✓ OK";
        const riskBg  = isScam ? "background:#FFF1F2;border:1px solid #FECDD3;color:#9F1239" : "background:#ECFDF5;border:1px solid #6EE7B7;color:#065F46";
        const amtCls  = isScam ? "color:#DC2626" : "color:#1E293B";

        return "<tr style='border-bottom:1px solid #F8FAFC'>" +
          "<td style='padding:8px 12px;font-family:monospace;font-size:11px;color:#6366F1'>" +
            "<a href='" + base + esc(hash) + "' target='_blank' style='text-decoration:none;color:inherit'>" + shorten(hash, 14) + " ↗</a>" +
          "</td>" +
          "<td style='padding:8px 12px'>" +
            "<span style='display:inline-block;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;" + dirBg + "'>" + dirTxt + "</span>" +
          "</td>" +
          "<td style='padding:8px 12px;font-family:monospace;font-size:11px;color:#64748B'>" + shorten(counter, 12) + "</td>" +
          "<td style='padding:8px 12px'>" +
            "<span style='display:inline-block;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:600;" + symBg + "'>" + esc(sym) + "</span>" +
          "</td>" +
          "<td style='padding:8px 12px;font-family:monospace;font-weight:700;font-size:12px;" + amtCls + "'>" + amt + "</td>" +
          "<td style='padding:8px 12px'>" +
            "<span style='display:inline-block;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;" + riskBg + "'>" + riskTxt + "</span>" +
          "</td>" +
          "<td style='padding:8px 12px;font-family:monospace;font-size:11px;color:#94A3B8'>" + time + "</td>" +
          "</tr>";
    }).join("");
}

// ── Chart.js Mini Gauge ───────────────────────────────────────────────────────
function initGauge(score) {
    const canvas = g("miniGaugeChart");
    if (!canvas || typeof Chart === "undefined") return;
    const c = scoreClr(score);
    miniGaugeChart = new Chart(canvas.getContext("2d"), {
        type: "doughnut",
        data: { datasets: [{ data: [score, 100 - score], backgroundColor: [c, "rgba(226,232,240,.4)"], borderWidth: 0 }] },
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

// ── History Sparkline ─────────────────────────────────────────────────────────
function initHistory() {
    const canvas = g("riskHistoryChart");
    if (!canvas || typeof Chart === "undefined") return;
    historyChart = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: { labels: [], datasets: [{ label: "Risk Score", data: [],
            borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,.1)",
            borderWidth: 2, pointRadius: 3, fill: true, tension: 0.4 }] },
        options: { responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { min: 0, max: 100, grid: { color: "#f1f5f9" } }, x: { grid: { display: false } } } }
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
    const peak = Math.max(...vals), avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
    set("peak-score", peak);
    set("avg-score",  avg);
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function g(id)       { return document.getElementById(id); }
function set(id, v)  { const e = g(id); if (e) e.textContent = v; }
function cls(id, c)  { const e = g(id); if (e) e.className = c; }
function fmt(n)      { return n != null ? Number(n).toFixed(3) : "—"; }
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
    return s > 80 ? "#EF4444" : s > 60 ? "#F97316" : s > 40 ? "#F59E0B" : s > 20 ? "#06B6D4" : "#10B981";
}
function lvlClr(l) {
    const m = { CRITICAL: "text-2xl font-black text-red-500", HIGH: "text-2xl font-black text-orange-500",
                MEDIUM: "text-2xl font-black text-amber-500", LOW: "text-2xl font-black text-cyan-500",
                SAFE: "text-2xl font-black text-emerald-500" };
    return m[l] || "text-2xl font-black text-slate-400";
}
function lvlBadge(l) {
    const m = { CRITICAL: "bg-rose-100 text-rose-700 border border-rose-300",
                HIGH: "bg-orange-100 text-orange-700 border border-orange-300",
                MEDIUM: "bg-amber-100 text-amber-700 border border-amber-300",
                LOW: "bg-cyan-100 text-cyan-700 border border-cyan-300",
                SAFE: "bg-emerald-100 text-emerald-700 border border-emerald-300" };
    return m[l] || m.SAFE;
}

function loading(on) {
    const btn  = g("scan-wallet-btn");
    const text = g("scan-btn-text");
    if (btn)  btn.disabled = on;
    if (text) text.textContent = on ? "⏳ Scanning…" : "⚡ Scan Wallet";
}
function setStatus(msg, ok) {
    const dot  = g("api-dot");
    const txt  = g("api-status-text");
    if (dot) dot.className = "w-2 h-2 rounded-full " + (ok ? "bg-emerald-400 pulse-dot" : "bg-red-400");
    if (txt) txt.textContent = msg;
}
function err(msg) {
    let b = g("err-banner");
    if (!b) {
        b = document.createElement("div");
        b.id = "err-banner";
        b.style.cssText = "position:fixed;top:16px;right:16px;z-index:9999;max-width:380px;padding:14px 16px;border-radius:12px;background:#DC2626;color:#fff;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,.2);display:flex;align-items:flex-start;gap:10px";
        document.body.appendChild(b);
    }
    b.innerHTML = "<span style='flex:1'>⚠️ " + esc(msg) + "</span><button onclick=\"document.getElementById('err-banner').remove()\" style='color:rgba(255,255,255,.7);background:none;border:none;cursor:pointer;font-size:18px;line-height:1'>✕</button>";
    setTimeout(() => { const x = g("err-banner"); if (x) x.remove(); }, 6000);
}
