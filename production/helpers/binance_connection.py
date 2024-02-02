from retrying import retry
from typing import Callable, Any
from binance.exceptions import BinanceAPIException


def retry_predict_if(exception: Exception) -> bool:
    '''
    Retry predict function if some of this codes occur

    Codes at:
    https://github.com/binance/binance-spot-api-docs/blob/master/errors.md
    '''
    if type(exception) is not BinanceAPIException:
        return False
    codes = [
        -1000,
        -1001,
        -1007,
        -1008
    ]
    print("EXCEPTION OCURRED WITH BINANCE:")
    print(repr(exception))
    print("SHOULD_RETRY:")
    print(exception.code in codes)
    # print(exception.code in codes)
    return exception.code in codes


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,
       stop_max_attempt_number=3, retry_on_exception=retry_predict_if)
def binance_run(function: Callable[..., Any], *args, **kwargs) -> Any:
    '''Run Binance API methods and handle errors'''
    result = function(*args, **kwargs)
    return result
