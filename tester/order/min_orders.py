class MinOrders():
    """
    Stores minimum amount that can be bought of asset.
    Multiples of base currency (first currency) must be purchased.
    """

    def __init__(self):
        """
        Stores min amounts to buy from pairs base currencies
        """
        self.BTCUSDT = 0.001

    def get_min_units(self, pair: str):
        """
        Gets minimum amount to buy of base currency from pair
        """
        try:
            return getattr(self, pair.upper())
        except AttributeError:
            raise AttributeError("Pair does not exist: " + pair.upper())


MINORDERS = MinOrders()
