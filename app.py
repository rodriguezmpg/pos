from flask import Flask, render_template, jsonify, request, Response, send_file, abort
import threading
import re 
import logging
import requests
import sqlite3
import os
import time as _time
from main_loop import iniciar_asyncio_orderupdate, symbol_list

import main_loop
from core.orders import prueba_conexion
from core.dbfunc import DB_PATH
from core.dbinit import init_db

app=Flask(__name__)
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/main')
def index_main():  
    return render_template('main_loop.html')


@app.route('/getip') #Por ahora retire la IP
def getip():
    ip = requests.get('https://api.ipify.org').text.strip()
    ip_check = prueba_conexion()
    return jsonify({'ip': ip, 'ip_check': ip_check})


@app.route('/dat_fixed')
def dat_fixed():
    ticker = request.args.get("ticker").lower()
    ps  = getattr(main_loop, f"{ticker}ps")
    rt = getattr(main_loop, f"{ticker}rt")
    fd = getattr(main_loop, f"{ticker}fd")  
 
    return jsonify({
        'fd_fechainicio': fd.fechainicio,
        'fd_Qty_min': fd.Qty_min,
        'ps_USDT1r': ps.USDT1r,
        'fd_r_1': fd.r_1,
        'fd_r0': fd.r0,
        'fd_r1': fd.r1,
        'fd_r2': fd.r2,
        'fd_type_pos': fd.type_pos,
        'fd_perc1_r': fd.perc1_r,
        'fd_perc1r': fd.perc1r,
        'fd_perc2r': fd.perc2r,
        'fd_Qty_mVar': fd.Qty_mVar,
        'fd_Qty_r1': fd.Qty_r1,
        'fd_Qty_r2': fd.Qty_r2,
        'fd_Qty_ts': fd.Qty_ts,
        'fd_pnl1_r': fd.pnl1_r,
        'fd_pnl1r': fd.pnl1r,
        'fd_pnl2r': fd.pnl2r,
        'fd_mensaje': fd.mensaje,
        
             
    })


@app.route('/precio') #Separo el precio para poder solicitarlo con intervalos menores
def precio():
    ticker = request.args.get("ticker").lower()
    rt  = getattr(main_loop, f"{ticker}rt")
    return jsonify({'Cprecio': rt.current_price })  


@app.route('/datos')
def datos():
    ticker = request.args.get("ticker").lower()
    ps  = getattr(main_loop, f"{ticker}ps")
    rt = getattr(main_loop, f"{ticker}rt")
    fd = getattr(main_loop, f"{ticker}fd")  
    
    return jsonify({
        'rt_BE_pos': rt.BE_pos,
        'rt_r_ts': rt.r_ts,
        'rt_r_1': rt.r_1 ,
        'rt_balance': round(rt.balance,2),
        'rt_posicion_porc': rt.posicion_porc,
        'rt_balance_vivo': round(rt.balance,2),
        'rt_pnl_vivo': rt.pnl_vivo,
        
    })


@app.route('/datos_PControl') #Datos para el panel de control de index
def datos_PControl():
    resultado = {}

    for ticker in symbol_list: 
        ps  = getattr(main_loop, f"{ticker}ps")
        rt = getattr(main_loop, f"{ticker}rt")
        fd = getattr(main_loop, f"{ticker}fd")  

        resultado[ticker] = {
            'fd_r0': fd.r0,
            'Cprecio': rt.current_price,
            'rt_posicion_porc': rt.posicion_porc,
            'rt_pnl_vivo': rt.pnl_vivo,
            'rt_BE_pos': rt.BE_pos,
            'ps_USDT1r': ps.USDT1r,
            'rt_balance': round(rt.balance,2),
            'rt_ALGO_pos': rt.ALGO_pos,
            'fd_fechainicio': fd.fechainicio,
            'ps_estado_soket': ps.estado_soket,
                 
        }       
    return jsonify(resultado)


@app.route('/stopsocket')
async def detener_socket():  
    ticker = request.args.get("ticker").lower()
    ps  = getattr(main_loop, f"{ticker}ps")
    rt = getattr(main_loop, f"{ticker}rt")
    fd = getattr(main_loop, f"{ticker}fd")  
    rt.detener_cm = True
    await main_loop.detener_socket(ticker, ps, fd, rt)
    main_loop.var_restart([ticker]) 
    ps = getattr(main_loop, f"{ticker}ps")
    ps.reset()

    return Response(status=204) 


