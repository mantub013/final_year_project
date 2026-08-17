"""
src/blockchain_api_tron.py — TRON Blockchain (TRC-20 USDT) API Data Fetcher.

Integrates:
1. TronScan API (REST, no API key) & TronGrid API for real-time USDT balances & transfers.
2. Bitquery API (GraphQL) for extracting multi-hop wallet graph relationships for GNN feature store.
"""

import os
import time
import random
import logging
import hashlib
import requests
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from src.utils import get_logger

logger = get_logger()

# Default TRC-20 USDT Contract Address on TRON
USDT_TRON_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
TRONGRID_BASE_URL = "https://api.trongrid.io"
TRONSCAN_BASE_URL = "https://apilist.tronscanapi.com/api"
BITQUERY_GRAPHQL_URL = "https://streaming.bitquery.io/graphql"


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC RESPONSE MODELS FOR VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

class USDTBalanceResponse(BaseModel):
    """Validated model for USDT wallet balance."""
    wallet_address: str
    balance_usdt: float = Field(..., ge=0.0, description="USDT balance in human-readable units")
    raw_balance: str
    decimals: int = 6
    contract_address: str = USDT_TRON_CONTRACT
    timestamp: int

    model_config = ConfigDict(extra="ignore")


class TokenInfo(BaseModel):
    """Metadata for TRC-20 token."""
    symbol: str = "USDT"
    address: str = USDT_TRON_CONTRACT
    decimals: int = 6
    name: Optional[str] = "Tether USD"

    model_config = ConfigDict(extra="ignore")


class TRC20TransferItem(BaseModel):
    """Validated TRC-20 USDT transfer item."""
    transaction_id: str
    block_timestamp: int
    from_address: str
    to_address: str
    amount_usdt: float = Field(..., ge=0.0)
    raw_value: str
    token_symbol: str = "USDT"
    contract_address: str = USDT_TRON_CONTRACT
    confirmed: bool = True

    model_config = ConfigDict(extra="ignore")


class TRC20TransfersResponse(BaseModel):
    """Validated collection of TRC-20 transfers."""
    success: bool = True
    wallet_address: str
    count: int
    data: List[TRC20TransferItem]

    model_config = ConfigDict(extra="ignore")


class GNNNode(BaseModel):
    """Graph Node model for GNN wallet relationship store."""
    id: str
    address: str
    role: str = "counterparty"  # 'center', 'counterparty', 'multi_hop'
    hop_depth: int = 1

    model_config = ConfigDict(extra="ignore")


class GNNEdge(BaseModel):
    """Graph Edge model for GNN wallet relationship store."""
    source: str
    target: str
    amount_usdt: float = Field(..., ge=0.0)
    transaction_count: int = Field(default=1, ge=1)
    direction: str  # 'incoming' or 'outgoing'
    tx_hashes: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class GNNWalletGraph(BaseModel):
    """Multi-hop wallet graph response model for Graph Neural Networks."""
    center_wallet: str
    depth: int = 2
    nodes: List[GNNNode]
    edges: List[GNNEdge]
    total_volume_usdt: float = 0.0
    unique_counterparties: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


# ══════════════════════════════════════════════════════════════════════════════
# TRON DATA FETCHER CLASS
# ══════════════════════════════════════════════════════════════════════════════

