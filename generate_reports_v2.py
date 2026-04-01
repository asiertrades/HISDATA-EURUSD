"""
Generador de Reportes V2: Markdown + HTML Dashboard (Corregido)
"""
from pathlib import Path
from datetime import datetime

RESULTS_PATH = Path('/home/user/HISDATA-EURUSD/results')

def generate_markdown():
    md = f"""# EUR/USD Analysis Report V2 (2000-2025)
**Período:** Mayo 2000 - Diciembre 2025
**Datos:** 8,720,939 velas M1 (2 filas corruptas eliminadas)
**Trading Days válidos:** 6,587 | **Semanas válidas:** 1,332
**Rango real:** 0.82290 - 1.60410
**Trading Day:** Open 17:00 ET → Close 16:59 ET siguiente
**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Resumen Ejecutivo

1. **10:00 ET es la hora más probable para HIGH y LOW del día** (~8-9%)
2. **08:00 ET es segunda hora más probable** (~7-8%)
3. **Monday concentra ~28-30% de los HIGH/LOW semanales**
4. **Semana alcista:** LOW el lunes (55%), HIGH el jueves (26%) → patrón OLHC (87%)
5. **Semana bajista:** HIGH el lunes (53%), LOW el jueves (26%) → patrón OHLC (86%)

---

## PASO 1: Datos Corregidos

| Métrica | Valor |
|---------|-------|
| Período | 2000-05-30 a 2025-12-31 |
| Velas M1 | 8,720,939 (limpio) |
| Trading Days válidos | 6,587 |
| Semanas válidas | 1,332 |
| Rango real | **0.82290 - 1.60410** |
| Máximo | 1.60410 (15 julio 2008) |
| Mínimo | 0.82290 |
| Rango diario promedio | 101.58 pips |
| Rango semanal promedio | 232.03 pips |

---

## PASO 2: ¿En qué HORA cae el HIGH/LOW de cada día?

### Distribución completa (ciclo 17:00→16:59)

| Hora ET | HIGH (%) | LOW (%) |
|---------|----------|---------|
| 17:00 | 6.01 | 6.82 |
| 18:00 | 3.19 | 3.19 |
| 19:00 | 3.55 | 3.31 |
| 20:00 | 3.22 | 4.54 |
| 21:00 | 2.81 | 2.95 |
| 22:00 | 1.85 | 1.70 |
| 23:00 | 1.52 | 1.05 |
| 00:00 | 1.06 | 1.21 |
| 01:00 | 2.37 | 1.67 |
| 02:00 | 5.78 | 4.62 |
| 03:00 | 6.10 | 5.97 |
| 04:00 | 4.96 | 3.70 |
| 05:00 | 3.63 | 2.98 |
| 06:00 | 3.02 | 2.72 |
| 07:00 | 3.22 | 3.60 |
| **08:00** | **6.85** | **7.89** |
| 09:00 | 5.86 | 6.13 |
| **10:00** | **8.06** | **8.71** |
| 11:00 | 5.72 | 6.63 |
| 12:00 | 4.39 | 4.75 |
| 13:00 | 3.81 | 3.37 |
| 14:00 | 4.40 | 4.63 |
| 15:00 | 3.64 | 3.29 |
| 16:00 | 4.96 | 4.57 |

### Top 5 horas

| Rank | HIGH del día | LOW del día |
|------|---|---|
| 1 | **10:00** (8.06%) | **10:00** (8.71%) |
| 2 | **08:00** (6.85%) | **08:00** (7.89%) |
| 3 | 03:00 (6.10%) | 17:00 (6.82%) |
| 4 | 17:00 (6.01%) | 11:00 (6.63%) |
| 5 | 09:00 (5.86%) | 09:00 (6.13%) |

### Insights
- **10:00 ET domina**: Es la hora #1 para HIGH (8.06%) y LOW (8.71%)
- **08:00-11:00 ET** (ventana NY abierto): Concentra ~27% de HIGHs y ~29% de LOWs
- **02:00-04:00 ET** (apertura Londres): Segundo pico de actividad
- **17:00 ET** (apertura trading day): Probabilidad significativa (~6-7%) por el gap/movimiento de apertura

### Por día de la semana

| Día | Top hora HIGH | Top hora LOW |
|-----|---|---|
| Monday | 10:00 (8.1%) | 10:00 (9.5%) |
| Tuesday | 14:00 (7.6%) | 10:00 (8.7%) |
| Wednesday | 08:00 (9.4%) | 10:00 (8.7%) |
| **Thursday** | **10:00 (11.0%)** | **08:00 (12.0%)** |

**Thursday es el día con extremos más concentrados:** 11% HIGH a las 10:00, 12% LOW a las 08:00.

---

## PASO 3: ¿En qué DÍA cae el HIGH/LOW de cada semana?

### Distribución completa

| Día | HIGH (%) | LOW (%) |
|-----|----------|---------|
| **Monday** | **27.85** | **30.41** |
| Tuesday | 14.64 | 15.62 |
| Wednesday | 15.62 | 13.89 |
| Thursday | 17.19 | 16.07 |
| Friday | 0.00 | 0.00 |

### Patrón OHLC vs OLHC

| Patrón | Probabilidad |
|--------|---|
| OHLC (High antes que Low) | 46.4% |
| OLHC (Low antes que High) | 50.8% |
| Mismo día | 2.8% |

### SEMANA ALCISTA vs BAJISTA (EL HALLAZGO MÁS POTENTE)

**Semana ALCISTA (693 semanas):**

| Día | HIGH (%) | LOW (%) |
|-----|----------|---------|
| Monday | 4.3 | **54.7** |
| Tuesday | 8.4 | 21.9 |
| Wednesday | 17.7 | 13.0 |
| **Thursday** | **25.5** | 7.2 |

- Patrón: **OLHC en 87%** de semanas alcistas
- LOW el LUNES (55%), HIGH el JUEVES (26%)

**Semana BAJISTA (639 semanas):**

| Día | HIGH (%) | LOW (%) |
|-----|----------|---------|
| **Monday** | **53.4** | 4.1 |
| Tuesday | 21.4 | 8.8 |
| Wednesday | 13.3 | 14.9 |
| Thursday | 8.1 | **25.7** |

- Patrón: **OHLC en 86%** de semanas bajistas
- HIGH el LUNES (53%), LOW el JUEVES (26%)

### Insight Operacional

El lunes DEFINE la semana:
- Si el lunes marca el LOW → semana probablemente ALCISTA (OLHC)
- Si el lunes marca el HIGH → semana probablemente BAJISTA (OHLC)
- El jueves tiende a marcar el extremo OPUESTO al del lunes

---

## Conclusiones Operacionales

1. **Timing de extremos diarios:** Busca los HIGH/LOW entre 08:00-11:00 ET (ventana NY). 10:00 ET es la hora pico.
2. **Thursday es el día más "explosivo":** 11% de HIGHs a las 10:00, 12% de LOWs a las 08:00.
3. **Monday define la semana:** 55% de LOWs semanales (alcista) o 53% de HIGHs semanales (bajista) se forman el lunes.
4. **Patrón semanal claro:** OLHC (87% en alcistas) o OHLC (86% en bajistas) — el extremo del lunes predice la dirección.
5. **Rango real:** 0.8229 - 1.6041 (máximo en julio 2008).

---

**Datos:** 8.7M+ velas EUR/USD M1 (2000-2025) | **Rango diario promedio:** 101.58 pips
"""

    with open(RESULTS_PATH / 'v2_ANALYSIS_REPORT.md', 'w') as f:
        f.write(md)
    print("✓ Markdown generado")


