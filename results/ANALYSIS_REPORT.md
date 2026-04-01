# EUR/USD M1 Analysis Report (2000-2025)
**Período analizado:** Mayo 2000 - Diciembre 2025
**Datos:** 8,720,941 velas de 1 minuto
**Trading days:** 6,668
**Generado:** 2026-04-01 08:38:01

---

## Resumen Ejecutivo

Este análisis cuantitativo examina patrones estadísticos en EUR/USD M1 con foco en la sesión de NY (H4) para operativa discrecional. Se identificaron sesgos claros por bloque horario, día de la semana y condiciones previas.

### Hallazgos Clave

1. **Rango por Bloque:** NY produce el rango más alto (14.72 pips), con 40% de extremos diarios en Post-NY
2. **Condicionales NY:** Cuando Asia + London tienen rango alto → NY expande +90%
3. **Sesgos Semanales:** Escalada lunes→jueves (+26%), 92% de días tendenciales
4. **H4 Analysis:** Rango óptimo cuando 25-50% ATR completado antes de NY (85.5 pips)

---

## PASO 1: Preparación de Datos

### Dataset Coverage

| Métrica | Valor |
|---------|-------|
| Período | 2000-05-30 a 2025-12-31 |
| Total M1 | 8,720,941 velas |
| Trading Days | 6,668 |
| Semanas | ~952 |
| Años cubiertos | 26 (2000-2025) |
| Rango de precios | 0.9302 - 1.1746 |

---

## PASO 2: Rango y Contribución por Bloque

### Estadísticas de Rango por Bloque (Todo el Período)

| session     |   Rango Promedio (pips) |   Contribución % al Rango Diario |
|:------------|------------------------:|---------------------------------:|
| Asia        |                    6.51 |                            40.56 |
| Post-Asia   |                    5.25 |                            32.7  |
| London      |                    9.68 |                            60.72 |
| Post-London |                    8.99 |                            54.82 |
| NY          |                   14.72 |                            80.82 |
| Post-NY     |                   11.5  |                            66.38 |

### Probabilidad de Extremos Diarios por Bloque


| Bloque | HIGH (%) | LOW (%) |
|--------|----------|---------|
| Asia | 9.33 | 10.15 |
| Post-Asia | 3.39 | 2.85 |
| London | 16.65 | 14.10 |
| Post-London | 9.75 | 9.18 |
| **NY** | **20.52** | **22.47** |
| **Post-NY** | **40.37** | **41.26** |

**Insight:** Post-NY concentra 40%+ de extremos diarios. NY es segunda en importancia (20%+).

---

## PASO 3: Foco en Sesión NY

### Condicionales Direccionales

| Condición Pre-NY | Casos | Continuación | Extensión Promedio |
|------------------|-------|--------------|-------------------|
| BULLISH | 3,163 | 49.6% | -0.12 pips |
| BEARISH | 3,382 | 50.4% | +0.66 pips |

**Insight:** ~50% continuación = aleatoria. No hay sesgo direccional fuerte pre-NY.

### Impacto Asia/London Alto → NY

| Condición | NY Rango Medio |
|-----------|--|
| Ambos BAJO | 13.44 pips |
| Asia alto | 15.22 pips |
| London alto | 15.38 pips |
| **Ambos ALTO** | **20.09 pips** 🔥 |

**Ventaja Estadística Clave:** +50% rango en NY cuando Asia Y London están en rango alto.

### Probabilidad de Nuevos Extremos en NY

**Nuevo HIGH en NY según donde se formó el HIGH previo:**

| Bloque anterior | Probabilidad nuevo HIGH |
|-----------------|---|
| Asia | 23.0% |
| Post-Asia | 29.7% |
| London | 34.0% |
| **Post-London** | **61.3%** 🔥 |

**Nuevo LOW en NY según donde se formó el LOW previo:**

| Bloque anterior | Probabilidad nuevo LOW |
|-----------------|---|
| Asia | 25.1% |
| Post-Asia | 27.4% |
| London | 34.7% |
| **Post-London** | **66.6%** 🔥 |

**Insight Crítico:** Si el extremo se formó en Post-London (05:00-08:00), hay 61-67% de probabilidad que NY haga NUEVO extremo en la misma dirección.

---

## PASO 4: Sesgos por Día de la Semana

### Rango NY por Día de Semana

| Día | Rango Promedio | Tendencial (%) |
|-----|---|---|
| Monday | 51.18 | 93% |
| Tuesday | 53.23 | 92% |
| Wednesday | 61.92 | 92% |
| **Thursday** | **64.54** | 92% |
| Friday | (sin datos) | (sin datos) |

