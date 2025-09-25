Binance Futures bot — places orders near 3‑day highs/lows


WHAT IT DOES
• Scans selected USDT‑M perpetual pairs.
• Only runs between 07:00 and 18:00 (UTC−06:00) — configurable.
• Filters symbols: listed > 7 days ago, and with sufficient volatility/volume.
• Position sizing: each order uses 2.5% of current account equity as margin (max 10 combined open orders + open positions).
• At most one position per symbol per day.
• Strategy: if price is close to the 3‑day high, place a short LIMIT a little below it; if near 3‑day low, place a long LIMIT a little above it.
• After a position opens, place a STOP‑MARKET slightly before (safer than) the current liquidation price.


IMPORTANT
• This is a reference implementation. Use DRY_RUN first. Real trading requires careful testing and monitoring.
• You are responsible for API keys, security, and compliance with Binance ToS and your local regulations.
• Timezone is fixed to UTC−06 (as requested). If you need DST behavior, adapt TZ handling accordingly.


Dependencies (Python 3.10+ recommended)
• requests, pydantic (optional but helpful), python-dotenv (optional), pandas, numpy


pip install requests pydantic python-dotenv pandas numpy


Usage
1) Create a .env file with your API keys (see ENV VARS below) and set DRY_RUN=true initially.
2) Run: python bot.py
3) Stop with Ctrl+C. The bot runs a scan loop on a fixed cadence.


ENV VARS (.env)
BINANCE_FAPI_BASE=https://fapi.binance.com
BINANCE_API_KEY=... # (for futures)
BINANCE_API_SECRET=...
# Paper test: DRY_RUN=true (default). Set to false to send real orders.
DRY_RUN=true
# Leverage to set on symbols (e.g., 10). The bot will set isolated margin + this leverage per symbol when needed.
DEFAULT_LEVERAGE=10


STATE
• state.json keeps: last position open date per symbol, and counts to enforce limits.