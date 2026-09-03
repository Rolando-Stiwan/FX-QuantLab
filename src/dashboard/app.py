"""
app.py — Dashboard Streamlit de FX QuantLab, página de Resumen.

Consume la API (Módulo 6) vía HTTP — no llama directo a los módulos
de pricing/risk, para no duplicar lógica.

Requiere que la API esté corriendo en local:
    uvicorn src.api.main:app --reload
"""

import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="FX QuantLab", layout="wide")


@st.cache_data(ttl=300)
def get_market_data(currency_pair: str = "EURUSD") -> dict:
    response = requests.get(f"{API_URL}/market-data", params={"currency_pair": currency_pair})
    response.raise_for_status()
    return response.json()


def call_price(payload: dict) -> dict:
    response = requests.post(f"{API_URL}/price", json=payload)
    response.raise_for_status()
    return response.json()


def call_greeks(payload: dict) -> dict:
    response = requests.post(f"{API_URL}/greeks", json=payload)
    response.raise_for_status()
    return response.json()


def call_var(payload: dict) -> dict:
    response = requests.post(f"{API_URL}/var", json=payload)
    response.raise_for_status()
    return response.json()


st.title("FX QuantLab")
st.caption("Plataforma de pricing, riesgo y análisis de escenarios para opciones FX vanilla")

with st.expander("¿Qué hace esta herramienta? — leer antes de usar", expanded=True):
    st.markdown("""
    **Caso de uso**: un gestor comercial recibe una llamada — *"dentro de 90 días
    tengo que pagar 5 millones de euros, quiero protegerme si el EUR/USD sube,
    ¿cuánto me cuesta una opción?"* — esta plataforma responde esa pregunta con
    precio, riesgo y escenarios de mercado.

    **Cómo usarla**: ajusta los parámetros de la opción en el panel izquierdo.
    Cada input tiene una explicación si pasas el cursor sobre el ícono ⓘ o el
    texto de ayuda debajo. Los resultados (precio, Greeks, VaR/CVaR) se
    recalculan automáticamente al cambiar cualquier parámetro, excepto el
    riesgo (VaR/CVaR), que requiere presionar un botón porque su cálculo es
    más costoso (simula miles de escenarios de mercado).

    **Otras páginas** (barra lateral): *Mercado* muestra la evolución histórica
    del spot y la volatilidad; *Simulación* muestra la distribución completa
    de resultados posibles y escenarios de shock; *Sensibilidad* muestra cómo
    cambia el precio si se mueve una sola variable de forma continua.
    """)

# --- Sidebar: inputs ---
st.sidebar.header("Parámetros de la opción")

try:
    market = get_market_data("EURUSD")
except requests.exceptions.ConnectionError:
    st.error(
        "No se pudo conectar con la API. Verifica que esté corriendo: "
        "`uvicorn src.api.main:app --reload`"
    )
    st.stop()

st.sidebar.caption(f"Datos de mercado al {market['date']}")

spot = st.sidebar.number_input(
    "Spot (EUR/USD)",
    value=market["spot"],
    format="%.6f",
    help="El tipo de cambio actual entre euro y dólar — cuántos dólares "
         "cuesta 1 euro en este momento. Se toma automáticamente del "
         "último dato de mercado disponible.",
)

strike = st.sidebar.number_input(
    "Strike (K)",
    value=round(market["spot"] * 1.03, 4),
    format="%.4f",
    help="El tipo de cambio al que el titular de la opción tiene derecho "
         "a comprar o vender los euros, sin importar dónde esté el spot "
         "en ese momento. Es el 'precio de ejercicio' pactado hoy.",
)

tenor_days = st.sidebar.slider(
    "Tenor (días)",
    min_value=1, max_value=365, value=90,
    help="Cuántos días faltan para que la opción venza — el plazo o "
         "vencimiento del contrato. Ej.: si el pago que quieres cubrir "
         "es en 90 días, el tenor de la opción debería ser 90 días para "
         "que coincida con esa fecha.",
)

