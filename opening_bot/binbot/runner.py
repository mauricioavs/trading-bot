import time
import pandas as pd
import traceback
from .config import Config
from .client import BinanceFutures
from .state import BotState
from .filters import load_symbol_filters
from .strategy import decide_orders_for_symbol
from .timeutil import now_utc, within_trading_window
from .housekeeping import (
    cancel_stale_orders,
    get_equity_usdt,
    symbol_universe,
    get_active_counts,
    ensure_protective_stops
)
import random
from datetime import datetime


def run_loop_once(cfg: Config, client: BinanceFutures, state: BotState, log_fn=print):
    # housekeeping: cancel orders older than 24h
    if cfg.verbose:
        start_ts = time.time()
        now_local = datetime.now(cfg.tz_local).strftime("%Y-%m-%d %H:%M:%S %Z%z")
        log_fn(f"[{now_local}] --- run_loop_once ---")

    cancel_stale_orders(client, cfg.max_order_age_hours, cfg.dry_run, log_fn)

    if not within_trading_window(now_utc(), cfg.tz_local, cfg.window_start_hm, cfg.window_end_hm):
        if cfg.verbose:
            log_fn("Outside trading window; skip.")
        return

    sym_filters = load_symbol_filters(client.exchange_info())
    tickers = client.ticker_24h()
    tdf = pd.DataFrame(tickers)
    tdf["quoteVolume"] = pd.to_numeric(tdf["quoteVolume"], errors="coerce")

    open_orders, open_positions, total_active = get_active_counts(client)
    if total_active >= cfg.max_active_slots:
        if cfg.verbose:
            log_fn(f"Capacity reached ({total_active}/{cfg.max_active_slots}); skip.")
        return

    equity = get_equity_usdt(client)
    if cfg.verbose:
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
                                             time_in_force=od.time_in_force, sym_filters=sym_filters)
                    log_fn(f"ORDER OK: {res}")
                    from .timeutil import now_utc as _now
                    state.last_open_iso_by_symbol[symbol] = _now().isoformat()
                    state.save(cfg.state_path)
        except Exception as e:
            log_fn(f"Error {symbol}: {e}")

        time.sleep(random.uniform(cfg.per_symbol_delay_min, cfg.per_symbol_delay_max))

    if cfg.verbose:
        end_local = datetime.now(cfg.tz_local).strftime("%Y-%m-%d %H:%M:%S %Z%z")
        elapsed = time.time() - start_ts
        log_fn(f"[{end_local}] --- run_loop_once END --- (took {elapsed:.2f}s)")


def run_loop(cfg: Config):
    client = BinanceFutures(cfg)
    state = BotState.load(cfg.state_path)

    last_scan_ts = 0.0
    # fuerza que la primera vez siempre ejecute stops también
    state.last_stops_check_ts = 0.0
    state.save(cfg.state_path)

    print("Starting run_loop… (Ctrl+C para detener)")
    try:
        while True:
            # 1) ¿toca scan de señales?
            if time.time() - last_scan_ts >= cfg.scan_interval_sec:
                try:
                    run_loop_once(cfg, client, state, log_fn=print)
                except Exception as e:
                    print(f"[scan] ERROR: {e}")
                    traceback.print_exc()
                finally:
                    last_scan_ts = time.time()

            # 2) ¿toca revisar/colocar stops protectores?
            if time.time() - state.last_stops_check_ts >= cfg.stops_check_interval_sec:
                try:
                    # prepara filtros/ticks una sola vez si no los tienes a mano
                    sym_filters = load_symbol_filters(client.exchange_info())
                    ensure_protective_stops(cfg, client, state, sym_filters, log_fn=print)
                except Exception as e:
                    print(f"[stops] ERROR: {e}")
                    traceback.print_exc()
                finally:
                    state.last_stops_check_ts = time.time()
                    state.save(cfg.state_path)

            # duerme el mínimo necesario para mantener responsivo el scheduler
            next_scan_due = (last_scan_ts + cfg.scan_interval_sec) - time.time()
            next_stops_due = (state.last_stops_check_ts + cfg.stops_check_interval_sec) - time.time()
            sleep_s = max(0.3, min(next_scan_due, next_stops_due, 1.0))  # duerme cortito (≤1s)
            time.sleep(sleep_s + random.uniform(0, 0.2))
    except KeyboardInterrupt:
        print("Shutting down…")