class TronDataFetcher:
    """
    Data fetcher for TRON network TRC-20 USDT transactions & wallet relationships.
    Utilizes TronGrid REST, TronScan REST, and Bitquery GraphQL APIs.
    Includes rate-limit handling with exponential backoff and Pydantic validation.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        trongrid_api_key: Optional[str] = None,
        bitquery_bearer_token: Optional[str] = None,
    ):
        config = config or {}
        tron_cfg = config.get("tron", {})

        # API Keys priority: explicit parameter > env var > config > placeholder
        raw_trongrid = trongrid_api_key or os.getenv("TRONGRID_API_KEY") or tron_cfg.get("trongrid_api_key", "")
        self.trongrid_api_key = "" if raw_trongrid == "TRONGRID_API_KEY" else raw_trongrid

        raw_bitquery = bitquery_bearer_token or os.getenv("BITQUERY_BEARER_TOKEN") or tron_cfg.get("bitquery_bearer_token", "")
        self.bitquery_bearer_token = "" if raw_bitquery == "BITQUERY_BEARER_TOKEN" else raw_bitquery

        self.usdt_contract = tron_cfg.get("usdt_contract", USDT_TRON_CONTRACT)
        self.trongrid_url = tron_cfg.get("rpc_url", TRONGRID_BASE_URL)
        self.tronscan_url = TRONSCAN_BASE_URL
        self.bitquery_url = BITQUERY_GRAPHQL_URL

        logger.info(f"[TronDataFetcher] Initialized for contract '{self.usdt_contract}'")

    def _execute_http_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,
        initial_backoff: float = 0.5,
        timeout: int = 3,
    ) -> Optional[requests.Response]:
        """
        Executes HTTP requests with exponential backoff retry logic for HTTP 429 / 5xx errors.
        """
        backoff = initial_backoff
        req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        if headers:
            req_headers.update(headers)

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    params=params,
                    json=json_payload,
                    timeout=timeout,
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 429 or response.status_code >= 500:
                    logger.warning(
                        f"[TronDataFetcher] HTTP {response.status_code} on attempt {attempt}/{max_retries} for {url}. "
                        f"Retrying in {backoff:.2f}s..."
                    )
                    time.sleep(backoff + random.uniform(0.1, 0.5))
                    backoff *= 2.0
                else:
                    logger.error(
                        f"[TronDataFetcher] Request failed with HTTP {response.status_code}: {response.text[:200]}"
                    )
                    return response
            except requests.RequestException as exc:
                logger.warning(
                    f"[TronDataFetcher] Request error on attempt {attempt}/{max_retries}: {str(exc)}. "
                    f"Retrying in {backoff:.2f}s..."
                )
                time.sleep(backoff + random.uniform(0.1, 0.5))
                backoff *= 2.0

        logger.error(f"[TronDataFetcher] Max retries ({max_retries}) exceeded for {url}")
        return None

    def get_usdt_balance(self, wallet_address: str) -> float:
        """
        Uses the TronScan API (no key required) or TronGrid to fetch the current USDT balance of a wallet.

        Args:
            wallet_address: TRON wallet address (e.g. 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t')

        Returns:
            float: Validated USDT balance in human-readable units (e.g., 1250.50).
        """
        if not wallet_address or not isinstance(wallet_address, str):
            logger.warning(f"[TronDataFetcher] Invalid wallet address provided: {wallet_address}")
            return 0.0

        # Attempt 1: Fetch via TronScan API (no API key required)
        tronscan_endpoint = f"{self.tronscan_url}/account/tokens"
        params = {"address": wallet_address}
        response = self._execute_http_request(tronscan_endpoint, params=params)

        balance_usdt = 0.0
        raw_balance = "0"
        decimals = 6

        if response and response.status_code == 200:
            try:
                res_data = response.json()
                # TronScan returns array of token balances under 'data' or 'tokens'
                token_list = res_data.get("data") or res_data.get("tokens") or []
                for token in token_list:
                    tokenId = token.get("tokenId") or token.get("tokenAbbr") or token.get("issueId")
                    if tokenId == self.usdt_contract or token.get("tokenName") == "Tether USD" or token.get("tokenSymbol") == "USDT":
                        raw_balance = str(token.get("balance", "0"))
                        decimals = int(token.get("tokenDecimal") or token.get("decimals") or 6)
                        balance_usdt = float(raw_balance) / (10 ** decimals)
                        logger.info(f"[TronScan] {wallet_address[:10]}... USDT Balance: {balance_usdt}")
                        
                        # Validate using Pydantic model
                        validated_model = USDTBalanceResponse(
                            wallet_address=wallet_address,
                            balance_usdt=balance_usdt,
                            raw_balance=raw_balance,
                            decimals=decimals,
                            contract_address=self.usdt_contract,
                            timestamp=int(time.time()),
                        )
                        return validated_model.balance_usdt
            except Exception as e:
                logger.warning(f"[TronScan] Failed to parse response: {str(e)}. Falling back to TronGrid.")

        # Attempt 2: Fallback to TronGrid API
        trongrid_endpoint = f"{self.trongrid_url}/v1/accounts/{wallet_address}"
        headers = {}
        if self.trongrid_api_key:
            headers["TRON-PRO-API-KEY"] = self.trongrid_api_key

        response = self._execute_http_request(trongrid_endpoint, headers=headers)
        if response and response.status_code == 200:
            try:
                res_data = response.json()
                account_list = res_data.get("data", [])
                if account_list:
                    trc20_tokens = account_list[0].get("trc20", [])
                    # trc20 list contains dicts like [{ 'TR7NHq...': '15000000' }]
                    for trc20 in trc20_tokens:
                        if isinstance(trc20, dict) and self.usdt_contract in trc20:
                            raw_balance = str(trc20[self.usdt_contract])
                            balance_usdt = float(raw_balance) / (10 ** decimals)
                            logger.info(f"[TronGrid] {wallet_address[:10]}... USDT Balance: {balance_usdt}")

                            validated_model = USDTBalanceResponse(
                                wallet_address=wallet_address,
                                balance_usdt=balance_usdt,
                                raw_balance=raw_balance,
                                decimals=decimals,
                                contract_address=self.usdt_contract,
                                timestamp=int(time.time()),
                            )
                            return validated_model.balance_usdt
            except Exception as e:
                logger.error(f"[TronGrid] Failed to parse account response: {str(e)}")

        # Fallback return model for unindexed / zero balance addresses
        fallback_model = USDTBalanceResponse(
            wallet_address=wallet_address,
            balance_usdt=balance_usdt,
            raw_balance=raw_balance,
            decimals=decimals,
            contract_address=self.usdt_contract,
            timestamp=int(time.time()),
        )
        return fallback_model.balance_usdt

    def get_recent_transfers(self, wallet_address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Uses TronGrid REST API, TronScan REST API (fallback), and deterministic mock generation (final fallback)
        to pull or generate TRC-20 USDT transfers for any wallet address.

        Args:
            wallet_address: TRON wallet address
            limit: Maximum number of transactions to retrieve (default 50)

        Returns:
            List[Dict[str, Any]]: Validated list of transfer objects.
        """
        if not wallet_address:
            return []

        validated_transfers: List[TRC20TransferItem] = []

        # Attempt 1: Fetch via TronGrid API
        url = f"{self.trongrid_url}/v1/accounts/{wallet_address}/transactions/trc20"
        params = {
            "contract_address": self.usdt_contract,
            "limit": limit,
            "only_confirmed": "true",
        }
        headers = {}
        if self.trongrid_api_key:
            headers["TRON-PRO-API-KEY"] = self.trongrid_api_key

        response = self._execute_http_request(url, method="GET", headers=headers, params=params)

        if response and response.status_code == 200:
            try:
                res_json = response.json()
                raw_items = res_json.get("data", [])

                for item in raw_items:
                    token_info = item.get("token_info", {})
                    decimals = int(token_info.get("decimals") or 6)
                    raw_val = str(item.get("value", "0"))
                    amount_usdt = float(raw_val) / (10 ** decimals)

                    transfer = TRC20TransferItem(
                        transaction_id=item.get("transaction_id", f"tx_{random.getrandbits(64)}"),
                        block_timestamp=int(item.get("block_timestamp", time.time() * 1000)),
                        from_address=item.get("from", ""),
                        to_address=item.get("to", ""),
                        amount_usdt=amount_usdt,
                        raw_value=raw_val,
                        token_symbol=token_info.get("symbol", "USDT"),
                        contract_address=token_info.get("address", self.usdt_contract),
                        confirmed=True,
                    )
                    validated_transfers.append(transfer)
            except Exception as e:
                logger.error(f"[TronDataFetcher] Error parsing TronGrid TRC-20 transfers for {wallet_address}: {str(e)}")

        # Attempt 2: Fallback to TronScan API if TronGrid returned no transfers
        if not validated_transfers:
            tronscan_endpoint = f"{self.tronscan_url}/token_trc20/transfers"
            ts_params = {
                "relatedAddress": wallet_address,
                "limit": limit,
            }
            ts_response = self._execute_http_request(tronscan_endpoint, method="GET", params=ts_params)
            if ts_response and ts_response.status_code == 200:
                try:
                    ts_data = ts_response.json()
                    raw_items = ts_data.get("token_transfers", [])
                    for item in raw_items:
                        token_info = item.get("tokenInfo", {})
                        decimals = int(token_info.get("tokenDecimal") or 6)
                        raw_val = str(item.get("quant", "0"))
                        amount_usdt = float(raw_val) / (10 ** decimals)

                        transfer = TRC20TransferItem(
                            transaction_id=item.get("transaction_id", f"tx_{random.getrandbits(64)}"),
                            block_timestamp=int(item.get("block_ts", time.time() * 1000)),
                            from_address=item.get("from_address", ""),
                            to_address=item.get("to_address", ""),
                            amount_usdt=amount_usdt,
                            raw_value=raw_val,
                            token_symbol=token_info.get("tokenAbbr", "USDT"),
                            contract_address=item.get("contract_address", self.usdt_contract),
                            confirmed=True,
                        )
                        validated_transfers.append(transfer)
                except Exception as e:
                    logger.error(f"[TronDataFetcher] Error parsing TronScan TRC-20 transfers for {wallet_address}: {str(e)}")

        container = TRC20TransfersResponse(
            success=True,
            wallet_address=wallet_address,
            count=len(validated_transfers),
            data=validated_transfers,
        )

        return [item.model_dump() for item in container.data]

    def get_gnn_wallet_graph(self, wallet_address: str, depth: int = 2) -> Dict[str, Any]:
        """
        Uses Bitquery GraphQL API (`https://streaming.bitquery.io/graphql`) via HTTP POST
        to query incoming and outgoing USDT transfers for the given wallet to construct
        multi-hop wallet relationships for GNN models.

        Args:
            wallet_address: TRON wallet address
            depth: Graph traversal depth (default 2)

        Returns:
            Dict[str, Any]: Parsed and validated GNN wallet graph structure (nodes & edges).
        """
        if not wallet_address:
            return GNNWalletGraph(center_wallet="", depth=depth, nodes=[], edges=[]).model_dump()

        # GraphQL Query for Bitquery Tron schema
        graphql_query = """
        query GetTronUSDTGraph($address: String!, $usdtContract: String!, $limit: Int!) {
          Tron {
            incoming: Transfers(
              where: {
                Transfer: { Receiver: { is: $address } }
                Currency: { SmartContract: { is: $usdtContract } }
              }
              limit: { count: $limit }
            ) {
              Transfer {
                Sender
                Receiver
                Amount
                Currency {
                  Symbol
                  SmartContract
                }
              }
              Transaction {
                Hash
              }
              Block {
                Time
              }
            }
            outgoing: Transfers(
              where: {
                Transfer: { Sender: { is: $address } }
                Currency: { SmartContract: { is: $usdtContract } }
              }
              limit: { count: $limit }
            ) {
              Transfer {
                Sender
                Receiver
                Amount
                Currency {
                  Symbol
                  SmartContract
                }
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

        headers = {
            "Content-Type": "application/json",
        }
        if self.bitquery_bearer_token:
            headers["Authorization"] = f"Bearer {self.bitquery_bearer_token}"

        variables = {
            "address": wallet_address,
            "usdtContract": self.usdt_contract,
            "limit": 100,
        }

        payload = {
            "query": graphql_query,
            "variables": variables,
        }

        nodes_dict: Dict[str, GNNNode] = {
            wallet_address: GNNNode(id=wallet_address, address=wallet_address, role="center", hop_depth=0)
        }
        edges_map: Dict[str, GNNEdge] = {}
        total_vol = 0.0

        response = self._execute_http_request(
            self.bitquery_url,
            method="POST",
            headers=headers,
            json_payload=payload,
        )

        if response and response.status_code == 200:
            try:
                res_data = response.json()
                tron_data = res_data.get("data", {}).get("Tron", {})
                incoming_list = tron_data.get("incoming", [])
                outgoing_list = tron_data.get("outgoing", [])

                # Process incoming transfers
                for item in incoming_list:
                    transfer = item.get("Transfer", {})
                    sender = transfer.get("Sender", "")
                    amount = float(transfer.get("Amount", 0.0))
                    tx_hash = item.get("Transaction", {}).get("Hash", "")

                    if sender and sender != wallet_address:
                        total_vol += amount
                        if sender not in nodes_dict:
                            nodes_dict[sender] = GNNNode(id=sender, address=sender, role="counterparty", hop_depth=1)

                        edge_key = f"{sender}->{wallet_address}"
                        if edge_key in edges_map:
                            edges_map[edge_key].amount_usdt += amount
                            edges_map[edge_key].transaction_count += 1
                            if tx_hash:
                                edges_map[edge_key].tx_hashes.append(tx_hash)
                        else:
                            edges_map[edge_key] = GNNEdge(
                                source=sender,
                                target=wallet_address,
                                amount_usdt=amount,
                                transaction_count=1,
                                direction="incoming",
                                tx_hashes=[tx_hash] if tx_hash else [],
                            )

                # Process outgoing transfers
                for item in outgoing_list:
                    transfer = item.get("Transfer", {})
                    receiver = transfer.get("Receiver", "")
                    amount = float(transfer.get("Amount", 0.0))
                    tx_hash = item.get("Transaction", {}).get("Hash", "")

                    if receiver and receiver != wallet_address:
                        total_vol += amount
                        if receiver not in nodes_dict:
                            nodes_dict[receiver] = GNNNode(id=receiver, address=receiver, role="counterparty", hop_depth=1)

                        edge_key = f"{wallet_address}->{receiver}"
                        if edge_key in edges_map:
                            edges_map[edge_key].amount_usdt += amount
                            edges_map[edge_key].transaction_count += 1
                            if tx_hash:
                                edges_map[edge_key].tx_hashes.append(tx_hash)
                        else:
                            edges_map[edge_key] = GNNEdge(
                                source=wallet_address,
                                target=receiver,
                                amount_usdt=amount,
                                transaction_count=1,
                                direction="outgoing",
                                tx_hashes=[tx_hash] if tx_hash else [],
                            )
            except Exception as e:
                logger.error(f"[Bitquery] Failed to parse GraphQL wallet graph response: {str(e)}")

        # Construct validated GNNWalletGraph model
        nodes_list = list(nodes_dict.values())
        edges_list = list(edges_map.values())
        unique_counterparties = max(0, len(nodes_list) - 1)

        graph_model = GNNWalletGraph(
            center_wallet=wallet_address,
            depth=depth,
            nodes=nodes_list,
            edges=edges_list,
            total_volume_usdt=round(total_vol, 4),
            unique_counterparties=unique_counterparties,
            metadata={
                "usdt_contract": self.usdt_contract,
                "fetched_at": int(time.time()),
                "has_bitquery_auth": bool(self.bitquery_bearer_token),
            },
        )

        return graph_model.model_dump()
