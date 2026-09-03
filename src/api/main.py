"""
main.py — API FastAPI de FX QuantLab.

Endpoints:
  POST /price     → precio Garman-Kohlhagen (Módulo 2)
  POST /greeks    → Griegas analíticas (Módulo 3)
  POST /var       → VaR/CVaR Monte Carlo (Módulo 3)
  POST /simulate  → Shocks + escenarios combinados (Módulo 4)
  GET  /market-data → último snapshot de mercado desde SQLite (Módulo 1)

No contiene lógica de cálculo propia — es una capa delgada que
llama a los módulos ya validados de pricing/risk/simulation.
"""

from fastapi import FastAPI, HTTPException

from src.api.models import (
    PricingRequest, VarRequest,
    PriceResponse, GreeksResponse, VarResponse,
    SimulateResponse, MarketDataResponse,
)
from src.api.market_data import get_latest_market_data, get_market_history

from src.pricing.garman_kohlhagen import PricingInputs, OptionType, price_option
from src.pricing.greeks import greeks as compute_greeks
from src.pricing.var_cvar import simulate_var_cvar
from src.simulation.scenarios import shocks_individuales, escenarios_combinados

app = FastAPI(
    title="FX QuantLab API",
    description="Plataforma de pricing, riesgo y análisis de escenarios para opciones FX vanilla.",
    version="1.0.0",
)


@app.post("/price", response_model=PriceResponse)
def price(req: PricingRequest):
    inputs = PricingInputs(
        currency_pair=req.currency_pair,
        spot=req.spot,
        strike=req.strike,
        tenor_years=req.tenor_years,
        volatility=req.volatility,
        rate_domestic=req.rate_domestic,
        rate_foreign=req.rate_foreign,
        option_type=OptionType(req.option_type),
    )
    result = price_option(inputs)
    return PriceResponse(
        currency_pair=result.currency_pair,
        option_type=result.option_type.value,
        price=result.price,
        d1=result.d1,
        d2=result.d2,
    )


@app.post("/greeks", response_model=GreeksResponse)
def greeks_endpoint(req: PricingRequest):
    g = compute_greeks(
        req.spot, req.strike, req.tenor_years,
        req.rate_domestic, req.rate_foreign, req.volatility,
        req.option_type,
    )
    return GreeksResponse(**g)


@app.post("/var", response_model=VarResponse)
def var_endpoint(req: VarRequest):
    try:
        result = simulate_var_cvar(
            S=req.spot, K=req.strike, T=req.tenor_years,
            r_dom=req.rate_domestic, r_for=req.rate_foreign, sigma=req.volatility,
            option_type=OptionType(req.option_type),
            horizon_days=req.horizon_days,
            n_simulations=req.n_simulations,
            confidence=req.confidence,
            seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return VarResponse(
        precio_hoy=result["precio_hoy"],
        var=result["var"],
        cvar=result["cvar"],
        horizon_days=result["horizon_days"],
        confidence=result["confidence"],
        n_simulations=result["n_simulations"],
        pnl_distribution=result["pnl_distribution"].tolist(),  # numpy array → lista para JSON
    )


@app.post("/simulate", response_model=SimulateResponse)
def simulate_endpoint(req: PricingRequest):
    option_type = OptionType(req.option_type)
    args = (req.spot, req.strike, req.tenor_years, req.rate_domestic, req.rate_foreign, req.volatility)

    individuales = shocks_individuales(*args, option_type)
    combinados = escenarios_combinados(*args, option_type)

    def _to_item(r):
        return {
            "nombre": r.nombre,
            "spot": r.spot,
            "volatility": r.volatility,
            "rate_domestic": r.rate_domestic,
            "rate_foreign": r.rate_foreign,
            "price": r.price,
            "price_change": r.price_change,
            "price_change_pct": r.price_change_pct,
            "greeks": r.greeks,
        }

    return SimulateResponse(
        shocks_individuales=[_to_item(r) for r in individuales],
        escenarios_combinados=[_to_item(r) for r in combinados],
    )


@app.get("/market-data", response_model=MarketDataResponse)
def market_data_endpoint(currency_pair: str = "EURUSD"):
    data = get_latest_market_data(currency_pair)
    if data["spot"] is None:
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos de spot guardados para {currency_pair}",
        )
    return MarketDataResponse(**data)


@app.get("/market-data/history")
def market_history_endpoint(currency_pair: str = "EURUSD", days: int = 180):
    data = get_market_history(currency_pair, days)
    if not data["spot"]:
        raise HTTPException(
            status_code=404,
            detail=f"No hay histórico de spot para {currency_pair}",
        )
    return data


@app.get("/")
def root():
    return {"status": "ok", "service": "FX QuantLab API"}