"""
src/stream_listener_tron.py — Real-time Streaming Listener & Kafka Producer for TRC-20 USDT Transfers.

Supports:
1. Bitquery WebSocket subscription (`wss://streaming.bitquery.io/graphql`) for live TRC-20 transfers.
2. Polling TronGrid API as fallback mechanism.
3. Pydantic validation of transaction payloads before publishing to Kafka topic 'tron-usdt-tx-stream'.
"""

import os
import json
import time
import random
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict

from src.utils import get_logger, ensure_dirs, load_yaml
from src.blockchain_api_tron import TronDataFetcher, USDT_TRON_CONTRACT

logger = get_logger()

KAFKA_TOPIC_TRON = "tron-usdt-tx-stream"
BITQUERY_WS_URL = "wss://streaming.bitquery.io/graphql"

# Predefined TRON addresses for simulation & fallback stream polling
TRON_SAMPLE_ADDRESSES = [
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # Tether Treasury / Contract
    "TNPeeaaTK7v3QGiBBWnWNFUzhMHucEjm84",
    "TL1rV5hB1YtZJp3Vj73t9728j928374930",
    "TX81920392817392817392019283716254",
    "TY00000000000000000000000000000bad",
    "TK987654321098765432109876543210fe",
]


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC STREAM PAYLOAD MODEL
# ══════════════════════════════════════════════════════════════════════════════

class TronStreamTxPayload(BaseModel):
    """
    Validated Pydantic transaction payload pushed to Kafka topic 'tron-usdt-tx-stream'.
    """
    tx_hash: str
    block_timestamp: int
    from_address: str
    to_address: str
    amount_usdt: float = Field(..., ge=0.0)
    contract_address: str = USDT_TRON_CONTRACT
    token_symbol: str = "USDT"
    chain: str = "tron"
    ingested_at: int = Field(default_factory=lambda: int(time.time()))

    model_config = ConfigDict(extra="ignore")


# ══════════════════════════════════════════════════════════════════════════════
# KAFKA PRODUCER SKELETON
# ══════════════════════════════════════════════════════════════════════════════