@app.route('/analisis')
def analisis_open():
    return render_template('analisis.html')

@app.route('/analisis_symbol')
def analisis_symbol():
    return render_template('analisis_symbol.html')
    
@app.route('/mainstart', methods=['POST'])
def start_trading():
    ticker = request.form.get("ticker").lower()
    ps = getattr(main_loop, f"{ticker}ps")  
    ps.USDT1r = float(request.form.get('USDT1r'))
    ps.p2r = float(request.form.get('p2r'))
    ps.estado_soket = True    
    
    if (request.form.get('send')) == 'iniciar': main_loop.iniciar_socket_async(ticker)

    return Response(status=204) 




class NoisyRequestFilter(logging.Filter): #Filtro del log para que no muestre determinados mensajes
    def filter(self, record):
        msg = record.getMessage()
        if "GET" in msg or "POST" in msg:
            return False
        if "/datos" in msg or "/precio" in msg or re.search(r"registro_posiciones\w*\.csv", msg):
            return False
        return True
werkzeug_logger = logging.getLogger('werkzeug')
if not any(isinstance(f, NoisyRequestFilter) for f in werkzeug_logger.filters):
    werkzeug_logger.addFilter(NoisyRequestFilter())



################################ LECTURA DATABASE ################################
@app.route('/admin/download_db') #Descargar DB
def download_db():
    token = request.args.get("token")
    expected = os.getenv("ADMIN_TOKEN")
    if not expected or token != expected:
        abort(403)
    return send_file(DB_PATH, as_attachment=True, download_name="data.db")



@app.route('/movimientos') #Consulta para main_loop.html
def movimientos():
    ticker = (request.args.get("ticker") or "").lower().strip()
 
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id_order, type, pos, pe, sl, r1, r2, qty,
               v1r, pnl, balance, comision, time
        FROM movimientos
        WHERE lower(trim(symbol)) = lower(trim(?))
          AND id_pos = (
              SELECT MAX(id_pos)
              FROM movimientos
              WHERE lower(trim(symbol)) = lower(trim(?))
          )
        ORDER BY pk ASC
    """, (ticker, ticker))
    filas = cur.fetchall()
    conn.close()
 
    return jsonify([[("" if v is None else v) for v in fila] for fila in filas])



@app.route('/analisis_data') #Consulta para analisis.html
def analisis_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, id_pos, type, pos, time_open, time_close,
               pe, ps, v1r, resultado, secuencia
        FROM analisis
        ORDER BY pk ASC
    """)
    filas = cur.fetchall()
    conn.close()

    return jsonify([[("" if v is None else v) for v in fila] for fila in filas])

@app.route('/analisis_data_symbol') #Consulta para analisis_symbol.html
def analisis_data_symbol():
    ticker = (request.args.get("ticker") or "").lower().strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, id_pos, type, pos, time_open, time_close,
               pe, ps, v1r, resultado, secuencia
        FROM analisis
        WHERE lower(trim(symbol)) = ?
        ORDER BY pk ASC
    """, (ticker,))
    filas = cur.fetchall()
    conn.close()
    return jsonify([[("" if v is None else v) for v in fila] for fila in filas])


@app.route('/movimientos_all') #Consulta para analisis_symbol.html
def movimientos_all():
    ticker = (request.args.get("ticker") or "").lower().strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # id_order es índice 0, id_pos es índice 1
    cur.execute("""
        SELECT id_order, id_pos, type, pos, pe, sl, r1, r2, qty,
               v1r, pnl, balance, comision, time
        FROM movimientos
        WHERE lower(trim(symbol)) = ?
        ORDER BY CAST(id_pos AS INTEGER) ASC, pk ASC
    """, (ticker,))
    filas = cur.fetchall()
    conn.close()
    return jsonify([[("" if v is None else v) for v in fila] for fila in filas])


if __name__ == '__main__':
    daemon_thread = threading.Thread(target=iniciar_asyncio_orderupdate, daemon=True)
    daemon_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)


