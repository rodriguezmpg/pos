
class DataPost: 
    def reset(self):
        self.__init__()
    def __init__(self):       
        self.p2r = 0.00
        self.USDT1r = 0
        self.estado_soket = False

        
        
class FixedData: 
    def reset(self):
        self.__init__()
    def __init__(self):
        self.fechainicio = None       
        self.type_pos = ''
        self.control = True
        self.mensaje = ''
        self.id_order = 0
        self.side_close = ''

        self.Qty_min = 0
        self.dec_precio = 0
        self.dec_qty = 0

        self.perc1r = 0.00
        self.perc2r = 0.00
        self.perc1_r = 0.00

        self.r_1 = 0.00
        self.r0 = 0.00
        self.r1 = 0.00
        self.r2 = 0.00
       
        self.dist_1r = 0.00

        self.Qty_r1 = 0.00
        self.Qty_r2 = 0.00
        self.Qty_ts = 0.00

        self.pnl1_r = 0.00
        self.pnl1r = 0.00
        self.pnl2r = 0.00

        self.Qty_mVar = 0.00
        


class RealTime:
    def reset(self):
        self.__init__()
    def __init__(self):
        self.current_price = 0.00
        self.previous_price = 0.00
        self.fechayhora = None
        self.secuencia = ''

        self.detener_cm = False #Detener soket

        self.balance = 0.00

        self.comision = 0.00

        self.BE_pos = 0

        self.r_1 = 0.00

        self.r1_active = False
        self.r2_active = False
        self.r_1_active = False
        self.r_ts = 0.00

        self.ALGO_orderid = 0
        self.ALGO_pnl = 0.00
        self.AlGO_comision = 0.00
        self.ALGO_QtymVar = 0.00
        self.ALGO_PE = 0.00        

        self.id_order_r1 = None
        self.id_order_r2 = None
        self.id_order_r_1 = None

        #Variables financieras
        self.posicion_porc = 0.00
        self.pnl_vivo = 0.00
        self.ALGO_pos = ''
        self.balance_vivo = 0.00

        self.capital = 5000


class Global:
    def reset(self):
        self.__init__()

    def __init__(self):
        self.capital = 5000

        
        self.usdt1r       = 0.0
        self.pnl_vivo     = 0.0
        self.balance      = 0.0
        self.sokets_activos      = 0   
        self.capital_arriesgado = 0
        self.disponible_operar = 0.00 
        self.balance_vivo = 0.00             

    def recalcular(self, symbol_list, main_loop):
        self.usdt1r        = 0.0
        self.pnl_vivo      = 0.0
        self.balance       = 0.0
        self.sokets_activos       = 0
        self.capital_arriesgado = 0
        self.disponible_operar = 0.00
        self.balance_vivo = 0.00 

        for symbol in symbol_list:
            ps = getattr(main_loop, f"{symbol}ps")
            rt = getattr(main_loop, f"{symbol}rt")
            fd = getattr(main_loop, f"{symbol}fd")  
            
            if not ps.estado_soket:
                continue
          
            
            if rt.BE_pos == -1:
                self.usdt1r  += ps.USDT1r  
                             
            self.pnl_vivo += rt.pnl_vivo
            self.balance += rt.balance
            
            self.sokets_activos += 1

        self.capital_arriesgado = (self.usdt1r / self.capital) *100
        self.disponible_operar = (self.capital * 0.025) - self.capital_arriesgado
        self.balance_vivo = self.pnl_vivo + self.balance



gl = Global() 

class OrderError(Exception): #Para que detenga el socket si hay error en la orden.
    pass




