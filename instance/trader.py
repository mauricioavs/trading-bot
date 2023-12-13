from lib.TechnicalIndicators import *
from binance.client import Client
from binance.websocket.cm_futures.websocket_client import CMFuturesWebsocketClient
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

class FuturesTrader():
    def __init__(self, symbol="btcusd", testnet = True, verbose = True):
        ####API CONNECTIONS ####
        self.stream = None
        self.testnet = testnet
        self.client = Client(api_key = api_key, api_secret = secret_key, tld = "com", testnet = testnet)
        self.verbose = verbose
        #######################
        self.data = None
        self.symbol = symbol
        self.asset = self.get_asset(self.symbol) #get asset like "USDT"
        #### "BTCUSD" is not valid with official api methods, need to use "BTCUSDT" ####
        symbol = self.symbol + "t" if self.asset == "USDT"  else self.symbol
        self.symbol_upper = symbol.upper()
        self.strategies = [] #this stores the strategies used
        self.leverage = 1 #stores current leverage
        self.get_current_invested_amount()
        self.initial_balance = self.get_current_balance() #sotres the initial balance of the session
        self.available_balance = self.initial_balance #stores available balance
        self.last_close_price = 0 #stores last close price
        self.min_units_to_trade = 1e-03
        self.last_heartbeat = datetime.now()
    
    def get_asset(self, symbol):
        if symbol.endswith('busd'): return "BUSD"
        if symbol.endswith('usd'): return "USDT"
        if symbol.endswith('eth'): return "ETH"
        if symbol.endswith('bnb'): return "BNB"
        if symbol.endswith('btc'): return "BTC"
    
    def send_heartbeat(self):
        URL = "https://push.statuscake.com/?PK=d4682066f8eabd0&TestID=7054134&time=0"
        r = requests.get(url = URL)
        
    def message_handler(self, msg):
        if 'result' in msg.keys(): #skip first message
            return
        # extract the required items from msg
        event_time = pd.to_datetime(msg["E"], unit = "ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit = "ms")
        first   = float(msg["k"]["o"])
        high    = float(msg["k"]["h"])
        low     = float(msg["k"]["l"])
        close   = float(msg["k"]["c"])
        volume  = float(msg["k"]["v"])
        
        QAVol   = float(msg["k"]["q"])
        NoT     = float(msg["k"]["n"])
        TBBAV   = float(msg["k"]["V"])
        TBQAV   = float(msg["k"]["Q"])
        
        complete=       msg["k"]["x"]
        
        time_elapsed = event_time - self.last_heartbeat
        
        if not self.testnet and time_elapsed.seconds > 300:
            self.send_heartbeat()
            self.last_heartbeat = datetime.now()
        
        # print out
        if self.verbose:
            print(".", end = "", flush = True) 
    
        # feed df (add new bar / update latest bar)
        col_num = self.data.shape[1]
        self.data.loc[start_time] = [first, high, low, close, volume,
                                     QAVol, NoT, TBBAV, TBQAV, complete] + [False]*(col_num-10)
        # prepare features and define strategy/trading positions whenever the latest bar is complete
        if complete:
            self.last_close_price = close
            self.run_strategy()
        
    def start_streaming(self, interval="1m"):
        self.stream = CMFuturesWebsocketClient()
        self.stream.start()
        self.stream.kline(
            symbol=self.symbol.lower() +"_perp",
            id=2,
            interval=interval,
            callback=self.message_handler,
        )
        
    def stop_streaming(self):
        self.stream.stop()
        
    def get_most_recent_data(self, num_candles=100, interval = "1m"):
        #### Get start time for candles ####
        now = datetime.utcnow()
        past = str(now - self.available_intervals(num_candles)[interval])
        #### Request candles and prepare the df ####
        bars = self.client.futures_historical_klines(symbol = self.symbol_upper.lower(), 
                                        interval = interval, 
                                        start_str =past,
                                        end_str = None)
        df = pd.DataFrame(bars)
        df["Date"] = pd.to_datetime(df.iloc[:,0], unit = "ms")
        df.columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                      "Close Time", "Quote Asset Volume", "Number of Trades",
                      "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"]
        use_columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Quote Asset Volume",
                       "Number of Trades", "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume"]
        df = df[use_columns].copy()
        df.set_index("Date", inplace = True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors = "coerce")
        df["Complete"] = [True for row in range(len(df)-1)] + [False]    
        self.data = df
    
    def start_trading(self, num_candles = 100, interval = "1m", initial_lev = 10,
                     initial_amount = 10, use_prc = True):
        if interval in self.available_intervals(num_candles).keys():
            self.get_most_recent_data(num_candles = num_candles, interval=interval)
            #### STRATEGY PARAMS ####
            self.use_prc = use_prc
            self.initial_amount = initial_amount
            self.curr_amount = self.initial_amount
            self.initial_lev = initial_lev
            self.curr_order = None
            ########################
            self.prepare_strategies()
            self.change_leverage(self.initial_lev)
            self.start_streaming(interval)
        else:
            print("That interval is not available")
            
    def stop_trading(self):
        self.stop_streaming()
        self.cancel_all_open_orders()
        self.go_neutral()
        #print ending metrics here!!
        
    def available_intervals(self, candles_required):
        '''
        Helper function for "get_most_recent_data" method.
        
        '''
        return {
            "1m"  : timedelta(minutes=candles_required),
            "3m"  : timedelta(minutes=candles_required*3),
            "5m"  : timedelta(minutes=candles_required*5),
            "15m" : timedelta(minutes=candles_required*15),
            "30m" : timedelta(minutes=candles_required*30),
            "1h"  : timedelta(hours=candles_required),
            "2h"  : timedelta(hours=candles_required*2),
            "4h"  : timedelta(hours=candles_required*4),
            "6h"  : timedelta(hours=candles_required*6),
            "8h"  : timedelta(hours=candles_required*8),
            "12h" : timedelta(hours=candles_required*12),
            "1d"  : timedelta(days=candles_required),
            "3d"  : timedelta(days=candles_required*3),
            "1w"  : timedelta(days=candles_required*7),
            "1M"  : timedelta(days=candles_required*28) #this may give less than the desired candles because each month has different amount of days
        }
    def prepare_strategies(self):
        self.strategies.append(
            RNN(
                data = self.data,
                default_strategy = 1,
                model = 'models_work/simple_current.h5',
                scaler = 'models_work/scaler.pkl',
                scaler_obj = 'models_work/scaler_obj.pkl'
            )
        )
        for strategy in self.strategies:
            strategy.calculate() #add columns to data 
    
    def submit_open_orders(self):
        
        #curr_invested = self.get_current_invested_amount()
        self.cancel_all_open_orders()
        amount = (self.get_current_balance() * self.curr_amount/100) * self.leverage
        for strategy in self.strategies:
            strategy.calculate_for_last_row()
            lower_band = strategy.get_param("lower", -1)
            upper_band = strategy.get_param("upper", -1)
            self.go_long(prc = False, amount = amount, go_neutral_first = False, 
                order_type = "LIMIT", price = lower_band, reduceOnly = False)
            self.go_short(prc = False, amount = amount, go_neutral_first = False, 
                order_type = "LIMIT", price = upper_band, reduceOnly = False)    
            #self.curr_amount*=2
            #self.change_leverage(self.leverage*2)
            
    def cancel_all_open_orders(self):
        self.client.futures_cancel_all_open_orders(symbol=self.symbol_upper)
    
    def cancel_open_order(self, order_id):
        self.client.futures_cancel_order(symbol = self.symbol_upper, orderId= order_id)
        
    def get_order(self, order_id):
        order = self.client.futures_get_order(symbol = self.symbol_upper, orderId = order_id)
        return order
    
    def run_strategy(self):
        ## CHECK CURRENT ORDERS ##
        if self.curr_order is not None:
            order = self.get_order(self.curr_order)
            if order["status"] not in ["FILLED"]: # if PARTIALLY_FILLED keep waiting  
                self.cancel_all_open_orders()
            self.curr_order = None
                
        self.pos = 0        
        ##### MAIN ALGORITHM #####
        for strategy in self.strategies:
            strategy.calculate_for_last_row()
            self.pos += strategy.strategy(-1)
            
        self.predicted_pos = np.sign(self.pos)   
        
        if self.predicted_pos == 1 and self.get_position() in [0, -1]:
            self.curr_order = self.go_long(
                prc = True,
                amount = 25,                
                order_type = "LIMIT", price = self.data["Close"][-1],
                go_neutral_first = True
            )
        if self.predicted_pos == 1 and self.get_position() in [0, -1]:
            self.curr_order = self.go_short(
                prc = True,
                amount = 25,                
                order_type = "LIMIT", price = self.data["Close"][-1],
                go_neutral_first = True
            )
        
            
    def go_long(self, prc = True, amount = None, go_neutral_first = False, 
                order_type = "MARKET", price = None, reduceOnly = False, 
                take_profit = False):
        if go_neutral_first:
            self.go_neutral() #if some position, go neutral first
        if prc: 
            amount = (self.get_current_balance() * amount/100) * self.leverage
        if order_type == "MARKET":
            quantity =  amount/self.last_close_price
        elif order_type == "LIMIT":
            quantity = amount/price
        if quantity < self.min_units_to_trade: quantity = self.min_units_to_trade
        order_id = self.create_order(side = "BUY", quantity = quantity, order_type = order_type, price = price,
                                    reduceOnly=reduceOnly)
        self.go_stop_market()    
        return order_id
        
    def go_short(self, prc = True, amount = None, go_neutral_first = False,
                order_type = "MARKET", price = None, reduceOnly = False, 
                 take_profit = False):
        if go_neutral_first:
            self.go_neutral() #if some position, go neutral first
        if prc: 
            amount = (self.get_current_balance() * amount/100) * self.leverage
        if order_type == "MARKET":
            quantity =  amount/self.last_close_price
        elif order_type == "LIMIT":
            quantity = amount/price
        if quantity < self.min_units_to_trade: quantity = self.min_units_to_trade
        order_id = self.create_order(side = "SELL", quantity = quantity, order_type = order_type, price = price,
                         reduceOnly=reduceOnly)
        self.go_stop_market()
        return order_id 
    
    def go_neutral(self, prc = 100, order_type = "MARKET", price = None):
        #prc between 0 and 100
        prc = min(prc, 100)
        prc = max(0, prc)
        quantity = self.get_current_invested_amount()*prc/100 #updates get_position() function
        
        is_invested = abs(self.curr_invested_amount) > 1e-16
        quantity_is_less_than_min_to_trade = quantity < self.min_units_to_trade
        if is_invested and quantity_is_less_than_min_to_trade:
            quantity = self.min_units_to_trade
        
        if self.get_position() == 1: #if long, sell all
            order_id = self.create_order(side = "SELL", quantity = quantity, reduceOnly = True,
                             order_type = order_type, price = price)
            self.close_all_stop_market()
            return order_id
        elif self.get_position() == -1: #if short, buy all
            order_id = self.create_order(side = "BUY", quantity = quantity, reduceOnly = True,
                             order_type = order_type, price = price)
            self.close_all_stop_market()
            return order_id
        return None
        
    def go_stop_market(self):
        #check if there is an stop market and close it
        self.close_all_stop_market()
        #put stop market near liq price to prevent losing all money
        quantity = self.get_current_invested_amount()
        side = "SELL" if self.current_pos > 0 else "BUY"
        liq_price = float(self.client.futures_position_information(symbol = "BTCUSDT")[0]["liquidationPrice"])
        entry_price = float(self.client.futures_position_information(symbol = "BTCUSDT")[0]["entryPrice"])
        stopPrice = round(liq_price + 0.01*(entry_price - liq_price),1)
        self.client.futures_create_order(symbol = self.symbol_upper, side = side,
                    type = "STOP_MARKET", stopPrice=stopPrice, quantity = quantity, reduceOnly = True)
    
    def close_all_stop_market(self):
        #check if there is an stop market and close it
        open_orders = pd.DataFrame(self.client.futures_get_open_orders())
        if len(open_orders) == 0: return
        orders = open_orders[open_orders["origType"]=="STOP_MARKET"]
        for i in range(len(orders)):
            order_id = orders.iloc[i]["orderId"]
            self.cancel_open_order(order_id)
    
    def create_order(self, side = "BUY", quantity = 0, reduceOnly = False, 
                     order_type = "MARKET", price = None, stopPrice = None):
        quantity = round(quantity, 3) #binance accepts max 3 decimals
        if price is not None:
            price = round(price, 1)
        if quantity < self.min_units_to_trade: #dont submit invalid orders
            return 
        if order_type == "MARKET":
            order_open = self.client.futures_create_order(symbol = self.symbol_upper, side = side,
                    type = order_type, quantity = quantity, reduceOnly = reduceOnly,
            )
            order_open = self.client.futures_get_order(symbol = self.symbol_upper,
                                                       orderId = order_open["orderId"])
        elif order_type == "LIMIT":
            order_open = self.client.futures_create_order(symbol = self.symbol_upper, side = side,
                    type = order_type, quantity = quantity, reduceOnly = reduceOnly,
                    price = price, timeInForce = "GTC"                                      
            )
        elif order_type == "TAKE_PROFIT":
            self.client.futures_create_order(symbol = self.symbol_upper, side = side,
                    type = order_type, quantity = quantity, price = price,
                           stopPrice = stopPrice)
        
        return order_open["orderId"]
    
    def get_current_invested_amount(self):
        #IMPORTANT: you wont get notified if a position is liquidated!!!
        #if you want your real time invested amount, call this function before an important action
        #inclues leverage
        infos = self.client.futures_position_information(symbol = self.symbol_upper)
        #use the info of the current pair
        for info in infos:
            if info["symbol"] == self.symbol_upper:
                pos = float(info["positionAmt"])
                self.curr_invested_amount = abs(pos) #invested amount on binance
                self.current_pos = np.sign(pos) #binance pos
                return self.curr_invested_amount
        #not found... no trades then..
        self.curr_invested_amount = 0
        self.current_pos = 0
        return 0
    
    def get_position(self):
        return self.current_pos
    
    def should_end_session(self):
        self.get_current_invested_amount() #updates get_position() function
        if self.available_balance < self.initial_balance * 0.3 and self.get_position() == 0: #no money and no positions
            self.stop_trading()
            return True
    def get_current_balance(self):
        balance = pd.DataFrame(self.client.futures_account_balance())# Asset Balance details
        balance = float(balance[ balance["asset"] == self.asset ].iloc[0]["balance"])
        return balance
    
    def change_leverage(self, new_leverage):
        self.client.futures_change_leverage(symbol = self.symbol_upper, leverage = new_leverage)
        self.leverage = new_leverage
        
        
        
if __name__ == '__main__':
    
    api_key = "6ce63f3406fd8ebbff01054a66c25fe3c851c45932088c8ca3131a7005188462"
    secret_key = "aa3ea32929252467fa5ffeac5818c95beabfb5dba691ef445e7eaa31ea0d15f6"
    
    #api_key = "UhpwtIoi0R1yRgGVp1B7iWPsEgJ4ztyW3Be9CtgiPYnLQfFT3EYe5IxWnRlH3zUG"
    #secret_key = "AbvONonWsBcbUwNx6a3UGBGv6t5EF8gWfIHn3MZHzfCVjXQJhE2fVlPzR52Qitxi"
    
    trader = FuturesTrader(symbol="btcusd", testnet = True, verbose = False)
    trader.start_trading(num_candles = 300, interval = "1h", initial_lev = 5,
                     initial_amount = 25, use_prc = True)