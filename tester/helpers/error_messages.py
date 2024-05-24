INVALID_ORDER_TYPE = (
    "Invalid value for order type: '{order_type}'."
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

CANT_CHANGE_LEV = (
    "Cant change leverage to {new_lev},"
    " current is {current_lev} with open position"
)

NO_MONEY = (
    "Can't withdraw {withdraw} quote from wallet. "
    "Available balance is {balance}"
)

MAX_INVEST_ERROR = "Trying to open position size: {}. Can't open more than {}"

REQUIRED_PARAM = "Some required parameter is None"