"""
PASO 4: Sesgos por Día de la Semana en Sesión NY
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

SUBPERIODS = [
    ('2000-2007', '2000-05-01', '2007-12-31'),
    ('2008-2013', '2008-01-01', '2013-12-31'),
    ('2014-2019', '2014-01-01', '2019-12-31'),
    ('2020-2025', '2020-01-01', '2025-12-31'),
]

DAY_NAMES = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday'}

# ============================================================================
# PASO 4: SESGOS POR DÍA DE LA SEMANA
# ============================================================================

def paso4_day_of_week_analysis():
    """Análisis de sesgos por día de la semana en NY."""
    print("\n" + "=" * 80)
    print("PASO 4: SESGOS POR DÍA DE LA SEMANA EN NY")
    print("=" * 80)

    # Cargar datos
    print("\n[4.0] Cargando datos...")
    daily_stats = pd.read_csv(RESULTS_PATH / 'daily_stats.csv', parse_dates=['trading_date'])
    block_daily = pd.read_csv(RESULTS_PATH / 'block_stats.csv', parse_dates=['trading_date'])

    # Extraer datos de NY (block_stats ya contiene daily_range_pips)
    ny_data = block_daily[block_daily['session'] == 'NY'].copy()

    # Día de la semana
    ny_data['day_of_week'] = pd.to_datetime(ny_data['trading_date']).dt.dayofweek
    ny_data['day_name'] = ny_data['day_of_week'].map(DAY_NAMES)

    # Rango en pips y retorno
    ny_data['ny_range_pips'] = (ny_data['block_high'] - ny_data['block_low']) * 10000
    ny_data['ny_return_pips'] = (ny_data['block_close'] - ny_data['block_open']) * 10000

    # Día tendencial: cierre en tercio superior/inferior del rango diario
    # Usar daily_return_pips que ya está en pips
    daily_stats_dict = daily_stats.set_index('trading_date')['close'].to_dict()
    ny_data['daily_close'] = ny_data['trading_date'].map(
        daily_stats.set_index('trading_date')['close']
    )
    ny_data['daily_open'] = ny_data['trading_date'].map(
        daily_stats.set_index('trading_date')['open']
    )

    daily_range_pips = ny_data['daily_range_pips']
    daily_return_pips = (ny_data['daily_close'] - ny_data['daily_open']) * 10000

    third = daily_range_pips / 3
    ny_data['is_trending'] = (daily_return_pips.abs() > third)

    # Percentiles de rango Asia/London
    asia_data = block_daily[block_daily['session'] == 'Asia'].copy()
    london_data = block_daily[block_daily['session'] == 'London'].copy()

    asia_p75 = asia_data['block_range_pips'].quantile(0.75)
    london_p75 = london_data['block_range_pips'].quantile(0.75)

    # Marcar si Asia/London fueron alto
    ny_data['asia_high'] = ny_data['trading_date'].isin(
        asia_data[asia_data['block_range_pips'] > asia_p75]['trading_date']
    )
    ny_data['london_high'] = ny_data['trading_date'].isin(
        london_data[london_data['block_range_pips'] > london_p75]['trading_date']
    )

    print("  ✓ Datos cargados y procesados")

    # ========================================================================
    # 4.1 - TABLA 1: MÉTRICAS BASE POR DÍA DE LA SEMANA
    # ========================================================================
    print("\n[4.1] ESTADÍSTICAS BASE POR DÍA DE LA SEMANA (TODO EL PERÍODO):")
    print("-" * 80)

    table1 = ny_data.groupby('day_name').agg({
        'ny_range_pips': ['count', 'mean', 'median', 'std'],
        'ny_return_pips': ['mean', 'median'],
        'is_trending': 'mean'  # % de días tendenciales
    }).round(2)

    table1.columns = ['Count', 'Mean Range', 'Median Range', 'Std Range',
                      'Mean Return', 'Median Return', '% Trending']

    # Reordenar por día de semana
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    table1 = table1.reindex([d for d in day_order if d in table1.index])
    table1['% Trending'] = table1['% Trending'] * 100

    print("\n" + table1.to_string())

    # ========================================================================
    # 4.2 - TABLA 2: CONDICIONADO A ASIA/LONDON ALTO vs BAJO
    # ========================================================================
    print("\n\n[4.2] NY RANGO MEDIO POR DÍA Y CONDICIÓN ASIA/LONDON:")
    print("-" * 80)

    conditions = [
        ('Both Low', {'asia_high': False, 'london_high': False}),
        ('Asia High Only', {'asia_high': True, 'london_high': False}),
        ('London High Only', {'asia_high': False, 'london_high': True}),
        ('Both High', {'asia_high': True, 'london_high': True}),
    ]

    for cond_name, cond_dict in conditions:
        print(f"\n  {cond_name}:")
        mask = pd.Series([True] * len(ny_data), index=ny_data.index)
        for key, val in cond_dict.items():
            mask = mask & (ny_data[key] == val)

        subset = ny_data[mask]
        if len(subset) > 0:
            table2 = subset.groupby('day_name').agg({
                'ny_range_pips': ['count', 'mean'],
                'is_trending': 'mean'
            }).round(2)
            table2.columns = ['Count', 'Avg Range', '% Trending']
            table2['% Trending'] = table2['% Trending'] * 100
            table2 = table2.reindex([d for d in day_order if d in table2.index])
            print(table2.to_string())

    # ========================================================================
    # 4.3 - DIRECCIÓN SEMANAL ACUMULADA
    # ========================================================================
    print("\n\n[4.3] NY SEGÚN DIRECCIÓN SEMANAL ACUMULADA:")
    print("-" * 80)

    # Calcular return acumulado semanal
    ny_data['week'] = pd.to_datetime(ny_data['trading_date']).dt.isocalendar().week
    ny_data['year'] = pd.to_datetime(ny_data['trading_date']).dt.year
    ny_data['week_key'] = ny_data['year'].astype(str) + '-W' + ny_data['week'].astype(str).str.zfill(2)

    # Return acumulado hasta ese día dentro de la semana
    weekly_returns = daily_stats.copy()
    weekly_returns['week'] = pd.to_datetime(weekly_returns['trading_date']).dt.isocalendar().week
    weekly_returns['year'] = pd.to_datetime(weekly_returns['trading_date']).dt.year
    weekly_returns['day_in_week'] = pd.to_datetime(weekly_returns['trading_date']).dt.dayofweek

    # Calcular return acumulado por semana hasta cada día
    ny_data['weekly_cumulative_return'] = 0.0

    # Merge con daily_return_pips
    daily_return_map = daily_stats.set_index('trading_date')['daily_return_pips'].to_dict()

    # Llenar daily_return para NY
    ny_data['daily_return_pips'] = ny_data['trading_date'].map(daily_return_map)

    for idx, row in ny_data.iterrows():
        week_data = weekly_returns[
            (weekly_returns['year'] == row['year']) &
            (weekly_returns['week'] == row['week']) &
            (weekly_returns['day_in_week'] <= row['day_of_week'])
        ]
        if len(week_data) > 0:
            ny_data.at[idx, 'weekly_cumulative_return'] = week_data['daily_return_pips'].sum()

    ny_data['weekly_direction'] = np.where(
        ny_data['weekly_cumulative_return'] > 0, 'UP',
        np.where(ny_data['weekly_cumulative_return'] < 0, 'DOWN', 'FLAT')
    )

    print("\n  NY RANGO PROMEDIO POR DIRECCIÓN SEMANAL:")
    print()

    for direction in ['UP', 'DOWN', 'FLAT']:
        print(f"  Semana {direction}:")
        subset = ny_data[ny_data['weekly_direction'] == direction]
        if len(subset) > 0:
            table3 = subset.groupby('day_name').agg({
                'ny_range_pips': ['count', 'mean'],
                'is_trending': 'mean'
            }).round(2)
            table3.columns = ['Count', 'Avg Range', '% Trending']
            table3['% Trending'] = table3['% Trending'] * 100
            table3 = table3.reindex([d for d in day_order if d in table3.index])
            print(table3.to_string())
            print()

    # ========================================================================
    # 4.4 - DESGLOSE POR SUBPERIODOS
    # ========================================================================
    print("\n[4.4] DESGLOSE POR SUBPERIODOS:")
    print("-" * 80)

    for period_name, start_date, end_date in SUBPERIODS:
        period_data = ny_data[
            (ny_data['trading_date'] >= start_date) &
            (ny_data['trading_date'] <= end_date)
        ]

        if len(period_data) > 0:
            print(f"\n  {period_name}:")
            period_table = period_data.groupby('day_name').agg({
                'ny_range_pips': 'mean',
                'is_trending': 'mean'
            }).round(2)
            period_table.columns = ['Avg Range', '% Trending']
            period_table['% Trending'] = period_table['% Trending'] * 100
            period_table = period_table.reindex([d for d in day_order if d in period_table.index])
            print(period_table.to_string())

    # Guardar resultados principales
    table1.to_csv(RESULTS_PATH / 'paso4_dow_summary.csv')
    ny_data.to_csv(RESULTS_PATH / 'paso4_full_data.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ PASO 4 COMPLETADO")
    print("=" * 80)

    return ny_data, table1


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    ny_data, table1 = paso4_day_of_week_analysis()
    print("\n✓ Resultados guardados en results/")
