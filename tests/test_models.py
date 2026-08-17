import pytest
import torch
from src.models_def import SimpleGNN, Autoencoder

def test_gnn_model_shapes():
    num_nodes = 10
    in_features = 5
    hidden_dim = 8
    out_features = 4
    
    # Random input features and normalized adj matrix
    x = torch.randn(num_nodes, in_features)
    adj = torch.eye(num_nodes)  # simple identity matrix as mock adj
    
    model = SimpleGNN(in_features, hidden_dim, out_features)
    output = model(x, adj)
    
    # Assert output shape is [num_nodes, 1] containing probability values
    assert output.shape == (num_nodes, 1)
    assert torch.all(output >= 0.0)
    assert torch.all(output <= 1.0)

def test_autoencoder_shapes():
    input_dim = 12
    latent_dim = 4
    batch_size = 5
    
    x = torch.randn(batch_size, input_dim)
    model = Autoencoder(input_dim=input_dim, latent_dim=latent_dim)
    
    reconstructed = model(x)
    errors = model.compute_reconstruction_error(x)
    
    assert reconstructed.shape == (batch_size, input_dim)
    assert errors.shape == (batch_size,)
    assert torch.all(errors >= 0.0)
