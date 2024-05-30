from binance_api import BinanceAPI
from typing import Any
import pandas as pd


class Tester(BinanceAPI):
    """
    This class includes test methods
    """
    def prepare_strategy(self) -> Any:
        """
        Prepare the strategy and return it.
        This prepares strategy.
        """
        strategy = {
            'percent_change_threshold': 0.5,  # Umbral de cambio porcentual para tomar una señal de trading
            'resistance_levels': [10000, 5000, 2500, 1000],  # Niveles de resistencia psicológica
            'resistance_threshold': 0.2,  # Umbral de distancia porcentual a cada resistencia psicológica
            'investment_proportions': [0.06, 0.02, 0.02, 0.02],  # Proporciones de inversión según la importancia de la resistencia
            'take_profit_threshold': 2  # Umbral de ROI para tomar ganancias y cerrar la posición
        }
        return strategy

    def get_investment_proportion(self, price: float, resistance_levels: list, investment_proportions: list, threshold: float) -> float:
        """
        Get the investment proportion based on the price's proximity to resistance levels.
        """
        for level, proportion in zip(resistance_levels, investment_proportions):
            number = abs(price % level)
            if number < level * threshold or number > level * (1-threshold):  # Considerar cerca si está dentro del 1% del nivel de resistencia
                return proportion
        return 0.01  # Default proportion if no resistance level is close

    def check_resistance(self, price: float, resistance_levels: list, threshold: float) -> bool:
        """
        Check if the price is close to any of the resistance levels.
        """
        for level in resistance_levels:
            number = abs(price % level)
            if number < level * threshold or number > level * (1-threshold):  # Considerar cerca si está dentro del 1% del nivel de resistencia
                return True
        return False

    def run_strategy(
        self,
        bar: pd.Series,
        strategy: Any
    ) -> Any:
        """
        Runs strategy given a bar.
        Updates strategy for the next execution.

        Returns strategy.
        """
        date_prev_24h = bar["Date"] - pd.Timedelta(hours=24)
        try:
            prev24h_bar = self.data.loc[date_prev_24h]
        except KeyError:
            return strategy
        
        # Calcular el cambio porcentual en el precio durante las últimas 24 horas
        percent_change_24h = (bar['Close'] - prev24h_bar['Close']) / prev24h_bar['Close'] * 100

        # Criterio de salida basado en el ROI
        if not self.order_manager.currently_neutral:
            current_roi = self.order_manager.get_ROI(low=bar["Low"], high=bar["High"], close=bar["Close"])
            if current_roi >= strategy['take_profit_threshold']:
                self.go_neutral(
                    bar=bar,
                    order_type="MARKET",
                    expected_exec_quote=bar["Close"]
                )
        else:
            current_roi = 0
        
        # Ajustar la cantidad a invertir cada vez que no se tengan posiciones abiertas
        if self.order_manager.currently_neutral:
            strategy["units_to_invest"] = self.max_invest(consider_closing=False)
            strategy["initial_balance"] = self.wallet.balance
        
        # Obtener la proporción de inversión basada en la proximidad a los niveles de resistencia
        investment_proportion = self.get_investment_proportion(bar['Close'], strategy['resistance_levels'], strategy['investment_proportions'], strategy['resistance_threshold'])
        investment_amount = strategy["units_to_invest"] * investment_proportion
        
        # Estrategia de cambio de 24 horas con resistencias psicológicas
        if (
            (True and  percent_change_24h  > strategy['percent_change_threshold']) or
            (self.order_manager.currently_long and current_roi < -20)
            #self.check_resistance(bar['Close'], strategy['resistance_levels'], strategy['resistance_threshold'])
            #(current_roi == 0 or current_roi < -50)
            #(current_roi == 0 or abs(current_roi) > 60) 
        ):
            if self.order_manager.currently_long and self.order_manager.open_margin_quote > strategy["initial_balance"] * 0.2:
                return strategy
            # Señal de compra (long) si el cambio porcentual es positivo, no hay resistencia cercana y no hay posición abierta
            self.go_long(
                bar=bar,
                quote=investment_amount,  # Cantidad a invertir en USDT
                wallet_prc=False,
                go_neutral_first=False,
                order_type="MARKET",
            )
        elif (
            (True and percent_change_24h < -strategy['percent_change_threshold']) or
            (self.order_manager.currently_short and current_roi < -20)
            #self.check_resistance(bar['Close'], strategy['resistance_levels'], strategy['resistance_threshold'])
            #(current_roi == 0 or current_roi < -50)
            # (current_roi == 0 or abs(current_roi) > 60) 
        ):
            if self.order_manager.currently_short and self.order_manager.open_margin_quote > strategy["initial_balance"] * 0.2:
                return strategy
            # Señal de venta (short) si el cambio porcentual es negativo, no hay resistencia cercana y no hay posición abierta
            self.go_short(
                bar=bar,
                quote=investment_amount,  # Cantidad a invertir en USDT
                wallet_prc=False,
                go_neutral_first=False,
                order_type="MARKET",
            )
            

        return strategy