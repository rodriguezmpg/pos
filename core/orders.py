import os
import asyncio
import hmac
import hashlib
import time as _time
from urllib.parse import urlencode
import requests
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv

from core.classes import OrderError


load_dotenv()
TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

if TESTNET:
    API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
    API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET")
else:
    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_API_SECRET")


FUTURES_BASE = "https://testnet.binancefuture.com" if TESTNET else "https://fapi.binance.com"
client = Client(API_KEY, API_SECRET, tld='com', testnet=TESTNET)


def _sign(params: dict) -> str:
    """Firma HMAC-SHA256 que requiere Binance para endpoints firmados."""
    query = urlencode(params, doseq=True)
    return hmac.new(
        API_SECRET.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _algo_order_post(params: dict) -> dict:
    """
    POST a /fapi/v1/algoOrder (Algo Order API).
    Tras la migración del 2026-04-23, las órdenes condicionales
    (STOP_MARKET, TAKE_PROFIT_MARKET, etc.) se envían acá, no por /fapi/v1/order.
    """
    params = dict(params)
    params["timestamp"] = int(_time.time() * 1000)
    params["recvWindow"] = 5000
    params["signature"] = _sign(params)

    headers = {"X-MBX-APIKEY": API_KEY}
    url = f"{FUTURES_BASE}/fapi/v1/algoOrder"

    resp = requests.post(url, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise OrderError(f"Algo API {resp.status_code}: {resp.text}")
    return resp.json()




async def order_market(symbol: str, side: str, quantity: float, reduce: bool = False):
    """MARKET sigue yendo por el endpoint clásico /fapi/v1/order."""
    try:
        if not reduce: #si hay una posicion abierta para ese simbolo no va abrir una nueva.
            positions = client.futures_position_information(symbol=symbol)

            if any(float(p.get('positionAmt', 0)) != 0 for p in positions):
                print(f"[order_market] Ya hay posición abierta para {symbol}, se omite la orden.")
                return None
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=quantity,
            reduceOnly=reduce,
            newOrderRespType='FULL'
        )
        id_order = order['orderId']
        return id_order
    except Exception as e:
        print(f"Error al enviar la orden para {symbol}: {e} - Qty = {quantity}")
        raise OrderError(f"Error en la orden para {symbol}: {e}")


async def order_tp_market(symbol: str, side: str, quantity: float, trigger_price: float):
    """
    TAKE_PROFIT_MARKET vía Algo Order API.
    Cuando el precio toca trigger_price, se dispara un MARKET (paga taker).
    """
    try:
        params = {
            "algoType": "CONDITIONAL",
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT_MARKET",
            "triggerPrice": trigger_price,
            "quantity": quantity,
            "reduceOnly": "true",
            "timeInForce": "GTC",
            "newOrderRespType": "RESULT",
        }
        result = await asyncio.to_thread(_algo_order_post, params)
        id_order = result.get("algoId")
        return id_order
    except Exception as e:
        print(f"Error TP_MARKET {symbol}: {e}")
        raise OrderError(f"Error TP_MARKET {symbol}: {e}")


async def order_sl_stop_market(symbol: str, side: str, stop_price: float):
    """
    STOP_MARKET vía Algo Order API. Cierra toda la posición (closePosition=true).
    """
    try:
        params = {
            "algoType": "CONDITIONAL",
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "triggerPrice": stop_price,
            "closePosition": "true",
            "timeInForce": "GTC",
            "newOrderRespType": "RESULT",
        }
        result = await asyncio.to_thread(_algo_order_post, params)
        id_order = result.get("algoId")
        return id_order
    except Exception as e:
        print(f"Error SL STOP_MARKET {symbol}: {e}")
        raise OrderError(f"Error SL STOP_MARKET {symbol}: {e}")



async def get_order_info(symbol, id_order, max_attempts=10, wait_seconds=2):
    if id_order is None:
        return 0, 0, 0, 0

    for attempt in range(max_attempts):
        trades = client.futures_account_trades(symbol=symbol)
        trades_de_la_orden = [t for t in trades if t['orderId'] == id_order]
        if trades_de_la_orden:
            fee = sum(float(t['commission']) for t in trades_de_la_orden)
            pnl = sum(float(t['realizedPnl']) for t in trades_de_la_orden)
            total_qty = sum(float(t['qty']) for t in trades_de_la_orden)
            if total_qty > 0:
                PE_order = sum(float(t['price']) * float(t['qty']) for t in trades_de_la_orden) / total_qty
            else:
                PE_order = 0
            return PE_order, pnl, fee, total_qty
        else:
            await asyncio.sleep(wait_seconds)
    raise Exception(f"No se encontró la orden {id_order} después de {max_attempts} intentos.")



async def close_total(symbol):
    def get_amt():
        positions = client.futures_position_information(symbol=symbol)
        for p in positions:
            amt = float(p.get('positionAmt', 0))
            if amt != 0:
                return amt
        return 0.0

    amt = 0.0
    for _ in range(3):
        amt = get_amt()
        if amt != 0:
            break
        await asyncio.sleep(0.4)

    if amt == 0:
        print(f"[close_total] No hay posición abierta para {symbol}")
        return None

    qty = abs(amt)
    side = SIDE_BUY if amt < 0 else SIDE_SELL
    id_order = await order_market(symbol, side=side, quantity=qty, reduce=True)

    await asyncio.sleep(0.4)
    rem = get_amt()

    if rem != 0:
        qty2 = abs(rem)
        side2 = SIDE_BUY if rem < 0 else SIDE_SELL
        print(f"[close_total] Quedó remanente {rem} en {symbol}, reintentando cierre...")
        id_order = await order_market(symbol, side=side2, quantity=qty2, reduce=True)

    return id_order

def cancel_algo_order(symbol: str, algo_id: int):
    if not algo_id:
        return None

    try:
        params = {
            "symbol": symbol,
            "algoId": algo_id,
            "timestamp": int(_time.time() * 1000),
            "recvWindow": 5000,
        }
        params["signature"] = _sign(params)

        headers = {"X-MBX-APIKEY": API_KEY}

        resp = requests.delete(
            f"{FUTURES_BASE}/fapi/v1/algoOrder",
            params=params,
            headers=headers,
            timeout=10
        )

        if resp.status_code in (400, 404):
            print(f"[INFO] AlgoId={algo_id} ya no existe, nada que cancelar.")
            return None

        if resp.status_code != 200:
            raise Exception(f"Error cancelando algoId {algo_id}: {resp.text}")

        print(f"[OK] Cancelada algoId={algo_id}")
        return resp.json()

    except Exception as e:
        print(f"[ERROR] cancel_algo_order: {e}")
        return None


def get_listen_key(): #para escucha de cambios en ordenes condicionales
    url = f"{FUTURES_BASE}/fapi/v1/listenKey"
    headers = {"X-MBX-APIKEY": API_KEY}
    resp = requests.post(url, headers=headers, timeout=10)
    return resp.json()["listenKey"]

def keepalive_listen_key(listen_key: str):
    """Renueva el listenKey para que no expire. Llamar cada 30-50 min."""
    url = f"{FUTURES_BASE}/fapi/v1/listenKey"
    headers = {"X-MBX-APIKEY": API_KEY}
    params = {"listenKey": listen_key}
    resp = requests.put(url, headers=headers, params=params, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"Keepalive listenKey falló {resp.status_code}: {resp.text}")



_ultima_prueba = 0
def prueba_conexion():
    global _ultima_prueba
    ahora = _time.time()
    
    # No probar más de una vez cada 60 segundos
    if ahora - _ultima_prueba < 60:
        return True  # asumir que está bien
    
    try:
        client.futures_ping()  # ← ping pesa mucho menos que futures_account()
        _ultima_prueba = ahora
        return True
    except Exception as e:
        print(f"No se pudo conectar a Binance. Motivo: {e}")
        return False


