from datetime import datetime
import time
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv

from core.dbfunc import write_db
from core.utils import restart_symbol, Qty_min
from core.orders import close_total, order_market, get_order_info


def Grid(ps, fd, rt):
    
    fd.perc2r = round(abs(ps.p2r - fd.r0) / fd.r0 * 100,4)
    fd.perc1r = round((fd.perc2r / 2),4)
    fd.perc1_r = round(-fd.perc1r,4)

    fd.mensaje = 'Aceptado'
    
    if fd.r0 < ps.p2r:
        fd.type_pos = 'LONG'
        fd.r_1 = round(fd.r0 * (1 - (fd.perc1r / 100)), fd.dec_precio)
        fd.r1 = round(fd.r0 * (1 + (fd.perc1r / 100)), fd.dec_precio)
        fd.r2 = round(fd.r0 * (1 + (fd.perc2r / 100)), fd.dec_precio)

    else:
        fd.type_pos = 'SHORT'
        fd.r_1 = round(fd.r0 * (1 + (fd.perc1r / 100)), fd.dec_precio)      
        fd.r1  = round(fd.r0 * (1 - (fd.perc1r / 100)), fd.dec_precio)     
        fd.r2  = round(fd.r0 * (1 - (fd.perc2r / 100)), fd.dec_precio)


    fd.Qty_mVar = round(ps.USDT1r / (fd.r0 - fd.r_1), fd.dec_qty)

    fd.Qty_r1 = round((fd.Qty_mVar / 2), fd.dec_qty)
    fd.Qty_r2 = round((fd.Qty_mVar / 4), fd.dec_qty)
    fd.Qty_ts = round((fd.Qty_mVar - fd.Qty_r1 - fd.Qty_r2), fd.dec_qty)

    fd.pnl1_r = round(((fd.r_1 - fd.r0 )* fd.Qty_mVar),4)
    fd.pnl1r = round(((fd.r1 - fd.r0 )* fd.Qty_r1),4)
    fd.pnl2r = round(((fd.r2 - fd.r0 )* fd.Qty_r2),4)
    
    print(fd.pnl1r)
    if (fd.Qty_r2 < fd.Qty_min):
        fd.control = False
        USDTmin = round(fd.Qty_min * (fd.r0 - fd.r_1),2)
        fd.mensaje = f'Cantidad minima no aceptada r1 {USDTmin}'

    
    '''
    - Comprar primero con Qty min si la fracmentacion se puede si no que no abra nada y tire mensaje.
    - Tiene que abrir las cuatro posiciones, y cuando se alcanze una ver como cancelar la otra, 
    asi como cuando alanza r1 borrrar el SL y poner el BE. 
    '''
    
# async def POs(i, ps, fds, fdl, rts, rtl, sd, symbol):

#     rts.control_pos[i] = True
#     rts.PE_Pos[i] = round(sd.current_price, sd.dec_precio)

#     if i == 2: rts.control_BE = True

#     sd.posicion = (f"PoS{i}")
#     rts.TP_Pos[i] = round(fds.step_valor[i] - (fds.Po_valor[i] - rts.PE_Pos[i]), sd.dec_precio)  #Primer calculo para definir el recupero (luego lo recalculara en base a el precio que realmente entre)

#     if i == 5: limite_inferior = rts.TP_Pos[i]
#     else: limite_inferior = fds.limite_inferior

#     rts.Qty_USDT_SubPosicion[i] = round(fds.PF_esperado[i] / ((rts.PE_Pos[i]  - limite_inferior) / rts.PE_Pos[i]), 2) #el segundo termino de la division es el recorrido_perc[1] pero calculado en el PE
    
#     SumatoriaProm = 0 #Para simular el Precio promedio 
#     for k in range(1, 8):
#         SumatoriaProm += round(rts.Qty_mVar[k], sd.dec_qty)
        
#     rts.Qty_mVar[i] = round(rts.Qty_USDT_SubPosicion[i] / rts.PE_Pos[i], sd.dec_qty)

