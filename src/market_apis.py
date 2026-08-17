"""
market_apis.py — Real-time market data integration for DeFi Risk Platform.

Priority chain:
  1. CoinGecko  → token prices, scam token metadata, market cap
  2. DIA Data   → fallback oracle prices, historical OHLC
  3. CoinMarketCap → global market context (symbol-based)

All methods degrade gracefully: if a live API call fails, a safe
default value is returned so the rest of the prediction pipeline
is never blocked.
"""

import time
import requests
from typing import Dict, Any, Optional, List
from src.utils import get_logger

logger = get_logger()

# ── Simple in-process TTL cache to avoid burning free-tier quotas ─────────────
_CACHE: Dict[str, Any] = {}
_CACHE_TS: Dict[str, float] = {}
_CACHE_TTL = 120  # seconds


def _cached(key: str, fn, *args, **kwargs):
    now = time.time()
    if key in _CACHE and (now - _CACHE_TS.get(key, 0)) < _CACHE_TTL:
        return _CACHE[key]
    try:
        result = fn(*args, **kwargs)
        _CACHE[key] = result
        _CACHE_TS[key] = now
        return result
    except Exception as e:
        logger.warning(f"[MarketAPI] Cache miss + error for {key}: {e}")
        return _CACHE.get(key)   # return stale if available


# ═══════════════════════════════════════════════════════════════════════════════
# 1. COINGECKO API
# ═══════════════════════════════════════════════════════════════════════════════
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Maps project chain names → CoinGecko platform IDs
COINGECKO_PLATFORM = {
    "ethereum": "ethereum",
    "bsc":      "binance-smart-chain",
    "polygon":  "polygon-pos",
    "arbitrum": "arbitrum-one",
}

# Known scam/rug-pull contract addresses flagged by CoinGecko community
KNOWN_SCAM_CONTRACTS = {
    "0xbadc0de1f111e111222333444555666777888999",  # project mock scam token
}


def coingecko_token_price(token_address: str, chain: str) -> float:
    """
    Returns the USD price of a token contract on the given chain.
    Falls back to 0.0 on error.
    """
    platform = COINGECKO_PLATFORM.get(chain.lower(), "ethereum")
    key = f"cg_price_{platform}_{token_address.lower()}"

    def _fetch():
        url = f"{COINGECKO_BASE}/simple/token_price/{platform}"
        params = {"contract_addresses": token_address.lower(), "vs_currencies": "usd"}
        resp = requests.get(url, params=params, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        return float(data.get(token_address.lower(), {}).get("usd", 0.0))

    return _cached(key, _fetch) or 0.0


def coingecko_native_price(chain: str) -> float:
    """
    Returns the USD price of the chain's native token (ETH/BNB/MATIC/ETH on Arb).
    """
    coin_id_map = {
        "ethereum": "ethereum",
        "bsc":      "binancecoin",
        "polygon":  "matic-network",
        "arbitrum": "ethereum",
    }
    coin_id = coin_id_map.get(chain.lower(), "ethereum")
    key = f"cg_native_{coin_id}"

    def _fetch():
        url = f"{COINGECKO_BASE}/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}
        resp = requests.get(url, params=params, timeout=6)
        resp.raise_for_status()
        return float(resp.json().get(coin_id, {}).get("usd", 0.0))

    return _cached(key, _fetch) or 0.0


def coingecko_token_metadata(token_address: str, chain: str) -> Dict[str, Any]:
    """
    Returns metadata for a token: name, symbol, market_cap, total_volume,
    price_change_24h, and a scam_flag heuristic.

    Used to identify scam/rug-pull tokens in the feature pipeline.
    """
    platform = COINGECKO_PLATFORM.get(chain.lower(), "ethereum")
    key = f"cg_meta_{platform}_{token_address.lower()}"

    def _fetch():
        url = f"{COINGECKO_BASE}/coins/{platform}/contract/{token_address.lower()}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 404:
            # Token not found → treat as suspicious
            return {
                "name": "UNKNOWN",
                "symbol": "???",
                "market_cap_usd": 0.0,
                "volume_24h_usd": 0.0,
                "price_change_24h_pct": 0.0,
                "scam_flag": 1,   # unknown unlisted token → elevated risk
            }
        resp.raise_for_status()
        d = resp.json()
        market_data = d.get("market_data", {})
        mc  = market_data.get("market_cap", {}).get("usd", 0.0) or 0.0
        vol = market_data.get("total_volume", {}).get("usd", 0.0) or 0.0
        chg = market_data.get("price_change_percentage_24h", 0.0) or 0.0

        # Heuristic scam detection:
        # Very low market cap + extreme price swing + no volume = likely rug/scam
        scam_flag = int(
            token_address.lower() in KNOWN_SCAM_CONTRACTS
            or (mc < 50_000 and vol < 1_000)
            or abs(chg) > 80
        )
        return {
            "name": d.get("name", ""),
            "symbol": d.get("symbol", "").upper(),
            "market_cap_usd": mc,
            "volume_24h_usd": vol,
            "price_change_24h_pct": chg,
            "scam_flag": scam_flag,
        }

    result = _cached(key, _fetch)
    return result or {"scam_flag": 0, "market_cap_usd": 0.0,
                      "volume_24h_usd": 0.0, "price_change_24h_pct": 0.0}


def coingecko_market_summary(chain: str) -> Dict[str, Any]:
    """
    Returns global market context for the chain's native token:
    market_cap, 24h volume, price change.
    Used in Model Diagnostics and as a risk multiplier.
    """
    coin_id_map = {
        "ethereum": "ethereum",
        "bsc":      "binancecoin",
        "polygon":  "matic-network",
        "arbitrum": "ethereum",
    }
    coin_id = coin_id_map.get(chain.lower(), "ethereum")
    key = f"cg_summary_{coin_id}"

    def _fetch():
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
        }
        resp = requests.get(url, params=params, timeout=6)
        resp.raise_for_status()
        items = resp.json()
        if not items:
            return {}
        item = items[0]
        return {
            "symbol":               item.get("symbol", "").upper(),
            "current_price_usd":    item.get("current_price", 0.0),
            "market_cap_usd":       item.get("market_cap", 0.0),
            "volume_24h_usd":       item.get("total_volume", 0.0),
            "price_change_24h_pct": item.get("price_change_percentage_24h", 0.0),
            "high_24h_usd":         item.get("high_24h", 0.0),
            "low_24h_usd":          item.get("low_24h", 0.0),
        }

    return _cached(key, _fetch) or {}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DIA DATA API  (fallback / backup oracle)
