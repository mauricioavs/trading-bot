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
        This prepares strategy.
        """
        strategy = dict()
        strategy["strategy"] = {7.5: 20}
        strategy["stop"] = False
        return strategy

    def run_strategy(
        self,
        bar: pd.Series,
        strategy: Any
    ) -> Any:
        """
        Runs strategy given a bar.
        Updates strategy for the next execution.

        Returns strategy.
        """
        date_prev_24h = bar["Date"] - pd.Timedelta(hours=24)
        try:
            prev24h_bar = self.data.loc[date_prev_24h]
        except KeyError:
            return strategy
        chg24h = (bar["Close"] - prev24h_bar["Close"])/prev24h_bar["Close"] * 100

        if self.order_manager.currently_neutral:
            strategy["min_invest"] = self.max_invest(consider_closing=False) / 100
            strategy["curr_strategy"] = []
            strategy["roi"] = None
            strategy["min_roi"] = -10
            if strategy["stop"] * chg24h > 0:
                strategy["stop"] = False
            elif strategy["stop"]:
               return strategy 


        if not self.order_manager.currently_neutral:
            current_roi = self.order_manager.get_ROI(low=bar["Low"], high=bar["High"], close=bar["Close"])

            if current_roi > 1 or current_roi < -30:
                strategy["stop"] = 1 if self.order_manager.currently_long else -1
                self.go_neutral(
                    bar=bar,
                    order_type="LIMIT",
                    expected_exec_quote=bar["Close"]
                )
                return strategy

            # current_multiple_of_10 = int(current_roi // 20) * 10
            # strategy["min_roi"] = max(current_multiple_of_10 - 10, strategy["min_roi"])

            # if current_roi < strategy["min_roi"]:
            #     strategy["stop"] = 1 if self.order_manager.currently_long else -1
            #     self.go_neutral(
            #         bar=bar,
            #         order_type="LIMIT",
            #         expected_exec_quote=bar["Close"]
            #     )
            #     return strategy

            # if strategy["roi"] is None:
            #     strategy["roi"] = current_roi
            # elif current_roi < strategy["roi"]:
            #     strategy["stop"] = 1 if self.order_manager.currently_long else -1
            #     self.go_neutral(
            #         bar=bar,
            #         order_type="LIMIT",
            #         expected_exec_quote=bar["Close"]
            #     )
            #     return strategy
            # elif current_roi > strategy["roi"]:
            #     strategy["roi"] = current_roi
        

        for change_lvl, multiplier in strategy["strategy"].items():
            if abs(chg24h) < change_lvl or change_lvl * np.sign(chg24h) in strategy["curr_strategy"]:
                continue
            strategy["curr_strategy"].append( change_lvl * np.sign(chg24h) )

            # if np.sign(chg24h) * np.sign(strategy["curr_strategy"][0]) == -1:
            #     self.go_neutral(
            #         bar=bar,
            #         order_type="LIMIT",
            #         expected_exec_quote=bar["Close"]
            #     )

            if chg24h > 0:
                self.go_short(
                    bar=bar,
                    quote=strategy["min_invest"] * multiplier,
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
