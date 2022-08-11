"""
This neural network is a regression RNN, this means it will predict the future 
stock price. It is up to you to decide how far into the future, it could be 1, 2
 or 10 sequences (defined timeframes) and each sequence can range from 
 1 minute to 1 day.
"""
import torch
import torch.nn as nn

class StockRNN(nn.Module):
    """
    Basic RNN block
    """
    def __init__(self, input_size: int, hidden_size: int, output_size: int) -> None:
        """
        input_size: Number of features for your input vector
        hidden_size: Number of hidden neurons
        output_size: Number of features for your output vector
        """
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        self.i2h = nn.Linear(input_size, hidden_size, bias=False)
        self.h2h = nn.Linear(hidden_size, hidden_size)
        self.h2o = nn.Linear(hidden_size, output_size)

    
    def forward(self, x, hidden_state) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns Linear output and tanh(i2h + i2o) hidden state
        
        Inputs
        ------
        x: Input vector x  with shape (vocab_size, )
        hidden_state: Hidden state matrix
        Outputs
        -------
        out: Prediction vector
        hidden_state: New hidden state matrix
        """
        x = self.i2h(x)
        hidden_state = self.h2h(hidden_state)
        hidden_state = torch.tanh(x + hidden_state)
        x = self.h2o(hidden_state)
        return x, hidden_state
        

    def init_zero_hidden(self, batch_size=1) -> torch.Tensor:
        """
        Returns a hidden state with specified batch size. Defaults to 1
        """
        return torch.zeros(batch_size, self.hidden_size, requires_grad=False)