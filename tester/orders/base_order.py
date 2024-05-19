from datetime import datetime
from margin_tables import MARGIN_TABLES
from orders import (
    OrderType,
    Position,
    Difficulty
)
from helpers import (
    INVALID_LEVERAGE,
)
from pydantic import (
    BaseModel,
    model_validator
)
from typing import List
from helpers import is_zero, cyan, yellow


class BaseOrder(BaseModel):
    """
    This class manages order validations, properties and
    base methods of order class.

    Note: In BTCUSDT and other pairs,
    BTC -> Base currency (first currency)
    USDT -> Quote currency (second currency)

    Init Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSDT
    expected_quote: Desired position quote investment
                    expected_quote/leverage is the quote we
                    spend (includes fee).
    expected_entry_price: Desired entry price for order
    position: Position enum, long or short
    leverage: Leverage to use, limited depending on pair
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    order_type: An example is MARKET, see order_type.py
    difficulty: Difficulty of market, see difficulty.py
    reduce_only: Tells if order is reduce_only. This is
        stored for limit orders execution use
        in order_manager.
    use_prc_close: Tells how much to close on prc. This is
    stored for limit orders execution use in order manager.
    created_at: datetime when order was created

    Opening Attributes:
    entry_price: The price where order executed
    size_quote: Total bought of position quote currency (margin*leverage).
                This number does not change due to market fluctuations,
                use notional value instead. Always positive
    margin_quote: Amount spent from my balance
    opening_fee_quote: Quote spent on opening fee >= 0
    opened_at: datetime when order was opened

    Closing Attributes:
    close_prices: The prices where order partially closed
    closed_size_quotes: List of partially closed quote until reaches size_quote
    closing_fee_quotes: Quotes spent on closing fees >= 0
    PnLs: Quote profits and losses, this does not include fees
          (opening or closing)
    liquidation_price: Tells if position was liquidated and when
    liquidated: Tells if position was liquidated
    closed_at: Stores the closing datetimes of order

    Post-Init Attributes:
    min_base_open: Min amount of base coin to buy
    """
    verbose: bool
    pair: str
    expected_quote: float
    expected_entry_price: float
    position: Position
    leverage: int = 1
    use_fee: bool = True
    fee_maker: float = 0.0002
    fee_taker: float = 0.0004
    order_type: OrderType = OrderType.MARKET
    difficulty: Difficulty = Difficulty.MEDIUM
    reduce_only: bool = False
    use_prc_close: bool = False
    created_at: datetime = datetime.now()

    entry_price: float = None
    size_quote: float = None
    margin_quote: float = None
    opening_fee_quote: float = 0
    opened_at: datetime = None

    close_prices: List[float] = []
    closed_size_quotes: List[float] = []
    closing_fee_quotes: List[float] = []
    closing_order_types: List[OrderType] = []
    PnLs: List[float] = []
    liquidation_price: float = None
    liquidated: bool = False
    closed_at: List[datetime] = []

    min_base_open: float = None

    @model_validator(mode='after')
    def validate_leverage(self) -> None:
        """
        Validates leverage considering used quote.
        """
        max_leverage = MARGIN_TABLES.get_max_leverage(
            self.pair, self.expected_quote
        )
        if self.leverage < 1 or self.leverage > max_leverage:
            raise ValueError(
                INVALID_LEVERAGE.format(
                    leverage=str(self.leverage),
                    max_leverage=str(max_leverage)
                )
            )

    @property
    def quote_used_to_limit(self) -> float:
        """
        Method used for limit orders in order to
        calculate our quote spent to register a
        limit order.
        """
        return self.expected_quote/self.leverage

    @property
    def open_size_quote(self) -> float:
        """
        Gets current open quote.
        This function not include the quote change
        due to market fluctuations.
        Open quote is positive for LONG and negative for SHORT
        """
        return self.size_quote - sum(self.closed_size_quotes)

    @property
    def open_margin_quote(self) -> float:
        """
        Gets current open margin quote.
        This function not include the quote change
        due to market fluctuations.
        This number is always positive
        """
        return abs(self.open_size_quote)/self.leverage

    @property
    def size_base(self) -> float:
        """
        Gets base bought on initial order
        """
        return self.size_quote / self.entry_price

    @property
    def open_size_base(self) -> float:
        """
        Gets base still opened on order
        """
        return self.open_size_quote / self.entry_price

    @property
    def open_quote_investment(self) -> float:
        """
        Gets quote invested to open position
        """
        return self.margin_quote + self.opening_fee_quote

    @property
    def is_open(self) -> bool:
        """
        Tells if order is open
        """
        if self.liquidated or is_zero(self.open_size_quote):
            return False
        return True

    @property
    def is_closed(self) -> bool:
        """
        Tells if order is closed
        """
        return not self.is_open

    @property
    def direction_int(
        self,
    ) -> int:
        """
        Gets number associated of position.
        Useful to make calculations.
        LONG: 1
        SHORT: -1
        """
        match self.position:
            case Position.LONG:
                return 1
            case Position.SHORT:
                return -1

    @property
    def realized_PnL(
        self,
    ) -> float:
        """
        Returns the realized PnL
        """
        if not self.PnLs:
            return 0
        return sum(self.PnLs)

    @property
    def realized_fee(
        self,
    ) -> float:
        """
        Returns the realized fee.

        Fees:
        Opening (just one)
        closing (could be multiple)
        """
        fee = 0
        fee += self.opening_fee_quote
        fee += sum(self.closing_fee_quotes)
        return fee

    @property
    def realized_PnL_with_fee(
        self,
    ) -> float:
        """
        Returns the realized PnL with opening
        and closing fees
        """
        return self.realized_PnL - self.realized_fee
    
    @property
    def liquidated_margin(
        self,
    ) -> float:
        """
        Returns the margin lost of liquidated order,
        0 instead. Not including opening or closing fees.
        """
        if not self.liquidated:
            return 0
        return self.PnLs[0]

    def __repr__(self):
        """
        String representation of object.
        """
        return self.position.name

    def size_to_margin(self, quantity: float) -> float:
        """
        Given a quantity, returns the user invested part.

        Basically, it just divides the quantity by leverage.
        """
        return quantity/self.leverage

    def get_fee_constant(
        self,
        order_type: OrderType
    ) -> float:
        """
        Gets fees defined in class depending on order type.

        Frequently, limit orders are cheaper.
        """
        if not self.use_fee:
            return 0.0
        match order_type:
            case OrderType.MARKET:
                return self.fee_taker
            case OrderType.LIMIT:
                return self.fee_maker

    def get_notional_value(
        self,
        current_price: float,
        base: float
    ) -> float:
        """
        Gets current notional value of position:
        Not. Value = units in contract  * spot price

        The variable base is the current units
        """
        notional_value = base * current_price

        return notional_value

    def get_PnL(
        self,
        current_price: float,
        quote: float
    ) -> float:
        """
        Gets quote PnL of certain quote bought on entry price.
        This does not include fees.
        """
        PnL = (1/self.entry_price - 1/current_price)
        PnL = PnL * quote * current_price * self.direction_int
        return PnL

    def should_liquidate(self, price: float) -> bool:
        """
        Tells if position should be liquidated given a price
        """
        liquidation_price = self.liquidation_price
        match self.position:
            case Position.LONG:
                if price <= liquidation_price:
                    return True
            case Position.SHORT:
                if price >= liquidation_price:
                    return True
        return False

    def print_message(self, message: str) -> None:
        """
        Prints messages if verbose is True
        """
        if self.verbose:
            print(message)

    def print_already_closed(self) -> None:
        match self.liquidated:
            case True:
                msg = cyan("liquidated")
            case False:
                msg = yellow("closed")
        self.print_message(f"Order already {msg}")

    def should_execute(
        self,
        low: float,
        high: float
    ) -> bool:
        """
        Checks if limit order should be executed.
        """
        expected_price = self.expected_entry_price
        match self.position:
            case Position.LONG:
                return low <= expected_price
            case Position.SHORT:
                return high >= expected_price

    def when_execute(
        self,
        open: float,
        low: float,
        high: float
    ) -> float:
        """
        Checks when limit order should be executed
        """
        expected_price = self.expected_entry_price
        match self.position:
            case Position.LONG:
                if open <= expected_price:
                    return open
                if low <= expected_price:
                    return expected_price
            case Position.SHORT:
                if open >= expected_price:
                    return open
                if high >= expected_price:
                    return expected_price
