"""
PASO 3: Análisis de la Sesión NY con Condicionales Direccionales
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

# ============================================================================
# PASO 3: FOCO EN NY
# ============================================================================

def paso3_ny_analysis(daily_stats, block_daily):
    """Análisis detallado de la sesión NY."""
    print("\n" + "=" * 80)
    print("PASO 3: FOCO EN SESIÓN NY")
    print("=" * 80)

    # ========================================================================
    # 3.1 - CONDICIONALES DIRECCIONALES
    # ========================================================================
    print("\n[3.1] CONDICIONALES DIRECCIONALES EN NY")
    print("-" * 80)

    # Filtrar bloques NY y Asia
    ny_blocks = block_daily[block_daily['session'] == 'NY'].copy()
    asia_blocks = block_daily[block_daily['session'] == 'Asia'].copy()

    # Calcular: precio a inicio de NY (08:00) vs apertura diaria
    # El precio de cierre de Post-London es aproximadamente el precio a las 08:00
    post_london_blocks = block_daily[block_daily['session'] == 'Post-London'].copy()

    # Merge para análisis de continuación
    ny_with_context = ny_blocks.merge(
        daily_stats[['daily_open', 'daily_close']].reset_index(),
        left_on='trading_date',
        right_on='trading_date'
    )

    ny_with_context = ny_with_context.merge(
        post_london_blocks[['trading_date', 'block_close']].rename(columns={'block_close': 'price_at_ny_start'}),
        on='trading_date',
        how='left'
    )

    # Clasificar según dirección pre-NY
    ny_with_context['direction_pre_ny'] = np.where(
        ny_with_context['price_at_ny_start'] > ny_with_context['daily_open'],
        'BULLISH',
        'BEARISH'
    )

    # Resultado en NY: ¿continuó o revirtió?
    ny_with_context['direction_result'] = np.where(
        ny_with_context['block_close'] > ny_with_context['price_at_ny_start'],
        'UP',
        'DOWN'
    )

    ny_with_context['extension_pips'] = (
        (ny_with_context['block_close'] - ny_with_context['price_at_ny_start']) * 10000
    )

    # Estadísticas por dirección pre-NY (TODO EL PERÍODO)
    print("\nESTADÍSTICAS NY POR DIRECCIÓN PRE-NY (TODO EL PERÍODO):")
    print()

    for direction in ['BULLISH', 'BEARISH']:
        subset = ny_with_context[ny_with_context['direction_pre_ny'] == direction]
        if len(subset) > 0:
            # Probabilidad de continuación
            continuations = (subset['direction_result'] == ('UP' if direction == 'BULLISH' else 'DOWN')).sum()
            cont_pct = 100 * continuations / len(subset)

            # Estadísticas de extensión
            ext_stats = subset['extension_pips'].describe()

            print(f"  {direction}:")
            print(f"    Casos: {len(subset)}")
            print(f"    Continuación: {continuations} ({cont_pct:.1f}%)")
            print(f"    Extensión promedio: {ext_stats['mean']:.2f} pips")
            print(f"    Extensión mediana: {ext_stats['50%']:.2f} pips")
            print(f"    P25: {ext_stats['25%']:.2f}, P75: {ext_stats['75%']:.2f}")
            print()

    # Desglose por subperiodos
    print("\nDESGLOSE POR SUBPERIODOS:")
    print()

    for period_name, start_date, end_date in SUBPERIODS:
        period_data = ny_with_context[
            (ny_with_context['trading_date'] >= start_date) &
            (ny_with_context['trading_date'] <= end_date)
        ]

        if len(period_data) > 0:
            print(f"  {period_name}:")
            for direction in ['BULLISH', 'BEARISH']:
                subset = period_data[period_data['direction_pre_ny'] == direction]
                if len(subset) > 0:
                    continuations = (subset['direction_result'] == ('UP' if direction == 'BULLISH' else 'DOWN')).sum()
                    cont_pct = 100 * continuations / len(subset)
                    ext_mean = subset['extension_pips'].mean()
                    print(f"    {direction}: {len(subset)} casos, {cont_pct:.1f}% continuación, {ext_mean:.2f} pips promedio")
            print()

    # ========================================================================
    # 3.2 - RELACIÓN ASIA/LONDON CON NY
    # ========================================================================
    print("\n[3.2] IMPACTO DE RANGO ALTO EN ASIA/LONDON → NY")
    print("-" * 80)

    # Calcular percentiles de rango
    asia_range_p75 = asia_blocks['block_range_pips'].quantile(0.75)
    london_range_p75 = block_daily[block_daily['session'] == 'London']['block_range_pips'].quantile(0.75)

    print(f"\n  Percentil 75 de rango:")
    print(f"    Asia: {asia_range_p75:.2f} pips")
    print(f"    London: {london_range_p75:.2f} pips")

    # Marcar días con rango alto en Asia/London
    asia_high_range_dates = set(
        asia_blocks[asia_blocks['block_range_pips'] > asia_range_p75]['trading_date']
    )
    london_high_range_dates = set(
        block_daily[
            (block_daily['session'] == 'London') &
            (block_daily['block_range_pips'] > london_range_p75)
        ]['trading_date']
    )

    # Análisis de NY condicionado a Asia/London alto
    ny_with_context['asia_high'] = ny_with_context['trading_date'].isin(asia_high_range_dates)
    ny_with_context['london_high'] = ny_with_context['trading_date'].isin(london_high_range_dates)

    print("\n  NY RANGO MEDIO SEGÚN RANGO PREVIO:")
    print()

    conditions = [
        ('Asia alto, London bajo', {'asia_high': True, 'london_high': False}),
        ('Asia bajo, London alto', {'asia_high': False, 'london_high': True}),
        ('Ambos alto', {'asia_high': True, 'london_high': True}),
        ('Ambos bajo', {'asia_high': False, 'london_high': False}),
    ]

    for cond_name, cond_dict in conditions:
        mask = pd.Series([True] * len(ny_with_context), index=ny_with_context.index)
        for key, val in cond_dict.items():
            mask = mask & (ny_with_context[key] == val)

        subset = ny_with_context[mask]
        if len(subset) > 0:
            ny_range_mean = subset['block_range_pips'].mean()
            ny_return_mean = subset['block_return_pips'].mean()
            print(f"  {cond_name}:")
            print(f"    Casos: {len(subset)}")
            print(f"    NY Rango promedio: {ny_range_mean:.2f} pips")
            print(f"    NY Return promedio: {ny_return_mean:.2f} pips")
            print()

    # ========================================================================
    # 3.3 - NUEVOS EXTREMOS EN NY
    # ========================================================================
    print("\n[3.3] PROBABILIDAD DE NUEVOS EXTREMOS EN NY")
    print("-" * 80)

    # Para cada día: ¿dónde se formó el high/low hasta el inicio de NY?
    # Sesiones previas a NY: Asia, Post-Asia, London, Post-London

    ny_with_context['high_before_ny'] = ny_with_context.apply(
        lambda row: max(
            block_daily[
                (block_daily['trading_date'] == row['trading_date']) &
                (block_daily['session'].isin(['Asia', 'Post-Asia', 'London', 'Post-London']))
            ]['block_high'].max(),
            row['daily_open']  # Al menos el open del día
        ),
        axis=1
    )

    ny_with_context['low_before_ny'] = ny_with_context.apply(
        lambda row: min(
            block_daily[
                (block_daily['trading_date'] == row['trading_date']) &
                (block_daily['session'].isin(['Asia', 'Post-Asia', 'London', 'Post-London']))
            ]['block_low'].min(),
            row['daily_open']
        ),
        axis=1
    )

    # ¿NY hizo nuevo high/low?
    ny_with_context['new_high'] = ny_with_context['block_high'] > ny_with_context['high_before_ny']
    ny_with_context['new_low'] = ny_with_context['block_low'] < ny_with_context['low_before_ny']

    # Identificar en qué bloque anterior se formó el high/low previo
    def find_session_of_high(row):
        before_blocks = block_daily[
            (block_daily['trading_date'] == row['trading_date']) &
            (block_daily['session'].isin(['Asia', 'Post-Asia', 'London', 'Post-London']))
        ]
        if len(before_blocks) == 0:
            return 'N/A'
        high_idx = before_blocks['block_high'].idxmax()
        return before_blocks.loc[high_idx, 'session']

    def find_session_of_low(row):
        before_blocks = block_daily[
            (block_daily['trading_date'] == row['trading_date']) &
            (block_daily['session'].isin(['Asia', 'Post-Asia', 'London', 'Post-London']))
        ]
        if len(before_blocks) == 0:
            return 'N/A'
        low_idx = before_blocks['block_low'].idxmin()
        return before_blocks.loc[low_idx, 'session']

    ny_with_context['session_of_high_before'] = ny_with_context.apply(find_session_of_high, axis=1)
    ny_with_context['session_of_low_before'] = ny_with_context.apply(find_session_of_low, axis=1)

    print("\nPROBABILIDAD DE NUEVO HIGH EN NY SEGÚN DÓNDE ESTABA EL HIGH PREVIO:")
    print()

    for session in ['Asia', 'Post-Asia', 'London', 'Post-London']:
        subset = ny_with_context[ny_with_context['session_of_high_before'] == session]
        if len(subset) > 0:
            new_highs = subset['new_high'].sum()
            prob = 100 * new_highs / len(subset)
            print(f"  High previo en {session}:")
            print(f"    Casos: {len(subset)}")
            print(f"    NY hizo nuevo high: {new_highs} ({prob:.1f}%)")
            print()

    print("\nPROBABILIDAD DE NUEVO LOW EN NY SEGÚN DÓNDE ESTABA EL LOW PREVIO:")
    print()

    for session in ['Asia', 'Post-Asia', 'London', 'Post-London']:
        subset = ny_with_context[ny_with_context['session_of_low_before'] == session]
        if len(subset) > 0:
            new_lows = subset['new_low'].sum()
            prob = 100 * new_lows / len(subset)
            print(f"  Low previo en {session}:")
            print(f"    Casos: {len(subset)}")
            print(f"    NY hizo nuevo low: {new_lows} ({prob:.1f}%)")
            print()

    return ny_with_context


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Cargar datos del PASO 2
    print("Cargando datos previos...")
    daily_stats = pd.read_csv(RESULTS_PATH / 'daily_stats.csv', parse_dates=['trading_date'])
    daily_stats = daily_stats.set_index('trading_date')
    daily_stats = daily_stats.rename(columns={'close': 'daily_close', 'open': 'daily_open'})

    block_daily = pd.read_csv(RESULTS_PATH / 'block_stats.csv', parse_dates=['trading_date'])

    # Ejecutar PASO 3
    ny_results = paso3_ny_analysis(daily_stats, block_daily)

    # Guardar resultados
    ny_results.to_csv(RESULTS_PATH / 'ny_analysis.csv', index=False)

    print("\n" + "=" * 80)
    print("✓ PASO 3 COMPLETADO - Resultados guardados en ny_analysis.csv")
    print("=" * 80)
