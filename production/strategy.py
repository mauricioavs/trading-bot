from futures_trader import FuturesTrader


class Strategy(FuturesTrader):
    """
    Stores the strategy using
    FuturesTrader methods.
    """
    def prepare_strategy(self) -> None:
        """
        Implement this on child class.

        Prepare the strategy and return it.
        """
        self.strategy = None

    def run_strategy(
        self,
        period_completed: bool
    ) -> None:
        """
        Implement this on child class.

        Runs strategy.
        """
        if not period_completed:
            return
        self.strategy = None
