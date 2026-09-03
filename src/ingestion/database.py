"""
Módulo de definición y conexión a la base de datos SQLite.

Responsabilidad única: crear el esquema y exponer una conexión.
No contiene lógica de descarga ni de cálculo (eso vive en otros
archivos del paquete ingestion).
"""

import sqlite3
from pathlib import Path

# Ruta al archivo .db, versionado dentro del repo (decisión ya cerrada:
# sin servidor externo, el propio Action hace commit+push del archivo).
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fx_quantlab.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS spot_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency_pair TEXT NOT NULL,       -- ej. 'EURUSD'
    date TEXT NOT NULL,                -- formato ISO 'YYYY-MM-DD'
    close REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'yfinance',
    UNIQUE(currency_pair, date)
);

CREATE TABLE IF NOT EXISTS interest_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency_pair TEXT NOT NULL,       -- ej. 'EURUSD' (para saber a qué par aplica el par de tasas)
    date TEXT NOT NULL,
    rate_domestic REAL NOT NULL,       -- r_dom
    rate_foreign REAL NOT NULL,        -- r_for
    source TEXT NOT NULL DEFAULT 'FRED',
    UNIQUE(currency_pair, date)
);

CREATE TABLE IF NOT EXISTS volatility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency_pair TEXT NOT NULL,
    date TEXT NOT NULL,
    method TEXT NOT NULL,              -- 'rolling_20d', 'rolling_60d', 'rolling_252d', 'ewma'
    value REAL NOT NULL,               -- volatilidad anualizada
    UNIQUE(currency_pair, date, method)
);

CREATE TABLE IF NOT EXISTS pipeline_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,       -- fecha+hora exacta de ejecución del pipeline (ISO 8601)
    currency_pair TEXT NOT NULL,
    spot_status TEXT NOT NULL,         -- 'ok' | 'stale_fallback' | 'failed'
    rates_status TEXT NOT NULL,
    volatility_status TEXT NOT NULL,
    notes TEXT                         -- detalle libre, ej. "usando último spot válido del 2026-08-24"
);
"""


def get_connection() -> sqlite3.Connection:
    """Abre (o crea) la base de datos y devuelve la conexión."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Crea las tablas si no existen. Idempotente: seguro de correr cada día."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Base de datos inicializada en: {DB_PATH}")