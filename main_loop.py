from binance.client import Client
from binance.enums import *
import csv
from datetime import datetime, timezone
import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import traceback

from core.classes import DataPost, FixedData, RealTime, OrderError
from core.logic import Grid, Steps_L, Steps_S
from core.utils import Qty_min, obtenerdecimales

symbol_list = ["ethusdt", "btcusdt", "bnbusdt", "solusdt", "xrpusdt", "trxusdt", "avaxusdt", "tonusdt", "ltcusdt",
               "1000shibusdt", "dogeusdt","adausdt","xlmusdt","xmrusdt","dotusdt","uniusdt","aptusdt","nearusdt",
               "fetusdt","arbusdt","hyperusdt","suiusdt","bchusdt","linkusdt","hbarusdt","1000pepeusdt","aaveusdt",
               "taousdt","icpusdt","etcusdt","ondousdt", "kasusdt", "atomusdt", "vetusdt", "renderusdt", "enausdt", 
               "filusdt", "wldusdt", "algousdt", "qntusdt",
                "seiusdt", "jupusdt", "spxusdt", "injusdt", "tiausdt", "virtualusdt", "stxusdt", "opusdt", "penguusdt", "grtusdt",
                "imxusdt", "iotausdt", "ipusdt", "cakeusdt", "jtousdt", "crvusdt", "thetausdt", "ldousdt", "galausdt", "zecusdt"]

for ticker in symbol_list:
    globals()[f"{ticker}ps"] = DataPost()
    globals()[f"{ticker}fd"] = FixedData()
    globals()[f"{ticker}rt"] = RealTime()
  


def var_restart(symbols):  
    for symbol in symbols:
        prefix = symbol.lower()
        ps, fd, rt = get_vars(symbol)
        fd.reset()
        rt.reset()

        fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        print(f"Variables reseteadas para, {symbol} - {fechayhora}")

def get_vars(symbol):#transforma las variables en ETHps, ETHfds, ETHfdl
    suffixes = ['ps','fd','rt']
    return tuple(globals()[f"{symbol}{suf}"] for suf in suffixes)

reinicio = {'ethusdt': True,'btcusdt': True,'bnbusdt': True,'solusdt': True,'xrpusdt': True, 'trxusdt': True, 'avaxusdt': True,
            'tonusdt': True, 'ltcusdt': True, '1000shibusdt': True, 'dogeusdt': True, 'adausdt': True, 'xlmusdt': True,
             'xmrusdt': True, 'dotusdt': True, 'uniusdt': True, 'aptusdt': True, 'nearusdt': True, 'fetusdt': True,
              'arbusdt': True,'hyperusdt': True,'suiusdt': True,'bchusdt': True,'linkusdt': True,'hbarusdt': True,
              '1000pepeusdt': True,'aaveusdt': True,'taousdt': True,'icpusdt': True,'etcusdt': True,
               "ondousdt": True, "kasusdt": True, "atomusdt": True, "vetusdt": True, "renderusdt": True, "enausdt": True, 
                "filusdt": True, "wldusdt": True, "algousdt": True, "qntusdt": True, "seiusdt": True, "jupusdt": True, 
                "spxusdt": True, "injusdt": True, "tiausdt": True, "virtualusdt": True, "stxusdt": True, "opusdt": True, 
                "penguusdt": True, "iotausdt": True, "imxusdt": True, "grtusdt": True, "ipusdt": True, "cakeusdt": True, 
                "jtousdt": True, "crvusdt": True, "thetausdt": True, "ldousdt": True, "galausdt": True, "zecusdt": True}       


