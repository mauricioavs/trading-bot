from pydantic import BaseModel
from orders import (
    Order,
    Position,
    OrderSystem,
    OrderType
)
from typing import List
from datetime import datetime
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

    Init Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSDT
    difficulty: Difficulty of market, see difficulty.py
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    system: Order behaviour:
        Netting: Orders are merged into one
        Hedging: Orders are separated

    Other Attributes:
    open_orders: Stores current open positions
    limit_orders: Stores limit orders (pending positions)
    closed_orders: Stores all closed orders (also liquidated)
    netting_liquidaiton: stores the liquidation
                    calculated for open orders
                    just for netting mode.
    """
    verbose: bool
    pair: str
    difficulty: Difficulty = Difficulty.MEDIUM
    use_fee: bool = True
    fee_maker: float = 0.0002
    fee_taker: float = 0.0004
    system: OrderSystem = OrderSystem.NETTING

    open_orders: List[Order] = []
    limit_orders: List[Order] = []
    closed_orders: List[Order] = []
    netting_liquidation: float = None

    @property
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

    def must_close_open_positions(
        self,
        requested_pos: Position
    ) -> bool:
        """
        Returns if positions must be closed using
        the requested position and current one.
        """
        current_pos = self.get_position
        if current_pos == Position.NEUTRAL:
            return False

        match self.system:
            case OrderSystem.NETTING:
                return current_pos != requested_pos
        return False

    def get_invested_not_val_quote(
        self,
        price: float
    ):
        """
        Sum all notional values of open orders in quote
        currency.
        """
        not_val_quote = 0
        for order in self.open_orders:
            not_val_quote += order.get_notional_value(
                current_price=price,
                base=order.open_size_base
            )
        return not_val_quote

    def get_execution_price(
        self,
        low: float,
        high: float,
        close: float,
        expected_price: float,
        order_type: OrderType,
        position: Position
    ) -> float:
        """
        NETTING:
        Gets first order close price to use generally.
        """
        order = self.create_order(
            quote=0,
            expected_execution_price=expected_price,
            position=position,
            leverage=1,
            order_type=order_type,
            date=datetime.now()
        )
        return order.get_execution_price(
            low=low, high=high, close=close,
            expected_price=expected_price,
            order_type=order_type,
            opening_order=True
        )

    def close_position(
        self,
        date: datetime,
        order_type: OrderType,
        close_price: float,
        quote: float
    ) -> dict:
        """
        closes the position of certain quote.

        Returns the closed quote (notional)
        and total return (includes investment, fees and pnl).
        """
        match self.system:
            case OrderSystem.NETTING:
                invested_not_quote = self.get_invested_not_val_quote(
                    price=close_price
                )

                quote_to_close = self.open_orders[0].multiple_of_min_base(
                    close_price=close_price,
                    notional_quote_close=min(
                        invested_not_quote,
                        quote
                    ),
                    notional_val_quote=invested_not_quote
                )
                prc_to_close = quote_to_close/invested_not_quote * 100
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
                    if order.is_closed:
                        self.open_orders.remove(order)
                        self.closed_orders.append(order)

                if len(self.open_orders) == 0:
                    self.netting_liquidation = None
                    print_order = self.closed_orders[-1]
                else:
                    print_order = self.open_orders[-1]

                print_order.print_close_message(
                    date=date,
                    close_price=close_price,
                    close_quote=quote_to_close,
                    liquidated=False
                )

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
        date: datetime,
        reduce_only: bool = False
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
            reduce_only=reduce_only
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
        close: float,
        high: float,
        quote: float,
        leverage: int,
        position: Position,
        order_type: OrderType,
        expected_exec_quote: float,
        fluctuation: float,
        reduce_only: bool = False
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
        # si estoy cerrando orden, no necesito tener el dinero
        min_quote_invest = self.get_min_quote_invest(
            current_quote_val=expected_exec_quote,
            leverage=leverage,
            order_type=order_type,
            fluctuation=fluctuation
        )
        print("MIN_INVEST: ", min_quote_invest)

        if quote < min_quote_invest:
            raise MIN_INVEST_ERROR.format(min_quote_invest)

        times_min_quote = quote // (min_quote_invest-1e-12)
        quote = min_quote_invest * times_min_quote
        print("quote: ", quote)

        match order_type:
            case OrderType.MARKET:
                returns = self.execute_order(
                    date=date, low=low, high=high, close=close,
                    quote=quote, leverage=leverage,
                    position=position, order_type=order_type,
                    expected_execution_price=expected_exec_quote,
                    reduce_only=reduce_only
                )
                return returns
            case OrderType.LIMIT:
                match position:
                    case Position.LONG:
                        if expected_exec_quote <= close:
                            returns = self.execute_order(
                                date=date, low=low, high=high, close=close,
                                quote=quote, leverage=leverage,
                                position=position, order_type=order_type,
                                expected_execution_price=expected_exec_quote,
                                reduce_only=reduce_only
                            )
                            return returns
                    case Position.SHORT:
                        if expected_exec_quote >= close:
                            returns = self.execute_order(
                                date=date, low=low, high=high, close=close,
                                quote=quote, leverage=leverage,
                                position=position, order_type=order_type,
                                expected_execution_price=expected_exec_quote,
                                reduce_only=reduce_only
                            )
                            return returns
                    case _:
                        order = self.create_order(
                            quote=quote,
                            expected_execution_price=expected_exec_quote,
                            position=position,
                            leverage=leverage,
                            order_type=order_type,
                            reduce_only=reduce_only,
                            date=date
                        )
                        self.add_to_limit_orders(order)
                        return -quote

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
        expected_execution_price: float,
        reduce_only: bool
    ) -> float:
        """
        Executes order and returns the profits (including
        investment).

        NETTING:
        Checks first if some fraction or position must be closed.
        """
        returns = 0
        execution_price = self.get_execution_price(
            low=low, high=high, close=close,
            expected_price=expected_execution_price,
            order_type=order_type, position=position
        )
        if self.must_close_open_positions(requested_pos=position):

            closed = self.close_position(
                date=date, quote=quote,
                order_type=order_type,
                close_price=execution_price
            )
            if reduce_only:
                return closed["total_return"]

            returns += closed["total_return"]
            quote -= closed["closed_quote"]

        elif reduce_only:
            return 0

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
            entry_price=execution_price,
            fail_silent=False
        )
        if not response["valid"]:
            return returns

        returns -= response["quote_spent"]
        self.open_orders.append(order)
        self.calculate_netting_liquidation()
        return returns

    def get_open_margin_quote(self) -> float:
        """
        Gets current invested amount from balance.
        """
        return sum(
            order.open_margin_quote for order in self.open_orders
        )

    def should_netting_liquidate(
        self,
        high: float,
        low: float
    ) -> bool:
        """
        Tells if position should be liquidated given a price
        """
        match self.system:
            case OrderSystem.HEDGING:
                return False

            case OrderSystem.NETTING:
                liquidation_price = self.netting_liquidation
                match self.get_position:
                    case Position.LONG:
                        if low <= liquidation_price:
                            return True
                    case Position.SHORT:
                        if high >= liquidation_price:
                            return True
                return False

    def netting_liquidate_position(
        self,
        liquidation_price: float,
        date: datetime
    ) -> None:
        """
        Liquidates all open orders.
        """
        match self.system:
            case OrderSystem.HEDGING:
                return False
            case OrderSystem.NETTING:
                quote_to_close = self.get_invested_not_val_quote(
                    price=liquidation_price
                )

                for order in self.open_orders:
                    order.liquidate_position(
                        liquidation_price=liquidation_price,
                        date=date,
                        print_message=False
                    )
                self.open_orders[0].print_close_message(
                    date=date,
                    close_price=liquidation_price,
                    close_quote=quote_to_close,
                    liquidated=True
                )
                self.closed_orders.extend(self.open_orders)
                self.open_orders = []

    def check_liquidation(
        self,
        high: float,
        low: float,
        date: datetime
    ):
        """
        Checks and liquidates position.

        NETING:
        Checks for netting liquidation.
        """
        if self.should_netting_liquidate(
            high=high,
            low=low
        ):
            self.netting_liquidate_position(
                liquidation_price=self.netting_liquidation,
                date=date
            )

    def calculate_netting_liquidation(self) -> None:
        if self.system == OrderSystem.HEDGING:
            self.netting_liquidation = None

        if len(self.open_orders) == 0:
            self.netting_liquidation = None
            return
        if len(self.open_orders) == 1:
            self.netting_liquidation = self.open_orders[0].liquidation_price
            return

        netting_liq = self.open_orders[-1].entry_price
        dir_int = self.open_orders[0].direction_int
        step = 512
        while step >= 0.4:
            available_quote = self.get_open_margin_quote()
            new_nl = netting_liq - step * dir_int
            for order in self.open_orders:
                if order.should_liquidate(price=new_nl):
                    available_quote -= order.open_margin_quote
                    extra_diff = order.liquidation_price - new_nl
                    extra_loss = order.entry_price - extra_diff
                    available_quote += order.get_PnL(
                        current_price=extra_loss,
                        quote=order.open_size_quote
                    )
                else:
                    available_quote += order.get_PnL(
                        current_price=new_nl,
                        quote=order.open_size_quote
                    ) + order.get_close_fee_quote(
                        quote_to_close=order.open_size_quote,
                        close_price=new_nl,
                        order_type=OrderType.MARKET
                    )

            if available_quote >= 0:
                netting_liq = new_nl
            else:
                step /= 2

        self.netting_liquidation = netting_liq

    def check_limit_orders(self):
        """
        Checks if limit orders should be executed.
        """
        return
