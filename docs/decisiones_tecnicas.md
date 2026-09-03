# Decisiones Técnicas — FX QuantLab

Documento de gobernanza técnica. Registra decisiones metodológicas
conscientes, sus razones, y las limitaciones honestas que implican.
Sigue el mismo estilo de documentación que HealthRisk360.

## 1. Fuentes de datos

Todas las fuentes son 100% gratuitas — decisión consciente para un
proyecto de portfolio, no una réplica de infraestructura bancaria real.

| Dato | Fuente | Frecuencia |
|---|---|---|
| Spot EUR/USD | Yahoo Finance (`yfinance`, ticker `EURUSD=X`) | Diaria |
| Tasa doméstica (USD) | FRED, serie `DGS3MO` (Treasury 3 meses) | Diaria |
| Tasa extranjera (EUR) | FRED, serie `ECBESTRVOLWGTTRMDMNRT` (€STR) | Diaria |
| Volatilidad | Calculada internamente (no descargada) | Diaria |

**Limitación conocida y aceptada**: no existen datos de mercado de
opciones FX gratuitos (mercado OTC, sin cotización pública). El
pricer NO usa precios de opciones como input — Garman-Kohlhagen
calcula el precio como output a partir de spot, strike, tenor,
volatilidad y tasas.

**Limitación conocida — asimetría de tenor en tasas**: `DGS3MO` es
una tasa a 3 meses; `ECBESTRVOLWGTTRMDMNRT` (€STR) es una tasa
overnight. Existe una pequeña asimetría de tenor entre ambas series
por ser la mejor combinación disponible gratuitamente. No se oculta
esta limitación.

**Limitación conocida — completitud de Yahoo Finance**: `yfinance`
es una fuente gratuita sin garantía de nivel de servicio (SLA). Es
posible que algún día hábil específico no tenga dato en la fuente
(no por fallo del pipeline, sino porque el dato no existe en origen).
Estos huecos no se rellenan artificialmente; los cálculos de
volatilidad operan sobre los días efectivamente disponibles, no
sobre un calendario fijo de días hábiles.

## 2. Volatilidad

Se ofrecen dos familias de modelos, ambas calculadas desde el
histórico de spot (volatilidad realizada), nunca implícita de mercado:

- **Rolling histórica** (20d / 60d / 252d): desviación estándar de
  retornos logarítmicos diarios en una ventana móvil, anualizada
  con factor √252.
- **EWMA** (estilo RiskMetrics/JP Morgan): factor de decaimiento
  λ = 0.94, estándar de la industria para datos diarios. Half-life
  de un shock ≈ 11.2 días. Se reconoce que estudios académicos
  posteriores (Bollen 2015, González-Rivera et al. 2007) cuestionan
  si 0.94 es el valor óptimo, pero no existe un reemplazo de
  consenso en la industria — se usa el estándar por ser la decisión
  defendible y ampliamente reconocida.

**GARCH queda explícitamente fuera de alcance del MVP.** Requiere
estimación por máxima verosimilitud que puede no converger en un
pipeline no supervisado (lección aprendida: evitar bloqueantes de
última hora, como ocurrió con Docker/Starlette en HealthRisk360).
Queda documentado como posible extensión futura, no como fase
planificada.

**Volatility smile**: no se puede calibrar una smile real de mercado
(requiere precios de opciones que no existen gratis). Se implementará
una smile SINTÉTICA (parabólica o SABR), explícitamente marcada como
ilustrativa y NO calibrada a mercado real.

## 3. Pricing

- **Garman-Kohlhagen** (fórmula cerrada) + **Monte Carlo** (validación
  cruzada) — nunca Monte Carlo como único método de pricing en
  producción; sirve para validar que ambos convergen.
- Validación sin datos de mercado externos:
  1. Monte Carlo vs. fórmula cerrada (deben converger).
  2. Casos límite: σ→0 converge a valor intrínseco descontado;
     T→0 converge a max(S-K, 0).
  3. Put-call parity.

## 4. Gestión de riesgo

**VaR/CVaR de opciones se calcula con Monte Carlo completo, NO
delta-normal/paramétrico.** Razón: el enfoque delta-normal asume
relación lineal entre el precio del subyacente y el valor de la
opción, lo cual falla en productos con gamma alta (opciones cerca
del strike, por ejemplo). Es una decisión metodológica consciente,
no una omisión.

