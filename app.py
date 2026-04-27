from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory, Response
import threading
import re 
import asyncio
import logging
import os
import requests
import pandas as pd
import sqlite3

import main_loop
from core.orders import prueba_conexion



app=Flask(__name__)

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
        'fd_mensaje': fd.mensaje
             
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
        'precio_banda': fd.r0,
        
    })


@app.route('/datos_PControl') #Datos para el panel de control de index
def datos_PControl():
    # Lista de los tickers que manejas
    tickers = ["ethusdt", "btcusdt", "bnbusdt", "solusdt", "xrpusdt", "trxusdt", "avaxusdt", "tonusdt", "ltcusdt",
               "1000shibusdt", "dogeusdt","adausdt","xlmusdt","xmrusdt","dotusdt","uniusdt","aptusdt","nearusdt",
               "fetusdt","arbusdt","hyperusdt","suiusdt","bchusdt","linkusdt","hbarusdt","1000pepeusdt","aaveusdt",
               "taousdt","icpusdt","etcusdt","ondousdt", "kasusdt", "atomusdt", "vetusdt", "renderusdt", "enausdt", 
               "filusdt", "wldusdt", "algousdt", "qntusdt",
                "seiusdt", "jupusdt", "spxusdt", "injusdt", "tiausdt", "virtualusdt", "stxusdt", "opusdt", "penguusdt", "iotausdt",
                "imxusdt", "grtusdt", "ipusdt", "cakeusdt", "jtousdt", "crvusdt", "thetausdt", "ldousdt", "galausdt", "zecusdt"]
    resultado = {}

    for ticker in tickers:
        ps  = getattr(main_loop, f"{ticker}ps")
        rt = getattr(main_loop, f"{ticker}rt")
        fd = getattr(main_loop, f"{ticker}fd")  

        resultado[ticker] = {
            'fd_r0': fd.r0,
            'Cprecio': rt.current_price
                 
        }       
    return jsonify(resultado)


@app.route('/stopsocket')
async def detener_socket():  
    ticker = request.args.get("ticker").lower()
    main_loop.detener_socket(ticker)
    main_loop.var_restart([ticker]) #Llama al reset solo cuando se llama al endpoint desde el boton detener.
    ps = getattr(main_loop, f"{ticker}ps")

    return Response(status=204) 

@app.route('/socket_status')
def socket_status():
    return main_loop.symbol_status()


@app.route('/analisis')
def analisis_open():
    return render_template('analisis.html')
    

@app.route('/mainstart', methods=['POST'])
def start_trading():
    ticker = request.form.get("ticker").lower()
    ps = getattr(main_loop, f"{ticker}ps")  
    ps.USDT1r = float(request.form.get('USDT1r'))
    ps.p2r = float(request.form.get('p2r'))
    
    
    if (request.form.get('send')) == 'iniciar': main_loop.iniciar_socket_async(ticker)

    return Response(status=204) 


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
@app.route('/movimientos')
def movimientos():
    ticker = (request.args.get("ticker") or "").lower().strip()

    conn = sqlite3.connect("static/data/data.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT id_order, type, pe, sl, r0, r1, r2, qty,
               v1r, pnl, balance, comision, time
        FROM movimientos
        WHERE lower(trim(symbol)) = lower(trim(?))
        ORDER BY pk ASC
    """, (ticker,))
    filas = cur.fetchall()
    conn.close()

    return jsonify([[("" if v is None else v) for v in fila] for fila in filas])



@app.route('/analisis_data')
def analisis_data():
    conn = sqlite3.connect("static/data/data.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, estado, sl, time_open, time_close,
               pe, ps, vcierre, balance, resultado, secuencia
        FROM analisis
        ORDER BY pk ASC
    """)
    filas = cur.fetchall()
    conn.close()

    return jsonify([[("" if v is None else v) for v in fila] for fila in filas])



if __name__ == '__main__':
    t = threading.Thread(target=main_loop.iniciar_asyncio_loop)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True, use_reloader=False)



