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
            'percent_change_threshold': 1  # Umbral de cambio porcentual para tomar una señal de trading
        }
        return strategy

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

        if self.order_manager.currently_neutral:
            multiplier = 5
            strategy["invest"] = self.max_invest(consider_closing=False) / 100 * multiplier
            strategy["invest_times"] = 0


        if percent_change_24h > strategy['percent_change_threshold']:
            # Señal de compra (long) si el cambio porcentual es positivo y no hay posición abierta
            # if self.order_manager.currently_long and not self.wallet.can_spend(strategy["invest"]/self.order_manager.leverage):
            #     return strategy
            self.go_long(
                bar=bar,
                quote=strategy["invest"],  # Cantidad a invertir en USDT
                wallet_prc=False,
                go_neutral_first=False,
                order_type="MARKET",
                expected_exec_quote=bar["High"]
            )
            
        elif percent_change_24h < -strategy['percent_change_threshold']:
            # if self.order_manager.currently_short and not self.wallet.can_spend(strategy["invest"]/self.order_manager.leverage):
            #     return strategy
            # Señal de venta (short) si el cambio porcentual es negativo y no hay posición abierta
            self.go_short(
                bar=bar,
                quote=strategy["invest"],  # Cantidad a invertir en USDT
                wallet_prc=False,
                go_neutral_first=False,
                order_type="MARKET",
                expected_exec_quote=bar["Low"]
            )

        return strategy
