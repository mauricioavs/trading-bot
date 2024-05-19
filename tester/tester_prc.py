from binance_api import BinanceAPI
from typing import Any
import pandas as pd
import numpy as np


class Tester(BinanceAPI):
    """
    This class includes test methods
    """
    def prepare_strategy(self) -> Any:
        """
        Prepare the strategy and return it.
        """
        strategy = dict()
        strategy["strategy"] = { 2.5:1, 5: 4, 7.5: 8}
        strategy["min_invest"] = self.max_invest(consider_closing=False) / 100
        strategy["curr_strategy"] = []
        return strategy

    def run_strategy(
        self,
        bar: pd.Series,
        strategy: Any
    ) -> Any:
        """
        Runs strategy given a bar.

        Returns strategy.
        """
        date_prev_24h = bar["Date"] - pd.Timedelta(hours=24)
        try:
            prev24h_bar = self.data.loc[date_prev_24h]
        except KeyError:
            return strategy
        
        chg24h = (bar["Close"] - prev24h_bar["Close"])/prev24h_bar["Close"] * 100

        for change_lvl, multiplier in strategy["strategy"].items():
            if abs(chg24h) < change_lvl or change_lvl * np.sign(chg24h) in strategy["curr_strategy"]:
                continue
            if strategy["curr_strategy"] and np.sign(strategy["curr_strategy"][0]) != np.sign(chg24h):
                self.go_neutral(
                    bar=bar,
                    order_type="LIMIT",
                    expected_exec_quote=bar["Close"]
                )
                strategy["curr_strategy"] = []
                strategy["min_invest"] = self.max_invest(consider_closing=False) / 100

            strategy["curr_strategy"].append( change_lvl * np.sign(chg24h) )
            if chg24h > 0:
                self.go_short(
                    bar=bar,
                    quote=strategy["min_invest"]*multiplier,
                    wallet_prc=False,
                    go_neutral_first=False,
                    order_type="LIMIT",
                    expected_exec_quote=bar["Close"]
                )
            else:
                self.go_long(
                    bar=bar,
                    quote=strategy["min_invest"] * multiplier,
                    wallet_prc=False,
                    go_neutral_first=False,
                    order_type="LIMIT",
                    expected_exec_quote=bar["Close"]
                )

        return strategy