#     Calculo_PP_simulacion = False
#     if rts.PE_prom == 0:
#         rts.PE_prom = rts.PE_Pos[i]
#         Calculo_PP_simulacion = False       
#     else:      
#         PP_anterior = rts.PE_prom
#         Qtyprom = (SumatoriaProm * rts.PE_prom) + (rts.Qty_mVar[i] * rts.PE_Pos[i])
#         rts.PE_prom = Qtyprom / (SumatoriaProm + rts.Qty_mVar[i]) #Calculo parcial para calcular bien el recupero, luego sumarlo y hacer el PP correspondiente.
#         Calculo_PP_simulacion = True
    
#     Qty_To_Open = round(rts.Qty_mVar[i], sd.dec_qty) 
#     Qty_mvar = rts.Qty_mVar[i]

#     sd.id_posicion = sd.id_posicion + 1

#     rts.ComisionPo[i] = (Qty_To_Open * sd.current_price) * fds.Tasa_Comision

#     if Calculo_PP_simulacion:
#         rts.PE_prom = ((SumatoriaProm * PP_anterior ) + (Qty_To_Open * rts.PE_Pos[i])) / (SumatoriaProm + Qty_To_Open)
    
#     if not bt.status and not ps.simulacion: 
#         id_order = await order_market(symbol=symbol, side=SIDE_SELL, quantity=Qty_To_Open)
#         PE_order, pnl, Fee = await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1) #intenta cada un segundo hasta que tenga valor
#         rts.PE_prom = await get_prom_price(symbol)
#         rts.PE_Pos[i] = PE_order
#         sd.id_posicion = id_order
#         rts.ComisionPo[i] = Fee

#     #Reajuste en base al precio que en realidad entro. 
#     splittage = (fds.Po_valor[i] - rts.PE_Pos[i])  
#     if i == 1: rts.SL_Pos[i] = round(sd.precio_banda - splittage, sd.dec_precio) #Establece el TP y el SL en base al precio tomado, mueve el sl y el tp de igual manera que el PE
#     else: rts.SL_Pos[i] = round(fds.Po_valor[i-1] - splittage, sd.dec_precio)
#     rts.TP_Pos[i] = round(fds.step_valor[i] - splittage, sd.dec_precio)
    
#     ValorPuro_Tot(rtl, rts, sd)

#     sd.Bal_Pos = round(sd.Bal_Pos - rts.ComisionPo[i], 8)
    
#     wcsv.type_Pos = f"Po{i}S"
#     sd.secuencia += wcsv.type_Pos + " | "
#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         round(rts.SL_Pos[i], sd.dec_precio),
#         round(rts.PE_Pos[i], sd.dec_precio),   
#         round(rts.TP_Pos[i], sd.dec_precio),
#         "",
#         round(rts.Qty_USDT_SubPosicion[i], 2),
#         round(Qty_mvar, sd.dec_qty),
#         round(rts.PE_prom, sd.dec_precio),
#         round(Qty_To_Open, sd.dec_qty),
#         round(sd.Bal_Pos,8),
#         round(sd.ValorPuro_Tot, 2),
#         round(rts.ComisionPo[i], 8),
#         sd.fechayhora                     
#         ]
#     ]
#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)

# async def TPs(i, ps, fds, fdl, rts, rtl, sd, symbol):

#     rts.control_TP[i] = True
#     rts.PE_TP_Pos[i] = sd.current_price

#     ValorPuro_Tot(rtl, rts, sd)

#     if ps.simulacion: sd.id_posicion = sd.id_posicion + 1

#     if i != 1: 
#         rts.BE = fds.step_valor[i-1]
#         rts.control_BE = True
#     else: 
#         rts.BE = sd.precio_bandaShort #Lo crea para Po2 y cuadno abre la posicion ponemos true la bandera

#     resultado = 0
   
