"""
Análisis EUR/USD M1 (2000-2025) — VERSIÓN 3 CORREGIDA
======================================================
Trading days:
  LUNES:     domingo 17:00 → lunes 17:00
  MARTES:    lunes 17:00 → martes 17:00
  MIÉRCOLES: martes 17:00 → miércoles 17:00
  JUEVES:    miércoles 17:00 → jueves 17:00
  VIERNES:   jueves 17:00 → viernes 16:00

Análisis:
  1. ¿En qué HORA (H1) cae el HIGH/LOW de cada día?
  2. ¿En qué DÍA cae el HIGH/LOW de cada semana?
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'
RESULTS_PATH.mkdir(exist_ok=True)

SUBPERIODS = [
    ('2000-2007', '2000-01-01', '2007-12-31'),
    ('2008-2013', '2008-01-01', '2013-12-31'),
    ('2014-2019', '2014-01-01', '2019-12-31'),
    ('2020-2025', '2020-01-01', '2025-12-31'),
]

DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# ============================================================================
# PASO 1: CARGA, LIMPIEZA Y PREPARACIÓN
# ============================================================================

def load_and_clean():
    print("=" * 80)
    print("PASO 1: CARGA, LIMPIEZA Y PREPARACIÓN")
    print("=" * 80)

    print("\n[1.1] Cargando CSVs...")
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
            print(f"  ✓ {year}: {len(d):,}")

    df = pd.concat(dfs, ignore_index=True).sort_values('datetime').reset_index(drop=True)
    df.set_index('datetime', inplace=True)

    # Limpiar corruptos
    before = len(df)
    df = df[(df['high'] > 0.80) & (df['high'] < 1.70) &
            (df['low'] > 0.80) & (df['low'] < 1.70) &
            (df['open'] > 0.80) & (df['open'] < 1.70) &
            (df['close'] > 0.80) & (df['close'] < 1.70)]
    print(f"\n  Filas eliminadas: {before - len(df)}")
    print(f"  Total limpio: {len(df):,}")
    print(f"  Rango: {df['low'].min():.5f} - {df['high'].max():.5f}")
    print(f"  Período: {df.index.min()} a {df.index.max()}")

    return df


def assign_trading_days(df):
    """
    Asigna trading day correctamente:
      Si hora >= 17 → trading_date = DÍA SIGUIENTE (esa sesión de 17:00 pertenece al día siguiente)
      Si hora < 17  → trading_date = MISMO DÍA

    Así:
      Domingo 17:00 → trading_date = Lunes
      Lunes 08:00   → trading_date = Lunes
      Lunes 16:59   → trading_date = Lunes
      Lunes 17:00   → trading_date = Martes
      Jueves 17:00  → trading_date = Viernes
      Viernes 15:00 → trading_date = Viernes
    """
    print("\n[1.2] Asignando trading days...")

    df = df.copy()
    df['hour'] = df.index.hour

    # Si hora >= 17, trading_date = fecha + 1 día (pertenece al día siguiente)
    # Si hora < 17, trading_date = misma fecha
    dates = pd.Series(df.index.date, index=df.index).astype('datetime64[ns]')
    mask_after_17 = df['hour'] >= 17
    dates[mask_after_17] = dates[mask_after_17] + pd.Timedelta(days=1)
    df['trading_date'] = dates

    # Day of week del trading_date
    df['dow'] = df['trading_date'].dt.dayofweek
    df['day_name'] = df['trading_date'].dt.day_name()

    # Week key
    iso = df['trading_date'].dt.isocalendar()
    df['week_key'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    # Verificación
    print(f"\n  Distribución por día de la semana:")
    dow_counts = df.groupby('day_name').size()
    for day in DAY_ORDER:
        if day in dow_counts.index:
            print(f"    {day}: {dow_counts[day]:,} velas")

    # Días completos
    bars_per_day = df.groupby('trading_date').size()
    n_days = len(bars_per_day)

    # Filtrar por umbrales diferentes según día
    # Viernes es más corto (jueves 17:00 → viernes 16:00 = 23h vs 24h)
    # Lunes puede ser corto (domingo 17:00 → lunes 17:00 pero a veces abre tarde)
    valid_days = bars_per_day[bars_per_day >= 50].index  # umbral bajo para incluir viernes

    print(f"\n  Trading days totales: {n_days:,}")
    print(f"  Trading days válidos (>=50 velas): {len(valid_days):,}")

    # Verificar viernes
    df_valid = df[df['trading_date'].isin(valid_days)]
    friday_count = df_valid[df_valid['day_name'] == 'Friday']['trading_date'].nunique()
    print(f"  Viernes válidos: {friday_count:,}")

    n_weeks = df_valid['week_key'].nunique()
    print(f"  Semanas: {n_weeks:,}")

    return df, valid_days


def build_h1(df):
    print("\n[1.3] Construyendo H1...")
    h1 = df[['open', 'high', 'low', 'close']].resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    h1['hour'] = h1.index.hour
    dates = pd.Series(h1.index.date, index=h1.index).astype('datetime64[ns]')
    mask = h1['hour'] >= 17
    dates[mask] = dates[mask] + pd.Timedelta(days=1)
    h1['trading_date'] = dates
    h1['dow'] = h1['trading_date'].dt.dayofweek
    h1['day_name'] = h1['trading_date'].dt.day_name()

    iso = h1['trading_date'].dt.isocalendar()
    h1['week_key'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    print(f"  ✓ {len(h1):,} velas H1")
    return h1


def build_daily(df, valid_days):
    print("\n[1.4] Construyendo D1...")
    d1 = df[df['trading_date'].isin(valid_days)].groupby('trading_date').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    })
    d1['range_pips'] = (d1['high'] - d1['low']) * 10000
    d1['return_pips'] = (d1['close'] - d1['open']) * 10000
    d1['dow'] = d1.index.dayofweek
    d1['day_name'] = d1.index.day_name()

    iso = d1.index.isocalendar()
    d1['week_key'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    print(f"  ✓ {len(d1):,} velas D1")

    # Stats por día
    print(f"\n  Rango diario promedio por día:")
    for day in DAY_ORDER:
        subset = d1[d1['day_name'] == day]
        if len(subset) > 0:
            print(f"    {day}: {subset['range_pips'].mean():.1f} pips ({len(subset):,} días)")

    return d1


def build_weekly(d1):
    print("\n[1.5] Construyendo W1...")
    w1 = d1.groupby('week_key').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    })
    w1['weekly_range_pips'] = (w1['high'] - w1['low']) * 10000
    w1['weekly_return_pips'] = (w1['close'] - w1['open']) * 10000

    days_per_week = d1.groupby('week_key').size()
    valid_weeks = days_per_week[days_per_week >= 3].index
    w1 = w1[w1.index.isin(valid_weeks)]

    print(f"  ✓ {len(w1):,} semanas (>=3 días)")
    print(f"  Rango semanal promedio: {w1['weekly_range_pips'].mean():.1f} pips")
    return w1


# ============================================================================
# PASO 2: ¿EN QUÉ HORA (H1) CAE EL HIGH/LOW DE CADA DÍA?
# ============================================================================

def analyze_hourly_extremes(h1, valid_days):
    print("\n" + "=" * 80)
    print("PASO 2: ¿EN QUÉ HORA (H1) CAE EL HIGH/LOW DE CADA DÍA?")
    print("=" * 80)

    h1v = h1[h1['trading_date'].isin(valid_days)].copy()

    # Para cada trading_date, hora del HIGH y LOW
    idx_high = h1v.groupby('trading_date')['high'].idxmax()
    idx_low = h1v.groupby('trading_date')['low'].idxmin()

    extremes = pd.DataFrame({
        'high_hour': h1v.loc[idx_high, 'hour'].values,
        'low_hour': h1v.loc[idx_low, 'hour'].values,
        'dow': h1v.loc[idx_high, 'dow'].values,
        'day_name': h1v.loc[idx_high, 'day_name'].values,
    }, index=h1v.loc[idx_high, 'trading_date'].values)
    extremes.index.name = 'trading_date'

    n = len(extremes)

    # Orden del trading day: 17,18,...,23,0,1,...,16
    trading_hours = list(range(17, 24)) + list(range(0, 17))

    high_dist = extremes['high_hour'].value_counts(normalize=True).reindex(trading_hours).fillna(0) * 100
    low_dist = extremes['low_hour'].value_counts(normalize=True).reindex(trading_hours).fillna(0) * 100

    # 2.1 - Tabla completa
    print(f"\n[2.1] DISTRIBUCIÓN COMPLETA ({n:,} días):")
    print(f"\n  {'Hora ET':>8} | {'HIGH (%)':>10} | {'LOW (%)':>10}")
    print(f"  {'-'*8}-+-{'-'*10}-+-{'-'*10}")
    for h in trading_hours:
        hp = high_dist.get(h, 0)
        lp = low_dist.get(h, 0)
        bh = '█' * int(hp * 2)
        bl = '▓' * int(lp * 2)
        print(f"  {h:02d}:00    | {hp:8.2f}%  | {lp:8.2f}%  {bh}{bl}")

    # 2.2 - Top 5
    print(f"\n[2.2] TOP 5 HORAS:")
    top_h = high_dist.sort_values(ascending=False).head(5)
    top_l = low_dist.sort_values(ascending=False).head(5)
    print(f"\n  HIGH: ", end='')
    for h, p in top_h.items():
        print(f"{int(h):02d}:00 ({p:.1f}%)  ", end='')
    print(f"\n  LOW:  ", end='')
    for h, p in top_l.items():
        print(f"{int(h):02d}:00 ({p:.1f}%)  ", end='')
    print()

    # 2.3 - Por subperiodo
    print(f"\n[2.3] POR SUBPERIODO:")
    for pname, start, end in SUBPERIODS:
        sub = extremes[(extremes.index >= start) & (extremes.index <= end)]
        if len(sub) < 50:
            continue
        th = sub['high_hour'].value_counts(normalize=True).head(3) * 100
        tl = sub['low_hour'].value_counts(normalize=True).head(3) * 100
        print(f"\n  {pname} ({len(sub):,} días):")
        print(f"    HIGH: ", end='')
        for h, p in th.items():
            print(f"{int(h):02d}:00 ({p:.1f}%)  ", end='')
        print(f"\n    LOW:  ", end='')
        for h, p in tl.items():
            print(f"{int(h):02d}:00 ({p:.1f}%)  ", end='')
        print()

    # 2.4 - Por día de la semana
    print(f"\n[2.4] POR DÍA DE LA SEMANA:")
    for day in DAY_ORDER:
        sub = extremes[extremes['day_name'] == day]
        if len(sub) < 50:
            continue
        th = sub['high_hour'].value_counts(normalize=True).head(3) * 100
        tl = sub['low_hour'].value_counts(normalize=True).head(3) * 100
        print(f"\n  {day} ({len(sub)} días):")
        print(f"    HIGH: ", end='')
        for h, p in th.items():
            print(f"{int(h):02d}:00 ({p:.1f}%)  ", end='')
        print(f"\n    LOW:  ", end='')
        for h, p in tl.items():
            print(f"{int(h):02d}:00 ({p:.1f}%)  ", end='')
        print()

    return extremes, high_dist, low_dist


# ============================================================================
# PASO 3: ¿EN QUÉ DÍA CAE EL HIGH/LOW DE CADA SEMANA?
# ============================================================================

def analyze_weekly_extremes(d1, w1):
    print("\n" + "=" * 80)
    print("PASO 3: ¿EN QUÉ DÍA CAE EL HIGH/LOW DE CADA SEMANA?")
    print("=" * 80)

    rows = []
    for wk in w1.index:
        wd = d1[d1['week_key'] == wk]
        if len(wd) < 3:
            continue
        hd = wd['high'].idxmax()
        ld = wd['low'].idxmin()
        rows.append({
            'week_key': wk,
            'high_day_name': hd.day_name(),
            'high_dow': hd.dayofweek,
            'low_day_name': ld.day_name(),
            'low_dow': ld.dayofweek,
            'weekly_range': w1.loc[wk, 'weekly_range_pips'],
            'weekly_return': w1.loc[wk, 'weekly_return_pips'],
        })

    wdf = pd.DataFrame(rows)
    n = len(wdf)

    # 3.1 - Distribución
    print(f"\n[3.1] DISTRIBUCIÓN HIGH/LOW SEMANAL ({n:,} semanas):")

    hd = wdf['high_day_name'].value_counts(normalize=True).reindex(DAY_ORDER).fillna(0) * 100
    ld = wdf['low_day_name'].value_counts(normalize=True).reindex(DAY_ORDER).fillna(0) * 100

    print(f"\n  {'Día':>12} | {'HIGH (%)':>10} | {'LOW (%)':>10}")
    print(f"  {'-'*12}-+-{'-'*10}-+-{'-'*10}")
    for day in DAY_ORDER:
        hp = hd.get(day, 0)
        lp = ld.get(day, 0)
        bh = '█' * int(hp)
        bl = '▓' * int(lp)
        print(f"  {day:>12} | {hp:8.2f}%  | {lp:8.2f}%  {bh}{bl}")

    # 3.2 - OHLC vs OLHC
    print(f"\n[3.2] PATRÓN OHLC vs OLHC:")
    wdf['high_first'] = wdf['high_dow'] < wdf['low_dow']
    wdf['low_first'] = wdf['low_dow'] < wdf['high_dow']
    wdf['same_day'] = wdf['high_dow'] == wdf['low_dow']

    ohlc = wdf['high_first'].sum()
    olhc = wdf['low_first'].sum()
    same = wdf['same_day'].sum()
    print(f"  OHLC (High antes que Low): {ohlc} ({100*ohlc/n:.1f}%)")
    print(f"  OLHC (Low antes que High): {olhc} ({100*olhc/n:.1f}%)")
    print(f"  Mismo día:                 {same} ({100*same/n:.1f}%)")

    # 3.3 - Subperiodos
    print(f"\n[3.3] POR SUBPERIODO:")
    wdf['year'] = wdf['week_key'].str[:4].astype(int)
    for pname, start, end in SUBPERIODS:
        sy, ey = int(start[:4]), int(end[:4])
        sub = wdf[(wdf['year'] >= sy) & (wdf['year'] <= ey)]
        if len(sub) < 20:
            continue
        hds = sub['high_day_name'].value_counts(normalize=True).reindex(DAY_ORDER).fillna(0) * 100
        lds = sub['low_day_name'].value_counts(normalize=True).reindex(DAY_ORDER).fillna(0) * 100
        o = sub['high_first'].sum()
        l = sub['low_first'].sum()
        ns = len(sub)
        print(f"\n  {pname} ({ns} semanas) — OHLC: {100*o/ns:.1f}% | OLHC: {100*l/ns:.1f}%")
        for day in DAY_ORDER:
            print(f"    {day:>12} | HIGH {hds.get(day,0):5.1f}%  | LOW {lds.get(day,0):5.1f}%")

    # 3.4 - Alcista vs Bajista
    print(f"\n[3.4] SEMANA ALCISTA vs BAJISTA:")
    wdf['bullish'] = wdf['weekly_return'] > 0

    for label, is_bull in [('ALCISTA', True), ('BAJISTA', False)]:
        sub = wdf[wdf['bullish'] == is_bull]
        if len(sub) < 20:
            continue
        hds = sub['high_day_name'].value_counts(normalize=True).reindex(DAY_ORDER).fillna(0) * 100
        lds = sub['low_day_name'].value_counts(normalize=True).reindex(DAY_ORDER).fillna(0) * 100
        o = sub['high_first'].sum()
        l = sub['low_first'].sum()
        ns = len(sub)
        print(f"\n  {label} ({ns} semanas) — OHLC: {100*o/ns:.1f}% | OLHC: {100*l/ns:.1f}%")
        for day in DAY_ORDER:
            print(f"    {day:>12} | HIGH {hds.get(day,0):5.1f}%  | LOW {lds.get(day,0):5.1f}%")

    return wdf


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    df = load_and_clean()
    df, valid_days = assign_trading_days(df)
    h1 = build_h1(df)
    d1 = build_daily(df, valid_days)
    w1 = build_weekly(d1)

    print("\n" + "=" * 80)
    print("✓ PASO 1 COMPLETADO")
    print("=" * 80)

    extremes, high_dist, low_dist = analyze_hourly_extremes(h1, valid_days)
    wdf = analyze_weekly_extremes(d1, w1)

    # Guardar
    d1.to_csv(RESULTS_PATH / 'v3_daily_stats.csv')
    w1.to_csv(RESULTS_PATH / 'v3_weekly_stats.csv')

    hour_df = pd.DataFrame({'HIGH_pct': high_dist, 'LOW_pct': low_dist})
    hour_df.to_csv(RESULTS_PATH / 'v3_hourly_extreme_distribution.csv')
    wdf.to_csv(RESULTS_PATH / 'v3_weekly_extremes.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ ANÁLISIS V3 COMPLETO")
    print("=" * 80)
