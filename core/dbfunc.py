import sqlite3

DB_PATH = "static/data/data.db"

def _to_num(v):
    """Convierte '' o None a NULL; deja números como están."""
    if v == "" or v is None:
        return None
    return v

def write_db(Data_csv, symbol):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    filas = []
    for row in Data_csv:
        filas.append((
            symbol,             
            row[0],             
            row[1],             
            _to_num(row[2]),  
            _to_num(row[3]),   
            _to_num(row[4]),   
            _to_num(row[5]),   
            _to_num(row[6]),    
            _to_num(row[7]),     
            _to_num(row[8]),     
            _to_num(row[9]),     
            _to_num(row[10]),    
            _to_num(row[11]),    
            row[12],    
        ))

    cur.executemany("""
        INSERT INTO movimientos
            (symbol, id_order, type, pe, sl, r0, r1, r2, qty,
               v1r, pnl, balance, comision, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, filas)

    conn.commit()
    conn.close()

def write_analisis_db(symbol, estado, sl, time_open, time_close,
                      pe, ps, vcierre, balance, resultado, secuencia):
    """Reemplaza la escritura en analisis.csv."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO analisis
            (symbol, estado, sl, time_open, time_close,
             pe, ps, vcierre, balance, resultado, secuencia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol,
        estado,
        sl,
        time_open,
        time_close,
        _to_num(pe),
        _to_num(ps),
        _to_num(vcierre),
        _to_num(balance),
        _to_num(resultado),
        secuencia,
    ))

    conn.commit()
    conn.close()