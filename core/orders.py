import os
import json
import asyncio
import hmac
import hashlib
import time as _time
from urllib.parse import urlencode

import requests
import websockets
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
import time

from core.classes import OrderError


load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET, tld='com')

FUTURES_BASE = "https://fapi.binance.com"


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


async def order_tp_market(symbol: str, side: str, quantity: float, trigger_price: float, tag: str = ""):
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
        if tag:
            params["clientAlgoId"] = f"{symbol.upper()}_{tag}_{int(time.time() * 1000)}"
        result = await asyncio.to_thread(_algo_order_post, params)
        id_order = result.get("algoId")
        return id_order
    except Exception as e:
        print(f"Error TP_MARKET {symbol}: {e}")
        raise OrderError(f"Error TP_MARKET {symbol}: {e}")


async def order_sl_stop_market(symbol: str, side: str, stop_price: float, tag: str = ""):
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
        if tag:
            params["clientAlgoId"] = f"{symbol.upper()}_{tag}_{int(time.time() * 1000)}"
        result = await asyncio.to_thread(_algo_order_post, params)
        id_order = result.get("algoId")
        return id_order
    except Exception as e:
        print(f"Error SL STOP_MARKET {symbol}: {e}")
        raise OrderError(f"Error SL STOP_MARKET {symbol}: {e}")



async def get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1):
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
            return PE_order, pnl, fee
        else:
            await asyncio.sleep(wait_seconds)
    raise Exception(f"No se encontró la orden {id_order} después de {max_attempts} intentos.")


async def get_order_pnl(symbol):
    trades = client.futures_account_trades(symbol=symbol)
    ultimo_trade = trades[-1]
    return float(ultimo_trade['realizedPnl'])


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


def prueba_conexion():
    try:
        info = client.futures_account()
        return True
    except Exception as e:
        print(f"No se pudo conectar a Binance. Motivo: {e}")
        return False



#--------------------- ESCUCHA DE ACTIVACION DE ORDENES -----------------------------#

FUTURES_WS_BASE = "wss://fstream.binance.com/ws"


def _create_listen_key() -> str:
    headers = {"X-MBX-APIKEY": API_KEY}
    url = f"{FUTURES_BASE}/fapi/v1/listenKey"

    resp = requests.post(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise OrderError(f"Error creando listenKey: {resp.status_code} {resp.text}")

    return resp.json()["listenKey"]


def _keepalive_listen_key(listen_key: str):
    headers = {"X-MBX-APIKEY": API_KEY}
    url = f"{FUTURES_BASE}/fapi/v1/listenKey"

    resp = requests.put(
        url,
        params={"listenKey": listen_key},
        headers=headers,
        timeout=10,
    )

    if resp.status_code != 200:
        raise OrderError(f"Error renovando listenKey: {resp.status_code} {resp.text}")


async def listen_order_updates(on_order_filled):
    """
    Escucha ejecuciones reales de órdenes Futures.
    Recibe eventos de TODOS los símbolos de la cuenta.
    """

    while True:
        listen_key = await asyncio.to_thread(_create_listen_key)
        url = f"{FUTURES_WS_BASE}/{listen_key}"

        print("[USER STREAM] Iniciado para órdenes de Binance Futures")

        async def keepalive_loop():
            while True:
                await asyncio.sleep(30 * 60)
                await asyncio.to_thread(_keepalive_listen_key, listen_key)
                print("[USER STREAM] listenKey renovado")

        keepalive_task = asyncio.create_task(keepalive_loop())

        try:
            async with websockets.connect(url) as websocket:
                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)

                    if data.get("e") != "ORDER_TRADE_UPDATE":
                        continue

                    order = data.get("o", {})

                    order_type = order.get("o")
                    execution_type = order.get("x")
                    order_status = order.get("X")

                    if (
                        execution_type == "TRADE"
                        and order_status == "FILLED"
                        and order_type in ("TAKE_PROFIT_MARKET", "STOP_MARKET")
                    ):
                        await on_order_filled(data)

        except Exception as e:
            print(f"[USER STREAM] Error: {e}. Reintentando en 5 segundos...")

        finally:
            keepalive_task.cancel()

        await asyncio.sleep(5)