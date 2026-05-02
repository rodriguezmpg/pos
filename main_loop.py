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


from core.orders import get_listen_key
from core.classes import DataPost, FixedData, RealTime, OrderError
from core.logic import Grid, Steps, r_1
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
        rt.fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        await Grid(symbol, ps, fd, rt)
        
        print(f"Grillas listas para {symbol} - {rt.fechayhora}")
        
        reinicio[symbol] = False  


    if rt.current_price != rt.previous_price:
        rt.previous_price = rt.current_price 

        rt.fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

        await Steps(ps, fd, rt, symbol)


################# FUNCIONES RELACIONADAS AL SOCKET #######################
#reinicio = {}
active_tasks = {}
event_loop = None

async def start_socket(symbol):
    global reinicio
    reinicio[symbol] = True
    url = f"wss://fstream.binance.com/market/ws/{symbol}@ticker"
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
                        print(f"[SOCKET] Sin mensajes hace 10s, reconectando: {symbol}")
                        break
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
  

async def detener_socket(symbol, ps, fd, rt):
    task = active_tasks.get(symbol)
    print(f"rt.detener_cm en stop soket: {rt.detener_cm}")
    await r_1(symbol, ps, fd, rt)
    if task:        
        task.cancel()
        del active_tasks[symbol]



def iniciar_asyncio_orderupdate():
    global event_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    event_loop = loop
    loop.create_task(start_user_data_socket_order_update())

    loop.run_forever()

async def start_user_data_socket_order_update():

    while True:
        try:
            listen_key = await asyncio.to_thread(get_listen_key)
            # Nos aseguramos de pedir todos los eventos posibles en el endpoint private
            eventos = "ORDER_TRADE_UPDATE/ALGO_UPDATE/ACCOUNT_CONFIG_UPDATE"
            url = f"wss://fstream.binance.com/private/ws?listenKey={listen_key}&events={eventos}"
            
            async with websockets.connect(url) as ws:
                print("[GENERAL SOCKET] Conectado")
                
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    evento = data.get("e")

                    if evento == "ORDER_TRADE_UPDATE":
                        o = data.get("o", {})
                        algo_id_vinculado = o.get("si") or o.get("ca") # ca es Client Algo ID
                        order_id_real = o.get("i")
                        symbol_raw = o.get("s")
                        
                        if o.get("X") == "FILLED":
                            pnl = float(o.get("rp", 0))
                            if pnl != 0:
                                if symbol_raw:
                                    try: 
                                        ps, fd, rt = get_vars(symbol_raw.lower())

                                        if algo_id_vinculado == rt.id_order_r1: rt.r1_active = True
                                        if algo_id_vinculado == rt.id_order_r2: rt.r2_active = True
                                        if algo_id_vinculado == rt.id_order_r_1: rt.r_1_active = True
                                        if algo_id_vinculado == rt.id_order_r_1: rt.r_1_active = True
                                        

                                        rt.ALGO_orderid = order_id_real
                                        rt.ALGO_pnl = float(pnl)
                                        rt.AlGO_comision = float(o.get('n')) #N
                                        rt.ALGO_QtymVar = float(o.get("z")) # o probar "l"
                                        rt.ALGO_PE = float(o.get("ap"))
                                                                             
                                    except Exception as var_error:
                                        print(f"[ERROR VARS] No se pudo asignar posicionalgo para {symbol_raw}: {var_error}")

                                # print(f"DETALLES DE CIERRE")
                                # print(f"Símbolo: {o.get('s')}")
                                # print(f"Order ID: {order_id_real}")
                                # print(f"Algo ID Vinculado: {algo_id_vinculado}")
                                # print(f"PNL Realizado: {pnl}")
                                # print(f"Comisión: {o.get('n')} {o.get('N')}")
                                # print(f"rt.id_order_r1: {rt.id_order_r1}")
                                # print(f"rt.id_order_r2: {rt.id_order_r2}")
                                # print(f"rt.id_order_r_1: {rt.id_order_r_1}")
                                # print(f"rt.r1_active: {rt.r1_active}")
                                # print(f"rt.r2_active: {rt.r2_active}")
                                # print(f"rt.r_1_active: {rt.r_1_active}")
                                

        except Exception as e:
            print(f"[USER SOCKET ERROR] Reintentando... {e}")
            await asyncio.sleep(5)


