"""
Validación de casos límite y put-call parity para Garman-Kohlhagen.

Estos checks no requieren datos de mercado externos (no hay precios
de opciones FX gratuitos para comparar) — son propiedades matemáticas
que la fórmula DEBE cumplir siempre, sin importar los inputs. Sirven
como red de seguridad: si algún día se rompe alguno de estos checks,
hay un bug en la implementación.
"""

import numpy as np

from src.pricing.garman_kohlhagen import OptionType, PricingInputs, price_option


def check_limit_sigma_zero(spot: float, strike: float, tenor_years: float,
                            r_dom: float, r_for: float) -> dict:
    """
    Cuando sigma -> 0 (sin incertidumbre), el precio de un call debe
    converger al valor intrínseco descontado:

        Call = max(S*exp(-r_for*T) - K*exp(-r_dom*T), 0)

    Se usa un sigma muy pequeño (no exactamente 0, para evitar división
    por cero en d1/d2) y se compara contra el valor teórico esperado.
    """
    tiny_sigma = 1e-6

    inputs = PricingInputs(
        currency_pair="EURUSD", spot=spot, strike=strike, tenor_years=tenor_years,
        volatility=tiny_sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=OptionType.CALL,
    )
    computed_price = price_option(inputs).price

    expected_price = max(
        spot * np.exp(-r_for * tenor_years) - strike * np.exp(-r_dom * tenor_years), 0.0
    )

    difference = abs(computed_price - expected_price)
    return {
        "check": "sigma -> 0 converge a valor intrínseco descontado",
        "computed": round(computed_price, 6),
        "expected": round(expected_price, 6),
        "difference": round(difference, 8),
        "passed": difference < 1e-4,
    }


def check_limit_tenor_zero(spot: float, strike: float, sigma: float,
                            r_dom: float, r_for: float) -> dict:
    """
    Cuando T -> 0 (vencimiento inmediato), el precio de un call debe
    converger al payoff inmediato sin descuento: max(S - K, 0).
    """
    tiny_tenor = 1e-6

    inputs = PricingInputs(
        currency_pair="EURUSD", spot=spot, strike=strike, tenor_years=tiny_tenor,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=OptionType.CALL,
    )
    computed_price = price_option(inputs).price
    expected_price = max(spot - strike, 0.0)

    difference = abs(computed_price - expected_price)
    return {
        "check": "T -> 0 converge a max(S-K, 0)",
        "computed": round(computed_price, 6),
        "expected": round(expected_price, 6),
        "difference": round(difference, 8),
        "passed": difference < 1e-3,
    }


def check_put_call_parity(spot: float, strike: float, tenor_years: float,
                           sigma: float, r_dom: float, r_for: float) -> dict:
    """
    Put-call parity para opciones FX (Garman-Kohlhagen):

        C - P = S*exp(-r_for*T) - K*exp(-r_dom*T)

    Debe cumplirse exactamente (dentro de tolerancia numérica), sin
    importar los valores de S, K, T, sigma, r_dom, r_for.
    """
    call_inputs = PricingInputs(
        currency_pair="EURUSD", spot=spot, strike=strike, tenor_years=tenor_years,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=OptionType.CALL,
    )
    put_inputs = PricingInputs(
        currency_pair="EURUSD", spot=spot, strike=strike, tenor_years=tenor_years,
        volatility=sigma, rate_domestic=r_dom, rate_foreign=r_for,
        option_type=OptionType.PUT,
    )

    call_price = price_option(call_inputs).price
    put_price = price_option(put_inputs).price

    left_side = call_price - put_price
    right_side = spot * np.exp(-r_for * tenor_years) - strike * np.exp(-r_dom * tenor_years)

    difference = abs(left_side - right_side)
    return {
        "check": "Put-call parity (C - P = S*exp(-r_for*T) - K*exp(-r_dom*T))",
        "call_price": round(call_price, 6),
        "put_price": round(put_price, 6),
        "left_side": round(left_side, 6),
        "right_side": round(right_side, 6),
        "difference": round(difference, 8),
        "passed": difference < 1e-6,
    }


if __name__ == "__main__":
    # Mismos parámetros de mercado que las pruebas anteriores
    params = dict(spot=1.166, strike=1.20, tenor_years=90 / 365,
                  r_dom=0.0386, r_for=0.0219)

    checks = [
        check_limit_sigma_zero(**params),
        check_limit_tenor_zero(spot=params["spot"], strike=params["strike"],
                                sigma=0.045, r_dom=params["r_dom"], r_for=params["r_for"]),
        check_put_call_parity(spot=params["spot"], strike=params["strike"],
                               tenor_years=params["tenor_years"], sigma=0.045,
                               r_dom=params["r_dom"], r_for=params["r_for"]),
    ]

    print("=" * 70)
    for result in checks:
        status = "PASA" if result["passed"] else "FALLA"
        print(f"[{status}] {result['check']}")
        for key, value in result.items():
            if key not in ("check", "passed"):
                print(f"    {key}: {value}")
        print("-" * 70)

    all_passed = all(c["passed"] for c in checks)
    print(f"\nResultado global: {'TODOS LOS CHECKS PASAN' if all_passed else 'HAY CHECKS FALLIDOS'}")