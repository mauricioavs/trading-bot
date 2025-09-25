from datetime import timedelta
from .timeutil import now_utc


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