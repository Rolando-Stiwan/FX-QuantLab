import numpy as np
import pytest

from src.pricing.greeks import greeks

# Mismo caso de prueba que Módulo 2
S = 1.166
K = 1.20
T = 90 / 365
R_DOM = 0.05
R_FOR = 0.03
SIGMA = 0.08


@pytest.fixture
def g_call():
    return greeks(S, K, T, R_DOM, R_FOR, SIGMA, "call")


@pytest.fixture
def g_put():
    return greeks(S, K, T, R_DOM, R_FOR, SIGMA, "put")


def test_delta_call_dentro_de_limites(g_call):
    """Delta de una call debe estar entre 0 y e^{-r_for*T}."""
    techo = np.exp(-R_FOR * T)
    assert 0 <= g_call["delta"] <= techo


def test_gamma_igual_call_put(g_call, g_put):
    """Gamma es idéntica para call y put (misma fórmula matemática)."""
    assert g_call["gamma"] == pytest.approx(g_put["gamma"])


def test_put_call_parity_delta(g_call, g_put):
    """Delta_call - Delta_put debe ser exactamente e^{-r_for*T}."""
    techo = np.exp(-R_FOR * T)
    diff = g_call["delta"] - g_put["delta"]
    assert diff == pytest.approx(techo)