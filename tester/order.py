from orders.base_order import BaseOrder
from datetime import datetime
from orders.order_type import OrderType
from chaos.triangular_distribution import CHAOS
from orders.min_orders import MIN_ORDERS
from margin_tables import MARGIN_TABLES
from helpers import (
    is_zero,
    red,
    green,
    cyan,
    yellow
)
from orders.position import Position


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
        min_size_quote = self.min_base_open * self.entry_price
        min_margin_quote = self.size_to_margin(min_size_quote)

        min_opening_fee_quote = min_size_quote * self.get_fee_constant(
            self.order_type
        )

        min_quote = min_margin_quote + min_opening_fee_quote
        expected_margin_quote = self.size_to_margin(self.expected_quote)
        times_min_quote = expected_margin_quote // min_quote
        if is_zero(times_min_quote):
            return False

        self.size_quote = min_size_quote * times_min_quote
        self.margin_quote = min_margin_quote * times_min_quote
        self.opening_fee_quote = min_opening_fee_quote * times_min_quote
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
            "{} |  {} {} quote for {}, leverage {}".format(
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
        low: float,
        high: float,
        close: float
    ) -> bool:
        """
        Executes position at a certain price
        """
        self.opened_at = date
        self.entry_price = self.get_execution_price(
            low=low, high=high, close=close,
            expected_price=self.expected_entry_price,
            order_type=self.order_type,
            opening_order=True
        )
        valid = self.get_spent_quote()
        if not valid:
            self.print_message("Insufficient Margin to buy units")
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
            "{} |  {} ({}{}) quote {} for {}".format(
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
        liquidated: bool = False
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
        self.print_close_message(
            date=date,
            close_price=close_price,
            close_quote=size_quote_closed,
            liquidated=liquidated
        )

    def close_position(
        self,
        date: datetime,
        low: float,
        high: float,
        close: float,
        expected_close_price: float,
        order_type: OrderType,
        notional_quote_close: float,
        prc: bool
    ) -> float:
        """
        Closes the position given a percentage or
        notional quote close of it.

        notional quote close is the quote associated
        to notional value you want to close or percentage
        if prc is True.

        Returns my invested money and PnL.
        """
        if self.is_closed:
            self.print_already_closed()
            return
        # si hay varias ordenes, entonces deberia pasar el close price?
        close_price = self.get_execution_price(
            low=low, high=high, close=close,
            expected_price=expected_close_price,
            order_type=order_type,
            opening_order=False
        )
        # si son varias ordenes, no debe ser un multiplo de min units
        min_quote_close = self.min_base_open * close_price
        notional_val_quote = self.get_notional_value(
            current_price=close_price,
            base=self.open_size_base
        )
        if prc:
            prc_closed = notional_quote_close/100
            notional_quote_close = notional_val_quote * prc_closed
        times_min_quote = notional_quote_close//(min_quote_close-1e-12)
        notional_quote_close = min_quote_close * times_min_quote

        remaining_open_quote = notional_val_quote - notional_quote_close

        if self.should_liquidate(close_price):
            self.liquidate_position(date=date)
            return 0

        if is_zero(notional_quote_close):
            notional_quote_close = min_quote_close

        # quitar en caso de que las pueda cerrar parcialmente
        elif remaining_open_quote + 1e-10 < min_quote_close:
            notional_quote_close = notional_val_quote

        prc_closed = notional_quote_close/notional_val_quote
        margin_quote_close = self.open_margin_quote * prc_closed
        self.update_close_attributes(
            date=date,
            close_price=close_price,
            order_type=order_type,
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
        liquidation_price: float
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
            liquidated=True
        )
