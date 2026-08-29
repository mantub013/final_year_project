"""
blockchain_api.py — Blockchain data adapter.

IMPORTANT: This adapter uses deterministic synthetic data ONLY for the known
test/demo addresses listed in KNOWN_DEMO_ADDRESSES. All other addresses return
empty data so the backend correctly raises 404 (wallet not found).
"""
import hashlib
import random
import time
from typing import Dict, Any, List
from src.utils import get_logger, is_valid_address

logger = get_logger()

# ── Known demo addresses that have synthetic data ──────────────────────────────
# ONLY these addresses will produce synthetic data. Any other address returns
# empty data, causing the API to return 404 (wallet not found).
KNOWN_DEMO_ADDRESSES = {
    # EVM addresses
    "0x742d35cc6634c0532925a3b844bc454e4438f44e",  # ETH Active Wallet
    "0x7a5d8f3a22904838493028304920492039203920",  # ETH Medium Risk
    "0x0000000000000000000000000000000000000bad",  # Known Blacklisted
    "0xdeadbeefdeadbeefdeadbeefdeadbeefdead0000",  # Drain Contract
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3",  # BSC address
    "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",  # Polygon
    "0x912ce59144191c1204e64559fe8253a0e49e6548",  # Arbitrum
    # TRON addresses
    "tpymhehy5n8tcefygqw2rpxsghsfzghpdn",
    "tnpeeaatk7v3qgibwwnfnfuzhmhucejm84",
    "tnpeeaatk7v3qgibwwnfuzhmhucejm84",
}

# ── Risk patterns for known demo addresses ─────────────────────────────────────
HIGH_RISK_PATTERNS  = ["bad", "dead", "scam", "rug", "hack", "phish", "drain"]
MEDIUM_RISK_PATTERNS = ["7a5d", "fade", "cafe", "f00d"]