## 5. Infraestructura del pipeline diario

- **Orquestador**: GitHub Actions, cron diario en días hábiles
  (lunes-viernes), `05:30 UTC` (7:30 España en horario de verano
  CEST / 6:30 España en horario de invierno CET — GitHub Actions usa
  UTC fijo, no se ajusta automáticamente al cambio de horario
  español). No se promete puntualidad exacta: el cron de GitHub
  Actions puede retrasarse.
- **Almacenamiento**: SQLite, archivo `.db` versionado dentro del
  propio repositorio Git. El mismo Action hace commit+push del
  archivo actualizado tras cada ejecución. Decisión consciente de
  simplicidad operativa — no pretende ser infraestructura de
  producción bancaria real.
- **Ingesta incremental**: cada corrida consulta la última fecha ya
  almacenada y descarga solo los datos nuevos desde ahí, no vuelve
  a traer el histórico completo cada vez.
- **Tolerancia a fallos**: si una fuente falla, el pipeline usa el
  último dato válido disponible (nunca rompe silenciosamente) y
  registra el estado de la corrida (`ok` / `stale_fallback` /
  `failed`) en la tabla `pipeline_snapshots`, con notas explicativas.
- **Trazabilidad**: cada snapshot de mercado queda timestampado, de
  modo que cualquier precio calculado sea trazable a los datos
  exactos usados en ese momento.
- **Cadencia diaria, no tiempo real**: los datos base de Yahoo/FRED
  son diarios; pretender mayor frecuencia sería falso dinamismo.

## 6. Ingeniería

- Versiones exactas pinneadas en `pyproject.toml` desde el commit
  inicial (lección aprendida de HealthRisk360, donde un bug de
  Starlette/Streamlit sin pinnear quedó como bloqueante final).
- Alcance de un solo par de divisas (EUR/USD) en el MVP, aunque el
  esquema de base de datos soporta múltiples pares desde el diseño
  (columna `currency_pair` en todas las tablas). Añadir pares
  adicionales no requiere migración de esquema.


### Griegas (greeks.py)

Calculadas de forma analítica (fórmulas cerradas de Garman-Kohlhagen),
no vía diferencias finitas sobre Monte Carlo — las fórmulas cerradas
existen para GK, son exactas y más rápidas que shock-and-reprice.

- Delta, Gamma, Vega: mismas fórmulas que Black-Scholes con dividendos
  continuos, usando r_for como "yield" de la divisa extranjera.
- Rho se separa en dos: rho_dom y rho_for, porque cada divisa del par
  tiene su propia curva de tasas y se mueven de forma independiente
  (a diferencia de acciones, donde solo hay una tasa relevante).
- Theta se expresa por día (dividido entre 365), no por año — decisión
  de usabilidad para que el número sea directamente interpretable
  ("esta opción pierde X pips por día").

**Validación** (tests/test_greeks.py, pytest):
1. Delta de una call está acotado entre 0 y e^(-r_for·T).
2. Gamma es idéntica para call y put (propiedad matemática de la
   fórmula, no específica de FX).
3. Put-call parity de Delta: Delta_call − Delta_put = e^(-r_for·T),
   exacto hasta error de punto flotante.

### VaR y CVaR (var_cvar.py)

Metodología: **Monte Carlo full-revaluation**, no delta-normal /
paramétrico. Decisión ya justificada en el documento de contexto del
proyecto: el enfoque delta-normal asume una relación lineal entre el
valor de la posición y el movimiento del subyacente, y falla quando
hay curvatura (Gamma) significativa — que es precisamente el caso de
las opciones, sobre todo cerca del strike o con tenor corto.

Proceso:
1. Simular N trayectorias del spot al horizonte de riesgo (GBM, drift
   neutral al riesgo con diferencial de tasas r_dom − r_for).
2. Repreciar la opción en cada escenario simulado, con el tenor
   reducido (T − horizonte).
3. Calcular la distribución de P&L: precio_repreciado − precio_hoy.
4. VaR = percentil de la cola de pérdidas (ej. percentil 5 para 95%
   de confianza). CVaR = promedio de las pérdidas más allá del VaR.