option_type = st.sidebar.selectbox(
    "Tipo de opción",
    ["call", "put"],
    help="'Call' = derecho a COMPRAR euros al strike pactado (protege "
         "contra una subida del EUR/USD — el caso de quien debe pagar en "
         "euros). 'Put' = derecho a VENDER euros al strike pactado "
         "(protege contra una caída del EUR/USD — el caso de quien va a "
         "recibir euros).",
)

vol_method = st.sidebar.selectbox(
    "Método de volatilidad",
    ["ewma", "rolling_20d", "rolling_60d", "rolling_252d"],
    index=0,
    help="Qué tan agitado ha estado el mercado recientemente, usado para "
         "estimar cuánto se puede mover el spot antes del vencimiento. "
         "'EWMA' da más peso a los movimientos recientes; los 'rolling' "
         "son promedios simples de los últimos 20/60/252 días.",
)
volatility = market[f"volatility_{vol_method}"]

r_dom = market["rate_domestic"]
r_for = market["rate_foreign"]

payload = {
    "spot": spot,
    "strike": strike,
    "tenor_years": tenor_days / 365,
    "rate_domestic": r_dom,
    "rate_foreign": r_for,
    "volatility": volatility,
    "option_type": option_type,
    "currency_pair": "EURUSD",
}

st.sidebar.divider()
st.sidebar.caption(
    f"Tasa USD: {r_dom:.4f} | Tasa EUR: {r_for:.4f} | "
    f"Volatilidad ({vol_method}): {volatility:.4f}"
)

# --- Cuerpo: resultados ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Precio")
    st.caption("Cuánto cuesta hoy comprar esta opción (por cada euro nocional).")
    price_result = call_price(payload)
    st.metric("Precio de la opción", f"{price_result['price']:.6f}")
    st.caption(f"d1 = {price_result['d1']:.4f} | d2 = {price_result['d2']:.4f}")

    st.subheader("Griegas")
    st.caption("Qué tan sensible es el precio a cambios en el mercado.")
    greeks_result = call_greeks(payload)
    g1, g2, g3 = st.columns(3)
    g1.metric("Delta", f"{greeks_result['delta']:.4f}", help="Cuánto cambia el precio si el spot sube 1 unidad.")
    g2.metric("Gamma", f"{greeks_result['gamma']:.4f}", help="Cuánto cambia el Delta si el spot se mueve — mide la curvatura.")
    g3.metric("Vega", f"{greeks_result['vega']:.4f}", help="Cuánto cambia el precio si la volatilidad sube 1 punto porcentual.")
    g4, g5 = st.columns(2)
    g4.metric("Theta (por día)", f"{greeks_result['theta']:.6f}", help="Cuánto valor pierde la opción cada día que pasa, sin que cambie nada más.")
    g5.metric("Rho dom / for", f"{greeks_result['rho_dom']:.4f} / {greeks_result['rho_for']:.4f}", help="Sensibilidad a la tasa de interés en USD y en EUR, respectivamente.")

with col2:
    st.subheader("Riesgo (VaR / CVaR)")
    st.caption(
        "Cuánto se podría perder en un escenario adverso. Simulado vía "
        "Monte Carlo, horizonte 1 día, 95% de confianza."
    )

    if st.button("Calcular VaR/CVaR"):
        var_payload = {**payload, "horizon_days": 1, "n_simulations": 10_000, "confidence": 0.95}
        with st.spinner("Simulando 10,000 escenarios de mercado..."):
            var_result = call_var(var_payload)
        v1, v2 = st.columns(2)
        v1.metric("VaR 95%", f"{var_result['var']:.6f}", help="Con 95% de confianza, la pérdida en 1 día no debería superar este valor.")
        v2.metric("CVaR 95%", f"{var_result['cvar']:.6f}", help="Si la pérdida SÍ supera el VaR, este es el promedio de qué tan grande sería.")
    else:
        st.info(
            "El cálculo de riesgo simula miles de escenarios de mercado, así "
            "que no se recalcula automáticamente al mover los sliders — "
            "presiona el botón cuando quieras verlo para la configuración actual."
        )