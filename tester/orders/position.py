from enum import Enum


class Position(Enum):
    """
    LONG: Order expecting price go up
    SHORT: Order expecting price go down
    NEUTRAL: No order
    """
    LONG = 1
    SHORT = -1
    NEUTRAL = 0
