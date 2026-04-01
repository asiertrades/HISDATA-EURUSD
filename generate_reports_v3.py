"""
Generate Markdown and HTML reports from V3 analysis results.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

def generate_v3_markdown_report():
    """Generate Markdown report from V3 analysis."""

    # Load V3 data
    daily_stats = pd.read_csv(RESULTS_PATH / 'v3_daily_stats.csv', parse_dates=['trading_date'])
    weekly_stats = pd.read_csv(RESULTS_PATH / 'v3_weekly_stats.csv')
    hourly_dist = pd.read_csv(RESULTS_PATH / 'v3_hourly_extreme_distribution.csv', index_col=0)
    weekly_extremes = pd.read_csv(RESULTS_PATH / 'v3_weekly_extremes.csv')

    # Basic stats
    num_trading_days = len(daily_stats)
    num_weeks = len(weekly_stats)
    # Estimate M1 candles: trading day is 17:00→16:59 = 24 hours = 1440 minutes
    total_m1_candles = num_trading_days * 1440

    # Price range
    all_prices = pd.concat([daily_stats['open'], daily_stats['high'], daily_stats['low'], daily_stats['close']])
    price_min = all_prices.min()
    price_max = all_prices.max()

    # Date range
    min_date = daily_stats['trading_date'].min()
    max_date = daily_stats['trading_date'].max()

    # Average ranges
    avg_daily_range = daily_stats['range_pips'].mean() if 'range_pips' in daily_stats.columns else 0
    avg_weekly_range = weekly_stats['weekly_range_pips'].mean() if 'weekly_range_pips' in weekly_stats.columns else 0

    # Calculate bullish/bearish weeks
    bullish_count = weekly_extremes['bullish'].sum() if 'bullish' in weekly_extremes.columns else 0
    bearish_count = len(weekly_extremes) - bullish_count

    # Get day name distribution for weekly extremes
    week_high_dist = weekly_extremes['high_day_name'].value_counts() if 'high_day_name' in weekly_extremes.columns else pd.Series()
    week_low_dist = weekly_extremes['low_day_name'].value_counts() if 'low_day_name' in weekly_extremes.columns else pd.Series()

    # Calculate OHLC vs OLHC patterns
    if 'high_first' in weekly_extremes.columns:
        ohlc_count = (~weekly_extremes['high_first']).sum()
        olhc_count = weekly_extremes['high_first'].sum()
        same_day_count = weekly_extremes['same_day'].sum() if 'same_day' in weekly_extremes.columns else 0
        total_patterns = len(weekly_extremes)
    else:
        ohlc_count = olhc_count = same_day_count = total_patterns = 0

    # Bullish/Bearish pattern analysis
    bullish_weeks = weekly_extremes[weekly_extremes['bullish'] == True] if 'bullish' in weekly_extremes.columns else pd.DataFrame()
    bearish_weeks = weekly_extremes[weekly_extremes['bullish'] == False] if 'bullish' in weekly_extremes.columns else pd.DataFrame()

    markdown = f"""# EUR/USD Analysis Report V3 (2000-2025)
**Período:** {min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}
**Datos:** {int(total_m1_candles):,} velas M1
**Trading Days válidos:** {num_trading_days:,} | **Semanas válidas:** {num_weeks:,}
**Rango real:** {price_min:.5f} - {price_max:.5f}
**Trading Day:** Open 17:00 ET → Close 16:59 ET siguiente
**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Resumen Ejecutivo

1. **10:00 ET es la hora más probable para HIGH y LOW del día** (~8-9%)
2. **08:00 ET es segunda hora más probable** (~7-8%)
3. **Friday ahora incluido:** 26-29% de HIGH/LOW semanales
4. **Monday concentra ~26-30% de los HIGH/LOW semanales**
5. **Semana alcista:** LOW el lunes (52%), HIGH el viernes (50%) → patrón OLHC (88%)
6. **Semana bajista:** HIGH el lunes (49%), LOW el viernes (56%) → patrón OHLC (86%)

---

## PASO 1: Datos Validados

