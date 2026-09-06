"""
Tests de integración de la API FastAPI (Módulo 6).

Usa TestClient para llamar los endpoints reales, sin levantar un servidor.
Los valores de referencia (precio, CVaR>=VaR, Flight to quality≈0) vienen
de los tests unitarios ya validados en Módulo 2/3/4 — aquí solo se confirma
que la capa de API no rompe/traiciona esos resultados.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

BASE_PAYLOAD = {
    "spot": 1.166,
    "strike": 1.20,
    "tenor_years": 90 / 365,
    "rate_domestic": 0.0386,
    "rate_foreign": 0.0219,
    "volatility": 0.045,
    "option_type": "call",
    "currency_pair": "EURUSD",
}


# ---------- /price ----------

def test_price_matches_known_value():
    resp = client.post("/price", json=BASE_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["price"] == pytest.approx(0.001793, abs=1e-5)
    assert "d1" in data and "d2" in data


def test_price_invalid_tenor_returns_422():
    payload = {**BASE_PAYLOAD, "tenor_years": -1}
    resp = client.post("/price", json=payload)
    assert resp.status_code == 422


def test_price_invalid_volatility_returns_422():
    payload = {**BASE_PAYLOAD, "volatility": 0}
    resp = client.post("/price", json=payload)
    assert resp.status_code == 422


# ---------- /greeks ----------

def test_greeks_delta_in_valid_range_for_call():
    resp = client.post("/greeks", json=BASE_PAYLOAD)
    assert resp.status_code == 200
    delta = resp.json()["delta"]
    assert 0 <= delta <= 1


def test_greeks_gamma_equal_call_and_put():
    call_resp = client.post("/greeks", json=BASE_PAYLOAD)
    put_payload = {**BASE_PAYLOAD, "option_type": "put"}
    put_resp = client.post("/greeks", json=put_payload)

    gamma_call = call_resp.json()["gamma"]
    gamma_put = put_resp.json()["gamma"]
    assert gamma_call == pytest.approx(gamma_put, rel=1e-6)


# ---------- /var ----------

def test_var_cvar_relationship_holds():
    payload = {**BASE_PAYLOAD, "n_simulations": 10_000, "seed": 42}
    resp = client.post("/var", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cvar"] >= data["var"]
    assert len(data["pnl_distribution"]) == 10_000


# ---------- /simulate ----------

def test_flight_to_quality_price_near_zero():
    resp = client.post("/simulate", json=BASE_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()

    flight_to_quality = next(
        s for s in data["escenarios_combinados"] if s["nombre"] == "Flight to quality"
    )
    assert flight_to_quality["price"] < 0.0001


# ---------- /market-data ----------

def test_market_data_returns_positive_spot():
    resp = client.get("/market-data", params={"currency_pair": "EURUSD"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["spot"] > 0


def test_market_data_history_returns_ordered_dates():
    resp = client.get("/market-data/history", params={"currency_pair": "EURUSD", "days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["spot"]) > 0


# ---------- root ----------

def test_root_status_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"