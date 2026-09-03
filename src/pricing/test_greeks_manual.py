from src.pricing.greeks import greeks
import numpy as np

# Mismo caso de prueba que Módulo 2
S = 1.166
K = 1.20
T = 90 / 365
r_dom = 0.05   # ajusta al valor real que usaste en garman_kohlhagen.py
r_for = 0.03   # ajusta al valor real que usaste en garman_kohlhagen.py
sigma = 0.08   # ajusta al valor real que usaste

g_call = greeks(S, K, T, r_dom, r_for, sigma, "call")
g_put = greeks(S, K, T, r_dom, r_for, sigma, "put")

print("CALL:", g_call)
print("PUT:", g_put)

# Chequeo 1: Delta call entre 0 y e^{-r_for*T}
techo = np.exp(-r_for * T)
print(f"\nCheck 1 - Delta call en [0, {techo:.6f}]: {0 <= g_call['delta'] <= techo}")

# Chequeo 2: Gamma igual en call y put
print(f"Check 2 - Gamma igual: {np.isclose(g_call['gamma'], g_put['gamma'])}")
print(f"  gamma_call={g_call['gamma']:.8f}, gamma_put={g_put['gamma']:.8f}")

# Chequeo 3: Delta_call - Delta_put == e^{-r_for*T}
diff = g_call['delta'] - g_put['delta']
print(f"Check 3 - Delta_call - Delta_put = {diff:.8f}, esperado = {techo:.8f}")
print(f"  Coincide: {np.isclose(diff, techo)}")