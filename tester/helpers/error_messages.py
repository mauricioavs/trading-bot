from orders.order_type import OrderType


INVALID_ORDER_TYPE = (
    "Invalid value '{order_type}'. "
    f"Allowed values are: {[e.value for e in OrderType]}"
)

INVALID_LEVERAGE = (
    "Invalid leverage {leverage}. "
    "Leverage must be between 1 and {max_leverage}"
)

INVALID_ATTRIBUTE_TYPE = (
    "Attribute '{attribute_name}' "
    "must be of type {expected_type}, "
    "got {current_type}"
)

INVALID_START_END_DATES = (
    "end date must be greater than start date"
)

NOT_PROVIDED_CLOSE_PRICE = (
    "One of expected_close_price or close_price must be provided"
)

NOT_PROVIDED_CANDLE = (
    "Must provide candle info to calculate close price"
)

FLUCTUATION_ERROR = (
    "Invalid value for fluctuation"
)

INSUFICCIENT_MARGIN = (
    "Insufficient Margin to buy units"
)

MIN_INVEST_ERROR = (
    "Error submitting order: Min quote invest is {min_quote}"
)
