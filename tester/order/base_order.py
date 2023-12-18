from datetime import datetime
from order_type import OrderType
from error_messages import (
    INVALID_ORDER_TYPE,
    INVALID_LEVERAGE,
    INVALID_ATTRIBUTE_TYPE
)
from margin_tables import MARGIN_TABLES
from pydantic import BaseModel, model_validator
from typing import List
from position import Position
from difficulty import Difficulty
from helpers import is_zero


class BaseOrder(BaseModel):
    """
    This class manages order validations.

    Note: In BTCUSD and other pairs,
    BTC -> Base currency (first currency)
    USD -> Quote currency (second currency)

    Init Attributes:
    verbose: Print actions
    pair: Use some pair like BTCUSD
    expected_quote: Selected quote investment (includes fee)
    expected_entry_price: Desired entry price for order
    position: Position enum, long or short
    leverage: Leverage to use, limited depending on pair
    use_fee: If false, fees are 0, otherwise use maker or taker
    fee_maker: Fee for limit orders (cheaper)
    fee_taker: Fee for market orders (expensive)
    order_type: An example is MARKET, see order_type.py
    difficulty: Difficulty of market, see difficulty.py
    created_at: datetime when order was created

    Opening Attributes:
    entry_price: The price where order executed
    size_quote: Total bought of position quote currency (margin*leverage).
                This number doest not change due to market fluctuations,
                use notional value instead. Always positive
    margin_quote: Amount spent from my balance
    opening_fee_quote: Quote spent on opening fee
    opened_at: datetime when order was opened

    Closing Attributes:
    close_prices: The prices where order partially closed
    closed_size_quotes: List of partially closed quote until reaches size_quote
    closing_fee_quotes: Quotes spent on closing fees
    PnLs: Quote profits and losses, this does not include fees (opening or closing)
    liquidation_price: Tells if position was liquidated and where
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
    fee_maker: float = 0.002
    fee_taker: float = 0.004
    order_type: OrderType = OrderType.MARKET
    difficulty: Difficulty = Difficulty.MEDIUM
    created_at: datetime = datetime.now()

    entry_price: float = None
    size_quote: float = None
    margin_quote: float = None
    opening_fee_quote: float = None
    opened_at: datetime = None

    close_prices: List[float] = []
    closed_size_quotes: List[float] = []
    closing_fee_quotes: List[float] = []
    closing_order_types: List[OrderType] = []
    PnLs: List[float] = []
    liquidation_price: float = None
    closed_at: List[datetime] = []

    min_base_open: float = None

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
        return abs(open_size_quote)/leverage
    
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


    def __repr__(self):
        return self.position.name

    @model_validator(mode='after')
    def validate_leverage(self) -> None:
        max_leverage = MARGIN_TABLES.get_max_leverage(self.pair, self.expected_quote)
        if self.leverage < 1 or self.leverage > max_leverage:
            INVALID_LEVERAGE.format(
                leverage=str(self.leverage),
                max_leverage=str(max_leverage)
            )

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

    def get_direction_int(
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
        PnL = PnL * quote * current_price * self.get_direction_int()
        return PnL 

    def is_open(self):
        if is_zero(self.open_size_quote):
            return False
        return True

    def print_message(self, message: str) -> None:
        """
        Prints messages if verbose is True
        """
        if self.verbose:
            print(message)

    def __init__(self, amount, leverage, expected_entry_price, position, created_at, 
                 fee_maker, fee_taker, use_fee, symbol, order_type = "MARKET", verbose = True):
        self.verbose = verbose
        self.symbol = symbol
        self.order_type = order_type
        self.amount = amount #desired size of position (leverage included)
        self.leverage = leverage
        self.expected_entry_price = expected_entry_price
        self.position = position #long (1) or short (-1)
        self.fee_maker = fee_maker #comision for limit order
        self.fee_taker= fee_taker #comision for market order
        self.use_fee = use_fee #True or False
        self.created_at = created_at # creating position datetime
        self.min_units = self.get_min_units()
        ########### Open position params ###########
        self.entry_price = None
        self.my_invest = None #amount to really spend from my balance
        self.opening_at = None #opening position datetime
        self.my_pos_amount = None #unlev amount to buy units (spent with no fee)
        self.my_pos_units = None #unit version of above attr
        self.pos_amount = None #position size (includes leverage)
        self.units = None #unit version of above attr
        self.opening_fee_as_amount = None 
        self.opening_fee_as_units = None
        self.blocks = 0 #stores the int number of times that min units can be bought
        self.available = 1 #currently all position is open
        ########### Close position params ###########
        self.closing_at = [] #close position datetime
        self.closing_fee_as_amount = [] 
        self.closing_fee_as_units = []
        self.closing_price = []
        self.liquidated = False #Tells if position was liquidated
        self.liquidation_price = None #stores the single liq price of order, if order is liquidated, to get real one, use closing_price[-1]
        
    def get_entry_price(self, low , high):
        if self.entry_price is not None:
            return self.entry_price
        #open price is a random number of current candle
        if self.order_type == "MARKET": 
            self.entry_price = np.random.uniform(low=low, high=high)
            #open price will be the expected...
        else:
            self.entry_price = self.expected_entry_price
        return self.entry_price

    def get_close_price(self, low, high, close, order_type = "MARKET"):
        if order_type == "MARKET": 
            close_price = np.random.uniform(low=low, high=high)
            #open price will be the expected...
        else:
            close_price = close
        return close_price
        
    def open_position(self, date, low, high):
        ##################### Works for long and short ################## 
        self.opening_at = date # open position datetime
        self.entry_price = self.get_entry_price(low, high)
        min_amount_with_fee = self.get_min_amount_to_spend(self.entry_price, include_fee = True, include_lev = False)
        self.blocks = self.amount // min_amount_with_fee #times min amount can be bought
        self.my_invest = self.get_min_amount_to_spend(self.entry_price, include_fee = True, include_lev = True) * self.blocks
        min_amount = self.get_min_amount_to_spend(self.entry_price, include_fee = False, include_lev = False)
        self.pos_amount = min_amount * self.blocks
        self.units = self.pos_amount / self.entry_price
        self.my_pos_amount = self.pos_amount / self.leverage
        self.my_pos_units = self.my_pos_amount / self.entry_price
        self.opening_fee_as_amount = (min_amount_with_fee - min_amount) * self.blocks
        self.opening_fee_as_units = self.opening_fee_as_amount/self.entry_price
        if self.blocks == 0: 
            print("Insufficient Margin to buy units")
            return False   
        if self.position == 1 and self.verbose:
            print("{} |  Buying {} for {}, leverage {}".format(self.opening_at, round(self.units, 5), round(self.entry_price, 4), self.leverage))
        elif self.verbose:
            print("{} |  Selling {} for {}, leverage {}".format(self.opening_at, round(self.units, 5), round(self.entry_price, 4), self.leverage))
        return True
        
    def get_close_fee(self, price, as_amount= True, prc = 100, use_available = True):
        #long - pay more comission if price raises
        #short - pay more comission if price falls
        if use_available:
            fraction = self.available * ( prc/100 )
        else: #if false, use all initial position budget
            fraction = ( prc/100 )
        fee = self.units * self.entry_price + self.position * self.units * (price - self.entry_price) 
        fee = fee * fraction * self.fee_taker #consider fee used and percentage of position to close
        if not as_amount: fee/=price #as units
        return fee * self.use_fee
    
    def get_PnL(self, price, include_fee = False, as_amount = True, prc = 100, use_available = True):
        #get profit (by default doesnt include fee as Binance)
        if use_available:
            fraction = self.available * ( prc/100 )
        else: #if false, use all initial position budget
            fraction = ( prc/100 )
        PnL = self.position * self.units * (price - self.entry_price) * fraction
        fee = self.get_close_fee(price, as_amount= True, prc = prc, use_available = use_available) * include_fee
        profit = PnL - fee
        if not as_amount: profit/=price
        return profit
    
    def get_current_amount(self, lev = True):
        if lev:
            return (self.pos_amount)*self.available
        else:
            return (self.my_pos_amount)*self.available
    
    def get_position_value(self, price, include_fee = True, as_amount = True, prc = 100, use_available = True):
        if use_available:
            fraction = self.available * ( prc/100 )
        else: #if false, use all initial position budget
            fraction = ( prc/100 )
        #gets the spent money and profits of the position (subtracts closing fee if True)
        profit = self.get_PnL(price = price, include_fee = include_fee, as_amount = True, prc = prc, use_available = use_available)
        pos_val = self.my_pos_amount * fraction  + profit
        if not as_amount: pos_val /= price
        return pos_val
    
    def close_position(self, date, price, prc = 100):
        fraction = self.available * (prc / 100)
        #if after closing with prc the remaining is less than min position, better close all now
        if self.units *(self.available - fraction) < self.min_units:
            prc = 100
            fraction = self.available
        #if closing is less than min units, close minimum units
        elif self.units * fraction < self.min_units:
            prc = (self.min_units / (self.units * self.available))*100
            fraction = self.available * (prc / 100)
        #close always a multiple of min units
        else:
            blocks_to_sell = round(self.blocks * fraction, 0)
            fraction = blocks_to_sell / self.blocks
            prc = fraction / self.available * 100 
        self.closing_at.append( date )
        self.closing_price.append( price )
        self.closing_fee_as_amount.append( self.get_close_fee(price, as_amount = True, prc = prc, use_available = True) )
        self.closing_fee_as_units.append( self.get_close_fee(price, as_amount = False, prc = prc, use_available = True) )
        pos_value = self.get_position_value(price, prc = prc, use_available = True)
        self.available = self.available - fraction #stores the position still opened
        partially = " partially" if self.is_open() else ""
        if self.position == -1 and self.verbose:
            print("{} |  Buying (closing{}) {} for {}".format(date, partially, self.units*fraction, round(price, 6)))
        elif self.verbose:
            print("{} |  Selling (closing{}) {} for {}".format(date, partially, self.units*fraction, round(price, 6)))  
        return pos_value
    
    def is_open(self):
        return abs(self.available) > 1e-12
    
    def is_closed(self):
        return not self.is_open()
    
    def get_maintenance_margin(self, price):
        #this is an example of how to retrieve a table and the necessary row with the information.
        if self.symbol.upper() in "BTCUSDT":
            table = MMT.get_table("BTCUSDT") 
        elif self.symbol.upper() in "BTCBUSD":
            table = MMT.get_table("BTCBUSD")
        else:
            table = MMT.get_table(self.symbol)
        size = self.units*price #size of position
        #locate the corresponding row with size
        row = table.loc[ size >= table['PB'].shift(1).fillna(0) ].loc[ size < table['PB'] ]
        #get all the row values, these are the required to calculate maintenance margin.
        tier, pb, ml, mmr, ma = row.values[0]
        mm = size * mmr - ma
        return mm
    
    def get_min_units(self):
        #get minimum units to buy (doesnt include fee)
        if self.symbol.upper() in "BTCUSDT":
            minimum = MO.get_min_units("BTCUSDT") 
        elif self.symbol.upper() in "BTCBUSD":
            minimum = MO.get_min_units("BTCBUSD")
        else:
            minimum = MO.get_min_units(self.symbol)
        return minimum
    
    def get_min_amount_to_spend(self, price, include_fee = True, include_lev = False):
        #this function returns the minimum amount to spend (includes fee).
        #get my invest in the position    
        pos_amount = self.min_units * price
        spent = pos_amount
        if include_lev: spent = pos_amount / self.leverage
        if not include_fee: return spent
        #include fees of position
        if self.order_type == "MARKET":
            spent += self.use_fee * self.fee_maker * pos_amount 
        else:
            spent += self.use_fee * self.fee_taker * pos_amount 
        return spent

    def calculate_margin_ratio(self, price):
        #when margin ratio == 1, that is the liquidation price
        maintenance_margin = self.get_maintenance_margin(price)
        balance = self.my_pos_amount #just for isolated mode (for cross you must use wallet)
        quantity = self.units
        mark_price = price #for simplicity
        entry_price = self.entry_price
        
        margin_ratio = maintenance_margin/( balance + self.position* quantity * ( mark_price - entry_price ))
        return margin_ratio
    
    def get_liquidation_price(self):
        #uses price instead of mark_price for simplicity
        #the liquidation price changes to farther when mark price gets close, so we  
        #execute this function many times to get close to the real one!!!!
        if self.liquidation_price is not None: return self.liquidation_price
        mark_price = self.entry_price
        pos = self.position
        entry_price = self.entry_price
        balance = self.my_pos_amount #just for isolated mode (for cross you must use wallet)
        quantity = self.units
        precision = 5 #more precision == closer you get to real liquidation price
        for i in range(precision):
            maintenance_margin = self.get_maintenance_margin(mark_price)
            liquidation_price = pos*( maintenance_margin - balance )/quantity + entry_price
            mark_price = liquidation_price
        self.liquidation_price = liquidation_price 
        return self.liquidation_price
    
    def should_liquidate(self, price): 
        if self.position == 1 and price <= self.get_liquidation_price():
            return True
        elif self.position == -1 and price >= self.get_liquidation_price():
            return True
        else:
            return False
    
    def liquidate_position(self, date, global_liquidation = None):
        liq_price = self.liquidation_price
        # if this is given, you have multiple orders and other liquidation price
        if global_liquidation != None:
            liq_price = global_liquidation
        self.closing_at.append( date )
        self.closing_price.append( liq_price )
        self.liquidated = True
        if self.position == -1 and self.verbose:
            print("{} |  Buying (liquidating) {} for {}".format(date, self.units*self.available, round(self.closing_price[-1], 5)))
        elif self.verbose:
            print("{} |  Selling (liquidating) {} for {}".format(date, self.units*self.available, round(self.closing_price[-1], 5))) 
        self.available = 0
        