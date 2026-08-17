import torch
import torch.nn as nn
import torch.nn.functional as F

class GraphSageLayer(nn.Module):
    """
    A custom GraphSAGE-like layer implemented in pure PyTorch.
    Aggregates neighbor features and combines them with target node features.
    """
    def __init__(self, in_features: int, out_features: int):
        super(GraphSageLayer, self).__init__()
        self.linear_self = nn.Linear(in_features, out_features)
        self.linear_neigh = nn.Linear(in_features, out_features)
        
    def forward(self, x: torch.Tensor, adj_matrix: torch.Tensor) -> torch.Tensor:
        # x shape: [num_nodes, in_features]
        # adj_matrix shape: [num_nodes, num_nodes] (normalized)
        
        # Aggregate neighbor features: D^-1 * A * X
        neigh_feats = torch.matmul(adj_matrix, x)
        
        # Combine self representation and neighbor representation
        out_self = self.linear_self(x)
        out_neigh = self.linear_neigh(neigh_feats)
        
        return F.relu(out_self + out_neigh)

class SimpleGNN(nn.Module):
    """
    A multi-layer Graph Neural Network using custom GraphSage layers.
    Learns node embeddings and classifies nodes.
    """
    def __init__(self, in_features: int, hidden_dim: int, out_features: int):
        super(SimpleGNN, self).__init__()
        self.layer1 = GraphSageLayer(in_features, hidden_dim)
        self.layer2 = GraphSageLayer(hidden_dim, out_features)
        self.classifier = nn.Linear(out_features, 1)
        
    def forward(self, x: torch.Tensor, adj_matrix: torch.Tensor) -> torch.Tensor:
        h = self.layer1(x, adj_matrix)
        h = self.layer2(h, adj_matrix)
        logits = self.classifier(h)
        return torch.sigmoid(logits)

class Autoencoder(nn.Module):
    """
    An unsupervised Autoencoder used for reconstruction-based anomaly detection.
    High reconstruction error indicates anomalous/unseen transaction patterns.
    """
    def __init__(self, input_dim: int, latent_dim: int = 4):
        super(Autoencoder, self).__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 8),
            nn.ReLU(),
            nn.Linear(8, latent_dim),
            nn.ReLU()
        )
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 8),
            nn.ReLU(),
            nn.Linear(8, input_dim),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed

    def compute_reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Returns reconstruction error (MSE) per row."""
        reconstructed = self.forward(x)
        return torch.mean((x - reconstructed) ** 2, dim=1)
