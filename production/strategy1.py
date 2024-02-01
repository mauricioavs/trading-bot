from futures_trader import FuturesTrader
from strategies import RNN
from orders import Position
from datetime import datetime


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
        self.strategy = dict()

        self.strategy["RNN"] = RNN(
            data=self.data,
            model_dir='strategies/models/simple_current.h5',
            scaler_dir='strategies/models/scaler.pkl',
            scaler_obj_dir='strategies/models/scaler_obj.pkl'
        )
        self.strategy["RNN"].load_model()
        self.strategy["RNN"].calculate()
        self.strategy["invest"] = self.get_max_invest() / 10

    def run_strategy(
        self,
        period_completed: bool,
        last_price: float,
        date: datetime
    ) -> None:
        """
        Implement this on child class.

        Runs strategy.
        """
        if not period_completed:
            return

        if self.currently_neutral:
            self.cancel_all_open_orders()
        else:
            self.cancel_all_open_orders()
            self.go_neutral(
                order_type="LIMIT",
                prc=100,
                price=last_price
            )
            return

        period = 12
        center_of_p = self.data.tail(period)["Close"].mean()
        low_of_p = min(self.data.tail(period)["Low"])
        high_of_p = max(self.data.tail(period)["High"])

        self.strategy["RNN"].calculate_for_row(index=date)
        predicted_pos = self.strategy["RNN"].strategy(index=date)
        print("PREDICTED_POS: ", predicted_pos)

        if predicted_pos == Position.LONG and self.currently_short:
            self.go_neutral(
                order_type="LIMIT",
                prc=100,
                price=low_of_p + abs(center_of_p - low_of_p) * 0.1
            )
            print(1)

        elif predicted_pos == Position.SHORT and self.currently_long:
            self.go_neutral(
                order_type="LIMIT",
                prc=100,
                price=high_of_p - abs(center_of_p - high_of_p) * 0.1
            )
            print(2)

        elif predicted_pos == Position.LONG and not self.currently_long:
            self.strategy["invest"] = self.get_max_invest() / 10
            self.go_long(
                order_type = "LIMIT",
                price=low_of_p + abs(center_of_p - low_of_p) * 0.1,
                quote=self.strategy["invest"],
                use_wallet_prc = False,
                reduceOnly = False,
            )
            self.go_stop_market(
                when_prc_reaches=99.0,
                close_previous=True
            )
            print(3)

        elif predicted_pos == Position.SHORT and not self.currently_short:
            self.strategy["invest"] = self.get_max_invest() / 10
            self.go_short(
                order_type = "LIMIT",
                price=high_of_p - abs(center_of_p - high_of_p) * 0.1,
                quote=self.strategy["invest"],
                use_wallet_prc = False,
                reduceOnly = False,
            )
            self.go_stop_market(
                when_prc_reaches=99.0,
                close_previous=True
            )
            print(4)
