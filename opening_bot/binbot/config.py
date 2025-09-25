import os
from dataclasses import dataclass
from datetime import timedelta, timezone
from binbot.timeutil import parse_hm
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # API / endpoints
    base_url: str = os.getenv("BINANCE_FAPI_BASE", "https://fapi.binance.com")
    api_key: str = os.getenv("BINANCE_API_KEY", "")
    api_secret: str = os.getenv("BINANCE_API_SECRET", "")

    # Behavior
    dry_run: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    default_leverage: int = int(os.getenv("DEFAULT_LEVERAGE", "10"))

    # Scanning
    scan_interval_sec: int = int(os.getenv("SCAN_INTERVAL_SEC", "60"))
    kline_interval: str = os.getenv("KLINE_INTERVAL", "15m")
    days_lookback: int = int(os.getenv("DAYS_LOOKBACK", "3"))

    # Risk and capacity
    margin_pct: float = float(os.getenv("MARGIN_PCT", "0.025")) # 2.5%
    max_active_slots: int = int(os.getenv("MAX_ACTIVE_SLOTS", "10"))
    min_listing_age_days: int = int(os.getenv("MIN_LISTING_AGE_DAYS", "7"))

    # Filters / signal params
    min_24h_usdt_volume: float = float(os.getenv("MIN_24H_USDT_VOLUME", "10000000"))
    min_atr_pct: float = float(os.getenv("MIN_ATR_PCT", "0.5"))
    near_level_pct: float = float(os.getenv("NEAR_LEVEL_PCT", "0.15"))
    offset_from_level_pct: float = float(os.getenv("OFFSET_FROM_LEVEL_PCT", "0.05"))
    stop_buffer_pct: float = float(os.getenv("STOP_BUFFER_PCT", "0.05"))
    max_order_age_hours: int = int(os.getenv("MAX_ORDER_AGE_HOURS", "24")) # after this hours, orders should be deleted
    order_cooldown_hours: int = int(os.getenv("COOLDOWN_HOURS", "24")) # hours to make another order of same symnol
    range_exclude_recent_bars: int = int(os.getenv("RANGE_EXCLUDE_RECENT_BARS", "0")) # exludes most recent N bars from low and high calc, in order to skip tendencies

    # Universe
    universe_size: int = int(os.getenv("UNIVERSE_SIZE", "40"))
    symbols_whitelist: tuple[str, ...] = tuple(s.strip() for s in os.getenv("SYMBOLS_WHITELIST", "").split(",") if s.strip())

    # Time window (fixed UTC-6 requested)
    tz_local: timezone = timezone(-timedelta(hours=int(os.getenv("TZ_OFFSET_HOURS", "6"))))
    window_start_hm: tuple[int, int] = parse_hm("WINDOW_START", "07:00")
    window_end_hm: tuple[int, int] = parse_hm("WINDOW_END", "18:00")

    # Requests limit control
    max_retries: int = int(os.getenv("MAX_RETRIES", "4"))
    base_backoff: float = float(os.getenv("BASE_BACKOFF", "0.5"))  # segundos
    jitter: float = float(os.getenv("BACKOFF_JITTER", "0.4"))      # segundos adicionales aleatorios
    pause_threshold_used_weight: int = int(os.getenv("PAUSE_THRESHOLD_USED_WEIGHT", "1000"))
    pause_seconds_when_near: float = float(os.getenv("PAUSE_SECONDS_WHEN_NEAR", "3.0"))
    per_symbol_delay_min: float = float(os.getenv("PER_SYMBOL_DELAY_MIN", "0.1"))
    per_symbol_delay_max: float = float(os.getenv("PER_SYMBOL_DELAY_MAX", "0.25"))

    # Files
    state_path: str = os.getenv("STATE_PATH", "state.json")

    # Verbosity / debug
    verbose: bool = os.getenv("VERBOSE", "true").lower() == "true"
    symbol_log_limit: int = int(os.getenv("SYMBOL_LOG_LIMIT", "0"))  # Log first N symbols; 0 is no limit