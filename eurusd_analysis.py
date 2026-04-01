"""
Análisis Cuantitativo EUR/USD M1 (2000-2025)
Especialización en estadísticas por bloque horario con foco en NY
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import os

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'
RESULTS_PATH.mkdir(exist_ok=True)

# Bloques horarios (ET)
SESSIONS = {
    'Asia': (20, 0),          # 20:00 a 00:00 (4h)
    'Post-Asia': (0, 2),      # 00:00 a 02:00 (2h)
    'London': (2, 5),         # 02:00 a 05:00 (3h)
    'Post-London': (5, 8),    # 05:00 a 08:00 (3h)
    'NY': (8, 11),            # 08:00 a 11:00 (3h)
    'Post-NY': (11, 20),      # 11:00 a 20:00 (9h)
}

# Subperiodos
SUBPERIODS = [
    ('2000-2007', '2000-05-01', '2007-12-31'),
    ('2008-2013', '2008-01-01', '2013-12-31'),
    ('2014-2019', '2014-01-01', '2019-12-31'),
    ('2020-2025', '2020-01-01', '2025-12-31'),
]

# ============================================================================
# PASO 1: CARGA Y PREPARACIÓN DE DATOS
# ============================================================================

def load_all_csvs():
    """Carga todos los CSV M1 y retorna DataFrame unificado."""
    print("=" * 80)
    print("PASO 1: CARGA Y PREPARACIÓN DE DATOS")
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
            # Parsear datetime
            df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
            df = df.drop('datetime_str', axis=1)
            dfs.append(df)
            print(f"  ✓ {year}: {len(df):,} filas")

    # Concatenar y ordenar
    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values('datetime').reset_index(drop=True)
    df = df.set_index('datetime')

    print(f"\n  Total: {len(df):,} filas")
    print(f"  Período: {df.index.min()} a {df.index.max()}")

    return df

def assign_trading_day_and_session(df):
    """
    Asigna día de trading y bloque horario.

    Ciclo del día de trading: 17:00 → 17:00 (siguiente día)
    - Si hora >= 17:00 → trading_date = fecha actual
    - Si hora < 17:00 → trading_date = fecha anterior
    """
    print("\n[1.2] Asignando trading day y bloques horarios...")

    # Extraer hora y fecha
    df['hour'] = df.index.hour
    df['date'] = df.index.date

    # Trading date: si hora >= 17, es el día actual; sino, es el día anterior
    # Usar where para vectorizar (mucho más rápido)
    df['trading_date'] = df['date'].astype('datetime64[ns]')
    df.loc[df['hour'] < 17, 'trading_date'] = (
        df.loc[df['hour'] < 17, 'trading_date'] - pd.Timedelta(days=1)
    )

    # Day of week (0=lunes, 4=viernes)
    df['day_of_week'] = df['trading_date'].dt.dayofweek
    df['day_name'] = df['trading_date'].dt.day_name()

    # Week ID
    df['week_id'] = df['trading_date'].dt.isocalendar().week
    df['year'] = df['trading_date'].dt.year

    # Session assignment
    def get_session(hour):
        for session_name, (start, end) in SESSIONS.items():
            if start < end:
                if start <= hour < end:
                    return session_name
            else:  # wraps around midnight (e.g., 20:00-00:00)
                if hour >= start or hour < end:
                    return session_name
        return None

    df['session'] = df['hour'].apply(get_session)

    # Convertir volumen a 0 (es siempre 0 en forex M1)
    df['volume'] = 0

    print(f"  ✓ Trading days asignados")
    print(f"  ✓ Bloques horarios asignados")

    return df

def create_resampled_data(df):
    """Crea datos resampled a H1, H4, D1, W1."""
    print("\n[1.3] Creando datos resampled (H1, H4, D1, W1)...")

    # H1
    h1 = df[['open', 'high', 'low', 'close', 'volume']].resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    print(f"  ✓ H1: {len(h1):,} velas")

    # H4 (alineado a 0, 4, 8, 12, 16, 20)
    h4 = df[['open', 'high', 'low', 'close', 'volume']].resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    print(f"  ✓ H4: {len(h4):,} velas")

    # D1 (por trading_date)
    d1 = df.groupby('trading_date').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    print(f"  ✓ D1: {len(d1):,} velas")

    # W1 (por semana - usando strftime simplificado)
    df['week_key'] = df['trading_date'].dt.strftime('%Y-W%U')
    w1 = df.groupby('week_key').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    print(f"  ✓ W1: {len(w1):,} velas")

    return h1, h4, d1, w1

def verify_data_quality(df, h1, h4, d1, w1):
    """Verifica la calidad de los datos cargados."""
    print("\n[1.4] Verificación de datos:")

    print(f"\n  Período cubierto:")
    print(f"    Inicio: {df.index.min()}")
    print(f"    Fin: {df.index.max()}")

    print(f"\n  Conteos:")
    print(f"    M1: {len(df):,} velas")
    print(f"    H1: {len(h1):,} velas")
    print(f"    H4: {len(h4):,} velas")
    print(f"    D1: {len(d1):,} velas")
    print(f"    W1: {len(w1):,} velas")

    # Trading days
    trading_days = df['trading_date'].nunique()
    weeks = df['week_id'].nunique()
    print(f"\n  Trading days: {trading_days:,}")
    print(f"  Weeks: {weeks:,}")

    # Huecos: días con < 100 velas (probables festivos/gaps)
    bars_per_day = df.groupby('trading_date').size()
    gaps = bars_per_day[bars_per_day < 100]
    if len(gaps) > 0:
        print(f"\n  ⚠ Días con < 100 velas (posibles festivos/gaps): {len(gaps)}")
        print(f"    Primeros: {gaps.head(10).to_dict()}")
    else:
        print(f"\n  ✓ No se detectan huecos significativos")

    # Distribución por sesión
    print(f"\n  Distribución por bloque horario (M1):")
    session_dist = df['session'].value_counts().sort_index()
    for session, count in session_dist.items():
        pct = 100 * count / len(df)
        print(f"    {session}: {count:,} ({pct:.1f}%)")

    # Rango de precios
    print(f"\n  Rango de precios (en precio absoluto):")
    print(f"    Min: {df['low'].min():.5f}")
    print(f"    Max: {df['high'].max():.5f}")
    print(f"    Cambio total: {(df['high'].max() - df['low'].min()):.5f}")

    return trading_days, weeks

# ============================================================================
# PASO 2: RANGO Y CONTRIBUCIÓN POR BLOQUE
# ============================================================================

def calculate_range_by_block(df):
    """
    Calcula rango diario y contribución de cada bloque al rango diario.

    - Daily range: high - low del día de trading
    - Block range: high - low del bloque
    - Block return: close - open del bloque
    - Contribution %: (block_range / daily_range) * 100
    """
    print("\n" + "=" * 80)
    print("PASO 2: RANGO Y CONTRIBUCIÓN POR BLOQUE")
    print("=" * 80)
    print("\n[2.1] Calculando rango diario y por bloque...")

    # Rango diario por trading_date
    daily_stats = df.groupby('trading_date').agg({
        'high': 'max',
        'low': 'min',
        'open': 'first',
        'close': 'last'
    }).reset_index()

    daily_stats['daily_range'] = (daily_stats['high'] - daily_stats['low']) * 10000  # en pips
    daily_stats['daily_return'] = (daily_stats['close'] - daily_stats['open']) * 10000  # en pips

    # Identificar bloque del high y low del día
    daily_high_times = df.loc[df.groupby('trading_date')['high'].idxmax(), ['trading_date', 'session']]
    daily_low_times = df.loc[df.groupby('trading_date')['low'].idxmin(), ['trading_date', 'session']]

    daily_stats = daily_stats.merge(
        daily_high_times.rename(columns={'session': 'session_high'}),
        on='trading_date', how='left'
    )
    daily_stats = daily_stats.merge(
        daily_low_times.rename(columns={'session': 'session_low'}),
        on='trading_date', how='left'
    )

    # Rango y retorno por bloque
    block_stats = df.groupby(['trading_date', 'session']).agg({
        'high': 'max',
        'low': 'min',
        'open': 'first',
        'close': 'last'
    }).reset_index()

    block_stats['block_range'] = (block_stats['high'] - block_stats['low']) * 10000  # en pips
    block_stats['block_return'] = (block_stats['close'] - block_stats['open']) * 10000  # en pips

    # Merge con daily_range para calcular contribución %
    block_stats = block_stats.merge(
        daily_stats[['trading_date', 'daily_range']],
        on='trading_date', how='left'
    )

    block_stats['contribution_pct'] = (
        (block_stats['block_range'] / block_stats['daily_range']) * 100
    ).fillna(0)

    print(f"  ✓ {len(daily_stats):,} días de trading procesados")
    print(f"  ✓ {len(block_stats):,} bloques × días calculados")

    # Estadísticas por bloque (todo el período)
    print("\n[2.2] Estadísticas de rango por bloque (TODO EL PERÍODO):")
    block_summary = block_stats.groupby('session').agg({
        'block_range': ['count', 'mean', 'median', 'std'],
        'block_return': ['mean', 'median'],
        'contribution_pct': ['mean', 'median']
    }).round(2)

    print("\n" + str(block_summary))

    # Probabilidad de que el high/low del día caiga en cada bloque
    print("\n[2.3] Probabilidad de HIGH/LOW del día por bloque:")

    prob_high = daily_stats['session_high'].value_counts(normalize=True).sort_index() * 100
    prob_low = daily_stats['session_low'].value_counts(normalize=True).sort_index() * 100

    prob_table = pd.DataFrame({
        'Prob HIGH (%)': prob_high,
        'Prob LOW (%)': prob_low
    }).fillna(0).round(2)

    print("\n" + str(prob_table))

    # Desglose por subperiodos
    print("\n[2.4] Rango medio por bloque y subperiodo:")

    for period_name, start_date, end_date in SUBPERIODS:
        period_data = block_stats[
            (block_stats['trading_date'] >= start_date) &
            (block_stats['trading_date'] <= end_date)
        ]
        if len(period_data) > 0:
            period_summary = period_data.groupby('session').agg({
                'block_range': 'mean',
                'contribution_pct': 'mean'
            }).round(2)
            print(f"\n  {period_name}:")
            print(f"  {period_summary.to_string()}")

    # Guardar resultados
    daily_stats.to_csv(RESULTS_PATH / 'daily_range_stats.csv', index=False)
    block_stats.to_csv(RESULTS_PATH / 'block_range_stats.csv', index=False)

    print("\n✓ Resultados guardados en results/daily_range_stats.csv y block_range_stats.csv")

    return daily_stats, block_stats

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Paso 1: Carga
    df = load_all_csvs()

    # Paso 1: Preparación
    df = assign_trading_day_and_session(df)

    # Paso 1: Resample
    h1, h4, d1, w1 = create_resampled_data(df)

    # Paso 1: Verificación
    trading_days, weeks = verify_data_quality(df, h1, h4, d1, w1)

    print("\n" + "=" * 80)
    print("PASO 1 COMPLETADO")
    print("=" * 80)

    # Guardar datos para pasos posteriores
    df.to_csv(RESULTS_PATH / 'df_m1_full.csv.gz', compression='gzip')
    h1.to_csv(RESULTS_PATH / 'h1_data.csv.gz', compression='gzip')
    h4.to_csv(RESULTS_PATH / 'h4_data.csv.gz', compression='gzip')
    d1.to_csv(RESULTS_PATH / 'd1_data.csv.gz', compression='gzip')
    w1.to_csv(RESULTS_PATH / 'w1_data.csv.gz', compression='gzip')

    print("\n✓ Datos preparados guardados en results/")

    # Paso 2: Rango y contribución por bloque
    daily_stats, block_stats = calculate_range_by_block(df)