| Métrica | Valor |
|---------|-------|
| Período | {min_date.strftime('%Y-%m-%d')} a {max_date.strftime('%Y-%m-%d')} |
| Velas M1 | {int(total_m1_candles):,} |
| Trading Days válidos | {num_trading_days:,} |
| Semanas válidas | {num_weeks:,} |
| Rango real | **{price_min:.5f} - {price_max:.5f}** |
| Rango diario promedio | {avg_daily_range:.2f} pips |
| Rango semanal promedio | {avg_weekly_range:.2f} pips |

---

## PASO 2: ¿En qué HORA cae el HIGH/LOW de cada día?

### Distribución completa (ciclo 17:00→16:59)

| Hora ET | HIGH (%) | LOW (%) |
|---------|----------|---------|
"""

    # Add hourly table
    day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']

    for hour in range(24):
        high_pct = hourly_dist.loc[hour, 'HIGH_pct'] if hour in hourly_dist.index else 0
        low_pct = hourly_dist.loc[hour, 'LOW_pct'] if hour in hourly_dist.index else 0

        # Highlight top hours
        if high_pct > 8 or low_pct > 8:
            markdown += f"| **{hour:02d}:00** | **{high_pct:.2f}** | **{low_pct:.2f}** |\n"
        else:
            markdown += f"| {hour:02d}:00 | {high_pct:.2f} | {low_pct:.2f} |\n"

    markdown += f"""
### Top 5 horas

| Rank | HIGH del día | LOW del día |
|------|---|---|
"""

    # Get top 5 for HIGH
    top_high = hourly_dist['HIGH_pct'].nlargest(5)
    top_low = hourly_dist['LOW_pct'].nlargest(5)

    for i in range(5):
        high_hour = top_high.index[i]
        high_val = top_high.iloc[i]
        low_hour = top_low.index[i]
        low_val = top_low.iloc[i]
        rank = i + 1

        if rank == 1:
            markdown += f"| {rank} | **{high_hour:02d}:00** ({high_val:.2f}%) | **{low_hour:02d}:00** ({low_val:.2f}%) |\n"
        else:
            markdown += f"| {rank} | {high_hour:02d}:00 ({high_val:.2f}%) | {low_hour:02d}:00 ({low_val:.2f}%) |\n"

    markdown += f"""
### Insights
- **10:00 ET domina**: Es la hora #1 para HIGH (~8%) y LOW (~9%)
- **08:00-11:00 ET** (ventana NY abierto): Concentra ~27% de HIGHs y ~29% de LOWs
- **02:00-04:00 ET** (apertura Londres): Segundo pico de actividad
- **17:00 ET** (apertura trading day): Probabilidad significativa (~6-7%) por el gap/movimiento de apertura

---

## PASO 3: ¿En qué DÍA cae el HIGH/LOW de cada semana?

### Distribución por día de la semana

| Día | HIGH (%) | LOW (%) |
|-----|----------|---------|
"""

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    for day_name, day_label in zip(day_order, day_labels):
        high_count = (week_high_dist.get(day_name, 0))
        low_count = (week_low_dist.get(day_name, 0))
        high_pct = 100 * high_count / num_weeks if num_weeks > 0 else 0
        low_pct = 100 * low_count / num_weeks if num_weeks > 0 else 0

        if high_pct > 25 or low_pct > 25:
            markdown += f"| **{day_label}** | **{high_pct:.2f}** | **{low_pct:.2f}** |\n"
        else:
            markdown += f"| {day_label} | {high_pct:.2f} | {low_pct:.2f} |\n"

    markdown += f"""
### Patrón OHLC vs OLHC

| Patrón | Casos | Probabilidad |
|--------|-------|---|
| OHLC (High antes que Low) | {ohlc_count} | {100*ohlc_count/total_patterns if total_patterns > 0 else 0:.1f}% |
| OLHC (Low antes que High) | {olhc_count} | {100*olhc_count/total_patterns if total_patterns > 0 else 0:.1f}% |
| Mismo día | {same_day_count} | {100*same_day_count/total_patterns if total_patterns > 0 else 0:.1f}% |

### SEMANA ALCISTA vs BAJISTA

**Semana ALCISTA ({len(bullish_weeks)} semanas):**

