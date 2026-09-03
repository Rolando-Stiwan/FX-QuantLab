from src.pricing.var_cvar import simulate_var_cvar

resultado = simulate_var_cvar(
    S=1.166,
    K=1.20,
    T=90/365,
    r_dom=0.05,
    r_for=0.03,
    sigma=0.08,
    option_type="call",
    horizon_days=1,
    n_simulations=50_000,
    confidence=0.95,
    seed=42,
)

print("Precio hoy:", resultado["precio_hoy"])
print("VaR 95%:", resultado["var"])
print("CVaR 95%:", resultado["cvar"])
print("N simulaciones:", resultado["n_simulations"])