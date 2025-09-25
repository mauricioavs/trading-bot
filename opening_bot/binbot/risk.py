from __future__ import annotations


def place_protective_stop(client, symbol: str, side: str, buffer_pct: float):
    risks = client.position_risk()
    r = next((x for x in risks if x.get("symbol") == symbol), None)
    if not r:
        return
    amt = abs(float(r.get("positionAmt", "0")))
    liq = float(r.get("liquidationPrice", "0"))
    if amt <= 0 or liq <= 0:
        return
    if side.upper() == "LONG":
        stop_price = liq * (1 + buffer_pct/100)
        stop_side = "SELL"
    else:
        stop_price = liq * (1 - buffer_pct/100)
        stop_side = "BUY"
    client.place_order(
        symbol,
        stop_side,
        "STOP_MARKET",
        f"{amt}", stop_price=f"{stop_price:.8f}",
        reduce_only="true"
    )
