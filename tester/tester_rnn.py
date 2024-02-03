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
            model_dir='strategies/models/simple_current-feb-2.h5',
            scaler_dir='strategies/models/scaler-feb-2.pkl',
            scaler_obj_dir='strategies/models/scaler_obj-feb-2.pkl'
        )
        strategy["RNN"].load_model()
        strategy["RNN"].calculate()
        # self.order_manager.change_leverage(5)
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
        if self.order_manager.currently_neutral:
            self.remove_limit_orders()

        else:
            self.remove_limit_orders()
            self.go_neutral(
               bar=bar,
               order_type="LIMIT",
               expected_exec_quote=None
            )
            return strategy

        period = 12
        center_of_period = self.data[max(0, bar+1-period):bar+1]["Close"].mean()
        low_of_period = min(self.data[max(0, bar+1-period):bar+1]["Low"])
        high_of_period = max(self.data[max(0, bar+1-period):bar+1]["High"])
        predicted_pos = strategy["RNN"].strategy(row=bar)

        # if predicted_pos == Position.LONG and self.order_manager.currently_short:
        #     self.go_neutral(
        #         bar=bar,
        #         order_type="LIMIT",
        #         expected_exec_quote=low_of_period + abs(center_of_period - low_of_period) * 0.1
        #     )

        # elif predicted_pos == Position.SHORT and self.order_manager.currently_long:
        #     self.go_neutral(
        #         bar=bar,
        #         order_type="LIMIT",
        #         expected_exec_quote=high_of_period - abs(center_of_period - high_of_period) * 0.1
        #     )

        if predicted_pos == Position.LONG and not self.order_manager.currently_long:
            # if strategy["pos_hist"][-1] == Position.LONG:
            # self.go_neutral(bar=bar)
            strategy["invest"] = self.max_invest(consider_closing=False) / 5
            self.go_long(
                bar=bar,
                quote=strategy["invest"],
                wallet_prc=False,
                go_neutral_first=True,
                order_type="LIMIT",
                expected_exec_quote=low_of_period + abs(center_of_period - low_of_period) * 0.1

            )

        elif predicted_pos == Position.SHORT and not self.order_manager.currently_short:
            # if strategy["pos_hist"][-1] == Position.SHORT:
            # self.go_neutral(bar=bar)
            strategy["invest"] = self.max_invest(consider_closing=False) / 5
            self.go_short(
                bar=bar,
                quote=strategy["invest"],
                wallet_prc=False,
                go_neutral_first=True,
                order_type="LIMIT",
                expected_exec_quote=high_of_period - abs(center_of_period - high_of_period) * 0.1
            )
        # strategy["pos_hist"].append(predicted_pos)
        return strategy
