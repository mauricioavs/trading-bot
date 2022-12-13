


import pandas as pd
import numpy as np
import pandas_ta as ta


class SMA():
    
    def __init__(self, data, SMA_S, SMA_L, column, default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.SMA_S = column + "|SMA|" + str(SMA_S) # short SMA
        self.SMA_L = column + "|SMA|" + str(SMA_L) # long SMA
        self.short = SMA_S
        self.long = SMA_L
        self.column = column # column to use SMA
        self.default_strategy = default_strategy #strategy to use
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.SMA_S in self.data.columns or force:
            self.data[self.SMA_S] = self.data[self.column].rolling(self.short).mean()  
        if not self.SMA_L in self.data.columns or force:    
            self.data[self.SMA_L] = self.data[self.column].rolling(self.long).mean()
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    
    def calculate_for_last_row(self): #calculate just for last row
        self.data.loc[self.data.index[-1],self.SMA_S] = self.data[self.column].iloc[-self.short:].rolling(self.short).mean()[-1]
        self.data.loc[self.data.index[-1],self.SMA_L] = self.data[self.column].iloc[-self.long:].rolling(self.long).mean()[-1]
    
    def strategy(self, row, num = -1):
        return self.strategy1(row)
    
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.SMA_S][row] > self.data[self.SMA_L][row]: # signal to go long
            return 1
        elif self.data[self.SMA_S][row] < self.data[self.SMA_L][row]: # signal to go short
            return -1
        else:
            return 0

class EWMA():
    #https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
    #approx average periods n are calculated by: n is approx 1/(1 - alpha)
    # => we are going to calculate alpha given n approx average periods as: alpha = 1- 1/n
    #Important: approx_avg_period are float in (1, inf). In (1,2) considers high weights for current day
    def __init__(self, data, approx_avg_period_s, approx_avg_period_l,
                 column, default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.approx_avg_period_s = approx_avg_period_s
        self.approx_avg_period_l = approx_avg_period_l
        self.alpha_s = 1-1/approx_avg_period_s #alpha for short EWMA
        self.alpha_l = 1-1/approx_avg_period_l #alpha for long EWMA
        self.column = column # column to use SMA
        self.EWMA_S = column + "|EWMA|a" + str(approx_avg_period_s) # short SMA using alpha
        self.EWMA_L = column + "|EWMA|a" + str(approx_avg_period_l) # long SMA using alpha
        self.default_strategy = default_strategy #strategy to use
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.EWMA_S in self.data.columns or force:
            self.data[self.EWMA_S] = self.data[self.column].ewm(alpha = self.alpha_s).mean()
        if not self.EWMA_L in self.data.columns or force:
            self.data[self.EWMA_L] = self.data[self.column].ewm(alpha = self.alpha_l).mean()
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        s = round(self.approx_avg_period_s)
        l = round(self.approx_avg_period_l)
        # precision. EWMA with more info gives more approx results as "calculate". recommend p = 2
        # for small s, needs more precision.
        p_s = max([100, s*2]) # min 100 of precision
        p_l = max([100, l*2]) # min 100 of precision
        #calculate EWMA and just update last row
        self.data.loc[self.data.index[-1],self.EWMA_S] = self.data[self.column][-p_s:].ewm(alpha = self.alpha_s).mean()[-1]
        self.data.loc[self.data.index[-1],self.EWMA_L] = self.data[self.column][-p_l:].ewm(alpha = self.alpha_l).mean()[-1]
    
    def strategy(self, row, num = -1):
        return self.strategy1(row)    
    
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.EWMA_S][row] > self.data[self.EWMA_L][row]: # signal to go long
            return 1
        elif self.data[self.EWMA_S][row] < self.data[self.EWMA_L][row]: # signal to go short
            return -1
        else:
            return 0
        
