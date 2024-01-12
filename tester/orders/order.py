from orders import (
    BaseOrder,
    OrderType,
    Position,
    MIN_ORDERS
)
from datetime import datetime
from chaos.triangular_distribution import CHAOS
from margin_tables import MARGIN_TABLES
from helpers import (
    is_zero,
    red,
    green,
    cyan,
    yellow,
    NOT_PROVIDED_CLOSE_PRICE,
    NOT_PROVIDED_CANDLE,
    INSUFICCIENT_MARGIN
)


class Order(BaseOrder):
    """
    Contains methods of orders.

    Inherits validations from BaseOrder.
    """

    def __init__(self, *args, **kwargs):
        """
        Validates attributes
        """
        super().__init__(*args, **kwargs)
        self.min_base_open = MIN_ORDERS.get_min_units(self.pair)

    def get_execution_price(
        self,
        low: float,
        high: float,
        close: float,
        expected_price: float,
        order_type: OrderType,
        opening_order: bool
    ) -> float:
        """
        Returns execution price of an order.

        This price is "random" because orders
        are not executed at the exact requested price
        due to market fluctuations.

        opening_order boolean tells if order is opening or
        closing.
        If order is closing, position must be the
        opposite one to give accurate difficulty:

        Example:
        Opening LONG: Best execution is low price
        Closing LONG: Best execution is high price
        """
        if not (low or high or close):
            raise ValueError(NOT_PROVIDED_CANDLE)
        if opening_order:
            execution_price = CHAOS.get_execution_price(
                expected_price=expected_price,
                low=low,
                close=close,
                high=high,
                position=self.position,
                order_type=order_type,
                difficulty=self.difficulty,
            )
        else:
            match self.position:
                case Position.LONG:
                    closing_position = Position.SHORT
                case Position.SHORT:
                    closing_position = Position.LONG

            execution_price = CHAOS.get_execution_price(
                expected_price=expected_price,
                low=low,
                close=close,
                high=high,
                position=closing_position,
                order_type=order_type,
                difficulty=self.difficulty,
            )

        return execution_price

    def get_min_quote_invest(
        self,
        execution_quote: float
    ) -> dict:
        """
        Gets min investment of a certain quote
        using a max fluctuation of a certain
        percentage.

        0 < fluctuation < 1

        Fluctuation is necessary due to difference
        of real with expected execution price.
        """
        min_size_quote = self.min_base_open * execution_quote * (
            1 + self.fluctuation
        )
        min_margin_quote = self.size_to_margin(min_size_quote)

        min_opening_fee_quote = min_size_quote * self.get_fee_constant(
            self.order_type
        ) * (1 + self.fluctuation)
        min_quote = min_margin_quote + min_opening_fee_quote

        return {
            "min_size_quote": min_size_quote,
            "min_margin_quote": min_margin_quote,
            "min_opening_fee_quote": min_opening_fee_quote,
            "min_quote": min_quote
        }

    def get_spent_quote(self) -> bool:
        """
        This function calculates the spent quote using
        entry price, i.e., margin and position size.

        The minimum required margin and fees are calculated
        and finally it is bought a multiple of that numbers
        until expected quote is almost reached.

        Returns if at least minimum base coin could be bought.

        Example:
        (Expected quote: 3000
        leverage: 3
        ->
        Expected margin quote: 1000)
        min_margin_quote: 100
        min_fee_quote: 10

        The maximum we can spend is 9 times the minimum, i.e.,
        990 quote.
        """
        inv = self.get_min_quote_invest(
            execution_quote=self.entry_price
        )
        expected_margin_quote = self.size_to_margin(self.expected_quote)
        times_min_quote = expected_margin_quote // (inv["min_quote"]-1e-12)
        if is_zero(times_min_quote):
            return False

        self.size_quote = inv["min_size_quote"] * times_min_quote
        self.margin_quote = inv["min_margin_quote"] * times_min_quote
        self.opening_fee_quote = inv["min_opening_fee_quote"] * times_min_quote
        return True

    def print_open_message(self) -> None:
        """
        Prints opening message position
        """
        match self.position:
            case Position.LONG:
                action = green("Buying")
            case Position.SHORT:
                action = red("Selling")
        self.print_message(
            "{} | {} {} quote for {}, leverage {}".format(
                self.opened_at,
                action,
                round(self.size_quote, 1),
                round(self.entry_price, 1),
                self.leverage
            )
        )

    def open_position(
        self,
        date: datetime,
        low: float = None,
        high: float = None,
        close: float = None,
        entry_price: float = None,
        fail_silent: bool = False
    ) -> bool:
        """
        Executes position at a certain price.

        Please give an entry price or
        candle info to calculate one.
        """
        self.opened_at = date
        if entry_price:
            self.entry_price = entry_price
        else:
            self.entry_price = self.get_execution_price(
                low=low, high=high, close=close,
                expected_price=self.expected_entry_price,
                order_type=self.order_type,
                opening_order=True
            )
        valid = self.get_spent_quote()
        if not valid:
            if not fail_silent:
                self.print_message(INSUFICCIENT_MARGIN)
            return {"valid": False, "margin": 0}
        self.calculate_liquidation_price()
        self.print_open_message()
        return {"valid": True, "quote_spent": self.open_quote_investment}

    def get_close_fee_quote(
        self,
        quote_to_close: float,
        close_price: float,
        order_type: OrderType
    ) -> float:
        """
        Gets fee of closing certain quote.

        quote_to_close maximum abs value is size_quote
        """
        fee_constant = self.get_fee_constant(order_type)
        notional_value = self.get_notional_value(
            current_price=close_price,
            base=quote_to_close/self.entry_price
        )
        fee = notional_value * fee_constant
        return fee

    def print_close_message(
        self,
        date: datetime,
        close_price: float,
        close_quote: float,
        liquidated: bool = False
    ) -> None:
        """
        Prints the closing order message
        """
        match self.position:
            case Position.SHORT:
                action = "Buying"
            case Position.LONG:
                action = "Selling"

        self.print_message(
            "{} |  {} ({}{}) {} quote for {}".format(
                date,
                action,
                cyan("liquidating") if liquidated
                else yellow("closing"),
                " partially" if self.is_open else "",
                round(close_quote, 1),
                round(close_price, 1)
            )
        )

    def update_close_attributes(
        self,
        date: datetime,
        close_price: float,
        order_type: OrderType,
        size_quote_closed: float,
        print_message: bool,
        liquidated: bool = False,
    ) -> None:
        """
        Updates closing attributes after closing
        a position (or partially).
        """
        margin_quote_closed = self.size_to_margin(size_quote_closed)
        self.closed_at.append(date)
        self.close_prices.append(close_price)
        self.closing_order_types.append(order_type)
        self.closing_fee_quotes.append(
            self.get_close_fee_quote(
                quote_to_close=size_quote_closed,
                close_price=close_price,
                order_type=order_type
            ) if not liquidated else 0
        )
        self.PnLs.append(
            self.get_PnL(
                current_price=close_price,
                quote=size_quote_closed
            ) if not liquidated else -margin_quote_closed
        )
        self.closed_size_quotes.append(
            size_quote_closed
        )
        if print_message:
            self.print_close_message(
                date=date,
                close_price=close_price,
                close_quote=size_quote_closed,
                liquidated=liquidated
            )

    def multiple_of_min_base(
        self,
        close_price: float,
        notional_quote_close: float,
        notional_val_quote: float
    ) -> float:
        """
        Closes a multiple of minimum base.

        returns the notional quote to close.
        """
        min_quote_close = self.min_base_open * close_price
        times_min_quote = notional_quote_close//(min_quote_close-1e-12)
        notional_quote_close = min_quote_close * times_min_quote

        remaining_open_quote = notional_val_quote - notional_quote_close
        if remaining_open_quote + 1e-10 < min_quote_close:
            notional_quote_close = notional_val_quote

        if is_zero(notional_quote_close):
            notional_quote_close = min_quote_close

        return notional_quote_close

    def close_position(
        self,
        date: datetime,
        order_type: OrderType,
        notional_quote_close: float,
        prc: bool,
        expected_close_price: float = None,
        close_price: float = None,
        multiple_of_min_base: bool = False,
        check_liquidation: bool = False,
        low: float = None,
        high: float = None,
        close: float = None,
        print_message: bool = True
    ) -> float:
        """
        Closes the position given a percentage or
        notional quote close of it.

        notional quote close is the quote associated
        to notional value you want to close or percentage
        if prc is True.

        If close_price is not provided, one is calculated using
        expected_close_price

        Returns my invested money and PnL.
        """
        if self.is_closed:
            self.print_already_closed()
            return

        if close_price is None:
            if not (expected_close_price):
                raise ValueError(NOT_PROVIDED_CLOSE_PRICE)

            close_price = self.get_execution_price(
                low=low, high=high, close=close,
                expected_price=expected_close_price,
                order_type=order_type,
                opening_order=False
            )

        if check_liquidation and self.should_liquidate(close_price):
            self.liquidate_position(date=date)
            return 0

        notional_val_quote = self.get_notional_value(
            current_price=close_price,
            base=self.open_size_base
        )

        if prc:
            prc_closed = notional_quote_close/100
            notional_quote_close = notional_val_quote * prc_closed

        if multiple_of_min_base:
            notional_quote_close = self.multiple_of_min_base(
                close_price=close_price,
                notional_quote_close=notional_quote_close,
                notional_val_quote=notional_val_quote
            )

        prc_closed = notional_quote_close/notional_val_quote
        margin_quote_close = self.open_margin_quote * prc_closed
        self.update_close_attributes(
            date=date, close_price=close_price,
            order_type=order_type, print_message=print_message,
            size_quote_closed=self.open_size_quote * prc_closed
        )
        return margin_quote_close + self.PnLs[-1] - self.closing_fee_quotes[-1]

    def calculate_liquidation_price(self):
        """
        Calculates the liquidation price using maintenance ratio.
        Position is liquidated when maintenance ratio reaches 1.

        More iterations == closer you get to approx. liquidation price.
        """
        iterations = 5
        direction = self.direction_int
        balance = self.open_margin_quote
        base_bought = self.open_size_base
        liquidation_price = self.entry_price
        for _ in range(iterations):
            maintenance_margin = MARGIN_TABLES.get_maintenance_margin(
                pair=self.pair,
                notional_value=self.get_notional_value(
                    current_price=liquidation_price,
                    base=self.open_size_quote/self.entry_price
                )
            )
            number = direction * (maintenance_margin - balance)/base_bought
            liquidation_price = self.entry_price + number
        self.liquidation_price = liquidation_price

    def liquidate_position(
        self,
        date: datetime,
        liquidation_price: float,
        print_message: bool
    ) -> None:
        """
        Liquidates position given a close price
        """
        if self.is_closed:
            self.print_already_closed()
            return
        self.liquidated = True
        self.update_close_attributes(
            date=date,
            close_price=liquidation_price,
            order_type=OrderType.MARKET,
            size_quote_closed=self.open_size_quote,
            liquidated=True,
            print_message=print_message
        )
