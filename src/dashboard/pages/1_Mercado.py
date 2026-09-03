"""
1_Mercado.py — Página de Mercado: evolución del spot, volatilidad
histórica, y distribución de retornos.

Consume /market-data/history de la API (Módulo 6).
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="FX QuantLab — Mercado", layout="wide")


@st.cache_data(ttl=300)
def get_market_history(currency_pair: str, days: int) -> dict:
    response = requests.get(
        f"{API_URL}/market-data/history",
        params={"currency_pair": currency_pair, "days": days},
    )
    response.raise_for_status()
    return response.json()


st.title("Mercado")
st.caption("Evolución histórica de spot, volatilidad y retornos — EUR/USD")

st.sidebar.header("Rango de histórico")
rango = st.sidebar.selectbox(
    "Días a mostrar",
    options=[30, 90, 180, 365, -1],
    format_func=lambda x: "Todo el histórico" if x == -1 else f"Últimos {x} días",
    index=2,  # default 180
)

try:
    history = get_market_history("EURUSD", rango)
except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar con la API. Verifica que esté corriendo.")
    st.stop()
except requests.exceptions.HTTPError:
    st.warning("No hay suficiente histórico disponible para este rango.")
    st.stop()

# --- Spot histórico ---
st.subheader("Evolución del spot (EUR/USD)")
df_spot = pd.DataFrame(history["spot"])
df_spot["date"] = pd.to_datetime(df_spot["date"])
df_spot = df_spot.set_index("date")
st.line_chart(df_spot["value"])

# --- Volatilidad histórica (las 4 métricas) ---
st.subheader("Volatilidad histórica")
vol_method = st.selectbox(
    "Método", ["ewma", "rolling_20d", "rolling_60d", "rolling_252d"], index=0
)
df_vol = pd.DataFrame(history["volatility"][vol_method])
if df_vol.empty:
    st.info(f"Sin datos suficientes para {vol_method} en este rango.")
else:
    df_vol["date"] = pd.to_datetime(df_vol["date"])
    df_vol = df_vol.set_index("date")
    st.line_chart(df_vol["value"])

# --- Distribución de retornos (calculada aquí, no viene de la API) ---
st.subheader("Distribución de retornos diarios (log-returns)")
if len(df_spot) > 1:
    log_returns = np.log(df_spot["value"] / df_spot["value"].shift(1)).dropna()
    st.bar_chart(log_returns)
    col1, col2, col3 = st.columns(3)
    col1.metric("Media diaria", f"{log_returns.mean():.6f}")
    col2.metric("Desv. estándar diaria", f"{log_returns.std():.6f}")
    col3.metric("Vol. anualizada implícita", f"{log_returns.std() * np.sqrt(252):.4f}")
else:
    st.info("Histórico insuficiente para calcular retornos.")