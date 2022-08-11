import torch.nn as nn
import torch.optim as optim

# Training Loop
def train(model: nn.Module, 
    data: DataLoader, 
    epochs: int, 
    optimizer: optim.Optimizer, 
    loss_fn: nn.Module) -> None:
    """
    Trains the model for the specified number of epochs
    Inputs
    ------
    model: RNN model to train
    data: Iterable DataLoader
    epochs: Number of epochs to train the model
    optiimizer: Optimizer to use for each epoch
    loss_fn: Function to calculate loss
    """
    train_losses = {}
    model.to(device)
    
    model.train()
    print("=> Starting training")
    for epoch in range(epochs):
        epoch_losses = list()
        for X, Y in data:
            # skip batch if it doesnt match with the batch_size
            if X.shape[0] != model.batch_size:
                continue
            hidden = model.init_zero_hidden(batch_size=model.batch_size)

            # send tensors to device
            X, Y, hidden = X.to(device), Y.to(device), hidden.to(device)

            # 2. clear gradients
            model.zero_grad()

            loss = 0
            for c in range(X.shape[1]):
                out, hidden = model(X[:, c].reshape(X.shape[0],1), hidden)
                l = loss_fn(out, Y[:, c].long())
                loss += l

            # 4. Compte gradients gradients
            loss.backward()

            # 5. Adjust learnable parameters
            # clip as well to avoid vanishing and exploding gradients
            nn.utils.clip_grad_norm_(model.parameters(), 3)
            optimizer.step()
        
            epoch_losses.append(loss.detach().item() / X.shape[1])

        train_losses[epoch] = torch.tensor(epoch_losses).mean()
        print(f'=> epoch: {epoch + 1}, loss: {train_losses[epoch]}')
        print(generate_text(model, data.dataset))