from binance_api import BinanceAPI
from typing import Any
from strategies import RNN
from orders import Position
import pandas as pd
from helpers import get_weekday


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
            model_dir='strategies/models/feb-19/model.h5',
            scaler_dir='strategies/models/feb-19/scaler.pkl',
            scaler_obj_dir='strategies/models/feb-19/scaler-obj.pkl',
            strategies_dir='strategies/models/feb-19/ta-strategy.npy',
            columns_filename_dir='strategies/models/feb-19/col-names.npy'
        )
        strategy["RNN"].load_model()
        strategy["RNN"].calculate()
        # self.order_manager.change_leverage(5)
        # strategy["pos_hist"] = [Position.NEUTRAL]
        strategy["invest"] = self.max_invest(consider_closing=False) / 100
        return strategy

    def run_strategy(
        self,
        bar: pd.Series,
        strategy: Any
    ) -> Any:
        """
        Runs strategy given a bar.

        Always return strategy.
        """
        self.remove_limit_orders()
        if get_weekday(date=bar["Date"]) in ["None"]:
            self.go_neutral(
               bar=bar,
               order_type="LIMIT",
               expected_exec_quote=bar["Close"]
            )
            return strategy
        # if self.order_manager.currently_neutral:
        #     self.remove_limit_orders()

        # idx_num = self.data.index.get_loc(bar["Date"])
        # period = 72
        # center_of_period = self.data[max(0, idx_num+1-period):idx_num+1]["Close"].mean()
        # low_of_period = min(self.data[max(0, idx_num+1-period):idx_num+1]["Low"])
        # high_of_period = max(self.data[max(0, idx_num+1-period):idx_num+1]["High"])

        # if abs(low_of_period - high_of_period) / center_of_period < 0.01:
        #     return strategy

        predicted_pos = strategy["RNN"].strategy(index=bar["Date"])

        if self.order_manager.currently_neutral:
            if predicted_pos == Position.LONG:
                self.go_long(
                    bar=bar,
                    quote=strategy["invest"],
                    wallet_prc=False,
                    go_neutral_first=False,
                    order_type="LIMIT",
                    expected_exec_quote=bar["Low"] # low_of_period + abs(center_of_period - low_of_period) * 0.1
                )
            elif predicted_pos == Position.SHORT:
                self.go_short(
                    bar=bar,
                    quote=strategy["invest"],
                    wallet_prc=False,
                    go_neutral_first=False,
                    order_type="LIMIT",
                    expected_exec_quote=bar["High"] # high_of_period - abs(center_of_period - high_of_period) * 0.1
                )


        # elif predicted_pos == Position.LONG and self.order_manager.currently_long and self.order_manager.get_PnL(price=bar["Close"]) < -self.order_manager.open_margin_quote * 0.7:
        #     # if strategy["pos_hist"][-1] == Position.LONG:
        #     # self.go_neutral(bar=bar)
        #     # strategy["invest"] = self.max_invest(consider_closing=False) / 100
        #     # self.go_neutral(
        #     #    bar=bar,
        #     #    order_type="LIMIT",
        #     #    expected_exec_quote=bar["Close"]
        #     # )
        #     self.go_long(
        #         bar=bar,
        #         quote=strategy["invest"],
        #         wallet_prc=False,
        #         go_neutral_first=False,
        #         order_type="LIMIT",
        #         expected_exec_quote=bar["Low"] # low_of_period + abs(center_of_period - low_of_period) * 0.0
        #     )

        # elif predicted_pos == Position.SHORT and self.order_manager.currently_short and self.order_manager.get_PnL(price=bar["Close"]) < -self.order_manager.open_margin_quote * 0.7:
        #     # if strategy["pos_hist"][-1] == Position.SHORT:
        #     # self.go_neutral(bar=bar)
        #     # strategy["invest"] = self.max_invest(consider_closing=False) / 100
        #     # self.go_neutral(
        #     #    bar=bar,
        #     #    order_type="LIMIT",
        #     #    expected_exec_quote=bar["Close"]
        #     # )
        #     self.go_short(
        #         bar=bar,
        #         quote=strategy["invest"],
        #         wallet_prc=False,
        #         go_neutral_first=False,
        #         order_type="LIMIT",
        #         expected_exec_quote=bar["High"] # high_of_period - abs(center_of_period - high_of_period) * 0.0
        #     )
        else: #self.order_manager.get_PnL(price=bar["Close"]) > 0: # self.order_manager.open_margin_quote * 0.5:
            self.go_neutral(
               bar=bar,
               order_type="LIMIT",
               expected_exec_quote=bar["Close"]
            )
        # else:
        #     self.remove_limit_orders()
        #     if self.order_manager.currently_long:
        #         execution = high_of_period - abs(center_of_period - high_of_period) * 0.2
        #     else:
        #         execution= low_of_period + abs(center_of_period - low_of_period) * 0.2
        #     self.go_neutral(
        #        bar=bar,
        #        order_type="LIMIT",
        #        expected_exec_quote=execution # bar["Close"]
        #     )

        # strategy["pos_hist"].append(predicted_pos)
        return strategy

