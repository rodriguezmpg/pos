import sqlite3

DB_PATH = "static/data/data.db"

def _to_num(v):
    """Convierte '' o None a NULL; deja números como están."""
    if v == "" or v is None:
        return None
    return v

def write_db(Data_csv, symbol, valorsl):
    """Reemplaza a write_csv: inserta las filas en la tabla movimientos."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    filas = []
    for row in Data_csv:
        filas.append((
            symbol,              # symbol
            valorsl,             # input_sl
            row[0],              # id_order
            row[1],              # type
            _to_num(row[2]),     # sl
            _to_num(row[3]),     # pe
            _to_num(row[4]),     # tp
            _to_num(row[5]),     # pnl
            _to_num(row[6]),     # qty_usdt
            _to_num(row[7]),     # qvar
            _to_num(row[8]),     # pp
            _to_num(row[9]),     # qty_total
            _to_num(row[10]),    # balance
            _to_num(row[11]),    # valor
            _to_num(row[12]),    # comision
            row[13],             # time
        ))

    cur.executemany("""
        INSERT INTO movimientos
            (symbol, input_sl, id_order, type, sl, pe, tp, pnl,
             qty_usdt, qvar, pp, qty_total, balance, valor, comision, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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