import sqlite3

from core.dbfunc import write_db, write_analisis_db, DB_PATH
from core.orders import close_total, order_market, get_order_info, order_tp_market, order_sl_stop_market, cancel_algo_order


async def Grid(symbol, ps, fd, rt):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id_pos FROM movimientos WHERE symbol = ? ORDER BY pk DESC LIMIT 1", (symbol,))
    row = cur.fetchone()
    conn.close()
    if row and row[0]: fd.id_pos = int(row[0]) + 1
    else: fd.id_pos = 1
    
    fd.perc2r = round(abs(ps.p2r - fd.r0) / fd.r0 * 100,4)
    fd.perc1r = round((fd.perc2r / 2),4)
    fd.perc1_r = round(-fd.perc1r,4)

    fd.mensaje = 'Aceptado'
    rt.BE_pos = -1
    rt.ALGO_pos = 'R0'
    
    if fd.r0 < ps.p2r:
        fd.type_pos = 'LONG'
        fd.r_1 = round(fd.r0 * (1 - (fd.perc1r / 100)), fd.dec_precio)
        fd.r1 = round(fd.r0 * (1 + (fd.perc1r / 100)), fd.dec_precio)
        fd.r2 = round(fd.r0 * (1 + (fd.perc2r / 100)), fd.dec_precio)
        fd.dist_1r = fd.r0 - fd.r_1
        rt.r_ts = round(fd.r2 + fd.dist_1r, fd.dec_precio)   
        side_open = 'BUY'
        fd.side_close = 'SELL'
    else:
        fd.type_pos = 'SHORT'
        fd.r_1 = round(fd.r0 * (1 + (fd.perc1r / 100)), fd.dec_precio)      
        fd.r1  = round(fd.r0 * (1 - (fd.perc1r / 100)), fd.dec_precio)     
        fd.r2  = round(fd.r0 * (1 - (fd.perc2r / 100)), fd.dec_precio)
        fd.dist_1r = fd.r_1 - fd.r0
        rt.r_ts = round(fd.r2 - fd.dist_1r, fd.dec_precio)
        side_open = 'SELL'
        fd.side_close = 'BUY'

    fd.Qty_mVar = round(ps.USDT1r / abs(fd.r0 - fd.r_1), fd.dec_qty)
    

    if ((fd.Qty_mVar / 4) < fd.Qty_min):
        fd.control = False
        USDTmin = round((fd.Qty_min * (fd.r0 - fd.r_1))*4,2)
        fd.mensaje = f'Cantidad minima no aceptada minimo: {USDTmin}'

    if fd.control:
        id_order_r0 = await order_market(symbol, side_open, 0.20, False) #teast rapido
        #id_order_r0 = await order_market(symbol, side_open, fd.Qty_mVar, False)
        PE_order, pnl, Fee, qty = await get_order_info(symbol, id_order_r0, max_attempts=10, wait_seconds=1) 
        fd.r0 = round(PE_order, fd.dec_precio)
        rt.comision = Fee

        if fd.r0 < ps.p2r: #long
            splittage = PE_order - fd.r0
            fd.r_1 = round(fd.r_1 + splittage, fd.dec_precio)
            fd.r1 = round(fd.r1 + splittage, fd.dec_precio)
            fd.r2 = round(fd.r2 + splittage, fd.dec_precio)
        else: #short
            splittage = fd.r0 - PE_order
            fd.r_1 = round(fd.r_1 - splittage, fd.dec_precio)
            fd.r1  = round(fd.r1 - splittage, fd.dec_precio) 
            fd.r2  = round(fd.r2 - splittage, fd.dec_precio)

        fd.Qty_r1 = round((fd.Qty_mVar / 2), fd.dec_qty)
        fd.Qty_r2 = round((fd.Qty_mVar / 4), fd.dec_qty)
        fd.Qty_ts = round((fd.Qty_mVar - fd.Qty_r1 - fd.Qty_r2), fd.dec_qty)

        fd.pnl1_r = round(((fd.r_1 - fd.r0 )* fd.Qty_mVar),4)
        fd.pnl1r = round(((fd.r1 - fd.r0 )* fd.Qty_r1),4)
        fd.pnl2r = round(((fd.r2 - fd.r0 )* fd.Qty_r2),4)

        rt.balance -= rt.comision
        rt.secuencia += 'R0' + " | "
        Data_db= [
            [
            id_order_r0,
            fd.id_pos,
            fd.type_pos,
            'R0',
            round(fd.r0, fd.dec_precio),
            round(fd.r_1, fd.dec_precio),   
            round(fd.r1, fd.dec_precio),
            round(fd.r2, fd.dec_precio),
            round(fd.Qty_mVar, fd.dec_qty),
            ps.USDT1r,
            '',
            round(rt.balance, 8),
            round(rt.comision, 8),
            rt.fechayhora                     
            ]
        ]
        write_db(Data_db, symbol)
        
        rt.balance -= rt.comision


        # if fd.type_pos == 'SHORT': #TEST RAPIDO
        #     fd.r_1 = round(fd.r0 * 1.0005, fd.dec_precio)
        #     fd.r1 = round(fd.r0 * 0.9995, fd.dec_precio)
        #     fd.r2 = round(fd.r0 * 0.9990, fd.dec_precio)
        # else:
        #     fd.r_1 = round(fd.r0 * 0.9995, fd.dec_precio)
        #     fd.r1 = round(fd.r0 * 1.0005, fd.dec_precio)
        #     fd.r2 = round(fd.r0 * 1.0010, fd.dec_precio)       
        # rt.id_order_r1 = await order_tp_market(symbol, fd.side_close, 0.10, fd.r1)
        # rt.id_order_r2 = await order_tp_market(symbol, fd.side_close, 0.05, fd.r2)
        # rt.id_order_r_1 = await order_sl_stop_market(symbol, fd.side_close, fd.r_1)

        rt.id_order_r1 = await order_tp_market(symbol, fd.side_close, fd.Qty_r1, fd.r1)
        rt.id_order_r2 = await order_tp_market(symbol, fd.side_close, fd.Qty_r2, fd.r2)
        rt.id_order_r_1 = await order_sl_stop_market(symbol, fd.side_close, fd.r_1)


