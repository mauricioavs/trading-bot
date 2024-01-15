from binance_api import BinanceAPI
from typing import Any
from strategies import RNN
from orders import Position


class Tester(BinanceAPI):
    """
    This class includes test methods
    """
    def prepare_strategy(self) -> Any:
        """
        Prepare the strategy and return it.
        """
        strategy = RNN(
            data=self.data,
            model_dir='strategies/models/simple_current.h5',
            scaler_dir='strategies/models/scaler.pkl',
            scaler_obj_dir='strategies/models/scaler_obj.pkl'
        )
        strategy.load_model()
        strategy.calculate()
        # self.order_manager.change_leverage(5)
        return strategy

    def run_strategy(
        self,
        bar: int,
        strategy: Any
    ) -> Any:
        """
        Runs strategy given a bar.

        Returns strategy.
        """
        predicted_pos = strategy.strategy(row=bar)

        if predicted_pos == Position.LONG and not self.order_manager.currently_long:
            self.go_long(
                bar=bar,
                quote=100,
                wallet_prc=True,
                go_neutral_first=True,
                order_type="MARKET"
            )

        if predicted_pos == Position.SHORT and not self.order_manager.currently_short:
            self.go_short(
                bar=bar,
                quote=100,
                wallet_prc=True,
                go_neutral_first=True,
                order_type="MARKET"
            )
        return strategy
