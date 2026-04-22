from datetime import datetime
import csv
import requests
import math
import time
import requests
from datetime import datetime, timezone
import pandas as pd

from core.dbfunc import write_db, write_analisis_db
from core.orders import close_total, get_order_info

async def restart_symbol(symbol, estado, sl, timeop, pentrada, psalida, vcierre, balance, secuencia, resultado, ps):
    fechayhora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    print(f"Proceso Cerrado para: {symbol} a causa de cierre automatico - {fechayhora}")
  

    write_analisis_db(
        symbol      = symbol,
        estado      = estado,
        sl          = sl,
        time_open   = timeop,
        time_close  = fechayhora,
        pe          = pentrada,
        ps          = psalida,
        vcierre     = round(vcierre, 2),
        balance     = round(balance, 2),
        resultado   = round(resultado, 2),
        secuencia   = secuencia,
    )
    print(f"Analisis DB escrito con exito para: {symbol}")

    
    try:
        from main_loop import  detener_socket, iniciar_socket_async # Hay que importarlo aca para que no haga importacion circular.
        
        detener_socket(symbol)

        ps.auto_restart  = True

        if ps.act_control_reinicio: iniciar_socket_async(symbol)

        write_db([['0', 'RESTART', '', '', '', '', '', '', '', '', '', '', '', fechayhora]], symbol, ps.input_sl)
        print(f"RESTART EXITOSO - {fechayhora}")


    except ImportError:
        print(f"RESTART NO EXITOSO - {fechayhora}")
        pass  # Por si no la necesitas en modo simulación, o no está importada  
   
        

def restart_symbol_backtest(symbol, estado, sl, timeop, pentrada, psalida, vcierre, balance, secuencia, resultado):
    global bt
    
    timeclose = bt.datetimerow
    Data_csv = [
        [
        bt.symbol,
        estado,
        sl,
        timeop,
        timeclose,
        pentrada,
        psalida,
        f"{vcierre  :.2f}", 
        f"{balance :.2f}",
        f"{resultado :.2f}",
        secuencia
        ]
    ]
    bt.contador_procesos += 1
    
    bt.SumaBalances +=  resultado

    if estado == "TP5L" or estado == "TP5S": bt.TP_Cont += 1      
    elif estado == "SL1L" or estado == "SL1S": bt.SL_Cont += 1
    elif estado == "BE": bt.BE_Cont += 1
  
    with open(bt.url_analisis, mode='a', newline='', encoding='utf-8') as archivo: 
        escritor_csv = csv.writer(archivo)
        escritor_csv.writerows(Data_csv)   
        
    write_csv_bt([['0', 'RESTART']], bt.symbol)

    bt.reinicio = True
    bt.activadores = False


def Qty_min(symbol, currentprice):
    """
    Devuelve solo la cantidad mínima requerida para abrir una orden,
    basada en MIN_NOTIONAL y respetando LOT_SIZE (minQty/stepSize).
    """
    data = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
    symbol = symbol.upper()

    min_notional = None
    min_qty = None
    step = None

    for s in data["symbols"]:
        if s["symbol"] == symbol:
            for f in s["filters"]:
                if f["filterType"] == "MIN_NOTIONAL":
                    min_notional = float(f["notional"])
                elif f["filterType"] == "LOT_SIZE":
                    min_qty = float(f["minQty"])
                    step = float(f["stepSize"])
            break
    if min_notional is None or min_qty is None or step is None:
        return None

    needed = min_notional / float(currentprice)   # cantidad por notional
    qty = math.ceil(needed / step) * step         # redondear hacia arriba al step
    return max(min_qty, qty)                      # respetar minQty



def obtenerdecimales(symbol: str):
    """
    Devuelve (decimalesprecio, decimalescantidad) para un símbolo de Binance Futures USDT-M.

    Parámetro:
        symbol (str): por ejemplo 'DOGEUSDT', 'BTCUSDT', 'CRVUSDT'

    Retorna:
        (decimalesprecio:int, decimalescantidad:int)

    Lanza:
        ValueError si el símbolo no existe o si está vacío.
        requests.HTTPError si falla la petición HTTP.
    """
    if not symbol:
        raise ValueError("Símbolo vacío.")
    sym = symbol.upper().strip()

    # Cache simple: descarga exchangeInfo solo la primera vez
    if not hasattr(obtenerdecimales, "_cache_exchange_info"):
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        obtenerdecimales._cache_exchange_info = resp.json()

    data = obtenerdecimales._cache_exchange_info
    symbols = data.get("symbols", [])
    info = next((s for s in symbols if s.get("symbol") == sym), None)
    if info is None:
        raise ValueError(f"Símbolo no encontrado en Binance Futures USDT-M: {sym}")

    # Filtros
    price_filter = next((f for f in info["filters"] if f["filterType"] == "PRICE_FILTER"), {})
    lot_size     = next((f for f in info["filters"] if f["filterType"] == "LOT_SIZE"), {})

    tick_size = price_filter.get("tickSize", "")
    step_size = lot_size.get("stepSize", "")

    # Cuenta decimales de tick_size
    if tick_size and "." in tick_size:
        parte_decimal_tick = tick_size.split(".")[1].rstrip("0")
        decimalesprecio = len(parte_decimal_tick)
    else:
        decimalesprecio = 0

    # Cuenta decimales de step_size
    if step_size and "." in step_size:
        parte_decimal_step = step_size.split(".")[1].rstrip("0")
        decimalescantidad = len(parte_decimal_step)
    else:
        decimalescantidad = 0

    return decimalesprecio, decimalescantidad


def soporte_resistencia(df, index_actual, bt):
    fecha_actual = df.loc[index_actual, 'datetime']
    dia = fecha_actual.date()

    if bt.sr_dia_actual == dia:
        return

    bt.sr_dia_actual = dia

    if bt.sr_primer_dia is None:
        bt.sr_primer_dia = dia

    if (dia - bt.sr_primer_dia).days < bt.sr_dias_lookback:
        return

    fecha_limite = fecha_actual - pd.Timedelta(days=bt.sr_dias_lookback)

    mascara = (df['datetime'] >= fecha_limite) & (df['datetime'] < fecha_actual)
    nuevo_soporte = float(df.loc[mascara, 'low'].min())
    nueva_resistencia = float(df.loc[mascara, 'high'].max())
    fecha_str = fecha_actual.strftime("%Y-%m-%d %H:%M")

    if bt.sr_soporte is None:
        bt.sr_soporte = nuevo_soporte
        bt.sr_resistencia = nueva_resistencia
        #print(f"[ACTIVADORES COLOCADOS] {fecha_str} | Soporte: {bt.sr_soporte} | Resistencia: {bt.sr_resistencia}")
        return

    if nuevo_soporte != bt.sr_soporte:
        anterior = bt.sr_soporte
        bt.sr_soporte = nuevo_soporte
        #print(f"[NUEVO SOPORTE] {fecha_str} | {anterior} → {bt.sr_soporte}")

    if nueva_resistencia != bt.sr_resistencia:
        anterior = bt.sr_resistencia
        bt.sr_resistencia = nueva_resistencia
        #print(f"[NUEVA RESISTENCIA] {fecha_str} | {anterior} → {bt.sr_resistencia}")