async def r1_r2(symbol, ps, fd, rt):
    if rt.r1_active:
        rt.ALGO_pos = 'R1'
        cancel_algo_order(symbol, rt.id_order_r_1)
        rt.r_1 = fd.r0
        rt.id_order_r_1 = await order_sl_stop_market(symbol, fd.side_close, rt.r_1)
        rt.BE_pos +=1 #vale 0
        rt.r1_active = False
        fd.Qty_r1 = 0
    elif rt.r2_active:       
        rt.ALGO_pos = 'R2'
        cancel_algo_order(symbol, rt.id_order_r_1)  
        rt.r_1 = fd.r1    
        rt.id_order_r_1 = await order_sl_stop_market(symbol, fd.side_close, rt.r_1)
        rt.BE_pos += 1 #vale 1
        rt.r2_active = False
        fd.Qty_r2 = 0
         

    rt.secuencia += rt.ALGO_pos + " | "

    rt.balance += (rt.ALGO_pnl - rt.AlGO_comision)

    Data_db= [
            [
            rt.ALGO_orderid,
            fd.id_pos,
            fd.type_pos,
            rt.ALGO_pos,
            round(rt.ALGO_PE, fd.dec_precio),
            '',   
            '',
            '',
            round(rt.ALGO_QtymVar, fd.dec_qty),
            '',
            round(rt.ALGO_pnl, 4),
            round(rt.balance, 8),
            round(rt.AlGO_comision, 8),
            rt.fechayhora                     
            ]
        ]
    write_db(Data_db, symbol)

