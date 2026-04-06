"""
Análisis: Para cada día de la semana, qué % de semanas contiene HOTW/LOTW
Combinación de ambos en porcentaje sobre 100
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

print("=" * 80)
print("ANÁLISIS: PROBABILIDAD DE EXTREMOS POR DÍA DE LA SEMANA")
print("=" * 80)

# Cargar datos
weekly_extremes = pd.read_csv(RESULTS_PATH / 'v3_weekly_extremes.csv')

print(f"\nTotal de semanas analizadas: {len(weekly_extremes)}")

# ============================================================================
# PASO 1: Contar cuántas veces HOTW/LOTW aparecen en cada día
# ============================================================================

print(f"\n[PASO 1] DISTRIBUCIÓN DE EXTREMOS POR DÍA")
print(f"=" * 80)

days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# Contar HOTW por día
hotw_by_day = weekly_extremes['high_day_name'].value_counts()
lotw_by_day = weekly_extremes['low_day_name'].value_counts()

# Crear tabla
result = []

for day in days_order:
    hotw_count = hotw_by_day.get(day, 0)
    lotw_count = lotw_by_day.get(day, 0)
    combined_count = hotw_count + lotw_count

    hotw_pct = 100 * hotw_count / len(weekly_extremes)
    lotw_pct = 100 * lotw_count / len(weekly_extremes)
    combined_pct = hotw_pct + lotw_pct

    result.append({
        'day': day,
        'hotw_count': hotw_count,
        'hotw_pct': hotw_pct,
        'lotw_count': lotw_count,
        'lotw_pct': lotw_pct,
        'combined_count': combined_count,
        'combined_pct': combined_pct,
    })

    print(f"\n{day:>12}")
    print(f"  HOTW: {hotw_count:4d} semanas ({hotw_pct:5.1f}%)")
    print(f"  LOTW: {lotw_count:4d} semanas ({lotw_pct:5.1f}%)")
    print(f"  ─────────────────────────")
    print(f"  TOTAL: {combined_count:4d} semanas ({combined_pct:5.1f}%)")

# ============================================================================
# PASO 2: TABLA RESUMEN
# ============================================================================

print(f"\n" + "=" * 80)
print("TABLA RESUMEN: COMBINACIÓN HOTW + LOTW")
print("=" * 80)

result_df = pd.DataFrame(result)

print(f"\n{'Día':>12} | {'HOTW':>6} | {'LOTW':>6} | {'TOTAL':>6} | {'% Total':>8} |")
print(f"{'-'*12}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*8}-+")

for idx, row in result_df.iterrows():
    day = row['day']
    hotw = row['hotw_count']
    lotw = row['lotw_count']
    total = row['combined_count']
    pct = row['combined_pct']

    marker = "★★★" if pct > 25 else ("★★" if pct > 20 else "★")
    print(f"{day:>12} | {hotw:>6.0f} | {lotw:>6.0f} | {total:>6.0f} | {pct:>7.1f}% | {marker}")

# ============================================================================
# PASO 3: PROBABILIDAD SOBRE 100%
# ============================================================================

print(f"\n" + "=" * 80)
print("PROBABILIDAD SOBRE 100% (TOTAL DE SEMANAS)")
print("=" * 80)

total_combinations = result_df['combined_count'].sum()
print(f"\nTotal de extremos (HOTW + LOTW): {total_combinations}")
print(f"Número de semanas: {len(weekly_extremes)}")
print(f"Promedio de extremos por semana: {total_combinations / len(weekly_extremes):.2f}")

print(f"\n{'Día':>12} | {'Probabilidad (%)':>20} |")
print(f"{'-'*12}-+-{'-'*20}-+")

for idx, row in result_df.iterrows():
    day = row['day']
    pct = row['combined_pct']

    # Barra visual
    bar_length = int(pct / 2)
    bar = "█" * bar_length

    print(f"{day:>12} | {pct:>6.1f}% {bar:<12} |")

# ============================================================================
# PASO 4: INSIGHTS OPERACIONALES
# ============================================================================

print(f"\n" + "=" * 80)
print("INSIGHTS OPERACIONALES")
print("=" * 80)

sorted_by_prob = result_df.sort_values('combined_pct', ascending=False)

print(f"\n[RANKING] Días más probables con extremo semanal:")
for i, (idx, row) in enumerate(sorted_by_prob.iterrows(), 1):
    day = row['day']
    pct = row['combined_pct']
    hotw = row['hotw_pct']
    lotw = row['lotw_pct']

    print(f"  {i}. {day:>12}: {pct:5.1f}% (HOTW: {hotw:5.1f}% | LOTW: {lotw:5.1f}%)")

# ============================================================================
# PASO 5: ANÁLISIS DE CONCENTRACIÓN
# ============================================================================

print(f"\n[CONCENTRACIÓN] Distribución de extremos:")

top_2_days = sorted_by_prob.head(2)
top_2_prob = top_2_days['combined_pct'].sum()

top_3_days = sorted_by_prob.head(3)
top_3_prob = top_3_days['combined_pct'].sum()

print(f"  Top 2 días: {top_2_prob:.1f}% de extremos (concentración)")
print(f"  Top 3 días: {top_3_prob:.1f}% de extremos (concentración)")

min_prob = result_df['combined_pct'].min()
max_prob = result_df['combined_pct'].max()

print(f"\n  Rango: {min_prob:.1f}% (mínimo) a {max_prob:.1f}% (máximo)")
print(f"  Diferencia: {max_prob - min_prob:.1f} puntos porcentuales")

# ============================================================================
# PASO 6: COMPARACIÓN HOTW vs LOTW
# ============================================================================

print(f"\n" + "=" * 80)
print("COMPARACIÓN: HOTW vs LOTW POR DÍA")
print("=" * 80)

print(f"\n{'Día':>12} | {'HOTW %':>8} | {'LOTW %':>8} | {'Diferencia':>12} |")
print(f"{'-'*12}-+-{'-'*8}-+-{'-'*8}-+-{'-'*12}-+")

for idx, row in result_df.iterrows():
    day = row['day']
    hotw_pct = row['hotw_pct']
    lotw_pct = row['lotw_pct']
    diff = hotw_pct - lotw_pct

    if diff > 0:
        marker = f"↑ HOTW +{diff:.1f}%"
    elif diff < 0:
        marker = f"↓ LOTW +{abs(diff):.1f}%"
    else:
        marker = "= IGUAL"

    print(f"{day:>12} | {hotw_pct:>7.1f}% | {lotw_pct:>7.1f}% | {marker:>12} |")

# ============================================================================
# GUARDAR RESULTADOS
# ============================================================================

result_df.to_csv(RESULTS_PATH / 'v3_daily_extremes_probability.csv', index=False)

print(f"\n" + "=" * 80)
print("Guardado: v3_daily_extremes_probability.csv")
print("=" * 80)

print(f"\n[CONCLUSIÓN]")
print(f"  - {sorted_by_prob.iloc[0]['day']}: {sorted_by_prob.iloc[0]['combined_pct']:.1f}% (DÍA MÁS PROBABLE)")
print(f"  - {sorted_by_prob.iloc[-1]['day']}: {sorted_by_prob.iloc[-1]['combined_pct']:.1f}% (DÍA MENOS PROBABLE)")
print(f"  - La probabilidad está CONCENTRADA en {top_2_prob:.1f}% en los 2 primeros días")
