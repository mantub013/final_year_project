"""
src/ingestion/live_poller.py
============================
Real-time blockchain transaction poller and streaming ingestion engine.
Uses Web3.py RPC + Etherscan / Blockscout API v1/v2 to pull new blocks/transactions
and stream them into the feature engineering and ML prediction pipeline.
"""

import time
import threading
import requests
from typing import Dict, Any, List, Optional, Callable
from src.utils import get_logger, load_yaml
from src.feature_engineering import generate_all_features

logger = get_logger()

class LiveBlockchainPoller:
    """
    Asynchronous / background thread poller that monitors a specific wallet address
    or latest blocks on Ethereum, Polygon, BSC, or Arbitrum.
    """
    def __init__(
        self,
        chain: str = "ethereum",
        poll_interval_seconds: float = 6.0,
        on_transaction_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.chain = chain.lower()
        self.poll_interval = poll_interval_seconds
        self.callback = on_transaction_callback
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.seen_tx_hashes = set()
        
        # Explorer mapping
        self.api_endpoints = {
            "ethereum": "https://eth.blockscout.com/api",
            "polygon": "https://polygon.blockscout.com/api",
            "arbitrum": "https://arbitrum.blockscout.com/api",
            "bsc": "https://bsc.blockscout.com/api"
        }

    def fetch_recent_transactions(self, address: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Queries Blockscout / Etherscan API for real confirmed transactions of the target wallet.
        """
        base_url = self.api_endpoints.get(self.chain, self.api_endpoints["ethereum"])
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "page": 1,
            "offset": limit,
            "sort": "desc"
        }
        
        try:
            resp = requests.get(base_url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "1" or data.get("message") == "OK":
                    return data.get("result", [])
        except Exception as e:
            logger.warning(f"[LivePoller] Failed to query {self.chain} API: {e}")
            
        return []

    def poll_wallet(self, address: str, max_iterations: Optional[int] = None):
        """
        Polls for new transactions on a target address and fires callback when new transactions land.
        """
        logger.info(f"[LivePoller] Monitoring real-time transactions for {address} on {self.chain} (interval: {self.poll_interval}s)...")
        self.is_running = True
        iterations = 0
        
        while self.is_running:
            try:
                txs = self.fetch_recent_transactions(address, limit=10)
                new_txs = []
                for tx in txs:
                    h = tx.get("hash") or tx.get("transaction_id")
                    if h and h not in self.seen_tx_hashes:
                        self.seen_tx_hashes.add(h)
                        new_txs.append(tx)
                
                if new_txs:
                    logger.info(f"[LivePoller] ⚡ Found {len(new_txs)} NEW transactions for {address[:10]}...")
                    for ntx in new_txs:
                        if self.callback:
                            self.callback({
                                "chain": self.chain,
                                "monitored_wallet": address,
                                "transaction": ntx,
                                "detected_at": time.time()
                            })
                            
            except Exception as e:
                logger.error(f"[LivePoller] Polling cycle error: {e}")
                
            iterations += 1
            if max_iterations and iterations >= max_iterations:
                break
                
            time.sleep(self.poll_interval)

    def start_background(self, address: str):
        """Starts poller in a daemon background thread."""
        self._thread = threading.Thread(target=self.poll_wallet, args=(address,), daemon=True)
        self._thread.start()
        logger.info(f"[LivePoller] Background listener thread spawned for {address}.")

    def stop(self):
        """Signals poller thread to terminate."""
        self.is_running = False
        logger.info("[LivePoller] Stopped live listener.")

if __name__ == "__main__":
    def sample_handler(event):
        print(f"--> EVENT: Tx {event['transaction'].get('hash')[:16]} on {event['chain']}")
        
    poller = LiveBlockchainPoller(chain="ethereum", poll_interval_seconds=3.0, on_transaction_callback=sample_handler)
    # Test on Vitalik wallet for 1 iteration
    txs = poller.fetch_recent_transactions("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", limit=5)
    print(f"Fetched {len(txs)} real live txs successfully.")
