import pandas as pd
from orders import Position
from typing import Union
from datetime import datetime


class BollingerBands():
    def __init__(
        self,
        data: pd.DataFrame,
        column: str = "Close",
        prefix: str = "price",
        dev: float = 1.0,
        periods: int = 50,
    ) -> None:
        """
        Inits attributes of class.
        data: dataframe with info
        column: column used to calculate strategy
        prefix: prefix used to store cols
        dev: standard deviation used
        periods: periods used for calculations.
        """
        self.data = data
        self.column = column
        self.prefix = prefix
        self.dev = dev
        self.periods = periods
        self.BBS = prefix + "|BBs|" + str(dev) + "|" + str(periods)
        self.BBS_distance = self.BBS + "|Distance"
        self.BBS_upper = self.BBS + "|Upper"
        self.BBS_lower = self.BBS + "|Lower"
        self.SMA = prefix + "|SMA|" + str(periods)
        self.last_position = Position.NEUTRAL

    def enough_info_to_predict(
        self,
        index: Union[datetime, pd.Timestamp]
    ) -> bool:
        """
        Tells if position can be predicted
        """
        idx_num = self.data.index.get_loc(index)
        return idx_num + 1 >= self.periods

    def calculate(self, force: bool = False) -> None:
        """Calculates strategy for all dataframe"""
        if self.BBS_distance in self.data.columns and not force:
            return

        if self.SMA not in self.data.columns or force:
            SM = self.data[self.column].rolling(self.periods)
            self.data[self.SMA] = SM.mean()

        std_dev = SM.std()
        self.data[self.BBS_lower] = self.data[self.SMA] - std_dev * self.dev
        self.data[self.BBS_upper] = self.data[self.SMA] + std_dev * self.dev
        self.data[
            self.BBS_distance
        ] = self.data[self.column] - self.data[self.SMA]

    def calculate_for_row(
        self,
        index: Union[datetime, pd.Timestamp]
    ) -> None:
        """Calculate strategy for some row using index"""
        index_num = self.data.index.get_loc(index)
        SM = self.data[self.column][
            index_num+1-self.periods:index_num+1
        ].rolling(self.periods)
        std_dev = SM.std().iloc[-1]
        sma = SM.mean().iloc[-1]

        self.data.loc[index, self.SMA] = sma
        self.data.loc[index, self.BBS_lower] = sma - std_dev * self.dev
        self.data.loc[index, self.BBS_upper] = sma + std_dev * self.dev
        self.data.loc[
            index, self.BBS_distance
        ] = self.data.loc[index, self.column] - sma

    def strategy(
        self,
        index: Union[datetime, pd.Timestamp]
    ) -> Position:
        '''Returns predicted position'''
        if not self.enough_info_to_predict(index=index):
            self.last_position = Position.NEUTRAL
            return self.last_position
        idx_num = self.data.index.get_loc(index)

        curr_value = self.data.loc[index, self.column]
        prev_distance = self.data[self.BBS_distance].iloc[idx_num-1]
        distance = self.data[self.BBS_distance].iloc[idx_num]

        if curr_value < self.data.loc[index, self.BBS_lower]:
            self.last_position = Position.LONG
        elif curr_value > self.data.loc[index, self.BBS_upper]:
            self.last_position = Position.SHORT
        elif distance * prev_distance < 0:
            self.last_position = Position.NEUTRAL
        return self.last_position
