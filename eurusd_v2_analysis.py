"""
Análisis EUR/USD M1 (2000-2025) — VERSIÓN CORREGIDA
=====================================================
- Datos limpios (filtro filas corruptas)
- Trading day: open 17:00 ET → close 17:00 ET siguiente
- Análisis H1: ¿en qué hora cae el HIGH/LOW de cada día?
- Análisis W1: ¿en qué día cae el HIGH/LOW de cada semana?
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'
RESULTS_PATH.mkdir(exist_ok=True)

SUBPERIODS = [
    ('2000-2007', '2000-01-01', '2007-12-31'),
    ('2008-2013', '2008-01-01', '2013-12-31'),
    ('2014-2019', '2014-01-01', '2019-12-31'),
    ('2020-2025', '2020-01-01', '2025-12-31'),
]

DAY_NAMES = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}

# ============================================================================
# PASO 1: CARGA, LIMPIEZA Y PREPARACIÓN
# ============================================================================

def load_and_clean():
    """Carga todos los CSV, limpia datos corruptos."""
    print("=" * 80)
    print("PASO 1: CARGA, LIMPIEZA Y PREPARACIÓN")
    print("=" * 80)

    print("\n[1.1] Cargando archivos CSV...")
    dfs = []
    for year in range(2000, 2026):
        filepath = REPO_PATH / f'DAT_ASCII_EURUSD_M1_{year}.csv'
        if filepath.exists():
            df = pd.read_csv(
                filepath, sep=';', header=None,
                names=['datetime_str', 'open', 'high', 'low', 'close', 'volume'],
                dtype={'open': float, 'high': float, 'low': float, 'close': float, 'volume': float}
            )
            df['datetime'] = pd.to_datetime(df['datetime_str'], format='%Y%m%d %H%M%S')
            df.drop('datetime_str', axis=1, inplace=True)
            dfs.append(df)
            print(f"  ✓ {year}: {len(df):,} filas")

    df = pd.concat(dfs, ignore_index=True).sort_values('datetime').reset_index(drop=True)
    df.set_index('datetime', inplace=True)
    print(f"\n  Total cargado: {len(df):,} filas")

    # Limpiar datos corruptos (EUR/USD realista: 0.80 - 1.70)
    print("\n[1.2] Limpiando datos corruptos...")
    before = len(df)
    df = df[(df['high'] > 0.80) & (df['high'] < 1.70) &
            (df['low'] > 0.80) & (df['low'] < 1.70) &
            (df['open'] > 0.80) & (df['open'] < 1.70) &
            (df['close'] > 0.80) & (df['close'] < 1.70)]
    removed = before - len(df)
    print(f"  Filas removidas: {removed}")
    print(f"  Datos limpios: {len(df):,} filas")

    # Rango real
    print(f"\n  RANGO REAL DEL DATASET:")
    print(f"    Máximo: {df['high'].max():.5f}")
    print(f"    Mínimo: {df['low'].min():.5f}")
    print(f"    Período: {df.index.min()} a {df.index.max()}")

    return df


def prepare_trading_days(df):
    """
    Asigna trading day.
    Trading day open = 17:00 ET del día X.
    Trading day close = 16:59 ET del día X+1.
    Si hora >= 17 → trading_date = fecha actual (ese día es el "open")
    Si hora < 17 → trading_date = fecha del día anterior
    """
    print("\n[1.3] Asignando trading days (open 17:00 ET)...")

    df = df.copy()
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute

    # Trading date
    dates = pd.Series(df.index.date, index=df.index).astype('datetime64[ns]')
    mask_before_17 = df['hour'] < 17
    dates[mask_before_17] = dates[mask_before_17] - pd.Timedelta(days=1)
    df['trading_date'] = dates

    # Day of week del trading_date
    df['dow'] = df['trading_date'].dt.dayofweek
    df['day_name'] = df['trading_date'].dt.day_name()

    # Week key
    iso = df['trading_date'].dt.isocalendar()
    df['week_key'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    # Verificación
    n_days = df['trading_date'].nunique()
    n_weeks = df['week_key'].nunique()
    print(f"  ✓ Trading days: {n_days:,}")
    print(f"  ✓ Semanas: {n_weeks:,}")

    # Filtrar días con pocas velas (festivos, gaps)
    bars_per_day = df.groupby('trading_date').size()
    valid_days = bars_per_day[bars_per_day >= 100].index
    invalid_days = bars_per_day[bars_per_day < 100]
    print(f"  ✓ Días válidos (>=100 velas): {len(valid_days):,}")
    print(f"  ⚠ Días con pocas velas (festivos/gaps): {len(invalid_days)}")

    return df, valid_days


def build_h1(df):
    """Construye velas H1 con trading_date y hora."""
    print("\n[1.4] Construyendo velas H1...")

    # Resample H1
    h1 = df[['open', 'high', 'low', 'close']].resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    h1['hour'] = h1.index.hour
    dates = pd.Series(h1.index.date, index=h1.index).astype('datetime64[ns]')
    mask = h1['hour'] < 17
    dates[mask] = dates[mask] - pd.Timedelta(days=1)
    h1['trading_date'] = dates
    h1['dow'] = h1['trading_date'].dt.dayofweek
    h1['day_name'] = h1['trading_date'].dt.day_name()

    iso = h1['trading_date'].dt.isocalendar()
    h1['week_key'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    print(f"  ✓ {len(h1):,} velas H1")
    return h1


def build_daily(df, valid_days):
    """Construye velas diarias basadas en trading_date."""
    print("\n[1.5] Construyendo velas D1 (trading day 17:00→17:00)...")

    d1 = df[df['trading_date'].isin(valid_days)].groupby('trading_date').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    })
    d1['range_pips'] = (d1['high'] - d1['low']) * 10000
    d1['return_pips'] = (d1['close'] - d1['open']) * 10000
    d1['dow'] = d1.index.dayofweek
    d1['day_name'] = d1.index.day_name()

    iso = d1.index.isocalendar()
    d1['week_key'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    print(f"  ✓ {len(d1):,} velas D1 válidas")
    print(f"\n  Rango diario promedio: {d1['range_pips'].mean():.2f} pips")
    print(f"  Rango diario mediana: {d1['range_pips'].median():.2f} pips")

    return d1


def build_weekly(d1):
    """Construye velas semanales a partir de D1."""
    print("\n[1.6] Construyendo velas W1...")

    w1 = d1.groupby('week_key').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last',
        'range_pips': 'sum'
    })
    w1['weekly_range_pips'] = (w1['high'] - w1['low']) * 10000
    w1['weekly_return_pips'] = (w1['close'] - w1['open']) * 10000

    # Filtrar semanas con al menos 3 días
    days_per_week = d1.groupby('week_key').size()
    valid_weeks = days_per_week[days_per_week >= 3].index
    w1 = w1[w1.index.isin(valid_weeks)]

    print(f"  ✓ {len(w1):,} semanas válidas (>=3 días)")
    print(f"  Rango semanal promedio: {w1['weekly_range_pips'].mean():.2f} pips")

    return w1


# ============================================================================
# PASO 2: ¿EN QUÉ HORA (H1) CAE EL HIGH/LOW DE CADA DÍA?
# ============================================================================

def analyze_daily_extremes_by_hour(h1, valid_days):
    """Para cada día, identifica en qué hora H1 se formó el HIGH y LOW."""
    print("\n" + "=" * 80)
    print("PASO 2: ¿EN QUÉ HORA (H1) CAE EL HIGH/LOW DE CADA DÍA?")
    print("=" * 80)

    h1_valid = h1[h1['trading_date'].isin(valid_days)].copy()

    # Para cada trading_date, encontrar la hora del HIGH y LOW
    idx_high = h1_valid.groupby('trading_date')['high'].idxmax()
    idx_low = h1_valid.groupby('trading_date')['low'].idxmin()

    high_hours = h1_valid.loc[idx_high, ['trading_date', 'hour']].rename(columns={'hour': 'high_hour'})
    low_hours = h1_valid.loc[idx_low, ['trading_date', 'hour']].rename(columns={'hour': 'low_hour'})

    daily_extremes = high_hours.set_index('trading_date').join(low_hours.set_index('trading_date'))

    n_days = len(daily_extremes)

    # ========================================================================
    # 2.1 - Distribución del HIGH por hora
    # ========================================================================
    print("\n[2.1] PROBABILIDAD DEL HIGH DIARIO POR HORA (H1):")
    print("-" * 80)

    # Ordenar horas en ciclo trading day: 17,18,19,20,21,22,23,0,1,...,16
    trading_hours = list(range(17, 24)) + list(range(0, 17))

    high_dist = daily_extremes['high_hour'].value_counts(normalize=True).reindex(trading_hours).fillna(0) * 100
    low_dist = daily_extremes['low_hour'].value_counts(normalize=True).reindex(trading_hours).fillna(0) * 100

    print(f"\n  {'Hora ET':>8} | {'HIGH (%)':>10} | {'LOW (%)':>10} | {'HIGH+LOW (%)':>14}")
    print(f"  {'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*14}")
    for h in trading_hours:
        h_pct = high_dist.get(h, 0)
        l_pct = low_dist.get(h, 0)
        total = h_pct + l_pct
        bar_h = '█' * int(h_pct * 2)
        bar_l = '▓' * int(l_pct * 2)
        print(f"  {h:02d}:00    | {h_pct:8.2f}%  | {l_pct:8.2f}%  | {total:10.2f}%    {bar_h}{bar_l}")

    print(f"\n  Total días analizados: {n_days:,}")

    # ========================================================================
    # 2.2 - Top horas para HIGH y LOW
    # ========================================================================
    print("\n[2.2] TOP 5 HORAS MÁS PROBABLES:")
    print("-" * 80)

    top_high = high_dist.sort_values(ascending=False).head(5)
    top_low = low_dist.sort_values(ascending=False).head(5)

    print("\n  TOP 5 HORAS PARA HIGH DEL DÍA:")
    for h, pct in top_high.items():
        print(f"    {int(h):02d}:00 → {pct:.2f}%")

    print("\n  TOP 5 HORAS PARA LOW DEL DÍA:")
    for h, pct in top_low.items():
        print(f"    {int(h):02d}:00 → {pct:.2f}%")

    # ========================================================================
    # 2.3 - Desglose por subperiodos
    # ========================================================================
    print("\n[2.3] DESGLOSE POR SUBPERIODOS:")
    print("-" * 80)

    for period_name, start, end in SUBPERIODS:
        mask = (daily_extremes.index >= start) & (daily_extremes.index <= end)
        subset = daily_extremes[mask]
        if len(subset) < 50:
            continue

        high_sub = subset['high_hour'].value_counts(normalize=True).reindex(trading_hours).fillna(0) * 100
        low_sub = subset['low_hour'].value_counts(normalize=True).reindex(trading_hours).fillna(0) * 100

        top_h = high_sub.sort_values(ascending=False).head(3)
        top_l = low_sub.sort_values(ascending=False).head(3)

        print(f"\n  {period_name} ({len(subset):,} días):")
        print(f"    Top 3 HIGH: ", end='')
        for h, pct in top_h.items():
            print(f"{int(h):02d}:00 ({pct:.1f}%)  ", end='')
        print()
        print(f"    Top 3 LOW:  ", end='')
        for h, pct in top_l.items():
            print(f"{int(h):02d}:00 ({pct:.1f}%)  ", end='')
        print()

    # ========================================================================
    # 2.4 - Desglose por día de la semana
    # ========================================================================
    print("\n[2.4] TOP 3 HORAS DE HIGH/LOW POR DÍA DE LA SEMANA:")
    print("-" * 80)

    daily_extremes['dow'] = daily_extremes.index.dayofweek
    daily_extremes['day_name'] = daily_extremes.index.day_name()

    for dow in range(5):  # Lunes a Viernes
        day_name = DAY_NAMES[dow]
        subset = daily_extremes[daily_extremes['dow'] == dow]
        if len(subset) < 50:
            continue

        top_h = subset['high_hour'].value_counts(normalize=True).head(3) * 100
        top_l = subset['low_hour'].value_counts(normalize=True).head(3) * 100

        print(f"\n  {day_name} ({len(subset)} días):")
        print(f"    Top 3 HIGH: ", end='')
        for h, pct in top_h.items():
            print(f"{int(h):02d}:00 ({pct:.1f}%)  ", end='')
        print()
        print(f"    Top 3 LOW:  ", end='')
        for h, pct in top_l.items():
            print(f"{int(h):02d}:00 ({pct:.1f}%)  ", end='')
        print()

    return daily_extremes, high_dist, low_dist


# ============================================================================
# PASO 3: ¿EN QUÉ DÍA CAE EL HIGH/LOW DE CADA SEMANA?
# ============================================================================

def analyze_weekly_extremes_by_day(d1, w1):
    """Para cada semana, identifica en qué día de la semana se formó el HIGH y LOW."""
    print("\n" + "=" * 80)
    print("PASO 3: ¿EN QUÉ DÍA CAE EL HIGH/LOW DE CADA SEMANA?")
    print("=" * 80)

    # Para cada semana, encontrar qué día tuvo el HIGH y LOW
    weekly_extremes = []

    for week_key in w1.index:
        week_days = d1[d1['week_key'] == week_key]
        if len(week_days) < 3:
            continue

        high_day = week_days['high'].idxmax()
        low_day = week_days['low'].idxmin()

        weekly_extremes.append({
            'week_key': week_key,
            'high_day': high_day,
            'high_dow': high_day.dayofweek,
            'high_day_name': high_day.day_name(),
            'low_day': low_day,
            'low_dow': low_day.dayofweek,
            'low_day_name': low_day.day_name(),
            'weekly_range_pips': w1.loc[week_key, 'weekly_range_pips'],
        })

    wdf = pd.DataFrame(weekly_extremes)
    n_weeks = len(wdf)

    # ========================================================================
    # 3.1 - Distribución del HIGH/LOW semanal por día
    # ========================================================================
    print("\n[3.1] PROBABILIDAD DEL HIGH/LOW SEMANAL POR DÍA:")
    print("-" * 80)

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    high_day_dist = wdf['high_day_name'].value_counts(normalize=True).reindex(day_order).fillna(0) * 100
    low_day_dist = wdf['low_day_name'].value_counts(normalize=True).reindex(day_order).fillna(0) * 100

    print(f"\n  {'Día':>12} | {'HIGH (%)':>10} | {'LOW (%)':>10}")
    print(f"  {'-'*12}-+-{'-'*10}-+-{'-'*10}")
    for day in day_order:
        h_pct = high_day_dist.get(day, 0)
        l_pct = low_day_dist.get(day, 0)
        bar_h = '█' * int(h_pct)
        bar_l = '▓' * int(l_pct)
        print(f"  {day:>12} | {h_pct:8.2f}%  | {l_pct:8.2f}%  {bar_h}{bar_l}")

    print(f"\n  Total semanas analizadas: {n_weeks:,}")

    # ========================================================================
    # 3.2 - OHLC/OLHC semanal
    # ========================================================================
    print("\n[3.2] PATRÓN OHLC vs OLHC SEMANAL:")
    print("-" * 80)

    # Para cada semana: ¿el HIGH se formó antes que el LOW (OHLC) o después (OLHC)?
    wdf['high_first'] = wdf['high_dow'] < wdf['low_dow']
    wdf['low_first'] = wdf['low_dow'] < wdf['high_dow']
    wdf['same_day'] = wdf['high_dow'] == wdf['low_dow']

    ohlc_count = wdf['high_first'].sum()  # Open → High → Low → Close
    olhc_count = wdf['low_first'].sum()   # Open → Low → High → Close
    same_count = wdf['same_day'].sum()

    print(f"\n  OHLC (High antes que Low): {ohlc_count:,} semanas ({100*ohlc_count/n_weeks:.1f}%)")
    print(f"  OLHC (Low antes que High):  {olhc_count:,} semanas ({100*olhc_count/n_weeks:.1f}%)")
    print(f"  Mismo día (High=Low):       {same_count:,} semanas ({100*same_count/n_weeks:.1f}%)")

    # ========================================================================
    # 3.3 - Desglose por subperiodos
    # ========================================================================
    print("\n[3.3] DESGLOSE POR SUBPERIODOS:")
    print("-" * 80)

    # Extraer año de week_key
    wdf['year'] = wdf['week_key'].str[:4].astype(int)

    for period_name, start, end in SUBPERIODS:
        start_year = int(start[:4])
        end_year = int(end[:4])
        subset = wdf[(wdf['year'] >= start_year) & (wdf['year'] <= end_year)]
        if len(subset) < 20:
            continue

        high_sub = subset['high_day_name'].value_counts(normalize=True).reindex(day_order).fillna(0) * 100
        low_sub = subset['low_day_name'].value_counts(normalize=True).reindex(day_order).fillna(0) * 100

        ohlc = subset['high_first'].sum()
        olhc = subset['low_first'].sum()
        n = len(subset)

        print(f"\n  {period_name} ({n} semanas):")
        print(f"    OHLC: {100*ohlc/n:.1f}% | OLHC: {100*olhc/n:.1f}%")
        print(f"    {'Día':>12} | {'HIGH':>7} | {'LOW':>7}")
        for day in day_order:
            print(f"    {day:>12} | {high_sub.get(day,0):5.1f}%  | {low_sub.get(day,0):5.1f}%")

    # ========================================================================
    # 3.4 - Alcista vs Bajista
    # ========================================================================
    print("\n[3.4] DISTRIBUCIÓN SEGÚN SEMANA ALCISTA vs BAJISTA:")
    print("-" * 80)

    wdf['weekly_return'] = w1.loc[wdf['week_key'], 'weekly_return_pips'].values
    wdf['bullish'] = wdf['weekly_return'] > 0

    for label, is_bull in [('ALCISTA', True), ('BAJISTA', False)]:
        subset = wdf[wdf['bullish'] == is_bull]
        if len(subset) < 20:
            continue

        high_sub = subset['high_day_name'].value_counts(normalize=True).reindex(day_order).fillna(0) * 100
        low_sub = subset['low_day_name'].value_counts(normalize=True).reindex(day_order).fillna(0) * 100

        ohlc = subset['high_first'].sum()
        olhc = subset['low_first'].sum()
        n = len(subset)

        print(f"\n  Semana {label} ({n} semanas):")
        print(f"    OHLC: {100*ohlc/n:.1f}% | OLHC: {100*olhc/n:.1f}%")
        print(f"    {'Día':>12} | {'HIGH':>7} | {'LOW':>7}")
        for day in day_order:
            print(f"    {day:>12} | {high_sub.get(day,0):5.1f}%  | {low_sub.get(day,0):5.1f}%")

    return wdf, high_day_dist, low_day_dist


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # PASO 1
    df = load_and_clean()
    df, valid_days = prepare_trading_days(df)
    h1 = build_h1(df)
    d1 = build_daily(df, valid_days)
    w1 = build_weekly(d1)

    print("\n" + "=" * 80)
    print("✓ PASO 1 COMPLETADO")
    print("=" * 80)

    # PASO 2: Extremos diarios por hora H1
    daily_extremes, high_dist, low_dist = analyze_daily_extremes_by_hour(h1, valid_days)

    # PASO 3: Extremos semanales por día
    weekly_extremes, high_day_dist, low_day_dist = analyze_weekly_extremes_by_day(d1, w1)

    # Guardar resultados
    d1.to_csv(RESULTS_PATH / 'v2_daily_stats.csv')
    w1.to_csv(RESULTS_PATH / 'v2_weekly_stats.csv')

    # Guardar distribuciones
    hour_dist = pd.DataFrame({
        'HIGH_pct': high_dist,
        'LOW_pct': low_dist
    })
    hour_dist.to_csv(RESULTS_PATH / 'v2_hourly_extreme_distribution.csv')

    day_dist = pd.DataFrame({
        'HIGH_pct': high_day_dist,
        'LOW_pct': low_day_dist
    })
    day_dist.to_csv(RESULTS_PATH / 'v2_daily_extreme_distribution.csv')

    weekly_extremes.to_csv(RESULTS_PATH / 'v2_weekly_extremes.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ ANÁLISIS COMPLETO — Resultados en results/v2_*")
    print("=" * 80)