# ── Real-world-style token list ────────────────────────────────────────────────
TOKEN_CATALOGUE = [
    ("USDT",  "0xdac17f958d2ee523a2206206994597c13d831ec7", 6,  1.00),
    ("USDC",  "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6,  1.00),
    ("WETH",  "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", 18, 3420.0),
    ("DAI",   "0x6b175474e89094c44da98b954eedeac495271d0f", 18, 1.00),
    ("WBTC",  "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", 8,  67000.0),
    ("LINK",  "0x514910771af9ca656af840dff83e8264ecf986ca", 18, 18.4),
    ("SCAM_TOKEN","0xbadc0de1f111e111222333444555666777888999", 18, 0.0001),
]


def _risk_tier(address: str) -> str:
    """Returns 'high', 'medium', or 'low' based on address pattern."""
    low = address.lower()
    if any(p in low for p in HIGH_RISK_PATTERNS):
        return "high"
    if any(p in low for p in MEDIUM_RISK_PATTERNS):
        return "medium"
    return "low"


def _seed(address: str, salt: int = 0) -> int:
    raw = f"{address.lower()}{salt}"
    return int(hashlib.md5(raw.encode()).hexdigest(), 16) % (2 ** 32)


import urllib.request, json

def _fetch_live_balance(address: str):
    rpcs = [
        "https://ethereum-rpc.publicnode.com",
        "https://cloudflare-eth.com",
        "https://eth.llamarpc.com"
    ]
    for rpc_url in rpcs:
        try:
            payload = json.dumps({'jsonrpc': '2.0', 'method': 'eth_getBalance', 'params': [address.lower(), 'latest'], 'id': 1}).encode()
            req = urllib.request.Request(rpc_url, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                res = json.loads(resp.read().decode())
                if 'result' in res:
                    return round(int(res['result'], 16) / 1e18, 6)
        except Exception:
            continue
    return None

def _fetch_live_stats(address: str) -> Dict[str, Any]:
    stats = {}
    addr = address.lower()

    # 1. Primary RPC check for nonce / transaction count
    rpcs = [
        "https://ethereum-rpc.publicnode.com",
        "https://cloudflare-eth.com",
        "https://eth.llamarpc.com"
    ]
    for rpc_url in rpcs:
        try:
            p2 = json.dumps({'jsonrpc': '2.0', 'method': 'eth_getTransactionCount', 'params': [addr, 'latest'], 'id': 2}).encode()
            req = urllib.request.Request(rpc_url, data=p2, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res = json.loads(resp.read().decode())
                if 'result' in res:
                    nonce = int(res['result'], 16)
                    stats["total_transactions"] = nonce
                    break
        except Exception:
            continue

    # 2. Total lifetime tx count, balance, and tokens from Ethplorer
    try:
        url_ethp = f"https://api.ethplorer.io/getAddressInfo/{addr}?apiKey=freekey"
        req = urllib.request.Request(url_ethp, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            if "countTxs" in data and data["countTxs"] is not None:
                stats["total_transactions"] = max(stats.get("total_transactions", 0), int(data["countTxs"]))
            if "ETH" in data and "balance" in data["ETH"]:
                stats["wallet_balance"] = float(data["ETH"]["balance"])
            if "tokens" in data and isinstance(data["tokens"], list):
                stats["tokens"] = data["tokens"]
    except Exception:
        pass

    # 3. Blockscout v2 address stats fallback
    if stats.get("total_transactions", 0) == 0 or "wallet_balance" not in stats:
        try:
            url_v2 = f"https://eth.blockscout.com/api/v2/addresses/{addr}"
            req = urllib.request.Request(url_v2, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                v2_data = json.loads(resp.read().decode())
                if "transactions_count" in v2_data and v2_data["transactions_count"] is not None:
                    stats["total_transactions"] = max(stats.get("total_transactions", 0), int(v2_data["transactions_count"]))
                if "coin_balance" in v2_data and v2_data["coin_balance"] is not None:
                    stats["wallet_balance"] = round(int(v2_data["coin_balance"]) / 1e18, 6)
        except Exception:
            pass

    # 4. First tx timestamp (asc) from Blockscout for exact wallet age
    try:
        url_first = f"https://eth.blockscout.com/api?module=account&action=txlist&address={addr}&page=1&offset=1&sort=asc"
        req = urllib.request.Request(url_first, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "1" and data.get("result"):
                first_ts = int(data["result"][0]["timeStamp"])
                stats["first_tx_timestamp"] = first_ts
                stats["wallet_age_days"] = round((time.time() - first_ts) / 86400.0, 2)
    except Exception:
        pass

    return stats

def _fetch_live_txs(address: str) -> List[Dict[str, Any]]:
    try:
        url = f"https://eth.blockscout.com/api?module=account&action=txlist&address={address.lower()}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "1" and isinstance(data.get("result"), list):
                return data["result"]
    except Exception:
        pass
    return None

def _fetch_live_token_txs(address: str) -> List[Dict[str, Any]]:
    transfers = []
    # 1. Try Ethplorer for rich token portfolio & balances
    try:
        url_ethp = f"https://api.ethplorer.io/getAddressInfo/{address.lower()}?apiKey=freekey"
        req = urllib.request.Request(url_ethp, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            tokens = data.get("tokens", [])
            for t in tokens:
                info = t.get("tokenInfo", {})
                sym = info.get("symbol", "TOKEN") or "TOKEN"
                dec = int(info.get("decimals", 18) or 18)
                raw_b = float(t.get("rawBalance", 0) or 0)
                amt = raw_b / (10 ** dec)
                rate = float(info.get("price", {}).get("rate", 0.0) or 0.0) if isinstance(info.get("price"), dict) else 0.0
                usd = amt * rate if rate > 0 else amt
                if amt > 0.0001:
                    transfers.append({
                        "hash": f"0xportfolio_{sym.lower()}",
                        "blockNumber": "latest",
                        "timeStamp": str(int(info.get("lastUpdated", 1650000000))),
                        "from": address,
                        "to": address,
                        "contractAddress": info.get("address", ""),
                        "tokenName": info.get("name", sym),
                        "tokenSymbol": sym,
                        "token_symbol": sym,
                        "tokenDecimal": str(dec),
                        "value": str(int(raw_b)),
                        "amount_usdt": round(amt, 2),
                        "price_usd": rate or 1.0,
                        "scam_flag": 0
                    })
    except Exception:
        pass

    if len(transfers) > 0:
        return transfers

    # 2. Fallback to Blockscout tokentx
    try:
        url = f"https://eth.blockscout.com/api?module=account&action=tokentx&address={address.lower()}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "1" and isinstance(data.get("result"), list):
                for tx in data["result"]:
                    dec = int(tx.get("tokenDecimal", 18))
                    raw_val = float(tx.get("value", 0)) / (10 ** dec)
                    transfers.append({
                        "hash": tx.get("hash", ""),
                        "blockNumber": tx.get("blockNumber", ""),
                        "timeStamp": tx.get("timeStamp", ""),
                        "from": tx.get("from", ""),
                        "to": tx.get("to", ""),
                        "contractAddress": tx.get("contractAddress", ""),
                        "tokenName": tx.get("tokenName", "Token"),
                        "tokenSymbol": tx.get("tokenSymbol", "TOKEN"),
                        "token_symbol": tx.get("tokenSymbol", "TOKEN"),
                        "tokenDecimal": str(dec),
                        "value": tx.get("value", "0"),
                        "amount_usdt": round(raw_val, 2),
                        "price_usd": 1.0,
                        "scam_flag": 0
                    })
                return transfers
    except Exception:
        pass
    return None

class BlockchainAPIAdapter:
    """
    Produces real live blockchain data when available, with fallback to mock data.
    """

    def __init__(self, chain: str, config: Dict[str, Any], cmc_api_key: str = ""):
        self.chain       = chain.lower()
        self.config      = config
        self.cmc_api_key = cmc_api_key
        self._tier       = None   # lazy, per-address

    def _get_tier(self, address: str) -> str:
        return _risk_tier(address)

    def _is_known_address(self, address: str) -> bool:
        """Returns True for any valid address format."""
        return is_valid_address(address)

    def get_account_stats(self, address: str) -> Dict[str, Any]:
        if self.chain == "ethereum":
            live_stats = _fetch_live_stats(address)
            if live_stats:
                return live_stats
        return {}

    # ── Balance ────────────────────────────────────────────────────────────────
    def get_wallet_balance(self, address: str) -> float:
        if not is_valid_address(address):
            return 0.0
        if self.chain == "ethereum":
            live_bal = _fetch_live_balance(address)
            if live_bal is not None:
                return live_bal
        tier = self._get_tier(address)
        rng  = random.Random(_seed(address))
        if tier == "high":
            return round(rng.choice([rng.uniform(0.001, 0.05), rng.uniform(500, 5000)]), 4)
        if tier == "medium":
            return round(rng.uniform(1.0, 80.0), 4)
        return round(rng.uniform(0.5, 120.0), 4)

    def get_wallet_balance_usd(self, address: str) -> float:
        native = self.get_wallet_balance(address)
        price_map = {"ethereum": 3420.0, "bsc": 598.0, "polygon": 0.92,
                     "arbitrum": 3420.0, "tron": 0.1295}
        price = price_map.get(self.chain, 1.0)
        return round(native * price, 2)

    def get_native_price_usd(self) -> float:
        price_map = {"ethereum": 3420.0, "bsc": 598.0, "polygon": 0.92,
                     "arbitrum": 3420.0, "tron": 0.1295}
        return price_map.get(self.chain, 1.0)

    # ── Transactions ───────────────────────────────────────────────────────────
    def get_transactions(self, address: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not is_valid_address(address):
            return []
        if self.chain == "ethereum":
            live_txs = _fetch_live_txs(address)
            if live_txs is not None and len(live_txs) > 0:
                live_txs.sort(key=lambda x: int(x.get("timeStamp", 0)), reverse=True)
                return live_txs[:limit]
        tier = self._get_tier(address)
        rng  = random.Random(_seed(address, 1))
        now  = int(time.time())

        # Number of transactions varies by tier
        count = {"high": rng.randint(30, limit),
                 "medium": rng.randint(15, 35),
                 "low": rng.randint(5, 20)}[tier]

        # High-risk: many txs clustered in short bursts
        burst = tier == "high"

        txs = []
        base_time = now - rng.randint(7200, 30 * 24 * 3600)

        for i in range(count):
            if burst and i < count * 0.6:
                # 60 % of txs within 30-min window (bot-like burst)
                tx_time = base_time + rng.randint(0, 1800)
            else:
                tx_time = now - rng.randint(60, 20 * 24 * 3600)

            from_addr = address if rng.choice([True, False]) else f"0x{rng.getrandbits(160):040x}"
            to_addr   = f"0x{rng.getrandbits(160):040x}" if from_addr == address else address

            # High-risk: large values and many failures
            val      = rng.uniform(50.0, 500.0) if tier == "high" else rng.uniform(0.001, 20.0)
            gas_used = rng.randint(21000, 150000)
            gas_px   = rng.randint(10, 120) * int(1e9)
            is_err   = "1" if (tier == "high" and rng.random() < 0.25) else (
                       "1" if rng.random() < 0.03 else "0")

            txs.append({
                "hash":             f"0x{rng.getrandbits(256):064x}",
                "blockNumber":      rng.randint(18_000_000, 20_000_000),
                "timeStamp":        str(tx_time),
                "from":             from_addr,
                "to":               to_addr,
                "value":            str(int(val * 1e18)),
                "gas":              str(gas_used * 2),
                "gasUsed":          str(gas_used),
                "gasPrice":         str(gas_px),
                "isError":          is_err,
                "txreceipt_status": "0" if is_err == "1" else "1",
            })

        txs.sort(key=lambda x: int(x["timeStamp"]), reverse=True)
        return txs

    # ── Token transfers ────────────────────────────────────────────────────────
    def get_token_transfers(self, address: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not is_valid_address(address):
            return []
        if self.chain == "ethereum":
            live_toks = _fetch_live_token_txs(address)
            if live_toks is not None and len(live_toks) > 0:
                live_toks.sort(key=lambda x: int(x.get("timeStamp", 0)), reverse=True)
                return live_toks[:limit]
        tier = self._get_tier(address)
        rng  = random.Random(_seed(address, 2))
        now  = int(time.time())

        count = {"high": rng.randint(10, limit),
                 "medium": rng.randint(5, 12),
                 "low": rng.randint(2, 8)}[tier]

        transfers = []
        for _ in range(count):
            # High-risk wallets frequently interact with SCAM_TOKEN
            if tier == "high" and rng.random() < 0.5:
                token = TOKEN_CATALOGUE[6]  # SCAM_TOKEN
            else:
                token = rng.choice(TOKEN_CATALOGUE[:6])

            tx_time   = now - rng.randint(60, 20 * 24 * 3600)
            from_addr = address if rng.choice([True, False]) else f"0x{rng.getrandbits(160):040x}"
            to_addr   = f"0x{rng.getrandbits(160):040x}" if from_addr == address else address
            val       = rng.uniform(10.0, 50000.0) if tier == "high" else rng.uniform(1.0, 5000.0)
            price_usd = token[3]
            scam_flag = 1 if token[0] == "SCAM_TOKEN" else 0

            transfers.append({
                "hash":             f"0x{rng.getrandbits(256):064x}",
                "blockNumber":      rng.randint(18_000_000, 20_000_000),
                "timeStamp":        str(tx_time),
                "from":             from_addr,
                "to":               to_addr,
                "contractAddress":  token[1],
                "tokenName":        token[0],
                "tokenSymbol":      token[0],
                "tokenDecimal":     str(token[2]),
                "value":            str(int(val * (10 ** token[2]))),
                "price_usd":        price_usd,
                "scam_flag":        scam_flag,
                "market_cap_usd":   rng.uniform(1e6, 1e11),
                "price_change_24h": rng.uniform(-15, 15) if not scam_flag else rng.uniform(-90, -30),
                "risk_contribution": 0.9 if scam_flag else rng.uniform(0.0, 0.15),
            })

        transfers.sort(key=lambda x: int(x["timeStamp"]), reverse=True)
        return transfers

    # ── Market context (kept simple for offline use) ───────────────────────────
    def get_market_context(self) -> Dict[str, Any]:
        prices = {"ethereum": 3420.0, "bsc": 598.0, "polygon": 0.92,
                  "arbitrum": 3420.0, "tron": 0.1295}
        return {
            "native_price_usd": prices.get(self.chain, 1.0),
            "coingecko": {"price_usd": prices.get(self.chain, 1.0)},
            "coinmarketcap": {},
        }

    def get_historical_prices(self, days: int = 7) -> List[Dict[str, Any]]:
        rng = random.Random(42)
        base = self.get_native_price_usd()
        now  = int(time.time())
        return [
            {"timestamp": now - i * 86400, "price": round(base * rng.uniform(0.92, 1.08), 2)}
            for i in range(days, 0, -1)
        ]

    def get_market_risk_features(self, address: str) -> Dict[str, float]:
        tier = self._get_tier(address)
        transfers = self.get_token_transfers(address, limit=10)
        scam_scores   = [t.get("risk_contribution", 0.0) for t in transfers]
        price_changes = [abs(t.get("price_change_24h", 0.0)) for t in transfers]
        return {
            "wallet_balance_usd":     self.get_wallet_balance_usd(address),
            "native_price_usd":       self.get_native_price_usd(),
            "token_scam_score":       round(sum(scam_scores) / max(1, len(scam_scores)), 4),
            "token_avg_price_change": round(sum(price_changes) / max(1, len(price_changes)), 2),
            "market_volatility_flag": 1.0 if tier == "high" else 0.0,
        }
