import pytest
from src.preprocessing import calculate_base_features

def test_calculate_base_features_empty():
    address = "0x7A5D8F3A22904838493028304920492039203920"
    features = calculate_base_features(address, [], [], 10.0)
    assert features["wallet_balance"] == 10.0
    assert features["transaction_amount"] == 0.0
    assert features["failed_transactions"] == 0
    assert features["token_transfers"] == 0

def test_calculate_base_features_with_data():
    address = "0x7A5D8F3A22904838493028304920492039203920"
    txs = [
        {
            "timeStamp": "1690000000",
            "from": address,
            "to": "0xrecipient",
            "value": "1000000000000000000", # 1 ETH
            "gasUsed": "21000",
            "gasPrice": "50000000000", # 50 Gwei
            "isError": "0",
            "txreceipt_status": "1"
        },
        {
            "timeStamp": "1690003600", # 1 hour later
            "from": "0xsender",
            "to": address,
            "value": "2000000000000000000", # 2 ETH
            "gasUsed": "50000",
            "gasPrice": "60000000000", # 60 Gwei
            "isError": "1",
            "txreceipt_status": "0"
        }
    ]
    
    token_txs = [
        {
            "contractAddress": "0xbadc0de1f111e111222333444555666777888999",
            "tokenSymbol": "SCAM",
            "value": "100"
        }
    ]
    
    features = calculate_base_features(address, txs, token_txs, 5.5)
    
    assert features["wallet_balance"] == 5.5
    assert features["transaction_amount"] == 3.0 # 1 + 2 ETH
    assert features["failed_transactions"] == 1
    assert features["token_transfers"] == 1
    assert features["rug_pull_token_interaction"] == 2

