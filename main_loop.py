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
        fd.dec_precio , fd.dec_qty = obtenerdecimales(symbol)
        fd.Qty_min = round(Qty_min(symbol, rt.current_price), fd.dec_qty)
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
#reinicio = {}
active_tasks = {}
event_loop = None



async def start_socket(symbol):
    global reinicio
    reinicio[symbol] = True
    url = f"wss://fstream.binance.com/ws/{symbol}@ticker"
    print(f"[SOCKET] WebSocket iniciado para: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
    while True:
        try:
            async with websockets.connect(url) as websocket:
                while True:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=10)
                        data = json.loads(msg)
                        payload = data
                        await calculos(symbol, payload) 
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError:
                        print(f"[SOCKET] Cancelado: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
                        return
                    except OrderError as oe:
                        print(f"[ERROR] en la orden: {oe} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
                        detener_socket(symbol)  # Detiene el ciclo pro error de orden  
                        return
                    except Exception as e:
                        print(f"[CONEXION ERROR SOKET] en WebSocket de {symbol}: {e} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
                        traceback.print_exc() #Esto es para que me muestre el error con todas las llamadas y la linea, lo puedo silenciar despues
                        break  # Si hay error en el recv, sal de este while para reconectar
        except Exception as e:
            print(f"[CONEXION ERROR] Conexión WebSocket de {symbol}: {e} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
            traceback.print_exc() #Esto es para que me muestre el error con todas las llamadas y la linea, lo puedo silenciar despues

        print(f"[SOCKET] Reintentando conexión para: {symbol} en 5 segundos... - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        await asyncio.sleep(5)  # Espera 5 segundos antes de intentar reconectar.
            
def iniciar_asyncio_loop():
    global event_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    event_loop = loop
    loop.run_forever()

def symbol_status(): #Para que devuelva el estado de un simbolo al endpoint y pasa al html
    return {symbol: (not task.done()) for symbol, task in active_tasks.items()}

def iniciar_socket_async(symbol):
    global active_tasks, event_loop

    if symbol in active_tasks:
        print(f"[SOCKET] Ya está activo: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        return

    if event_loop is None:
        print(f"[ERROR] Event loop no está inicializado - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        return

    task = asyncio.run_coroutine_threadsafe(start_socket(symbol), event_loop)
    active_tasks[symbol] = task
    print(f"[SOCKET] Tarea enviada al loop para: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
    
    
    ps, fd, rt = get_vars(symbol)
  

def detener_socket(symbol):
    task = active_tasks.get(symbol)
    if task:        
        task.cancel()
        del active_tasks[symbol]







