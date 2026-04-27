import sqlite3

conn = sqlite3.connect("static/data/data.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS movimientos (
    pk          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    id_order    TEXT,
    type        TEXT,
    pe          REAL,
    sl          REAL,
    r0          REAL,
    r1          REAL,
    r2          REAL,
    qty         REAL,
    v1r         REAL,
    pnl         REAL,
    balance     REAL,
    comision    REAL,
    time        TEXT
)
""")

# Índices para acelerar las consultas más comunes
cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol     ON movimientos(symbol)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_time       ON movimientos(time)")


cur.execute("""
CREATE TABLE IF NOT EXISTS analisis (
    pk         INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol     TEXT    NOT NULL,
    estado     TEXT,
    sl         INTEGER,
    time_open  TEXT,
    time_close TEXT,
    pe         REAL,
    ps         REAL,
    vcierre    REAL,
    balance    REAL,
    resultado  REAL,
    secuencia  TEXT
)
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_analisis_symbol    ON analisis(symbol)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_analisis_symbol_sl ON analisis(symbol, sl)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_analisis_time      ON analisis(time_close)")

conn.commit()
conn.close()
print("Tabla movimientos creada ✅")

