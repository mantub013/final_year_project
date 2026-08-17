import os
import sqlite3
import pandas as pd
import json
from typing import Dict, Any, List, Optional
from src.utils import get_logger, ensure_dirs

logger = get_logger()

class OfflineFeatureStore:
    def __init__(self, db_path: str = "data/offline_store.db"):
        self.db_path = db_path
        ensure_dirs([os.path.dirname(db_path)])
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_features (
                address TEXT,
                timestamp INTEGER,
                chain TEXT,
                features_json TEXT,
                PRIMARY KEY (address, timestamp)
            )
        """)
        conn.commit()
        conn.close()

    def save_features(self, address: str, chain: str, features: Dict[str, Any]):
        """Saves a feature snapshot for a wallet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        import time
        cursor.execute("""
            INSERT OR REPLACE INTO offline_features (address, timestamp, chain, features_json)
            VALUES (?, ?, ?, ?)
        """, (address.lower(), int(time.time()), chain, json.dumps(features)))
        conn.commit()
        conn.close()
        logger.info(f"Saved feature snapshot to offline store for {address}")

    def get_historical_features(self, address: str) -> List[Dict[str, Any]]:
        """Retrieves history of feature snapshots for a wallet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, chain, features_json FROM offline_features 
            WHERE address = ? ORDER BY timestamp DESC
        """, (address.lower(),))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            features = json.loads(row[2])
            features["timestamp"] = row[0]
            features["chain"] = row[1]
            history.append(features)
        return history
        
    def export_training_dataframe(self) -> pd.DataFrame:
        """Exports all snapshots as a single DataFrame for retraining."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM offline_features", conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
            
        records = []
        for _, row in df.iterrows():
            feat = json.loads(row["features_json"])
            feat["address"] = row["address"]
            feat["timestamp"] = row["timestamp"]
            feat["chain"] = row["chain"]
            records.append(feat)
            
        return pd.DataFrame(records)
