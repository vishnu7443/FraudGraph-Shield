import torch
from gnn_model import GraphSAGEModel

def test_model_output_shape():
    model = GraphSAGEModel(in_channels=74, hidden_channels=128, out_channels=1)
    x = torch.randn(100, 74)
    edge_index = torch.randint(0, 100, (2, 200))
    out = model(x, edge_index)
    assert out.shape == (100, 1)

def test_output_is_probability():
    model = GraphSAGEModel(in_channels=74, hidden_channels=128, out_channels=1)
    x = torch.randn(50, 74)
    edge_index = torch.randint(0, 50, (2, 100))
    out = model(x, edge_index)
    assert torch.all(out >= 0.0) and torch.all(out <= 1.0)

def test_model_is_deterministic_in_eval_mode():
    model = GraphSAGEModel(in_channels=74, hidden_channels=128, out_channels=1)
    model.eval()
    x = torch.randn(20, 74)
    edge_index = torch.randint(0, 20, (2, 40))
    out1 = model(x, edge_index)
    out2 = model(x, edge_index)
    assert torch.allclose(out1, out2)

def test_gradient_flows_during_training():
    model = GraphSAGEModel(in_channels=74, hidden_channels=128, out_channels=1)
    model.train()
    x = torch.randn(30, 74, requires_grad=True)
    edge_index = torch.randint(0, 30, (2, 60))
    # use return_logits=True for BCEWithLogitsLoss during gradient check
    out = model(x, edge_index, return_logits=True)
    loss = out.mean()
    loss.backward()
    assert x.grad is not None