**Nota de diseño — vectorización**: `garman_kohlhagen.price_option()`
opera sobre un solo escenario (usa un dataclass con validación
escalar), y no vectoriza directamente sobre arrays de NumPy. Para
Monte Carlo full-revaluation con 50,000+ escenarios, se implementó
`_price_vectorized()` en `var_cvar.py`: una réplica de la misma
fórmula matemática, vectorizada con NumPy, sin modificar el motor de
pricing ya validado de Módulo 2. Esta decisión evita loops de Python
puro (jamás usados en este proyecto, conforme a la decisión ya fijada
sobre performance de Monte Carlo) y evita reabrir código ya cerrado y
validado de Módulo 2.

**Validación de la vectorización** (tests/test_var_cvar.py, pytest):
antes de confiar en `_price_vectorized`, se verifica que da un
resultado idéntico a `price_option()` (la función oficial) para un
caso escalar — esto descarta errores de transcripción de la fórmula
al vectorizarla.

**Validación de VaR/CVaR**:
1. VaR y CVaR son positivos (representan magnitud de pérdida).
2. CVaR ≥ VaR siempre (el promedio de la cola nunca puede ser menor
   que el percentil que la delimita) — propiedad matemática, no un
   resultado específico del caso de prueba.

### Nota sobre performance en producción (para Módulo 5)

`simulate_var_cvar()` recalcula 50,000 escenarios cada vez que se
llama — correcto y necesario para el cálculo de riesgo en sí, pero
esto NO debe recalcularse en cada interacción del usuario en el
dashboard. La estrategia de cacheo (`@st.cache_data` en Streamlit,
menos simulaciones para sliders en tiempo real vs. más para el
reporte final) se implementa en Módulo 5, no aquí — este módulo es
el motor de cálculo, agnóstico de cómo se consume después.

---


## Módulo 4 — Simulador de escenarios (scenarios.py)

Capa que conecta Módulo 2 (pricing) y Módulo 3 (Greeks) para responder
"¿qué pasa si el mercado se mueve X?", sin duplicar fórmulas.

**Diseño de performance**: precio y Greeks se recalculan en tiempo
real (fórmulas cerradas, instantáneo). VaR/CVaR queda deliberadamente
fuera de este módulo — recalcular 50,000 simulaciones Monte Carlo en
cada movimiento de un slider haría el dashboard lento. VaR/CVaR se
invoca aparte, bajo demanda, solo cuando el usuario lo pide
explícitamente para un escenario concreto (ver Módulo 3).

**Shocks individuales**: Spot ±5%/±8%, Volatilidad ±15%/±20%,
Tasas +1% — un shock a la vez, todo lo demás constante. Es el
estándar de sensitivity analysis / reporting diario de un desk.

**Escenarios combinados**: 3 escenarios curados con sentido
económico (no una matriz combinatoria exhaustiva, que generaría
combinaciones sin lógica de mercado real):
- **Crisis de tasas**: tasas +1% y volatilidad +20% simultáneo
  (cuando los bancos centrales suben tasas agresivamente, la
  incertidumbre dispara la volatilidad).
- **Flight to quality**: spot −8% y volatilidad +20% (huida hacia
  activos seguros; correlación negativa típica entre spot y
  volatilidad en shocks de mercado).
- **Mercado calmo**: spot +2% y volatilidad −15% (entorno benigno de
  baja incertidumbre).

**Observación cualitativa del modelo** (validado con caso de prueba
EURUSD call OTM, spot 1.166, strike 1.20, 90d): en el escenario
"Flight to quality", el precio de la opción cae a prácticamente cero
a pesar del incremento de volatilidad (+20%). Esto ocurre porque el
shock de spot (−8%, alejando aún más la opción del strike) domina
completamente sobre el efecto de la volatilidad — una opción muy
fuera del dinero no se "salva" con más volatilidad si el spot se aleja
lo suficiente del strike. Es un comportamiento esperado del modelo
(no un bug): ilustra que el efecto direccional del spot puede opacar
al efecto de la volatilidad cuando la opción está muy OTM.

**Validación**: el escenario "Base" (sin shocks) reproduce
exactamente el precio ya validado en Módulo 2 (0.001793 con los
inputs del caso de prueba estándar), confirmando que la capa de
escenarios no introduce desviación alguna sobre el pricer original.