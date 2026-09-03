from src.pricing.garman_kohlhagen import OptionType
from src.simulation.scenarios import shocks_individuales, escenarios_combinados

# Mismo caso de prueba de siempre
S = 1.166
K = 1.20
T = 90 / 365
R_DOM = 0.0386
R_FOR = 0.0219
SIGMA = 0.045

print("=" * 70)
print("SHOCKS INDIVIDUALES")
print("=" * 70)
for r in shocks_individuales(S, K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL):
    print(f"{r.nombre:15s} | Precio: {r.price:.6f} | "
          f"Δ: {r.price_change:+.6f} ({r.price_change_pct:+.2f}%) | "
          f"Delta: {r.greeks['delta']:.4f}")

print()
print("=" * 70)
print("ESCENARIOS COMBINADOS")
print("=" * 70)
for r in escenarios_combinados(S, K, T, R_DOM, R_FOR, SIGMA, OptionType.CALL):
    print(f"{r.nombre:20s} | Precio: {r.price:.6f} | "
          f"Δ: {r.price_change:+.6f} ({r.price_change_pct:+.2f}%) | "
          f"Delta: {r.greeks['delta']:.4f}")