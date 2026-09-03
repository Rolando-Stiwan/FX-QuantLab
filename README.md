# FX QuantLab: Pricing, Risk & Analytics Platform

Plataforma de apoyo a decisiones para productos derivados FX — el
tipo de herramienta interna que usaría un equipo de mercados o
tesorería. No es una "calculadora de opciones": la calculadora de
pricing es una funcionalidad dentro de un sistema más amplio de
datos, pricing, riesgo y análisis de escenarios.

**Caso de uso guía**: un gestor comercial recibe una llamada — "dentro
de 90 días tengo que pagar 5 millones de euros, quiero protegerme si
el EUR/USD sube, ¿cuánto me cuesta una opción?" — y la plataforma
permite responder con precio, riesgo y escenarios.

## Contexto y motivación

Proyecto de portfolio dentro de una narrativa de progresión en riesgo
cuantitativo: crédito ([CreditRiskLab](https://creditrisklab.streamlit.app))
→ seguros/salud (HealthRisk360) → derivados FX y mercados (este
proyecto). Cada proyecto reutiliza y extiende patrones técnicos del
anterior (Monte Carlo, VaR/CVaR, arquitectura FastAPI+Streamlit+
Docker+CI, documentación de decisiones técnicas).

Motivado por vacantes de perfil cuantitativo junior en banca/mercados
en España. **Nota honesta**: este proyecto acerca la parte cuantitativa
(pricing, riesgo, Python) transferible a roles de mercados FX, pero no
sustituye experiencia real de trading floor ni herramientas de nicho
específicas del sector (Q/KDB+, plataformas de BI internas). Es un
puente de portfolio, no una equivalencia de experiencia de mercado.

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
├── docker/
└── .github/workflows/ # cron diario del pipeline
```

## Estado del proyecto

- [x] **Módulo 1 — Ingesta de datos**: Yahoo Finance (spot) + FRED
      (tasas) + volatilidad (rolling 20d/60d/252d y EWMA) + SQLite +
      pipeline incremental con tolerancia a fallos. Validado localmente.
- [ ] Workflow de GitHub Actions: escrito, pendiente de despliegue
      (subir repo + configurar Secret `FRED_API_KEY`).
- [ ] **Módulo 2 — Motor de pricing**: Garman-Kohlhagen + Monte Carlo.
- [ ] **Módulo 3 — Riesgo**: Greeks, VaR, CVaR (Monte Carlo completo).
- [ ] **Módulo 4 — Simulador de escenarios**.
- [ ] **Módulo 5 — Dashboard** (Streamlit).
- [ ] **Módulo 6 — API** (FastAPI).
- [ ] **Módulo 7 — Reporte PDF** (opcional, fase final).

Ver [`docs/decisiones_tecnicas.md`](docs/decisiones_tecnicas.md) para
el detalle de cada decisión metodológica y sus limitaciones.

## Instalación

```bash
pip install -e ".[dev]"
```

Requiere un archivo `.env` en la raíz con tu clave de FRED:

FRED_API_KEY=clave_aqui


## Correr el pipeline manualmente

```bash
python -m src.ingestion.pipeline
```

## Autor

Rolando Stiwan — [GitHub: Rolando-Stiwan](https://github.com/Rolando-Stiwan)