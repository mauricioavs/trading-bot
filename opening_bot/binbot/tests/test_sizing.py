from binbot.sizing import round_step, compute_qty


def test_round_step():
    assert round_step(1.234, 0.01) == 1.23
    assert round_step(0.009, 0.01) == 0.0


def test_compute_qty():
    qty = compute_qty(price=100.0, equity=100.0, leverage=10, margin_pct=0.025, step=0.001, min_qty=0.001)
    # margin=2.5, notional=25, qty=0.25 -> rounded
    assert abs(qty - 0.25) < 1e-9
