from binbot.indicators import build_ohlcv, atr_percent, three_day_levels


def test_build_ohlcv(fake_kline_rows):
    df = build_ohlcv(fake_kline_rows)
    assert {"open", "high", "low", "close", "volume"}.issubset(df.columns)
    assert len(df) == len(fake_kline_rows)


def test_atr_percent(fake_kline_rows):
    df = build_ohlcv(fake_kline_rows)
    val = atr_percent(df, period=14)
    assert val > 0


def test_three_day_levels(fake_kline_rows):
    df = build_ohlcv(fake_kline_rows)
    hi, lo = three_day_levels(df, bars_needed=100)
    assert hi >= lo