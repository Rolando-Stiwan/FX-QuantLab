"""
market_data.py — Lectura de snapshots de mercado desde SQLite.

Responsabilidad única: SELECT del último dato disponible por tabla.
No recalcula nada — el pipeline diario (Módulo 1) ya guardó los
valores; este módulo solo los expone para la API.
"""

from src.ingestion.database import get_connection


def get_latest_market_data(currency_pair: str = "EURUSD") -> dict:
    """
    Devuelve el snapshot de mercado más reciente disponible para un
    par de divisas: spot, tasas, y las 4 volatilidades calculadas.

    Si alguna tabla no tiene datos para ese par, el campo
    correspondiente vuelve None (no lanza error) — el consumidor
    de la API decide qué hacer con datos faltantes.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT date, close FROM spot_prices "
            "WHERE currency_pair = ? ORDER BY date DESC LIMIT 1",
            (currency_pair,),
        )
        spot_row = cur.fetchone()

        cur.execute(
            "SELECT date, rate_domestic, rate_foreign FROM interest_rates "
            "WHERE currency_pair = ? ORDER BY date DESC LIMIT 1",
            (currency_pair,),
        )
        rates_row = cur.fetchone()

        volatilidades = {}
        for method in ("ewma", "rolling_20d", "rolling_60d", "rolling_252d"):
            cur.execute(
                "SELECT value FROM volatility "
                "WHERE currency_pair = ? AND method = ? ORDER BY date DESC LIMIT 1",
                (currency_pair, method),
            )
            row = cur.fetchone()
            volatilidades[method] = row[0] if row else None

        # La fecha de referencia es la del spot (fuente más crítica)
        fecha = spot_row[0] if spot_row else None

        return {
            "currency_pair": currency_pair,
            "date": fecha,
            "spot": spot_row[1] if spot_row else None,
            "rate_domestic": rates_row[1] if rates_row else None,
            "rate_foreign": rates_row[2] if rates_row else None,
            "volatility_ewma": volatilidades["ewma"],
            "volatility_rolling_20d": volatilidades["rolling_20d"],
            "volatility_rolling_60d": volatilidades["rolling_60d"],
            "volatility_rolling_252d": volatilidades["rolling_252d"],
        }
    finally:
        conn.close()

def get_market_history(currency_pair: str = "EURUSD", days: int = 180) -> dict:
    """
    Devuelve series históricas de spot y volatilidad (todas las
    4 métricas) para los últimos `days` días. Si days <= 0, devuelve
    todo el histórico disponible.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        if days > 0:
            limit_clause = f"ORDER BY date DESC LIMIT {days}"
        else:
            limit_clause = "ORDER BY date DESC"

        cur.execute(
            f"SELECT date, close FROM spot_prices "
            f"WHERE currency_pair = ? {limit_clause}",
            (currency_pair,),
        )
        spot_rows = cur.fetchall()[::-1]  # orden cronológico ascendente

        volatilidades = {}
        for method in ("ewma", "rolling_20d", "rolling_60d", "rolling_252d"):
            cur.execute(
                f"SELECT date, value FROM volatility "
                f"WHERE currency_pair = ? AND method = ? {limit_clause}",
                (currency_pair, method),
            )
            volatilidades[method] = cur.fetchall()[::-1]

        return {
            "currency_pair": currency_pair,
            "spot": [{"date": d, "value": v} for d, v in spot_rows],
            "volatility": {
                method: [{"date": d, "value": v} for d, v in rows]
                for method, rows in volatilidades.items()
            },
        }
    finally:
        conn.close()