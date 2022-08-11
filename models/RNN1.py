"""
This neural network is a regression RNN, this means it will predict the future 
stock price. It is up to you to decide how far into the future, it could be 1, 2
 or 10 sequences (defined timeframes) and each sequence can range from 
 1 minute to 1 day.
"""
import torch
import torch.nn as nn
import torch.optim as optim

class StockLSTM(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        