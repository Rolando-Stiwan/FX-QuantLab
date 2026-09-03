"""
models.py — Modelos Pydantic compartidos por los endpoints de la API.

Un solo modelo de request base (PricingRequest) reutilizado en
/price, /greeks, /var, /simulate — evita duplicar validación de
los mismos 7 campos en cuatro lugares distintos.
"""

from pydantic import BaseModel, Field
from typing import Literal


class PricingRequest(BaseModel):
    """Inputs estándar de una opción FX vanilla bajo Garman-Kohlhagen."""
    spot: float = Field(..., gt=0, description="Precio spot actual (S)")
    strike: float = Field(..., gt=0, description="Precio de ejercicio (K)")
    tenor_years: float = Field(..., gt=0, description="Tiempo a vencimiento en años (ej. 90/365)")
    rate_domestic: float = Field(..., description="Tasa doméstica anualizada, decimal (ej. 0.0386)")
    rate_foreign: float = Field(..., description="Tasa extranjera anualizada, decimal (ej. 0.0219)")
    volatility: float = Field(..., gt=0, description="Volatilidad anualizada, decimal (ej. 0.045)")
    option_type: Literal["call", "put"] = "call"
    currency_pair: str = "EURUSD"


class VarRequest(PricingRequest):
    """PricingRequest + parámetros específicos de VaR/CVaR."""
    horizon_days: int = Field(1, gt=0, description="Horizonte de riesgo en días")
    n_simulations: int = Field(
        10_000, gt=0, le=100_000,
        description="Número de simulaciones Monte Carlo. Default bajo (10,000) "
                    "por límite de memoria en Streamlit Cloud — subir solo si "
                    "el entorno de despliegue lo permite.",
    )
    confidence: float = Field(0.95, gt=0, lt=1, description="Nivel de confianza (ej. 0.95, 0.99)")
    seed: int | None = Field(None, description="Semilla para reproducibilidad (opcional)")


class PriceResponse(BaseModel):
    currency_pair: str
    option_type: str
    price: float
    d1: float
    d2: float


class GreeksResponse(BaseModel):
    delta: float
    gamma: float
    vega: float
    theta: float
    rho_dom: float
    rho_for: float


class VarResponse(BaseModel):
    precio_hoy: float
    var: float
    cvar: float
    horizon_days: int
    confidence: float
    n_simulations: int


class ScenarioItem(BaseModel):
    nombre: str
    spot: float
    volatility: float
    rate_domestic: float
    rate_foreign: float
    price: float
    price_change: float
    price_change_pct: float
    greeks: GreeksResponse


class SimulateResponse(BaseModel):
    shocks_individuales: list[ScenarioItem]
    escenarios_combinados: list[ScenarioItem]


class MarketDataResponse(BaseModel):
    currency_pair: str
    date: str
    spot: float | None
    rate_domestic: float | None
    rate_foreign: float | None
    volatility_ewma: float | None
    volatility_rolling_20d: float | None
    volatility_rolling_60d: float | None
    volatility_rolling_252d: float | None

class VarResponse(BaseModel):
    precio_hoy: float
    var: float
    cvar: float
    horizon_days: int
    confidence: float
    n_simulations: int
    pnl_distribution: list[float]