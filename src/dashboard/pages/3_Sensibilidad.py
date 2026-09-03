"""
3_Sensibilidad.py — Página de Sensibilidad: curvas de precio vs.
strike, volatilidad y tiempo a vencimiento.

Genera cada curva con un loop de llamadas a /price (instantáneo,
fórmula cerrada) — no se añade un endpoint nuevo a la API para esto,
dado el bajo costo de 30-50 llamadas a un cálculo ya rápido.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="FX QuantLab — Sensibilidad", layout="wide")


@st.cache_data(ttl=300)
def get_market_data(currency_pair: str = "EURUSD") -> dict:
    response = requests.get(f"{API_URL}/market-data", params={"currency_pair": currency_pair})
    response.raise_for_status()
    return response.json()


def call_price(payload: dict) -> float:
    response = requests.post(f"{API_URL}/price", json=payload)
    response.raise_for_status()
    return response.json()["price"]


@st.cache_data(ttl=60)
def curva_vs_strike(base_payload: dict, spot: float, n_puntos: int = 30) -> pd.DataFrame:
    strikes = np.linspace(spot * 0.85, spot * 1.15, n_puntos)
    precios = []
    for k in strikes:
        payload = {**base_payload, "strike": float(k)}
        precios.append(call_price(payload))
    return pd.DataFrame({"strike": strikes, "precio": precios}).set_index("strike")


@st.cache_data(ttl=60)
def curva_vs_volatilidad(base_payload: dict, n_puntos: int = 30) -> pd.DataFrame:
    vols = np.linspace(0.01, 0.15, n_puntos)
    precios = []
    for v in vols:
        payload = {**base_payload, "volatility": float(v)}
        precios.append(call_price(payload))
    return pd.DataFrame({"volatilidad": vols, "precio": precios}).set_index("volatilidad")


@st.cache_data(ttl=60)
def curva_vs_tiempo(base_payload: dict, n_puntos: int = 30) -> pd.DataFrame:
    dias = np.linspace(2, 365, n_puntos)
    precios = []
    for d in dias:
        payload = {**base_payload, "tenor_years": float(d) / 365}
        precios.append(call_price(payload))
    return pd.DataFrame({"dias_a_vencimiento": dias, "precio": precios}).set_index("dias_a_vencimiento")


st.title("Sensibilidad")
st.caption("Curvas de precio vs. strike, volatilidad y tiempo a vencimiento — EUR/USD")

try:
    market = get_market_data("EURUSD")
except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar con la API. Verifica que esté corriendo.")
    st.stop()

st.sidebar.header("Parámetros base")
spot = st.sidebar.number_input("Spot (EUR/USD)", value=market["spot"], format="%.6f")
strike = st.sidebar.number_input("Strike (K)", value=round(market["spot"] * 1.03, 4), format="%.4f")
tenor_days = st.sidebar.slider("Tenor (días)", min_value=2, max_value=365, value=90)
option_type = st.sidebar.selectbox("Tipo de opción", ["call", "put"])
volatility = market["volatility_ewma"]

base_payload = {
    "spot": spot,
    "strike": strike,
    "tenor_years": tenor_days / 365,
    "rate_domestic": market["rate_domestic"],
    "rate_foreign": market["rate_foreign"],
    "volatility": volatility,
    "option_type": option_type,
    "currency_pair": "EURUSD",
}

st.subheader("Precio vs. Strike")
st.caption(f"Spot fijo en {spot:.4f}, volatilidad {volatility:.4f}, tenor {tenor_days} días")
df_strike = curva_vs_strike(base_payload, spot)
st.line_chart(df_strike)

st.subheader("Precio vs. Volatilidad")
st.caption(f"Strike fijo en {strike:.4f}, tenor {tenor_days} días")
df_vol = curva_vs_volatilidad(base_payload)
st.line_chart(df_vol)

st.subheader("Precio vs. Tiempo a vencimiento")
st.caption(f"Strike fijo en {strike:.4f}, volatilidad {volatility:.4f}")
df_tiempo = curva_vs_tiempo(base_payload)
st.line_chart(df_tiempo)