async def r_ts(symbol, ps, fd, rt):
    print("R_TS")
    if fd.type_pos == 'LONG':
        rt.r_1 = round(rt.r_ts - fd.dist_1r, fd.dec_precio)
        rt.r_ts += round(fd.dist_1r, fd.dec_precio)

    elif fd.type_pos == 'SHORT':
        rt.r_1 = round(rt.r_ts + fd.dist_1r, fd.dec_precio)
        rt.r_ts -= round(fd.dist_1r, fd.dec_precio)

    rt.BE_pos += 1
    rt.ALGO_pos = 'TS'

    cancel_algo_order(symbol, rt.id_order_r_1)
    rt.id_order_r_1 = await order_sl_stop_market(symbol, fd.side_close, rt.r_1)

async def r_1(symbol, ps, fd, rt):

    if rt.detener_cm: #detener soket
        id_order = cancel_algo_order(symbol, rt.id_order_r_1)       
        id_order_cm = await close_total(symbol)
        PE_order, pnl, Fee, qty = await get_order_info(symbol, id_order_cm, max_attempts=10, wait_seconds=1)
        rt.ALGO_orderid = id_order_cm
        rt.ALGO_PE = PE_order
        rt.ALGO_pnl = pnl
        rt.AlGO_comision = Fee
        rt.ALGO_QtymVar = qty
        ALGO_pos = 'CM' 
    else:
        if rt.BE_pos == -1: 
            ALGO_pos = 'SL'
        else:
            ALGO_pos = f'BE{rt.BE_pos}'

    rt.balance += (rt.ALGO_pnl - rt.AlGO_comision)
    rt.secuencia += ALGO_pos + " | "

    Data_db= [
            [
            rt.ALGO_orderid,
            fd.id_pos,
            fd.type_pos,
            ALGO_pos,
            round(rt.ALGO_PE, fd.dec_precio),
            '',  
            '',
            '',
            round(rt.ALGO_QtymVar, fd.dec_qty),
            '',
            round(rt.ALGO_pnl, 4),
            round(rt.balance, 8),
            round(rt.AlGO_comision, 8),
            rt.fechayhora                     
            ]
        ]
    write_db(Data_db, symbol)

    write_analisis_db(
        symbol      = symbol,
        id_pos      = fd.id_pos,
        type_pos    = fd.type_pos,
        pos         = ALGO_pos,
        time_open   = fd.fechainicio,
        time_close  = rt.fechayhora,
        pe          = fd.r0,
        ps          = rt.ALGO_PE,
        v1r         = ps.USDT1r,
        resultado   = round(rt.balance, 4),
        secuencia   = rt.secuencia,
    )

    cancel_algo_order(symbol, rt.id_order_r1)
    cancel_algo_order(symbol, rt.id_order_r2)

    rt.r_1_active = False

async def metrics(symbol, ps, fd, rt):
    
    #distancia porcentual desde r0 para Pcontrol.
    if rt.BE_pos == -1 and ((fd.r1 - fd.r0) != 0): 
        rt.posicion_porc = round((((rt.current_price - fd.r0) / (fd.r1 - fd.r0)) * 100),2)
    elif ((fd.r1 - rt.r_1) != 0): 
        rt.posicion_porc = round((((rt.current_price - rt.r_1) / (fd.r1 - rt.r_1)) * 100),2)

    #pnl vivo
    if fd.type_pos == 'LONG':
        rt.pnl_vivo = round((rt.current_price - fd.r0) * (fd.Qty_r1 + fd.Qty_r2 + fd.Qty_ts), 2)
    elif fd.type_pos == 'SHORT':
        rt.pnl_vivo = round((fd.r0 - rt.current_price) * (fd.Qty_r1 + fd.Qty_r2 + fd.Qty_ts), 2)

    rt.balance_vivo = rt.balance + rt.pnl_vivo


async def Steps(ps, fd, rt, symbol):
    if fd.control:
        if rt.r1_active or rt.r2_active:
            await r1_r2(symbol, ps, fd, rt)
        if rt.r_1_active:
            await r_1(symbol, ps, fd, rt)

        if fd.type_pos == 'LONG':
            if rt.current_price >= rt.r_ts:
                await r_ts(symbol, ps, fd, rt)
        elif fd.type_pos == 'SHORT':
            if rt.current_price <= rt.r_ts:
                await r_ts(symbol, ps, fd, rt)

        await metrics(symbol, ps, fd, rt)
    
    return


    


