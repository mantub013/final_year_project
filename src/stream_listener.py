import os
import json
import time
import random
from typing import List, Dict, Any
from src.utils import get_logger, ensure_dirs, load_yaml
from src.prediction import predict_wallet_risk

logger = get_logger()

# Predefined list of mock addresses to cycle through in the stream
MOCK_STREAM_ADDRESSES = [
    "0x7A5D8F3A22904838493028304920492039203920",
    "0x0000000000000000000000000000000000000bad",
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
    "0xbadc0de1f111e111222333444555666777888999",
    "0x71c7656ec7ab88b098defb751b7401b5f6d8976f",
    "0xdeadbeefdeadbeefdeadbeefdeadbeefdead0000",
    "0x8626f6940e2eb28930efb4cef49b2d1f2c9c1199",
    "0xdd2fd4581271e230360230f9337d5c0430bf44c0",
    "0x2546f6940e2eb28930efb4cef49b2d1f2c9c1188"
]

def append_alert(alert: Dict[str, Any]):
    """Appends an alert to the local data/alerts.json file."""
    ensure_dirs(["data"])
    alerts_file = "data/alerts.json"
    
    alerts = []
    if os.path.exists(alerts_file):
        try:
            with open(alerts_file, "r") as f:
                alerts = json.load(f)
        except Exception:
            alerts = []
            
    alerts.insert(0, alert)  # Newest alert at the top
    alerts = alerts[:50]    # Keep only the latest 50 alerts
    
    with open(alerts_file, "w") as f:
        json.dump(alerts, f, indent=2)

def run_stream_listener(chains_config: Dict[str, Any], run_once: bool = False):
    """Simulates real-time transaction ingestion and risk prediction."""
    logger.info("Starting real-time streaming pipeline...")
    
    # Initialize blank alerts file
    with open("data/alerts.json", "w") as f:
        json.dump([], f)
        
    chains = list(chains_config.keys())
    
    try:
        while True:
            # Select random wallet and chain
            address = random.choice(MOCK_STREAM_ADDRESSES)
            chain = random.choice(chains)
            
            logger.info(f"Ingested live transaction for {address} on {chain}")
            
            # Predict risk
            try:
                result = predict_wallet_risk(address, chain, chains_config)
                score = result["risk_score"]
                level = result["risk_level"]
                
                # If risk is medium, high, or critical, generate alert
                if score >= 40:
                    alert = {
                        "timestamp": int(time.time()),
                        "address": address,
                        "chain": chain,
                        "risk_score": score,
                        "risk_level": level,
                        "alert_id": f"alert_{random.randint(100000, 999999)}",
                        "reason": f"High risk transaction detected. Tabular score: {result['breakdown']['tabular_ensemble']:.2f}, Network risk: {result['breakdown']['gnn_network_risk']:.2f}"
                    }
                    append_alert(alert)
                    logger.warning(f"⚠️ ALERT GENERATED: {address} on {chain} scored {score} ({level})")
            except Exception as e:
                logger.error(f"Error processing transaction in stream: {str(e)}")
                
            if run_once:
                break
                
            # Sleep 3 to 7 seconds between transactions
            time.sleep(random.uniform(3.0, 7.0))
            
    except KeyboardInterrupt:
        logger.info("Real-time pipeline stopped by user.")

if __name__ == "__main__":
    chains_cfg = load_yaml("config/chains.yaml")
    run_stream_listener(chains_cfg)
