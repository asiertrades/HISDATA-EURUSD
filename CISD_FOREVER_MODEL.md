# CISD H4 + Forever Model

Fusión del indicador que ya funciona (**CLAUDE CISD H4 v5**) con los módulos del
**Forever Model**, más un backtester en Python para medir resultados sobre los
M1 del repo antes de tocar nada.

Archivos:

| Archivo | Qué es |
|---|---|
| `CISD_ForeverModel.pine` | Indicador fusionado (Pine v6) para TradingView |
| `cisd_forever_backtest.py` | Backtester del mismo motor sobre `DAT_ASCII_EURUSD_M1_*.csv` |

---

## 1. Cómo se hizo la fusión

El motor de señales **no se toca**. El código v5 (reset 17:00 NY → barrido del
extremo de sesión → CISD tier A / tier B → correcciones) está copiado literal,
con los mismos inputs y los mismos defaults. Los módulos del Forever Model se
montan **por encima**, en tres capas:

1. **Capa de filtro** (`SMT`, `FVG HTF`): no altera la máquina de estados, solo
   decide si una señal ya generada se muestra/opera. Con los filtros en `Off`
   el script produce exactamente las mismas flechas que el original.
2. **Capa de gestión** (OB → SL → proyecciones → TP/ERL): convierte cada señal
   en una operación simulada y la sigue vela a vela.
3. **Capa de reporte** (marcadores de resultado + tabla de estadísticas +
   registro de operaciones): para poder contrastar con un calendario real.

### Qué se importó de cada script

| Del Forever Model | Cómo queda en la fusión |
|---|---|
| SMT con par correlacionado (tabla auto, 2º par, inverso) | Anclada a la sesión de las 17:00: hay SMT bajista si EURUSD barre el máximo de sesión y el par correlacionado no. Filtro `Off / Informar / Requerir SMT` |
| FVG del timeframe superior (caja, CE, mitigación, ERL) | FVG diario por defecto, con vida propia (mitigación + barrido de ERL lo mata). Filtro `Off / Informar / Señal dentro de FVG / FVG activo a favor` |
| Order Block + invalidación + proyecciones `+2 / +3` | El OB es el que ya usa el CISD (`_lBullO` / `_aBullO`…). El SL admite 3 modos y las proyecciones se dibujan sobre el riesgo real |
| ERL como objetivo | Modo de TP `ERL (extremo opuesto de la sesión)` y `ERL (FVG HTF)` |
| Marcadores de backtest (TP ◆ / SL ✕ / no-fill ◆) | Se pintan en la vela de cierre de cada operación simulada |
| Tabla informativa | Tabla de estadísticas por tier + registro de las últimas operaciones |

### Qué se dejó fuera y por qué

- Alineación LTF/HTF automática, bias, filtros horarios del Forever Model: el
  CISD ya define su propio calendario (velas de 21:00 / 01:00 / 05:00 NY) y
  mezclar ambos generaría dos relojes en conflicto.
- Los pivotes ICT multi-tier (ST/IT/LT) y el barrido interno de liquidez del
  Forever Model: en H4 con reset diario el "barrido" ya es el extremo de las
  17:00. Meter los tres tiers duplicaba la definición de liquidez.

---

## 2. Cómo probarlo en TradingView

1. Pega `CISD_ForeverModel.pine` en el Pine Editor → *Add to chart* en EURUSD H4.
2. **Primero valida la equivalencia**: con `Filtro SMT = Off` y `Filtro FVG = Off`
   las flechas deben coincidir una a una con las del indicador original.
3. Después activa un filtro cada vez y mira la tabla: `Ops`, `TP`, `WR`, `R`.
4. `Mostrar señales descartadas por los filtros` pinta en gris lo que el filtro
   ha quitado — es la forma rápida de ver si está cortando lo bueno o lo malo.

Notas de gestión (afectan solo a las estadísticas, no a las señales):

- **Entrada**: `Apertura vela de entrada` (mercado, como el original) o
  `Zona de retroceso (límite)` usando el mapa de percentiles del v5.
- **SL**: `Invalidación del mapa` (la línea roja discontinua), `Extremo de la
  vela CISD` o `Open del OB`.
- **TP**: múltiplo de R, ERL de sesión o ERL del FVG.

---

## 3. Backtester en Python

```bash
python3 cisd_forever_backtest.py --years 2025                 # lista de señales
python3 cisd_forever_backtest.py --years 2001-2025 --quiet    # solo el resumen
python3 cisd_forever_backtest.py --years 2025 --csv trades.csv
```

Opciones: `--fvg`, `--entry`, `--sl`, `--tp`, `--r`, `--max-bars`, `--tiers`,
`--single-trade`, `--hour9`, `--no-corr`, `--no-tierb`.

Detalles de implementación:

- Las velas H4 se construyen desde los M1 alineadas a la sesión FX
  (17, 21, 01, 05, 09, 13 NY), igual que TradingView. Los timestamps de HistData
  ya vienen en hora de Nueva York con DST (la apertura semanal cae siempre a las
  17:00), así que no hay conversión de zona horaria.
- La primera ejecución genera `h4_eurusd_cache.csv` (~50 s); a partir de ahí
  cada backtest tarda menos de un segundo.
- Por defecto **cada señal se evalúa por separado**. Con `--single-trade` se
  simula una sola operación a la vez, como se operaría en el gráfico.

### Referencia: 2001-2025, entrada a mercado, sin filtros

| SL | R objetivo | WR | R total |
|---|---|---|---|
| Invalidación del mapa | 1.5 | 40.7 % | −55.6 |
| Invalidación del mapa | 2.0 | 36.7 % | +13.6 |
| Invalidación del mapa | 3.0 | 33.6 % | +158.7 |
| Extremo vela CISD | 1.5 | 43.3 % | +25.5 |
| **Extremo vela CISD** | **2.0** | **40.8 %** | **+94.0** |
| Extremo vela CISD | 3.0 | 38.8 % | +131.9 |
| Open del OB | 2.0 | 32.2 % | −535.6 |

Filtro FVG diario sobre la misma base (SL mapa, R 2.0):

| Filtro | Señales operadas | WR | R total |
|---|---|---|---|
| Off | 4259 | 36.7 % | +13.6 |
| FVG activo a favor | 4121 | 37.0 % | +49.5 |
| Señal dentro de FVG | 1540 | 38.1 % | +45.6 |

2025 aislado (sin filtros, SL mapa, R 2.0): 181 señales — tier A 64, tier B 103,
correcciones 14. Ninguna señal en la vela de las 21:00 (entrada 01:00) porque el
tier B está vetado ahí y el tier A casi nunca llega a barrer y confirmar en la
segunda vela de la sesión.

### Limitación conocida

El filtro **SMT no se puede backtestear en local**: el repo solo tiene EURUSD y
la divergencia necesita el par correlacionado (GBPUSD o DXY). En TradingView sí
funciona en vivo. Si se añaden los M1 de GBPUSD al repo, el backtester puede
incorporarlo sin cambios de arquitectura.

---

## 4. Siguiente paso

Contrastar el calendario real de operaciones de 2025 con la salida de
`--years 2025 --csv trades.csv` para separar lo que el motor acierta de lo que
sobra, y ajustar filtros (SMT / FVG / horas / tier B) con esa referencia.
