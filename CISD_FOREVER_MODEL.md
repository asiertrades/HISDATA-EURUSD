# CISD H4 + Forever Model

Fusión del indicador que ya funciona (**CLAUDE CISD H4 v5**) con los módulos del
**Forever Model**, más un backtester en Python para medir resultados sobre los
M1 del repo antes de tocar nada.

Archivos:

| Archivo | Qué es |
|---|---|
| `CISD_ForeverModel.pine` | Indicador fusionado (Pine v6) para TradingView |
| `cisd_forever_backtest.py` | Backtester del mismo motor sobre `DAT_ASCII_EURUSD_M1_*.csv` |
| `cisd_m1_sim.py` | Simulación de las operaciones a resolución de minuto |
| `analisis_calendario.py` | Cruce con el calendario real de 2025 |
| `forever_model_engine.py` | Las entradas *propias* del Forever Model, portadas a Python |
| `correlacion_cisd_forever.py` | Cruce entre las entradas de los dos motores |
| `unicorn_engine.py` | Motor del Unicorn Model (M5 / M15) portado a Python |
| `ltf_bars.py` | Velas M5 / M15 con caché, a partir de los M1 |
| `combo_cisd_unicorn.py` | **CISD H4 para la dirección + Unicorn M15 para la entrada** |
| `anticipacion.py` | ¿Se puede adelantar la señal dentro de la vela, y con cuánto ruido? |
| `calendario_trades_2025.csv` | El calendario del Excel, una fila por marca |

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

## 4. Calibración con el calendario real de 2025

El calendario del Excel trae **208 marcas** (115 ✓, 64 ✕, 29 vetadas por
noticias/festivos). Las horas de las casillas son la **vela de entrada** en
hora de Nueva York y el tier C son las correcciones.

### 4.1 Qué reproduce el motor

| | |
|---|---|
| Marcas del calendario | 208 (≈202 huecos únicos fecha+hora+dirección) |
| Señales del motor en 2025 | 181 |
| Coinciden fecha + hora + dirección | **144** |
| Solo en el calendario | 58 |
| Solo en el motor | 37 |

El grueso encaja. Las diferencias tienen tres causas y ninguna es un fallo de
la lógica:

- **Tier A vs B baila en ~34 señales.** Son casos límite de "vela limpia": el
  feed de TradingView y los M1 de HistData discrepan por décimas en el body
  ratio y la señal cae de un lado o del otro. La señal existe en ambos, cambia
  la etiqueta.
- **Las 7 entradas de la 01:00** del calendario no las genera el motor con
  estos datos: implicarían una señal en la vela de las 21:00 barriendo el
  extremo contrario al que marca la dirección. Son reconstrucciones del Excel,
  no salidas del indicador.
- **Correcciones**: el calendario tiene 33 y el motor 14. El Excel ya avisa de
  "12 correcciones fantasma".

### 4.2 Qué es realmente una marca ✓

Midiendo la excursión real minuto a minuto durante las 24 h siguientes:

| | excursión favorable (mediana) | adversa (mediana) | adversa (p75) |
|---|---|---|---|
| ✓ ganadoras (n=89) | **41.7 p** | 20.2 p | 32.6 p |
| ✕ perdedoras (n=48) | 14.3 p | 48.4 p | 76.7 p |

Una ✓ es un movimiento de ~40 pips a favor tolerando ~20 en contra. Con un stop
de 10 pips medido desde el cierre de la vela H4 morirían casi todas: **el valor
está en afinar la entrada en M15**, no en entrar al cierre. Ninguna regla
mecánica fija reproduce el 64 % del calendario; la que más se le acerca (81 % de
coincidencia) es "+20 p antes que −40 p".

### 4.3 Filtros: qué separa las ✓ de las ✕

Sobre las 137 señales del motor que el calendario etiqueta (acierto base 65 %):

| Filtro | señales que deja | acierto |
|---|---|---|
| sin filtro | 100 % | 65.0 % |
| cuerpo del CISD >= 20 p | 65 % | 71.9 % |
| cuerpo del CISD >= 30 p | 34 % | 78.7 % |
| cuerpo/rango >= 0.60 | 55 % | 76.3 % |
| mecha en contra < 0.5 × cuerpo | 72 % | 70.4 % |
| **cuerpo >= 20 p + ratio >= 0.50 + exceso del barrido <= 8 p** | **38 %** | **80.8 %** |

Por celdas: **09h en largo es la peor** (44 %, n=27) frente a 05h en corto
(76 %); los días de **BCE** rinden 29 % (n=7, muestra corta pero coherente con
tus vetos manuales); y a mayor profundidad del barrido sobre el extremo de las
17:00, peor resultado (>15 p → 50 %).

