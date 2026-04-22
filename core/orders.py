import os
import json
import asyncio
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

# API_KEY = '5a4aa2b8a3af4b8508f73fd14a44d24aea7a1ac4f8ff7e506f0c0df1531fc079'
# API_SECRET = '4381c8656f03f515775d19e7a15b80b2c0b00e63cd3fce529082602f29682e9e'
# client = Client(API_KEY, API_SECRET, testnet=True)
# client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
# client.FUTURES_WEBSOCKET_URL = 'wss://stream.binancefuture.com/ws'



async def order_market(symbol: str, side: str, quantity: float, reduce: bool = False):
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
        print(f"Orden enviada: {id_order} - {symbol}")
        return id_order
    except Exception as e:
        print(f"Error al enviar la orden para {symbol}: {e} - Qty = {quantity}")
        raise OrderError(f"Error en la orden para {symbol}: {e}")


async def order_tp_market(symbol: str, side: str, quantity: float, trigger_price: float):
    """
    TP como TAKE_PROFIT_MARKET: cuando el precio toca trigger_price,
    se dispara un MARKET garantizado. Paga Taker (0.05%).
    """
    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        type='TAKE_PROFIT_MARKET',
        stopPrice=trigger_price,
        quantity=quantity,
        reduceOnly=True,
        timeInForce='GTE_GTC',
        newOrderRespType='FULL'
    )
    return order['orderId']

async def order_sl_stop_market(symbol: str, side: str, stop_price: float):
    try:
        order = client.futures_create_order(
            symbol=symbol,                        # Ej: 'BTCUSDT'
            side=side,                            # 'SELL' si la posición es LONG
            type=FUTURE_ORDER_TYPE_STOP_MARKET,   # Tipo STOP_MARKET
            stopPrice=stop_price,                 # Precio de disparo del SL
            closePosition=True,                   # Cierra toda la posición
            timeInForce='GTE_GTC',
            newOrderRespType='FULL'
        )
        id_order = order['orderId']
        print(f"SL STOP_MARKET enviado: {id_order} - {symbol} @ {stop_price}")
        return id_order
    except Exception as e:
        print(f"Error al enviar SL STOP_MARKET para {symbol}: {e}")
        raise OrderError(f"Error en SL STOP_MARKET para {symbol}: {e}")
    
    

async def get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1): #Obtiene los datos del historial de operaciones
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
            # Si no se encontró la orden, esperar y reintentar
            await asyncio.sleep(wait_seconds)
    # Si llegamos aquí, nunca encontramos la orden
    raise Exception(f"No se encontró la orden {id_order} después de {max_attempts} intentos. en la fucion get_order_info()")


async def get_order_pnl(symbol): #Para obtener el pnl de cierres parciales
    trades = client.futures_account_trades(symbol=symbol)
    ultimo_trade = trades[-1]
    Pnl = float(ultimo_trade['realizedPnl'])
    return Pnl

async def close_total(symbol):
    def get_amt():
        positions = client.futures_position_information(symbol=symbol)
        for p in positions:
            amt = float(p.get('positionAmt', 0))
            if amt != 0:
                return amt
        return 0.0

    # 1) detectar posición abierta (con reintento corto)
    amt = 0.0
    for _ in range(3):
        amt = get_amt()
        if amt != 0:
            break
        await asyncio.sleep(0.4)

    if amt == 0:
        print(f"[close_total] No hay posición abierta para {symbol} (tras reintentos)")
        return None

    # 2) primer cierre reduceOnly
    qty = abs(amt)
    side = SIDE_BUY if amt < 0 else SIDE_SELL
    id_order = await order_market(symbol, side=side, quantity=qty, reduce=True)

    # 3) verificar si quedó resto
    await asyncio.sleep(0.4)
    rem = get_amt()

    # 4) segundo intento solo si sigue habiendo posición
    if rem != 0:
        qty2 = abs(rem)
        side2 = SIDE_BUY if rem < 0 else SIDE_SELL
        print(f"[close_total] Quedó remanente {rem} en {symbol}, reintentando cierre...")
        id_order = await order_market(symbol, side=side2, quantity=qty2, reduce=True)

    return id_order




def prueba_conexion(): #Para revisar si la IP es correcta
    try:
        info = client.futures_account()
        return True
    except Exception as e:
        print(f"No se pudo conectar a Binance. Motivo: {e}")
        return False
        
