from enum import Enum


class OrderSystem(Enum):
    """
    A netting account allows the broker to keep the
    risk exposure only for a particular financial
    instrument, while a hedging type account lets
    the broker keep both buy and sell orders
    simultaneously.
    """
    NETTING = "NETTING"
    HEDGING = "HEDGING"
