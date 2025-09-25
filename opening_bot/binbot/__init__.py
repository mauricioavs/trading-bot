# =============================
# Project layout
# =============================
#
# binbot/
# __init__.py
# config.py
# timeutil.py
# client.py
# state.py
# indicators.py
# filters.py
# sizing.py
# strategy.py
# risk.py
# housekeeping.py
# runner.py
# main.py
# requirements.txt
# .env.example
#
# Notes on design:
# • Clear separation of concerns (SRP): market client, config, indicators, sizing, risk, housekeeping, strategy, runner.
# • Dependency Injection: pass the Binance client and config into functions — easy to mock for tests.
# • Ports & Adapters: the strategy/risk/housekeeping depend on an abstract "client" interface (we use BinanceFutures adapter).
# • Stateless functions where possible; minimal shared state in state.py.
# • Testability: each module can be unit-tested in isolation.


# -----------------------------
# file: binbot/__init__.py
# -----------------------------
from .config import Config
from .client import BinanceFutures
from .runner import run_loop_once, run_loop


__all__ = [
"Config",
"BinanceFutures",
"run_loop_once",
"run_loop",
]