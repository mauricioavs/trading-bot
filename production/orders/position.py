from enum import Enum


class Position(Enum):
    """
    LONG: Order expecting price go up
    SHORT: Order expecting price go down
    NEUTRAL: No order
    """
    LONG = "BUY"
    SHORT = "SELL"
    NEUTRAL = None
