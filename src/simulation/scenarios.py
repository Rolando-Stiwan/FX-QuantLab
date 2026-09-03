"""
scenarios.py — Simulador de escenarios: shocks individuales y
escenarios combinados con sentido económico.

Diseño: precio + Greeks se recalculan en tiempo real (fórmulas
cerradas, instantáneo). VaR/CVaR NO se incluye aquí — es demasiado
costoso (Monte Carlo, ~50,000 sims) para recalcular en cada
movimiento de un slider. Se calcula aparte, bajo demanda, llamando
directamente a var_cvar.simulate_var_cvar() sobre el escenario
elegido.

Shocks individuales: mueven una sola variable, todo lo demás
constante (estándar de sensitivity analysis / reporting diario).

Escenarios combinados: shocks que se mueven juntos porque así se
mueve el mercado en la realidad (spot y volatilidad correlacionados
negativamente; tasas y volatilidad correlacionados positivamente en
crisis). No son una matriz combinatoria — son 3 escenarios curados,
documentados con su lógica económica.
"""

from dataclasses import dataclass

from src.pricing.garman_kohlhagen import PricingInputs, OptionType, price_option
from src.pricing.greeks import greeks as compute_greeks


@dataclass
class ScenarioResult:
    """Resultado de recalcular precio + Greeks bajo un escenario."""
    nombre: str
    spot: float
    volatility: float
    rate_domestic: float
    rate_foreign: float
    price: float
    price_change: float          # vs. escenario base
    price_change_pct: float
    greeks: dict


def _evaluar_escenario(
    nombre: str,
    S: float, K: float, T: float,
    r_dom: float, r_for: float, sigma: float,
    option_type: OptionType,
    precio_base: float,
) -> ScenarioResult:
    """Recalcula precio + Greeks para un set de inputs dado."""
    inputs = PricingInputs(
        currency_pair="N/A", spot=S, strike=K, tenor_years=T,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=option_type,
    )
    precio = price_option(inputs).price
    g = compute_greeks(S, K, T, r_dom, r_for, sigma, option_type.value)

    return ScenarioResult(
        nombre=nombre,
        spot=S,
        volatility=sigma,
        rate_domestic=r_dom,
        rate_foreign=r_for,
        price=precio,
        price_change=precio - precio_base,
        price_change_pct=(precio - precio_base) / precio_base * 100,
        greeks=g,
    )


def shocks_individuales(
    S: float, K: float, T: float,
    r_dom: float, r_for: float, sigma: float,
    option_type: OptionType = OptionType.CALL,
) -> list[ScenarioResult]:
    """
    Aplica shocks individuales estándar: Spot ±5%/±8%,
    Volatilidad ±15%/±20%, Tasas +1%. Un shock a la vez,
    todo lo demás constante.
    """
    inputs_base = PricingInputs(
        currency_pair="N/A", spot=S, strike=K, tenor_years=T,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=option_type,
    )
    precio_base = price_option(inputs_base).price

    resultados = [
        _evaluar_escenario("Base", S, K, T, r_dom, r_for, sigma, option_type, precio_base),
        _evaluar_escenario("Spot +5%", S * 1.05, K, T, r_dom, r_for, sigma, option_type, precio_base),
        _evaluar_escenario("Spot -5%", S * 0.95, K, T, r_dom, r_for, sigma, option_type, precio_base),
        _evaluar_escenario("Spot +8%", S * 1.08, K, T, r_dom, r_for, sigma, option_type, precio_base),
        _evaluar_escenario("Spot -8%", S * 0.92, K, T, r_dom, r_for, sigma, option_type, precio_base),
        _evaluar_escenario("Vol +15%", S, K, T, r_dom, r_for, sigma * 1.15, option_type, precio_base),
        _evaluar_escenario("Vol -15%", S, K, T, r_dom, r_for, sigma * 0.85, option_type, precio_base),
        _evaluar_escenario("Vol +20%", S, K, T, r_dom, r_for, sigma * 1.20, option_type, precio_base),
        _evaluar_escenario("Vol -20%", S, K, T, r_dom, r_for, sigma * 0.80, option_type, precio_base),
        _evaluar_escenario("Tasas +1%", S, K, T, r_dom + 0.01, r_for + 0.01, sigma, option_type, precio_base),
    ]
    return resultados


def escenarios_combinados(
    S: float, K: float, T: float,
    r_dom: float, r_for: float, sigma: float,
    option_type: OptionType = OptionType.CALL,
) -> list[ScenarioResult]:
    """
    Escenarios con sentido económico conjunto (no combinatoria
    exhaustiva). Cada uno documenta la lógica de mercado que
    justifica mover esas variables juntas.
    """
    inputs_base = PricingInputs(
        currency_pair="N/A", spot=S, strike=K, tenor_years=T,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=option_type,
    )
    precio_base = price_option(inputs_base).price

    resultados = [
        # Crisis de tasas: bancos centrales suben tasas agresivamente,
        # la incertidumbre dispara la volatilidad.
        _evaluar_escenario(
            "Crisis de tasas", S, K, T,
            r_dom + 0.01, r_for + 0.01, sigma * 1.20,
            option_type, precio_base,
        ),
        # Flight to quality: huida hacia activos seguros, el spot cae
        # fuerte y la volatilidad se dispara (correlación negativa
        # típica en shocks de mercado).
        _evaluar_escenario(
            "Flight to quality", S * 0.92, K, T,
            r_dom, r_for, sigma * 1.20,
            option_type, precio_base,
        ),
        # Mercado calmo: escenario benigno, spot sube ligeramente y
        # la volatilidad cae (entorno de baja incertidumbre).
        _evaluar_escenario(
            "Mercado calmo", S * 1.02, K, T,
            r_dom, r_for, sigma * 0.85,
            option_type, precio_base,
        ),
    ]
    return resultados