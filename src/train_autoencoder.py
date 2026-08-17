import os
import pickle
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from src.utils import get_logger, load_yaml, ensure_dirs
from src.models_def import Autoencoder

logger = get_logger()

def train_autoencoder():
    ensure_dirs(["models/anomaly"])
    
    # Load tabular dataset
    data_path = "data/datasets/tabular_dataset.csv"
    if not os.path.exists(data_path):
        logger.error(f"Tabular dataset not found at {data_path}. Please train tabular model first.")
        return
        
    df = pd.read_csv(data_path)
    config = load_yaml("config/model_config.yaml")
    feature_cols = config["features"]["tabular"]
    
    # Select only normal/non-fraud records to train the Autoencoder
    normal_df = df[df["is_fraud"] == 0]
    X_normal = normal_df[feature_cols].values
    
    # Load scaler
    scaler_path = "models/scaler.pkl"
    if not os.path.exists(scaler_path):
        logger.error("Scaler not found. Train tabular model first.")
        return
        
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
        
    X_normal_scaled = scaler.transform(X_normal)
    
    # Split into train and validation for early stopping
    X_train, X_val = train_test_split(X_normal_scaled, test_size=0.15, random_state=42)
    
    # Setup PyTorch data loaders
    train_tensor = torch.tensor(X_train, dtype=torch.float32)
    val_tensor = torch.tensor(X_val, dtype=torch.float32)
    
    train_dataset = TensorDataset(train_tensor, train_tensor)
    val_dataset = TensorDataset(val_tensor, val_tensor)
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
    
    input_dim = len(feature_cols)
    model = Autoencoder(input_dim=input_dim, latent_dim=4)
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    criterion = nn.MSELoss()
    
    logger.info("Training Autoencoder with Early Stopping...")
    
    best_val_loss = float('inf')
    patience = 5
    patience_counter = 0
    best_model_state = None
    
    for epoch in range(100):
        model.train()
        total_train_loss = 0.0
        for batch_x, _ in train_loader:
            optimizer.zero_grad()
            reconstructed = model(batch_x)
            loss = criterion(reconstructed, batch_x)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item() * batch_x.size(0)
            
        avg_train_loss = total_train_loss / len(train_dataset)
        
        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for batch_x, _ in val_loader:
                reconstructed = model(batch_x)
                loss = criterion(reconstructed, batch_x)
                total_val_loss += loss.item() * batch_x.size(0)
                
        avg_val_loss = total_val_loss / len(val_dataset)
        
        if (epoch + 1) % 5 == 0:
            logger.info(f"Epoch {epoch+1:03d} | Train MSE: {avg_train_loss:.6f} | Val MSE: {avg_val_loss:.6f}")
            
        # Early Stopping Logic
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            best_model_state = model.state_dict()
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping triggered at epoch {epoch+1}. Best Val MSE: {best_val_loss:.6f}")
                break
            
    # Save best autoencoder
    if best_model_state:
        torch.save(best_model_state, "models/anomaly/autoencoder.pt")
        logger.info("Saved best Autoencoder model to models/anomaly/autoencoder.pt")
    else:
        torch.save(model.state_dict(), "models/anomaly/autoencoder.pt")

if __name__ == "__main__":
    train_autoencoder()
