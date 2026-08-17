import streamlit as st
import pandas as pd
import numpy as np
import pickle
from src.risk_scoring import compute_final_risk_score
from src.explainability import get_shap_explanations

st.set_page_config(page_title="DeFi Risk Intelligence", layout="wide")

# Load Models
@st.cache_resource
def load_models():
    with open("models/xgboost_classifier.pkl", "rb") as f:
        xgb = pickle.load(f)
    with open("models/isolation_forest.pkl", "rb") as f:
        iso = pickle.load(f)
    with open("models/scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    with open("data/datasets/feature_names.pkl", "rb") as f:
        feats = pickle.load(f)
    return xgb, iso, scaler, feats

xgb_model, iso_model, scaler, feature_names = load_models()

st.title("🛡️ AI-DeFi Risk Intelligence Platform")
st.markdown("Classify blockchain wallets/transactions as **safe** or **risky** in real-time.")

# Sidebar Input
st.sidebar.header("Input Wallet Data")
address = st.sidebar.text_input("Wallet Address", value="0x1234...abcd")

# Dummy feature inputs for demo
st.sidebar.subheader("Transaction Features")
features = {}
for f in feature_names:
    features[f] = st.sidebar.number_input(f, value=0.0)

if st.sidebar.button("Analyze Risk"):
    input_df = pd.DataFrame([features])
    scaled_input = scaler.transform(input_df)
    
    # Predictions
    xgb_prob = xgb_model.predict_proba(scaled_input)[0][1]
    iso_score = iso_model.decision_function(scaled_input)[0]
    
    # Scoring
    result = compute_final_risk_score(xgb_prob, iso_score)
    
    # SHAP Explanations
    explanations = get_shap_explanations(scaled_input)
    
    # UI Display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Calibrated Risk Score", f"{result['score']}/100", result['level'])
        
    with col2:
        st.metric("XGBoost Probability", f"{result['xgb_prob']:.2%}")
        
    with col3:
        st.metric("Isolation Forest Anomaly", f"{result['anomaly_risk']:.2%}")
        
    st.markdown("---")
    st.subheader("🧠 SHAP Explainability: Top Contributing Features")
    
    # SHAP Bar Chart
    shap_df = pd.DataFrame(explanations)
    if not shap_df.empty:
        # Determine color: positive contribution (riskier) = red, negative (safer) = green
        shap_df['color'] = shap_df['contribution'].apply(lambda x: '#ff4b4b' if x > 0 else '#00cc96')
        st.bar_chart(shap_df.set_index('feature')['contribution'])
        
        st.markdown("**Key Drivers:**")
        for exp in explanations:
            direction = "Increased" if exp['contribution'] > 0 else "Decreased"
            st.write(f"- **{exp['feature']}**: {direction} risk score (SHAP value: {exp['contribution']:.4f})")

    st.markdown("---")
    st.subheader("🚨 Flagged High-Risk Wallets")
    st.dataframe(pd.DataFrame({
        "Address": ["0xbadc0de...", "0xmixer..."],
        "Risk Score": [95, 88],
        "Reason": ["High transaction velocity", "Contract interaction anomaly"]
    }))
