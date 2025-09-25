# =============================
# Test layout
# =============================
#
# tests/
#   __init__.py
#   conftest.py
#   test_timeutil.py
#   test_indicators.py
#   test_filters.py
#   test_sizing.py
#   test_housekeeping.py
#   test_risk.py
#   test_strategy.py
#   test_runner.py
# pytest.ini
#
# Run:
#   pytest -q
#   # with coverage:
#   coverage run -m pytest && coverage report -m
#
# Notes:
# • Se mockean llamadas de red, no se toca la API real.
# • Usa fixtures para datos sintéticos: klines, exchangeInfo, ticker24h, openOrders, account, positionRisk.
# • Tests se enfocan en contratos de funciones, no en valores de mercado.