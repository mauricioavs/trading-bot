from pandas import DataFrame
import numpy as np

def preprocess_df (
    dataframe: DataFrame,
    index_col: str ="Date", 
    keep_cols: list[str] = ["Close", "Volume"], 
    future_n_rows: int = 0
    ) -> DataFrame:
    """
    Preprocess dataframe so we can use in in the neural network

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
    if index_col != None:
        dataframe.set_index(index_col, inplace=True)
    
    dataframe = dataframe[keep_cols]

    if future_n_rows > 0:
        dataframe['future'] = dataframe['Close'].shift(-future_n_rows)
        # drop last future_n_days columns since they dont have "futures" col
        dataframe = dataframe.iloc[:-future_n_rows]

    return dataframe

def split_np_matrix(data: np.ndarray, test_percent: int = 5) -> tuple[np.ndarray, np.ndarray]:
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
    