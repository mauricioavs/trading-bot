from tables import BTCUSDT_TABLE


class MaintenanceMarginTables():
    """
    The maximum amount of leverage available depends on the notional value
    of your position, the larger the position, the lower the leverage.
    Tables obtained from:
    https://www.binance.com/en/futures/trading-rules/perpetual/leverage-margin
    PB: Position Bracket (Notional Value in USDT) (top boundary)
    ML: Max Leverage
    MMR: Maintenance Margin Rate
    MA: Maintenance Amount (USDT)
    """

    def __init__(self):
        """
        Get tables from constants
        """
        self.BTCUSDT = BTCUSDT_TABLE

    def get_table(self, pair: str):
        """
        Get a table using its name
        """
        table = getattr(self, pair.upper())
        return eval(table)

    def get_max_leverage(
        self,
        pair: str,
        notional_value: float
    ) -> int:
        """
        Get max leverage given position size. 
        """
        table = self.get_table(pair)
        max_lev = table.loc[notional_value <= table['PB']].ML.iloc[0]
        return max_lev


MARGIN_TABLES = MaintenanceMarginTables()
