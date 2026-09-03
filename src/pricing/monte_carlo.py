"""
Motor de pricing Monte Carlo para opciones FX europeas.

Diseño: calculadora pura, igual que garman_kohlhagen.py. Simula
trayectorias del spot bajo movimiento geométrico browniano (GBM) en
medida neutral al riesgo, y calcula el precio como el valor esperado
descontado del payoff.

Uso principal: validación cruzada contra Garman-Kohlhagen (deben
converger). El número de simulaciones es configurable según el
contexto: menos para el simulador interactivo (velocidad), más para
el reporte final (precisión).
"""

import logging
import time

import numpy as np

from src.pricing.garman_kohlhagen import OptionType, PricingInputs

logger = logging.getLogger(__name__)


def simulate_terminal_spot(inputs: PricingInputs, n_simulations: int, seed: int | None = None) -> np.ndarray:
    """
    Simula el spot al vencimiento bajo GBM neutral al riesgo:

        S_T = S_0 * exp[(r_dom - r_for - 0.5*sigma^2) * T + sigma * sqrt(T) * Z]

    donde Z ~ N(0, 1). Vectorizado con NumPy (nunca loops de Python puro),
    como acordado para que 50.000-100.000 trayectorias corran en milisegundos.
    """
    rng = np.random.default_rng(seed)
    Z = rng.standard_normal(n_simulations)

    S, T = inputs.spot, inputs.tenor_years
    sigma, r_dom, r_for = inputs.volatility, inputs.rate_domestic, inputs.rate_foreign

    drift = (r_dom - r_for - 0.5 * sigma**2) * T
    diffusion = sigma * np.sqrt(T) * Z

    return S * np.exp(drift + diffusion)


def compute_payoff(terminal_spot: np.ndarray, strike: float, option_type: OptionType) -> np.ndarray:
    """Payoff al vencimiento, sin descontar."""
    if option_type == OptionType.CALL:
        return np.maximum(terminal_spot - strike, 0.0)
    return np.maximum(strike - terminal_spot, 0.0)


def price_option_monte_carlo(
    inputs: PricingInputs,
    n_simulations: int = 50_000,
    seed: int | None = None,
) -> dict:
    """
    Calcula el precio vía Monte Carlo: promedio de los payoffs
    descontado a valor presente con la tasa doméstica.

    Returns:
        dict con: price, std_error (error estándar de la estimación,
        útil para saber qué tan confiable es el resultado con n_simulations
        dado), n_simulations, elapsed_seconds
    """
    start = time.perf_counter()

    terminal_spot = simulate_terminal_spot(inputs, n_simulations, seed)
    payoffs = compute_payoff(terminal_spot, inputs.strike, inputs.option_type)

    discount_factor = np.exp(-inputs.rate_domestic * inputs.tenor_years)
    discounted_payoffs = payoffs * discount_factor

    price = float(np.mean(discounted_payoffs))
    std_error = float(np.std(discounted_payoffs, ddof=1) / np.sqrt(n_simulations))

    elapsed = time.perf_counter() - start

    return {
        "price": round(price, 6),
        "std_error": round(std_error, 6),
        "n_simulations": n_simulations,
        "elapsed_seconds": round(elapsed, 4),
    }


def validate_against_closed_form(
    inputs: PricingInputs,
    closed_form_price: float,
    n_simulations: int = 50_000,
    seed: int = 42,
) -> dict:
    """
    Compara el precio Monte Carlo contra el precio de Garman-Kohlhagen.
    Devuelve la diferencia absoluta y si está dentro de un margen razonable
    (3 desviaciones estándar del error de Monte Carlo, criterio estadístico
    estándar de convergencia).
    """
    mc_result = price_option_monte_carlo(inputs, n_simulations, seed)
    difference = abs(mc_result["price"] - closed_form_price)
    tolerance = 3 * mc_result["std_error"]

    return {
        **mc_result,
        "closed_form_price": closed_form_price,
        "difference": round(difference, 6),
        "within_tolerance": difference <= tolerance,
        "tolerance": round(tolerance, 6),
    }


if __name__ == "__main__":
    from src.pricing.garman_kohlhagen import price_option

    example = PricingInputs(
        currency_pair="EURUSD",
        spot=1.166,
        strike=1.20,
        tenor_years=90 / 365,
        volatility=0.045,
        rate_domestic=0.0386,
        rate_foreign=0.0219,
        option_type=OptionType.CALL,
    )

    closed_form = price_option(example)
    validation = validate_against_closed_form(example, closed_form.price, n_simulations=50_000)

    print(f"Precio Garman-Kohlhagen: {closed_form.price}")
    print(f"Precio Monte Carlo:      {validation['price']} (± {validation['std_error']})")
    print(f"Diferencia:              {validation['difference']}")
    print(f"Tolerancia (3 sigma):    {validation['tolerance']}")
    print(f"¿Convergen?              {'Sí' if validation['within_tolerance'] else 'NO'}")
    print(f"Simulaciones: {validation['n_simulations']} | Tiempo: {validation['elapsed_seconds']}s")