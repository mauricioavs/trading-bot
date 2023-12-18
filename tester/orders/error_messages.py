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
