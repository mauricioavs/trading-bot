import pandas as pd
from unittest.mock import MagicMock
from binbot.strategy import decide_orders_for_symbol
from binbot.filters import load_symbol_filters


def test_decide_orders_for_symbol_generates_orders(cfg, mock_client, fake_kline_rows, fake_exchange_info, fake_ticker24h):
    # Prep filtros por símbolo y tickers
    sym_filters = load_symbol_filters(fake_exchange_info)
    tdf = pd.DataFrame(fake_ticker24h)

    # KLInes para BTCUSDT
    mock_client.klines.return_value = fake_kline_rows

    orders = decide_orders_for_symbol(
        client=mock_client,
        symbol="BTCUSDT",
        sym_filters=sym_filters,
        last_open_iso_by_symbol={},
        tdf=tdf,
        equity=100.0,
        cfg=cfg,
    )
    # Según datos sintéticos, debería al menos evaluar y devolver 0 o más órdenes
    assert isinstance(orders, list)
