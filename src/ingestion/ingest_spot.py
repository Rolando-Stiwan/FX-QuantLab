"""
Módulo de ingesta de precios spot desde Yahoo Finance.

Responsabilidad única: descargar el histórico de spot para un par
de divisas y guardarlo en la base de datos. No calcula volatilidad
ni hace nada más que traer y persistir el dato crudo.
"""

import logging
from datetime import datetime, timedelta

import yfinance as yf

from src.ingestion.database import get_connection

logger = logging.getLogger(__name__)

# Yahoo Finance identifica los pares FX con el sufijo "=X"
YFINANCE_TICKER_MAP = {
    "EURUSD": "EURUSD=X",
}

# Carga inicial: 5 años de histórico (ver justificación ya acordada:
# suficiente para rolling 252d + EWMA, sin exceso de datos no usados).
INITIAL_HISTORY_YEARS = 5


def fetch_spot_history(currency_pair: str, start_date: str | None = None) -> list[dict]:
    """
    Descarga el histórico de spot para un par de divisas desde Yahoo Finance.

    Args:
        currency_pair: ej. 'EURUSD'
        start_date: fecha ISO 'YYYY-MM-DD' desde donde descargar.
                    Si es None, descarga los últimos INITIAL_HISTORY_YEARS años
                    (uso pensado para la primera carga).

    Returns:
        Lista de dicts: [{"date": "2024-01-02", "close": 1.0945}, ...]
        Lista vacía si la descarga falla (nunca lanza excepción hacia arriba,
        para que el pipeline pueda decidir usar el último dato válido).
    """
    ticker_symbol = YFINANCE_TICKER_MAP.get(currency_pair)
    if ticker_symbol is None:
        logger.error(f"Par de divisas no soportado: {currency_pair}")
        return []

    if start_date is None:
        start = (datetime.today() - timedelta(days=365 * INITIAL_HISTORY_YEARS)).strftime("%Y-%m-%d")
    else:
        start = start_date

    try:
        ticker = yf.Ticker(ticker_symbol)
        history = ticker.history(start=start, interval="1d")
    except Exception as exc:
        logger.error(f"Fallo al descargar spot para {currency_pair} ({ticker_symbol}): {exc}")
        return []

    if history.empty:
        logger.warning(f"Yahoo Finance devolvió histórico vacío para {currency_pair}")
        return []

    records = [
        {"date": index.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 6)}
        for index, row in history.iterrows()
    ]
    logger.info(f"Descargados {len(records)} registros de spot para {currency_pair}")
    return records


def save_spot_prices(currency_pair: str, records: list[dict]) -> int:
    """
    Guarda registros de spot en la base de datos.
    Usa INSERT OR REPLACE para ser idempotente (evita duplicados si
    el pipeline corre dos veces el mismo día).

    Returns:
        Número de filas insertadas/actualizadas.
    """
    if not records:
        return 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO spot_prices (currency_pair, date, close, source)
            VALUES (?, ?, ?, 'yfinance')
            """,
            [(currency_pair, r["date"], r["close"]) for r in records],
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def run_spot_ingestion(currency_pair: str = "EURUSD", start_date: str | None = None) -> bool:
    """
    Orquesta la descarga + guardado para un par. Devuelve True si tuvo éxito,
    False si falló (para que el pipeline principal decida el fallback).
    """
    records = fetch_spot_history(currency_pair, start_date)
    if not records:
        return False
    save_spot_prices(currency_pair, records)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.ingestion.database import init_db

    init_db()
    success = run_spot_ingestion("EURUSD")
    print("Ingesta de spot exitosa" if success else "Ingesta de spot FALLÓ")

#7207666c8ef594c7e654cd772f81075d