import pandas as pd


def build_ohlcv(kline_rows):
    cols = ["open_time","open","high","low","close","volume","close_time",
            "quote_asset_volume","number_of_trades","taker_buy_base","taker_buy_quote","ignore"]
    df = pd.DataFrame(kline_rows, columns=cols)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df[["open_time","open","high","low","close","volume","close_time"]]


def atr_percent(df: pd.DataFrame, period: int = 20) -> float:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    trs = []
    prev_close = closes[0]
    for h, l, c in zip(highs, lows, closes):
        tr = max(h-l, abs(h-prev_close), abs(l-prev_close))
        trs.append(tr)
        prev_close = c
    atr = float(pd.Series(trs).tail(period).mean())
    last_close = float(closes[-1])
    return (atr / last_close) * 100.0


def three_day_levels(df: pd.DataFrame, bars_needed: int) -> tuple[float, float]:
    hi = float(df["high"].tail(bars_needed).max())
    lo = float(df["low"].tail(bars_needed).min())
    return hi, lo