def generate_html():
    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EUR/USD Analysis V2 (2000-2025)</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#0f172a,#1e293b);color:#e2e8f0;line-height:1.6;padding:20px}
.container{max-width:1200px;margin:0 auto}
header{text-align:center;margin-bottom:40px;padding:30px;background:rgba(30,41,59,0.8);border-radius:12px;border-left:4px solid #3b82f6}
h1{font-size:2.2em;margin-bottom:10px;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
h2{font-size:1.6em;margin:35px 0 15px;color:#60a5fa;border-bottom:2px solid #3b82f6;padding-bottom:8px}
h3{font-size:1.2em;margin:20px 0 12px;color:#93c5fd}
.section{background:rgba(30,41,59,0.6);border-radius:12px;padding:25px;margin-bottom:25px;border:1px solid #334155;box-shadow:0 10px 25px rgba(0,0,0,0.3)}
table{width:100%;border-collapse:collapse;margin:15px 0;background:rgba(15,23,42,0.4);border-radius:8px;overflow:hidden}
th{background:linear-gradient(135deg,#3b82f6,#2563eb);padding:12px;text-align:left;font-weight:600;color:white}
td{padding:10px 12px;border-bottom:1px solid #334155}
tr:hover{background:rgba(59,130,246,0.1)}
.g{background:rgba(34,197,94,0.12);color:#86efac;font-weight:600}
.r{background:rgba(239,68,68,0.12);color:#fca5a5;font-weight:600}
.y{background:rgba(234,179,8,0.12);color:#fcd34d;font-weight:600}
.insight{background:rgba(59,130,246,0.15);border-left:4px solid #3b82f6;padding:15px;margin:18px 0;border-radius:6px}
.big-number{font-size:2em;font-weight:700;color:#60a5fa}
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:20px 0}
.metric-card{background:rgba(15,23,42,0.5);padding:20px;border-radius:8px;border-left:3px solid #60a5fa;text-align:center}
.metric-card .label{font-size:0.85em;color:#94a3b8;margin-bottom:5px}
.metric-card .value{font-size:1.6em;font-weight:700;color:#60a5fa}
footer{text-align:center;margin-top:40px;padding:20px;border-top:1px solid #334155;color:#64748b;font-size:0.9em}
.bar{display:inline-block;height:18px;border-radius:3px;margin-right:4px;vertical-align:middle}
.bar-h{background:linear-gradient(90deg,#3b82f6,#60a5fa)}
.bar-l{background:linear-gradient(90deg,#ef4444,#f87171)}
</style>
</head>
<body>
<div class="container">

<header>
<h1>EUR/USD Analysis V2</h1>
<p>Análisis Cuantitativo M1 — Datos Corregidos (2000-2025)</p>
<div style="margin-top:15px;color:#94a3b8">
<strong>Rango real:</strong> 0.82290 - 1.60410 |
<strong>Trading Days:</strong> 6,587 |
<strong>Semanas:</strong> 1,332
</div>
</header>

<!-- MÉTRICAS CLAVE -->
<div class="section">
<h2>Métricas Clave</h2>
<div class="metric-grid">
<div class="metric-card"><div class="label">Velas M1</div><div class="value">8.72M</div></div>
<div class="metric-card"><div class="label">Rango Diario Promedio</div><div class="value">101.6 pips</div></div>
<div class="metric-card"><div class="label">Rango Semanal Promedio</div><div class="value">232.0 pips</div></div>
<div class="metric-card"><div class="label">Máximo Histórico</div><div class="value">1.6041</div></div>
<div class="metric-card"><div class="label">Mínimo Histórico</div><div class="value">0.8229</div></div>
<div class="metric-card"><div class="label">Período</div><div class="value">25 años</div></div>
</div>
</div>

<!-- PASO 2: EXTREMOS POR HORA -->
<div class="section">
<h2>¿En qué HORA cae el HIGH/LOW del día?</h2>

<h3>Distribución completa (ciclo 17:00 → 16:59 ET)</h3>
<table>
<thead><tr><th>Hora ET</th><th>HIGH (%)</th><th></th><th>LOW (%)</th><th></th></tr></thead>
<tbody>
<tr><td>17:00</td><td>6.01</td><td><span class="bar bar-h" style="width:60px"></span></td><td>6.82</td><td><span class="bar bar-l" style="width:68px"></span></td></tr>
<tr><td>18:00</td><td>3.19</td><td><span class="bar bar-h" style="width:32px"></span></td><td>3.19</td><td><span class="bar bar-l" style="width:32px"></span></td></tr>
<tr><td>19:00</td><td>3.55</td><td><span class="bar bar-h" style="width:36px"></span></td><td>3.31</td><td><span class="bar bar-l" style="width:33px"></span></td></tr>
<tr><td>20:00</td><td>3.22</td><td><span class="bar bar-h" style="width:32px"></span></td><td>4.54</td><td><span class="bar bar-l" style="width:45px"></span></td></tr>
<tr><td>21:00</td><td>2.81</td><td><span class="bar bar-h" style="width:28px"></span></td><td>2.95</td><td><span class="bar bar-l" style="width:30px"></span></td></tr>
<tr><td>22:00</td><td>1.85</td><td><span class="bar bar-h" style="width:19px"></span></td><td>1.70</td><td><span class="bar bar-l" style="width:17px"></span></td></tr>
<tr><td>23:00</td><td>1.52</td><td><span class="bar bar-h" style="width:15px"></span></td><td>1.05</td><td><span class="bar bar-l" style="width:11px"></span></td></tr>
<tr><td>00:00</td><td>1.06</td><td><span class="bar bar-h" style="width:11px"></span></td><td>1.21</td><td><span class="bar bar-l" style="width:12px"></span></td></tr>
<tr><td>01:00</td><td>2.37</td><td><span class="bar bar-h" style="width:24px"></span></td><td>1.67</td><td><span class="bar bar-l" style="width:17px"></span></td></tr>
<tr><td class="y">02:00</td><td class="y">5.78</td><td><span class="bar bar-h" style="width:58px"></span></td><td class="y">4.62</td><td><span class="bar bar-l" style="width:46px"></span></td></tr>
<tr><td class="y">03:00</td><td class="y">6.10</td><td><span class="bar bar-h" style="width:61px"></span></td><td class="y">5.97</td><td><span class="bar bar-l" style="width:60px"></span></td></tr>
<tr><td>04:00</td><td>4.96</td><td><span class="bar bar-h" style="width:50px"></span></td><td>3.70</td><td><span class="bar bar-l" style="width:37px"></span></td></tr>
<tr><td>05:00</td><td>3.63</td><td><span class="bar bar-h" style="width:36px"></span></td><td>2.98</td><td><span class="bar bar-l" style="width:30px"></span></td></tr>
<tr><td>06:00</td><td>3.02</td><td><span class="bar bar-h" style="width:30px"></span></td><td>2.72</td><td><span class="bar bar-l" style="width:27px"></span></td></tr>
<tr><td>07:00</td><td>3.22</td><td><span class="bar bar-h" style="width:32px"></span></td><td>3.60</td><td><span class="bar bar-l" style="width:36px"></span></td></tr>
<tr><td class="g">08:00</td><td class="g">6.85</td><td><span class="bar bar-h" style="width:69px"></span></td><td class="g">7.89</td><td><span class="bar bar-l" style="width:79px"></span></td></tr>
<tr><td class="g">09:00</td><td class="g">5.86</td><td><span class="bar bar-h" style="width:59px"></span></td><td class="g">6.13</td><td><span class="bar bar-l" style="width:61px"></span></td></tr>
<tr><td class="g">10:00</td><td class="g">8.06</td><td><span class="bar bar-h" style="width:81px"></span></td><td class="g">8.71</td><td><span class="bar bar-l" style="width:87px"></span></td></tr>
<tr><td class="g">11:00</td><td class="g">5.72</td><td><span class="bar bar-h" style="width:57px"></span></td><td class="g">6.63</td><td><span class="bar bar-l" style="width:66px"></span></td></tr>
<tr><td>12:00</td><td>4.39</td><td><span class="bar bar-h" style="width:44px"></span></td><td>4.75</td><td><span class="bar bar-l" style="width:48px"></span></td></tr>
<tr><td>13:00</td><td>3.81</td><td><span class="bar bar-h" style="width:38px"></span></td><td>3.37</td><td><span class="bar bar-l" style="width:34px"></span></td></tr>
<tr><td>14:00</td><td>4.40</td><td><span class="bar bar-h" style="width:44px"></span></td><td>4.63</td><td><span class="bar bar-l" style="width:46px"></span></td></tr>
<tr><td>15:00</td><td>3.64</td><td><span class="bar bar-h" style="width:36px"></span></td><td>3.29</td><td><span class="bar bar-l" style="width:33px"></span></td></tr>
<tr><td>16:00</td><td>4.96</td><td><span class="bar bar-h" style="width:50px"></span></td><td>4.57</td><td><span class="bar bar-l" style="width:46px"></span></td></tr>
</tbody>
</table>

<div class="insight">
<strong>10:00 ET es la hora #1</strong> para extremos diarios (HIGH 8.06%, LOW 8.71%). La ventana <strong>08:00-11:00 ET</strong> concentra ~27% de HIGHs y ~29% de LOWs del día.
</div>

<h3>Thursday: el día más concentrado</h3>
<table>
<thead><tr><th>Hora</th><th>HIGH (%)</th><th>LOW (%)</th></tr></thead>
<tbody>
<tr><td class="g">10:00</td><td class="g">11.0%</td><td>9.2%</td></tr>
<tr><td class="r">08:00</td><td>9.5%</td><td class="r">12.0%</td></tr>
<tr><td>09:00</td><td>5.8%</td><td>7.5%</td></tr>
</tbody>
</table>
<div class="insight">
<strong>Thursday:</strong> 11% de HIGHs a las 10:00, 12% de LOWs a las 08:00. El día más predecible para timing de extremos.
</div>
</div>

<!-- PASO 3: EXTREMOS POR DÍA -->
<div class="section">
<h2>¿En qué DÍA cae el HIGH/LOW de cada semana?</h2>

<h3>Distribución general (1,332 semanas)</h3>
<table>
<thead><tr><th>Día</th><th>HIGH (%)</th><th></th><th>LOW (%)</th><th></th></tr></thead>
<tbody>
<tr><td class="g">Monday</td><td class="g">27.85</td><td><span class="bar bar-h" style="width:140px"></span></td><td class="g">30.41</td><td><span class="bar bar-l" style="width:152px"></span></td></tr>
<tr><td>Tuesday</td><td>14.64</td><td><span class="bar bar-h" style="width:73px"></span></td><td>15.62</td><td><span class="bar bar-l" style="width:78px"></span></td></tr>
<tr><td>Wednesday</td><td>15.62</td><td><span class="bar bar-h" style="width:78px"></span></td><td>13.89</td><td><span class="bar bar-l" style="width:69px"></span></td></tr>
<tr><td>Thursday</td><td>17.19</td><td><span class="bar bar-h" style="width:86px"></span></td><td>16.07</td><td><span class="bar bar-l" style="width:80px"></span></td></tr>
<tr><td>Friday</td><td>0.00</td><td></td><td>0.00</td><td></td></tr>
</tbody>
</table>

<div class="insight">
<strong>Monday concentra ~28-30% de extremos semanales.</strong> Es el día que más define la estructura de la semana.
</div>

<h3>Patrón OHLC vs OLHC</h3>
<table>
<thead><tr><th>Patrón</th><th>Probabilidad</th></tr></thead>
<tbody>
<tr><td>OHLC (High antes que Low)</td><td>46.4%</td></tr>
<tr><td>OLHC (Low antes que High)</td><td>50.8%</td></tr>
<tr><td>Mismo día</td><td>2.8%</td></tr>
</tbody>
</table>
</div>

<!-- HALLAZGO PRINCIPAL -->
<div class="section" style="border-left:4px solid #f59e0b">
<h2 style="color:#f59e0b">EL HALLAZGO MÁS POTENTE: Semana Alcista vs Bajista</h2>

<h3 style="color:#22c55e">Semana ALCISTA (693 semanas) → Patrón OLHC en 87%</h3>
<table>
<thead><tr><th>Día</th><th>HIGH (%)</th><th>LOW (%)</th><th>Rol</th></tr></thead>
<tbody>
<tr><td>Monday</td><td>4.3</td><td class="g">54.7</td><td class="g">LOW de la semana</td></tr>
<tr><td>Tuesday</td><td>8.4</td><td>21.9</td><td></td></tr>
<tr><td>Wednesday</td><td>17.7</td><td>13.0</td><td></td></tr>
<tr><td class="g">Thursday</td><td class="g">25.5</td><td>7.2</td><td class="g">HIGH de la semana</td></tr>
</tbody>
</table>

<h3 style="color:#ef4444">Semana BAJISTA (639 semanas) → Patrón OHLC en 86%</h3>
<table>
<thead><tr><th>Día</th><th>HIGH (%)</th><th>LOW (%)</th><th>Rol</th></tr></thead>
<tbody>
<tr><td class="r">Monday</td><td class="r">53.4</td><td>4.1</td><td class="r">HIGH de la semana</td></tr>
<tr><td>Tuesday</td><td>21.4</td><td>8.8</td><td></td></tr>
<tr><td>Wednesday</td><td>13.3</td><td>14.9</td><td></td></tr>
<tr><td>Thursday</td><td>8.1</td><td class="r">25.7</td><td class="r">LOW de la semana</td></tr>
</tbody>
</table>

<div class="insight" style="border-color:#f59e0b;background:rgba(245,158,11,0.15)">
<strong>REGLA OPERACIONAL:</strong><br>
- Si el <strong>lunes marca el LOW</strong> → semana probablemente ALCISTA (OLHC 87%)<br>
- Si el <strong>lunes marca el HIGH</strong> → semana probablemente BAJISTA (OHLC 86%)<br>
- El <strong>jueves</strong> tiende a marcar el extremo OPUESTO al del lunes
</div>
</div>

<footer>
<p>EUR/USD Analysis V2 | 8.7M+ velas M1 (2000-2025) | Datos corregidos</p>
<p>Trading Day: Open 17:00 ET | Rango real: 0.8229 - 1.6041</p>
</footer>
</div>
</body>
</html>"""

    with open(RESULTS_PATH / 'v2_ANALYSIS_DASHBOARD.html', 'w') as f:
        f.write(html)
    print("✓ HTML Dashboard generado")


if __name__ == '__main__':
    generate_markdown()
    generate_html()
    print("✅ Reportes V2 generados en results/")
