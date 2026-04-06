"""
Análisis H1: Distribución horaria de TODOS los extremos (HOTW y LOTW juntos)
Para cada día de la semana, a qué hora se forma CUALQUIER extremo semanal
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

print("=" * 120)
print("ANÁLISIS H1: DISTRIBUCIÓN HORARIA DE EXTREMOS (HOTW + LOTW COMBINADOS)")
print("=" * 120)

# ============================================================================
# CARGAR Y PREPARAR DATOS
# ============================================================================

dfs = []
for year in range(2000, 2026):
    fp = REPO_PATH / f'DAT_ASCII_EURUSD_M1_{year}.csv'
    if fp.exists():
        d = pd.read_csv(fp, sep=';', header=None,
                        names=['dt', 'open', 'high', 'low', 'close', 'volume'],
                        dtype={'open': float, 'high': float, 'low': float, 'close': float})
        d['datetime'] = pd.to_datetime(d['dt'], format='%Y%m%d %H%M%S')
        d.drop('dt', axis=1, inplace=True)
        dfs.append(d)

df = pd.concat(dfs, ignore_index=True).sort_values('datetime').reset_index(drop=True)
df.set_index('datetime', inplace=True)

# Limpiar
df = df[(df['high'] > 0.80) & (df['high'] < 1.70) &
        (df['low'] > 0.80) & (df['low'] < 1.70)]

print(f"\nDatos cargados: {len(df):,} velas M1")

# Asignar trading days
df['hour'] = df.index.hour
dates = pd.Series(df.index.date, index=df.index).astype('datetime64[ns]')
mask_after_17 = df['hour'] >= 17
dates[mask_after_17] = dates[mask_after_17] + pd.Timedelta(days=1)
df['trading_date'] = dates
df['dow'] = df['trading_date'].dt.dayofweek
df['day_name'] = df['trading_date'].dt.day_name()
df['week_key'] = df['trading_date'].dt.strftime('%Y-W%V')

# Filtrar días válidos
valid_days = df.groupby('trading_date').size()
valid_days = valid_days[valid_days >= 50].index
df = df[df['trading_date'].isin(valid_days)]

print(f"Trading days válidos: {len(valid_days):,}")

# ============================================================================
# PARA CADA SEMANA, ENCONTRAR HOTW Y LOTW CON HORA
# ============================================================================

weeks = df.groupby('week_key')

extremes_data = []

for week_key, week_data in weeks:
    if len(week_data) < 100:
        continue

    # Encontrar HOTW y LOTW
    hotw_idx = week_data['high'].idxmax()
    lotw_idx = week_data['low'].idxmin()

    hotw_hour = hotw_idx.hour
    hotw_day_name = week_data.loc[hotw_idx, 'day_name']

    lotw_hour = lotw_idx.hour
    lotw_day_name = week_data.loc[lotw_idx, 'day_name']

    # Agregar ambos extremos
    extremes_data.append({
        'week_key': week_key,
        'hour': hotw_hour,
        'day_name': hotw_day_name,
        'type': 'HOTW',
    })

    extremes_data.append({
        'week_key': week_key,
        'hour': lotw_hour,
        'day_name': lotw_day_name,
        'type': 'LOTW',
    })

extremes_df = pd.DataFrame(extremes_data)

print(f"Semanas analizadas: {len(extremes_df) // 2:,}")
print(f"Total de extremos (HOTW + LOTW): {len(extremes_df):,}")

# ============================================================================
# CREAR TABLA DE DISTRIBUCIÓN HORARIA COMBINADA POR DÍA
# ============================================================================

days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
hours_list = list(range(24))

day_stats = {}

for day in days_order:
    # Todos los extremos que ocurren este día (sin importar si son HIGH o LOW)
    day_extremes = extremes_df[extremes_df['day_name'] == day]
    total_extremes_this_day = len(day_extremes)

    # % de semanas que tienen extremo este día
    day_prob = 100 * total_extremes_this_day / (len(extremes_df) // 2)

    # Para cada hora, contar cuántos extremos se forman
    hourly_stats = []
    for hour in hours_list:
        hour_count = len(day_extremes[day_extremes['hour'] == hour])
        hour_pct = (100 * hour_count / total_extremes_this_day) if total_extremes_this_day > 0 else 0

        hourly_stats.append({
            'hour': hour,
            'count': int(hour_count),
            'pct': hour_pct,
        })

    day_stats[day] = {
        'day_prob': day_prob,
        'total_extremes': total_extremes_this_day,
        'hourly': hourly_stats,
    }

# ============================================================================
# IMPRIMIR TABLA PRINCIPAL
# ============================================================================

print(f"\n" + "=" * 150)
print("TABLA: DISTRIBUCIÓN HORARIA DE EXTREMOS SEMANALES (HOTW + LOTW COMBINADOS)")
print(f"=" * 150)
print("Cada celda muestra: % de veces que se forma CUALQUIER extremo a esa hora en ese día")
print(f"En cabecera: Día (% de semanas con extremo en ese día)\n")

# Header
header = f"{'Hora ET':>8} |"
for day in days_order:
    prob = day_stats[day]['day_prob']
    header += f" {day:>12} ({prob:5.1f}%) |"

print(header)
print("=" * 150)

# Para cada hora
for hour in hours_list:
    row = f"{hour:02d}:00 ET |"

    for day in days_order:
        hourly = day_stats[day]['hourly']
        hour_data = next((h for h in hourly if h['hour'] == hour), None)

        if hour_data:
            pct = hour_data['pct']
            count = hour_data['count']
            row += f" {pct:5.1f}% ({count:2d}x) |"
        else:
            row += f"  0.0% ( 0x) |"

    print(row)

print("=" * 150)

# ============================================================================
# ESTADÍSTICAS POR DÍA
# ============================================================================

print(f"\n" + "=" * 120)
print("ESTADÍSTICAS POR DÍA")
print(f"=" * 120)

for day in days_order:
    stats = day_stats[day]
    hourly = stats['hourly']

    print(f"\n{day} ({stats['day_prob']:.1f}% de semanas):")
    print(f"  Total de extremos: {stats['total_extremes']} (cualquier hora)")

    # Top 5 horas
    sorted_hours = sorted(hourly, key=lambda x: x['pct'], reverse=True)

    print(f"\n  Top 5 horas con extremos:")
    for i, h in enumerate(sorted_hours[:5], 1):
        bar = "█" * int(h['pct'] / 2)
        print(f"    {i}. {h['hour']:02d}:00 → {h['pct']:5.1f}% ({h['count']:2d} casos) {bar}")

# ============================================================================
# ANÁLISIS COMPARATIVO
# ============================================================================

print(f"\n" + "=" * 120)
print("ANÁLISIS COMPARATIVO: HORARIOS CRÍTICOS")
print(f"=" * 120)

# Agrupar horas por sesión
sessions = {
    '17:00-20:59 (Apertura NY)': list(range(17, 21)),
    '02:00-04:59 (Apertura Londres)': [2, 3, 4],
    '08:00-11:59 (Session NY)': list(range(8, 12)),
    '16:00-16:59 (Cierre Viernes)': [16],
}

print(f"\n{'Sesión':>30} |", end='')
for day in days_order:
    print(f" {day:>15} |", end='')
print()

print("=" * 120)

for session_name, session_hours in sessions.items():
    row = f"{session_name:>30} |"

    for day in days_order:
        hourly = day_stats[day]['hourly']
        total_in_session = sum(h['pct'] for h in hourly if h['hour'] in session_hours)
        count_in_session = sum(h['count'] for h in hourly if h['hour'] in session_hours)

        row += f" {total_in_session:5.1f}% ({count_in_session:2d}x) |"

    print(row)

# ============================================================================
# GUARDAR DATOS
# ============================================================================

all_hours_data = []

for day in days_order:
    stats = day_stats[day]
    for hour_data in stats['hourly']:
        all_hours_data.append({
            'day': day,
            'day_probability': stats['day_prob'],
            'hour': hour_data['hour'],
            'count': hour_data['count'],
            'percentage': hour_data['pct'],
            'total_extremes': stats['total_extremes'],
        })

output_df = pd.DataFrame(all_hours_data)
output_df.to_csv(RESULTS_PATH / 'v3_hourly_extremes_combined.csv', index=False)

print(f"\n" + "=" * 120)
print("Guardado: v3_hourly_extremes_combined.csv")
print("=" * 120)