### 4.4 Validación fuera de muestra (2001-2024, resolución M1)

Entrada a mercado en la vela de entrada, SL 20 p, TP 3R, 4078 señales:

| Filtro | ops | WR | R/operación |
|---|---|---|---|
| sin filtro | 4078 | 32.2 % | +0.067 |
| cuerpo >= 20 p | 2910 | 31.0 % | +0.063 |
| ratio >= 0.50 | 3051 | 31.8 % | +0.054 |
| **exceso del barrido <= 8 p** | 2449 | 33.6 % | **+0.103** |
| **calibrado (20 p + 0.50 + exc 8 p)** | 1538 | 32.3 % | **+0.094** |
| estricto (25 p + 0.60 + mecha + exc 15 p) | 1286 | 31.4 % | +0.062 |

Conclusión honesta: **el único filtro que mejora la esperanza mecánica en 24
años es el del barrido superficial**. Los umbrales de cuerpo y ratio suben el
*acierto* (que es lo que miden tus marcas, porque entras afinado en M15) pero
no la R por operación: seleccionan velas más grandes, que exigen stops más
anchos. El combinado gana en ambos terrenos: 81 % de acierto en tus marcas y
+40 % de esperanza sobre la base en 24 años, a cambio de quedarse con ~38 % de
las señales (≈66 al año en vez de 181).

### 4.5 Parámetros aplicados

El indicador trae el grupo **"Filtro de calidad"** activado con esos valores:

| Input | Valor |
|---|---|
| Activar filtro de calidad | ON |
| Cuerpo mínimo del CISD | 20 pips |
| Cuerpo / rango mínimo | 0.50 |
| Mecha en contra máx. | 9.99 (desactivado — sube el acierto pero baja la R) |
| Exceso máx. del barrido | 8 pips |

**Apagando el interruptor el indicador vuelve exactamente al comportamiento del
original.** En el backtester el filtro va apagado por defecto; se activa con
`--calidad`.

Lo que **no** se ha tocado, a propósito:

- **Vetar los largos de las 09:00** y **operar solo cortos**: en 2025 (año de
  tendencia alcista clara) los cortos aciertan 74 % y los largos 54 %, pero en
  24 años esa asimetría desaparece (R/op +0.007 para solo-cortos). Es sesgo de
  un año, no una regla.
- **Vetar días de BCE/CPI**: con n=7 no se sostiene un umbral, y el indicador
  no tiene calendario macro. Sigue siendo un veto manual tuyo.

---

## 5. ¿Cuadran las entradas del CISD con las del Forever Model?

`forever_model_engine.py` porta el motor completo del Forever Model (FVG diario →
pivotes ICT por tiers → barrido → order block → confirmación → entrada al volver
al OB) con LTF = H4 y HTF = diario, que es la alineación comparable con el CISD.
**Sin la puerta SMT**, que necesitaría el par correlacionado: sin ella el modelo
dispara más de la cuenta, así que el solape medido es un techo.

### 5.1 No cuadran

| | 2025 | 2001-2025 |
|---|---|---|
| Entradas CISD | 181 | 4358 |
| Entradas Forever Model | 36 | 1228 |
| Misma vela y dirección | 1 (0.6 %) | 19 (0.4 %) |
| Misma sesión y dirección | 13 (7.2 %) | 414 (9.7 %) |
| El Forever Model dice lo contrario | 17 (9.4 %) | 423 (9.9 %) |
| Entradas del Forever Model con un CISD equivalente | 36 % | 34 % |

La razón es estructural y se ve en el reparto horario: el CISD solo entra en las
velas de las 05:00 y 09:00 (2127 y 1941 de 4358), mientras que el Forever Model
reparte sus entradas por las seis velas del día (262 a la 01:00, 226 a las 17:00,
223 a las 13:00…). Son modelos distintos: el CISD reacciona al barrido del extremo
de la sesión a una hora fija; el Forever Model espera a que el precio vuelva a un
order block dentro de un FVG diario, y eso ocurre cuando ocurre.

### 5.2 La trampa: la confluencia "mata" las señales… pero es una tautología

Cruzando sin cuidado sale un efecto espectacular: las señales del CISD que
coinciden con una entrada del Forever Model en la misma dirección rinden
−0.297 R/op frente a +0.029 de la base, y en la coincidencia exacta de vela
**pierden 19 de 19**. Estable en los tres periodos y superviviente al filtro de
calidad. Sobre las marcas de 2025: 9 % de acierto contra 70 %.

Es un espejismo. El Forever Model entra con orden límite: que su OB se llene en
la misma vela en la que entra el CISD, y en el mismo sentido, significa que el
precio se ha ido en contra de la entrada. Se está midiendo el resultado con
información de la propia operación.

