import pandas as pd
from unittest.mock import MagicMock
from binbot.runner import run_loop_once
from binbot.state import BotState


def test_run_loop_once_smoke(cfg, mock_client, fake_exchange_info, fake_ticker24h):
    state = BotState()
    # Ajustar mocks para universo reducido
    mock_client.exchange_info.return_value = fake_exchange_info
    mock_client.ticker_24h.return_value = fake_ticker24h

    def logger(*args, **kwargs):
        pass

    run_loop_once(cfg, mock_client, state, log_fn=logger)
    # Si llegó aquí sin excepciones, pasa el smoke test
    assert True