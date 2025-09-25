import hmac
import time
import hashlib
from typing import Dict, Optional
import requests
from binbot.config import Config


class BinanceFutures:
    """Minimal adapter for Binance USDT-M Futures REST."""
    def __init__(self, cfg: Config):
        self.base = cfg.base_url.rstrip('/')
        self.key = cfg.api_key
        self.secret = cfg.api_secret.encode()
        self.session = requests.Session()
        if self.key:
            self.session.headers.update({"X-MBX-APIKEY": self.key})

        # rate limit configuration
        self.max_retries = getattr(cfg, "max_retries")
        self.base_backoff = getattr(cfg, "base_backoff")
        self.jitter = getattr(cfg, "jitter")
        self.pause_threshold_used_weight = getattr(cfg, "pause_threshold_used_weight")
        self.pause_seconds_when_near = getattr(cfg, "pause_seconds_when_near")

    # signing helpers
    def _sign(self, params: Dict[str, str]) -> Dict[str, str]:
        qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
        sig = hmac.new(self.secret, qs.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    def _request(self, method: str, path: str, *,
                 params: Dict[str, str] | None = None,
                 signed: bool = False):
        url = f"{self.base}{path}"
        params = params or {}
        if signed:
            params.update({"timestamp": int(time.time() * 1000)})
            params = self._sign(params)

        last_err = None
        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    r = self.session.get(url, params=params, timeout=10)
                elif method == "POST":
                    r = self.session.post(url, data=params, timeout=10)
                elif method == "DELETE":
                    r = self.session.delete(url, data=params, timeout=10)
                else:
                    raise RuntimeError(f"Unsupported method {method}")

                # Si nos acercamos al límite, pausa breve
                used = int(r.headers.get("X-MBX-USED-WEIGHT-1M", "0") or 0)
                if used >= self.pause_threshold_used_weight:
                    time.sleep(self.pause_seconds_when_near)

                r.raise_for_status()
                return r.json()

            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                # 429 => Too Many Requests, 418 => IP Banned temporal (cuida esto)
                if status in (429, 418):
                    backoff = self.base_backoff * (2 ** attempt) + random.uniform(0, 0.3)
                    time.sleep(backoff)
                    last_err = e
                    continue
                raise
            except requests.RequestException as e:
                # problemas de red: backoff y reintento
                backoff = self.base_backoff * (2 ** attempt) + random.uniform(0, 0.3)
                time.sleep(backoff)
                last_err = e
                continue

        # si llegamos aquí, agotamos reintentos
        if last_err:
            raise last_err

    def _get(self, path: str, params: Dict[str, str] | None = None, signed: bool = False):
        return self._request("GET", path, params=params, signed=signed)

    def _post(self, path: str, params: Dict[str, str], signed: bool = True):
        return self._request("POST", path, params=params, signed=signed)

    def _delete(self, path: str, params: Dict[str, str], signed: bool = True):
        return self._request("DELETE", path, params=params, signed=signed)

    # public
    # https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information
    def exchange_info(self):
        return self._get("/fapi/v1/exchangeInfo")

    # https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/24hr-Ticker-Price-Change-Statistics
    def ticker_24h(self):
        return self._get("/fapi/v1/ticker/24hr")

    def klines(self, symbol: str, interval: str, start_ms: int, end_ms: int):
        return self._get("/fapi/v1/klines", {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1500,
        })

    # private
    # https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V2
    def account(self):
        return self._get("/fapi/v2/account", signed=True)

    def position_risk(self):
        return self._get("/fapi/v2/positionRisk", signed=True)

    def open_orders(self, symbol: Optional[str]=None):
        params = {"symbol": symbol} if symbol else {}
        return self._get("/fapi/v1/openOrders", params, signed=True)

    def set_isolated_and_leverage(self, symbol: str, leverage: int):
        # set isolated
        try:
            self._post("/fapi/v1/marginType", {"symbol": symbol, "marginType": "ISOLATED"})
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 400:
                raise
        # set leverage
        self._post("/fapi/v1/leverage", {"symbol": symbol, "leverage": str(leverage)})

    def place_order(self, symbol: str, side: str, type_: str, quantity: str,
                    price: Optional[str]=None, time_in_force: Optional[str]=None,
                    reduce_only: Optional[str]=None, stop_price: Optional[str]=None):
        p = {"symbol": symbol, "side": side, "type": type_, "quantity": quantity}
        if price: p["price"] = price
        if time_in_force: p["timeInForce"] = time_in_force
        if reduce_only: p["reduceOnly"] = reduce_only
        if stop_price: p["stopPrice"] = stop_price
        return self._post("/fapi/v1/order", p)

    def cancel_order(self, symbol: str, order_id: int|str):
        return self._delete("/fapi/v1/order", {"symbol": symbol, "orderId": str(order_id)})