class BollingerBands():
    
    def __init__(self, data, column = "price", dev = 1, periods = 50,
                 default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.column = column #column used to calculate BBs
        self.dev = dev #standard deviations for BBs
        self.BBS = column + "|BBs|" + str(dev)+"|"+str(periods) #Name of BBS
        self.SMA = column + "|SMA|" + str(periods) #SMA FOR BBs
        self.last_position = 0 #saves last position
        self.periods = periods
        self.default_strategy = default_strategy #strategy to use
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.BBS+"|Distance" in self.data.columns or force:
            SM = self.data[self.column].rolling(self.periods) #SMA one step before calculating mean()
            if not self.SMA in self.data.columns or force: self.data[self.SMA] = SM.mean()
            self.data[self.BBS+"|Lower"] = self.data[self.SMA] - SM.std() * self.dev
            self.data[self.BBS+"|Upper"] = self.data[self.SMA] + SM.std() * self.dev
            self.data[self.BBS+"|Distance"] = self.data[self.column] - self.data[self.SMA] 
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        SM = self.data[self.column][-self.periods:].rolling(self.periods)
        self.data.loc[self.data.index[-1],self.SMA] = SM.mean()[-1]
        self.data.loc[self.data.index[-1],self.BBS + "|Lower"] = self.data[self.SMA][-1] - SM.std()[-1] * self.dev
        self.data.loc[self.data.index[-1],self.BBS + "|Upper"] = self.data[self.SMA][-1] + SM.std()[-1] * self.dev
        self.data.loc[self.data.index[-1],self.BBS + "|Distance"] = self.data[self.column][-1] - self.data[self.SMA][-1] 

    def strategy(self, row, num = -1):
        return self.strategy1(row)  
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        ### How to evaluate vectorized strategy ###
        #self.data["position"] = np.where(self.data[self.column] < self.data.Lower, 1, np.nan)
        #self.data["position"] = np.where(self.data[self.column] > self.data.Upper, -1, self.data["position"])
        #self.data["position"] = np.where(self.data.distance * self.data.distance.shift(1) < 0, 0, self.data["position"])
        #self.data["position"] = self.data.position.ffill().fillna(0) 
                
        if self.data[self.column][row] < self.data[self.BBS+"|Lower"][row]:
            self.last_position = 1
        elif self.data[self.column][row] > self.data[self.BBS+"|Upper"][row]:
            self.last_position = -1 
        elif row != 0 and self.data[self.BBS+"|Distance"][row] * self.data[self.BBS+"|Distance"][row-1] < 0:
            self.last_position = 0
        return self.last_position

    
class MACD():
    #https://www.alpharithms.com/calculate-macd-python-272222/
    def __init__(self, data, column, fast=12, slow=26, signal=9, 
                 default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.column = column # column to use SMA
        self.fast = fast
        self.slow = slow
        self.signal = signal
        #column names given by pandas_ta
        self.macd = column + "_MACD_" + str(fast) + "_"+ str(slow)  + "_" + str(signal) #ewmaFast - ewmaSlow
        self.macds = column + "_MACDs_" + str(fast) + "_"+ str(slow)  + "_" + str(signal) #ewmaSignal
        self.macdh = column + "_MACDh_" + str(fast) + "_"+ str(slow)  + "_" + str(signal) #macd - macds
        self.default_strategy = default_strategy #strategy to use
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.macd in self.data.columns or force:
            self.data.ta.macd(close=self.column, fast=self.fast, slow=self.slow, 
                              signal=self.signal, append=True, prefix = self.column)  
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        #approximate results, dont use all dataframe 
        cols = self.data[-250:].ta.macd(close=self.column, fast=self.fast, slow=self.slow, 
                          signal=self.signal, append=False, prefix = self.column)
        #append results to last row
        self.data.loc[self.data.index[-1], self.macd] = cols[self.macd][-1]
        self.data.loc[self.data.index[-1], self.macdh] = cols[self.macdh][-1]
        self.data.loc[self.data.index[-1], self.macds] = cols[self.macds][-1]
   
    def strategy(self, row, num = -1):
        return self.strategy1(row)          
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.macdh][row] > 0: # signal to go long
            return 1
        else:
            return -1
        
class RSI():
    #https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/
    def __init__(self, data, column, length=14, default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.column = column # column to use SMA
        self.length = length
        #column names given by pandas_ta
        self.rsi = column + "_RSI_" + str(length)
        self.default_strategy = default_strategy #strategy to use
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.rsi in self.data.columns or force:
            self.data.ta.rsi(close=self.column, length = self.length, append=True, prefix = self.column)  
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        #approximate results, dont use all dataframe 
        cols = self.data[-200:].ta.rsi(close=self.column, length = self.length, append=False)
        #append results to last row
        self.data.loc[self.data.index[-1], self.rsi] = cols[-1]

    def strategy(self, row, num = -1):
        if num == -1: num = self.default_strategy #use default strategy 
        if num == 2:
            return self.strategy2(row)
        return self.strategy1(row)   
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.rsi][row] > 70: 
            return -1
        elif self.data[self.rsi][row] < 30:
            return 1
        return 0
    
    def strategy2(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.rsi][row] > 70: 
            return 1
        elif self.data[self.rsi][row] < 30:
            return -1
        return 0
    
class Hammer():
    #https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/
    def __init__(self, data, open_ = "Open", high = "High", low = "Low",
                 close = "Close", default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.open_ = open_
        self.high = high
        self.low = low
        self.close = close
        self.default_strategy = default_strategy #strategy to use
        #column names given by pandas_ta
        self.hammer = "CDL_HAMMER" 
        self.invhammer = "CDL_INVERTEDHAMMER"
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.hammer in self.data.columns or force:
            res = ta.cdl_pattern(name = "hammer", open_ = self.data[self.open_], high = self.data[self.high], 
               close = self.data[self.close], low = self.data[self.low])
            self.data[self.hammer] = np.sign(res)
        if not self.invhammer in self.data.columns or force:
            res = ta.cdl_pattern(name = "invertedhammer", open_ = self.data[self.open_], 
                high = self.data[self.high], close = self.data[self.close], low = self.data[self.low]) 
            self.data[self.invhammer] = np.sign(res)
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        res = ta.cdl_pattern(name = "hammer", open_ = self.data[self.open_][-1:], 
                             high = self.data[self.high][-1:], close = self.data[self.close][-1:], 
                             low = self.data[self.low][-1:])
        resinv = ta.cdl_pattern(name = "invertedhammer", open_ = self.data[self.open_][-1:], 
                             high = self.data[self.high][-1:], close = self.data[self.close][-1:], 
                             low = self.data[self.low][-1:])
        #append results to last row
        self.data.loc[self.data.index[-1], self.hammer] = np.sign(res[self.hammer][0])
        self.data.loc[self.data.index[-1], self.invhammer] = np.sign(resinv[self.invhammer][0])

    def strategy(self, row, num = -1):
        if num == -1: num = self.default_strategy #use default strategy 
        if num == 2:
            return self.strategy2(row)
        return self.strategy1(row)   
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.hammer][row] == 1: 
            return 1
        elif self.data[self.invhammer][row] == 1:
            return -1
        return 0
    
    def strategy2(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.hammer][row] == 1: 
            return -1
        elif self.data[self.invhammer][row] == 1:
            return 1
        return 0
    
class Doji():
    #https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/
    def __init__(self, data, open_ = "Open", high = "High", low = "Low",
                 close = "Close", default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.open_ = open_
        self.high = high
        self.low = low
        self.close = close
        self.default_strategy = default_strategy #strategy to use
        #column names given by pandas_ta
        self.doji = "CDL_DOJI_10_0.1"
        self.dfdoji = "CDL_DRAGONFLYDOJI"
        self.gsdoji = "CDL_GRAVESTONEDOJI"
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.doji in self.data.columns or force:
            res = ta.cdl_pattern(name = "doji", open_ = self.data[self.open_], 
                                 high = self.data[self.high], close = self.data[self.close], 
                                 low = self.data[self.low])
            self.data[self.doji] = np.sign(res)
        if not self.dfdoji in self.data.columns or force:
            res = ta.cdl_pattern(name = "dragonflydoji", open_ = self.data[self.open_], 
                                 high = self.data[self.high], close = self.data[self.close], 
                                 low = self.data[self.low])
            self.data[self.dfdoji] = np.sign(res)
        if not self.gsdoji in self.data.columns or force:
            res = ta.cdl_pattern(name = "gravestonedoji", open_ = self.data[self.open_], 
                                 high = self.data[self.high], close = self.data[self.close], 
                                 low = self.data[self.low])
            self.data[self.gsdoji] = np.sign(res)    
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        doji = ta.cdl_pattern(name = "doji", open_ = self.data[self.open_], 
                             high = self.data[self.high], close = self.data[self.close], 
                             low = self.data[self.low])
        dfdoji = ta.cdl_pattern(name = "dragonflydoji", open_ = self.data[self.open_][-1:], 
                             high = self.data[self.high][-1:], close = self.data[self.close][-1:], 
                             low = self.data[self.low][-1:])
        gsdoji = ta.cdl_pattern(name = "gravestonedoji", open_ = self.data[self.open_][-1:], 
                             high = self.data[self.high][-1:], close = self.data[self.close][-1:], 
                             low = self.data[self.low][-1:])
        #append results to last row
        self.data.loc[self.data.index[-1], self.doji] =np.sign(doji[self.doji][-1])
        self.data.loc[self.data.index[-1], self.dfdoji] =np.sign(dfdoji[self.dfdoji][0])
        self.data.loc[self.data.index[-1], self.gsdoji] =np.sign(gsdoji[self.gsdoji][0])

    def strategy(self, row, num = -1):
        if num == -1: num = self.default_strategy #use default strategy 
        if num == 2:
            return self.strategy2(row)
        return self.strategy1(row)   
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.gsdoji][row] == 1: 
            return -1
        elif self.data[self.dfdoji][row] == 1:
            return 1
        elif self.data[self.doji][row] == 1:
            return 0
        return 0
    
    def strategy2(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.gsdoji][row] == 1: 
            return 1
        elif self.data[self.dfdoji][row] == 1:
            return -1
        elif self.data[self.doji][row] == 1:
            return 0
        return 0

class EBSW():
    def __init__(self, data, column = "Close", default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.column = column
        self.default_strategy = default_strategy #strategy to use
        self.ebsw = column + "_EBSW" 
        self.last_position = 0 #saves last position
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.ebsw in self.data.columns or force:
            res = ta.ebsw(close = self.data[self.column])
            self.data[self.ebsw] = res
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        res = ta.ebsw(close = self.data[self.column].tail(90))
        #append results to last row
        self.data.loc[self.data.index[-1], self.ebsw] = res[-1]

    def strategy(self, row, num = -1):
        if num == -1: num = self.default_strategy #use default strategy 
        if num == 2:
            return self.strategy2(row)
        return self.strategy1(row)   
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.ebsw][row] > 0.9: 
            self.last_position = -1
        elif self.data[self.ebsw][row] < -0.9:
            self.last_position = 1
        return self.last_position

    
    def strategy2(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.ebsw][row] > 0.8: 
            self.last_position = -1
        elif self.data[self.ebsw][row] < -0.8:
            self.last_position = 1
        return self.last_position

class ADX():
    def __init__(self, data, close = "Close", high = "High", low = "Low", default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.close = close
        self.high = high
        self.low = low
        self.default_strategy = default_strategy #strategy to use
        self.adx = close + "_" + high + "_" + low + "_ADX_14"
        self.dmp = close + "_" + high + "_" + low + "_DMP_14" 
        self.dmn = close + "_" + high + "_" + low + "_DMN_14" 
        self.last_position = 0 #saves last position
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.adx in self.data.columns or force:
            self.data.ta.adx(close = self.close, high = self.high, low = self.low, 
                             append = True, prefix = self.close + "_" + self.high + "_" + self.low)
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        res = self.data.tail(250).ta.adx(close = self.close, high = self.high, low = self.low, 
                             append = False, prefix = self.close + "_" + self.high + "_" + self.low)
        self.data.loc[self.data.index[-1], self.adx] = res[self.adx][-1]
        self.data.loc[self.data.index[-1], self.dmp] = res[self.dmp][-1]
        self.data.loc[self.data.index[-1], self.dmn] = res[self.dmn][-1]

    def strategy(self, row, num = -1):
        if num == -1: num = self.default_strategy #use default strategy 
        if num == 2:
            return self.strategy2(row)
        return self.strategy1(row)   
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.adx][row] < 25: 
            self.last_position = 0
            return 0
        if self.data[self.dmp][row] > self.data[self.dmn][row]:
            self.last_position = 1
        else:
            self.last_position = -1
        return self.last_position

    
    def strategy2(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.adx][row] < 20: 
            self.last_position = 0
            return 0
        if self.data[self.dmp][row] > self.data[self.dmn][row]:
            self.last_position = 1
        else:
            self.last_position = -1
        return self.last_position

class KVO():
    def __init__(self, data, close = "Close", high = "High", 
                 low = "Low", volume = "Volume", default_strategy = 1, weight = 1):
        self.data = data # Dataframe
        self.weight = weight #weight on the strategy (importance)
        self.close = close
        self.high = high
        self.low = low
        self.volume = volume
        self.default_strategy = default_strategy #strategy to use
        self.kvo = close + "_" + high + "_" + low + "_" + volume + "_KVO_34_55_13"
        self.kvos = close + "_" + high + "_" + low + "_" + volume + "_KVOs_34_55_13" 
        self.last_position = 0 #saves last position
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.kvo in self.data.columns or force:
            self.data.ta.kvo(close = self.close, high = self.high, low = self.low, 
                             volume = self.volume, append = True, 
                             prefix = self.close + "_" + self.high + "_" + self.low + "_" + self.volume)
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        res = ta.kvo(close = self.data[self.close][-400:], high = self.data[self.high][-400:], 
                     low = self.data[self.low][-400:], volume = self.data[self.volume][-400:])
        self.data.loc[self.data.index[-1], self.kvo] = res["KVO_34_55_13"][-1]
        self.data.loc[self.data.index[-1], self.kvos] = res["KVOs_34_55_13"][-1]

    def strategy(self, row, num = -1):
        if num == -1: num = self.default_strategy #use default strategy 
        if num == 2:
            return self.strategy2(row)
        return self.strategy1(row)   
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.kvo][row] > 0 and self.data[self.kvo][row] > self.data[self.kvos][row]: 
            self.last_position = 1
        elif self.data[self.kvo][row] < 0 and self.data[self.kvo][row] < self.data[self.kvos][row]: 
            self.last_position = -1
        else:
            self.last_position = 0
        return self.last_position

    
    def strategy2(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.kvo][row] > self.data[self.kvos][row]: 
            self.last_position = 1
        elif self.data[self.kvo][row] < self.data[self.kvos][row]: 
            self.last_position = -1
        return self.last_position