"""
Análisis Intensivo H1: Para cada día de la semana, a qué hora se forman HOTW/LOTW
Tabla con distribución horaria de extremos semanal por día
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

print("=" * 100)
print("ANÁLISIS H1: DISTRIBUCIÓN HORARIA DE EXTREMOS SEMANALES POR DÍA")
print("=" * 100)

# ============================================================================
# CARGAR Y PREPARAR DATOS
# ============================================================================

# Cargar datos M1
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
# PARA CADA SEMANA, ENCONTRAR HOTW Y LOTW
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
    hotw_dow = week_data.loc[hotw_idx, 'dow']

    lotw_hour = lotw_idx.hour
    lotw_day_name = week_data.loc[lotw_idx, 'day_name']
    lotw_dow = week_data.loc[lotw_idx, 'dow']

    extremes_data.append({
        'week_key': week_key,
        'hotw_hour': hotw_hour,
        'hotw_day_name': hotw_day_name,
        'hotw_dow': hotw_dow,
        'lotw_hour': lotw_hour,
        'lotw_day_name': lotw_day_name,
        'lotw_dow': lotw_dow,
    })

extremes_df = pd.DataFrame(extremes_data)

print(f"Semanas analizadas: {len(extremes_df):,}")

# ============================================================================
# CREAR TABLA DE DISTRIBUCIÓN HORARIA POR DÍA
# ============================================================================

days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
hours_list = list(range(24))  # 0-23 ET

# Para cada día, crear distribución de horas para HOTW y LOTW
day_hour_stats = {}

for day in days_order:
    # Casos donde este día tiene HOTW
    hotw_this_day = extremes_df[extremes_df['hotw_day_name'] == day]
    hotw_hour_dist = hotw_this_day['hotw_hour'].value_counts() if len(hotw_this_day) > 0 else pd.Series()

    # Casos donde este día tiene LOTW
    lotw_this_day = extremes_df[extremes_df['lotw_day_name'] == day]
    lotw_hour_dist = lotw_this_day['lotw_hour'].value_counts() if len(lotw_this_day) > 0 else pd.Series()

    # Total de semanas donde este día tiene extremo
    total_hotw = len(hotw_this_day)
    total_lotw = len(lotw_this_day)
    total_extremes = total_hotw + total_lotw

    # % de semanas con extremo este día
    day_prob = 100 * total_extremes / len(extremes_df)

    # Para cada hora, calcular %
    hourly_stats = []
    for hour in hours_list:
        hotw_count = hotw_hour_dist.get(hour, 0)
        lotw_count = lotw_hour_dist.get(hour, 0)

        # % dentro de las semanas donde este día tiene HOTW
        hotw_pct = (100 * hotw_count / total_hotw) if total_hotw > 0 else 0

        # % dentro de las semanas donde este día tiene LOTW
        lotw_pct = (100 * lotw_count / total_lotw) if total_lotw > 0 else 0

        hourly_stats.append({
            'hour': hour,
            'hotw_count': int(hotw_count),
            'hotw_pct': hotw_pct,
            'lotw_count': int(lotw_count),
            'lotw_pct': lotw_pct,
        })

    day_hour_stats[day] = {
        'day_prob': day_prob,
        'total_hotw': total_hotw,
        'total_lotw': total_lotw,
        'hourly': hourly_stats,
    }

# ============================================================================
# IMPRIMIR TABLA RESUMEN POR HORA
# ============================================================================

print(f"\n" + "=" * 120)
print("TABLA: DISTRIBUCIÓN HORARIA DE EXTREMOS POR DÍA DE LA SEMANA")
print(f"=" * 120)

# Header con nombres de días y sus probabilidades
header = "Hora ET |"
for day in days_order:
    prob = day_hour_stats[day]['day_prob']
    header += f" {day:>12} ({prob:5.1f}%) |"

print(f"\n{header}")
print(f"        | {'HOTW%':>6} {'LOTW%':>6} " * len(days_order) + "|")
print("=" * 120)

# Para cada hora
for hour in hours_list:
    row = f"{hour:02d}:00  |"

    for day in days_order:
        hourly = day_hour_stats[day]['hourly']
        hour_data = next((h for h in hourly if h['hour'] == hour), None)

        if hour_data:
            hotw = hour_data['hotw_pct']
            lotw = hour_data['lotw_pct']
            row += f" {hotw:5.1f}% {lotw:5.1f}% |"
        else:
            row += f"  0.0%  0.0% |"

    print(row)

print("=" * 120)

# ============================================================================
# ESTADÍSTICAS ADICIONALES
# ============================================================================

print(f"\n" + "=" * 120)
print("ESTADÍSTICAS ADICIONALES")
print(f"=" * 120)

for day in days_order:
    stats = day_hour_stats[day]
    hourly = stats['hourly']

    print(f"\n{day} ({stats['day_prob']:.1f}% de semanas):")
    print(f"  Total HOTW: {stats['total_hotw']} semanas")
    print(f"  Total LOTW: {stats['total_lotw']} semanas")

    # Top 3 horas para HOTW
    hotw_sorted = sorted(hourly, key=lambda x: x['hotw_pct'], reverse=True)
    print(f"\n  Top 3 horas para HOTW:")
    for i, h in enumerate(hotw_sorted[:3], 1):
        print(f"    {i}. {h['hour']:02d}:00 → {h['hotw_pct']:5.1f}% ({h['hotw_count']} casos)")

    # Top 3 horas para LOTW
    lotw_sorted = sorted(hourly, key=lambda x: x['lotw_pct'], reverse=True)
    print(f"\n  Top 3 horas para LOTW:")
    for i, h in enumerate(lotw_sorted[:3], 1):
        print(f"    {i}. {h['hour']:02d}:00 → {h['lotw_pct']:5.1f}% ({h['lotw_count']} casos)")

# ============================================================================
# GUARDAR DATOS
# ============================================================================

# Convertir a DataFrame para guardar
all_hours_data = []

for day in days_order:
    stats = day_hour_stats[day]
    for hour_data in stats['hourly']:
        all_hours_data.append({
            'day': day,
            'day_prob': stats['day_prob'],
            'hour': hour_data['hour'],
            'hotw_count': hour_data['hotw_count'],
            'hotw_pct': hour_data['hotw_pct'],
            'lotw_count': hour_data['lotw_count'],
            'lotw_pct': hour_data['lotw_pct'],
            'total_hotw': stats['total_hotw'],
            'total_lotw': stats['total_lotw'],
        })

output_df = pd.DataFrame(all_hours_data)
output_df.to_csv(RESULTS_PATH / 'v3_hourly_extremes_by_day.csv', index=False)

print(f"\n" + "=" * 120)
print("Guardado: v3_hourly_extremes_by_day.csv")
print("=" * 120)