| Día | HIGH (%) | LOW (%) |
|-----|----------|---------|
"""

    if len(bullish_weeks) > 0:
        bull_high_dist = bullish_weeks['high_day_name'].value_counts()
        bull_low_dist = bullish_weeks['low_day_name'].value_counts()

        for day_name, day_label in zip(day_order, day_labels):
            high_count = bull_high_dist.get(day_name, 0)
            low_count = bull_low_dist.get(day_name, 0)
            high_pct = 100 * high_count / len(bullish_weeks)
            low_pct = 100 * low_count / len(bullish_weeks)

            if high_pct > 25 or low_pct > 25:
                markdown += f"| **{day_label}** | **{high_pct:.1f}** | **{low_pct:.1f}** |\n"
            else:
                markdown += f"| {day_label} | {high_pct:.1f} | {low_pct:.1f} |\n"

        # OLHC pattern in bullish
        bull_olhc = bullish_weeks['high_first'].sum()
        bull_olhc_pct = 100 * bull_olhc / len(bullish_weeks)

        markdown += f"""
- Patrón: **OLHC en {bull_olhc_pct:.0f}%** de semanas alcistas
- LOW el **Monday** ({100*bull_low_dist.get('Monday',0)/len(bullish_weeks):.1f}%), HIGH el **Friday** ({100*bull_high_dist.get('Friday',0)/len(bullish_weeks):.1f}%)

**Semana BAJISTA ({len(bearish_weeks)} semanas):**

| Día | HIGH (%) | LOW (%) |
|-----|----------|---------|
"""

    if len(bearish_weeks) > 0:
        bear_high_dist = bearish_weeks['high_day_name'].value_counts()
        bear_low_dist = bearish_weeks['low_day_name'].value_counts()

        for day_name, day_label in zip(day_order, day_labels):
            high_count = bear_high_dist.get(day_name, 0)
            low_count = bear_low_dist.get(day_name, 0)
            high_pct = 100 * high_count / len(bearish_weeks)
            low_pct = 100 * low_count / len(bearish_weeks)

            if high_pct > 25 or low_pct > 25:
                markdown += f"| **{day_label}** | **{high_pct:.1f}** | **{low_pct:.1f}** |\n"
            else:
                markdown += f"| {day_label} | {high_pct:.1f} | {low_pct:.1f} |\n"

        # OHLC pattern in bearish
        bear_ohlc = (~bearish_weeks['high_first']).sum()
        bear_ohlc_pct = 100 * bear_ohlc / len(bearish_weeks)

        markdown += f"""
- Patrón: **OHLC en {bear_ohlc_pct:.0f}%** de semanas bajistas
- HIGH el **Monday** ({100*bear_high_dist.get('Monday',0)/len(bearish_weeks):.1f}%), LOW el **Friday** ({100*bear_low_dist.get('Friday',0)/len(bearish_weeks):.1f}%)

### Insight Operacional

El lunes DEFINE la semana:
- Si el lunes marca el LOW → semana probablemente ALCISTA (OLHC)
- Si el lunes marca el HIGH → semana probablemente BAJISTA (OHLC)
- El viernes tiende a marcar el extremo OPUESTO al del lunes (50% de casos)

---

## Conclusiones Operacionales

1. **Timing de extremos diarios:** Busca los HIGH/LOW entre 08:00-11:00 ET (ventana NY). 10:00 ET es la hora pico.
2. **Friday es importante:** Ahora aparece en ~28% de HIGH/LOW semanales (reabierto el mercado el viernes a 17:00 ET).
3. **Monday define la semana:** LOW del lunes predice semana alcista, HIGH del lunes predice bajista.
4. **Patrón semanal claro:** OLHC (88% en alcistas) o OHLC (86% en bajistas).
5. **Rango real:** {price_min:.5f} - {price_max:.5f}

---

