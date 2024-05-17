import pandas as pd


def get_weekday(date: pd.Timestamp, as_num=False) -> str:
    """
    Returns day of week of the given date.

    if as_num: Monday -> 0 to Sunday -> 6

    else: returns strings capitalized like 'Monday'
    """
    if as_num:
        return date.weekday()
    return date.strftime('%A')
