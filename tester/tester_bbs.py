from binance_api import BinanceAPI
from typing import Any
import pandas as pd
from strategies import BollingerBands
from orders import Position


class Tester(BinanceAPI):
    """
    This class includes test methods
    """
    def prepare_strategy(self) -> Any:
        """
        Prepare the strategy and return it.
        """
        strategy = dict()
        strategy["strategy"] = BollingerBands(
            data=self.data,
            dev=2,
            periods=50,
            column="Close",
        )
        strategy["strategy"].calculate()
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
        if self.order_manager.currently_neutral:
            self.remove_limit_orders()

        idx_num = self.data.index.get_loc(bar["Date"])
        period = 24
        center_of_period = self.data[max(0, idx_num+1-period):idx_num+1]["Close"].mean()
        low_of_period = min(self.data[max(0, idx_num+1-period):idx_num+1]["Low"])
        high_of_period = max(self.data[max(0, idx_num+1-period):idx_num+1]["High"])

        predicted_pos = strategy["strategy"].strategy(index=bar["Date"])

        if predicted_pos == Position.LONG and self.order_manager.currently_neutral:
            strategy["invest"] = self.max_invest(consider_closing=False) / 10
            self.go_long(
                bar=bar,
                quote=strategy["invest"],
                wallet_prc=False,
                go_neutral_first=False,
                order_type="LIMIT",
                expected_exec_quote=low_of_period + abs(center_of_period - low_of_period) * 0.05
            )

        elif predicted_pos == Position.SHORT and self.order_manager.currently_neutral:
            strategy["invest"] = self.max_invest(consider_closing=False) / 10
            self.go_short(
                bar=bar,
                quote=strategy["invest"],
                wallet_prc=False,
                go_neutral_first=False,
                order_type="LIMIT",
                expected_exec_quote=high_of_period - abs(center_of_period - high_of_period) * 0.05
            )
        elif predicted_pos == Position.NEUTRAL and not self.order_manager.currently_neutral:
            self.remove_limit_orders()
            if self.order_manager.currently_long:
                execution = high_of_period - abs(center_of_period - high_of_period) * 0.05
            else:
                execution= low_of_period + abs(center_of_period - low_of_period) * 0.05
            self.go_neutral(
               bar=bar,
               order_type="LIMIT",
               expected_exec_quote=execution
            )

        return strategy
