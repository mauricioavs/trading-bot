import torch
import torch.nn as nn

class LSTM(nn.Module):
    """
    Basic RNN block
    """
    def __init__(self, input_size: int, 
        hidden_size: int, seq_length: int, 
        output_size: int = 1, num_layers: int = 1) -> None:
        """
        input_size: Number of features for your input vector
        hidden_size: Number of hidden neurons
        output_size: Number of features for your output vector
        """
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.seq_length = seq_length
        self.num_layers = num_layers

        self.rnn = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_size * seq_length, output_size)

    
    def forward(self, x) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns result for the whole sequence on the LSTM layer
        
        Input shape is (n_batches x seq_length x features)
        Inputs
        ------
        x: Input vector x  with shape (vocab_size, )
        hidden_state: Hidden state matrix

        Outputs
        -------
        out: Prediction vector
        """
        # initialize hidden and cell
        # and place them on the same device as the input x
        h0 = self.init_zero_hidden(x.shape[0]).to(x.device)
        c0 = self.init_zero_hidden(x.shape[0]).to(x.device)

        # Pass through LSTM
        out, _ = self.rnn(x, (h0, c0))

        # reshape to flatten hidden_size * seq_length
        out = out.reshape(out.shape[0], -1)

        # Decode the hidden state of the last time step
        out = self.linear(out)

        return out
        

    def init_zero_hidden(self, batch_size=1) -> torch.Tensor:
        """
        Returns a hidden state with specified batch size. Defaults to 1
        """
        return torch.zeros(self.num_layers, batch_size, self.hidden_size)