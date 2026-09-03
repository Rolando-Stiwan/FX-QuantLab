import numpy as np
import pytest

from src.pricing.garman_kohlhagen import PricingInputs, OptionType, price_option
from src.pricing.var_cvar import _price_vectorized, simulate_var_cvar

S, K, T = 1.166, 1.20, 90 / 365
R_DOM, R_FOR, SIGMA = 0.0386, 0.0219, 0.045


def test_price_vectorized_coincide_con_price_option():
    """_price_vectorized debe dar el mismo precio que la función oficial."""
    inputs = PricingInputs(
        currency_pair="EURUSD", spot=S, strike=K, tenor_years=T,
        volatility=SIGMA, rate_domestic=R_DOM, rate_foreign=R_FOR,
        option_type=OptionType.CALL,
    )
    precio_oficial = price_option(inputs).price
    precio_vectorizado = _price_vectorized(
        np.array([S]), K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL
    )[0]
    assert precio_vectorizado == pytest.approx(precio_oficial, abs=1e-6)


def test_var_cvar_positivos():
    """VaR y CVaR deben ser positivos (representan magnitud de pérdida)."""
    resultado = simulate_var_cvar(
        S, K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL,
        horizon_days=1, n_simulations=50_000, confidence=0.95, seed=42,
    )
    assert resultado["var"] > 0
    assert resultado["cvar"] > 0


def test_cvar_mayor_o_igual_que_var():
    """CVaR (promedio de la cola) siempre debe ser >= VaR (percentil)."""
    resultado = simulate_var_cvar(
        S, K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL,
        horizon_days=1, n_simulations=50_000, confidence=0.95, seed=42,
    )
    assert resultado["cvar"] >= resultado["var"]