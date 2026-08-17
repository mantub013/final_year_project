import os
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from src.utils import get_logger, ensure_dirs

logger = get_logger()

def train_models():
    ensure_dirs(["models"])
    
    X_train = np.load("data/datasets/X_train_scaled.npy")
    X_test = np.load("data/datasets/X_test_scaled.npy")
    y_train = np.load("data/datasets/y_train.npy")
    y_test = np.load("data/datasets/y_test.npy")
    
    # 4. MODEL BUILDING: Train and compare baseline models
    models = {
        "Logistic Regression": LogisticRegression(random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(random_state=42),
        "XGBoost": XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42, max_depth=5, learning_rate=0.1)
    }
    
    results = []
    
    for name, model in models.items():
        logger.info(f"Training {name}...")
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else preds
        
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds)
        rec = recall_score(y_test, preds)
        f1 = f1_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        
        results.append({
            "Model": name,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1-Score": f1,
            "ROC-AUC": auc
        })
        
        if name == "XGBoost":
            # Save the primary model
            with open("models/xgboost_classifier.pkl", "wb") as f:
                pickle.dump(model, f)
            logger.info("Saved XGBoost model to models/xgboost_classifier.pkl")
            
    # Present a comparison table
    df_results = pd.DataFrame(results)
    logger.info("\n" + df_results.to_string(index=False))
    df_results.to_csv("models/model_comparison.csv", index=False)

if __name__ == "__main__":
    train_models()
