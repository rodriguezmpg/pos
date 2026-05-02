import os
import sqlite3
from core.dbfunc import DB_PATH


def init_db():
    # Asegurar que el directorio existe (clave en Render: /var/data ya existe,
    # pero esto cubre el caso local cuando todavía no creaste static/data/).
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON movimientos(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_time   ON movimientos(time)")

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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_analisis_symbol ON analisis(symbol)")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("DB inicializada ✅")