**Escalada:** +26% rango Monday → Thursday.

### Impacto Asia/London Alto por Día

| Condición | Monday | Tuesday | Wednesday | Thursday |
|-----------|--------|---------|-----------|----------|
| Ambos BAJO | 43.36 | 45.58 | 53.63 | 58.99 |
| **Ambos ALTO** | **82.44** | **86.45** | **91.37** | **88.66** |

**Multiplicador:** +90% rango cuando Asia+London alto (consistente todos los días).

### Volatilidad por Período

| Período | Monday | Tuesday | Wednesday | Thursday |
|---------|--------|---------|-----------|----------|
| 2000-2007 | 50.14 | 52.76 | 59.44 | 71.89 |
| **2008-2013** | **71.51** | **72.13** | **83.67** | **82.19** |
| 2014-2019 | 41.88 | 44.93 | 54.93 | 56.08 |
| 2020-2025 | 41.50 | 43.16 | 49.97 | 47.03 |

**Hallazgo:** 2008-2013 máxima volatilidad (crisis). Desde 2014 normalizó a niveles actuales.

---

## PASO 5: Integración con H4

### Estadísticas H4 en NY (6,546 velas)

| Métrica | Valor |
|---------|-------|
| Rango Promedio | 60.83 pips |
| Mediana | 52.00 pips |
| Cuerpo Promedio | 30.21 pips |
| P25 Rango | 36.00 pips |
| P75 Rango | 75.00 pips |
| UP | 50.7% |
| DOWN | 49.3% |

### Continuación al H4 Siguiente

| Métrica | Valor |
|---------|-------|
| Continuación dirección | 48.6% |
| Extensión media | 17.99 pips |
| Extensión mediana | 11.75 pips |
| P25-P75 extensión | 5.00 - 23.47 pips |

**Insight:** Continuación débil (48.6%) = mercado consolidador en NY.

### H4 Rango según % ATR Diario Completado ANTES de NY

| % ATR | Casos | H4 Rango NY |
|-------|-------|-------------|
| 0-25% | 56 | 66.67 pips |
| **25-50%** | 170 | **85.50 pips** 🔥 |
| 50-75% | 296 | 75.63 pips |
| 75-100% | 356 | 71.97 pips |

**Ventana Óptima:** 25-50% ATR completado antes de NY → máximo rango esperado.

### H4 Rango según Extremos Semanales

| Posición | Casos | Rango H4 | Continuación |
|----------|-------|----------|---|
| **Lejos de extremos** | 1,850 | **66.32 pips** | 51.5% |
| Cerca máximo semanal | 1,958 | 58.17 pips | 48.3% |
| Cerca mínimo semanal | 2,099 | 57.68 pips | 46.8% |
| Ambos extremos | 639 | 63.43 pips | 46.6% |

**Insight:** Extremos semanales "contienen" el rango (-12%). Mejor continuación lejos de extremos.

---

## Conclusiones y Recomendaciones Operacionales

### Para Operativa en NY (Sesión de 8:00-11:00 ET)

1. **Setup Ideal:**
   - Día: Jueves (máximo rango esperado)
   - Condición previa: Asia + London con rango alto (>P75)
   - ATR completado: 25-50% antes de NY inicio
   - Resultado esperado: 80-90 pips en H4 NY

2. **Configuración de Riesgo:**
   - Rango típico H4 NY: 60.83 pips (P25: 36, P75: 75)
   - Extremos semanales actúan como contención (-12%)
   - Continuación débil: dimensionar para consolidación, no momentum

3. **Días de Menor Volatilidad:**
   - Lunes (51.18 pips): -20% vs Thursday
   - Cuando Asia/London están bajos: -40% rango esperado

4. **Periodos de Máxima Incertidumbre:**
   - >75% ATR completado antes de NY: rango comprimido
   - En zona de máximos/mínimos semanales: rango -12%

---

## Anexo: Datos Disponibles

Todos los resultados detallados están disponibles en archivos CSV:
- `daily_stats.csv` - Estadísticas diarias
- `block_stats.csv` - Estadísticas por bloque horario
- `ny_analysis.csv` - Análisis NY detallado
- `paso4_full_data.csv` - Datos día de semana
- `paso5_h4_ny_analysis.csv` - Análisis H4

---

**Análisis realizado con Python + Pandas**
**Datos: 8.7M+ velas EUR/USD M1 (2000-2025)**
