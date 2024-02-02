from strategy1 import Strategy

st = Strategy(
    pair="BTCUSDT",
    heartbeat_url="https://push.statuscake.com/?PK=e3102a7d53e9e20&TestID=7133222&time=0",
    heartbeat_period=60,
    testnet=False,
    verbose=True
)

st.start_trading(
    interval="1h",
    initial_lev=50,
    num_candles=500,
)