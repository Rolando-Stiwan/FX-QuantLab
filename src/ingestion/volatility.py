"""
Módulo de cálculo de volatilidad histórica.

Responsabilidad única: leer el spot ya guardado en SQLite, calcular
volatilidad rolling (20d/60d/252d) y EWMA, y guardar los resultados.
No descarga nada — depende de que ingest_spot.py ya haya corrido.
"""

import logging

import numpy as np
import pandas as pd

from src.ingestion.database import get_connection

logger = logging.getLogger(__name__)

# Decisión ya confirmada: λ=0.94, estándar RiskMetrics/JP Morgan para datos diarios
EWMA_LAMBDA = 0.94

ROLLING_WINDOWS = {
    "rolling_20d": 20,
    "rolling_60d": 60,
    "rolling_252d": 252,
}

TRADING_DAYS_PER_YEAR = 252


def load_spot_series(currency_pair: str) -> pd.Series:
    """
    Carga el histórico de spot desde SQLite como una serie de pandas
    indexada por fecha. Solo incluye los días que realmente existen
    en la base de datos (sin rellenar huecos con un calendario fijo).
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT date, close FROM spot_prices WHERE currency_pair = ? ORDER BY date ASC",
            conn,
            params=(currency_pair,),
        )
    finally:
        conn.close()

    if df.empty:
        logger.warning(f"Sin datos de spot para {currency_pair}; corre ingest_spot.py primero")
        return pd.Series(dtype=float)

    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"]


def compute_log_returns(spot: pd.Series) -> pd.Series:
    """Retornos logarítmicos diarios: ln(P_t / P_t-1)."""
    return np.log(spot / spot.shift(1)).dropna()


def compute_rolling_volatility(log_returns: pd.Series, window: int) -> pd.Series:
    """
    Volatilidad rolling anualizada: desviación estándar de retornos
    en una ventana móvil, escalada a base anual con sqrt(252).
    """
    return log_returns.rolling(window=window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def compute_ewma_volatility(log_returns: pd.Series, lam: float = EWMA_LAMBDA) -> pd.Series:
    """
    Volatilidad EWMA anualizada (estilo RiskMetrics).

    Fórmula recursiva: sigma2_t = lambda * sigma2_(t-1) + (1 - lambda) * r_(t-1)^2

    Se implementa vectorizado usando pandas.ewm(), que aplica exactamente
    esta misma recursión internamente (alpha = 1 - lambda).
    """
    squared_returns = log_returns**2
    ewma_variance = squared_returns.ewm(alpha=(1 - lam), adjust=False).mean()
    return np.sqrt(ewma_variance) * np.sqrt(TRADING_DAYS_PER_YEAR)


def compute_all_volatilities(currency_pair: str) -> pd.DataFrame:
    """
    Calcula todas las volatilidades (rolling + EWMA) para un par.

    Returns:
        DataFrame con columnas: date, method, value
        Vacío si no hay suficiente historia de spot.
    """
    spot = load_spot_series(currency_pair)
    if spot.empty:
        return pd.DataFrame(columns=["date", "method", "value"])

    log_returns = compute_log_returns(spot)

    results = []
    for method_name, window in ROLLING_WINDOWS.items():
        rolling_vol = compute_rolling_volatility(log_returns, window).dropna()
        for date, value in rolling_vol.items():
            results.append({"date": date.strftime("%Y-%m-%d"), "method": method_name, "value": round(float(value), 6)})

    ewma_vol = compute_ewma_volatility(log_returns).dropna()
    for date, value in ewma_vol.items():
        results.append({"date": date.strftime("%Y-%m-%d"), "method": "ewma", "value": round(float(value), 6)})

    return pd.DataFrame(results)


def save_volatility(currency_pair: str, vol_df: pd.DataFrame) -> int:
    """Guarda los resultados de volatilidad en la base de datos."""
    if vol_df.empty:
        return 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO volatility (currency_pair, date, method, value)
            VALUES (?, ?, ?, ?)
            """,
            [(currency_pair, row["date"], row["method"], row["value"]) for _, row in vol_df.iterrows()],
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def run_volatility_calculation(currency_pair: str = "EURUSD") -> bool:
    """
    Orquesta el cálculo + guardado de volatilidad para un par.
    Devuelve True si tuvo éxito, False si no había suficiente spot.
    """
    vol_df = compute_all_volatilities(currency_pair)
    if vol_df.empty:
        return False
    save_volatility(currency_pair, vol_df)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.ingestion.database import init_db

    init_db()
    success = run_volatility_calculation("EURUSD")
    print("Cálculo de volatilidad exitoso" if success else "Cálculo de volatilidad FALLÓ (sin datos de spot)")