#     if i==5:
#         rts.Pnl_TP[i] = sd.ValorPuro_Tot
#         rts.ComisionTP[i] = round(rts.Pnl_TP[i] * fds.Tasa_Comision, 8)

#         if not ps.simulacion and not bt.status:
#             id_order = await close_total(symbol)
#             PE_order, pnl, Fee =  await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1)       
#             rts.PE_TP_Pos[i] = round(PE_order, sd.dec_precio) 
#             sd.id_posicion = id_order
#             rts.ComisionTP[i] = Fee
#             rts.Pnl_TP[i] = pnl
        
#         resultado = rts.Pnl_TP[i] - rts.ComisionSL[i] + sd.Bal_Pos 
#         sd.Bal_Pos += round(rts.Pnl_TP[i] - rts.ComisionTP[i], 8)

      
    
#     wcsv.type_Pos = f"TP{i}S"
#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         "",
#         round(rts.PE_TP_Pos[i], sd.dec_precio),
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         sd.fechayhora 
#         ]
#     ]
    
#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)
#     sd.secuencia += wcsv.type_Pos + " | "

#     if i == 5:
#         if bt.status: restart_symbol_backtest(symbol, wcsv.type_Pos, ps.input_sl, sd.fechainicio, sd.precio_banda, round(rts.PE_TP_Pos[i], sd.dec_precio), rts.Pnl_TP[i], sd.Bal_Pos, sd.secuencia, resultado)
#         else: await restart_symbol(symbol, wcsv.type_Pos, ps.input_sl, sd.fechainicio, sd.precio_banda, round(rts.PE_TP_Pos[i], sd.dec_precio), rts.Pnl_TP[i], sd.Bal_Pos, sd.secuencia, resultado, ps)

# async def SLs(i, ps, fds, fdl, rts, rtl, sd, symbol):

#     rts.PE_SL_Pos[i] = sd.current_price 
#     Qty_To_Close = round(rts.Qty_mVar[i], sd.dec_qty)  #Si paso por el TP la Qty_mVar1_rec va a ser cero y va a cerrar solo la parte pura, en el SL debe quedar todo cerrado.

#     rts.PnL_SL[i] =  round((Qty_To_Close * rts.PE_prom) - (Qty_To_Close * rts.PE_SL_Pos[i]), 2) #Calcula la perdida de la posicion abierta que se esta cerrando
    
#     rts.ComisionSL[i] = round((Qty_To_Close * rts.PE_SL_Pos[i]) * fds.Tasa_Comision, 8)
    
#     ValorPuro_Tot(rtl, rts, sd)

#     sd.id_posicion = sd.id_posicion + 1
   
#     sd.posicion = 'SL'
#     rts.PE_prom = 0

#     Bal_Pos_Control = sd.Bal_Pos + rts.PnL_SL[i]
  
#     if not ps.simulacion and not bt.status: #obtener el Qty_to close aca, para que cierre todo y no tener que calcularlo
#         id_order = await close_total(symbol)
#         PE_order, pnl, Fee =  await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1)
#         rts.PE_SL_Pos[i] = PE_order
#         sd.id_posicion = id_order
#         rts.ComisionSL[i] = Fee
#         rts.PnL_SL[i] = pnl
#     else:
#         sd.Bal_Pos += round(rts.PnL_SL[i] - rts.ComisionSL[i], 8)

#     resultado = rts.PnL_SL[i] - rts.ComisionSL[i] + sd.Bal_Pos
    
#     Pnl_SLs = rts.PnL_SL[i]
   