Restringiendo a lo que se sabe **antes** de entrar, el efecto desaparece:

| Ventana (solo velas anteriores a la entrada) | n | WR | R/op |
|---|---|---|---|
| todas | 4259 | 40.8 % | +0.022 |
| OB llenado en las 3 velas previas, misma dirección | 147 | 45.6 % | +0.087 |
| OB llenado en las 6 velas previas, misma dirección | 356 | 39.3 % | −0.014 |
| OB llenado en las 6 previas, dirección contraria | 412 | 40.0 % | +0.035 |

Ni confirma ni veta. **Las entradas del Forever Model no sirven como filtro del
CISD**, ni a favor ni en contra.

### 5.3 El Forever Model por su cuenta

Con proyección 2R y SL en el extremo del order block, 2001-2025: 1228 entradas
(49 al año), 32.2 % de acierto, −0.035 R por operación. Esto **no es un veredicto
sobre el modelo**: le falta justo la pieza que selecciona, la divergencia SMT.
Medirlo de verdad exige meter GBPUSD o DXY en el repo.

---

## 6. CISD H4 + Unicorn M15: probado y descartado

> **Corrección.** Una primera versión de este apartado daba +0.494 R netos por
> operación y 21 de 21 años en positivo. Era falso: el simulador tenía un fallo
> que se describe en 6.4. Con él arreglado, la combinación **pierde dinero**.
> Los números de abajo son los corregidos.

La idea: el CISD H4 da dirección y ventana horaria, y el Unicorn en M15 da la
entrada afinada — retesteo del breaker con el stop en su extremo, 5-6 pips de
riesgo en vez de los 35 de la invalidación H4.

`unicorn_engine.py` porta el modelo (barrido de liquidez → breaker → activación
por cierre a través de la zona → FVG solapado) sobre velas M15 construidas desde
los M1. Fuentes de liquidez: máximo/mínimo de la H4 previa y del día previo,
extremos de sesión (Asia, Londres, NY AM, NY PM) y pivotes swing del propio M15.

Lo que sí es cierto y sigue en pie: **la altura mediana del breaker M15 es de
8.9 pips**, el mismo riesgo que reporta la hoja de estadísticas del calendario.
El mecanismo es el que se opera a mano. Lo que no aguanta es el resultado.

### 6.1 Resultado corregido, 2005-2025

Entrada en la mitad del breaker, SL al extremo opuesto +1 pip, TP 1.5R, riesgo
mínimo 4 pips, coste de 1 pip, simulación minuto a minuto:

| | |
|---|---|
| Operaciones | 1397 |
| Riesgo mediano | 5.5 pips |
| Acierto | 41.7 % |
| R/operación | +0.042 bruto · **−0.159 neto** |
| Años en positivo | **2 de 21** (2011 y 2013) |

En bruto apenas empata; el coste de ejecución lo hunde. Con el filtro de calidad
del CISD encima mejora algo (−0.121) pero sigue en negativo.

### 6.2 El CISD sí aporta, pero sobre una base perdedora

2015-2025, mismas reglas de entrada:

| | ops | WR | R/op bruto | neto |
|---|---|---|---|---|
| Unicorn M15 solo, a cualquier hora | 7326 | 40.1 % | +0.001 | −0.241 |
| con señal CISD en la misma dirección y ventana | 1255 | 46.4 % | +0.160 | −0.069 |
| sin CISD alrededor | 6071 | 38.8 % | −0.032 | −0.277 |

El filtro del CISD vale unos +0.17 R por operación — es real y consistente. El
problema es que el punto de partida (el Unicorn suelto con stops de 4-5 pips)
está tan por debajo de cero que no basta.

### 6.3 En M5 es peor

`--tf 5` añade la H1 como fuente de liquidez (el mapeo automático de un gráfico
de 5 minutos). 2019-2025, 1244 señales CISD:

| Configuración | ops | fill | riesgo | WR | bruto | neto |
|---|---|---|---|---|---|---|
| M15, setup desde la vela CISD | 290 | 23 % | 5.9 p | 39.0 % | −0.026 | −0.195 |
| M15, solo tras el cierre H4 | 51 | 4 % | 5.9 p | 45.1 % | +0.127 | −0.033 |
| M5, solo tras el cierre H4 | 181 | 15 % | 5.5 p | 35.9 % | −0.102 | −0.277 |
| M5, tras el cierre, sin mínimo de riesgo | 433 | 35 % | 3.7 p | 41.1 % | +0.031 | −0.244 |
| M5, setup desde la vela CISD | 256 | 21 % | 5.4 p | 48.8 % | +0.218 | **+0.039** |

