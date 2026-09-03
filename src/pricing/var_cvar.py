"""
var_cvar.py — VaR y CVaR de una opción FX vía Monte Carlo full-revaluation.

Metodología:
1. Simula N trayectorias del spot (GBM) al horizonte de riesgo.
2. Repreicia la opción en cada escenario (vectorizado, NumPy).
3. Calcula la distribución de P&L: precio_repreciado - precio_hoy.
4. VaR = percentil de la distribución de pérdidas.
   CVaR = promedio de las pérdidas más allá del VaR (cola).

Nota de diseño: garman_kohlhagen.price_option() opera sobre un solo
escenario a la vez (PricingInputs es un dataclass con validación
escalar). Para Monte Carlo full-revaluation necesitamos vectorizar
la MISMA fórmula sobre 50,000+ escenarios de golpe. Por eso aquí se
define _price_vectorized(), que replica exactamente la matemática de
garman_kohlhagen.py pero acepta arrays de NumPy en S. No se modifica
garman_kohlhagen.py (Módulo 2 queda intacto y validado).
"""

import numpy as np
from scipy.stats import norm

from src.pricing.garman_kohlhagen import PricingInputs, OptionType, price_option


def _price_vectorized(
    S: np.ndarray, K: float, T: float, r_dom: float, r_for: float,
    sigma: float, option_type: OptionType
) -> np.ndarray:
    """
    Misma fórmula de garman_kohlhagen.price_option(), vectorizada
    sobre S (array de NumPy). Debe dar resultados idénticos a
    price_option() para un solo escenario — esto se valida con un
    test cruzado antes de confiar en esta función.
    """
    d1 = (np.log(S / K) + (r_dom - r_for + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    domestic_discount = np.exp(-r_dom * T)
    foreign_discount = np.exp(-r_for * T)

    if option_type == OptionType.CALL:
        price = S * foreign_discount * norm.cdf(d1) - K * domestic_discount * norm.cdf(d2)
    else:
        price = K * domestic_discount * norm.cdf(-d2) - S * foreign_discount * norm.cdf(-d1)

    return price


def simulate_var_cvar(
    S: float,
    K: float,
    T: float,
    r_dom: float,
    r_for: float,
    sigma: float,
    option_type: OptionType = OptionType.CALL,
    horizon_days: int = 1,
    n_simulations: int = 50_000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    Calcula VaR y CVaR de una posición en opción FX vanilla, vía
    Monte Carlo full-revaluation (vectorizado con NumPy).
    """
    if not (0 < confidence < 1):
        raise ValueError("confidence debe estar entre 0 y 1")
    if horizon_days <= 0:
        raise ValueError("horizon_days debe ser > 0")

    horizon_years = horizon_days / 365.0
    if horizon_years >= T:
        raise ValueError(
            f"horizon_days ({horizon_days}) no puede ser >= al tenor "
            f"restante de la opción ({T*365:.0f} días)"
        )

    rng = np.random.default_rng(seed)

    # Precio hoy: usa la función oficial de Módulo 2 (un solo escenario)
    inputs_hoy = PricingInputs(
        currency_pair="N/A", spot=S, strike=K, tenor_years=T,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=option_type,
    )
    precio_hoy = price_option(inputs_hoy).price

    # Simula spot al horizonte de riesgo (GBM, drift neutral al riesgo)
    drift = (r_dom - r_for - 0.5 * sigma**2) * horizon_years
    shock = sigma * np.sqrt(horizon_years) * rng.standard_normal(n_simulations)
    S_simulado = S * np.exp(drift + shock)

    # Repricea vectorizado, con T reducido
    T_restante = T - horizon_years
    precios_simulados = _price_vectorized(
        S_simulado, K, T_restante, r_dom, r_for, sigma, option_type
    )

    pnl = precios_simulados - precio_hoy

    var = -np.percentile(pnl, (1 - confidence) * 100)
    perdidas_extremas = pnl[pnl <= -var]
    cvar = -np.mean(perdidas_extremas) if len(perdidas_extremas) > 0 else var

    return {
        "precio_hoy": precio_hoy,
        "var": var,
        "cvar": cvar,
        "pnl_distribution": pnl,
        "horizon_days": horizon_days,
        "confidence": confidence,
        "n_simulations": n_simulations,
    }