#     wcsv.type_Pos = f"SL{i}S"
#     sd.secuencia += wcsv.type_Pos + " | "
#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         "",
#         round(rts.PE_SL_Pos[i], sd.dec_precio),
#         "",
#         round(rts.PnL_SL[i], 2),
#         "",  
#         round(rts.Qty_mVar[i], sd.dec_qty),
#         "",
#         round(Qty_To_Close, sd.dec_qty),
#         round(sd.Bal_Pos, 8),
#         round(sd.ValorPuro_Tot, 2),
#         round(rts.ComisionSL[i], 8),
#         sd.fechayhora 
#         ]
#     ]
#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)
   
   
#     max_index = ps.input_niveles if ps.input_niveles > 5 else 5
#     for vp in range(1, max_index + 1):
#         rts.control_pos[vp] = False
#         rts.control_TP[vp] = False
#         rts.Qty_mVar[vp] = 0
#         rts.Pnl_TP[vp] = 0
#         rts.PnL_SL[vp] = 0
#     rts.PE_prom = 0
   

# async def POl(i, ps, fds, fdl, rts, rtl, sd, symbol):

#     rtl.control_pos[i] = True
#     rtl.PE_Pos[i] = round(sd.current_price, sd.dec_precio) 

#     if i == 2: rtl.control_BE = True
    
#     sd.posicion = (f"PoL{i}")
#     rtl.TP_Pos[i] = round(fdl.step_valor[i] + (rtl.PE_Pos[i] - fdl.Po_valor[i]) , sd.dec_precio) #Primer calculo para definir el recupero (luego lo recalculara en base a el precio que realmente entre)

#     if i == 5: limite_superior = rtl.TP_Pos[i] #Para evitar que sean iguales o mayor en un salto.
#     else: limite_superior = fdl.limite_superior
        
#     rtl.Qty_USDT_SubPosicion[i] = round(fdl.PF_esperado[i] / abs(((rtl.PE_Pos[i]  - limite_superior) / rtl.PE_Pos[i])), 2) #el segundo termino de la division es el recorrido_perc[1] pero calculado en el PE
    
#     SumatoriaProm = 0
#     for k in range(1, 8):
#         SumatoriaProm += round(rtl.Qty_mVar[k], sd.dec_qty)
    
#     rtl.Qty_mVar[i] = round(rtl.Qty_USDT_SubPosicion[i] / rtl.PE_Pos[i], sd.dec_qty)

#     Calculo_PP_simulacion = False
#     if rtl.PE_prom == 0:
#         rtl.PE_prom = rtl.PE_Pos[i]
#         Calculo_PP_simulacion = False 
#     else: 
#         PP_anterior = rtl.PE_prom
#         Qtyprom = (SumatoriaProm * rtl.PE_prom) + (rtl.Qty_mVar[i] * rtl.PE_Pos[i])
#         rtl.PE_prom = Qtyprom / (SumatoriaProm + rtl.Qty_mVar[i])
#         Calculo_PP_simulacion = True

#     Qty_To_Open = round(rtl.Qty_mVar[i], sd.dec_qty) 
#     Qty_mvar = rtl.Qty_mVar[i]

#     sd.id_posicion = sd.id_posicion + 1

#     rtl.ComisionPo[i] = (Qty_To_Open * sd.current_price) * fds.Tasa_Comision

#     if Calculo_PP_simulacion:
#         rtl.PE_prom = ((SumatoriaProm * PP_anterior ) + (Qty_To_Open * rtl.PE_Pos[i])) / (SumatoriaProm + Qty_To_Open)
    
    
#     if not bt.status and not ps.simulacion:
#         id_order = await order_market(symbol=symbol, side=SIDE_BUY, quantity=Qty_To_Open)
#         PE_order, pnl, Fee = await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1)
#         rtl.PE_prom = await get_prom_price(symbol)
#         rtl.PE_Pos[i] = PE_order
#         sd.id_posicion = id_order
#         rtl.ComisionPo[i] = Fee

#     #Reajuste en base al precio que en realidad entro.
#     splittage = (rtl.PE_Pos[i] - fdl.Po_valor[i])
#     if i == 1: rtl.SL_Pos[i] = round(sd.precio_banda + splittage, sd.dec_precio) #Establece el TP y el SL en base al precio tomado, mueve el sl y el tp de igual manera que el PE
#     else: rtl.SL_Pos[i] = round(fdl.Po_valor[i-1] + splittage, sd.dec_precio)
#     rtl.TP_Pos[i] = round(fdl.step_valor[i] + splittage, sd.dec_precio)

