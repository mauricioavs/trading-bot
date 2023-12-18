from .tables import BTCUSDT_TABLE


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
        return table

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

    def get_maintenance_margin(
        self,
        pair: str,
        notional_value: float
    ) -> float:
        """
        Gets maintenance margin of position, useful to calculate
        liquidation price
        """
        table = self.get_table(pair)
        row = table.loc[notional_value <= table['PB']].head(1)
        _, _, _, mmr, ma = row.values[0]
        mm = notional_value * mmr - ma
        return mm

    def calculate_margin_ratio(
        self,
        pair: str,
        notional_value: float,
        margin_quote: float,
        size_base: float,
        entry_price: float,
        mark_price: float,
        direction: int
    ):
        """
        Calculates margin ratio.
        When margin ratio reaches 1, position is liquidated
        """
        maintenance_margin = self.get_maintenance_margin(
            pair=pair,
            notional_value=notional_value
        )
        price_diff = direction * (mark_price - entry_price)
        quote_diff = size_base * price_diff
        margin_ratio = maintenance_margin/(margin_quote + quote_diff)
        return margin_ratio


MARGIN_TABLES = MaintenanceMarginTables()
