


import pandas as pd
import numpy as np


class SMA():
    
    def __init__(self, data, SMA_S, SMA_L, column):
        self.data = data # Dataframe
        self.SMA_S = column + "|SMA|" + str(SMA_S) # short SMA
        self.SMA_L = column + "|SMA|" + str(SMA_L) # long SMA
        self.short = SMA_S
        self.long = SMA_L
        self.column = column # column to use SMA
        
    def calculate(self, force = False): #calculate for all dataframe
        if not self.SMA_S in self.data.columns or force:
            self.data[self.SMA_S] = self.data[self.column].rolling(self.short).mean()  
        if not self.SMA_L in self.data.columns or force:    
            self.data[self.SMA_L] = self.data[self.column].rolling(self.long).mean()
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    
    def calculate_for_last_row(self): #calculate just for last row
        self.data[self.SMA_S].iloc[-1] = self.data[self.column].iloc[-self.short:].rolling(self.short).mean()[-1]
        self.data[self.SMA_L].iloc[-1] = self.data[self.column].iloc[-self.long:].rolling(self.long).mean()[-1]
    
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.SMA_S].iloc[row] > self.data[self.SMA_L].iloc[row]: # signal to go long
            return 1
        elif self.data[self.SMA_S].iloc[row] < self.data[self.SMA_L].iloc[row]: # signal to go short
            return -1
        else:
            return 0

class EWMA():
    #https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
    #approx average periods n are calculated by: n is approx 1/(1 - alpha)
    # => we are going to calculate alpha given n approx average periods as: alpha = 1- 1/n
    #Important: approx_avg_period are float in (1, inf). In (1,2) considers high weights for current day
    def __init__(self, data, approx_avg_period_s, approx_avg_period_l, column):
        self.data = data # Dataframe
        self.approx_avg_period_s = approx_avg_period_s
        self.approx_avg_period_l = approx_avg_period_l
        self.alpha_s = 1-1/approx_avg_period_s #alpha for short EWMA
        self.alpha_l = 1-1/approx_avg_period_l #alpha for long EWMA
        self.column = column # column to use SMA
        self.EWMA_S = column + "|EWMA|" + str(approx_avg_period_s) # short SMA
        self.EWMA_L = column + "|EWMA|" + str(approx_avg_period_l) # long SMA
        
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
        self.data[self.EWMA_S].iloc[-1:] = self.data[self.column].iloc[-p_s:].ewm(alpha = self.alpha_s).mean()[-1]
        self.data[self.EWMA_L].iloc[-1:] = self.data[self.column].iloc[-p_l:].ewm(alpha = self.alpha_l).mean()[-1]
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        if self.data[self.EWMA_S].iloc[row] > self.data[self.EWMA_L].iloc[row]: # signal to go long
            return 1
        elif self.data[self.EWMA_S].iloc[row] < self.data[self.EWMA_L].iloc[row]: # signal to go short
            return -1
        else:
            return 0
        
class BollingerBands():
    #https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
    #approx average periods n are calculated by: n is approx 1/(1 - alpha)
    # => we are going to calculate alpha given n approx average periods as: alpha = 1- 1/n
    #Important: approx_avg_period are float in (1, inf). In (1,2) considers high weights for current day
    def __init__(self, data, column = "price", dev = 1, periods = 50):
        self.data = data # Dataframe
        self.column = column #column used to calculate BBs
        self.dev = dev #standard deviations for BBs
        self.SMA = column + "|BBs|" + str(dev)+"|"+str(periods) #SMA FOR BBs
        self.last_position = 0 #saves last position
        self.periods = periods
    def calculate(self, force = False): #calculate for all dataframe
        if not self.SMA in self.data.columns or force:
            SM = self.data[self.column].rolling(self.periods) #SMA one step before calculating mean()
            self.data[self.SMA] = SM.mean()
            self.data[self.SMA+"|Lower"] = self.data[self.SMA] - SM.std() * self.dev
            self.data[self.SMA+"|Upper"] = self.data[self.SMA] + SM.std() * self.dev
            self.data[self.SMA+"|Distance"] = self.data[self.column] - self.data[self.SMA] 
        #DONT DROP NA BECAUSE OTHER INDICATORS NEED THAT ROWS!!!
    def calculate_for_last_row(self): #calculate just for last row
        SM = self.data[self.column].iloc[-self.SMA:].rolling(self.SMA)
        self.data[self.SMA].iloc[-1:] = SM.mean()[-1]
        self.data[self.SMA + "|Lower"].iloc[-1:] = self.data[self.SMA].iloc[-1:] - SM.std()[-1] * self.dev
        self.data[self.SMA + "|Upper"].iloc[-1:] = self.data[self.SMA].iloc[-1:] + SM.std()[-1] * self.dev
        
    def strategy1(self, row):
        '''Returns predicted position (1,0 or -1)'''
        ### How to evaluate vectorized strategy ###
        #self.data["position"] = np.where(self.data[self.column] < self.data.Lower, 1, np.nan)
        #self.data["position"] = np.where(self.data[self.column] > self.data.Upper, -1, self.data["position"])
        #self.data["position"] = np.where(self.data.distance * self.data.distance.shift(1) < 0, 0, self.data["position"])
        #self.data["position"] = self.data.position.ffill().fillna(0) 
                
        if self.data[self.column].iloc[row] < self.data[self.SMA+"|Lower"].iloc[row]:
            self.last_position = 1
            return self.last_position
        elif self.data[self.column].iloc[row] > self.data[self.SMA+"|Upper"].iloc[row]:
            self.last_position = -1 
            return self.last_position
        elif row != 0 and self.data[self.SMA+"|Distance"].iloc[row] * self.data[self.SMA+"|Distance"].iloc[row-1] < 0:
            self.last_position = 0
            return self.last_position
        else:
            return self.last_position
        