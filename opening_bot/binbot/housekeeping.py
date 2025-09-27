from datetime import timedelta, datetime
from time import time as _now
from .timeutil import now_utc
from binbot.client import BinanceFutures
from binbot.config import Config
from binbot.state import BotState
import pandas as pd
import math


def cancel_stale_orders(client, max_age_hours: int, dry_run: bool, log_fn=print):
    try:
        orders = client.open_orders()
        cutoff_ms = int((now_utc() - timedelta(hours=max_age_hours)).timestamp() * 1000)
        for od in orders:
            created = int(od.get("time", od.get("updateTime", 0)))
            if created and created < cutoff_ms:
                # ---- filtro: no tocar SL/TP ----
                if od.get("type") in ("STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"):
                    continue
                if od.get("reduceOnly") is True:
                    continue
                # -------------------------------
                symbol = od.get("symbol")
                oid = od.get("orderId")
                if dry_run:
                    log_fn(f"DRYRUN cancel stale {symbol} #{oid} (age >= {max_age_hours}h)")
                else:
                    client.cancel_order(symbol, oid)
                    log_fn(f"Canceled stale {symbol} #{oid}")
    except Exception as e:
        log_fn(f"Stale-cancel sweep error: {e}")


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
        universe = list(cfg.symbols_whitelist)
    else:
        tickers = client.ticker_24h()
        tdf = pd.DataFrame(tickers)
        tdf = tdf[tdf["symbol"].str.endswith("USDT")]
        tdf["quoteVolume"] = pd.to_numeric(tdf["quoteVolume"], errors="coerce")
        tdf = tdf.sort_values("quoteVolume", ascending=False).head(cfg.universe_size)
        universe = tdf["symbol"].tolist()

    if cfg.symbols_blacklist:
        universe = [s for s in universe if s not in cfg.symbols_blacklist]

    return universe


def has_protective_stop_for_symbol(open_orders: list, symbol: str) -> bool:
    # Busca STOP_MARKET/TP_MARKET con closePosition=true para ese símbolo
    for od in open_orders:
        if od.get("symbol") != symbol:
            continue
        t = od.get("type", "")
        if t in ("STOP_MARKET", "TAKE_PROFIT_MARKET"):
            cp = str(od.get("closePosition", "false")).lower() == "true"
            if cp:
                return True
    return False


def floor_to_tick(x: float, tick: float) -> float:
    return math.floor(x / tick) * tick


def ceil_to_tick(x: float, tick: float) -> float:
    return math.ceil(x / tick) * tick


def plan_stop_near_liq(side_entry: str, liq_price: float, tick: float, buffer_pct: float, min_gap_ticks: int = 1):
    """
    Calcula side de cierre y precio stop con:
      - buffer en % respecto al liq
      - al menos 'min_gap_ticks' de distancia al liq en la dirección correcta
      - redondeo correcto (ceil si arriba, floor si abajo)
    """
    buf = buffer_pct / 100.0
    if side_entry.upper() == "BUY":
        # LONG: stop por encima del liq
        target = liq_price * (1 + buf)
        stop_price = ceil_to_tick(target, tick)
        min_allowed = liq_price + min_gap_ticks * tick
        if stop_price < min_allowed:
            stop_price = ceil_to_tick(min_allowed, tick)
        side_close = "SELL"
    else:
        # SHORT: stop por debajo del liq
        target = liq_price * (1 - buf)
        stop_price = floor_to_tick(target, tick)
        max_allowed = liq_price - min_gap_ticks * tick
        if stop_price > max_allowed:
            stop_price = floor_to_tick(max_allowed, tick)
        side_close = "BUY"

    return side_close, stop_price


