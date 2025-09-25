from __future__ import annotations
from datetime import datetime, timezone, timedelta
import math
import re
import os


def parse_hm(env_name: str, default: str) -> tuple[int, int]:
    val = os.getenv(env_name, default)
    try:
        h, m = val.split(":")
        return int(h), int(m)
    except Exception as e:
        raise ValueError(f"Formato inválido para {env_name}: {val}") from e

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def within_trading_window(dt_utc: datetime, tz_local, start_hm: tuple[int, int], end_hm: tuple[int, int]) -> bool:
    local = dt_utc.astimezone(tz_local)
    start = local.replace(
        hour=start_hm[0], minute=start_hm[1], second=0, microsecond=0
    )
    end = local.replace(
        hour=end_hm[0], minute=end_hm[1], second=0, microsecond=0
    )
    return start <= local <= end


# Conversión de intervalos Binance a duración
# Soporta: Xm, Xh, Xd, Xw, XM (mes ~30 días aprox.)
_INTERVAL_RE = re.compile(r"^(?P<n>\d+)(?P<u>[mhdwM])$")

_UNIT_TO_MINUTES = {
    "m": 1,            # minutos
    "h": 60,           # horas
    "d": 60 * 24,      # días
    "w": 60 * 24 * 7,  # semanas
    # "M" lo tratamos especial (mes aproximado)
}

def interval_to_minutes(interval: str) -> int:
    """
    Convierte un intervalo Binance (e.g., '15m', '1h', '4h', '1d', '3d', '1w', '1M')
    a su duración en minutos. Para 'M' (mes) se aproxima a 30 días.
    """
    m = _INTERVAL_RE.match(interval)
    if not m:
        raise ValueError(f"Intervalo inválido: {interval}")

    n = int(m.group("n"))
    u = m.group("u")

    if n <= 0:
        raise ValueError(f"El intervalo no puede ser 0: {interval}")

    if u == "M":
        # Aproximación estándar: 30 días por mes
        return n * 30 * 24 * 60

    base = _UNIT_TO_MINUTES.get(u)
    if base is None:
        raise ValueError(f"Unidad desconocida en intervalo: {interval}")

    return n * base

def interval_to_timedelta(interval: str) -> timedelta:
    """Devuelve un timedelta aproximado para el intervalo Binance dado."""
    minutes = interval_to_minutes(interval)
    return timedelta(minutes=minutes)

def candles_needed(days_lookback: int, interval: str, buffer: int = 5) -> int:
    """
    Calcula cuántas velas necesitas para cubrir 'days_lookback' días,
    dado un 'interval' de Binance (e.g., '1h', '15m', '1d', '1w', '1M').

    - Para unidades < 1 día, es días*24h / intervalo.
    - Para unidades >= 1 día, se hace un cálculo general: ceil((days*24h) / minutes_per_candle).
    - '1M' (mes) se aproxima a 30 días.
    - 'buffer' añade unas velas extra para bordes/alineación.

    Retorna un int >= 1.
    """
    minutes_per_candle = interval_to_minutes(interval)
    total_minutes = days_lookback * 24 * 60
    n = max(1, math.ceil(total_minutes / minutes_per_candle) + buffer)
    return n
