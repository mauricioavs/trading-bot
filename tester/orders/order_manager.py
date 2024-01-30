from pydantic import BaseModel, field_validator
from orders import (
    Order,
    Position,
    OrderSystem,
    OrderType
)
from typing import List, Union
from datetime import datetime
from orders.difficulty import Difficulty
from helpers import (
    MIN_INVEST_ERROR,
    CANT_CHANGE_LEV,
    FLUCTUATION_ERROR
)


class OrderManager(BaseModel):
    """
    This class manages orders.

    Manages their closing, liquidating and
    other behaviours.

    Init Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSDT
    leverage: leverage used in orders
    difficulty: Difficulty of market, see difficulty.py
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    system: Order behaviour:
        Netting: Orders are merged into one
        Hedging: Orders are separated
    fluctuation: Stores max difference of price in percentage:
                0 < fluctuation < 1

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
    leverage: int = 1
    difficulty: Difficulty = Difficulty.MEDIUM
    use_fee: bool = True
    fee_maker: float = 0.0002
    fee_taker: float = 0.0004
    system: OrderSystem = OrderSystem.NETTING
    fluctuation: float = 0.05

    open_orders: List[Order] = []
    limit_orders: List[Order] = []
    closed_orders: List[Order] = []
    netting_liquidation: float = None

    @field_validator("fluctuation")
    def validate_fluctuation(cls, value: float) -> None:
        """
        Fluctuation is necessary due to difference
        of real with expected execution price:

        0 < fluctuation < 1
        """
        if value < 0 or value > 1:
            raise ValueError(FLUCTUATION_ERROR)
        return value

    @property
    def get_position(self) -> Position:
        """
        Gets current position
        LONG, SHORT or NEUTRAL
        """
        if not self.open_orders:
            return Position.NEUTRAL
        match self.system:
            case OrderSystem.NETTING:
                return self.open_orders[0].position

    @property
    def currently_long(self) -> bool:
        """
        Tells if position is LONG
        """
        return self.get_position == Position.LONG

    @property
    def currently_short(self) -> bool:
        """
        Tells if position is SHORT
        """
        return self.get_position == Position.SHORT

    @property
    def currently_neutral(self) -> bool:
        """
        Tells if position is NEUTRAL
        """
        return self.get_position == Position.NEUTRAL

    @property
    def get_opposite_position(self) -> Position:
        """
        Gets reverse of current position:
        NEUTRAL -> NEUTRAL
        LONG -> SHORT
        SHORT -> LONG
        """
        curr_pos = self.get_position
        if curr_pos == Position.SHORT:
            return Position.LONG
        elif curr_pos == Position.LONG:
            return Position.SHORT
        return Position.NEUTRAL

    def print_message(self, message: str) -> None:
        """
        Prints messages if verbose is True
        """
        if self.verbose:
            print(message)

    def get_min_quote_invest(
        self,
        current_quote_val: float,
        order_type: OrderType,
        position: Position
    ) -> float:
        """
        Gets min investment of a certain quote
        using a max fluctuation of a certain
        percentage.

        If must close orders, then it's 0
        because order will close minimum
        amount automatically.
        """
        if self.must_close_open_positions(
            requested_pos=position
        ):
            return 0

        order = self.create_order(
            quote=0,
            expected_execution_price=current_quote_val,
            position=Position.LONG,
            order_type=order_type,
            date=datetime.now()
        )
        inv = order.get_min_quote_invest(
            execution_quote=current_quote_val,
            fluctuation=self.fluctuation
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

    def get_invested_margin_and_PnL(
        self,
        low: float,
        close: float,
        high: float
    ) -> float:
        """
        Gets invested margin and PnL at the end of period.
        """
        match self.system:
            case OrderSystem.NETTING:
                if self.should_netting_liquidate(
                    low=low,
                    high=high
                ):
                    return 0
                total = 0
                for order in self.open_orders:
                    total += order.open_margin_quote
                    total += order.get_PnL(
                            current_price=close,
                            quote=order.open_size_quote
                        )
                return total

    def get_limit_orders_margin(
        self
    ):
        """
        Sum all margin of limit orders, i.e., the quote
        used to register each limit order.
        """
        quote = 0
        for order in self.limit_orders:
            quote += order.quote_used_to_limit
        return quote

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
        quote: float,
        use_prc: bool = False
    ) -> dict:
        """
        closes the position of certain quote.

        If use_prc is true, then:

        0 < quote < 100

        Returns the closed quote (notional)
        and total return (includes investment, fees and pnl).
        """
        match self.system:
            case OrderSystem.NETTING:
                invested_not_quote = self.get_invested_not_val_quote(
                    price=close_price
                )
                if use_prc:
                    quote = invested_not_quote * quote / 100
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

                if not self.open_orders:
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
        order_type: OrderType,
        date: datetime,
        use_prc_close: float = False,
        reduce_only: bool = False,
    ) -> Order:
        """
        creates order object
        """
        return Order(
            verbose=self.verbose,
            pair=self.pair,
            use_fee=self.use_fee,
            fee_maker=self.fee_maker,
            fee_taker=self.fee_taker,
            difficulty=self.difficulty,
            expected_quote=quote,
            expected_entry_price=expected_execution_price,
            position=position,
            leverage=self.leverage,
            order_type=order_type,
            created_at=date,
            use_prc_close=use_prc_close,
            reduce_only=reduce_only,
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
        creation_date: datetime,
        low: float,
        close: float,
        high: float,
        quote: float,
        position: Position,
        order_type: Union[OrderType, str],
        expected_exec_quote: float,
        execution_date: datetime = None,
        reduce_only: bool = False,
        use_prc_close: bool = False,
        force_limit: bool = False
    ) -> float:
        """
        Submits an order to system.

        Returns the earnings or investment of order
        (could be negative).
        """
        if isinstance(order_type, str):
            order_type = OrderType(order_type.upper())
        if use_prc_close:
            reduce_only = True
        if execution_date is None:
            execution_date = creation_date
        min_quote_invest = self.get_min_quote_invest(
            current_quote_val=expected_exec_quote,
            order_type=order_type,
            position=position
        )
        if quote + 1e-12 < min_quote_invest:
            self.print_message(
                MIN_INVEST_ERROR.replace(
                    "{min_quote}", str(min_quote_invest)
                )
            )
            return 0.0

        if not reduce_only:
            times_min_quote = quote // (min_quote_invest-1e-12)
            quote = min_quote_invest * times_min_quote

        match order_type:
            case OrderType.MARKET:
                returns = self.execute_order(
                    creation_date=creation_date,
                    execution_date=execution_date,
                    low=low, high=high, close=close,
                    quote=quote, order_type=order_type,
                    position=position,
                    expected_execution_price=expected_exec_quote,
                    use_prc_close=use_prc_close,
                    reduce_only=reduce_only
                )
                return returns
            case OrderType.LIMIT:
                match position:
                    case Position.LONG:
                        if close <= expected_exec_quote or force_limit:
                            returns = self.execute_order(
                                creation_date=creation_date,
                                execution_date=execution_date,
                                low=low, high=high, close=close,
                                quote=quote, order_type=order_type,
                                position=position,
                                expected_execution_price=expected_exec_quote,
                                use_prc_close=use_prc_close,
                                reduce_only=reduce_only
                            )
                            return returns
                    case Position.SHORT:
                        if expected_exec_quote <= close or force_limit:
                            returns = self.execute_order(
                                creation_date=creation_date,
                                execution_date=execution_date,
                                low=low, high=high, close=close,
                                quote=quote, order_type=order_type,
                                position=position,
                                expected_execution_price=expected_exec_quote,
                                use_prc_close=use_prc_close,
                                reduce_only=reduce_only
                            )
                            return returns
                order = self.create_order(
                    quote=quote,
                    expected_execution_price=expected_exec_quote,
                    position=position,
                    order_type=order_type,
                    use_prc_close=use_prc_close,
                    reduce_only=reduce_only,
                    date=creation_date
                )
                self.add_to_limit_orders(order)
                return -order.quote_used_to_limit

    def execute_order(
        self,
        creation_date: datetime,
        execution_date: datetime,
        low: float,
        high: float,
        close: float,
        position: Position,
        order_type: OrderType,
        expected_execution_price: float,
        reduce_only: bool,
        quote: float,
        use_prc_close: bool
    ) -> float:
        """
        Executes order and returns the profits (including
        investment).

        use_prc_close means that quote is in percentage
        and reduce_only is obviously activated.

        NETTING:
        Checks first if some fraction or position must be closed.
        """
        if use_prc_close:
            reduce_only = True
        returns = 0
        execution_price = self.get_execution_price(
            low=low, high=high, close=close,
            expected_price=expected_execution_price,
            order_type=order_type, position=position
        )
        if self.must_close_open_positions(requested_pos=position):

            closed = self.close_position(
                date=execution_date, quote=quote,
                order_type=order_type, use_prc=use_prc_close,
                close_price=execution_price,
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
            order_type=order_type,
            date=creation_date
        )

        response = order.open_position(
            date=execution_date,
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
    ) -> float:
        """
        Liquidates all open orders and closes
        limit orders.

        Returns money of limit orders
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
                return self.remove_limit_orders()

    def check_liquidation(
        self,
        high: float,
        low: float,
        date: datetime
    ) -> float:
        """
        Checks and liquidates position.

        NETING:
        Checks for netting liquidation.

        returns quote of canceled limit orders
        """
        if self.should_netting_liquidate(
            high=high,
            low=low
        ):
            match self.system:
                case OrderSystem.NETTING:
                    returns = self.netting_liquidate_position(
                        liquidation_price=self.netting_liquidation,
                        date=date
                    )
                    return returns
        return 0

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

    def remove_limit_order(self, order: Order) -> float:
        """
        Removes limit order not executed and returns the
        invested money.
        """
        self.limit_orders.remove(order)
        return order.expected_quote

    def remove_limit_orders(self) -> float:
        """
        Removes limit orders not executed and returns the
        invested money.
        """
        returns = 0
        for order in self.limit_orders:
            returns += order.quote_used_to_limit
        self.limit_orders = []
        return returns

    def check_limit_orders(
        self,
        date: datetime,
        low: float,
        close: float,
        high: float,
    ) -> float:
        """
        Checks if limit orders should be executed.

        Returns the not invested money.
        """
        returns = 0
        for order in self.limit_orders[:]:
            if order.should_execute(
                low=low,
                high=high
            ):
                returns += self.submit_order(
                    creation_date=order.created_at,
                    execution_date=date,
                    low=low,
                    close=close,
                    high=high,
                    quote=order.expected_quote,
                    position=order.position,
                    order_type=order.order_type,
                    expected_exec_quote=order.expected_entry_price,
                    use_prc_close=order.use_prc_close,
                    reduce_only=order.reduce_only,
                    force_limit=True
                )
                returns += order.quote_used_to_limit
                self.limit_orders.remove(order)
        return returns

    def get_invested_notional_value(
        self,
        quote_value: float
    ) -> float:
        """
        NETTING:
        Gets invested notional value. This does not include
        limit orders not opened.
        """
        match self.system:
            case OrderSystem.NETTING:
                if not self.open_orders:
                    return 0
                invested = 0
                for order in self.open_orders:
                    invested += order.get_notional_value(
                        current_price=quote_value,
                        base=order.open_size_base
                    )
                return invested

    def get_min_leverage(self):
        """
        Returns the min leverage of the orders,
        that is the minimum leverage we can use
        """
        match self.system:
            case OrderSystem.NETTING:
                if not self.open_orders:
                    return 1
                return self.leverage

    def change_leverage(
        self,
        new_lev: int
    ) -> bool:
        """
        Changes leverage considering open positions.

        Returns if change was successful.
        """
        min_lev = self.get_min_leverage()
        match self.system:
            case OrderSystem.NETTING:
                if new_lev < min_lev:
                    self.print_message(
                        CANT_CHANGE_LEV.replace(
                            "{new_lev}", str(new_lev)
                        ).replace(
                            "{current_lev}", str(self.leverage)
                        )
                    )
                    return False
                self.leverage = new_lev
                return True
