"""
blockchain_api.py — Blockchain data adapter with deterministic, realistic mock data.

Each wallet address produces consistent, reproducible on-chain data seeded from
its address hash, ensuring the ML pipeline sees meaningful variance across wallets.
High-risk addresses (containing 'bad', 'dead', 'scam') always produce high-risk features.
"""
import hashlib
import random
import time
from typing import Dict, Any, List
from src.utils import get_logger, is_valid_address

logger = get_logger()

# ── Known high-risk address patterns ──────────────────────────────────────────
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


class BlockchainAPIAdapter:
    """
    Produces deterministic, realistic mock blockchain data.
    Risk tier (high/medium/low) is derived from address pattern so that
    the ML models receive meaningfully differentiated feature vectors.
    """

    def __init__(self, chain: str, config: Dict[str, Any], cmc_api_key: str = ""):
        self.chain       = chain.lower()
        self.config      = config
        self.cmc_api_key = cmc_api_key
        self._tier       = None   # lazy, per-address

    def _get_tier(self, address: str) -> str:
        return _risk_tier(address)

    # ── Balance ────────────────────────────────────────────────────────────────
    def get_wallet_balance(self, address: str) -> float:
        if not is_valid_address(address):
            return 0.0
        tier = self._get_tier(address)
        rng  = random.Random(_seed(address))
        if tier == "high":
            # High-risk: either nearly empty (drained) or suspiciously large
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