El breaker de M5 mide 4.3 pips de mediana (p25 2.8 · p75 6.7) frente a 8.9 en
M15: entrando en su mitad quedan 2-3 pips de riesgo y un pip de spread se lleva
toda la ventaja. La única casilla que sobrevive a cero es la última, y por poco.

### 6.4 El fallo, porque merece quedar escrito

El simulador recibía la vela M15 en la que el precio tocaba el límite y empezaba
a vigilar stop y objetivo **desde el principio de esa vela**, sin esperar al
minuto del llenado. Con órdenes límite eso es letal: en un corto, el límite está
por encima del precio, y dentro de esa misma vela el precio suele bajar primero
(hacia el objetivo) y subir después (hasta el límite). El simulador apuntaba un
objetivo alcanzado antes de estar dentro.

Con objetivos de 8 pips (1.5R sobre 5 pips de riesgo) y velas M15 que se mueven
40 pips en NFP, el fantasma aparecía constantemente. Corregido —buscar primero
el minuto del llenado y vigilar salidas solo a partir de ahí—, 2025 pasó de
+0.169 a −0.175 y el histórico de +0.494 a −0.159.

El resto del repo no está afectado: el motor CISD y su validación entran a
mercado en la apertura de la vela, donde el problema no existe, y el análisis de
anticipación del apartado 7 solo cuenta señales, no simula operaciones.

### 6.5 Qué queda vivo de esta línea

- **El diagnóstico del calendario sigue en pie**: el breaker M15 mide lo mismo
  que el stop real, así que el mecanismo es el correcto. Lo que falla es esta
  forma concreta de mecanizarlo.
- **El CISD como filtro de dirección vale +0.17 R** sobre el Unicorn suelto.
- Para que la idea funcione haría falta o bien un coste de ejecución muy por
  debajo de 1 pip, o bien entradas con más recorrido: objetivos mayores que 1.5R
  sobre stops de 5 pips no se sostienen contra el spread.

## 7. Anticipar la señal dentro de la vela: cuánto cuesta en ruido

`anticipacion.py` evalúa la señal CISD como si la vela H4 cerrase en cada una de
sus 16 velas M15 ("señal provisional") y la contrasta con lo que ocurre de
verdad al cierre. Tres resultados posibles por vela y dirección:

- **anticipada y confirmada** → adelanto limpio
- **anticipada y no confirmada** → ruido: una señal falsa que hoy no existe
- **confirmada sin anticipar** → no se podía adelantar

Adelantarse a lo bruto no sale gratis: en 2025 caza el 92 % de las señales pero
mete 157 falsas, una por cada buena. Con tres palancas —exigir setup Unicorn
M15, esperar a la última hora de la vela, y exigir que la vela provisional ya
cumpla el filtro de calidad— la cosa cambia (2015-2025, 1794 señales reales):

| Variante | anticipadas | cobertura | ruido | fiabilidad | adelanto |
|---|---|---|---|---|---|
| sin filtros | 1779 | 99 % | 1758 | 50.3 % | 135 min |
| última hora | 1756 | 98 % | 675 | 72.2 % | 45 min |
| última hora + calidad | 1122 | 63 % | 192 | 85.4 % | 45 min |
| **última hora + calidad + Unicorn** | **942** | **53 %** | **141** | **87.0 %** | 45 min |

La última fila son **13 señales falsas al año** a cambio de adelantar algo más
de la mitad de las señales unos 45 minutos. En 2025 aislado: 78 anticipadas y
12 falsas.

El precio del adelanto es la cobertura: cuanto más tarde se dispara y más
exigente es el filtro, menos ruido y menos señales se cazan. Lo que **no** se
puede es adelantarse mucho (135 min) y no ensuciar: a mitad de vela la
información todavía no está.

Pendiente de medir: qué resultado dan esas operaciones falsas. 13 al año pueden
ser inofensivas o pueden comerse la ventaja del adelanto; hasta simularlas con
la misma regla de entrada, el balance neto de anticipar no está cerrado.

---

## 8. Siguiente paso

- Pegar el indicador en TradingView y comprobar que con "Filtro de calidad" OFF
  las flechas son las del original; luego activarlo y ver la tabla.
- Añadir los M1 de GBPUSD (o DXY) al repo: desbloquea el filtro SMT del
  indicador y la evaluación honesta del Forever Model como sistema propio.
- Si la combinación con el Unicorn convence, el paso natural es llevar la regla
  de entrada (BB 50 % + stop al extremo + 4 pips mínimos) al propio indicador
  fusionado, para no depender de dos scripts en dos gráficos.
- Simular las operaciones de las señales falsas del adelanto (13 al año con la
  variante estricta) para cerrar el balance neto de anticipar.
