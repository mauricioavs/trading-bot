from binbot.risk import place_protective_stop


def test_place_protective_stop_long(mock_client, cfg, fake_position_risk_long):
    mock_client.position_risk.return_value = fake_position_risk_long
    place_protective_stop(mock_client, "BTCUSDT", "LONG", cfg.stop_buffer_pct)
    # Debe mandar STOP_MARKET SELL para long
    args, _ = mock_client.place_order.call_args
    assert args[0] == "BTCUSDT"
    assert args[1] == "SELL"
    assert args[2] == "STOP_MARKET"


def test_place_protective_stop_short(mock_client, cfg, fake_position_risk_short):
    mock_client.position_risk.return_value = fake_position_risk_short
    place_protective_stop(mock_client, "BTCUSDT", "SHORT", cfg.stop_buffer_pct)
    args, _ = mock_client.place_order.call_args
    assert args[1] == "BUY"
    assert args[2] == "STOP_MARKET"