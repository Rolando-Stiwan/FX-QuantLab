"""
greeks.py — Griegas analíticas de Garman-Kohlhagen (FX options).

Función pura: no accede a DB. Recibe inputs de mercado y devuelve
un diccionario con las 5 griegas.

Convenciones:
- Theta expresado como decay POR DÍA (no por año) — se divide por 365.
- Rho se separa en rho_dom (tasa doméstica, USD) y rho_for (tasa
  extranjera, EUR), porque cada tasa afecta el precio de forma
  independiente (no hay una única "tasa" en FX como en Black-Scholes
  clásico de acciones).
- Delta y Vega llevan el factor e^{-r_for*T} porque el spot FX
  "paga" su propia tasa de interés mientras se mantiene (equivalente
  a un dividend yield continuo en Black-Scholes con dividendos).
"""

import numpy as np
from scipy.stats import norm


def _d1_d2(S: float, K: float, T: float, r_dom: float, r_for: float, sigma: float) -> tuple[float, float]:
    """
    Calcula d1 y d2 de Garman-Kohlhagen.

    Debe ser IDÉNTICA a la fórmula usada en garman_kohlhagen.py —
    si allí cambias algo, cámbialo aquí también (o mejor: importa
    la función desde garman_kohlhagen.py en vez de duplicarla).
    """
    d1 = (np.log(S / K) + (r_dom - r_for + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def greeks(
    S: float,
    K: float,
    T: float,
    r_dom: float,
    r_for: float,
    sigma: float,
    option_type: str = "call",
) -> dict:
    """
    Calcula las griegas de una opción FX vanilla bajo Garman-Kohlhagen.

    Parameters
    ----------
    S : spot actual (ej. EURUSD)
    K : strike
    T : tenor en años (ej. 90/365)
    r_dom : tasa doméstica (USD), en decimal (ej. 0.05 = 5%)
    r_for : tasa extranjera (EUR), en decimal
    sigma : volatilidad anualizada, en decimal
    option_type : "call" o "put"

    Returns
    -------
    dict con delta, gamma, vega, theta, rho_dom, rho_for

    Unidades:
    - delta: adimensional (sensibilidad a 1 unidad de spot)
    - gamma: por unidad de spot al cuadrado
    - vega: por 1.00 (100%) de cambio en sigma — divide entre 100
      si quieres "por 1 punto de vol"
    - theta: por DÍA (ya dividido entre 365)
    - rho_dom / rho_for: por 1.00 (100%) de cambio en la tasa —
      divide entre 100 si quieres "por 1 punto porcentual"
    """
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type debe ser 'call' o 'put', recibido: {option_type}")
    if T <= 0:
        raise ValueError("T debe ser > 0 (usa validation_checks.py para el límite T→0)")
    if sigma <= 0:
        raise ValueError("sigma debe ser > 0 (usa validation_checks.py para el límite sigma→0)")

    d1, d2 = _d1_d2(S, K, T, r_dom, r_for, sigma)
    sqrtT = np.sqrt(T)
    disc_for = np.exp(-r_for * T)
    disc_dom = np.exp(-r_dom * T)
    pdf_d1 = norm.pdf(d1)

    # Gamma y Vega son iguales para call y put
    gamma = disc_for * pdf_d1 / (S * sigma * sqrtT)
    vega = S * disc_for * pdf_d1 * sqrtT

    if option_type == "call":
        delta = disc_for * norm.cdf(d1)
        rho_dom = K * T * disc_dom * norm.cdf(d2)
        rho_for = -T * S * disc_for * norm.cdf(d1)
        theta_annual = (
            -(S * disc_for * pdf_d1 * sigma) / (2 * sqrtT)
            + r_for * S * disc_for * norm.cdf(d1)
            - r_dom * K * disc_dom * norm.cdf(d2)
        )
    else:  # put
        delta = disc_for * (norm.cdf(d1) - 1)
        rho_dom = -K * T * disc_dom * norm.cdf(-d2)
        rho_for = T * S * disc_for * norm.cdf(-d1)
        theta_annual = (
            -(S * disc_for * pdf_d1 * sigma) / (2 * sqrtT)
            - r_for * S * disc_for * norm.cdf(-d1)
            + r_dom * K * disc_dom * norm.cdf(-d2)
        )

    theta_per_day = theta_annual / 365.0

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta_per_day,
        "rho_dom": rho_dom,
        "rho_for": rho_for,
    }