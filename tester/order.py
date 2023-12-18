from order.base_order import BaseOrder
from datetime import datetime
from order.order_type import OrderType
from order.triangular_distribution import CAOS
from order.min_orders import MINORDERS
from order.helpers import is_zero
from order.position import Position


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
        self.min_base_open = MINORDERS.get_min_units(self.pair)

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
            execution_price = CAOS.get_execution_price(
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

            execution_price = CAOS.get_execution_price(
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
        Expected quote: 1000
        min_margin_quote: 100
        min_fee_quote: 10

        The maximum we can spend is 9 times the minimum, i.e.,
        990 quote
        """
        min_size_quote = self.min_units * self.entry_price
        min_margin_quote = min_size_quote / self.leverage

        min_opening_fee_quote = self.use_fee * min_size_quote
        min_opening_fee_quote *= self.get_fee_constant(self.order_type)

        min_quote = min_margin_quote + min_opening_fee_quote
        times_min_quote = self.expected_quote // min_quote
        if is_zero(times_min_quote):
            return False

        self.size_quote = min_size_quote * times_min_quote
        self.margin_quote = min_margin_quote * times_min_quote
        self.opening_fee_quote = min_opening_fee_quote * times_min_quote
        return True

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

        match self.position:
            case Position.LONG:
                self.print_message(
                    "{} |  Buying {} quote for {}, leverage {}".format(
                        self.opened_at,
                        round(self.size_quote, 1),
                        round(self.entry_price, 1),
                        self.leverage
                    )
                )
            case Position.SHORT:
                self.print_message(
                    "{} |  Selling {} quote for {}, leverage {}".format(
                        self.opened_at,
                        round(self.size_quote, 1),
                        round(self.entry_price, 1),
                        self.leverage
                    )
                )
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
        close_quote: float
    ) -> None:
        """
        Prints the closing order message
        """
        match self.position:
            case Position.SHORT:
                self.print_message(
                    "{} |  Buying (closing{}) {} quote for {}".format(
                        date,
                        " partially" if self.is_open() else "",
                        round(close_quote, 1),
                        round(close_price, 1)
                    )
                )
            case Position.LONG:
                self.print_message(
                    "{} |  Selling (closing{}) quote {} for {}".format(
                        date,
                        " partially" if self.is_open() else "",
                        round(close_quote, 1),
                        round(close_price, 1)
                    )
                )

    def update_close_attributes(
        self,
        date: datetime,
        close_price: float,
        order_type: OrderType,
        size_quote_closed: float
    ) -> None:
        """
        Updates closing attributes after closing
        a position (or partially).

        """
        self.closed_at.append(date)
        self.close_prices.append(close_price)
        self.closing_order_types.append(order_type)
        self.closing_fee_quotes.append(
            self.get_close_fee_quote(
                quote_to_close=size_quote_closed,
                close_price=close_price,
                order_type=order_type
            )
        )
        self.PnLs.append(
            self.get_PnL(
                current_price=close_price,
                quote=size_quote_closed
            )
        )
        self.closed_size_quotes.append(
            size_quote_closed
        )
        self.print_close_message(
            date=date,
            close_price=close_price,
            close_quote=size_quote_closed
        )

    def close_position(
        self,
        date: datetime,
        low: float,
        high: float,
        close: float,
        expected_close_price: float,
        order_type: OrderType,
        prc: int = 100
    ) -> float:
        """
        Closes the position given a percentage of it.

        Returns my invested money and PnL.
        """
        close_price = self.get_execution_price(
            low=low, high=high, close=close,
            expected_price=expected_close_price,
            order_type=order_type,
            opening_order=False
        )
        #verificar que el close price no sea liquidacion porque quedaria a deber dinero
        # si son varias ordenes, no debe ser un multiplo de min units
        min_quote_close = self.min_units * close_price
        notional_val_quote = self.get_notional_value(
            current_price=close_price,
            base=self.open_size_base
        )
        desired_quote_close = notional_val_quote * prc/100
        times_min_quote = desired_quote_close//min_quote_close
        real_quote_close = min_quote_close * times_min_quote

        remaining_open_quote = notional_val_quote - real_quote_close

        if is_zero(real_quote_close):
            real_quote_close = min_quote_close

        elif remaining_open_quote + 1e-10 < min_quote_close:
            real_quote_close = notional_val_quote

        prc_closed = real_quote_close/notional_val_quote

        self.update_close_attributes(
            date=date,
            close_price=close_price,
            order_type=order_type,
            size_quote_closed=self.open_size_quote * prc_closed
        )
        margin_quote_close = self.open_margin_quote * prc_closed
        return margin_quote_close + self.PnLs[-1] - self.closing_fee_quotes[-1]