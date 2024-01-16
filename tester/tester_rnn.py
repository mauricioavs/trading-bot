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
        strategy = dict()
        strategy["RNN"] = RNN(
            data=self.data,
            model_dir='strategies/models/simple_current.h5',
            scaler_dir='strategies/models/scaler.pkl',
            scaler_obj_dir='strategies/models/scaler_obj.pkl'
        )
        strategy["RNN"].load_model()
        strategy["RNN"].calculate()
        # self.order_manager.change_leverage(5)
        strategy["invest"] = self.max_invest(consider_closing=False) / 10
        strategy["pos_hist"] = [Position.NEUTRAL]
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
        predicted_pos = strategy["RNN"].strategy(row=bar)

        if predicted_pos == Position.LONG and self.order_manager.currently_short:
            self.go_neutral(bar=bar)
            # self.go_long(
            #     bar=bar,
            #     quote=strategy["invest"],
            #     wallet_prc=False,
            #     go_neutral_first=True,
            #     order_type="MARKET"
            # )

        elif predicted_pos == Position.SHORT and self.order_manager.currently_long:
            self.go_neutral(bar=bar)
            # self.go_short(
            #     bar=bar,
            #     quote=strategy["invest"],
            #     wallet_prc=False,
            #     go_neutral_first=True,
            #     order_type="MARKET"
            # )

        elif predicted_pos == Position.LONG and not self.order_manager.currently_long:
            # if strategy["pos_hist"][-1] == Position.LONG:
            self.go_neutral(bar=bar)
            strategy["invest"] = self.max_invest(consider_closing=False) / 10
            self.go_long(
                bar=bar,
                quote=strategy["invest"],
                wallet_prc=False,
                go_neutral_first=True,
                order_type="MARKET"
            )

        elif predicted_pos == Position.SHORT and not self.order_manager.currently_short:
            # if strategy["pos_hist"][-1] == Position.SHORT:
            self.go_neutral(bar=bar)
            strategy["invest"] = self.max_invest(consider_closing=False) / 10
            self.go_short(
                bar=bar,
                quote=strategy["invest"],
                wallet_prc=False,
                go_neutral_first=True,
                order_type="MARKET"
            )
        strategy["pos_hist"].append(predicted_pos)
        return strategy
