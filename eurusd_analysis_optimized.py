"""
Análisis Cuantitativo EUR/USD M1 (2000-2025) - VERSIÓN OPTIMIZADA
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'
RESULTS_PATH.mkdir(exist_ok=True)

# Bloques horarios (ET)
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
# PASO 1: CARGA Y PREPARACIÓN
# ============================================================================

def load_all_csvs():
    """Carga todos los CSV y prepara datos."""
    print("=" * 80)
    print("PASO 1: CARGA Y PREPARACIÓN")
    print("=" * 80)
    print("\n[1.1] Cargando archivos CSV...")

    dfs = []
    for year in range(2000, 2026):
        filepath = REPO_PATH / f'DAT_ASCII_EURUSD_M1_{year}.csv'
        if filepath.exists():
            df = pd.read_csv(
                filepath,
                sep=';',
                header=None,
                names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'],
                dtype={'open': float, 'high': float, 'low': float, 'close': float, 'volume': float}
            )
            df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
            df = df.drop('datetime_str', axis=1)
            dfs.append(df)
            print(f"  ✓ {year}: {len(df):,} filas")

    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values('datetime').reset_index(drop=True)
    df = df.set_index('datetime')

    print(f"\n  Total: {len(df):,} filas")
    print(f"  Período: {df.index.min()} a {df.index.max()}")

    return df

def prepare_data(df):
    """Prepara columnas auxiliares y asigna bloques horarios."""
    print("\n[1.2] Preparando columnas auxiliares...")

    df = df.copy()
    df['hour'] = df.index.hour
    df['date'] = df.index.date

    # Trading date (ciclo 17:00)
    df['trading_date'] = df['date'].astype('datetime64[ns]')
    df.loc[df['hour'] < 17, 'trading_date'] = (
        df.loc[df['hour'] < 17, 'trading_date'] - pd.Timedelta(days=1)
    )

    df['day_of_week'] = pd.to_datetime(df['trading_date']).dt.dayofweek
    df['day_name'] = pd.to_datetime(df['trading_date']).dt.day_name()

    # Session assignment
    def get_session(hour):
        for session_name, (start, end) in SESSIONS.items():
            if start < end:
                if start <= hour < end:
                    return session_name
            else:
                if hour >= start or hour < end:
                    return session_name
        return None

    df['session'] = df['hour'].apply(get_session)

    print(f"  ✓ Columnas preparadas")
    print(f"  ✓ Trading dates asignadas")
    print(f"  ✓ Bloques horarios asignados")

    return df

# ============================================================================
# PASO 2: RANGO Y CONTRIBUCIÓN POR BLOQUE
# ============================================================================

def calculate_block_statistics(df):
    """Calcula estadísticas de rango por bloque."""
    print("\n" + "=" * 80)
    print("PASO 2: RANGO Y CONTRIBUCIÓN POR BLOQUE")
    print("=" * 80)
    print("\n[2.1] Calculando estadísticas...")

    # Convertir a pips
    df = df.copy()
    df['range_pips'] = (df['high'] - df['low']) * 10000
    df['return_pips'] = (df['close'] - df['open']) * 10000

    # Estadísticas diarias
    daily = df.groupby('trading_date').agg({
        'high': 'max',
        'low': 'min',
        'open': 'first',
        'close': 'last',
        'range_pips': 'max'
    }).rename(columns={'range_pips': 'daily_range_pips'})

    daily['daily_return_pips'] = (daily['close'] - daily['open']) * 10000

    # Estadísticas por bloque × día
    block_daily = df.groupby(['trading_date', 'session']).agg({
        'high': ['max', 'first'],
        'low': ['min', 'first'],
        'open': 'first',
        'close': 'last',
        'range_pips': 'max'
    }).reset_index()

    block_daily.columns = ['trading_date', 'session', 'block_high', 'block_high_first',
                           'block_low', 'block_low_first', 'block_open', 'block_close', 'block_range_pips']

    block_daily['block_return_pips'] = (block_daily['block_close'] - block_daily['block_open']) * 10000

    # Merge con daily
    block_daily = block_daily.merge(daily[['daily_range_pips']], left_on='trading_date', right_index=True)

    block_daily['contribution_pct'] = (block_daily['block_range_pips'] / block_daily['daily_range_pips'] * 100).fillna(0)

    print(f"  ✓ Estadísticas de {len(daily):,} días procesadas")
    print(f"  ✓ {len(block_daily):,} bloques calculados")

    return daily, block_daily

def print_block_summary(daily, block_daily):
    """Imprime resumen de bloques."""
    print("\n[2.2] RANGO MEDIO POR BLOQUE (TODO EL PERÍODO):")

    summary = block_daily.groupby('session').agg({
        'block_range_pips': ['count', 'mean', 'median', 'std'],
        'block_return_pips': ['mean', 'median'],
        'contribution_pct': ['mean', 'median']
    }).round(2)

    summary.columns = ['Count', 'Mean Range', 'Median Range', 'Std Range',
                       'Mean Return', 'Median Return', 'Mean Contrib %', 'Median Contrib %']

    print("\n" + summary.to_string())

    # Probabilidades de HIGH/LOW
    print("\n[2.3] PROBABILIDAD DE HIGH/LOW DEL DÍA POR BLOQUE:")

    # Identificar bloque del high y low
    idx_high = df.groupby('trading_date')['high'].idxmax()
    idx_low = df.groupby('trading_date')['low'].idxmin()

    sessions_high = df.loc[idx_high, 'session'].value_counts(normalize=True) * 100
    sessions_low = df.loc[idx_low, 'session'].value_counts(normalize=True) * 100

    prob_table = pd.DataFrame({
        'HIGH (%)': sessions_high,
        'LOW (%)': sessions_low
    }).fillna(0).round(2).sort_index()

    print("\n" + prob_table.to_string())

    return summary, prob_table

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # PASO 1
    df = load_all_csvs()
    df = prepare_data(df)

    print("\n✓ PASO 1 COMPLETADO")

    # PASO 2
    daily, block_daily = calculate_block_statistics(df)
    summary, prob_table = print_block_summary(daily, block_daily)

    # Guardar resultados
    daily.to_csv(RESULTS_PATH / 'daily_stats.csv')
    block_daily.to_csv(RESULTS_PATH / 'block_stats.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ ANÁLISIS COMPLETADO - Resultados guardados en results/")
    print("=" * 80)