#     ValorPuro_Tot(rtl, rts, sd)

#     sd.Bal_Pos = round(sd.Bal_Pos - rtl.ComisionPo[i], 8)

#     wcsv.type_Pos = f"Po{i}L"
#     sd.secuencia += wcsv.type_Pos + " | "
#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         round(rtl.SL_Pos[i], sd.dec_precio),
#         round(rtl.PE_Pos[i], sd.dec_precio),   
#         round(rtl.TP_Pos[i], sd.dec_precio),
#         "",
#         round(rtl.Qty_USDT_SubPosicion[i], 2),
#         round(Qty_mvar, sd.dec_qty),
#         round(rtl.PE_prom, sd.dec_precio),
#         round(Qty_To_Open, sd.dec_qty),
#         round(sd.Bal_Pos, 8),
#         round(sd.ValorPuro_Tot, 2),
#         round(rtl.ComisionPo[i], 8),
#         sd.fechayhora                    
#         ]
#     ]
#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)

# async def TPl(i, ps, fds, fdl, rts, rtl, sd, symbol):

#     rtl.control_TP[i] = True
#     rtl.PE_TP_Pos[i] = sd.current_price

#     ValorPuro_Tot(rtl, rts, sd)

#     if ps.simulacion: sd.id_posicion = sd.id_posicion + 1

#     if i != 1: 
#         rtl.BE = fdl.step_valor[i-1]
#         rtl.control_BE = True
#     else:
#         rtl.BE = sd.precio_bandaLong

#     resultado = 0

#     if i==5:
#         rtl.Pnl_TP[i] = round(sd.ValorPuro_Tot - rtl.ComisionPo[i], 2)
#         rtl.ComisionTP[i] = round(rtl.Pnl_TP[i] * fds.Tasa_Comision, 8)
        
#         if not ps.simulacion and not bt.status:
#             id_order = await close_total(symbol)
#             PE_order, pnl, Fee = await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1)       
#             rtl.PE_TP_Pos[i] = round(PE_order, sd.dec_precio) 
#             sd.id_posicion = id_order
#             rtl.ComisionTP[i] = Fee
#             rtl.Pnl_TP[i] = pnl
 
#         resultado = rtl.Pnl_TP[i] - rtl.ComisionTP[i] + sd.Bal_Pos
#         sd.Bal_Pos += round(rtl.Pnl_TP[i] - rtl.ComisionPo[i], 8)

    

#     wcsv.type_Pos = f"TP{i}L"
#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         "",
#         round(rtl.PE_TP_Pos[i], sd.dec_precio),
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         "",
#         "", 
#         sd.fechayhora 
#         ]
#     ]
        
#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)
#     sd.secuencia += wcsv.type_Pos + " | "

#     if i == 5:
#         if bt.status: restart_symbol_backtest(symbol, wcsv.type_Pos, ps.input_sl, sd.fechainicio, sd.precio_banda, round(rts.PE_TP_Pos[i], sd.dec_precio), rtl.Pnl_TP[i], sd.Bal_Pos, sd.secuencia, resultado)
#         else: await restart_symbol(symbol, wcsv.type_Pos, ps.input_sl, sd.fechainicio, sd.precio_banda, round(rts.PE_TP_Pos[i], sd.dec_precio), rtl.Pnl_TP[i], sd.Bal_Pos, sd.secuencia, resultado, ps)

# async def SLl(i, ps, fds, fdl, rts, rtl, sd, symbol):
   
#     rtl.PE_SL_Pos[i] = sd.current_price 
#     Qty_To_Close = round(rtl.Qty_mVar[i], sd.dec_qty) #Si paso por el TP la Qty_mVar1_rec va a ser cero y va a cerrar solo la parte pura, en el SL debe quedar todo cerrado.
    
