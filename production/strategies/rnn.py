import pandas as pd
from orders import Position
from pydantic import (
    BaseModel,
    ConfigDict
)
import keras
from typing import List, Union
from pickle import load
import numpy as np
from keras import Sequential
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import pandas_ta as ta


class RNN(BaseModel):
    """
    Stores the RNN model and has strategies to use it.

    Settings:
    model_config: Allows custom objects as attributes

    Init Attributes:
    model_dir: dir of rnn model
    scaler_dir: dir of data scaler
    scaler_obj_dir: dir of objective scaler
    strategies_dir: file where strategies array is stored
    columns_filename_dir: File where columns are stored
    last_position: stores last position
    column_name: Column where prediction is saved

    Post-Init Attributes:
    model: Architecture of model
    scaler: data scaler
    scaler_obj: objective scaler
    timestamps: Timestamps of model
    columns_to_use: columns to use of model

    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: pd.DataFrame
    model_dir: str
    scaler_dir: str
    scaler_obj_dir: str
    strategies_dir: str = None
    columns_filename_dir: str = None
    last_position: Position = Position.NEUTRAL
    column_name: str = "rnn"

    model: Sequential = None
    scaler: StandardScaler = None
    scaler_obj: StandardScaler = None
    timestamps: int = None
    columns_to_use: List[str] = ['Close']

    def load_model(self) -> None:
        """
        Loads model and stores it on model
        """
        self.model = keras.models.load_model(
            self.model_dir,
            compile=False
        )
        self.scaler = load(open(self.scaler_dir, 'rb'))
        self.scaler_obj = load(open(self.scaler_obj_dir, 'rb'))
        self.timestamps = self.model.layers[0].input_shape[1]
        if self.strategies_dir:
            strategies = list(np.load(self.strategies_dir, allow_pickle=True))
            CustomStrategy = ta.Strategy(name="custom", ta=strategies)
            self.data.ta.strategy(CustomStrategy)
        if self.columns_filename_dir:
            self.columns_to_use = np.load(self.columns_filename_dir)

    def enough_info_to_predict(
        self,
        row: int
    ) -> bool:
        """
        Tells if row can be predicted by model
        """
        return row + 1 >= self.timestamps

    def calculate(self, force=False) -> None:
        """
        1. Gets data and scales it
        2. Prepares timeseries
        3. Predicts position for each timeseries
        4. Unscale result
        5. Put info in dataframe
        """
        if self.column_name in self.data.columns and not force:
            return

        inputs = self.data[self.columns_to_use].copy()
        inputs = self.scaler.transform(inputs)

        X = []
        for i in range(self.timestamps, len(inputs)+1):
            X.append(inputs[i-self.timestamps:i])
        X = np.array(X)

        predicted_position = np.concatenate((
            [np.nan]*(self.timestamps-1), self.model.predict(
                X, verbose=0
            ).flatten()
        ))
        self.data[self.column_name] = self.scaler_obj.inverse_transform(
            predicted_position.reshape(-1, 1)
        )

    def calculate_for_row(
        self,
        index: Union[datetime, pd.Timestamp]
    ) -> None:
        """
        Calculate for row...
        """
        index_num = self.data.index.get_loc(index)
        inputs = self.data[index_num+1-self.timestamps:index_num+1].copy()[
            self.columns_to_use
        ]
        inputs = self.scaler_obj.transform(inputs)
        X = np.array([inputs])
        predicted_position = self.model.predict(X, verbose=0)
        self.data.loc[index, self.column_name] = (
            self.scaler_obj.inverse_transform(
                predicted_position.reshape(-1, 1)
            )[0]
        )

    def strategy(
        self,
        index: Union[datetime, pd.Timestamp]
    ) -> Position:
        '''
        Returns predicted position for a row.
        '''
        idx_num = self.data.index.get_loc(index)
        if not self.enough_info_to_predict(row=idx_num):
            self.last_position = Position.NEUTRAL
            return self.last_position
        prev_index = self.data.index[idx_num-1]
        current_price = self.data.loc[index, "Close"]
        previous_prediction = self.data.loc[prev_index, self.column_name]
        current_prediction = self.data.loc[index, self.column_name]
        diff = current_price - previous_prediction
        real_prediction = current_prediction + diff

        if real_prediction > current_price:
            self.last_position = Position.LONG
        elif real_prediction < current_price:
            self.last_position = Position.SHORT
        else:
            self.last_position = Position.NEUTRAL
        return self.last_position
