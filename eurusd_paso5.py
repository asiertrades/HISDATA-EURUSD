"""
PASO 5: Integración con H4 - Análisis de Velas de 4 Horas
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'

SESSIONS = {
    'Asia': (20, 0),
    'Post-Asia': (0, 2),
    'London': (2, 5),
    'Post-London': (5, 8),
    'NY': (8, 11),
    'Post-NY': (11, 20),
}

SUBPERIODS = [
    ('2000-2007', '2000-05-01', '2007-12-31'),
    ('2008-2013', '2008-01-01', '2013-12-31'),
    ('2014-2019', '2014-01-01', '2019-12-31'),
    ('2020-2025', '2020-01-01', '2025-12-31'),
]

# ============================================================================
# PASO 5: INTEGRACIÓN CON H4
# ============================================================================

def paso5_h4_analysis():
    """Análisis de H4 alineadas a bloques horarios."""
    print("\n" + "=" * 80)
    print("PASO 5: INTEGRACIÓN CON H4")
    print("=" * 80)

    # Cargar datos M1
    print("\n[5.0] Cargando y procesando datos M1...")
    dfs = []
    for year in range(2000, 2026):
        filepath = REPO_PATH / f'DAT_ASCII_EURUSD_M1_{year}.csv'
        if filepath.exists():
            df = pd.read_csv(
                filepath,
                sep=';',
                header=None,
                names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'],
                dtype={'open': float, 'high': float, 'low': float, 'close': float}
            )
            df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
            df = df.drop('datetime_str', axis=1)
            dfs.append(df)

    df_m1 = pd.concat(dfs, ignore_index=True)
    df_m1 = df_m1.sort_values('datetime').reset_index(drop=True)
    df_m1.set_index('datetime', inplace=True)

    # Agregar datos de bloque horario
    df_m1['hour'] = df_m1.index.hour

    def get_session(hour):
        for session_name, (start, end) in SESSIONS.items():
            if start < end:
                if start <= hour < end:
                    return session_name
            else:
                if hour >= start or hour < end:
                    return session_name
        return None

    df_m1['session'] = df_m1['hour'].apply(get_session)

    # Crear H4 resampled
    print("\n[5.1] Creando velas H4...")
    h4_data = df_m1[['open', 'high', 'low', 'close']].resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna().reset_index()

    # Asignar bloque horario de INICIO de cada H4
    h4_data['hour_start'] = h4_data['datetime'].dt.hour
    h4_data['session_start'] = h4_data['hour_start'].apply(get_session)

    # Calcular rango y cuerpo en pips
    h4_data['range_pips'] = (h4_data['high'] - h4_data['low']) * 10000
    h4_data['body_pips'] = (h4_data['close'] - h4_data['open']).abs() * 10000
    h4_data['direction'] = np.where(h4_data['close'] > h4_data['open'], 'UP', 'DOWN')

    # Crear trading_date para H4
    h4_data['date'] = h4_data['datetime'].dt.date
    h4_data['hour'] = h4_data['datetime'].dt.hour
    h4_data['trading_date'] = pd.to_datetime(h4_data['date'])
    h4_data.loc[h4_data['hour'] < 17, 'trading_date'] = (
        h4_data.loc[h4_data['hour'] < 17, 'trading_date'] - pd.Timedelta(days=1)
    )

    print(f"  ✓ {len(h4_data):,} velas H4 creadas")

    # ========================================================================
    # 5.1 - VELAS H4 EN NY
    # ========================================================================
    print("\n[5.2] ESTADÍSTICAS H4 QUE INICIAN EN NY:")
    print("-" * 80)

    h4_ny = h4_data[h4_data['session_start'] == 'NY'].copy()

    if len(h4_ny) > 0:
        print(f"\n  Velas H4 en NY: {len(h4_ny):,}")
        print(f"\n  Rango H4 (pips):")
        print(f"    Media: {h4_ny['range_pips'].mean():.2f}")
        print(f"    Mediana: {h4_ny['range_pips'].median():.2f}")
        print(f"    P25: {h4_ny['range_pips'].quantile(0.25):.2f}")
        print(f"    P75: {h4_ny['range_pips'].quantile(0.75):.2f}")

        print(f"\n  Cuerpo H4 (pips):")
        print(f"    Media: {h4_ny['body_pips'].mean():.2f}")
        print(f"    Mediana: {h4_ny['body_pips'].median():.2f}")

        print(f"\n  Dirección:")
        dir_counts = h4_ny['direction'].value_counts()
        for direction, count in dir_counts.items():
            pct = 100 * count / len(h4_ny)
            print(f"    {direction}: {count} ({pct:.1f}%)")

    # ========================================================================
    # 5.2 - CONTINUACIÓN AL SIGUIENTE H4
    # ========================================================================
    print("\n[5.3] PROBABILIDAD DE CONTINUACIÓN AL SIGUIENTE H4:")
    print("-" * 80)

    # Crear columna de siguiente H4
    h4_data['next_direction'] = h4_data['direction'].shift(-1)
    h4_data['next_range'] = h4_data['range_pips'].shift(-1)
    h4_data['price_change_next'] = (
        (h4_data['close'].shift(-1) - h4_data['close']).abs() * 10000
    )

    h4_ny_with_next = h4_ny[h4_ny['datetime'] < h4_ny['datetime'].max()].copy()
    h4_ny_with_next = h4_ny_with_next.merge(
        h4_data[['datetime', 'next_direction', 'price_change_next', 'next_range']],
        on='datetime',
        how='left'
    )

    if len(h4_ny_with_next) > 0:
        # Continuación en dirección
        continuations = (h4_ny_with_next['direction'] == h4_ny_with_next['next_direction']).sum()
        cont_pct = 100 * continuations / len(h4_ny_with_next)
        print(f"\n  Continuación en DIRECCIÓN al siguiente H4:")
        print(f"    {continuations} / {len(h4_ny_with_next)} ({cont_pct:.1f}%)")

        # Distribución de extensión al siguiente H4
        print(f"\n  Extensión de precio al siguiente H4 (cuando continúa dirección):")
        continuations_subset = h4_ny_with_next[
            h4_ny_with_next['direction'] == h4_ny_with_next['next_direction']
        ]
        if len(continuations_subset) > 0:
            ext_stats = continuations_subset['price_change_next'].describe()
            print(f"    Media: {ext_stats['mean']:.2f} pips")
            print(f"    Mediana: {ext_stats['50%']:.2f} pips")
            print(f"    P25: {ext_stats['25%']:.2f}, P75: {ext_stats['75%']:.2f}")

    # ========================================================================
    # 5.3 - CONDICIONAL: ATR DIARIO COMPLETADO
    # ========================================================================
    print("\n[5.4] RANGO H4 SEGÚN % ATR DIARIO COMPLETADO ANTES DE NY:")
    print("-" * 80)

    # Cargar datos diarios
    daily_stats = pd.read_csv(RESULTS_PATH / 'daily_stats.csv', parse_dates=['trading_date'])

    # Merge con daily ATR
    daily_stats['daily_atr'] = daily_stats['daily_range_pips']
    h4_data = h4_data.merge(
        daily_stats[['trading_date', 'daily_atr']],
        on='trading_date',
        how='left'
    )

    # Para cada H4 en NY, calcular qué % del ATR ya se completó hasta el inicio de NY
    # Calcular rango hasta inicio de NY (20:00-08:00) = Asia + Post-Asia + London + Post-London
    h4_ny_with_atr = h4_ny.merge(
        daily_stats[['trading_date', 'daily_range_pips']],
        on='trading_date',
        how='left'
    )

    block_stats = pd.read_csv(RESULTS_PATH / 'block_stats.csv', parse_dates=['trading_date'])
    range_before_ny = block_stats[
        block_stats['session'].isin(['Asia', 'Post-Asia', 'London', 'Post-London'])
    ].groupby('trading_date')['block_range_pips'].sum().reset_index()
    range_before_ny.columns = ['trading_date', 'range_before_ny']

    h4_ny_with_atr = h4_ny_with_atr.merge(range_before_ny, on='trading_date', how='left')
    h4_ny_with_atr['pct_atr_completed'] = (
        (h4_ny_with_atr['range_before_ny'] / h4_ny_with_atr['daily_range_pips'] * 100)
        .fillna(0).clip(0, 100)
    )

    # Clasificar por % ATR completado
    print(f"\n  Rango H4 en NY según % ATR diario ya completado antes de NY:")
    print()

    atr_thresholds = [0, 25, 50, 75, 100]
    for i in range(len(atr_thresholds) - 1):
        lower = atr_thresholds[i]
        upper = atr_thresholds[i + 1]
        subset = h4_ny_with_atr[
            (h4_ny_with_atr['pct_atr_completed'] >= lower) &
            (h4_ny_with_atr['pct_atr_completed'] < upper)
        ]
        if len(subset) > 0:
            mean_range = subset['range_pips'].mean()
            print(f"  ATR {lower:2d}%-{upper:2d}%: {len(subset):4d} casos, H4 rango promedio: {mean_range:7.2f} pips")

    # ========================================================================
    # 5.4 - CONDICIONAL: ZONA DE MÁXIMOS/MÍNIMOS SEMANALES
    # ========================================================================
    print("\n[5.5] RANGO H4 EN NY SEGÚN ZONA DE EXTREMOS SEMANALES:")
    print("-" * 80)

    # Calcular máximos/mínimos semanales
    h4_data['week'] = h4_data['datetime'].dt.isocalendar().week
    h4_data['year'] = h4_data['datetime'].dt.year
    h4_data['week_key'] = h4_data['year'].astype(str) + '-W' + h4_data['week'].astype(str).str.zfill(2)

    weekly_highs = h4_data.groupby('week_key')['high'].max()
    weekly_lows = h4_data.groupby('week_key')['low'].min()

    h4_ny_with_atr['week_key'] = (
        h4_ny_with_atr['datetime'].dt.year.astype(str) + '-W' +
        h4_ny_with_atr['datetime'].dt.isocalendar().week.astype(str).str.zfill(2)
    )

    h4_ny_with_atr['week_high'] = h4_ny_with_atr['week_key'].map(weekly_highs)
    h4_ny_with_atr['week_low'] = h4_ny_with_atr['week_key'].map(weekly_lows)

    # Clasificar si la vela H4 en NY toca zona de máximos o mínimos semanales
    zone_threshold = 50  # pips
    h4_ny_with_atr['near_weekly_high'] = (
        (h4_ny_with_atr['high'] >= h4_ny_with_atr['week_high'] - zone_threshold / 10000)
    )
    h4_ny_with_atr['near_weekly_low'] = (
        (h4_ny_with_atr['low'] <= h4_ny_with_atr['week_low'] + zone_threshold / 10000)
    )

    print(f"\n  Rango H4 en NY según zona de extremos semanales:")
    print()

    conditions_weekly = [
        ('Lejos de extremos', {'near_weekly_high': False, 'near_weekly_low': False}),
        ('Cerca de máximo semanal', {'near_weekly_high': True, 'near_weekly_low': False}),
        ('Cerca de mínimo semanal', {'near_weekly_high': False, 'near_weekly_low': True}),
        ('En zona de ambos extremos', {'near_weekly_high': True, 'near_weekly_low': True}),
    ]

    for cond_name, cond_dict in conditions_weekly:
        mask = pd.Series([True] * len(h4_ny_with_atr), index=h4_ny_with_atr.index)
        for key, val in cond_dict.items():
            mask = mask & (h4_ny_with_atr[key] == val)

        subset = h4_ny_with_atr[mask]
        if len(subset) > 0:
            mean_range = subset['range_pips'].mean()
            cont_pct = 0
            # Calcular continuación si hay siguientes H4
            subset_with_next = subset.merge(
                h4_data[['datetime', 'next_direction']],
                on='datetime',
                how='left'
            )
            if len(subset_with_next) > 0 and subset_with_next['next_direction'].notna().any():
                continuations = (
                    subset_with_next['direction'] == subset_with_next['next_direction']
                ).sum()
                cont_pct = 100 * continuations / len(subset_with_next)

            print(f"  {cond_name}:")
            print(f"    Casos: {len(subset)}")
            print(f"    H4 rango promedio: {mean_range:.2f} pips")
            print(f"    Continuación siguiente H4: {cont_pct:.1f}%")
            print()

    # Guardar resultados
    h4_ny_with_atr.to_csv(RESULTS_PATH / 'paso5_h4_ny_analysis.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ PASO 5 COMPLETADO")
    print("=" * 80)

    return h4_ny_with_atr


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    h4_results = paso5_h4_analysis()
    print("\n✓ Resultados guardados en results/paso5_h4_ny_analysis.csv")
