import math
import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from binbot.config import Config
from binbot.client import BinanceFutures

UTC = timezone.utc


@pytest.fixture
def cfg():
    # Config mínima para tests (sin .env)
    return Config(
        base_url="https://fapi.binance.com",
        api_key="k", api_secret="s",
        dry_run=True,
        default_leverage=10,
        scan_interval_sec=1,
        kline_interval="15m",
        days_lookback=3,
        margin_pct=0.025,
        max_active_slots=10,
        min_listing_age_days=7,
        min_24h_usdt_volume=1_000_000,
        min_atr_pct=0.1,
        near_level_pct=0.2,
        offset_from_level_pct=0.05,
        max_order_age_hours=24,
        universe_size=5,
        symbols_whitelist=tuple(),
    )


@pytest.fixture
def fake_kline_rows():
    # 3 días de velas 15m ~ 288*3 = 864; fabricamos menos pero suficiente
    rows = []
    start = datetime(2024,1,1,tzinfo=UTC)
    price = 100.0
    for i in range(200):
        t = int((start + timedelta(minutes=15*i)).timestamp()*1000)
        o = price
        h = o * 1.01
        l = o * 0.99
        c = o * (1 + (0.001 if i%2==0 else -0.001))
        v = 10+i
        rows.append([t,o,h,l,c,v,t+14*60*1000,0,0,0,0,"0"])
        price = c
    return rows


@pytest.fixture
def fake_exchange_info():
    return {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "contractType": "PERPETUAL",
                "onboardDate": int((datetime.now(UTC)-timedelta(days=30)).timestamp()*1000),
                "filters": [
                    {"filterType":"LOT_SIZE","stepSize":"0.001","minQty":"0.001"},
                    {"filterType":"PRICE_FILTER","tickSize":"0.1"}
                ]
            },
            {
                "symbol": "NEWUSDT",
                "status": "TRADING",
                "contractType": "PERPETUAL",
                "onboardDate": int((datetime.now(UTC)-timedelta(days=3)).timestamp()*1000),
                "filters": [
                    {"filterType":"LOT_SIZE","stepSize":"1","minQty":"1"},
                    {"filterType":"PRICE_FILTER","tickSize":"0.01"}
                ]
            }
        ]
    }


@pytest.fixture
def fake_ticker24h():
    return [
        {"symbol":"BTCUSDT","contractType":"PERPETUAL","quoteVolume":"50000000"},
        {"symbol":"ETHUSDT","contractType":"PERPETUAL","quoteVolume":"40000000"},
        {"symbol":"NEWUSDT","contractType":"PERPETUAL","quoteVolume":"5000"},
    ]


@pytest.fixture
def fake_open_orders_recent():
    now_ms = int(datetime.now(UTC).timestamp()*1000)
    return [
        {"symbol":"BTCUSDT","orderId":1,"time":now_ms-3600*1000}, # 1h
    ]


@pytest.fixture
def fake_open_orders_old():
    now_ms = int(datetime.now(UTC).timestamp()*1000)
    return [
        {"symbol":"BTCUSDT","orderId":2,"time":now_ms-25*3600*1000}, # 25h
    ]


@pytest.fixture
def fake_account():
    return {"totalWalletBalance":"100.0"}


@pytest.fixture
def fake_position_risk_long():
    return [{"symbol":"BTCUSDT","positionAmt":"0.01","liquidationPrice":"80.0"}]


@pytest.fixture
def fake_position_risk_short():
    return [{"symbol":"BTCUSDT","positionAmt":"-0.01","liquidationPrice":"120.0"}]


@pytest.fixture
def mock_client(cfg, fake_exchange_info, fake_ticker24h, fake_account, fake_open_orders_recent):
    c = BinanceFutures(cfg)
    # stub methods
    c.exchange_info = MagicMock(return_value=fake_exchange_info)
    c.ticker_24h = MagicMock(return_value=fake_ticker24h)
    c.account = MagicMock(return_value=fake_account)
    c.open_orders = MagicMock(return_value=fake_open_orders_recent)
    c.position_risk = MagicMock(return_value=[])
    c.klines = MagicMock()
    c.place_order = MagicMock()
    c.cancel_order = MagicMock()
    c.set_isolated_and_leverage = MagicMock()
    return c