class TronKafkaProducer:
    """
    Kafka Producer wrapper for sending validated TRC-20 transfer payloads.
    Attempts to import kafka-python or confluent_kafka, defaulting to standalone logging mode if Kafka is offline.
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = KAFKA_TOPIC_TRON):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", bootstrap_servers)
        self.topic = topic
        self.producer = None
        self._init_producer()

    def _init_producer(self):
        """Initializes Kafka producer connection with graceful fallback."""
        try:
            from kafka import KafkaProducer  # type: ignore
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=5000,
            )
            logger.info(f"[TronKafkaProducer] Connected to Kafka broker at {self.bootstrap_servers}")
        except Exception as e:
            logger.info(
                f"[TronKafkaProducer] Kafka broker unavailable ({str(e)}). "
                f"Operating in Standalone / Mock Logging Mode."
            )
            self.producer = None

    def publish_transfer_event(self, payload: TronStreamTxPayload) -> bool:
        """
        Validates payload and publishes to Kafka topic 'tron-usdt-tx-stream'.
        """
        event_dict = payload.model_dump()

        if self.producer:
            try:
                self.producer.send(self.topic, event_dict)
                logger.info(f"[Kafka:{self.topic}] Published tx {payload.tx_hash[:12]}... ({payload.amount_usdt} USDT)")
                return True
            except Exception as e:
                logger.error(f"[Kafka:{self.topic}] Failed to produce message: {str(e)}")
                return False
        else:
            logger.info(
                f"[MockKafkaStream:{self.topic}] Event: {payload.from_address[:8]}... -> {payload.to_address[:8]}... "
                f"| Amount: ${payload.amount_usdt:.2f} USDT | Hash: {payload.tx_hash[:12]}..."
            )
            return True


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET & POLLING SUBSCRIBER IMPLEMENTATION
# ══════════════════════════════════════════════════════════════════════════════

class TronStreamListener:
    """
    Streaming listener that connects to Bitquery WebSocket subscriptions or polls TronGrid REST API.
    Pushes events to Kafka topic after Pydantic validation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, kafka_servers: str = "localhost:9092"):
        self.config = config or {}
        self.fetcher = TronDataFetcher(self.config)
        self.kafka_producer = TronKafkaProducer(bootstrap_servers=kafka_servers)
        self.topic = KAFKA_TOPIC_TRON
        self.bitquery_token = self.fetcher.bitquery_bearer_token

    async def listen_bitquery_websocket(self, max_events: Optional[int] = None):
        """
        Listens for real-time TRC-20 USDT transfers using Bitquery's WebSocket subscriptions (`wss://streaming.bitquery.io/graphql`).
        Includes exponential backoff reconnection logic.
        """
        try:
            import websockets
        except ImportError:
            logger.warning("[TronStreamListener] 'websockets' library not installed. Falling back to polling mode.")
            return

        ws_url = BITQUERY_WS_URL
        headers = {}
        if self.bitquery_token:
            headers["Authorization"] = f"Bearer {self.bitquery_token}"

        subscription_query = {
            "type": "start",
            "payload": {
                "query": """
                subscription {
                  Tron {
                    Transfers(
                      where: {
                        Currency: { SmartContract: { is: "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t" } }
                      }
                    ) {
                      Transfer {
                        Sender
                        Receiver
                        Amount
                      }
                      Transaction {
                        Hash
                      }
                      Block {
                        Time
                      }
                    }
                  }
                }
                """
            }
        }

        backoff = 1.0
        event_count = 0

        while True:
            try:
                logger.info(f"[TronStreamListener] Connecting to Bitquery WebSocket: {ws_url}...")
                async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                    logger.info("[TronStreamListener] WebSocket connected! Subscribing to TRC-20 transfers...")
                    await websocket.send(json.dumps(subscription_query))
                    backoff = 1.0  # Reset backoff on success

                    while True:
                        msg = await websocket.recv()
                        data = json.loads(msg)

                        # Extract payload
                        transfers = data.get("payload", {}).get("data", {}).get("Tron", {}).get("Transfers", [])
                        for item in transfers:
                            t = item.get("Transfer", {})
                            payload = TronStreamTxPayload(
                                tx_hash=item.get("Transaction", {}).get("Hash", f"tx_{random.getrandbits(64)}"),
                                block_timestamp=int(time.time() * 1000),
                                from_address=t.get("Sender", ""),
                                to_address=t.get("Receiver", ""),
                                amount_usdt=float(t.get("Amount", 0.0)),
                            )
                            self.kafka_producer.publish_transfer_event(payload)
                            event_count += 1
                            if max_events and event_count >= max_events:
                                return

            except Exception as e:
                logger.warning(f"[TronStreamListener] WebSocket connection error: {str(e)}. Reconnecting in {backoff:.2f}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 60.0)

    def poll_trongrid_stream(self, interval_sec: float = 3.0, run_once: bool = False, max_loops: Optional[int] = None):
        """
        Polls TronGrid or active sample addresses periodically as fallback to simulate real-time ingestion.
        """
        logger.info(f"[TronStreamListener] Starting REST polling loop (interval={interval_sec}s)...")
        loop_cnt = 0

        while True:
            loop_cnt += 1
            sample_wallet = random.choice(TRON_SAMPLE_ADDRESSES)

            try:
                # Fetch recent transfers for selected wallet
                transfers = self.fetcher.get_recent_transfers(sample_wallet, limit=5)

                if transfers:
                    raw_tx = random.choice(transfers)
                    payload = TronStreamTxPayload(
                        tx_hash=raw_tx.get("transaction_id", f"0x{random.getrandbits(256):064x}"),
                        block_timestamp=raw_tx.get("block_timestamp", int(time.time() * 1000)),
                        from_address=raw_tx.get("from_address", sample_wallet),
                        to_address=raw_tx.get("to_address", "TNPeeaaTK7v3QGiBBWnWNFUzhMHucEjm84"),
                        amount_usdt=raw_tx.get("amount_usdt", round(random.uniform(10.0, 5000.0), 2)),
                    )
                else:
                    # Synthetic stream payload fallback
                    payload = TronStreamTxPayload(
                        tx_hash=f"0x{random.getrandbits(256):064x}",
                        block_timestamp=int(time.time() * 1000),
                        from_address=sample_wallet,
                        to_address=random.choice(TRON_SAMPLE_ADDRESSES),
                        amount_usdt=round(random.uniform(5.0, 10000.0), 2),
                    )

                self.kafka_producer.publish_transfer_event(payload)

            except Exception as exc:
                logger.error(f"[TronStreamListener] Polling exception: {str(exc)}")

            if run_once or (max_loops and loop_cnt >= max_loops):
                break

            time.sleep(interval_sec + random.uniform(0.1, 0.5))


def run_stream_listener_tron(run_once: bool = False):
    """Main entry point to start the Tron real-time streaming pipeline."""
    chains_cfg = load_yaml("config/chains.yaml")
    listener = TronStreamListener(config=chains_cfg)
    listener.poll_trongrid_stream(interval_sec=3.0, run_once=run_once)


if __name__ == "__main__":
    run_stream_listener_tron(run_once=False)
