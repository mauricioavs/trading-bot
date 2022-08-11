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

    def __init__(self, 
        data: np.ndarray | torch.Tensor, 
        seq_length: int = 60) -> None:
        """
        Here we load the features and the target. 
        WARNING! It is asumed that the last column is the target

        Inputs
        ---
        data: numpy array or torch tensor data
        seq_length: sequence length. Data will be split into these chunks
        ---
        """
        self.X = torch.Tensor(data[:, :-1])
        self.Y =  torch.Tensor(data[:, -1])
        self.seq_length = seq_length
    
    def __len__(self):
        return int(self.X.shape[0] / self.seq_length -1)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        start_idx = index * self.seq_length
        end_idx = start_idx + self.seq_length

        X = self.X[start_idx:end_idx, :]
        Y = self.Y[start_idx:end_idx]

        return X, Y
