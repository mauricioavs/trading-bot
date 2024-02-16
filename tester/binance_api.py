from pydantic import (
    BaseModel,
    field_validator,
    ConfigDict
)
from binance.client import Client
import pandas as pd
from config.settings import API_KEY, SECRET_KEY
from orders import (
    OrderManager,
    OrderSystem,
    Position,
    OrderType
)
from orders.difficulty import Difficulty
from datetime import datetime
import numpy as np
from wallet import Wallet
from helpers import (
    MAX_INVEST_ERROR,
    REQUIRED_PARAM
)
from typing import Union, List, Any
import matplotlib.pyplot as plt


class BinanceAPI(BaseModel):
    """
    This class manages binance API methods.

    Note: In BTCUSDT and other pairs,
    BTC -> Base currency (first currency)
    USDT -> Quote currency (second currency)

    Settings:
    model_config: Allows custom objects as attributes

    Init Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSDT
    difficulty: Stores difficulty of simulation, see difficulty.py
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    system: Order behaviour:
        Netting: Orders are merged into one
        Hedging: Orders are separated
    fluctuation: Stores max difference of price in percentage:
                0 < fluctuation < 1 (validated in order)

    Attributes:
    client: Manages communication with Binance API. Used to load info
    wallet: Stores quote balance
    data: Data to be used in simulator. Load it with load_data method
    order_manager: Stores communication with orders
    position_history: Stores the position history
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    verbose: bool
    pair: str
    difficulty: Difficulty
    use_fee: bool
    fee_maker: float
    fee_taker: float
    system: OrderSystem = OrderSystem.NETTING
    fluctuation: float = 0.05

    client: Client = Client(
        api_key=API_KEY,
        api_secret=SECRET_KEY,
        tld="com",
        testnet=False
    )
    wallet: Wallet = Wallet()
    data: pd.DataFrame = None
    order_manager: OrderManager = None
    position_history: List = []

    @field_validator("pair", mode="before")
    def validate_pair(cls, value) -> str:
        """
        Returns fields in uppercase letters
        """
        return value.upper()

    def get_value(
        self,
        bar: int,
        column: str
    ) -> Any:
        """
        Returns a certain value of a column with bar index
        """
        if column == "Date":
            value = str(self.data.index[bar])
        else:
            value = round(self.data[column].iloc[bar], 5)
        return value

    def init_order_manager(self) -> None:
        """
        Inits order_manager to manage
        order methods.
        """
        self.order_manager = OrderManager(
            verbose=self.verbose,
            pair=self.pair,
            difficulty=self.difficulty,
            use_fee=self.use_fee,
            fee_maker=self.fee_maker,
            fee_taker=self.fee_taker,
            system=self.system,
            fluctuation=self.fluctuation
        )

    def init_wallet(
        self,
        initial_quote: float
    ) -> None:
        """
        Inits wallet balance
        """
        self.wallet = Wallet()
        self.wallet.set_initial_balance(
            quote=initial_quote
        )

    def print_message(self, message: str) -> None:
        """
        Prints messages if verbose is True
        """
        if self.verbose:
            print(message)

    def make_filename(
        self,
        interval_of_candles: str,
        start_date_utc: str,
        end_date_utc: str,
    ) -> str:
        """
        Makes filename with variables inside
        data dir.
        """
        filename = "_".join(
            [
                self.pair,
                str(interval_of_candles),
                start_date_utc,
                end_date_utc
            ]
        )
        return "data/" + filename + ".csv"

    def load_from_api(
        self,
        interval_of_candles: str,
        start_date_utc: str,
        end_date_utc: str,
    ) -> None:
        """
        Loads data from API.

        start_date_utc: start date UTC str year-month-day
        end_date_utc: end date UTC str year-month-day
        interval_of_candles: Could be 1m (minute), 1h (hour),
                            1d (day), etc. More at Binance API.
        """
        self.print_message("Trying to download info from API...")
        bars = self.client.futures_historical_klines(
            symbol=self.pair,
            interval=interval_of_candles,
            start_str=start_date_utc,
            end_str=end_date_utc
        )

        data = pd.DataFrame(bars)
        data["Date"] = pd.to_datetime(data.iloc[:, 0], unit="ms")
        data.columns = [
            "Open Time", "Open", "High", "Low", "Close", "Volume",
            "Close Time", "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume",
            "Ignore", "Date"
        ]

        use_columns = [
            "Date", "Open", "High", "Low", "Close", "Volume",
            "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume"
        ]

        data = data[use_columns].copy()
        data.set_index("Date", inplace=True)
        for column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

        data.to_csv(
            self.make_filename(
                interval_of_candles,
                start_date_utc,
                end_date_utc
            )
        )
        self.data = data
        return self.data

    def load_from_directory(
        self,
        interval_of_candles: str,
        start_date_utc: str,
        end_date_utc: str,
    ) -> None:
        """
        Loads data from directory.

        start_date_utc: start date UTC str year-month-day
        end_date_utc: end date UTC str year-month-day
        interval_of_candles: Could be 1m (minute), 1h (hour),
                            1d (day), etc. More at Binance API.
        """
        self.print_message("Trying to load info from directory...")
        filename_dir = self.make_filename(
            interval_of_candles,
            start_date_utc,
            end_date_utc
        )
        self.data = pd.read_csv(
            filename_dir,
            index_col="Date",
            parse_dates=["Date"]
        )
        return self.data

    def load_data(
        self,
        interval_of_candles: str,
        start_date_utc: str,
        end_date_utc: str,
    ) -> None:
        """
        Loads data from "data" directory, if not found,
        downloads info and stores it.

        start_date_utc: start date UTC str year-month-day
        end_date_utc: end date UTC str year-month-day
        interval_of_candles: Could be 1m (minute), 1h (hour),
                            1d (day), etc. More at Binance API.
        """
        try:
            self.load_from_directory(
                interval_of_candles=interval_of_candles,
                start_date_utc=start_date_utc,
                end_date_utc=end_date_utc
            )
        except FileNotFoundError:
            self.load_from_api(
                interval_of_candles=interval_of_candles,
                start_date_utc=start_date_utc,
                end_date_utc=end_date_utc
            )
        self.print_message("Data loaded.")
        return self.data

    def get_nav(
        self,
        bar: pd.Series
    ):
        """
        Gets net asset value: Total current balance
        considering open orders notional value in
        certain price and limit orders not executed.
        """
        low = bar["Low"]
        close = bar["Close"]
        high = bar["High"]
        inv_quote = self.order_manager.get_invested_margin_and_PnL(
            low=low,
            close=close,
            high=high
        )
        limit_quote = self.order_manager.get_limit_orders_margin()
        return self.wallet.balance + inv_quote + limit_quote

    def max_invest(
        self,
        position: Position = None,
        expected_exec_quote: float = None,
        consider_closing: bool = True
    ) -> float:
        """
        Returns the max invest quote considering the closing of
        positions
        """
        if consider_closing and not (position or expected_exec_quote):
            raise AttributeError(REQUIRED_PARAM)

        max_invest = self.wallet.balance * self.order_manager.leverage
        if consider_closing and self.order_manager.must_close_open_positions(
            requested_pos=position
        ):
            max_invest += self.order_manager.get_invested_not_val_quote(
                price=expected_exec_quote
            ) * (1 + self.fluctuation)
        return max_invest

    def can_invest(
        self,
        quote: float,
        expected_exec_quote: float,
        position: Position
    ) -> bool:
        """
        Tells if a quote could be spent considering
        available in wallet and open positions.
        """
        if self.order_manager.must_close_open_positions(
            requested_pos=position
        ):
            return True
        max_invest = self.max_invest(
            expected_exec_quote=expected_exec_quote,
            position=position
        )
        if max_invest + 1e-12 < quote:
            self.print_message(
                MAX_INVEST_ERROR.format(
                    str(round(quote, 2)),
                    str(round(max_invest, 2))
                )
            )
            return False

        return True

    def submit_order(
        self,
        creation_date: datetime,
        open: float,
        low: float,
        close: float,
        high: float,
        quote: float,
        position: Position,
        order_type: OrderType,
        expected_exec_quote: float,
        execution_date: datetime = None,
        use_prc_close: bool = False,
        reduce_only: bool = False
    ) -> float:
        """
        Submits an order to system.

        Returns the earnings or investment of order
        (could be negative).
        """
        if reduce_only or self.can_invest(
            quote=quote,
            expected_exec_quote=expected_exec_quote,
            position=position
        ):
            returns = self.order_manager.submit_order(
                creation_date=creation_date,
                open=open,
                low=low,
                close=close,
                high=high,
                quote=quote,
                position=position,
                order_type=order_type,
                expected_exec_quote=expected_exec_quote,
                execution_date=execution_date,
                use_prc_close=use_prc_close,
                reduce_only=reduce_only
            )
            self.wallet.update_balance(quote=returns)
            return
        self.print_message(
            self.wallet.cant_spend_msg(
                quote=quote
            )
        )

    def close_position(
        self,
        quote: float,
        bar: pd.Series,
        use_prc: bool = True,
        order_type: Union[OrderType, str] = OrderType.MARKET,
        expected_exec_quote: float = None
    ) -> None:
        """
        Closes a percentage of position or an amount of it.
        """
        if self.order_manager.currently_neutral:
            return

        if expected_exec_quote is None:
            expected_exec_quote = bar["Close"]

        self.submit_order(
            creation_date=bar["Date"],
            open=bar["Open"],
            low=bar["Low"],
            close=bar["Close"],
            expected_exec_quote=expected_exec_quote,
            high=bar["High"],
            quote=quote,
            position=self.order_manager.get_opposite_position,
            order_type=order_type,
            use_prc_close=use_prc,
            reduce_only=True
        )

    def go_neutral(
        self,
        bar: pd.Series,
        order_type: Union[OrderType, str] = OrderType.MARKET,
        expected_exec_quote: float = None
    ) -> None:
        """
        Closes all the opened positions
        """
        match self.system:
            case OrderSystem.NETTING:
                self.close_position(
                    quote=100.0,
                    bar=bar,
                    use_prc=True,
                    order_type=order_type,
                    expected_exec_quote=expected_exec_quote
                )

    def go_long(
        self,
        bar: pd.Series,
        quote: float,
        expected_exec_quote: float = None,
        wallet_prc: bool = False,
        go_neutral_first: bool = False,
        order_type: Union[OrderType, str] = OrderType.MARKET,
        reduce_only: bool = False
    ) -> None:
        """
        Submits a LONG position
        """
        if go_neutral_first:
            self.go_neutral(bar)

        if wallet_prc:
            quote = self.wallet.balance * quote / 100

        if expected_exec_quote is None:
            expected_exec_quote = bar["Close"]

        self.submit_order(
            creation_date=bar["Date"],
            open=bar["Open"],
            low=bar["Low"],
            close=bar["Close"],
            expected_exec_quote=expected_exec_quote,
            high=bar["High"],
            quote=quote,
            position=Position.LONG,
            order_type=order_type,
            use_prc_close=False,
            reduce_only=reduce_only
        )

    def go_short(
        self,
        bar: pd.Series,
        quote: float,
        expected_exec_quote: float = None,
        wallet_prc: bool = False,
        go_neutral_first: bool = False,
        order_type: Union[OrderType, str] = OrderType.MARKET,
        reduce_only: bool = False
    ) -> None:
        """
        Submits a LONG position
        """
        if go_neutral_first:
            self.go_neutral(bar)

        if wallet_prc:
            quote = self.wallet.balance * quote / 100

        if expected_exec_quote is None:
            expected_exec_quote = bar["Close"]

        self.submit_order(
            creation_date=bar["Date"],
            open=bar["Open"],
            low=bar["Low"],
            close=bar["Close"],
            expected_exec_quote=expected_exec_quote,
            high=bar["High"],
            quote=quote,
            position=Position.SHORT,
            order_type=order_type,
            use_prc_close=False,
            reduce_only=reduce_only
        )

    def print_final_result(self):
        profits = (self.wallet.balance - self.wallet.initial_balance)
        perf = profits/self.wallet.initial_balance * 100
        total_orders = 0
        good_orders = 0
        bad_orders = 0
        good_orders_prc = 0
        bad_orders_prc = 0
        times_liquidated = 0
        paid_fee = 0
        if self.order_manager.closed_orders:
            total_orders = len(self.order_manager.closed_orders)
            good_orders = sum(
                order.realized_PnL_with_fee > 0 for order
                in self.order_manager.closed_orders
            )
            good_orders_prc = round(good_orders / total_orders * 100, 1)
            bad_orders = total_orders - good_orders
            bad_orders_prc = round(100-good_orders_prc, 1)
            match self.system:
                case OrderSystem.NETTING:
                    times_liquidated = len(
                        set(
                            [
                                order.closed_at[-1] for order
                                in self.order_manager.closed_orders
                                if order.liquidated
                            ]
                        )
                    )
            paid_fee = sum(
                order.realized_fee > 0 for order
                in self.order_manager.closed_orders
            )

        if self.verbose:
            self.print_message(75 * "-")
            self.print_message("+++ CLOSING FINAL POSITION +++")
            self.print_message("net performance (%) = {}".format(
                    round(perf, 2)
                )
            )
            self.print_message("number of positions opened = {}".format(
                    total_orders
                )
            )
            self.print_message("times liquidated = {}".format(
                    times_liquidated
                )
            )
            self.print_message("number of good orders = {} ({}%)".format(
                    good_orders,
                    good_orders_prc
                )
            )
            self.print_message("number of bad orders = {} ({}%)".format(
                    bad_orders,
                    bad_orders_prc
                )
            )
            self.print_message(
                "Amount spent on fee = {} ({}% of initial balance)".format(
                    paid_fee, round(
                        paid_fee/self.wallet.initial_balance*100, 1
                    )
                )
             )
            self.print_message(75 * "-")

    def calculate_hold_strategy(
        self,
        initial_quote: float
    ) -> None:
        """
        Calculates hold strategy.
        """
        close = self.data.Close
        self.data["returns"] = np.log(close / close.shift(1))
        returns = self.data["returns"]
        self.data["Hold Strategy"] = (
            returns.cumsum().apply(np.exp) * initial_quote
        )

    def reset_params(
        self,
        interval_of_candles: str,
        start_date_utc: str,
        end_date_utc: str,
        initial_quote: float,
    ) -> None:
        """
        Resets params for a fresh data strategy.
        """
        self.load_data(
            interval_of_candles=interval_of_candles,
            start_date_utc=start_date_utc,
            end_date_utc=end_date_utc
        )
        self.calculate_hold_strategy(
            initial_quote=initial_quote
        )
        self.position_history = []
        self.init_order_manager()
        self.init_wallet(initial_quote=initial_quote)
        np.random.seed(1)

    def remove_limit_orders(self) -> float:
        """
        Removes limit orders not executed and returns the
        invested money to wallet.
        """
        returns = self.order_manager.remove_limit_orders()
        self.wallet.update_balance(
            quote=returns
        )

    def system_checks(self, bar: pd.Series) -> None:
        """
        Makes system checking like liquidation and
        limit order execution.

        The order is:
        - check liquidation
        - check limit orders
        - check again liquidation

        This is managed that way in order to give
        preference to liquidation on period.
        """
        # debo checar la liquidación primero o las limit orders???
        # tal vez deba ejecutar la limit order
        # si se alcanzó primero que la liquidación
        # si se liquida, tengo que cerrar todas las limit orders
        self.wallet.update_balance(
            quote=self.order_manager.check_liquidation(
                date=bar["Date"],
                low=bar["Low"],
                high=bar["High"]
            )
        )
        self.wallet.update_balance(
            quote=self.order_manager.check_limit_orders(
                open=bar["Open"],
                date=bar["Date"],
                low=bar["Low"],
                close=bar["Close"],
                high=bar["High"],
            )
        )
        self.wallet.update_balance(
            quote=self.order_manager.check_liquidation(
                date=bar["Date"],
                low=bar["Low"],
                high=bar["High"]
            )
        )

    def post_system_checks(self, bar: pd.Series) -> None:
        """
        System checking that runs after strategy.
        """
        self.wallet.history.append(
            self.get_nav(bar=bar)
        )
        self.position_history.append(self.order_manager.get_position)

    def test_strategy(
        self,
        interval_of_candles: str,
        start_date_utc: str,
        end_date_utc: str,
        initial_quote: float,
        initial_leverage: int = 1
    ) -> float:
        self.reset_params(
            interval_of_candles=interval_of_candles,
            start_date_utc=start_date_utc,
            end_date_utc=end_date_utc,
            initial_quote=initial_quote
        )
        self.order_manager.change_leverage(initial_leverage)
        self.print_message("-" * 75)
        self.print_message("Testing strategy | " + self.pair)
        self.print_message("-" * 75)

        strategy = self.prepare_strategy()
        for index, bar in self.data[:-1].iterrows():
            bar["Date"] = index
            self.system_checks(bar=bar)
            strategy = self.run_strategy(
                bar=bar,
                strategy=strategy
            )
            self.post_system_checks(bar=bar)

        last_bar = self.data.iloc[-1].copy()
        last_bar["Date"] = last_bar.name

        self.system_checks(bar=last_bar)
        self.remove_limit_orders()
        self.close_position(
            quote=100.0,
            bar=last_bar,
            use_prc=True,
            order_type=OrderType.MARKET
        )
        self.post_system_checks(bar=last_bar)
        self.print_final_result()

        return self.wallet.balance

    def plot_data(
        self,
        cols: Union[List[str], str] = ["Hold Strategy"],
        show_pos: bool = False
    ) -> None:
        """
        Plots columns of data
        """
        plt.figure(figsize=(12, 8))
        for col in cols:
            plt.plot(
                self.data.index,
                self.data[[col]],
                linewidth=1,
                label=col
            )
        if not show_pos:
            plt.plot(
                self.data.index,
                self.wallet.history,
                label="Strategy"
            )
        else:
            colors = [
                'green' if pos == Position.LONG
                else (
                    "red" if pos == Position.SHORT
                    else "gray"
                )
                for pos in self.position_history
            ]
            for i in range(1, len(self.data)):
                plt.plot(
                    self.data.iloc[i-1:i+1].index,
                    self.wallet.history[i-1:i+1],
                    c=colors[i-1],
                    linewidth=1,
                    label="Strategy" if i == 1 else None
                )
        plt.title(self.pair)
        plt.legend(loc="best")
        plt.show()

    def prepare_strategy(self) -> Any:
        """
        Implement this on child class.

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
        Implement this on child class.

        Runs strategy given a bar.

        Returns strategy.
        """
        pass
        return strategy