#     rtl.PnL_SL[i] = round((Qty_To_Close * rtl.PE_SL_Pos[i]) - (Qty_To_Close * rtl.PE_prom),2)  #Calcula la perdida de la posicion abierta que se esta cerrando
    
#     rtl.ComisionSL[i] = round((Qty_To_Close * rtl.PE_SL_Pos[i]) * fds.Tasa_Comision, 8)
    
#     ValorPuro_Tot(rtl, rts, sd)

#     sd.id_posicion = sd.id_posicion + 1
   
#     sd.posicion = 'SL'
#     rtl.PE_prom = 0

#     Bal_Pos_Control = sd.Bal_Pos + rtl.PnL_SL[i]

#     if not ps.simulacion and not bt.status:
#         id_order = await close_total(symbol)
#         PE_order, pnl, Fee = await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1)
#         rtl.PE_SL_Pos[i] = PE_order
#         sd.id_posicion = id_order
#         rtl.ComisionSL[i] = Fee
#         rtl.PnL_SL[i] = pnl
#     else:
#         sd.Bal_Pos += round(rtl.PnL_SL[i] - rtl.ComisionPo[i], 8)

#     resultado = rtl.PnL_SL[i] - rtl.ComisionSL[i] + sd.Bal_Pos

#     Pnl_SLl = rtl.PnL_SL[i]
    

#     wcsv.type_Pos = f"SL{i}L"
#     sd.secuencia += wcsv.type_Pos + " | "
#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         "",
#         round(rtl.PE_SL_Pos[i], sd.dec_precio),
#         "",
#         round(rtl.PnL_SL[i], 2),
#         "",  
#         round(rtl.Qty_mVar[i], sd.dec_qty),
#         "",
#         round(Qty_To_Close, sd.dec_qty),
#         round(sd.Bal_Pos, 8),
#         round(sd.ValorPuro_Tot, 2),
#         round(rtl.ComisionSL[i], 8),
#         sd.fechayhora    
#         ]
#     ]
#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)
   
#     max_index = ps.input_niveles if ps.input_niveles > 5 else 5
#     for vp in range(1, max_index + 1):
#         rtl.control_pos[vp] = False
#         rtl.control_TP[vp] = False
#         rtl.Qty_mVar[vp] = 0
#         rtl.Pnl_TP[vp] = 0
#         rtl.PnL_SL[vp] = 0
#     rtl.PE_prom = 0


# async def BE(i, ps, fds, fdl, rts, rtl, sd, symbol):
 
#     sd.id_posicion = sd.id_posicion + 1
#     ValorPuro_Tot(rtl, rts, sd)  

#     if not ps.simulacion:
#         id_order = await close_total(symbol)
#         PE_order, pnl, Fee = await get_order_info(symbol, id_order, max_attempts=10, wait_seconds=1)
#         sd.id_posicion = id_order 
#         sd.PnL_BE = pnl
#         sd.Fee_BE = abs(Fee)
#     else:
#         sd.PnL_BE = sd.ValorPuro_Tot 
#         sd.Fee_BE =  abs((sd.Qty_Mvar_control * sd.current_price) * fds.Tasa_Comision)


#     valorcierre = sd.PnL_BE - sd.Fee_BE
#     resultado = sd.PnL_BE - sd.Fee_BE + sd.Bal_Pos
    
#     wcsv.type_Pos = f"BE"
#     sd.secuencia += wcsv.type_Pos + " | "

#     Data_csv = [
#         [
#         str(sd.id_posicion).zfill(11),
#         wcsv.type_Pos,
#         "",
#         sd.current_price,
#         "",
#         round(sd.PnL_BE, 2),
#         "",
#         round(sd.Qty_Mvar_control, sd.dec_qty),
#         "",
#         "",
#         round(sd.Bal_Pos, 8),
#         round(sd.ValorPuro_Tot, 2),
#         round(sd.Fee_BE, 8),
#         sd.fechayhora 
#         ]
#     ]

