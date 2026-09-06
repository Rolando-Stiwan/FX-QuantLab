# FX QuantLab: Pricing, Risk & Analytics Platform

**🔗 Demo en vivo: [https://fx-quantlab.onrender.com](https://fx-quantlab.onrender.com)**

Plataforma de apoyo a decisiones para productos derivados FX — el tipo de herramienta interna que usaría un equipo de mercados o tesorería. No es una "calculadora de opciones": la calculadora de pricing es una funcionalidad dentro de un sistema más amplio de datos, pricing, riesgo y análisis de escenarios.

**Caso de uso guía**: un cliente llama a su banco — "dentro de 90 días tengo que pagar 5 millones de euros, quiero protegerme si el EUR/USD sube" — y un gestor de mercados/tesorería del banco usa la plataforma para evaluar internamente si ofrecer la cobertura, con qué precio de referencia y qué riesgo asume el banco al hacerlo. La plataforma es una herramienta de apoyo a la decisión para el banco, no para el cliente final ni para ejecutar operaciones de mercado real.

## Contexto y motivación

Proyecto de portfolio dentro de una narrativa de progresión en riesgo cuantitativo: crédito ([CreditRiskLab](https://creditrisklab.streamlit.app)) → seguros/salud (HealthRisk360) → derivados FX y mercados (este proyecto). Cada proyecto reutiliza y extiende patrones técnicos del anterior (Monte Carlo, VaR/CVaR, arquitectura FastAPI+Streamlit+Docker+CI, documentación de decisiones técnicas).

Motivado por vacantes de perfil cuantitativo junior en banca/mercados en España. **Nota honesta**: este proyecto acerca la parte cuantitativa (pricing, riesgo, Python) transferible a roles de mercados FX, pero no sustituye experiencia real de trading floor ni herramientas de nicho específicas del sector (Q/KDB+, plataformas de BI internas). Es un puente de portfolio, no una equivalencia de experiencia de mercado.

## Arquitectura
```
FX-QuantLab/
├── data/ # base de datos SQLite (versionada en el repo)
├── src/
│ ├── ingestion/ # Módulo 1: datos, volatilidad, pipeline diario
│ ├── pricing/ # Módulo 2: Garman-Kohlhagen + Monte Carlo
│ ├── risk/ # Módulo 3: Greeks, VaR, CVaR
│ ├── simulation/ # Módulo 4: simulador de escenarios
│ ├── api/ # Módulo 6: FastAPI
│ └── dashboard/ # Módulo 5: Streamlit
├── tests/
├── docs/
│ └── decisiones_tecnicas.md
├── Dockerfile # imagen única (API + dashboard en un solo contenedor)
├── start.sh # arranca uvicorn (interno) + streamlit (público)
├── render.yaml # despliegue en Render (Blueprint, autoDeploy)
└── .github/workflows/
├── daily_pipeline.yml # cron diario de ingesta de datos
└── ci.yml # tests automáticos en cada push/PR
```


## Estado del proyecto

- [x] **Módulo 1 — Ingesta de datos**: Yahoo Finance (spot) + FRED (tasas) + volatilidad (rolling 20d/60d/252d y EWMA) + SQLite + pipeline incremental. Cron diario en GitHub Actions corriendo en producción.
- [x] **Módulo 2 — Motor de pricing**: Garman-Kohlhagen + Monte Carlo (validado por convergencia).
- [x] **Módulo 3 — Riesgo**: Greeks analíticas, VaR/CVaR vía Monte Carlo full-revaluation.
- [x] **Módulo 4 — Simulador de escenarios**: shocks individuales + 3 escenarios combinados (Crisis de tasas, Flight to quality, Mercado calmo).
- [x] **Módulo 5 — Dashboard** (Streamlit): 4 páginas — Resumen, Mercado, Simulación, Sensibilidad.
- [x] **Módulo 6 — API** (FastAPI): 5 endpoints, con tests automatizados (pytest + TestClient).
- [x] **Módulo 7 — Docker + CI/CD**: contenedor único, tests en CI, despliegue automático en Render en cada push a `main`.

Ver [`docs/decisiones_tecnicas.md`](docs/decisiones_tecnicas.md) para el detalle de cada decisión metodológica y sus limitaciones.

## Correr en producción

La aplicación está desplegada y corriendo en Render: **[fx-quantlab.onrender.com](https://fx-quantlab.onrender.com)**. Los datos se actualizan automáticamente cada día laborable vía GitHub Actions.

## Correr localmente

**Opción A — Con Docker (recomendado, igual que producción):**
```bash
docker build -t fx-quantlab .
docker run -p 8501:8501 -e PORT=8501 fx-quantlab
```
Abre `http://localhost:8501`.

**Opción B — Sin Docker (entorno Python directo):**
```bash
pip install -e ".[dev]"
```

Requiere un archivo `.env` en la raíz con tu clave de FRED:
FRED_API_KEY=clave_aqui


Correr el pipeline de datos manualmente:
```bash
python -m src.ingestion.pipeline
```

Correr los tests:
```bash
pytest -v
```

## Autor

Rolando Stiwan — [GitHub: Rolando-Stiwan](https://github.com/Rolando-Stiwan)