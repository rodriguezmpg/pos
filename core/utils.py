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
   
        

data = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
_exchange_info_cache = None

def get_exchange_info(): #Para que descague los datos para Qtymin y obtenerdecimales una sola vez.
    global _exchange_info_cache

    if _exchange_info_cache is None:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        _exchange_info_cache = resp.json()

    return _exchange_info_cache


def Qty_min(symbol, currentprice):
    """
    Devuelve solo la cantidad mínima requerida para abrir una orden,
    basada en MIN_NOTIONAL y respetando LOT_SIZE (minQty/stepSize).
    """
    data = get_exchange_info()
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
    if not symbol:
        raise ValueError("Símbolo vacío.")

    sym = symbol.upper().strip()
    data = get_exchange_info()

    symbols = data.get("symbols", [])
    info = next((s for s in symbols if s.get("symbol") == sym), None)

    if info is None:
        raise ValueError(f"Símbolo no encontrado en Binance Futures USDT-M: {sym}")

    price_filter = next((f for f in info["filters"] if f["filterType"] == "PRICE_FILTER"), {})
    lot_size = next((f for f in info["filters"] if f["filterType"] == "LOT_SIZE"), {})

    tick_size = price_filter.get("tickSize", "")
    step_size = lot_size.get("stepSize", "")

    if tick_size and "." in tick_size:
        decimalesprecio = len(tick_size.split(".")[1].rstrip("0"))
    else:
        decimalesprecio = 0

    if step_size and "." in step_size:
        decimalescantidad = len(step_size.split(".")[1].rstrip("0"))
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

