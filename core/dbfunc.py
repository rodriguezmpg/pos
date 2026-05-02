import sqlite3

DB_PATH = os.getenv("DB_PATH", "static/data/data.db")

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
            row[0],             #id_order
            row[1],             #id_pos
            row[2],             #type
            row[3],             #pos
            _to_num(row[4]),    #pe
            _to_num(row[5]),    #sl
            _to_num(row[6]),    #r1 
            _to_num(row[7]),    #r2 
            _to_num(row[8]),    #qty
            _to_num(row[9]),   #v1r 
            _to_num(row[10]),   #pnl 
            _to_num(row[11]),   #balance
            _to_num(row[12]),   #comision
            row[13],            #time
        ))

    cur.executemany("""
        INSERT INTO movimientos
            (symbol, id_order, id_pos, type, pos, pe, sl, r1, r2, qty,
               v1r, pnl, balance, comision, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, filas)

    conn.commit()
    conn.close()

def write_analisis_db(symbol, id_pos, type_pos, pos, time_open, time_close,
                      pe, ps, v1r, resultado, secuencia):
    """Reemplaza la escritura en analisis.csv."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO analisis
            (symbol, id_pos, type, pos, time_open, time_close,
             pe, ps, v1r, resultado, secuencia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol,
        id_pos,
        type_pos,
        pos,
        time_open,
        time_close,
        _to_num(pe),
        _to_num(ps),
        _to_num(v1r),
        _to_num(resultado),
        secuencia,
    ))

    conn.commit()
    conn.close()