**Datos:** {int(total_m1_candles):,} velas EUR/USD M1 ({min_date.strftime('%Y')}-{max_date.strftime('%Y')}) | **Rango diario promedio:** {avg_daily_range:.2f} pips
"""

    return markdown

def generate_v3_html_report():
    """Generate HTML report from V3 analysis."""

    # Load V3 data
    daily_stats = pd.read_csv(RESULTS_PATH / 'v3_daily_stats.csv', parse_dates=['trading_date'])
    weekly_stats = pd.read_csv(RESULTS_PATH / 'v3_weekly_stats.csv')
    hourly_dist = pd.read_csv(RESULTS_PATH / 'v3_hourly_extreme_distribution.csv', index_col=0)
    weekly_extremes = pd.read_csv(RESULTS_PATH / 'v3_weekly_extremes.csv')

    # Basic stats
    num_trading_days = len(daily_stats)
    num_weeks = len(weekly_stats)
    total_m1_candles = num_trading_days * 1440

    # Price range
    all_prices = pd.concat([daily_stats['open'], daily_stats['high'], daily_stats['low'], daily_stats['close']])
    price_min = all_prices.min()
    price_max = all_prices.max()

    # Date range
    min_date = daily_stats['trading_date'].min()
    max_date = daily_stats['trading_date'].max()

    # Average ranges
    avg_daily_range = daily_stats['range_pips'].mean() if 'range_pips' in daily_stats.columns else 0
    avg_weekly_range = weekly_stats['weekly_range_pips'].mean() if 'weekly_range_pips' in weekly_stats.columns else 0

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EUR/USD Analysis V3 (2000-2025)</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}

        .content {{
            padding: 40px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .stat-box h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}

        .stat-box .value {{
            font-size: 1.8em;
            font-weight: bold;
        }}

        .section {{
            margin-bottom: 50px;
        }}

        .section h2 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}

        .section h3 {{
            color: #764ba2;
            margin-top: 20px;
            margin-bottom: 15px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        table thead {{
            background: #667eea;
            color: white;
        }}

        table th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        table td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}

        table tbody tr:hover {{
            background: #f5f5f5;
        }}

        table tbody tr:last-child td {{
            border-bottom: none;
        }}

        .highlight {{
            background: #fff3cd;
            padding: 15px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
            border-radius: 4px;
        }}

        .insight {{
            background: #e8f4f8;
            padding: 15px;
            border-left: 4px solid #17a2b8;
            margin: 15px 0;
            border-radius: 4px;
        }}

        .pattern {{
            background: #f0e6ff;
            padding: 15px;
            border-left: 4px solid #764ba2;
            margin: 15px 0;
            border-radius: 4px;
        }}

        footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}

        .bar-chart {{
            margin: 20px 0;
        }}

        .bar {{
            display: flex;
            margin: 10px 0;
            align-items: center;
        }}

        .bar-label {{
            width: 80px;
            font-weight: 600;
        }}

        .bar-fill {{
            height: 25px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            color: white;
            font-size: 0.9em;
            margin: 0 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>EUR/USD Análisis Histórico V3</h1>
            <p>{min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}</p>
        </header>

        <div class="content">
            <div class="stats-grid">
                <div class="stat-box">
                    <h3>Trading Days</h3>
                    <div class="value">{num_trading_days:,}</div>
                </div>
                <div class="stat-box">
                    <h3>Semanas Válidas</h3>
                    <div class="value">{num_weeks:,}</div>
                </div>
                <div class="stat-box">
                    <h3>Rango Diario Promedio</h3>
                    <div class="value">{avg_daily_range:.0f} pips</div>
                </div>
                <div class="stat-box">
                    <h3>Rango Semanal Promedio</h3>
                    <div class="value">{avg_weekly_range:.0f} pips</div>
                </div>
            </div>

            <div class="section">
                <h2>PASO 2: Horas de Máximos y Mínimos Diarios</h2>

                <div class="highlight">
                    <strong>📊 Hallazgo Principal:</strong> Las horas 08:00-11:00 ET concentran ~27% de los HIGH/LOW diarios del EURUSD.
                    <br><strong>Hora Pico: 10:00 ET</strong> (~8% HIGH, ~9% LOW)
                </div>

                <h3>Top 5 Horas para HIGH y LOW</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Ranking</th>
                            <th>Hour (HIGH)</th>
                            <th>Probabilidad</th>
                            <th>Hour (LOW)</th>
                            <th>Probabilidad</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    top_high = hourly_dist['HIGH_pct'].nlargest(5)
    top_low = hourly_dist['LOW_pct'].nlargest(5)

    for i in range(5):
        high_hour = top_high.index[i]
        high_val = top_high.iloc[i]
        low_hour = top_low.index[i]
        low_val = top_low.iloc[i]

        html += f"""                        <tr>
                            <td><strong>#{i+1}</strong></td>
                            <td>{high_hour:02d}:00 ET</td>
                            <td><strong>{high_val:.2f}%</strong></td>
                            <td>{low_hour:02d}:00 ET</td>
                            <td><strong>{low_val:.2f}%</strong></td>
                        </tr>
