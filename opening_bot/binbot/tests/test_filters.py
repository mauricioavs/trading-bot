from datetime import datetime, timezone
from binbot.filters import load_symbol_filters, passes_listing_age, passes_volume


def test_load_symbol_filters(fake_exchange_info):
    sf = load_symbol_filters(fake_exchange_info)
    assert "BTCUSDT" in sf and "stepSize" in sf["BTCUSDT"]


def test_passes_listing_age(fake_exchange_info):
    sf = load_symbol_filters(fake_exchange_info)
    now = lambda: datetime.now(timezone.utc)
    assert passes_listing_age("BTCUSDT", sf, 7, now)
    assert not passes_listing_age("NEWUSDT", sf, 7, now)


def test_passes_volume(fake_ticker24h):
    import pandas as pd
    tdf = pd.DataFrame(fake_ticker24h)
    assert passes_volume("BTCUSDT", tdf, 1_000_000)
    assert not passes_volume("NEWUSDT", tdf, 1_000_000)
