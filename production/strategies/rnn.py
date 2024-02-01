import pandas as pd
from orders import Position
from pydantic import (
    BaseModel,
    ConfigDict
)
import keras
from typing import List
from pickle import load
import numpy as np
from keras import Sequential
from sklearn.preprocessing import StandardScaler
from datetime import datetime


class RNN(BaseModel):
    """
    Stores the RNN model and has strategies to use it.

    Settings:
    model_config: Allows custom objects as attributes

    Init Attributes:
    model_dir: dir of rnn model
    scaler_dir: dir of data scaler
    scaler_obj_dir: dir of objective scaler

    Post-Init Attributes:
    model_name: rnn model
    scaler_name: data scaler
    scaler_obj_name: objective scaler

    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: pd.DataFrame
    model_dir: str
    scaler_dir: str
    scaler_obj_dir: str
    last_position: Position = Position.NEUTRAL
    column_name: str = "rnn"
    columns_to_use: List[str] = ['Close']

    model: Sequential = None
    scaler: StandardScaler = None
    scaler_obj: StandardScaler = None
    timestamps: int = None

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
        index: datetime
    ) -> None:
        """
        Calculate just for last row
        """
        index_num = self.data.index.get_loc(index)
        print("IDX_NUM1: ", str(index_num))
        inputs = self.data[index_num+1-self.timestamps:index_num+1].copy()[
            self.columns_to_use
        ]
        print("INPUTS: ")
        print(inputs)
        print("SHAPE: ")
        print(inputs.shape)
        inputs = self.scaler_obj.transform(inputs)
        X = np.array([inputs])
        predicted_position = self.model.predict(X, verbose=0)
        self.data.loc[index, self.column_name] = (
            self.scaler_obj.inverse_transform(
                predicted_position.reshape(-1, 1)
            )[0]
        )
        print("PREDICTION: ")
        print(self.data.loc[index, self.column_name])

    def strategy(
        self,
        index: datetime
    ) -> Position:
        '''
        Returns predicted position for a row.
        '''
        idx_num = self.data.index.get_loc(index)
        print("IDX_NUM2: ", str(idx_num))
        if not self.enough_info_to_predict(row=idx_num):
            self.last_position = Position.NEUTRAL
            return self.last_position

        current_price = self.data["Close"][idx_num]
        print("CURR_PRICE: ", str(current_price))
        previous_prediction = self.data[self.column_name][idx_num-1]
        print("PREV: ", str(previous_prediction))
        current_prediction = self.data[self.column_name][idx_num]
        print("CURR_PRED: ", str(current_prediction))
        diff = current_price - previous_prediction
        real_prediction = current_prediction + diff

        if real_prediction > current_price:
            self.last_position = Position.LONG
        elif real_prediction < current_price:
            self.last_position = Position.SHORT
        else:
            self.last_position = Position.NEUTRAL
        return self.last_position
