from config.settings import (
    TEST_API_KEY, TEST_SECRET_KEY,
    API_KEY, SECRET_KEY,
)
from binance.client import Client
from binance.websocket.um_futures.websocket_client import (
    UMFuturesWebsocketClient
)
from helpers import (
    INVALID_PAIR,
    LESS_THAN_MIN,
    INVALID_ORDER_TYPE,
    ERROR_STOP_MARKET,
    INVALID_PERIOD,
    CHOOSE_ONE_WALLET_PRC,
    is_zero,
    available_periods
)
import pandas as pd
import requests
from orders import Position, MIN_ORDERS
from datetime import datetime
import json


class FuturesTrader():
    """
    Contains methods to make a Futures connection.

    Init Attributes:
    pair: Use some pair like BTCUSDT
    heartbeat_url: Statuscake URL to make push requests
    heartbeat_period: Stores the seconds period of the
                    heartbeat
    testnet: Tells if connection must be to testnet
    verbose: Print relevant actions

    Attributes:
    client: Stores connection
    quote: stores the quote of the pair
    last_heartbeat: Stores the datetime of last heartbeat
    strategy: Stores the strategy
    stream:
    data: Stores historical candle data
    min_base_open: min base to buy
    strategy: Stores strategy info for message handler.
    history: Saves actions like last orders submitted.
    """

    def __init__(
        self,
        pair: str,
        heartbeat_url: str,
        heartbeat_period: int = 300,
        testnet: bool = True,
        verbose: bool = True
    ) -> None:
        self.pair: str = pair.upper()
        self.heartbeat_url: str = heartbeat_url
        self.heartbeat_period: int = heartbeat_period
        self.testnet: bool = testnet
        self.verbose: bool = verbose

        self.client: Client = self.init_client()
        self.quote = self.get_quote_symbol(self.pair)
        self.last_heartbeat: datetime = datetime.now()
        self.strategy: dict = dict()
        self.stream: UMFuturesWebsocketClient = None
        self.data: pd.DataFrame = None
        self.min_base_open = MIN_ORDERS.get_min_units(self.pair)
        self.strategy = None
        self.history = dict()

    def init_client(self) -> Client:
        """
        Inits Binance client depending
        on testnet value.
        """
        test = self.testnet
        return Client(
            api_key=TEST_API_KEY if test else API_KEY,
            api_secret=TEST_SECRET_KEY if test else SECRET_KEY,
            tld="com",
            testnet=test
        )

    def print_message(self, msg: str, **kwargs) -> None:
        """
        Prints message if verbose is True.
        """
        if self.verbose:
            print(msg, **kwargs)

    def get_quote_symbol(
        self,
        pair: str
    ) -> str:
        """
        given a pair, returns the quote in uppercase
        """
        pair = pair.upper()
        quotes = [
            "BUSD",
            "USDT",
            "ETH",
            "BNB",
            "BTC"
        ]
        for quote in quotes:
            if pair.endswith(quote):
                return quote
        raise ValueError(INVALID_PAIR)

    def get_pos_info(self) -> dict:
        """
        Gets real time position size.
        """
        infos = self.client.futures_position_information(
            symbol=self.pair
        )
        response = {
            "size_base": 0,
            "position": Position.NEUTRAL

        }
        for info in infos:
            if info["symbol"] == self.pair:
                size_base = float(info["positionAmt"])
                response["size_base"] += abs(size_base)
                if size_base > 0:
                    response["position"] = Position.LONG
                elif size_base < 0:
                    response["position"] = Position.SHORT
                response["leverage"] = int(info["leverage"])
        return response

    def get_position(self) -> Position:
        """
        Gets LONG, SHORT or NEUTRAL
        """
        return self.get_pos_info()["position"]

    @property
    def currently_neutral(self) -> bool:
        """
        Tells if no current position
        """
        return self.get_position() == Position.NEUTRAL

    @property
    def currently_long(self) -> bool:
        """
        Tells if current long position
        """
        return self.get_position() == Position.LONG

    @property
    def currently_short(self) -> bool:
        """
        Tells if current short position
        """
        return self.get_position() == Position.SHORT

    def get_opposite_position(self) -> Position:
        """
        Gets opposite position.
        """
        match self.get_position():
            case Position.NEUTRAL:
                return Position.NEUTRAL
            case Position.LONG:
                return Position.SHORT
            case Position.SHORT:
                return Position.LONG

    def get_open_base(self) -> float:
        """
        Gets absolute open base
        """
        return self.get_pos_info()["size_base"]

    def get_current_balance(self) -> float:
        """
        Gets current quote balance.
        Includes the amount of positions
        """
        balance = pd.DataFrame(self.client.futures_account_balance())
        quote = float(
            balance[balance["asset"] == self.quote].iloc[0]["balance"]
        )
        return quote

    def get_available_balance(self) -> float:
        """
        Gets current quote balance.
        Includes just wallet available balance.
        """
        balance = pd.DataFrame(self.client.futures_account_balance())
        quote = float(
            balance[balance["asset"] == self.quote].iloc[0][
                "availableBalance"
            ]
        )
        return quote

    def get_current_leverage(self) -> int:
        """
        Gets current leverage
        """
        response = self.get_pos_info()
        return response["leverage"]

    def get_max_invest(self) -> float:
        """
        Gets max invest considering just wallet
        balance and leverage
        """
        wallet = self.get_available_balance()
        lev = self.get_current_leverage()

        return wallet * lev

    def get_liquidation_price(self) -> float:
        """
        Gets current liquidation price.
        """
        liq_price = float(
            self.client.futures_position_information(
                symbol=self.pair
            )[0]["liquidationPrice"]
        )
        return liq_price

    def get_entry_price(self) -> float:
        """
        Gets current entry price.
        """
        entry_price = float(
            self.client.futures_position_information(
                symbol=self.pair
            )[0]["entryPrice"]
        )
        return entry_price

    def change_leverage(
        self,
        new_leverage: int
    ):
        """
        Changes leverage.

        Be aware that:
        - you can't decrease lev with
            open positions
        """
        self.client.futures_change_leverage(
            symbol=self.pair,
            leverage=new_leverage
        )
        return self.get_current_leverage()

    def get_most_recent_data(
        self,
        num_candles: int = 100,
        interval: str = "1m"
    ) -> None:
        now = datetime.utcnow()
        past = str(now - available_periods(num_candles)[interval])

        bars = self.client.futures_historical_klines(
            symbol=self.pair.lower(),
            interval=interval,
            start_str=past,
            end_str=None
        )
        df = pd.DataFrame(bars)
        df["Date"] = pd.to_datetime(df.iloc[:, 0], unit="ms")
        df.columns = [
            "Open Time", "Open", "High", "Low",
            "Close", "Volume", "Close Time",
            "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume",
            "Taker Buy Quote Asset Volume", "Ignore", "Date"
        ]
        use_columns = ["Date"] + list(self.cols_to_use().keys())
        df = df[use_columns].copy()
        df.set_index("Date", inplace=True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["Complete"] = [True for row in range(len(df)-1)] + [pd.NA]
        self.data = df

    def start_streaming(
        self,
        interval="1m"
    ) -> None:
        """
        Starts streaming of Binance.
        """
        self.stream = UMFuturesWebsocketClient(
            on_message=self.message_handler
        )
        self.stream.kline(
            symbol=self.pair,
            id=1,
            interval=interval
        )

    def stop_streaming(self) -> None:
        """
        Stops streaming of Binance.
        """
        self.stream.stop()

    def start_trading(
        self,
        interval: str,
        initial_lev: int = 1,
        num_candles: int = 1000,
    ) -> None:
        """
        Starts trading session
        """
        if interval not in available_periods(num_candles).keys():
            self.print_message(INVALID_PERIOD)
            return
        self.get_most_recent_data(
            num_candles=num_candles,
            interval=interval
        )
        self.change_leverage(new_leverage=initial_lev)
        self.prepare_strategy()
        self.start_streaming(interval)

    def stop_trading(self, go_neutral: bool = False) -> None:
        """
        Stops trading
        """
        self.stop_streaming()
        self.cancel_all_open_orders()
        if go_neutral:
            self.go_neutral()

    def skip_first_message(self, msg: dict) -> bool:
        """
        Skips first confirmation message of streaming
        """
        return 'result' in msg.keys()

    def send_heartbeat(self) -> None:
        """
        Send push request to Statuscake url and
        updates last heartbeat.
        """
        requests.get(url=self.heartbeat_url)
        self.last_heartbeat = datetime.now()

    def manage_heartbeat(
        self,
        current_datetime: datetime
    ) -> None:
        """
        Send requests to Statuscake in order to guarantee
        that task is still running.
        """
        if self.testnet:
            return
        time_elapsed = current_datetime - self.last_heartbeat
        if time_elapsed.seconds > self.heartbeat_period:
            self.send_heartbeat()
    
    def cols_to_use(
        self,
        oopen: float = pd.NA,
        high: float = pd.NA,
        low: float = pd.NA,
        close: float = pd.NA,
        volume: float = pd.NA,
        QAVol: float = pd.NA,
        NoT: float = pd.NA,
        TBBAV: float = pd.NA,
        TBQAV: float = pd.NA
    ) -> dict:
        """
        Columns to use, do not include Date here
        because it is used to index in get_most_recent_data
        function.
        """
        return {
            "Open": oopen,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
            "Quote Asset Volume": QAVol,
            "Number of Trades": NoT,
            "Taker Buy Base Asset Volume": TBBAV,
            "Taker Buy Quote Asset Volume": TBQAV
        }

    def message_handler(self, _, msg: dict) -> None:
        """
        Handles the streaming
        """
        msg = json.loads(msg)
        if self.skip_first_message(msg=msg):
            return
        self.print_message(msg=".", end="", flush=True)

        event_time = pd.to_datetime(msg["E"], unit="ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit="ms")
        oopen = float(msg["k"]["o"])
        high = float(msg["k"]["h"])
        low = float(msg["k"]["l"])
        close = float(msg["k"]["c"])
        volume = float(msg["k"]["v"])

        QAVol = float(msg["k"]["q"])
        NoT = float(msg["k"]["n"])
        TBBAV = float(msg["k"]["V"])
        TBQAV = float(msg["k"]["Q"])

        complete = msg["k"]["x"]

        self.manage_heartbeat(current_datetime=event_time)

        new_row = self.cols_to_use(
            oopen=oopen,
            high=high,
            low=low,
            close=close,
            volume=volume,
            QAVol=QAVol,
            NoT=NoT,
            TBBAV=TBBAV,
            TBQAV=TBBAV
        )

        new_row["Complete"] = complete

        col_names = list(new_row.keys())
        col_values = list(new_row.values())
        self.data.loc[start_time, col_names] = col_values
        self.run_strategy(
            period_completed=complete,
            last_price=close
        )
        if complete:
            self.print_message(msg="C", end="", flush=True)

    def cancel_all_open_orders(self):
        """
        Cancels all open orders
        """
        self.client.futures_cancel_all_open_orders(symbol=self.pair)

    def cancel_open_order(self, order_id: str):
        """
        Cancels an open order given an order id.
        """
        self.client.futures_cancel_order(
            symbol=self.pair,
            orderId=order_id
        )

    def go_stop_market(
        self,
        when_prc_reaches: float = 99.0,
        close_previous: bool = True
    ) -> None:
        """
        Makes a stop market in order to lose less money.
        """
        if close_previous:
            self.close_all_stop_market()
        base = self.get_open_base()
        side = self.get_opposite_position()
        if side == Position.NEUTRAL:
            self.print_message(ERROR_STOP_MARKET)
            return
        liq_price = self.get_liquidation_price()
        entry_price = self.get_entry_price()
        rangee = entry_price - liq_price
        stopPrice = round(
            entry_price - (when_prc_reaches/100) * rangee,
            1
        )
        self.client.futures_create_order(
            stopPrice=stopPrice,
            quantity=base,
            symbol=self.pair,
            side=side.value,
            type="STOP_MARKET",
            reduceOnly=True
        )

    def close_all_stop_market(self) -> None:
        """
        Closes all stop market orders
        """
        open_orders = pd.DataFrame(self.client.futures_get_open_orders())
        if len(open_orders) == 0:
            return
        orders = open_orders[
            (open_orders["origType"] == "STOP_MARKET") &
            (open_orders["symbol"] == self.pair)
        ]
        for i in range(len(orders)):
            order_id = orders.iloc[i]["orderId"]
            self.cancel_open_order(order_id)

    def get_order(self, order_id: str) -> dict:
        """
        Gets an order given an id.
        """
        order = self.client.futures_get_order(
            symbol=self.pair, orderId=order_id
        )
        return order

    def get_current_position(self):
        """
        Gets current position of open order.
        """
        response = self.get_pos_info()
        return response["position"]

    def create_order(
        self,
        base: float,
        side: Position,
        price: float = None,
        order_type: str = "MARKET",
        reduceOnly: bool = False,
        stopPrice: float = None
    ):
        """
        Creates order for Binance

        Notes:
        Binance accepts max 3 decimals.
        """
        base = round(base, 3)

        if price is not None:
            price = round(price, 1)

        if base < self.min_base_open:
            self.print_message(
                LESS_THAN_MIN.format(
                    str(base)
                )
            )
            return

        match order_type:
            case "MARKET":
                order_open = self.client.futures_create_order(
                    quantity=base,
                    symbol=self.pair,
                    side=side.value,
                    type=order_type,
                    reduceOnly=reduceOnly,
                )
                pos_open = self.client.futures_get_order(
                    symbol=self.pair,
                    orderId=order_open["orderId"]
                )
                self.history["last_pos_open"] = pos_open["orderId"]
            case "LIMIT":
                order_open = self.client.futures_create_order(
                    quantity=base,
                    price=price,
                    symbol=self.pair,
                    side=side.value,
                    type=order_type,
                    reduceOnly=reduceOnly,
                    timeInForce="GTC",
                )
                self.history["last_limit_order"] = order_open["orderId"]
            case "TAKE_PROFIT":
                order_open = self.client.futures_create_order(
                    quantity=base,
                    price=price,
                    stopPrice=stopPrice,
                    symbol=self.pair,
                    side=side.value,
                    type=order_type,
                )
                self.history["last_take_profit"] = order_open["orderId"]
            case _:
                self.print_message(INVALID_ORDER_TYPE)
                return

    def go_neutral(
        self,
        order_type: str = "MARKET",
        prc: float = 100,
        price: float = None
    ) -> None:
        """
        CLoses a percentage of position.
        """
        open_base = self.get_open_base()
        if is_zero(open_base):
            return

        prc = min(prc, 100)
        prc = max(0, prc)
        close_base = open_base * prc / 100

        self.create_order(
            side=self.get_opposite_position(),
            base=close_base,
            reduceOnly=True,
            order_type=order_type,
            price=price
        )
        self.close_all_stop_market()

    def get_quote(
        self,
        quote: float,
        use_wallet_prc: bool = False,
        use_available_prc: bool = False,
    ) -> float:
        """
        Gets real quote.

        wallet_prc: considers wallet + positions value
        available_prc: Just available balance
        """
        if use_wallet_prc and use_available_prc:
            self.print_message(CHOOSE_ONE_WALLET_PRC)
            return

        if use_wallet_prc:
            quote = (self.get_current_balance() * quote / 100)
            quote *= self.get_current_leverage()

        if use_available_prc:
            quote = (self.get_available_balance() * quote / 100)
            quote *= self.get_current_leverage()

        return quote

    def go_long(
        self,
        quote: float,
        price: float,
        use_wallet_prc: bool = False,
        use_available_prc: bool = False,
        order_type: str = "MARKET",
        reduceOnly: bool = False,
    ) -> None:
        """
        Go LONG position.

        If use_wallet_prc, then quote corresponds to prc of
        wallet used:
                        0 < base < 100
        """
        quote = self.get_quote(
            use_wallet_prc=use_wallet_prc,
            use_available_prc=use_available_prc,
            quote=quote
        )

        base = max(self.min_base_open, quote/price)

        self.create_order(
            base=base,
            price=price,
            side=Position.LONG,
            order_type=order_type,
            reduceOnly=reduceOnly
        )

    def go_short(
        self,
        quote: float,
        price: float,
        use_wallet_prc: bool = False,
        use_available_prc: bool = False,
        order_type: str = "MARKET",
        reduceOnly: bool = False,
    ) -> None:
        """
        Go SHORT position.

        If use_wallet_prc, then quote corresponds to prc of
        wallet used:
                        0 < base < 100
        """
        quote = self.get_quote(
            use_wallet_prc=use_wallet_prc,
            use_available_prc=use_available_prc,
            quote=quote
        )

        base = max(self.min_base_open, quote/price)

        self.create_order(
            base=base,
            price=price,
            side=Position.SHORT,
            order_type=order_type,
            reduceOnly=reduceOnly
        )

    def prepare_strategy(self) -> None:
        """
        Implement this on child class.

        Prepare the strategy.
        """
        self.strategy = None

    def run_strategy(
        self,
        period_completed: bool,
        last_price: float
    ) -> None:
        """
        Implement this on child class.

        Runs strategy.
        """
        if not period_completed:
            return
        self.strategy = None
