from pydantic import (
    BaseModel,
    field_validator,
    ConfigDict
)
from binance.client import Client
import pandas as pd
from config.settings import API_KEY, SECRET_KEY


class BinanceAPI(BaseModel):
    """
    This class manages binance API methods.

    Note: In BTCUSDT and other pairs,
    BTC -> Base currency (first currency)
    USDT -> Quote currency (second currency)

    Settings:
    model_config: Allows Client object as attribute.

    Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSDT
    initial_balance: Initial balance quote. For example, in BTCUSDT,
                    this indicates x USDT you have initially.
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    client: Manages communication with Binance API. Used to load info.
    data: Data to be used in simulator. Load it with load_data method.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    verbose: bool
    pair: str
    # initial_balance: float
    # use_fee: bool
    # fee_maker: float
    # fee_taker: float
    client: Client = Client(
        api_key=API_KEY,
        api_secret=SECRET_KEY,
        tld="com",
        testnet=True
    )
    data: pd.DataFrame = None

    @field_validator("pair", mode="before")
    def validate_pair(cls, value) -> str:
        """
        Validates pair is in uppercase letters
        """
        return value.upper()

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
        return self.data
