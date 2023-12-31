from pydantic import BaseModel
from orders import (
    Order,
    Position,
    OrderSystem,
    OrderType
)
from typing import List
from datetime import datetime
from helpers import is_zero
from orders.difficulty import Difficulty
from helpers.error_messages import (
    FLUCTUATION_ERROR,
    MIN_INVEST_ERROR
)


class OrderManager(BaseModel):
    """
    This class manages orders.

    Manages their closing, liquidating and
    other behaviours.

    Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSDT
    difficulty: Difficulty of market, see difficulty.py
    open_orders: Stores current open positions
    limit_orders: Stores limit orders (pending positions)
    closed_orders: Stores all closed orders (also liquidated)
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    global_liquidaiton: stores the liquidation
                    calculated for open orders
                    just for netting mode.
    system: Order behaviour:
        Netting: Orders are merged into one
        Hedging: Orders are separated


    """
    verbose: bool
    pair: str
    difficulty: Difficulty = Difficulty.MEDIUM
    open_orders: List[Order]
    limit_orders: List[Order]
    closed_orders: List[Order]
    use_fee: bool = True
    fee_maker: float = 0.0002
    fee_taker: float = 0.0004
    global_liquidation: float = None
    system: OrderSystem = OrderSystem.NETTING

    def get_min_quote_invest(
        self,
        current_quote_val: float,
        leverage: int,
        order_type: OrderType,
        fluctuation: float
    ) -> float:
        """
        Gets min investment of a certain quote
        using a max fluctuation of a certain
        percentage.

        0 < fluctuation < 1

        Fluctuation is necessary due to difference
        of real with expected execution price.
        """
        if fluctuation < 0 or fluctuation > 1:
            raise ValueError(FLUCTUATION_ERROR)
        order = self.create_order(
            quote=0,
            expected_execution_price=current_quote_val,
            position=Position.LONG,
            leverage=leverage,
            order_type=order_type,
            date=datetime.now()
        )
        inv = order.get_min_quote_invest(
            execution_quote=current_quote_val,
            fluctuation=fluctuation
        )
        return inv["min_quote"]

    def get_position(self) -> Position:
        """
        Gets current position
        LONG, SHORT or NEUTRAL
        """
        if len(self.open_orders) == 0:
            return Position.NEUTRAL
        match self.system:
            case OrderSystem.NETTING:
                return self.open_orders[0].position

    def must_close_open_positions(
        self,
        requested_pos: Position
    ) -> bool:
        """
        Returns if positions must be closed using
        the requested position and current one.
        """
        current_pos = self.get_position()
        if current_pos == Position.NEUTRAL:
            return False

        match self.system:
            case OrderSystem.NETTING:
                return current_pos != requested_pos

    def get_invested_not_val_quote(
        self,
        close_price: float
    ):
        """
        Sum all notional values of open orders in quote
        currency.
        """
        not_val_quote = 0
        for order in self.open_orders:
            not_val_quote += order.get_notional_value(
                current_price=close_price,
                base=order.open_size_base
            )
        return not_val_quote

    def get_close_price(
        self,
        low: float,
        high: float,
        close: float,
        expected_close_price: float,
        order_type: OrderType,
    ) -> float:
        """
        NETTING:
        Gets first order close price to use generally.
        """
        match self.system:
            case OrderSystem.NETTING:
                return self.open_orders[0].get_execution_price(
                    low=low, high=high, close=close,
                    expected_price=expected_close_price,
                    order_type=order_type,
                    opening_order=False
                )

    def close_position(
        self,
        date: datetime,
        order_type: OrderType,
        close_price: float,
        quote: float
    ):
        """
        closes the position of certain quote.

        Returns the closed quote (notional) 
        and total return (includes investment, fees and pnl).
        """
        match self.system:
            case OrderSystem.NETTING:
                #checar si no se liquido la posición con global liquidation
                invested_not_quote = self.get_invested_not_val_quote(
                    close_price=close_price
                )

                quote_to_close = self.open_orders[0].multiple_of_min_base(
                    close_price=close_price,
                    notional_quote_close=min(
                        invested_not_quote,
                        quote
                    ),
                    notional_val_quote=invested_not_quote
                )
                prc_to_close = quote_to_close/invested_not_quote
                self.open_orders[0].print_close_message(
                    date=date,
                    close_price=close_price,
                    close_quote=quote_to_close,
                    liquidated=False
                )
                total_return = 0
                for order in self.open_orders[:]:
                    total_return += order.close_position(
                        date=date,
                        order_type=order_type,
                        notional_quote_close=prc_to_close,
                        prc=True,
                        close_price=close_price,
                        multiple_of_min_base=False,
                        check_liquidation=False,
                        print_message=False
                    )
                    if order.is_closed():
                        self.open_orders.remove(order)
                        self.closed_orders.append(order)

                if len(self.open_orders) == 0:
                    self.global_liquidation = None

                return {
                    "total_return": total_return,
                    "closed_quote": quote_to_close
                }

    def create_order(
        self,
        quote: float,
        expected_execution_price: float,
        position: Position,
        leverage: int,
        order_type: OrderType,
        date: datetime
    ) -> Order:
        """
        creates order object
        """
        return Order(
            verbose=self.verbose,
            pair=self.pair,
            expected_quote=quote,
            expected_entry_price=expected_execution_price,
            position=position,
            leverage=leverage,
            use_fee=self.use_fee,
            fee_maker=self.fee_maker,
            fee_taker=self.fee_taker,
            order_type=order_type,
            difficulty=self.difficulty,
            created_at=date,
        )

    def add_to_limit_orders(
        self,
        order: OrderType
    ) -> None:
        """
        Append order to limit orders and arranges them:

        Put long positions together and arrange them in 
        descendant order.

        Put short positions together and arrange them in 
        ascendant order.
        """
        self.limit_orders.append(order)
        long_positions = sorted(
            filter(
                lambda order: order.position == Position.LONG,
                self.limit_orders
            ),
            key=lambda order: order.expected_entry_price,
            reverse=True
        )
        short_positions = sorted(
            filter(
                lambda order: order.position == Position.SHORT,
                self.limit_orders
            ),
            key=lambda order: order.expected_entry_price,
            reverse=False
        )
        self.limit_orders = long_positions + short_positions

    def submit_order(
        self,
        date: datetime,
        low: float,
        high: float,
        close: float,
        quote: float,
        leverage: int,
        position: Position,
        order_type: OrderType,
        expected_exec_quote: float,
        fluctuation: float
    ) -> float:
        """
        Submits an order to system.

        Fluctuation is the max difference  of price
        when executing in percentage.

        0 < fluctuation < 1

        Returns the quote spent to open or
        store order.
        """
        # debo validar que tengo el dinero
        min_quote_invest = self.get_min_quote_invest(
            current_quote_val=expected_exec_quote,
            leverage=leverage,
            order_type=order_type,
            fluctuation=fluctuation
        )["min_quote"]

        if quote < min_quote_invest:
            raise MIN_INVEST_ERROR.format(min_quote_invest)
        
        times_min_quote = quote // (min_quote_invest-1e-12)
        quote = min_quote_invest * times_min_quote

        match order_type:
            case OrderType.MARKET:
                quote_spent = self.execute_order(
                    date=date, low=low, high=high, close=close,
                    quote=quote, leverage=leverage,
                    position=position, order_type=order_type,
                    expected_execution_price=expected_exec_quote
                )
                return quote_spent
            case OrderType.LIMIT:
                match position:
                    case Position.LONG:
                        if expected_exec_quote <= close:
                            quote_spent = self.execute_order(
                                date=date, low=low, high=high, close=close,
                                quote=quote, leverage=leverage,
                                position=position, order_type=order_type,
                                expected_execution_price=expected_exec_quote
                            )
                            return quote_spent
                    case Position.SHORT:
                        if expected_exec_quote >= close:
                            quote_spent = self.execute_order(
                                date=date, low=low, high=high, close=close,
                                quote=quote, leverage=leverage,
                                position=position, order_type=order_type,
                                expected_execution_price=expected_exec_quote
                            )
                            return quote_spent
                    case _:
                        order = self.create_order(
                            quote=quote,
                            expected_execution_price=expected_exec_quote,
                            position=position,
                            leverage=leverage,
                            order_type=order_type,
                            date=date
                        )
                        self.add_to_limit_orders(order)
                        return quote

    def execute_order(
        self,
        date: datetime,
        low: float,
        high: float,
        close: float,
        quote: float,
        leverage: int,
        position: Position,
        order_type: OrderType,
        expected_execution_price: float
    ) -> float:
        """
        Executes order.

        NETTING:
        Checks first if some fraction os position must be closed.
        """
        execution_price = self.get_close_price(
            low=low, high=high, close=close,
            expected_price=expected_execution_price,
            order_type=order_type
        )

        if self.must_close_open_positions(requested_pos=position):

            response = self.close_position(
                date=date, low=low, high=high,
                close=close, quote=quote, order_type=order_type,
                close_price=execution_price
            )
            quote -= response["closed_quote"]
            if is_zero(quote):
                return

        order = self.create_order(
                    quote=quote,
                    expected_execution_price=expected_execution_price,
                    position=position,
                    leverage=leverage,
                    order_type=order_type,
                    date=date
                )

        response = order.open_position(
            date=date,
            entry_price=execution_price
        )
        if order.my_pos_amount > self.available_balance: #avoids floating errors
            self.not_enough_balance(order.my_pos_amount, self.available_balance)
        if not response["valid"]:
            return 0
        self.open_orders.append(order)
        self.calculate_global_liquidation() #solo calcular si se abrio posicion
        #tambien ver si se liquidó!
        return response["quote_spent"]
