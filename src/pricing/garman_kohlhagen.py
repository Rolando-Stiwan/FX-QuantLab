"""
Motor de pricing Garman-Kohlhagen para opciones FX europeas.

Diseño: calculadora pura — no accede a la base de datos ni a ninguna
fuente externa. Recibe todos los inputs como parámetros y devuelve
el precio. La obtención de datos de mercado (spot, tasas, volatilidad)
es responsabilidad de otro módulo (API, dashboard, o un helper de
"market data lookup" que aún no se ha construido).

Garman-Kohlhagen es la extensión de Black-Scholes para divisas: trata
cada divisa como un activo con su propia tasa de interés (r_dom, r_for).
"""

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


@dataclass
class PricingInputs:
    """
    Todos los inputs necesarios para un cálculo de Garman-Kohlhagen.

    currency_pair: identificador del par, ej. 'EURUSD'. No se usa en
                   el cálculo matemático en sí, pero viaja junto a los
                   inputs para trazabilidad (saber a qué par corresponde
                   este resultado cuando se combinan resultados de
                   varios pares más adelante).
    spot:          precio spot actual (S)
    strike:        precio de ejercicio (K)
    tenor_years:   tiempo a vencimiento en años (T). Ej. 90 días = 90/365
    volatility:    volatilidad anualizada (sigma), como decimal (0.045 = 4.5%)
    rate_domestic: tasa doméstica anualizada (r_dom), como decimal
    rate_foreign:  tasa extranjera anualizada (r_for), como decimal
    option_type:   CALL o PUT
    """
    currency_pair: str
    spot: float
    strike: float
    tenor_years: float
    volatility: float
    rate_domestic: float
    rate_foreign: float
    option_type: OptionType

    def __post_init__(self):
        if self.spot <= 0 or self.strike <= 0:
            raise ValueError("Spot y strike deben ser positivos")
        if self.tenor_years <= 0:
            raise ValueError("El tenor debe ser positivo (usar valor intrínseco si T=0)")
        if self.volatility < 0:
            raise ValueError("La volatilidad no puede ser negativa")


@dataclass
class PricingResult:
    """Resultado del cálculo, con detalle de los términos intermedios (d1, d2)."""
    currency_pair: str
    option_type: OptionType
    price: float
    d1: float
    d2: float


def _compute_d1_d2(inputs: PricingInputs) -> tuple[float, float]:
    """Términos d1 y d2 de la fórmula, compartidos entre call y put."""
    S, K, T = inputs.spot, inputs.strike, inputs.tenor_years
    sigma, r_dom, r_for = inputs.volatility, inputs.rate_domestic, inputs.rate_foreign

    d1 = (np.log(S / K) + (r_dom - r_for + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def price_option(inputs: PricingInputs) -> PricingResult:
    """
    Calcula el precio de una opción europea FX vía Garman-Kohlhagen.

    Call: C = S * exp(-r_for*T) * N(d1) - K * exp(-r_dom*T) * N(d2)
    Put:  P = K * exp(-r_dom*T) * N(-d2) - S * exp(-r_for*T) * N(-d1)
    """
    S, K, T = inputs.spot, inputs.strike, inputs.tenor_years
    r_dom, r_for = inputs.rate_domestic, inputs.rate_foreign

    d1, d2 = _compute_d1_d2(inputs)

    domestic_discount = np.exp(-r_dom * T)
    foreign_discount = np.exp(-r_for * T)

    if inputs.option_type == OptionType.CALL:
        price = S * foreign_discount * norm.cdf(d1) - K * domestic_discount * norm.cdf(d2)
    else:
        price = K * domestic_discount * norm.cdf(-d2) - S * foreign_discount * norm.cdf(-d1)

    return PricingResult(
        currency_pair=inputs.currency_pair,
        option_type=inputs.option_type,
        price=round(float(price), 6),
        d1=round(float(d1), 6),
        d2=round(float(d2), 6),
    )


if __name__ == "__main__":
    # Prueba rápida con el caso de uso guía: cobertura de pago EUR
    # (comprar un CALL EUR/USD para protegerse de que el euro suba)
    example = PricingInputs(
        currency_pair="EURUSD",
        spot=1.166,
        strike=1.20,
        tenor_years=90 / 365,
        volatility=0.045,   # EWMA del día, tomado de tu última prueba real
        rate_domestic=0.0386,
        rate_foreign=0.0219,
        option_type=OptionType.CALL,
    )
    result = price_option(example)
    print(f"Precio: {result.price}")
    print(f"d1={result.d1}, d2={result.d2}")