import os
import logging
import json
import yaml
from typing import Dict, Any

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger("defi_risk_prediction")

def get_logger():
    return logger

def load_yaml(path: str) -> Dict[str, Any]:
    """Loads a YAML configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def ensure_dirs(dirs: list):
    """Ensures directories exist."""
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def is_valid_address(address: str) -> bool:
    """Validates if the address is a valid EVM-compatible hex address or TRON base58 address."""
    if not isinstance(address, str):
        return False
    if address.startswith("0x") and len(address) == 42:
        try:
            int(address, 16)
            return True
        except ValueError:
            return False
    if address.startswith("T") and len(address) == 34:
        return True
    return False

# Initialize necessary folders
ensure_dirs([
    "data/raw",
    "data/processed",
    "data/datasets",
    "models/registry",
    "models/tabular",
    "models/graph",
    "models/anomaly"
])