#     if bt.status: write_csv_bt(Data_csv, symbol)
#     else: write_db(Data_csv, symbol, ps.input_sl)
#     if bt.status: restart_symbol_backtest(symbol, wcsv.type_Pos, ps.input_sl, sd.fechainicio, sd.precio_banda, round(sd.current_price, sd.dec_precio), sd.ValorPuro_Tot , sd.Bal_Pos, sd.secuencia, resultado)
#     else: await restart_symbol(symbol, wcsv.type_Pos, ps.input_sl, sd.fechainicio, sd.precio_banda, sd.current_price, valorcierre, sd.Bal_Pos, sd.secuencia, resultado, ps)
    
async def Steps_S(ps, fd, rt, symbol):
    # sd.contador = sd.contador + 1  
    # if sd.current_price >= rts.SL_Pos[1] and rts.control_pos[1]: 
    #         await SLs(1,ps, fds, fdl, rts, rtl, sd, symbol)
    # max_indexS = ps.input_niveles if ps.input_niveles > 5 else 5
    # for i in range(1, max_indexS + 1):
        
    #     if (sd.current_price <= fds.Po_valor[i] and not rts.control_pos[i]): 
    #         await POs(i,ps, fds, fdl, rts, rtl, sd, symbol)                               
    #     if sd.current_price <= rts.TP_Pos[i] and not rts.control_TP[i] and rts.control_pos[i]: 
    #         await TPs(i,ps, fds, fdl, rts, rtl, sd, symbol)

    # if (sd.current_price >= rts.BE) and rts.control_BE: 
    #     await BE(1, ps, fds, fdl, rts, rtl, sd, symbol)
    return

async def Steps_L(ps, fd, rt, symbol):
    # if sd.current_price <= rtl.SL_Pos[1] and rtl.control_pos[1]:
    #     await SLl(1, ps, fds, fdl, rts, rtl, sd, symbol)

    # max_indexL = ps.input_niveles if ps.input_niveles > 5 else 5
    # for i in range(1, max_indexL + 1):
    #     if (sd.current_price >= fdl.Po_valor[i] and not rtl.control_pos[i]):
    #         await POl(i, ps, fds, fdl, rts, rtl, sd, symbol)
    #     if sd.current_price >= rtl.TP_Pos[i] and not rtl.control_TP[i] and rtl.control_pos[i]:
    #         await TPl(i, ps, fds, fdl, rts, rtl, sd, symbol)

    # if (sd.current_price <= rtl.BE) and rtl.control_BE:  
    #     await BE(1, ps, fds, fdl, rts, rtl, sd, symbol)
    return
    

# def ValorPuro_Tot(rtl, rts, sd): 
#     rtl.ValorPuro_Tot = 0
#     rts.ValorPuro_Tot = 0
#     sd.ValorPuro_Tot = 0
#     sd.Qty_Mvar_control = 0
#     for vp in range(1, 8):
        
#         if rts.control_pos[vp]:
#              rts.ValorPuro_Pos[vp] = ((rts.Qty_mVar[vp]) * rts.PE_prom) - ((rts.Qty_mVar[vp]) * sd.current_price)
#              sd.Qty_Mvar_control += rts.Qty_mVar[vp]
#         else: rts.ValorPuro_Pos[vp] = 0 
#         rts.ValorPuro_Tot += rts.ValorPuro_Pos[vp]
        
#         if rtl.control_pos[vp]:
#             rtl.ValorPuro_Pos[vp] = ((rtl.Qty_mVar[vp]) * sd.current_price) - ((rtl.Qty_mVar[vp]) * rtl.PE_prom)
#             sd.Qty_Mvar_control += rtl.Qty_mVar[vp]
#         else: rtl.ValorPuro_Pos[vp] = 0 
#         rtl.ValorPuro_Tot += rtl.ValorPuro_Pos[vp]

#     sd.ValorPuro_Tot = round(rtl.ValorPuro_Tot + rts.ValorPuro_Tot, 2)

