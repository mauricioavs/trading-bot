from dataclasses import dataclass
from typing import Dict, List
from datetime import timedelta, datetime
import pandas as pd
import math

from .indicators import build_ohlcv, atr_percent, three_day_levels
from .sizing import compute_qty
from .filters import passes_listing_age, passes_volume
from binbot.timeutil import candles_needed, now_utc


@dataclass
class PlannedOrder:
    symbol: str
    side: str         # BUY/SELL
    type: str         # LIMIT / STOP_MARKET
    quantity: float
    price: float | None
    time_in_force: str | None
    context: str


def fetch_ohlcv(client, symbol: str, interval: str, days_lookback: int, now_utc_fn) -> pd.DataFrame:
    end = now_utc_fn()
    start = end - timedelta(days=days_lookback, hours=2)
    rows = client.klines(symbol, interval, int(start.timestamp()*1000), int(end.timestamp()*1000))
    return build_ohlcv(rows)


def decide_orders_for_symbol(*, client, symbol: str, sym_filters: dict, last_open_iso_by_symbol: Dict[str,str],
                             tdf: pd.DataFrame, equity: float, cfg) -> List[PlannedOrder]:

    # Basic filters
    last_iso = last_open_iso_by_symbol.get(symbol)
    if last_iso:
        last_dt = datetime.fromisoformat(last_iso)
        hours_since = (now_utc() - last_dt).total_seconds() / 3600.0
        if hours_since < cfg.cooldown_hours:
            if cfg.verbose:
                print(
                    f"  - SKIP cooldown: last opened {symbol} {hours_since:.1f}h ago "
                    f"(min {cfg.cooldown_hours}h required)"
                )
            return []

    if not passes_listing_age(
        symbol,
        sym_filters,
        cfg.min_listing_age_days,
        now_utc_fn=lambda: cfg.tz_local.utcoffset(None) and __import__('datetime').datetime.now(__import__('datetime').timezone.utc) or __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    ):
        if cfg.verbose:
            onboard_ms = sym_filters.get(symbol, {}).get("onboard_ms", 0)
            print(f"  - SKIP listing age: onboard={onboard_ms} (< {cfg.min_listing_age_days}d)")
        return []

    if not passes_volume(symbol, tdf, cfg.min_24h_usdt_volume):
        if cfg.verbose:
            vol = 0.0
            row = tdf.loc[tdf["symbol"] == symbol]
            if not row.empty:
                try:
                    vol = float(row.iloc[0]["quoteVolume"])
                except Exception:
                    pass
            print(f"  - SKIP volume: {vol:.0f} < {cfg.min_24h_usdt_volume}")
        return []

    # Data & volatility
    df = fetch_ohlcv(client, symbol, cfg.kline_interval, cfg.days_lookback, now_utc_fn=lambda: __import__('datetime').datetime.now(__import__('datetime').timezone.utc))
    if len(df) < 50:
        if cfg.verbose:
            print(f"  - SKIP ohlcv: len(df)={len(df)} < 50")
        return []
    atrp = atr_percent(df, period=20)

    if atrp < cfg.min_atr_pct:
        if cfg.verbose:
            print(f"  - SKIP atr: {atrp:.3f} < {cfg.min_atr_pct}")
        return []

    bars_needed = candles_needed(cfg.days_lookback, cfg.kline_interval)
    exclude_n = cfg.range_exclude_recent_bars

    if exclude_n > 0:
        if len(df) <= exclude_n:
            if cfg.verbose:
                print(f"  - SKIP band: len(df)={len(df)} <= exclude_n={exclude_n}")
            return []
        df_range = df.iloc[:-exclude_n] 
    else:
        df_range = df

    hi, lo = three_day_levels(df_range, bars_needed)
    last = float(df["close"].iloc[-1])

    if cfg.verbose:
        print(f"  - stats: ATR%={atrp:.3f} last={last:.6f} hi={hi:.6f} lo={lo:.6f}")

    if not (lo <= last <= hi):
        if cfg.verbose:
            side = "above" if last > hi else "below"
            print(f"  - SKIP band: last is {side} previous range [{lo:.6f}, {hi:.6f}]")
        return []

    def prox(p, level):
        return abs(p - level) / level * 100.0

    dist_hi = prox(last, hi)
    dist_lo = prox(last, lo)
    near_hi = dist_hi <= cfg.near_level_pct
    near_lo = dist_lo <= cfg.near_level_pct

    if not (near_hi or near_lo):
        if cfg.verbose:
            print("  - SKIP proximity: price not within near_level_pct")
        return []

    if cfg.verbose:
        print(f"  - proximity: to_hi={dist_hi:.3f}% ({'near' if near_hi else 'far'}), to_lo={dist_lo:.3f}% ({'near' if near_lo else 'far'})")

    chosen_side = None

    if near_hi and near_lo:
        chosen_side = "hi" if dist_hi <= dist_lo else "lo"
    elif near_hi:
        chosen_side = "hi"
    elif near_lo:
        chosen_side = "lo"

    step = sym_filters[symbol]["stepSize"]
    min_qty = sym_filters[symbol]["minQty"]
    tick = sym_filters[symbol]["tickSize"]

    def round_tick(x: float) -> float:
        return math.floor(x / tick) * tick

    qty = compute_qty(price=last, equity=equity, leverage=cfg.default_leverage,
                      margin_pct=cfg.margin_pct, step=step, min_qty=min_qty)
    if qty <= 0:
        return []

    out: List[PlannedOrder] = []
    if chosen_side == "hi":
        price = round_tick(hi * (1 - cfg.offset_from_level_pct/100))
        out.append(PlannedOrder(symbol, "SELL", "LIMIT", qty, price, "GTC",
                                f"short near high {hi:.4f}"))
    if chosen_side == "lo":
        price = round_tick(lo * (1 + cfg.offset_from_level_pct/100))
        out.append(PlannedOrder(symbol, "BUY", "LIMIT", qty, price, "GTC",
                                f"long near low {lo:.4f}"))
    return out
