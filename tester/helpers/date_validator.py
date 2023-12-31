from typing import Union
from datetime import datetime
from helpers.error_messages import (
    INVALID_START_END_DATES
)


def parse_date(value: Union[str, datetime]) -> datetime:
    """
    Validates received values are either:
    - str with form year-month-day
    - datetime
    and returns a datetime.

    Note: year/month/day structure is not accepted
    because it is similar to directory structure.
    """
    if isinstance(value, datetime):
        return value
    value = datetime.strptime(
        value,
        "%Y-%m-%d"
    )
    return value


def validate_date_range(
    start: datetime,
    end: datetime
) -> None:
    """
    Validates that start < end.
    """
    if end <= start:
        raise ValueError(INVALID_START_END_DATES)
