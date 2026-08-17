import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, f1_score, roc_auc_score, confusion_matrix, roc_curve
from src.utils import get_logger, load_yaml, ensure_dirs

logger = get_logger()

def generate_mock_tabular_data(n_samples: int = 50000) -> pd.DataFrame:
    """Generates a realistic synthetic tabular blockchain dataset at scale."""
    logger.info(f"Generating mock tabular dataset with {n_samples} samples...")
    np.random.seed(42)
    
    # Generate features
    wallet_age = np.random.exponential(scale=100, size=n_samples) + 0.1
    transaction_frequency = np.random.exponential(scale=5, size=n_samples) + 0.1
    transaction_amount = np.random.exponential(scale=50, size=n_samples) + 0.01
    failed_transactions = np.random.poisson(lam=0.5, size=n_samples)
    average_gas_fee = np.random.exponential(scale=0.005, size=n_samples)
    wallet_balance = np.random.exponential(scale=10, size=n_samples)
    unique_counterparties = np.random.poisson(lam=3, size=n_samples) + 1
    smart_contract_calls = np.random.poisson(lam=2, size=n_samples)
    
    # Threat signals
    rug_pull_token_interaction = np.random.choice([0, 1, 2, 3], p=[0.85, 0.10, 0.04, 0.01], size=n_samples)
    flash_loan_usage = np.random.choice([0, 1], p=[0.98, 0.02], size=n_samples)
    
    token_transfers = np.random.poisson(lam=4, size=n_samples)
    nft_transfers = np.random.poisson(lam=0.5, size=n_samples)
    burst_activity_score = np.random.uniform(0, 1, size=n_samples)

    # Label assignment based on complex logic
    risk_prob = (
        0.05 * (wallet_age < 3) +
        0.15 * failed_transactions +
        0.30 * rug_pull_token_interaction +
        0.45 * flash_loan_usage +
        0.20 * (burst_activity_score > 0.8) +
        0.10 * (transaction_frequency > 15)
    )
    
    # Clip probabilities between 0 and 1
    risk_prob = np.clip(risk_prob, 0.0, 1.0)
    is_fraud = np.random.binomial(1, risk_prob)

    df = pd.DataFrame({
        "wallet_age": wallet_age,
        "transaction_frequency": transaction_frequency,
        "transaction_amount": transaction_amount,
        "failed_transactions": failed_transactions,
        "average_gas_fee": average_gas_fee,
        "wallet_balance": wallet_balance,
        "unique_counterparties": unique_counterparties,
        "smart_contract_calls": smart_contract_calls,
        "rug_pull_token_interaction": rug_pull_token_interaction,
        "flash_loan_usage": flash_loan_usage,
        "token_transfers": token_transfers,
        "nft_transfers": nft_transfers,
        "burst_activity_score": burst_activity_score,
        "is_fraud": is_fraud
    })
    
    return df

def train_tabular_models():
    ensure_dirs(["data/datasets", "models/tabular", "models/figures"])
    
    data_path = "data/datasets/tabular_dataset.csv"
    # Always regenerate for final project to ensure 50k rows
    df = generate_mock_tabular_data()
    df.to_csv(data_path, index=False)
    logger.info(f"Saved massive mock dataset to {data_path}")
        
    config = load_yaml("config/model_config.yaml")
    feature_cols = config["features"]["tabular"]
    
    X = df[feature_cols]
    y = df["is_fraud"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Save scaler
    with open("models/scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    logger.info("Saved scaler to models/scaler.pkl")
    
    # GridSearchCV for XGBoost to demonstrate academic rigor
    logger.info("Performing Hyperparameter Tuning for XGBoost...")
    param_grid = {
        'max_depth': [3, 5],
        'learning_rate': [0.1, 0.01],
        'n_estimators': [100, 200]
    }
    xgb_base = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
    grid_search = GridSearchCV(estimator=xgb_base, param_grid=param_grid, cv=3, scoring='f1', n_jobs=-1)
    grid_search.fit(X_train_scaled, y_train)
    logger.info(f"Best XGBoost Params: {grid_search.best_params_}")
    best_xgb = grid_search.best_estimator_
    
    models = {
        "random_forest": RandomForestClassifier(random_state=42),
        "gradient_boosting": GradientBoostingClassifier(random_state=42),
        "xgboost": best_xgb
    }
    
    best_f1 = -1
    best_model_name = ""
    best_model = None
    
    for name, model in models.items():
        logger.info(f"Training {name}...")
        if name != "xgboost": # xgb is already fitted via GridSearchCV
            model.fit(X_train_scaled, y_train)
        
        preds = model.predict(X_test_scaled)
        probs = model.predict_proba(X_test_scaled)[:, 1]
        
        f1 = f1_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        
        logger.info(f"{name} Evaluation: F1={f1:.4f}, AUC={auc:.4f}")
        
        model_path = f"models/tabular/{name}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            best_model = model
            best_preds = preds
            best_probs = probs

    logger.info(f"Best model was {best_model_name} with F1={best_f1:.4f}")
    
    # Generate and save plots for the best model
    logger.info("Generating Evaluation Charts...")
    
    # 1. Confusion Matrix
    cm = confusion_matrix(y_test, best_preds)
    plt.figure(figsize=(6,5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'Confusion Matrix - {best_model_name}')
    plt.ylabel('Actual Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig('models/figures/confusion_matrix.png')
    plt.close()
    
    # 2. ROC Curve
    fpr, tpr, _ = roc_curve(y_test, best_probs)
    plt.figure(figsize=(6,5))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {best_f1:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'ROC Curve - {best_model_name}')
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig('models/figures/roc_curve.png')
    plt.close()
    
    with open("models/tabular/best_model.pkl", "wb") as f:
        pickle.dump(best_model, f)
    logger.info("Saved best model to models/tabular/best_model.pkl and generated charts in models/figures/")

if __name__ == "__main__":
    train_tabular_models()
