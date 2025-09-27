import hmac
import time
import hashlib
from typing import Dict, Optional
import requests
from binbot.config import Config
import random
from urllib.parse import urlencode
from decimal import Decimal
import math


def _cut_decimals(val: float|str, tick_size: float) -> str:
    """Recorta decimales según tick_size sin redondear."""
    tick_decimals = abs(Decimal(str(tick_size)).as_tuple().exponent)
    factor = 10 ** tick_decimals
    return f"{math.floor(float(val) * factor) / factor:.{tick_decimals}f}"


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

        # verbose
        self.verbose = cfg.verbose

        self.cfg = cfg

    # signing helpers
    def _sign(self, params: Dict[str, str]) -> Dict[str, str]:
        # Copia para no mutar el original
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)

        # Generar querystring exactamente como se enviará
        query = urlencode(params, doseq=True)
        sig = hmac.new(self.secret, query.encode(), hashlib.sha256).hexdigest()

        params["signature"] = sig
        return params

    def _request(self, method: str, path: str, *,
                 params: Dict[str, str] | None = None,
                 signed: bool = False):
        url = f"{self.base}{path}"
        params = params or {}
        if signed:
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

                # --- 👇 interceptamos errores Binance antes de raise_for_status ---
                if r.status_code >= 400:
                    err_code, err_msg = None, None
                    try:
                        data = r.json()
                        err_code = data.get("code")
                        err_msg = data.get("msg")
                    except Exception:
                        err_msg = r.text
                    raise requests.HTTPError(
                        f"Binance error {err_code}: {err_msg} "
                        f"(HTTP {r.status_code} {r.reason} for {url})",
                        response=r
                    )

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

    def leverage_bracket(self, symbol: str):
        return self._get("/fapi/v1/leverageBracket", {"symbol": symbol}, signed=True)

    def set_isolated_and_leverage(self, symbol: str, leverage: int):
        """
        1) Cambia el margin type del símbolo a ISOLATED (idempotente).
        2) Ajusta el leverage al valor solicitado (sin clamps ni lógica extra).
        """
        # 1) marginType ISOLATED
        try:
            self._post("/fapi/v1/marginType", {"symbol": symbol, "marginType": "ISOLATED"})
        except requests.HTTPError as e:
            # Binance devuelve 400 con code -4046 si ya está en ISOLATED
            try:
                data = e.response.json()
                if data.get("code") != -4046:
                    raise
            except Exception:
                # si no podemos parsear o no es -4046, relanzamos
                raise

        # 2) set leverage solicitado
        return self._post("/fapi/v1/leverage", {"symbol": symbol, "leverage": str(leverage)})

    def place_order(self, symbol: str, side: str, type_: str, quantity: str,
                price: Optional[str]=None, time_in_force: Optional[str]=None,
                reduce_only: Optional[str]=None, stop_price: Optional[str]=None,
                close_position: Optional[bool]=None, working_type: Optional[str]=None,
                sym_filters: Optional[dict]=None):
        if sym_filters is not None and symbol in sym_filters:
            f = sym_filters[symbol]
            if quantity is not None:
                quantity = _cut_decimals(quantity, f["stepSize"])
            if price is not None:
                price = _cut_decimals(price, f["tickSize"])
            if stop_price is not None:
                stop_price = _cut_decimals(stop_price, f["tickSize"])

        p = {"symbol": symbol, "side": side, "type": type_, "quantity": quantity}
        if price: p["price"] = price
        if time_in_force: p["timeInForce"] = time_in_force
        if reduce_only: p["reduceOnly"] = reduce_only
        if stop_price: p["stopPrice"] = stop_price
        if close_position is not None: p["closePosition"] = "true" if close_position else "false"
        if working_type: p["workingType"] = working_type  # "MARK_PRICE" o "CONTRACT_PRICE"
        return self._post("/fapi/v1/order", p)

    def cancel_order(self, symbol: str, order_id: int|str):
        return self._delete("/fapi/v1/order", {"symbol": symbol, "orderId": str(order_id)})
