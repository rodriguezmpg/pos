import sqlite3

conn = sqlite3.connect("static/data/data.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS movimientos (
    pk          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    id_order    REAL,
    id_pos      INTEGER,
    type        TEXT,
    pos         TEXT,
    pe          REAL,
    sl          REAL,
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
    id_pos     INTEGER,
    type       TEXT,
    pos        TEXT,
    time_open  TEXT,
    time_close TEXT,
    pe         REAL,
    ps         REAL,
    v1r        REAL,
    resultado  REAL,
    secuencia  TEXT
)
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_analisis_symbol    ON analisis(symbol)")

conn.commit()
conn.close()
print("Tabla movimientos y analisis creada ✅")

