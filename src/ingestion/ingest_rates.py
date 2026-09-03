"""
Módulo de ingesta de tasas de interés desde FRED.

Responsabilidad única: descargar r_dom (USD) y r_for (EUR) y
guardarlas en la base de datos. Sigue el mismo patrón de tolerancia
a fallos que ingest_spot.py.
"""

import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fredapi import Fred

from src.ingestion.database import get_connection

logger = logging.getLogger(__name__)

load_dotenv()

# Series FRED ya decididas: Treasury 3M (USD) y €STR (EUR)
FRED_SERIES_DOMESTIC = "DGS3MO"                    # r_dom, USD
FRED_SERIES_FOREIGN = "ECBESTRVOLWGTTRMDMNRT"      # r_for, EUR

INITIAL_HISTORY_YEARS = 5


def _get_fred_client() -> Fred:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY no encontrada. Revisa tu archivo .env")
    return Fred(api_key=api_key)


def fetch_rate_series(series_id: str, start_date: str | None = None) -> dict[str, float]:
    """
    Descarga una serie de tasas desde FRED.

    Args:
        series_id: código de la serie FRED (ej. 'DGS3MO')
        start_date: fecha ISO 'YYYY-MM-DD' desde donde descargar.
                    Si es None, descarga los últimos INITIAL_HISTORY_YEARS años.

    Returns:
        Dict {fecha_iso: valor}. Diccionario vacío si falla (nunca lanza
        excepción hacia arriba, mismo criterio que ingest_spot.py).
    """
    if start_date is None:
        start = (datetime.today() - timedelta(days=365 * INITIAL_HISTORY_YEARS)).strftime("%Y-%m-%d")
    else:
        start = start_date

    try:
        fred = _get_fred_client()
        series = fred.get_series(series_id, observation_start=start)
    except Exception as exc:
        logger.error(f"Fallo al descargar serie FRED {series_id}: {exc}")
        return {}

    if series.empty:
        logger.warning(f"FRED devolvió serie vacía para {series_id}")
        return {}

    # FRED a veces reporta NaN en días sin dato (feriados, retrasos de publicación).
    # Se descartan esos puntos: no se inventan valores para huecos.
    series = series.dropna()

    records = {index.strftime("%Y-%m-%d"): round(float(value) / 100, 6) for index, value in series.items()}
    logger.info(f"Descargados {len(records)} registros de {series_id}")
    return records


def save_interest_rates(currency_pair: str, domestic_rates: dict[str, float], foreign_rates: dict[str, float]) -> int:
    """
    Combina r_dom y r_for por fecha y guarda en la base de datos.
    Solo guarda fechas donde AMBAS tasas están disponibles (Garman-Kohlhagen
    necesita las dos para calcular un precio en esa fecha).

    Returns:
        Número de filas insertadas/actualizadas.
    """
    common_dates = set(domestic_rates.keys()) & set(foreign_rates.keys())
    if not common_dates:
        logger.warning("Sin fechas comunes entre r_dom y r_for; nada que guardar")
        return 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO interest_rates
            (currency_pair, date, rate_domestic, rate_foreign, source)
            VALUES (?, ?, ?, ?, 'FRED')
            """,
            [
                (currency_pair, date, domestic_rates[date], foreign_rates[date])
                for date in sorted(common_dates)
            ],
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def run_rates_ingestion(currency_pair: str = "EURUSD", start_date: str | None = None) -> bool:
    """
    Orquesta la descarga + guardado de ambas tasas.
    Devuelve True si tuvo éxito, False si falló (para que el pipeline
    principal decida el fallback).
    """
    domestic = fetch_rate_series(FRED_SERIES_DOMESTIC, start_date)
    foreign = fetch_rate_series(FRED_SERIES_FOREIGN, start_date)

    if not domestic or not foreign:
        return False

    save_interest_rates(currency_pair, domestic, foreign)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.ingestion.database import init_db

    init_db()
    success = run_rates_ingestion("EURUSD")
    print("Ingesta de tasas exitosa" if success else "Ingesta de tasas FALLÓ")