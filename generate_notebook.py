import nbformat as nbf
import os

def create_notebook():
    os.makedirs("notebooks", exist_ok=True)
    nb = nbf.v4.new_notebook()

    nb['cells'] = [
        nbf.v4.new_markdown_cell("# AI-DeFi Risk Intelligence: EDA and Modeling\nThis notebook demonstrates the Exploratory Data Analysis, SMOTE class imbalance handling, and Model Comparison as required by the final project rubric."),
        
        nbf.v4.new_markdown_cell("## 1. Data Loading and EDA"),
        nbf.v4.new_code_cell("import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\ndf = pd.read_csv('../data/datasets/blockchain_data.csv')\ndf.head()"),
        nbf.v4.new_code_cell("plt.figure(figsize=(6,4))\nsns.countplot(data=df, x='is_fraud')\nplt.title('Original Class Distribution (Highly Imbalanced)')\nplt.show()"),
        
        nbf.v4.new_markdown_cell("## 2. SMOTE and Preprocessing"),
        nbf.v4.new_code_cell("X = df.drop(columns=['is_fraud'])\ny = df['is_fraud']\n\nfrom imblearn.over_sampling import SMOTE\nsmote = SMOTE(random_state=42)\nX_resampled, y_resampled = smote.fit_resample(X, y)\n\nplt.figure(figsize=(6,4))\nsns.countplot(x=y_resampled)\nplt.title('Class Distribution after SMOTE')\nplt.show()"),
        
        nbf.v4.new_markdown_cell("## 3. Model Comparison"),
        nbf.v4.new_code_cell("results = pd.read_csv('../models/model_comparison.csv')\nresults.head()"),
        nbf.v4.new_code_cell("plt.figure(figsize=(10,5))\nsns.barplot(data=results, x='Model', y='F1-Score')\nplt.title('Model F1-Score Comparison')\nplt.show()"),
        
        nbf.v4.new_markdown_cell("## 4. SHAP Explainability on XGBoost"),
        nbf.v4.new_code_cell("import shap\nimport pickle\n\nwith open('../models/xgboost_classifier.pkl', 'rb') as f:\n    xgb = pickle.load(f)\nwith open('../models/scaler.pkl', 'rb') as f:\n    scaler = pickle.load(f)\nwith open('../data/datasets/feature_names.pkl', 'rb') as f:\n    feature_names = pickle.load(f)\n\nexplainer = shap.TreeExplainer(xgb)\nX_test = np.load('../data/datasets/X_test_scaled.npy')\nshap_values = explainer.shap_values(X_test[:100])\n\nshap.summary_plot(shap_values, X_test[:100], feature_names=feature_names)")
    ]

    with open("notebooks/EDA_and_Modeling.ipynb", "w") as f:
        nbf.write(nb, f)
        
    print("Notebook successfully generated at notebooks/EDA_and_Modeling.ipynb")

if __name__ == "__main__":
    create_notebook()
