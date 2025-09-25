from datetime import datetime, timezone, timedelta
from binbot.timeutil import (
    within_trading_window,
    candles_needed,
    interval_to_minutes,
    interval_to_timedelta,
)
import pytest


def test_within_trading_window():
    tz = timezone(-timedelta(hours=6))
    # Fecha a las 8am local UTC-6
    dt_utc = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
    assert within_trading_window(dt_utc, tz, (7, 0), (18, 0))
    # Fuera (6am local)
    dt_utc2 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert not within_trading_window(dt_utc2, tz, (7, 0), (18, 0))


# ---------------------------
# Tests de interval_to_minutes
# ---------------------------

@pytest.mark.parametrize(
    "interval, minutes",
    [
        ("1m", 1),
        ("5m", 5),
        ("15m", 15),
        ("1h", 60),
        ("4h", 240),
        ("12h", 720),
        ("1d", 1440),
        ("3d", 4320),
        ("1w", 10080),
        ("2w", 20160),
        ("1M", 43200),   # 30 días * 24h * 60m
        ("2M", 86400),
    ],
)
def test_interval_to_minutes_ok(interval, minutes):
    assert interval_to_minutes(interval) == minutes


@pytest.mark.parametrize("bad", ["", "h1", "60x", "1y", "foo", "m15", "0h"])
def test_interval_to_minutes_bad_inputs(bad):
    with pytest.raises(ValueError):
        interval_to_minutes(bad)


def test_interval_to_timedelta_matches_minutes():
    td = interval_to_timedelta("15m")
    assert td.total_seconds() == 15 * 60


# ---------------------------
# Tests de candles_needed
# ---------------------------

@pytest.mark.parametrize(
    "days_lookback, interval, buffer, expected",
    [
        # Ejemplos mencionados:
        (3,  "1h", 5, 77),    # 3*24 = 72 + 5
        (2,  "15m", 5, 197),  # 2 días = 2880 min / 15 = 192 + 5
        (10, "4h", 5, 65),    # 10 días = 240h / 4h = 60 + 5
        (21, "1d", 5, 26),    # 21 + 5
        (60, "1w", 5, 14),    # ceil(60/7)=9 + 5 = 14
        (90, "1M", 5, 8),     # 90/30=3 + 5 = 8
    ],
)
def test_candles_needed_examples(days_lookback, interval, buffer, expected):
    assert candles_needed(days_lookback, interval, buffer) == expected


@pytest.mark.parametrize(
    "days_lookback, interval",
    [
        (0, "1m"),
        (0, "1h"),
        (0, "1d"),
    ],
)
def test_candles_needed_zero_days_uses_buffer(days_lookback, interval):
    # Con days=0, el cálculo bruto da 0; el resultado debe ser al menos el buffer (>=1).
    res = candles_needed(days_lookback, interval, buffer=5)
    assert res == 5


def test_candles_needed_min_is_one_if_buffer_zero():
    # Si days=0 e incluso buffer=0, aseguramos mínimo 1 por max(1, ...)
    assert candles_needed(0, "1h", buffer=0) == 1


def test_candles_needed_buffer_increases_linearly():
    base = candles_needed(3, "1h", buffer=0)   # 3*24=72
    plus5 = candles_needed(3, "1h", buffer=5)  # 72+5
    plus10 = candles_needed(3, "1h", buffer=10)  # 72+10
    assert plus5 - base == 5
    assert plus10 - base == 10


@pytest.mark.parametrize("bad_interval", ["", "foo", "1y", "60x"])
def test_candles_needed_invalid_interval_raises(bad_interval):
    with pytest.raises(ValueError):
        candles_needed(3, bad_interval, buffer=5)