async def calculos(symbol, datasocket):
    global reinicio
    ps, fd, rt = get_vars(symbol) #Transforma las variables en ETHps, ETHfds, ETHfdl, ETHrts, ETHrtl, ETHsd
    
    rt.current_price = float(datasocket['c'])

   

    if reinicio[symbol]: #reinicio las variables un sola vez
        var_restart([symbol])
        rt.current_price = float(datasocket['c'])
        fd.r0 = rt.current_price
        fd.fechainicio = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        fd.dec_precio, fd.dec_qty = await asyncio.to_thread(obtenerdecimales, symbol)
        qty_min = await asyncio.to_thread(Qty_min, symbol, rt.current_price)
        fd.Qty_min = round(qty_min, fd.dec_qty)
        fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        Grid(ps, fd, rt)

        print(f"Grillas listas para {symbol} - Simulacion = {ps.simulacion} - {fechayhora}")

        reinicio[symbol] = False
 


    if rt.current_price != rt.previous_price:
        rt.previous_price = rt.current_price 

        rt.fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

        # await Steps_S(ps, fd, rt, symbol)
        # await Steps_L(ps, fd, rt, symbol)


################# FUNCIONES RELACIONADAS AL SOCKET #######################

active_symbols = set()
combined_task = None
event_loop = None


async def start_combined_socket():
    streams = "/".join(f"{symbol}@ticker" for symbol in symbol_list)
    url = f"wss://fstream.binance.com/stream?streams={streams}"

    print(f"[SOCKET] Combined stream iniciado - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"[SOCKET] URL combined stream con {len(symbol_list)} símbolos")

    while True:
        try:
            async with websockets.connect(
                url,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            ) as websocket:

                print(f"[SOCKET] Combined stream CONECTADO - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}")

                while True:
                    try:
                        msg = await websocket.recv()
                        data = json.loads(msg)

                        payload = data.get("data", {})
                        symbol = payload.get("s", "").lower()

                        if not symbol:
                            continue

                        if symbol not in active_symbols:
                            continue

                        await calculos(symbol, payload)

                    except asyncio.CancelledError:
                        print(f"[SOCKET] Combined stream cancelado - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
                        return

                    except OrderError as oe:
                        print(f"[ERROR] en la orden: {oe} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
                        traceback.print_exc()
                        break

                    except Exception as e:
                        print(f"[CONEXION ERROR SOCKET] Combined stream: {repr(e)} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
                        traceback.print_exc()
                        break

        except asyncio.CancelledError:
            print(f"[SOCKET] Combined stream cancelado fuera de conexión - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
            return

        except Exception as e:
            print(f"[CONEXION ERROR] Combined stream: {repr(e)} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
            traceback.print_exc()

        print(f"[SOCKET] Reintentando combined stream en 5 segundos... - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        await asyncio.sleep(5)


def iniciar_asyncio_loop():
    global event_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    event_loop = loop
    loop.run_forever()


def symbol_status():
    return {symbol: (symbol in active_symbols) for symbol in symbol_list}


def iniciar_socket_async(symbol):
    global combined_task, event_loop, active_symbols, reinicio

    symbol = symbol.lower().strip()

    if symbol in active_symbols:
        print(f"[SOCKET] Ya está activo: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        return

    if event_loop is None:
        print(f"[ERROR] Event loop no está inicializado - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        return

    active_symbols.add(symbol)
    reinicio[symbol] = True

    print(f"[SOCKET] Símbolo activado: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")

    if combined_task is None or combined_task.done():
        combined_task = asyncio.run_coroutine_threadsafe(start_combined_socket(), event_loop)
        print(f"[SOCKET] Tarea combined stream enviada al loop - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")


def detener_socket(symbol):
    global combined_task, active_symbols

    symbol = symbol.lower().strip()

    if symbol in active_symbols:
        active_symbols.remove(symbol)
        print(f"[SOCKET] Símbolo detenido: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
    else:
        print(f"[SOCKET] Símbolo no estaba activo: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")

    if not active_symbols and combined_task is not None and not combined_task.done():
        combined_task.cancel()
        combined_task = None
        print(f"[SOCKET] Combined stream detenido porque no quedan símbolos activos - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")




