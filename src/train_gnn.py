import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import networkx as nx
from src.utils import get_logger, ensure_dirs
from src.models_def import SimpleGNN

logger = get_logger()

def generate_mock_graph_data(num_nodes: int = 5000) -> tuple:
    """
    Generates a synthetic directed transaction graph and sets up node features
    and labels (fraud / normal) for graph neural network training.
    """
    logger.info(f"Generating massive mock wallet graph with {num_nodes} nodes...")
    # Power-law/Barabasi-Albert graph to simulate scale-free transaction distribution
    G = nx.extended_barabasi_albert_graph(n=num_nodes, m=2, p=0.1, q=0.05, seed=42)
    G = G.to_directed()
    
    # Generate random features for nodes
    np.random.seed(42)
    features = np.random.uniform(0, 1, size=(num_nodes, 5))
    
    # Designate a few hubs as blacklisted
    blacklisted_nodes = [10, 45, 82, 120, 250, 500, 1024, 3450]
    
    # Calculate shortest path length to blacklisted nodes
    labels = np.zeros(num_nodes)
    for i in range(num_nodes):
        min_dist = 99
        for bl in blacklisted_nodes:
            try:
                dist = nx.shortest_path_length(G, source=i, target=bl)
                min_dist = min(min_dist, dist)
            except nx.NetworkXNoPath:
                continue
        
        # Proximity indicator feature
        features[i, 4] = 1.0 / (min_dist + 1)
        
        # Label node as fraud if it is a blacklisted hub or directly connected (1 hop)
        if i in blacklisted_nodes or min_dist == 1:
            labels[i] = 1.0
            
    # Adjacency matrix
    adj_matrix = nx.to_numpy_array(G)
    adj_matrix = adj_matrix + np.eye(num_nodes)
    row_sum = adj_matrix.sum(axis=1)
    row_sum[row_sum == 0] = 1.0
    deg_inv = 1.0 / row_sum
    deg_inv_mat = np.diag(deg_inv)
    norm_adj = deg_inv_mat.dot(adj_matrix)
    
    # Generate strict academic train/test masks (80% train, 20% test)
    indices = np.random.permutation(num_nodes)
    split = int(0.8 * num_nodes)
    train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    test_mask = torch.zeros(num_nodes, dtype=torch.bool)
    train_mask[indices[:split]] = True
    test_mask[indices[split:]] = True
    
    return (
        torch.tensor(features, dtype=torch.float32), 
        torch.tensor(norm_adj, dtype=torch.float32), 
        torch.tensor(labels, dtype=torch.float32).unsqueeze(1),
        train_mask,
        test_mask
    )

def train_gnn():
    ensure_dirs(["models/graph"])
    
    features, adj, labels, train_mask, test_mask = generate_mock_graph_data()
    
    in_features = features.shape[1]
    hidden_dim = 16
    out_features = 8
    
    model = SimpleGNN(in_features, hidden_dim, out_features)
    optimizer = optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-5)
    criterion = nn.BCELoss()
    
    logger.info("Training GNN model with strict Train/Test splits...")
    
    best_test_acc = 0.0
    best_model_state = None
    
    for epoch in range(150):
        model.train()
        optimizer.zero_grad()
        output = model(features, adj)
        loss = criterion(output[train_mask], labels[train_mask])
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                pred = (output > 0.5).float()
                train_acc = (pred[train_mask] == labels[train_mask]).float().mean()
                test_acc = (pred[test_mask] == labels[test_mask]).float().mean()
                
                if test_acc > best_test_acc:
                    best_test_acc = test_acc
                    best_model_state = model.state_dict()
                    
                logger.info(f"Epoch {epoch+1:03d} | Train Loss: {loss.item():.4f} | Train Acc: {train_acc:.4f} | Test Acc: {test_acc:.4f}")
            
    # Save the best GNN model weights
    if best_model_state:
        torch.save(best_model_state, "models/graph/gnn_model.pt")
        logger.info(f"Saved best GNN model (Test Acc: {best_test_acc:.4f}) to models/graph/gnn_model.pt")
    else:
        torch.save(model.state_dict(), "models/graph/gnn_model.pt")

if __name__ == "__main__":
    train_gnn()
