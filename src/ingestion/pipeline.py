"""
Orquestador del pipeline diario de FX QuantLab.

Responsabilidad: coordinar ingesta incremental de spot + tasas,
recálculo de volatilidad, y registro de trazabilidad. No contiene
lógica de descarga ni de cálculo propia — delega a los módulos
ya construidos (ingest_spot, ingest_rates, volatility).
"""

import logging
from datetime import datetime, timezone

from src.ingestion.database import get_connection, init_db
from src.ingestion.ingest_spot import run_spot_ingestion
from src.ingestion.ingest_rates import run_rates_ingestion
from src.ingestion.volatility import run_volatility_calculation

logger = logging.getLogger(__name__)


def get_last_spot_date(currency_pair: str) -> str | None:
    """Devuelve la fecha más reciente de spot guardada, o None si no hay ninguna."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(date) FROM spot_prices WHERE currency_pair = ?",
            (currency_pair,),
        )
        result = cursor.fetchone()[0]
        return result
    finally:
        conn.close()


def get_last_rates_date(currency_pair: str) -> str | None:
    """Devuelve la fecha más reciente de tasas guardada, o None si no hay ninguna."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(date) FROM interest_rates WHERE currency_pair = ?",
            (currency_pair,),
        )
        result = cursor.fetchone()[0]
        return result
    finally:
        conn.close()


def save_snapshot(
    currency_pair: str,
    spot_status: str,
    rates_status: str,
    volatility_status: str,
    notes: str,
) -> None:
    """Registra el resultado de la corrida en pipeline_snapshots."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pipeline_snapshots
            (run_timestamp, currency_pair, spot_status, rates_status, volatility_status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                currency_pair,
                spot_status,
                rates_status,
                volatility_status,
                notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def run_daily_pipeline(currency_pair: str = "EURUSD") -> None:
    """
    Corre el pipeline diario completo para un par de divisas.

    Nunca lanza excepción hacia arriba: cada paso se intenta de forma
    independiente, y el resultado (ok/fallback/failed) queda registrado
    en pipeline_snapshots, sin romper silenciosamente.
    """
    init_db()
    notes = []

    # --- Spot ---
    last_spot_date = get_last_spot_date(currency_pair)
    spot_success = run_spot_ingestion(currency_pair, start_date=last_spot_date)
    if spot_success:
        spot_status = "ok"
        logger.info(f"Spot actualizado correctamente desde {last_spot_date}")
    else:
        spot_status = "stale_fallback" if last_spot_date else "failed"
        notes.append(f"Spot: fallo en descarga, usando último dato válido ({last_spot_date or 'ninguno'})")
        logger.warning(notes[-1])

    # --- Tasas ---
    last_rates_date = get_last_rates_date(currency_pair)
    rates_success = run_rates_ingestion(currency_pair, start_date=last_rates_date)
    if rates_success:
        rates_status = "ok"
        logger.info(f"Tasas actualizadas correctamente desde {last_rates_date}")
    else:
        rates_status = "stale_fallback" if last_rates_date else "failed"
        notes.append(f"Tasas: fallo en descarga, usando último dato válido ({last_rates_date or 'ninguno'})")
        logger.warning(notes[-1])

    # --- Volatilidad (solo se recalcula si hay algo de spot, sin importar si fue fallback) ---
    volatility_success = run_volatility_calculation(currency_pair)
    if volatility_success:
        volatility_status = "ok"
        logger.info("Volatilidad recalculada correctamente")
    else:
        volatility_status = "failed"
        notes.append("Volatilidad: no se pudo calcular, sin datos de spot disponibles")
        logger.error(notes[-1])

    save_snapshot(
        currency_pair=currency_pair,
        spot_status=spot_status,
        rates_status=rates_status,
        volatility_status=volatility_status,
        notes="; ".join(notes) if notes else "Corrida completa sin incidencias",
    )

    logger.info(
        f"Pipeline completo para {currency_pair}: "
        f"spot={spot_status}, rates={rates_status}, volatility={volatility_status}"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_daily_pipeline("EURUSD")