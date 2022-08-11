"""
Dataloaders used to manipulate objects instead of numpy arrays
It also converts the numpy array to torch tensors so we can use
GPUs
"""
from torch.utils.data import Dataset
import torch
import numpy as np

class StockDataloader(Dataset):
    """
    Dataset class used to get rows of items as well as batches (with Dataloaders)
    """
    X: torch.Tensor
    Y: torch.Tensor

    def __init__(self, data: np.ndarray | torch.Tensor) -> None:
        """
        Here we load the features and the target. 
        WARNING! It is asumed that the last column is the target
        """
        self.X = torch.Tensor(data[:, :-1])
        self.Y =  torch.Tensor(data[:, -1])
    
    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[index, :], self.Y[index]
