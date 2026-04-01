"""
Generador de Reportes: Markdown + HTML Dashboard
Extrae resultados de todos los PASOS y genera documentos visuales
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

# ============================================================================
# GENERAR MARKDOWN REPORT
# ============================================================================

def generate_markdown_report():
    """Genera reporte en Markdown."""
    print("Generando Markdown Report...")

    md_content = f"""# EUR/USD M1 Analysis Report (2000-2025)
**Período analizado:** Mayo 2000 - Diciembre 2025
**Datos:** 8,720,941 velas de 1 minuto
**Trading days:** 6,668
**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
"""

    # PASO 1 Info
    daily_stats = pd.read_csv(RESULTS_PATH / 'daily_stats.csv', parse_dates=['trading_date'])

    md_content += f"""
| Métrica | Valor |
|---------|-------|
| Período | 2000-05-30 a 2025-12-31 |
| Total M1 | 8,720,941 velas |
| Trading Days | {len(daily_stats):,} |
| Semanas | ~{len(daily_stats)//7:,} |
| Años cubiertos | 26 (2000-2025) |
| Rango de precios | 0.9302 - 1.1746 |

---

## PASO 2: Rango y Contribución por Bloque

### Estadísticas de Rango por Bloque (Todo el Período)
"""

    block_stats = pd.read_csv(RESULTS_PATH / 'block_stats.csv', parse_dates=['trading_date'])
    block_summary = block_stats.groupby('session').agg({
        'block_range_pips': ['count', 'mean', 'median', 'std'],
        'block_return_pips': ['mean', 'median'],
        'contribution_pct': ['mean', 'median']
    }).round(2)

    # Crear tabla markdown
    block_table = block_stats.groupby('session').agg({
        'block_range_pips': 'mean',
        'contribution_pct': 'mean'
    }).round(2)
    block_table.columns = ['Rango Promedio (pips)', 'Contribución % al Rango Diario']
    block_table = block_table.reindex(['Asia', 'Post-Asia', 'London', 'Post-London', 'NY', 'Post-NY'])

    md_content += "\n" + block_table.to_markdown() + "\n"

    # Probabilidades HIGH/LOW
    md_content += """
### Probabilidad de Extremos Diarios por Bloque

"""

    # Calcular probabilidades
    daily_stats['trading_date'] = pd.to_datetime(daily_stats['trading_date'])

    md_content += """
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
"""

    with open(RESULTS_PATH / 'ANALYSIS_REPORT.md', 'w') as f:
        f.write(md_content)

    print("✓ Markdown Report generado: ANALYSIS_REPORT.md")
    return md_content


# ============================================================================
# GENERAR HTML DASHBOARD
# ============================================================================

def generate_html_dashboard():
    """Genera dashboard HTML interactivo."""
    print("Generando HTML Dashboard...")

    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EUR/USD Analysis Dashboard (2000-2025)</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(30, 41, 59, 0.8);
            border-radius: 12px;
            border-left: 4px solid #3b82f6;
        }

        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        h2 {
            font-size: 1.8em;
            margin: 40px 0 20px 0;
            color: #60a5fa;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 10px;
        }

        h3 {
            font-size: 1.3em;
            margin: 25px 0 15px 0;
            color: #93c5fd;
        }

        .metadata {
            font-size: 0.95em;
            color: #94a3b8;
            margin-top: 15px;
        }

        .section {
            background: rgba(30, 41, 59, 0.6);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid #334155;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: rgba(15, 23, 42, 0.4);
            border-radius: 8px;
            overflow: hidden;
        }

        th {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: white;
            border-bottom: 2px solid #1e40af;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid #334155;
        }

        tr:hover {
            background: rgba(59, 130, 246, 0.1);
        }

        tr:last-child td {
            border-bottom: none;
        }

        .highlight-good {
            background: rgba(34, 197, 94, 0.1);
            color: #86efac;
            font-weight: 600;
        }

        .highlight-warning {
            background: rgba(234, 179, 8, 0.1);
            color: #fcd34d;
            font-weight: 600;
        }

        .highlight-danger {
            background: rgba(239, 68, 68, 0.1);
            color: #fca5a5;
            font-weight: 600;
        }

        .insight {
            background: rgba(59, 130, 246, 0.2);
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin: 20px 0;
            border-radius: 6px;
            font-style: italic;
        }

        .key-metric {
            display: inline-block;
            background: rgba(59, 130, 246, 0.15);
            padding: 10px 15px;
            border-radius: 6px;
            margin: 5px;
            border-left: 3px solid #60a5fa;
        }

        .metric-value {
            color: #60a5fa;
            font-weight: 700;
            font-size: 1.1em;
        }

        footer {
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            border-top: 1px solid #334155;
            color: #64748b;
            font-size: 0.9em;
        }

        .badge {
            display: inline-block;
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            margin: 5px 5px 5px 0;
        }

        .emoji {
            margin: 0 5px;
        }

        @media (max-width: 768px) {
            h1 { font-size: 1.8em; }
            h2 { font-size: 1.3em; }
            .section { padding: 20px; }
            table { font-size: 0.9em; }
            th, td { padding: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><span class="emoji">📊</span>EUR/USD Analysis Dashboard</h1>
            <p>Análisis Cuantitativo M1 (2000-2025)</p>
            <div class="metadata">
                <p><strong>Período:</strong> Mayo 2000 - Diciembre 2025</p>
                <p><strong>Datos:</strong> 8,720,941 velas de 1 minuto | <strong>Trading Days:</strong> 6,668</p>
            </div>
        </header>

        <!-- PASO 1 -->
        <div class="section">
            <h2><span class="emoji">📥</span>PASO 1: Preparación de Datos</h2>
            <table>
                <thead>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Período Cubierto</td>
                        <td class="highlight-good">2000-05-30 a 2025-12-31</td>
                    </tr>
                    <tr>
                        <td>Total Velas M1</td>
                        <td class="highlight-good">8,720,941</td>
                    </tr>
                    <tr>
                        <td>Trading Days</td>
                        <td class="highlight-good">6,668</td>
                    </tr>
                    <tr>
                        <td>Rango de Precios</td>
                        <td class="highlight-good">0.9302 - 1.1746</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- PASO 2 -->
        <div class="section">
            <h2><span class="emoji">📈</span>PASO 2: Rango y Contribución por Bloque</h2>

            <h3>Rango Promedio por Bloque Horario</h3>
            <table>
                <thead>
                    <tr>
                        <th>Bloque</th>
                        <th>Rango (pips)</th>
                        <th>Contribución % Diaria</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Asia</td>
                        <td>6.51</td>
                        <td>40.56%</td>
                    </tr>
                    <tr>
                        <td>Post-Asia</td>
                        <td>5.25</td>
                        <td>32.70%</td>
                    </tr>
                    <tr>
                        <td>London</td>
                        <td>9.68</td>
                        <td>60.72%</td>
                    </tr>
                    <tr>
                        <td>Post-London</td>
                        <td>8.99</td>
                        <td>54.82%</td>
                    </tr>
                    <tr>
                        <td class="highlight-good">NY</td>
                        <td class="highlight-good">14.72</td>
                        <td class="highlight-good">80.82%</td>
                    </tr>
                    <tr>
                        <td>Post-NY</td>
                        <td>11.50</td>
                        <td>66.38%</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">💡</span> <strong>NY produce el rango máximo</strong> (14.72 pips) y <strong>contribuye 81% al rango diario</strong>. Post-NY es segundo lugar.
            </div>

            <h3>Probabilidad de Extremos Diarios</h3>
            <table>
                <thead>
                    <tr>
                        <th>Bloque</th>
                        <th>HIGH (%)</th>
                        <th>LOW (%)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Asia</td>
                        <td>9.33%</td>
                        <td>10.15%</td>
                    </tr>
                    <tr>
                        <td>London</td>
                        <td>16.65%</td>
                        <td>14.10%</td>
                    </tr>
                    <tr>
                        <td class="highlight-good">NY</td>
                        <td class="highlight-good">20.52%</td>
                        <td class="highlight-good">22.47%</td>
                    </tr>
                    <tr>
                        <td class="highlight-good">Post-NY</td>
                        <td class="highlight-good">40.37%</td>
                        <td class="highlight-good">41.26%</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">🎯</span> <strong>Post-NY concentra 40%+ de extremos</strong>, seguido por NY con 20%+. Son los dos bloques dominantes.
            </div>
        </div>

        <!-- PASO 3 -->
        <div class="section">
            <h2><span class="emoji">🗽</span>PASO 3: Foco en Sesión NY</h2>

            <h3>Impacto de Asia/London Alto → Rango NY</h3>
            <table>
                <thead>
                    <tr>
                        <th>Condición</th>
                        <th>NY Rango Promedio</th>
                        <th>Variación</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Ambos BAJO</td>
                        <td>13.44 pips</td>
                        <td>Baseline</td>
                    </tr>
                    <tr>
                        <td>Asia alto solo</td>
                        <td>15.22 pips</td>
                        <td>+13%</td>
                    </tr>
                    <tr>
                        <td>London alto solo</td>
                        <td>15.38 pips</td>
                        <td>+14%</td>
                    </tr>
                    <tr>
                        <td class="highlight-danger">Ambos ALTO</td>
                        <td class="highlight-danger">20.09 pips</td>
                        <td class="highlight-danger">+50%</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">🔥</span> <strong>VENTAJA ESTADÍSTICA CLAVE:</strong> Cuando Asia Y London tienen rango >P75, NY expande <strong>+50%</strong>. Esta es una ventaja operacional clara.
            </div>

            <h3>Probabilidad de Nuevos Extremos en NY</h3>
            <table>
                <thead>
                    <tr>
                        <th>Donde se formó extremo anterior</th>
                        <th>Nuevo HIGH en NY</th>
                        <th>Nuevo LOW en NY</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Asia</td>
                        <td>23.0%</td>
                        <td>25.1%</td>
                    </tr>
                    <tr>
                        <td>London</td>
                        <td>34.0%</td>
                        <td>34.7%</td>
                    </tr>
                    <tr>
                        <td class="highlight-danger">Post-London</td>
                        <td class="highlight-danger">61.3%</td>
                        <td class="highlight-danger">66.6%</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">⚡</span> <strong>CRÍTICO:</strong> Si el extremo (high/low) se formó en Post-London (05:00-08:00), hay <strong>61-67% de probabilidad</strong> que NY haga NUEVO extremo en la misma dirección.
            </div>
        </div>

        <!-- PASO 4 -->
        <div class="section">
            <h2><span class="emoji">📅</span>PASO 4: Sesgos por Día de la Semana</h2>

            <h3>Rango NY por Día de Semana (Todo el Período)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Día</th>
                        <th>Rango Promedio</th>
                        <th>Mediana</th>
                        <th>% Tendencial</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Monday</td>
                        <td>51.18 pips</td>
                        <td>45.00</td>
                        <td>93%</td>
                    </tr>
                    <tr>
                        <td>Tuesday</td>
                        <td>53.23 pips</td>
                        <td>46.35</td>
                        <td>92%</td>
                    </tr>
                    <tr>
                        <td>Wednesday</td>
                        <td>61.92 pips</td>
                        <td>52.70</td>
                        <td>92%</td>
                    </tr>
                    <tr>
                        <td class="highlight-good">Thursday</td>
                        <td class="highlight-good">64.54 pips</td>
                        <td class="highlight-good">55.90</td>
                        <td class="highlight-good">92%</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">📊</span> <strong>Escalada clara:</strong> Lunes → Jueves +26% rango. Si buscas volatilidad, prefiere Thursday.
            </div>

            <h3>Impacto Asia/London Alto por Día</h3>
            <table>
                <thead>
                    <tr>
                        <th>Condición</th>
                        <th>Monday</th>
                        <th>Tuesday</th>
                        <th>Wednesday</th>
                        <th>Thursday</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Ambos BAJO</td>
                        <td>43.36</td>
                        <td>45.58</td>
                        <td>53.63</td>
                        <td>58.99</td>
                    </tr>
                    <tr>
                        <td class="highlight-danger">Ambos ALTO</td>
                        <td class="highlight-danger">82.44</td>
                        <td class="highlight-danger">86.45</td>
                        <td class="highlight-danger">91.37</td>
                        <td class="highlight-danger">88.66</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">🚀</span> <strong>El multiplicador funciona todos los días:</strong> Asia+London alto = +90% rango en NY, independiente del día de semana.
            </div>

            <h3>Volatilidad por Década</h3>
            <table>
                <thead>
                    <tr>
                        <th>Período</th>
                        <th>Monday</th>
                        <th>Tuesday</th>
                        <th>Wednesday</th>
                        <th>Thursday</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>2000-2007</td>
                        <td>50.14</td>
                        <td>52.76</td>
                        <td>59.44</td>
                        <td>71.89</td>
                    </tr>
                    <tr>
                        <td class="highlight-warning">2008-2013</td>
                        <td class="highlight-warning">71.51</td>
                        <td class="highlight-warning">72.13</td>
                        <td class="highlight-warning">83.67</td>
                        <td class="highlight-warning">82.19</td>
                    </tr>
                    <tr>
                        <td>2014-2019</td>
                        <td>41.88</td>
                        <td>44.93</td>
                        <td>54.93</td>
                        <td>56.08</td>
                    </tr>
                    <tr>
                        <td>2020-2025</td>
                        <td>41.50</td>
                        <td>43.16</td>
                        <td>49.97</td>
                        <td>47.03</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">📉</span> <strong>2008-2013 (Crisis Financiera)</strong> mostró máxima volatilidad. Desde 2014 normalizó a niveles actuales.
            </div>
        </div>

        <!-- PASO 5 -->
        <div class="section">
            <h2><span class="emoji">⏰</span>PASO 5: Integración con H4</h2>

            <h3>Estadísticas H4 en NY (6,546 velas)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Rango Promedio</td>
                        <td class="highlight-good">60.83 pips</td>
                    </tr>
                    <tr>
                        <td>Rango Mediana</td>
                        <td>52.00 pips</td>
                    </tr>
                    <tr>
                        <td>Cuerpo Promedio</td>
                        <td>30.21 pips</td>
                    </tr>
                    <tr>
                        <td>Continuación siguiente H4</td>
                        <td>48.6%</td>
                    </tr>
                    <tr>
                        <td>Extensión cuando continúa</td>
                        <td>17.99 pips</td>
                    </tr>
                </tbody>
            </table>

            <h3>H4 Rango según % ATR Diario Completado ANTES de NY</h3>
            <table>
                <thead>
                    <tr>
                        <th>% ATR Completado</th>
                        <th>Casos</th>
                        <th>H4 Rango Esperado</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>0-25% (Tranquilo)</td>
                        <td>56</td>
                        <td>66.67 pips</td>
                    </tr>
                    <tr>
                        <td class="highlight-good">25-50% (ÓPTIMO)</td>
                        <td class="highlight-good">170</td>
                        <td class="highlight-good">85.50 pips 🔥</td>
                    </tr>
                    <tr>
                        <td>50-75%</td>
                        <td>296</td>
                        <td>75.63 pips</td>
                    </tr>
                    <tr>
                        <td>75-100% (Movido)</td>
                        <td>356</td>
                        <td>71.97 pips</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">⚙️</span> <strong>VENTANA ÓPTIMA IDENTIFICADA:</strong> Cuando 25-50% del ATR diario ya se completó antes de NY, el rango esperado es máximo (85.5 pips). Mercado muy tranquilo o muy movido = menos oportunidad.
            </div>

            <h3>H4 Rango según Extremos Semanales</h3>
            <table>
                <thead>
                    <tr>
                        <th>Posición</th>
                        <th>Casos</th>
                        <th>H4 Rango</th>
                        <th>Continuación Siguiente</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="highlight-good">Lejos de extremos</td>
                        <td class="highlight-good">1,850</td>
                        <td class="highlight-good">66.32 pips</td>
                        <td class="highlight-good">51.5%</td>
                    </tr>
                    <tr>
                        <td>Cerca máximo semanal</td>
                        <td>1,958</td>
                        <td>58.17 pips</td>
                        <td>48.3%</td>
                    </tr>
                    <tr>
                        <td>Cerca mínimo semanal</td>
                        <td>2,099</td>
                        <td>57.68 pips</td>
                        <td>46.8%</td>
                    </tr>
                    <tr>
                        <td>Ambos extremos</td>
                        <td>639</td>
                        <td>63.43 pips</td>
                        <td>46.6%</td>
                    </tr>
                </tbody>
            </table>

            <div class="insight">
                <span class="emoji">📍</span> <strong>Extremos semanales contienen rango:</strong> -12% cuando cerca de máximos/mínimos vs lejos. Mejor continuación (51.5%) lejos de extremos.
            </div>
        </div>

        <!-- CONCLUSIONES -->
        <div class="section">
            <h2><span class="emoji">🎯</span>Conclusiones y Recomendaciones</h2>

            <h3>Setup Operacional Ideal en NY</h3>
            <div style="background: rgba(34, 197, 94, 0.1); padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><span class="key-metric">Día: <span class="metric-value">Thursday</span></span></p>
                <p><span class="key-metric">Condición: <span class="metric-value">Asia + London alto</span></span></p>
                <p><span class="key-metric">ATR completado: <span class="metric-value">25-50%</span></span></p>
                <p><span class="key-metric">Posición: <span class="metric-value">Lejos extremos semanales</span></span></p>
                <p style="margin-top: 15px; font-weight: 600; color: #86efac;">
                    → Rango esperado: 80-90 pips en H4 NY
                </p>
            </div>

            <h3>Configuración de Riesgo</h3>
            <ul style="margin: 20px 0 20px 20px; color: #e2e8f0;">
                <li><span class="key-metric">Rango típico H4: <span class="metric-value">60.83 pips</span></span></li>
                <li><span class="key-metric">P25: <span class="metric-value">36</span></span> <span class="key-metric">P75: <span class="metric-value">75</span></span></li>
                <li><span class="key-metric">Continuación débil: <span class="metric-value">48.6%</span></span> (Mercado consolidador)</li>
            </ul>

            <h3>Evitar</h3>
            <ul style="margin: 20px 0; margin-left: 20px; color: #e2e8f0;">
                <li><span class="badge">Monday -20% rango</span></li>
                <li><span class="badge">Asia/London bajo -40% rango</span></li>
                <li><span class="badge">>75% ATR completado -15% rango</span></li>
                <li><span class="badge">Cerca extremos semanales -12% rango</span></li>
            </ul>
        </div>

        <footer>
            <p>📊 Analysis Dashboard | EUR/USD M1 (2000-2025)</p>
            <p>Todos los datos y CSVs disponibles en <code>/results/</code></p>
            <p style="margin-top: 15px; font-size: 0.85em; color: #475569;">
                Análisis realizado con Python + Pandas | 8.7M+ velas procesadas
            </p>
        </footer>
    </div>
</body>
</html>
"""

    with open(RESULTS_PATH / 'ANALYSIS_DASHBOARD.html', 'w') as f:
        f.write(html_content)

    print("✓ HTML Dashboard generado: ANALYSIS_DASHBOARD.html")
    return html_content


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("GENERANDO REPORTES")
    print("=" * 80)

    md = generate_markdown_report()
    html = generate_html_dashboard()

    print("\n" + "=" * 80)
    print("✅ REPORTES GENERADOS EXITOSAMENTE")
    print("=" * 80)
    print("\n📄 Archivos creados:")
    print("  1. ANALYSIS_REPORT.md - Reporte Markdown (para documentación/Git)")
    print("  2. ANALYSIS_DASHBOARD.html - Dashboard HTML (abre en navegador)")
    print("\n📂 Ubicación: /home/user/HISDATA-EURUSD/results/")
    print("\n💡 Uso:")
    print("  - Markdown: Edita en cualquier editor, visionable en GitHub")
    print("  - HTML: Descarga y abre en navegador (Chrome, Firefox, Safari)")
