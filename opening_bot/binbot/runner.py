import time
import pandas as pd

from .config import Config
from .client import BinanceFutures
from .state import BotState
from .filters import load_symbol_filters, passes_listing_age, passes_volume
from .strategy import decide_orders_for_symbol
from .timeutil import now_utc, within_trading_window
from .housekeeping import cancel_stale_orders
import random


def get_active_counts(client: BinanceFutures) -> tuple[int, int, int]:
    orders = client.open_orders()
    filtered_orders = [
        o for o in orders
        if o.get("type") not in {
            "STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET", "TRAILING_STOP_MARKET"
        }
    ]
    positions = client.position_risk()
    open_pos = [p for p in positions if float(p.get("positionAmt", "0")) != 0.0]

    return len(filtered_orders), len(open_pos), len(filtered_orders) + len(open_pos)


def get_equity_usdt(client: BinanceFutures) -> float:
    acct = client.account()
    return float(acct.get("totalWalletBalance", "0"))


def symbol_universe(client: BinanceFutures, cfg: Config) -> list[str]:
    if cfg.symbols_whitelist:
        return list(cfg.symbols_whitelist)
    tickers = client.ticker_24h()
    tdf = pd.DataFrame(tickers)
    tdf = tdf[(tdf["symbol"].str.endswith("USDT"))]
    tdf["quoteVolume"] = pd.to_numeric(tdf["quoteVolume"], errors="coerce")
    tdf = tdf.sort_values("quoteVolume", ascending=False).head(cfg.universe_size)
    return tdf["symbol"].tolist()


def run_loop_once(cfg: Config, client: BinanceFutures, state: BotState, log_fn=print):
    # housekeeping: cancel orders older than 24h
    cancel_stale_orders(client, cfg.max_order_age_hours, cfg.dry_run, log_fn)

    if not within_trading_window(now_utc(), cfg.tz_local, cfg.window_start_hm, cfg.window_end_hm):
        log_fn("Outside trading window; skip.")
        return

    sym_filters = load_symbol_filters(client.exchange_info())
    tickers = client.ticker_24h()
    tdf = pd.DataFrame(tickers)
    tdf["quoteVolume"] = pd.to_numeric(tdf["quoteVolume"], errors="coerce")

    open_orders, open_positions, total_active = get_active_counts(client)
    if total_active >= cfg.max_active_slots:
        log_fn(f"Capacity reached ({total_active}/{cfg.max_active_slots}); skip.")
        return

    equity = get_equity_usdt(client)
    log_fn(f"Equity: {equity:.2f} | Active: orders={open_orders} positions={open_positions}")

    universe = symbol_universe(client, cfg)

    if cfg.verbose:
        log_fn(f"Universe ({len(universe)}): {', '.join(universe[:min(len(universe), 30)])}" + (" ..." if len(universe) > 30 else ""))

    for idx, symbol in enumerate(universe, start=1):
        open_orders, open_positions, total_active = get_active_counts(client)
        if total_active >= cfg.max_active_slots:
            if cfg.verbose:
                log_fn(f"[{idx}/{len(universe)}] {symbol} → stop (capacity {total_active}/{cfg.max_active_slots})")
            break

        if cfg.verbose:
            log_fn(f"[{idx}/{len(universe)}] {symbol} → evaluating")

        try:
            planned = decide_orders_for_symbol(client=client, symbol=symbol, sym_filters=sym_filters,
                                               last_open_iso_by_symbol=state.last_open_iso_by_symbol,
                                               tdf=tdf, equity=equity, cfg=cfg)
            for od in planned:
                msg = f"{symbol} | {od.context} | qty={od.quantity} @ {od.price or 'MKT'}"
                if cfg.dry_run:
                    log_fn("DRYRUN place: " + msg)
                else:
                    client.set_isolated_and_leverage(symbol, cfg.default_leverage)
                    res = client.place_order(symbol, od.side, od.type, f"{od.quantity}",
                                             price=(f"{od.price:.8f}" if od.price else None),
                                             time_in_force=od.time_in_force)
                    log_fn(f"ORDER OK: {res}")
                    from .timeutil import now_utc as _now
                    state.last_open_iso_by_symbol[symbol] = _now().isoformat()
                    state.save(cfg.state_path)
        except Exception as e:
            log_fn(f"Error {symbol}: {e}")

        time.sleep(random.uniform(cfg.per_symbol_delay_min, cfg.per_symbol_delay_max))


def run_loop(cfg: Config):
    client = BinanceFutures(cfg)
    state = BotState.load(cfg.state_path)
    try:
        while True:
            run_loop_once(cfg, client, state, print)
            time.sleep(cfg.scan_interval_sec)
    except KeyboardInterrupt:
        print("Shutting down…")