# ═══════════════════════════════════════════════════════════════════════════════
DIA_BASE = "https://api.diadata.org/v1"

DIA_SYMBOL_MAP = {
    "ethereum": "ETH",
    "bsc":      "BNB",
    "polygon":  "MATIC",
    "arbitrum": "ETH",
}


def dia_native_price(chain: str) -> float:
    """
    Returns USD price of chain native token via DIA oracle.
    Used as fallback when CoinGecko is rate-limited.
    """
    symbol = DIA_SYMBOL_MAP.get(chain.lower(), "ETH")
    key = f"dia_price_{symbol}"

    def _fetch():
        url = f"{DIA_BASE}/assetQuotation/Ethereum/{symbol}"
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        return float(resp.json().get("Price", 0.0))

    return _cached(key, _fetch) or 0.0


def dia_token_price(symbol: str) -> float:
    """Returns price for a known token symbol via DIA (e.g. USDT, USDC, DAI)."""
    key = f"dia_token_{symbol.upper()}"

    def _fetch():
        url = f"{DIA_BASE}/assetQuotation/Ethereum/{symbol.upper()}"
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        return float(resp.json().get("Price", 0.0))

    return _cached(key, _fetch) or 0.0


def dia_historical_prices(symbol: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Returns historical price data from DIA for the Historical Risk Trend chart.
    Returns list of {time, price} dicts.
    """
    key = f"dia_hist_{symbol}_{days}"

    def _fetch():
        end_time   = int(time.time())
        start_time = end_time - days * 86400
        url = f"{DIA_BASE}/chartPoints/MAIR120/{symbol}/USD"
        params = {"starttime": start_time, "endtime": end_time}
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"timestamp": int(p.get("Time", 0)), "price": float(p.get("Value", 0.0))}
            for p in data.get("DataPoints", [])
        ]

    return _cached(key, _fetch) or []


# ═══════════════════════════════════════════════════════════════════════════════
# 3. COINMARKETCAP API  (global market context)
# ═══════════════════════════════════════════════════════════════════════════════
CMC_BASE = "https://pro-api.coinmarketcap.com/v1"
CMC_SYMBOL_MAP = {
    "ethereum": "ETH",
    "bsc":      "BNB",
    "polygon":  "MATIC",
    "arbitrum": "ETH",
}


def cmc_global_metrics(api_key: str, chain: str) -> Dict[str, Any]:
    """
    Returns market rank, market cap dominance, and circulating supply
    from CoinMarketCap for the chain native token.
    Requires a free CMC API key (signup at coinmarketcap.com).
    """
    symbol = CMC_SYMBOL_MAP.get(chain.lower(), "ETH")
    key = f"cmc_metrics_{symbol}"

    def _fetch():
        if not api_key or api_key == "YOUR_CMC_KEY_HERE":
            logger.info("[CMC] No API key provided, skipping.")
            return {}
        url = f"{CMC_BASE}/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
        params = {"symbol": symbol, "convert": "USD"}
        resp = requests.get(url, headers=headers, params=params, timeout=6)
        resp.raise_for_status()
        quote = resp.json()["data"][symbol]["quote"]["USD"]
        return {
            "symbol":              symbol,
            "cmc_rank":            resp.json()["data"][symbol].get("cmc_rank", 0),
            "market_cap_usd":      quote.get("market_cap", 0.0),
            "volume_24h_usd":      quote.get("volume_24h", 0.0),
            "percent_change_24h":  quote.get("percent_change_24h", 0.0),
            "percent_change_7d":   quote.get("percent_change_7d", 0.0),
            "market_cap_dominance": quote.get("market_cap_dominance", 0.0),
        }

    return _cached(key, _fetch) or {}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. UNIFIED FACADE — used by BlockchainAPIAdapter
# ═══════════════════════════════════════════════════════════════════════════════
def get_native_price_usd(chain: str) -> float:
    """
    Gets native token USD price. Tries CoinGecko first, falls back to DIA.
    """
    price = coingecko_native_price(chain)
    if price and price > 0:
        logger.info(f"[MarketAPI] CoinGecko native price for {chain}: ${price}")
        return price
    price = dia_native_price(chain)
    if price and price > 0:
        logger.info(f"[MarketAPI] DIA fallback price for {chain}: ${price}")
        return price
    logger.warning(f"[MarketAPI] Could not fetch price for {chain}, using 0.0")
    return 0.0


def get_wallet_balance_usd(chain: str, balance_native: float) -> float:
    """Converts native balance to USD using real market price."""
    price = get_native_price_usd(chain)
    return round(balance_native * price, 2)


def get_token_risk_signals(
    token_address: str,
    chain: str,
    cmc_key: str = "",
) -> Dict[str, Any]:
    """
    Returns enriched risk signals for a token contract:
    - scam_flag         (0/1) — suspicious token heuristic
    - market_cap_usd    — low cap = higher risk
    - volume_24h_usd    — low volume = illiquid / potential rug
    - price_change_24h  — extreme swings = pump & dump signal
    - price_usd         — current token price

    Aggregates data from CoinGecko + DIA + CMC.
    """
    signals: Dict[str, Any] = {
        "scam_flag":          0,
        "market_cap_usd":     0.0,
        "volume_24h_usd":     0.0,
        "price_change_24h":   0.0,
        "price_usd":          0.0,
        "source":             "none",
    }

    # CoinGecko metadata
    meta = coingecko_token_metadata(token_address, chain)
    if meta:
        signals["scam_flag"]        = meta.get("scam_flag", 0)
        signals["market_cap_usd"]   = meta.get("market_cap_usd", 0.0)
        signals["volume_24h_usd"]   = meta.get("volume_24h_usd", 0.0)
        signals["price_change_24h"] = meta.get("price_change_24h_pct", 0.0)
        signals["source"]           = "coingecko"

    # Token price from CoinGecko
    price = coingecko_token_price(token_address, chain)
    if price > 0:
        signals["price_usd"] = price

    # Derive additional risk score contribution (0.0 – 1.0)
    risk_contribution = 0.0
    if signals["scam_flag"]:
        risk_contribution += 0.50
    if signals["market_cap_usd"] < 100_000:
        risk_contribution += 0.25
    if abs(signals["price_change_24h"]) > 50:
        risk_contribution += 0.15
    if signals["volume_24h_usd"] < 500:
        risk_contribution += 0.10

    signals["risk_contribution"] = round(min(1.0, risk_contribution), 4)
    return signals
