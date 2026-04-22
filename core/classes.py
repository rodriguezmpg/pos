
class DataPost: 
    def reset(self):
        self.__init__()
    def __init__(self):       
        self.p2r = 0.00
        self.USDT1r = 0
        self.simulacion = False
        
class FixedData: 
    def reset(self):
        self.__init__()
    def __init__(self):
        self.fechainicio = None
        self.type_pos = ''

        self.Qty_min = 0
        self.dec_precio = 0
        self.dec_qty = 0

        self.perc1r = 0.00
        self.perc2r = 0.00
        self.valor_r = 0.00

        self.r_1 = 0.00
        self.r0 = 0.00
        self.r1 = 0.00
        self.r2 = 0.00

        self.Qty_mVar = 0.00


class RealTime:
    def reset(self):
        self.__init__()
    def __init__(self):
        self.current_price = 0.00
        self.previous_price = 0.00
        self.fechayhora = None



class OrderError(Exception): #Para que detenga el socket si hay error en la orden.
    pass