def ensure_protective_stops(cfg: Config, client: BinanceFutures, state: BotState, sym_filters, log_fn=print):
    """Una sola llamada a positionRisk y una a openOrders para cubrir todas las posiciones."""
    try:
        if cfg.verbose:
            now_local = datetime.now(cfg.tz_local).strftime("%Y-%m-%d %H:%M:%S %Z")
            log_fn(f"[{now_local}] --- ensure_protective_stops ---")

        risks = client.position_risk()          # todas las posiciones
        all_open_orders = client.open_orders()  # todas las órdenes abiertas

        seen = 0
        with_pos = 0
        no_liq = 0
        already = 0
        cooldown = 0
        placed = 0
        skipped_missing_tick = 0

        for r in risks:
            seen += 1
            symbol = r.get("symbol")
            try:
                amt = float(r.get("positionAmt", "0") or 0.0)
                liq = float(r.get("liquidationPrice", "0") or 0.0)
            except (ValueError, TypeError) as e:
                if cfg.verbose:
                    log_fn(f"[stops] {symbol}: SKIP (bad numeric parse: {e})")
                continue
            if amt == 0.0:
                # this is commented bcs it prints all the symbols with no positions
                # if cfg.verbose:
                #     log_fn(f"[stops] {symbol}: SKIP (no position)")
                continue

            with_pos += 1

            if liq <= 0.0:
                no_liq += 1
                if cfg.verbose:
                    log_fn(f"[stops] {symbol}: SKIP (no liquidationPrice yet)")
                continue

            if has_protective_stop_for_symbol(all_open_orders, symbol):
                already += 1
                if cfg.verbose:
                    log_fn(f"[stops] {symbol}: SKIP (protective stop already present)")
                continue

            last_attempt = state.last_stop_attempt_ts_by_symbol.get(symbol, 0.0)
            if _now() - last_attempt < cfg.stops_retry_cooldown_sec:
                cooldown += 1
                if cfg.verbose:
                    wait_s = int(cfg.stops_retry_cooldown_sec - (_now() - last_attempt))
                    log_fn(f"[stops] {symbol}: SKIP (cooldown ~{wait_s}s)")
                continue

            # tickSize disponible?
            filt = sym_filters.get(symbol)
            if not filt or "tickSize" not in filt:
                skipped_missing_tick += 1
                if cfg.verbose:
                    log_fn(f"[stops] {symbol}: SKIP (no tickSize in filters)")
                continue

            tick = filt["tickSize"]
            side_entry = "BUY" if amt > 0 else "SELL"
            side_close, stop_price = plan_stop_near_liq(
                side_entry=side_entry,
                liq_price=liq,
                tick=tick,
                buffer_pct=cfg.stop_near_liq_buffer_pct,
                min_gap_ticks=1  # mínimo 1 tick de separación
            )

            if cfg.dry_run:
                log_fn(
                    f"DRYRUN STOP {symbol}: closePosition {side_close} @ {stop_price} "
                    f"(liq={liq}, buf={cfg.stop_near_liq_buffer_pct:.2f}%, tick={tick}, working={cfg.stop_working_type})"
                )
            else:
                client.place_order(
                    symbol=symbol,
                    side=side_close,
                    type_="STOP_MARKET",
                    quantity="0",
                    stop_price=f"{stop_price:.8f}",
                    close_position=True,
                    working_type=cfg.stop_working_type,
                    sym_filters=sym_filters
                )
                log_fn(
                    f"STOP set near liq: {symbol} @ {stop_price} "
                    f"(liq={liq}, buf={cfg.stop_near_liq_buffer_pct:.2f}%, tick={tick})"
                )
            placed += 1
            state.last_stop_attempt_ts_by_symbol[symbol] = _now()

        state.save(cfg.state_path)

        # Resumen final
        log_fn(
            f"[stops] seen={seen} with_pos={with_pos} placed={placed} "
            f"already={already} no_liq={no_liq} cooldown={cooldown} missing_tick={skipped_missing_tick}"
        )

    except Exception as e:
        log_fn(f"[stops] ERROR: {e}")
