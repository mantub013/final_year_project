import os
import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split
from src.utils import get_logger, ensure_dirs

logger = get_logger()

def generate_blockchain_dataset(n_samples: int = 10000) -> pd.DataFrame:
    """Simulates a public blockchain transaction dataset (e.g., Etherscan data)"""
    logger.info(f"Generating mock blockchain dataset with {n_samples} samples...")
    np.random.seed(42)
    
    # 3. FEATURE ENGINEERING: Derive transaction velocity, wallet age, avg size, etc.
    wallet_age_days = np.random.exponential(scale=100, size=n_samples) + 0.1
    transaction_velocity = np.random.exponential(scale=5, size=n_samples) + 0.1
    avg_transaction_size = np.random.exponential(scale=50, size=n_samples) + 0.01
    failed_transactions_ratio = np.random.uniform(0, 0.3, size=n_samples)
    gas_used = np.random.exponential(scale=100000, size=n_samples)
    wallet_balance = np.random.exponential(scale=10, size=n_samples)
    in_degree = np.random.poisson(lam=3, size=n_samples) + 1
    out_degree = np.random.poisson(lam=2, size=n_samples)
    std_dev_tx_amounts = np.random.exponential(scale=20, size=n_samples)
    contract_interaction_flag = np.random.choice([0, 1], p=[0.7, 0.3], size=n_samples)

    # Label assignment based on complex logic
    risk_prob = (
        0.10 * (wallet_age_days < 5) +
        0.20 * failed_transactions_ratio +
        0.30 * contract_interaction_flag +
        0.15 * (transaction_velocity > 20) +
        0.10 * (in_degree > 10)
    )
    
    risk_prob = np.clip(risk_prob, 0.0, 1.0)
    # Imbalanced dataset: Fraud is minority (~10%)
    is_fraud = np.random.binomial(1, risk_prob * 0.3)

    df = pd.DataFrame({
        "wallet_age_days": wallet_age_days,
        "transaction_velocity": transaction_velocity,
        "avg_transaction_size": avg_transaction_size,
        "failed_transactions_ratio": failed_transactions_ratio,
        "gas_used": gas_used,
        "wallet_balance": wallet_balance,
        "in_degree": in_degree,
        "out_degree": out_degree,
        "std_dev_tx_amounts": std_dev_tx_amounts,
        "contract_interaction_flag": contract_interaction_flag,
        "is_fraud": is_fraud
    })
    
    return df

def preprocess_data():
    ensure_dirs(["data/datasets", "models"])
    
    data_path = "data/datasets/blockchain_data.csv"
    df = generate_blockchain_dataset()
    df.to_csv(data_path, index=False)
    logger.info(f"Saved dataset to {data_path}")
        
    X = df.drop(columns=["is_fraud"])
    y = df["is_fraud"]
    
    # 2. DATA PREPROCESSING: Handle class imbalance using SMOTE
    logger.info(f"Original class distribution: {y.value_counts().to_dict()}")
    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X, y)
    logger.info(f"Resampled class distribution: {pd.Series(y_resampled).value_counts().to_dict()}")
    
    X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)
    
    # Normalize/scale numeric features (StandardScaler)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    with open("models/scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    logger.info("Saved scaler to models/scaler.pkl")
    
    # Save splits for model training
    np.save("data/datasets/X_train_scaled.npy", X_train_scaled)
    np.save("data/datasets/X_test_scaled.npy", X_test_scaled)
    np.save("data/datasets/y_train.npy", y_train)
    np.save("data/datasets/y_test.npy", y_test)
    
    # Save feature names for SHAP
    with open("data/datasets/feature_names.pkl", "wb") as f:
        pickle.dump(X.columns.tolist(), f)
        
    logger.info("Data preprocessing completed successfully.")

if __name__ == "__main__":
    preprocess_data()
