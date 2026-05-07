from datetime import datetime, timezone
import asyncio
import websockets
import json
import traceback
import os


from core.orders import get_listen_key, keepalive_listen_key
from core.classes import DataPost, FixedData, RealTime, OrderError, gl
from core.logic import Grid, Steps, r_1
from core.utils import Qty_min, obtenerdecimales

import logging
logger = logging.getLogger('reg')


TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"


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
        ps, fd, rt = get_vars(symbol)
        fd.reset()
        rt.reset()
        ps.reset()

        fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        logger.info(f"Variables reseteadas para, {symbol} - {fechayhora}")

def get_vars(symbol):#transforma las variables en ETHps, ETHfds, ETHfdl
    suffixes = ['ps','fd','rt']
    return tuple(globals()[f"{symbol}{suf}"] for suf in suffixes)

reinicio = {s: True for s in symbol_list}       


async def calculos(symbol, datasocket):
    global reinicio
    ps, fd, rt = get_vars(symbol) #Transforma las variables en ETHps, ETHfds, ETHfdl, ETHrts, ETHrtl, ETHsd
    
    rt.current_price = float(datasocket['c'])

   

    if reinicio[symbol]: #reinicio las variables un sola vez
        reinicio[symbol] = False  #importante que este primero antes de los await
        #var_restart([symbol]) #No lo necesito por que resetea al detener el soket.
        rt.current_price = float(datasocket['c'])
        fd.r0 = rt.current_price
        fd.fechainicio = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        fd.dec_precio , fd.dec_qty = obtenerdecimales(symbol)
        fd.Qty_min = round(Qty_min(symbol, rt.current_price), fd.dec_qty)
        rt.fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        await Grid(symbol, ps, fd, rt)        
        logger.info(f"[{symbol}] - Inicio terminado")
        
        


    if rt.current_price != rt.previous_price:
        rt.previous_price = rt.current_price 

        rt.fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

        await Steps(ps, fd, rt, symbol)


################# FUNCIONES RELACIONADAS AL SOCKET #######################
active_tasks = {}
event_loop = None


def iniciar_socket_async(symbol):
    global active_tasks, event_loop

    if symbol in active_tasks:
        logger.info(f"[SOCKET] Ya está activo: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        return

    if event_loop is None:
        logger.info(f"[ERROR] Event loop no está inicializado - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
        return

    task = asyncio.run_coroutine_threadsafe(start_socket(symbol), event_loop)
    active_tasks[symbol] = task
    logger.info(f"[SOCKET] Tarea enviada al loop para: {symbol} - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}")
    
    
    ps, fd, rt = get_vars(symbol)

async def start_socket(symbol):
    global reinicio
    reinicio[symbol] = True
    if TESTNET: url = f"wss://stream.binancefuture.com/ws/{symbol}@ticker"
    else: url = f"wss://fstream.binance.com/market/ws/{symbol}@ticker"
    logger.info(f"[{symbol}][SOCKET] WebSocket iniciado correctamente")
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
                        logger.info(f"[{symbol}][SOCKET] Sin mensajes hace 10s, reconectando...")
                        break
                    except asyncio.CancelledError:
                        logger.info(f"[{symbol}][SOCKET] Cancelado ")
                        return
                    except OrderError as oe:
                        logger.info(f"[{symbol}][SOKET] ERROR en el envio orden al socket: {oe} - ")
                        return
                    except Exception as e:
                        logger.info(f"[{symbol}][CONEXION ERROR SOCKET] {e} ")  
                        break  # Si hay error en el recv, sal de este while para reconectar
        except Exception as e:
            logger.info(f"[{symbol}][ERROR CONEXION WEBSOCKET] {e} ")

        logger.info(f"[{symbol}][CONEXION ERROR SOCKET]Perdida de conexion, reintentando en en 5 segundos...")
        await asyncio.sleep(5)  #



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
            if TESTNET: url = f"wss://stream.binancefuture.com/ws/{listen_key}"
            else: url = f"wss://fstream.binance.com/private/ws?listenKey={listen_key}&events={eventos}"

            last_keepalive = asyncio.get_event_loop().time()
            
            async with websockets.connect(url) as ws:
                print("[GENERAL SOCKET] Conectado")
                while True:
                    try: 
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
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
                                            

                                            rt.ALGO_orderid = order_id_real
                                            rt.ALGO_pnl = float(pnl)
                                            rt.AlGO_comision = float(o.get('n')) #N
                                            rt.ALGO_QtymVar = float(o.get("z")) # o probar "l"
                                            rt.ALGO_PE = float(o.get("ap"))
                                                                                
                                        except Exception as var_error:
                                            logger.info(f"[ERROR VARS] No se pudo asignar posicionalgo para {symbol_raw}: {var_error}")

                    except asyncio.TimeoutError:
                        # Keepalive cada 30 minutos para que el listenKey no expire
                        ahora = asyncio.get_event_loop().time()
                        if ahora - last_keepalive > 1800:
                            try:
                                await asyncio.to_thread(keepalive_listen_key, listen_key)
                                last_keepalive = ahora
                            except Exception as ka_error:
                                logger.info(f"[GENERAL SOCKET] Keepalive falló, reconectando: {ka_error}")
                                break  # Fuerza reconexión con nuevo listenKey


        except Exception as e:
            logger.info(f"[SOCKET GENERAL ERROR] Reintentando... {e}")
            await asyncio.sleep(10)


    
async def detener_socket(symbol, ps, fd, rt):
    task = active_tasks.get(symbol)
    if fd.control and rt.detener_cm:
        logger.info(f"[DETENER SOCKET] Detencion Manual")
        await r_1(symbol, ps, fd, rt)
    else: logger.info(f"[DETENER SOCKET] Detencion Automatica")
    if task:        
        task.cancel()
        del active_tasks[symbol]