from binance_api import BinanceAPI
from typing import Any
import pandas as pd
from helpers import get_weekday


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
            'investment_proportions': [0.04, 0.03, 0.02],  # Proporciones de inversión según la importancia de la resistencia
            'take_profit_threshold': 100,  # Umbral de ROI para tomar ganancias y cerrar la posición
            'percent_change_levels': [7.5, 5, 2.5],  # Niveles de cambio porcentual para cierre de posición
            'percent_change_proximity': 0.05,  # Umbral de proximidad para el cierre basado en el porcentaje de cambio
            'wait': 0  # Cantidad de iteraciones a esperar 
        }
        return strategy

    def get_investment_proportion(self, number: float, resistance_levels: list, investment_proportions: list, threshold: float) -> float:
        """
        Get the investment proportion based on the number's proximity to resistance levels.
        """
        for level, proportion in zip(resistance_levels, investment_proportions):
            num = abs(abs(number) - level)
            if num < level * threshold:  # Considerar cerca si está dentro del threshold% del nivel de resistencia
                return proportion
        return 0.01  # Default proportion if no resistance level is close

    def check_resistance(self, number: float, resistance_levels: list, threshold: float) -> bool:
        """
        Check if the number is close to any of the resistance levels.
        """
        for level in resistance_levels:
            num = abs(abs(number) - level)
            if num < level * threshold:  # Considerar cerca si está dentro del threshold% del nivel de resistencia
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
        self.remove_limit_orders() 
        date_prev_24h = bar["Date"] - pd.Timedelta(hours=24)
        try:
            prev24h_bar = self.data.loc[date_prev_24h]
        except KeyError:
            return strategy
        
        # Calcular el cambio porcentual en el precio durante las últimas 24 horas
        percent_change_24h = (bar['Close'] - prev24h_bar['Close']) / prev24h_bar['Close'] * 100
        # if bar['Close'] > prev24h_bar['Close']:
        #     percent_change_24h = (bar['High'] - prev24h_bar['Low']) / prev24h_bar['Low'] * 100
        # else:
        #     percent_change_24h = (bar['Low'] - prev24h_bar['High']) / prev24h_bar['High'] * 100

        # Criterio de salida basado en el ROI o proximidad al porcentaje de cambio
        if not self.order_manager.currently_neutral:
            current_roi = self.order_manager.get_ROI(low=bar["Low"], high=bar["High"], close=bar["Close"])
            if (
                current_roi >= strategy['take_profit_threshold'] or (
                    current_roi > 100 and
                    self.check_resistance(percent_change_24h, strategy['percent_change_levels'], strategy['percent_change_proximity'])
                )
            ):
                self.go_neutral(
                    bar=bar,
                    order_type="LIMIT",
                    expected_exec_quote=bar["Close"]
                )
        else:
            current_roi = 0
        
        # Ajustar la cantidad a invertir cada vez que no se tengan posiciones abiertas
        if self.order_manager.currently_neutral:
            strategy["units_to_invest"] = self.max_invest(consider_closing=False)
            strategy["initial_balance"] = self.wallet.balance
        
        # Obtener la proporción de inversión basada en la proximidad a los niveles de resistencia
        investment_proportion = self.get_investment_proportion(percent_change_24h, strategy['percent_change_levels'], strategy['investment_proportions'], strategy['percent_change_proximity'])
        investment_amount = strategy["units_to_invest"] * investment_proportion

        if strategy['wait'] > 0:
            strategy['wait'] -= 1
            return strategy
  
        if get_weekday(bar["Date"], as_num=False) in ["Friday", "Saturday", "Sunday"]:
            return strategy
     
        # Estrategia de cambio de 24 horas con resistencias psicológicas
        #percent_change_24h < -strategy['percent_change_threshold'] and percent_change_24h > -2.5
        if (
            self.check_resistance(percent_change_24h, strategy['percent_change_levels'], strategy['percent_change_proximity']) and
            percent_change_24h < 0
        ):
            if self.order_manager.currently_long and self.order_manager.open_margin_quote > strategy["initial_balance"] * 0.2:
                return strategy
            if self.order_manager.currently_short and current_roi < 0:
                return strategy
            # Señal de compra (long) si el cambio porcentual es positivo, no hay resistencia cercana y no hay posición abierta
            self.go_long(
                bar=bar,
                quote=investment_amount,  # Cantidad a invertir en USDT
                wallet_prc=False,
                go_neutral_first=False,
                order_type="LIMIT",
                expected_exec_quote=bar["Close"]
            )
            strategy['wait'] = 0
        elif (
            self.check_resistance(percent_change_24h, strategy['percent_change_levels'], strategy['percent_change_proximity']) and
            percent_change_24h > 0 and current_roi >= 0
        ):
            if self.order_manager.currently_short and self.order_manager.open_margin_quote > strategy["initial_balance"] * 0.2:
                return strategy
            if self.order_manager.currently_long and current_roi < 0:
                return strategy
            # Señal de venta (short) si el cambio porcentual es negativo, no hay resistencia cercana y no hay posición abierta
            self.go_short(
                bar=bar,
                quote=investment_amount,  # Cantidad a invertir en USDT
                wallet_prc=False,
                go_neutral_first=False,
                order_type="LIMIT",
                expected_exec_quote=bar["Close"]
            )
            strategy['wait'] = 0

        return strategy
