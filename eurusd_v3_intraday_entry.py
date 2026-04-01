"""
Análisis de ENTRADA EN TIEMPO REAL: ¿A qué HORA se forma LOTW/HOTW?
¿Qué pasa después? ¿Cómo entrar SIN información retrospectiva?

Análisis:
  PASO 4: Distribución horaria de LOTW/HOTW dentro del lunes
  PASO 5: Dinámica martes-viernes después del extremo del lunes
  PASO 6: Validación de reversals (¿realmente reversa el martes?)
  PASO 7: Matrices de entrada en tiempo real
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO_PATH = Path('/home/user/HISDATA-EURUSD')
RESULTS_PATH = REPO_PATH / 'results'
RESULTS_PATH.mkdir(exist_ok=True)

DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# ============================================================================
# CARGA Y PREPARACIÓN
# ============================================================================

def load_and_clean():
    print("=" * 80)
    print("CARGANDO DATOS M1 PARA ANÁLISIS INTRADÍA")
    print("=" * 80)

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

    # Limpiar corruptos
    before = len(df)
    df = df[(df['high'] > 0.80) & (df['high'] < 1.70) &
            (df['low'] > 0.80) & (df['low'] < 1.70) &
            (df['open'] > 0.80) & (df['open'] < 1.70) &
            (df['close'] > 0.80) & (df['close'] < 1.70)]

    print(f"  Total M1 limpio: {len(df):,}")
    return df


def assign_trading_days(df):
    print("\n[1.2] Asignando trading days...")
    df = df.copy()
    df['hour'] = df.index.hour

    dates = pd.Series(df.index.date, index=df.index).astype('datetime64[ns]')
    mask_after_17 = df['hour'] >= 17
    dates[mask_after_17] = dates[mask_after_17] + pd.Timedelta(days=1)
    df['trading_date'] = dates

    df['dow'] = df['trading_date'].dt.dayofweek
    df['day_name'] = df['trading_date'].dt.day_name()
    df['week_key'] = df['trading_date'].dt.strftime('%Y-W%V')

    valid_days = df.groupby('trading_date').size()
    valid_days = valid_days[valid_days >= 50].index
    print(f"  Trading days válidos: {len(valid_days):,}")

    return df, valid_days


# ============================================================================
# PASO 4: ANÁLISIS INTRADÍA DEL LUNES
# ============================================================================

def analyze_monday_intraday(df, valid_days):
    print("\n" + "=" * 80)
    print("PASO 4: ¿A QUÉ HORA DEL LUNES SE FORMA LOTW/HOTW?")
    print("=" * 80)

    # Filtrar solo lunes
    mondays = df[(df['day_name'] == 'Monday') & (df['trading_date'].isin(valid_days))].copy()

    # Para cada lunes, encontrar la hora del LOW y HIGH de la semana completa
    weeks = df[df['trading_date'].isin(valid_days)].groupby('week_key')

    monday_analysis = []

    for week_key, week_data in weeks:
        # Encontrar LOW y HIGH de toda la semana
        week_low_idx = week_data['low'].idxmin()
        week_high_idx = week_data['high'].idxmax()

        week_low_day = week_data.loc[week_low_idx, 'day_name']
        week_high_day = week_data.loc[week_high_idx, 'day_name']

        week_low_hour = week_data.loc[week_low_idx, 'hour']
        week_high_hour = week_data.loc[week_high_idx, 'hour']

        week_low_price = week_data.loc[week_low_idx, 'low']
        week_high_price = week_data.loc[week_high_idx, 'high']

        # Si el LOTW es el lunes, guardar info
        if week_low_day == 'Monday':
            monday_data = week_data[week_data['day_name'] == 'Monday']
            monday_low_idx = monday_data['low'].idxmin()
            monday_low_hour = monday_data.loc[monday_low_idx, 'hour']

            monday_analysis.append({
                'week_key': week_key,
                'lotw_hour': week_low_hour,
                'hotw_day': week_high_day,
                'hotw_hour': week_high_hour,
                'lotw_price': week_low_price,
                'hotw_price': week_high_price,
                'range': (week_high_price - week_low_price) * 10000,
                'is_lotw_monday': True,
                'monday_lowest_hour': monday_low_hour,
            })

        # Si el HOTW es el lunes, guardar info
        if week_high_day == 'Monday':
            monday_data = week_data[week_data['day_name'] == 'Monday']
            monday_high_idx = monday_data['high'].idxmax()
            monday_high_hour = monday_data.loc[monday_high_idx, 'hour']

            monday_analysis.append({
                'week_key': week_key,
                'hotw_hour': week_high_hour,
                'lotw_day': week_low_day,
                'lotw_hour': week_low_hour,
                'hotw_price': week_high_price,
                'lotw_price': week_low_price,
                'range': (week_high_price - week_low_price) * 10000,
                'is_hotw_monday': True,
                'monday_highest_hour': monday_high_hour,
            })

    monday_df = pd.DataFrame(monday_analysis)

    print(f"\n[4.1] SEMANAS CON LOTW EN LUNES:")
    lotw_mondays = monday_df[monday_df['is_lotw_monday'] == True]
    print(f"  Total: {len(lotw_mondays)} semanas")

    if len(lotw_mondays) > 0:
        print(f"\n  Distribución de HORAS cuando se forma LOTW del lunes:")
        hour_dist = lotw_mondays['lotw_hour'].value_counts().sort_index()
        for hour, count in hour_dist.items():
            pct = 100 * count / len(lotw_mondays)
            print(f"    {int(hour):02d}:00 ET: {pct:5.1f}% ({int(count):3d} semanas)")

        print(f"\n  Hora pico para LOTW: {int(lotw_mondays['lotw_hour'].mode()[0]):02d}:00 ET")
        print(f"  Promedio LOTW hora: {lotw_mondays['lotw_hour'].mean():.1f} (≈ {int(lotw_mondays['lotw_hour'].mean()):02d}:00 ET)")

        # Dónde ocurre HOTW después
        print(f"\n  HOTW después (martes-viernes):")
        hotw_dist = lotw_mondays['hotw_day'].value_counts().reindex(DAY_ORDER[1:]).fillna(0)
        for day in DAY_ORDER[1:]:
            count = hotw_dist[day]
            pct = 100 * count / len(lotw_mondays)
            print(f"    {day:>12}: {pct:5.1f}% ({int(count):3d} semanas)")

    print(f"\n[4.2] SEMANAS CON HOTW EN LUNES:")
    hotw_mondays = monday_df[monday_df['is_hotw_monday'] == True]
    print(f"  Total: {len(hotw_mondays)} semanas")

    if len(hotw_mondays) > 0:
        print(f"\n  Distribución de HORAS cuando se forma HOTW del lunes:")
        hour_dist = hotw_mondays['hotw_hour'].value_counts().sort_index()
        for hour, count in hour_dist.items():
            pct = 100 * count / len(hotw_mondays)
            print(f"    {int(hour):02d}:00 ET: {pct:5.1f}% ({int(count):3d} semanas)")

        print(f"\n  Hora pico para HOTW: {int(hotw_mondays['hotw_hour'].mode()[0]):02d}:00 ET")
        print(f"  Promedio HOTW hora: {hotw_mondays['hotw_hour'].mean():.1f} (≈ {int(hotw_mondays['hotw_hour'].mean()):02d}:00 ET)")

        # Dónde ocurre LOTW después
        print(f"\n  LOTW después (martes-viernes):")
        lotw_dist = hotw_mondays['lotw_day'].value_counts().reindex(DAY_ORDER[1:]).fillna(0)
        for day in DAY_ORDER[1:]:
            count = lotw_dist[day]
            pct = 100 * count / len(hotw_mondays)
            print(f"    {day:>12}: {pct:5.1f}% ({int(count):3d} semanas)")

    return monday_df, lotw_mondays, hotw_mondays


# ============================================================================
# PASO 5: DINÁMICA MARTES-VIERNES DESPUÉS DEL EXTREMO DEL LUNES
# ============================================================================

def analyze_week_dynamics(df, valid_days):
    print("\n" + "=" * 80)
    print("PASO 5: DINÁMICA MARTES-VIERNES DESPUÉS DEL EXTREMO DEL LUNES")
    print("=" * 80)

    # Para cada semana, comparar LOW/HIGH del lunes vs el resto
    weeks = df[df['trading_date'].isin(valid_days)].groupby('week_key')

    dynamics = []

    for week_key, week_data in weeks:
        # LOW semanal
        week_low_idx = week_data['low'].idxmin()
        week_low_day = week_data.loc[week_low_idx, 'day_name']
        week_low_price = week_data.loc[week_low_idx, 'low']

        # HIGH semanal
        week_high_idx = week_data['high'].idxmax()
        week_high_day = week_data.loc[week_high_idx, 'day_name']
        week_high_price = week_data.loc[week_high_idx, 'high']

        # Lunes data
        monday_data = week_data[week_data['day_name'] == 'Monday']
        if len(monday_data) == 0:
            continue

        monday_low = monday_data['low'].min()
        monday_high = monday_data['high'].max()
        monday_close = monday_data['close'].iloc[-1]

        # Martes data
        tuesday_data = week_data[week_data['day_name'] == 'Tuesday']
        if len(tuesday_data) == 0:
            tuesday_close = np.nan
        else:
            tuesday_close = tuesday_data['close'].iloc[-1]

        # Caso 1: LOTW en lunes
        if week_low_day == 'Monday':
            # ¿Qué pasó el martes?
            if len(tuesday_data) > 0:
                tuesday_return = (tuesday_close - monday_close) * 10000
                tuesday_direction = 'UP' if tuesday_return > 0 else 'DOWN'
            else:
                tuesday_return = np.nan
                tuesday_direction = 'N/A'

            # Rango del lunes vs rango total semanal
            monday_range = (monday_high - monday_low) * 10000
            week_range = (week_high_price - week_low_price) * 10000

            dynamics.append({
                'week_key': week_key,
                'case': 'LOTW_Monday',
                'monday_low': monday_low,
                'monday_high': monday_high,
                'monday_close': monday_close,
                'monday_range': monday_range,
                'week_range': week_range,
                'tuesday_close': tuesday_close,
                'tuesday_return_pips': tuesday_return,
                'tuesday_direction': tuesday_direction,
                'week_low_price': week_low_price,
                'week_high_price': week_high_price,
                'confirms_bullish': tuesday_direction == 'UP',
            })

        # Caso 2: HOTW en lunes
        elif week_high_day == 'Monday':
            # ¿Qué pasó el martes?
            if len(tuesday_data) > 0:
                tuesday_return = (tuesday_close - monday_close) * 10000
                tuesday_direction = 'DOWN' if tuesday_return < 0 else 'UP'
            else:
                tuesday_return = np.nan
                tuesday_direction = 'N/A'

            # Rango del lunes vs rango total semanal
            monday_range = (monday_high - monday_low) * 10000
            week_range = (week_high_price - week_low_price) * 10000

            dynamics.append({
                'week_key': week_key,
                'case': 'HOTW_Monday',
                'monday_low': monday_low,
                'monday_high': monday_high,
                'monday_close': monday_close,
                'monday_range': monday_range,
                'week_range': week_range,
                'tuesday_close': tuesday_close,
                'tuesday_return_pips': tuesday_return,
                'tuesday_direction': tuesday_direction,
                'week_low_price': week_low_price,
                'week_high_price': week_high_price,
                'confirms_bearish': tuesday_direction == 'DOWN',
            })

    dyn_df = pd.DataFrame(dynamics)

    print(f"\n[5.1] DESPUÉS DE LOTW EN LUNES (alcista esperado):")
    lotw_cases = dyn_df[dyn_df['case'] == 'LOTW_Monday']
    print(f"  Total casos: {len(lotw_cases)}")

    if len(lotw_cases) > 0:
        confirms = lotw_cases['confirms_bullish'].sum()
        not_confirms = len(lotw_cases) - confirms
        print(f"\n  Martes CONFIRMA alcista (sube): {confirms} ({100*confirms/len(lotw_cases):.1f}%)")
        print(f"  Martes NO confirma (baja): {not_confirms} ({100*not_confirms/len(lotw_cases):.1f}%)")

        print(f"\n  Promedio retorno martes: {lotw_cases['tuesday_return_pips'].mean():.1f} pips")
        print(f"  Mediana retorno martes: {lotw_cases['tuesday_return_pips'].median():.1f} pips")
        print(f"  Mín retorno martes: {lotw_cases['tuesday_return_pips'].min():.1f} pips")
        print(f"  Máx retorno martes: {lotw_cases['tuesday_return_pips'].max():.1f} pips")

    print(f"\n[5.2] DESPUÉS DE HOTW EN LUNES (bajista esperado):")
    hotw_cases = dyn_df[dyn_df['case'] == 'HOTW_Monday']
    print(f"  Total casos: {len(hotw_cases)}")

    if len(hotw_cases) > 0:
        confirms = hotw_cases['confirms_bearish'].sum()
        not_confirms = len(hotw_cases) - confirms
        print(f"\n  Martes CONFIRMA bajista (baja): {confirms} ({100*confirms/len(hotw_cases):.1f}%)")
        print(f"  Martes NO confirma (sube): {not_confirms} ({100*not_confirms/len(hotw_cases):.1f}%)")

        print(f"\n  Promedio retorno martes: {hotw_cases['tuesday_return_pips'].mean():.1f} pips")
        print(f"  Mediana retorno martes: {hotw_cases['tuesday_return_pips'].median():.1f} pips")
        print(f"  Mín retorno martes: {hotw_cases['tuesday_return_pips'].min():.1f} pips")
        print(f"  Máx retorno martes: {hotw_cases['tuesday_return_pips'].max():.1f} pips")

    return dyn_df, lotw_cases, hotw_cases


# ============================================================================
# PASO 6: MATRIZ DE VALIDACIÓN EN TIEMPO REAL
# ============================================================================

def create_entry_matrix(lotw_cases, hotw_cases):
    print("\n" + "=" * 80)
    print("PASO 6: MATRIZ DE ENTRADA EN TIEMPO REAL")
    print("=" * 80)

    # Filtrar valores NaN primero
    lotw_valid = lotw_cases[lotw_cases['tuesday_return_pips'].notna()].copy()
    hotw_valid = hotw_cases[hotw_cases['tuesday_return_pips'].notna()].copy()

    print(f"\n[6.1] ESCENARIO ALCISTA (LOTW el lunes):")
    print(f"\n  Si el lunes forma el LOW de la semana:")

    if 'confirms_bullish' in lotw_valid.columns:
        confirms_count = lotw_valid['confirms_bullish'].sum()
        prob = 100 * confirms_count / len(lotw_valid)
        print(f"  ├─ Probabilidad de alcista confirmado: {prob:.1f}%")

        wins = lotw_valid[lotw_valid['confirms_bullish'] == True]
        losses = lotw_valid[lotw_valid['confirms_bullish'] == False]

        if len(wins) > 0:
            print(f"  ├─ Retorno esperado martes (cuando confirma): {wins['tuesday_return_pips'].mean():.1f} pips")

        if len(losses) > 0:
            print(f"  └─ Riesgo si NO confirma: {abs(losses['tuesday_return_pips'].mean()):.1f} pips")

        # Calcular RR ratio
        if len(wins) > 0 and len(losses) > 0:
            win_avg = wins['tuesday_return_pips'].mean()
            loss_avg = abs(losses['tuesday_return_pips'].mean())

            if loss_avg > 0:
                rr_bullish = win_avg / loss_avg
                print(f"\n  RR Ratio (alcista): {rr_bullish:.2f}:1")
                print(f"  Breakeven %: {100 * loss_avg / (win_avg + loss_avg):.1f}%")

    print(f"\n[6.2] ESCENARIO BAJISTA (HOTW el lunes):")
    print(f"\n  Si el lunes forma el HIGH de la semana:")

    if 'confirms_bearish' in hotw_valid.columns:
        confirms_count = hotw_valid['confirms_bearish'].sum()
        prob = 100 * confirms_count / len(hotw_valid)
        print(f"  ├─ Probabilidad de bajista confirmado: {prob:.1f}%")

        wins = hotw_valid[hotw_valid['confirms_bearish'] == True]
        losses = hotw_valid[hotw_valid['confirms_bearish'] == False]

        if len(wins) > 0:
            print(f"  ├─ Retorno esperado martes (cuando confirma): {wins['tuesday_return_pips'].mean():.1f} pips")

        if len(losses) > 0:
            print(f"  └─ Riesgo si NO confirma: {abs(losses['tuesday_return_pips'].mean()):.1f} pips")

        if len(wins) > 0 and len(losses) > 0:
            win_avg = abs(wins['tuesday_return_pips'].mean())
            loss_avg = abs(losses['tuesday_return_pips'].mean())

            if loss_avg > 0:
                rr_bearish = win_avg / loss_avg
                print(f"\n  RR Ratio (bajista): {rr_bearish:.2f}:1")
                print(f"  Breakeven %: {100 * loss_avg / (win_avg + loss_avg):.1f}%")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    df = load_and_clean()
    df, valid_days = assign_trading_days(df)

    monday_df, lotw_mondays, hotw_mondays = analyze_monday_intraday(df, valid_days)
    dyn_df, lotw_cases, hotw_cases = analyze_week_dynamics(df, valid_days)

    create_entry_matrix(lotw_cases, hotw_cases)

    # Guardar
    monday_df.to_csv(RESULTS_PATH / 'v3_monday_extremes.csv', index=False)
    dyn_df.to_csv(RESULTS_PATH / 'v3_week_dynamics.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ ANÁLISIS DE ENTRADA EN TIEMPO REAL COMPLETADO")
    print("=" * 80)
    print(f"\nGuardado: v3_monday_extremes.csv, v3_week_dynamics.csv")
