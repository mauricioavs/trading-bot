from binbot.housekeeping import cancel_stale_orders


def test_cancel_stale_orders_noop(mock_client, cfg, fake_open_orders_recent):
    mock_client.open_orders.return_value = fake_open_orders_recent
    cancel_stale_orders(mock_client, cfg.max_order_age_hours, cfg.dry_run, log_fn=lambda *_: None)
    mock_client.cancel_order.assert_not_called()


def test_cancel_stale_orders_cancels(mock_client, cfg, fake_open_orders_old):
    mock_client.open_orders.return_value = fake_open_orders_old
    # En dry_run solo loguea; forzamos dry_run=False para verificar cancelación
    cancel_stale_orders(mock_client, cfg.max_order_age_hours, False, log_fn=lambda *_: None)
    mock_client.cancel_order.assert_called()
