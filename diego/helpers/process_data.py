import pandas as pd
import numpy as np
from sklearn.base import TransformerMixin

def process_df (
    dataframe: pd.DataFrame,
    index_col: str = "Date",
    keep_cols: list[str] = ["Close", "Volume"],
    scaler: TransformerMixin | None = None,
    future_n_rows: int = 0
    ) -> pd.DataFrame:
    """
    Preprocess dataframe so we can use in in the neural network
    It also standardizes and normalize the inputs

    Arguments
    ---
    index_col: Index column
    keep_cols: Columns which will be kept on the final dataframe
    future_n_rows: if set, a 'future' column gets created with the 
                   Close value for the next n days

    Returns
    ---
    Dataframe
    """
    # copy dataframe to avoid updating in place the original one
    dataframe = dataframe.copy()

    if index_col != None:
        dataframe.set_index(index_col, inplace=True)
    
    dataframe = dataframe[keep_cols]

    # scale and place it into a pandas dataframe instead of numpy array
    if scaler:
        df_scaled = pd.DataFrame(scaler.fit_transform(dataframe),
            columns = dataframe.columns)

        dataframe = df_scaled

    if future_n_rows > 0:
        dataframe['future_close'] = dataframe['Close'].shift(-future_n_rows)
        # drop last future_n_days columns since they dont have "futures" col
        dataframe = dataframe.iloc[:-future_n_rows]

    return dataframe

def split_data(data: np.ndarray, test_percent: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """
    Gets the full numpy matrix and splits it into train and test
    
    Returned values are grabbed sequentially, not randomly, which means
    that 'test_percent' grabs the last 5 percent of data by default.

    Inputs
    ---
    data: numpy array containing all your data
    test_percent: percentage of data which will be used for the test set

    Outputs
    ---
    train_data: training data as numpy array
    test_data: test data as numpy array
    """
    split_index = int(data.shape[0] * ((100-test_percent) / 100))
    train_data = data[0: split_index, :]
    test_data = data[split_index:, :]
    return train_data, test_data
    