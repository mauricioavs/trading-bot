from datetime import datetime, timezone
import pandas as pd


def load_symbol_filters(exchange_info: dict) -> dict:
    out = {}
    for sym in exchange_info.get("symbols", []):
        if sym.get("contractType") == "PERPETUAL" and sym.get("status") == "TRADING":
            symbol = sym["symbol"]
            onboard_ms = sym.get("onboardDate")
            filters = {f["filterType"]: f for f in sym.get("filters", [])}
            lot = filters.get("LOT_SIZE", {})
            price = filters.get("PRICE_FILTER", {})
            out[symbol] = {
                "onboard_ms": onboard_ms,
                "stepSize": float(lot.get("stepSize", "0.001")),
                "minQty": float(lot.get("minQty", "0.0")),
                "tickSize": float(price.get("tickSize", "0.01")),
            }
    return out


def passes_listing_age(symbol: str, sym_filters: dict, min_days: int, now_utc_fn) -> bool:
    onboard_ms = sym_filters.get(symbol, {}).get("onboard_ms")
    if not onboard_ms:
        return False
    listed = datetime.fromtimestamp(onboard_ms/1000, tz=timezone.utc)
    return (now_utc_fn() - listed).days >= min_days


def passes_volume(symbol: str, tdf: pd.DataFrame, min_quote_volume: float) -> bool:
    row = tdf.loc[tdf["symbol"] == symbol]
    if row.empty:
        return False
    try:
        vol = float(row.iloc[0]["quoteVolume"])
    except Exception:
        return False
    return vol >= min_quote_volume
