import pytest
from src.utils import load_yaml
from src.blockchain_api_tron import TronDataFetcher, USDT_TRON_CONTRACT, USDTBalanceResponse, GNNWalletGraph
from src.stream_listener_tron import TronStreamListener, TronStreamTxPayload, TronKafkaProducer

def test_chains_yaml_tron_config():
    config = load_yaml("config/chains.yaml")
    assert "tron" in config
    tron_cfg = config["tron"]
    assert tron_cfg["name"] == "Tron Mainnet"
    assert tron_cfg["usdt_contract"] == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    assert "trongrid_api_key" in tron_cfg
    assert "bitquery_bearer_token" in tron_cfg

def test_tron_data_fetcher_usdt_balance():
    fetcher = TronDataFetcher()
    test_wallet = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    balance = fetcher.get_usdt_balance(test_wallet)
    assert isinstance(balance, float)
    assert balance >= 0.0

def test_tron_data_fetcher_recent_transfers():
    fetcher = TronDataFetcher()
    test_wallet = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    transfers = fetcher.get_recent_transfers(test_wallet, limit=5)
    assert isinstance(transfers, list)

def test_tron_data_fetcher_gnn_wallet_graph():
    fetcher = TronDataFetcher()
    test_wallet = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    graph = fetcher.get_gnn_wallet_graph(test_wallet, depth=2)
    assert isinstance(graph, dict)
    assert "nodes" in graph
    assert "edges" in graph
    assert "center_wallet" in graph
    assert graph["center_wallet"] == test_wallet

def test_stream_tx_payload_pydantic_validation():
    payload = TronStreamTxPayload(
        tx_hash="0x1234567890abcdef",
        block_timestamp=1670000000000,
        from_address="TNPeeaaTK7v3QGiBBWnWNFUzhMHucEjm84",
        to_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        amount_usdt=100.5,
    )
    assert payload.amount_usdt == 100.5
    assert payload.chain == "tron"
    assert payload.token_symbol == "USDT"

def test_tron_stream_listener_run_once():
    config = load_yaml("config/chains.yaml")
    listener = TronStreamListener(config=config)
    # Perform single iteration run
    listener.poll_trongrid_stream(interval_sec=0.1, run_once=True)
