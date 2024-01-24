from datetime import timedelta


def available_periods(candles_required: int) -> dict:
    '''
    Helper function to get available periods
    of candles.
    '''
    return {
        "1m": timedelta(minutes=candles_required),
        "3m": timedelta(minutes=candles_required*3),
        "5m": timedelta(minutes=candles_required*5),
        "15m": timedelta(minutes=candles_required*15),
        "30m": timedelta(minutes=candles_required*30),
        "1h": timedelta(hours=candles_required),
        "2h": timedelta(hours=candles_required*2),
        "4h": timedelta(hours=candles_required*4),
        "6h": timedelta(hours=candles_required*6),
        "8h": timedelta(hours=candles_required*8),
        "12h": timedelta(hours=candles_required*12),
        "1d": timedelta(days=candles_required),
        "3d": timedelta(days=candles_required*3),
        "1w": timedelta(days=candles_required*7),
        "1M": timedelta(days=candles_required*30)
    }