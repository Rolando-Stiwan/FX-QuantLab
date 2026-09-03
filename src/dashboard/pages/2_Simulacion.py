"""
2_Simulacion.py — Página de Simulación: distribución de precios/P&L
futuros vía Monte Carlo, y escenarios de shock.

Consume /var (para la distribución Monte Carlo) y /simulate (para
shocks individuales y escenarios combinados) de la API.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="FX QuantLab — Simulación", layout="wide")


@st.cache_data(ttl=300)
def get_market_data(currency_pair: str = "EURUSD") -> dict:
    response = requests.get(f"{API_URL}/market-data", params={"currency_pair": currency_pair})
    response.raise_for_status()
    return response.json()


def call_var(payload: dict) -> dict:
    response = requests.post(f"{API_URL}/var", json=payload)
    response.raise_for_status()
    return response.json()


def call_simulate(payload: dict) -> dict:
    response = requests.post(f"{API_URL}/simulate", json=payload)
    response.raise_for_status()
    return response.json()


st.title("Simulación")
st.caption("Distribución Monte Carlo de P&L y escenarios de shock — EUR/USD")

try:
    market = get_market_data("EURUSD")
except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar con la API. Verifica que esté corriendo.")
    st.stop()

st.sidebar.header("Parámetros de la opción")
spot = st.sidebar.number_input("Spot (EUR/USD)", value=market["spot"], format="%.6f")
strike = st.sidebar.number_input("Strike (K)", value=round(market["spot"] * 1.03, 4), format="%.4f")
tenor_days = st.sidebar.slider("Tenor (días)", min_value=2, max_value=365, value=90)
option_type = st.sidebar.selectbox("Tipo de opción", ["call", "put"])
volatility = market["volatility_ewma"]

payload_base = {
    "spot": spot,
    "strike": strike,
    "tenor_years": tenor_days / 365,
    "rate_domestic": market["rate_domestic"],
    "rate_foreign": market["rate_foreign"],
    "volatility": volatility,
    "option_type": option_type,
    "currency_pair": "EURUSD",
}

# --- Distribución Monte Carlo de P&L ---
st.subheader("Distribución de P&L (Monte Carlo)")

horizon = st.sidebar.slider("Horizonte de riesgo (días)", min_value=1, max_value=tenor_days - 1, value=1)

if st.button("Correr simulación Monte Carlo"):
    var_payload = {**payload_base, "horizon_days": horizon, "n_simulations": 10_000, "confidence": 0.95}
    with st.spinner("Simulando 10,000 trayectorias..."):
        var_result = call_var(var_payload)

    pnl = pd.Series(var_result["pnl_distribution"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Precio hoy", f"{var_result['precio_hoy']:.6f}")
    col2.metric("VaR 95%", f"{var_result['var']:.6f}")
    col3.metric("CVaR 95%", f"{var_result['cvar']:.6f}")

    st.bar_chart(pnl)
    st.caption(
        f"Distribución de {var_result['n_simulations']:,} escenarios simulados de P&L "
        f"a {horizon} día(s). Barra roja mental en -VaR: el 5% de los escenarios cae "
        f"más allá de ese punto."
    )
else:
    st.info("Presiona el botón para correr la simulación Monte Carlo (costoso, no automático).")

st.divider()

# --- Escenarios de shock ---
st.subheader("Escenarios de shock")

resultado = call_simulate(payload_base)

st.markdown("**Shocks individuales**")
df_shocks = pd.DataFrame(resultado["shocks_individuales"])
df_shocks_display = df_shocks[["nombre", "price", "price_change", "price_change_pct"]]
df_shocks_display.columns = ["Escenario", "Precio", "Δ Precio", "Δ %"]
st.dataframe(df_shocks_display, use_container_width=True, hide_index=True)

st.markdown("**Escenarios combinados (sentido económico)**")
df_comb = pd.DataFrame(resultado["escenarios_combinados"])
df_comb_display = df_comb[["nombre", "price", "price_change", "price_change_pct"]]
df_comb_display.columns = ["Escenario", "Precio", "Δ Precio", "Δ %"]
st.dataframe(df_comb_display, use_container_width=True, hide_index=True)