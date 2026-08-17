import pickle
import shap
import numpy as np

# Load XGBoost model once
with open("models/xgboost_classifier.pkl", "rb") as f:
    xgb_model = pickle.load(f)

# Initialize SHAP TreeExplainer
explainer = shap.TreeExplainer(xgb_model)

with open("data/datasets/feature_names.pkl", "rb") as f:
    feature_names = pickle.load(f)

def get_shap_explanations(scaled_features_array):
    """
    Computes SHAP values for a single prediction and returns the top 3-5 driving features.
    """
    # Calculate SHAP values
    shap_values = explainer.shap_values(scaled_features_array)
    
    # Create dictionary of feature -> absolute shap value
    contributions = []
    for i, name in enumerate(feature_names):
        val = shap_values[0][i]
        contributions.append({
            "feature": name,
            "contribution": float(val)
        })
        
    # Sort by absolute impact
    contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    
    # Return top 5
    return contributions[:5]
