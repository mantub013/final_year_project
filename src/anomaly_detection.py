import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from src.utils import get_logger

logger = get_logger()

def train_anomaly_detector():
    logger.info("Training Isolation Forest Anomaly Detector...")
    
    # Load raw data before SMOTE for anomaly detection (we want real distribution)
    df = pd.read_csv("data/datasets/blockchain_data.csv")
    
    # Isolate normal transactions to train the Isolation Forest baseline
    normal_df = df[df["is_fraud"] == 0].drop(columns=["is_fraud"])
    
    # Load scaler to scale features
    with open("models/scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
        
    X_normal_scaled = scaler.transform(normal_df)
    
    # Train Isolation Forest
    iso_forest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    iso_forest.fit(X_normal_scaled)
    
    # Save model
    with open("models/isolation_forest.pkl", "wb") as f:
        pickle.dump(iso_forest, f)
        
    logger.info("Saved Isolation Forest model to models/isolation_forest.pkl")

if __name__ == "__main__":
    train_anomaly_detector()
