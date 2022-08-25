import torch
import torch.nn as nn
import os

def get_num_trainable_params(model: nn.Module):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def save_model(model: nn.Module, name: str, save_dir = "./saved_models") -> None:
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        n_params = get_num_trainable_params(model)
        save_path = f"{save_dir}/{name}_{n_params}.pickle"
        print(f"Saving model at location {save_path}")
        torch.save(model.state_dict(), save_path)
    except Exception as e:
        raise e