import math


def round_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.floor(x / step) * step


def compute_qty(price: float, equity: float, leverage: int, margin_pct: float, step: float, min_qty: float) -> float:
    margin = equity * margin_pct
    notional = margin * leverage
    qty = notional / price
    qty = round_step(qty, step)
    return max(qty, min_qty)