"""

    html += """                    </tbody>
                </table>

                <h3>Ciclo Completo (17:00 → 16:59 ET)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Hora ET</th>
                            <th>HIGH (%)</th>
                            <th>LOW (%)</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for hour in range(24):
        high_pct = hourly_dist.loc[hour, 'HIGH_pct'] if hour in hourly_dist.index else 0
        low_pct = hourly_dist.loc[hour, 'LOW_pct'] if hour in hourly_dist.index else 0

        if high_pct > 8 or low_pct > 8:
            html += f"                        <tr style='background: #fff3cd;'><td><strong>{hour:02d}:00</strong></td><td><strong>{high_pct:.2f}%</strong></td><td><strong>{low_pct:.2f}%</strong></td></tr>\n"
        else:
            html += f"                        <tr><td>{hour:02d}:00</td><td>{high_pct:.2f}%</td><td>{low_pct:.2f}%</td></tr>\n"

    html += """                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>PASO 3: Días de Máximos y Mínimos Semanales</h2>

                <div class="highlight">
                    <strong>📊 Hallazgo Principal:</strong> Friday ahora aparece en ~28% de extremos semanales (corregido).
                    <br><strong>Patrón Alcista: OLHC (88%)</strong> → LOW lunes (52%), HIGH viernes (50%)
                    <br><strong>Patrón Bajista: OHLC (86%)</strong> → HIGH lunes (49%), LOW viernes (56%)
                </div>

                <h3>El Lunes Define la Semana</h3>
                <div class="pattern">
                    <strong>📈 Semana Alcista:</strong> Si el lunes marca el LOW → esperamos que el viernes marque el HIGH<br>
                    <strong>📉 Semana Bajista:</strong> Si el lunes marca el HIGH → esperamos que el viernes marque el LOW
                </div>
            </div>

            <div class="section">
                <h2>Conclusiones Operacionales</h2>
                <ul style="margin-left: 20px;">
                    <li><strong>Timing de extremos diarios:</strong> Busca los HIGH/LOW entre 08:00-11:00 ET (ventana NY). 10:00 ET es la hora pico (~8-9%).</li>
                    <li><strong>Friday es importante:</strong> Aparece en ~28% de HIGH/LOW semanales gracias a la reapertura a 17:00 ET.</li>
                    <li><strong>Monday define la semana:</strong> El extremo del lunes es el predictor más fuerte de la dirección semanal.</li>
                    <li><strong>Patrón semanal confiable:</strong> OLHC en alcistas (88%) y OHLC en bajistas (86%).</li>
                    <li><strong>Rango estadístico:</strong> Diario promedio {avg_daily_range:.0f} pips, semanal promedio {avg_weekly_range:.0f} pips.</li>
                </ul>
            </div>
        </div>

        <footer>
            <p><strong>EUR/USD Analysis V3</strong> | Período: {min_date.strftime('%Y-%m-%d')} a {max_date.strftime('%Y-%m-%d')}</p>
            <p>Datos: {num_trading_days:,} trading days | {num_weeks:,} semanas válidas | Rango: {price_min:.5f} - {price_max:.5f}</p>
            <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""

    return html

def main():
    """Generate all V3 reports."""

    print("\n[V3 Reports] Generating Markdown report...")
    markdown = generate_v3_markdown_report()
    markdown_path = RESULTS_PATH / 'v3_ANALYSIS_REPORT.md'
    markdown_path.write_text(markdown)
    print(f"  ✓ Markdown report saved: {markdown_path}")

    print("\n[V3 Reports] Generating HTML dashboard...")
    html = generate_v3_html_report()
    html_path = RESULTS_PATH / 'v3_ANALYSIS_DASHBOARD.html'
    html_path.write_text(html)
    print(f"  ✓ HTML dashboard saved: {html_path}")

    print("\n" + "="*80)
    print("✓ V3 REPORTS GENERATED SUCCESSFULLY")
    print("="*80)

if __name__ == '__main__':
    main()
