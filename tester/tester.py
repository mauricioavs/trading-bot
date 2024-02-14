from binance_api import BinanceAPI
from typing import Any
import pandas as pd


class Tester(BinanceAPI):
    """
    This class includes test methods
    """
    def prepare_strategy(self) -> Any:
        """
        Prepare the strategy and return it.
        """
        strategy = None
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
        pass
        return strategy
