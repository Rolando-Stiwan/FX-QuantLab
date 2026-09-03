import pytest

from src.pricing.garman_kohlhagen import OptionType
from src.simulation.scenarios import shocks_individuales, escenarios_combinados

S = 1.166
K = 1.20
T = 90 / 365
R_DOM = 0.0386
R_FOR = 0.0219
SIGMA = 0.045

PRECIO_BASE_CONOCIDO = 0.001793  # ya validado en Módulo 2


@pytest.fixture
def shocks():
    return {r.nombre: r for r in shocks_individuales(S, K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL)}


@pytest.fixture
def combinados():
    return {r.nombre: r for r in escenarios_combinados(S, K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL)}


def test_base_coincide_con_precio_conocido_de_modulo_2(shocks):
    """El escenario Base no debe introducir ninguna desviación sobre price_option()."""
    assert shocks["Base"].price == pytest.approx(PRECIO_BASE_CONOCIDO, abs=1e-6)
    assert shocks["Base"].price_change == pytest.approx(0.0, abs=1e-9)


def test_delta_crece_monotonicamente_con_spot_al_alza(shocks):
    """Para una call, a mayor spot, mayor Delta (más profunda en el dinero)."""
    delta_base = shocks["Base"].greeks["delta"]
    delta_5 = shocks["Spot +5%"].greeks["delta"]
    delta_8 = shocks["Spot +8%"].greeks["delta"]
    assert delta_base < delta_5 < delta_8


def test_delta_decrece_monotonicamente_con_spot_a_la_baja(shocks):
    """Para una call, a menor spot, menor Delta (más lejos del dinero)."""
    delta_base = shocks["Base"].greeks["delta"]
    delta_neg5 = shocks["Spot -5%"].greeks["delta"]
    delta_neg8 = shocks["Spot -8%"].greeks["delta"]
    assert delta_neg8 < delta_neg5 < delta_base


def test_mayor_volatilidad_aumenta_precio_de_call(shocks):
    """Vega positiva: más volatilidad siempre aumenta el valor de una opción vanilla."""
    precio_base = shocks["Base"].price
    assert shocks["Vol +15%"].price > precio_base
    assert shocks["Vol +20%"].price > precio_base
    assert shocks["Vol -15%"].price < precio_base
    assert shocks["Vol -20%"].price < precio_base


def test_shock_mayor_de_vol_tiene_mayor_efecto(shocks):
    """Vol +20% debe alejarse más del precio base que Vol +15% (mismo signo)."""
    precio_base = shocks["Base"].price
    cambio_15 = abs(shocks["Vol +15%"].price - precio_base)
    cambio_20 = abs(shocks["Vol +20%"].price - precio_base)
    assert cambio_20 > cambio_15


def test_precios_nunca_negativos(shocks, combinados):
    """Ningún escenario, individual o combinado, debe dar precio negativo."""
    for r in list(shocks.values()) + list(combinados.values()):
        assert r.price >= 0


def test_flight_to_quality_precio_cercano_a_cero(combinados):
    """
    Observación documentada: el shock de spot domina sobre el de
    volatilidad cuando la opción está muy OTM, llevando el precio
    a prácticamente cero pese al aumento de volatilidad.
    """
    assert combinados["Flight to quality"].price == pytest.approx(0.0, abs=1e-4)