# Josh Models — assumptions.md

Decisiones de implementación donde el spec (`JOSH_EURUSD_2025_BACKTEST_SPEC.md` v1.0)
era ambiguo o no se podía cumplir con los datos disponibles. Fase actual: **solo
detectores + calendario diario**. La simulación de entradas vendrá tras la
auditoría del calendario.

## Datos y zona horaria
- Fuente: HistData M1 (`DAT_ASCII_EURUSD_M1_*.csv`). Timestamps ya en hora de
  Nueva York con DST (validado previamente en este repo contra las sesiones H4
  de TradingView). No se hace conversión.
- H1/M15/H4/D1 agregados desde M1. Vela H1 de la hora X = minutos [X:00, X:59].
- H4 en buckets FX (17, 21, 01, 05, 09, 13 NY), igual que el motor CISD del repo.

## Calendario económico — NO DISPONIBLE
- No hay `calendar.csv` en el repo. `news_0830` y `news_1000` van a `False` en
  todos los días y cada fila lleva la nota `news_unavailable`.
- El News Protocol está descrito pero **no aplicado**. Cuando haya calendario,
  se activará sin tocar los detectores.
- SMT: sin datos DXY/GBPUSD en esta fase → `smt_unavailable` (el spec lo permite).

## Ventanas y niveles
- Asia = 4 velas H1 de 20:00–23:59 NY de la tarde anterior (día natural anterior).
- LDNH/LDNL = extremos de 02:00–07:59 NY (la ventana por defecto del spec).
- PDH/PDL = día natural NY anterior **con datos** (retrocede hasta 4 días por
  festivos/fines de semana). Para el lunes, el "día anterior" es el domingo
  (solo 17:00–23:59); el spec pedía día natural anterior y así queda, aunque el
  rango del domingo es corto.
- D1 (para OSOK/TGIF y PDH/PDL) = día natural NY 00:00–23:59, no vela de 17:00.
- Apertura semanal = primer tick del domingo (17:00 NY).
- "Tomar" un nivel = extremo estrictamente más allá (`high > nivel` / `low < nivel`).
  No se exige que sea el primer toque del día (el spec no lo pide) — ver
  "Hallazgos" abajo.

## Confirmaciones
- **LR1**: confirmación fiel al spec = OB + desplazamiento tras el raid, buscada
  en los M15 de la hora del raid: tras el M15 que toma el nivel, un M15 cierra
  más allá del extremo del M15 del raid en la dirección del giro, y existe un
  M15 de color contrario previo (el OB; puede ser la propia vela del raid).
  Fallback sin M15: la vela H1 del raid cierra de vuelta dentro.
- **LR2.1**: "02:00 MUST confirm" = la vela de 02:00 cierra en la dirección del
  giro Y de vuelta al otro lado del nivel raideado. Niveles admitidos para el
  raid de 01:00: AH/AL y PDH/PDL ("prior swing" → PDH/PDL; no se buscan swings
  intradía arbitrarios).
- **Asia Model.1**: barrido de AH/AL en las horas 00:00–02:00 y la vela de
  02:00 cierra en la dirección del giro y de vuelta dentro del rango.
- **NY Reversal.1**: solo se exige cierre de vuelta dentro del nivel (el spec
  dice "closes back inside / shows rejection"); no se exige color de vela.
- **NY Reversal.2**: desplazamiento = H1 posterior al extremo (hasta 07:00) que
  cierra en la dirección del giro con cuerpo ≥ 50% de su rango y más allá del
  extremo de la vela previa. OB = última H1 de color contrario antes de esa vela.
- **LRLR**: existe si alguna H1 de 05:00–07:00 cierra contra la dirección del
  giro de Londres; el extremo del pullback = high/low máximo de esas tres horas.

## OSOK / TGIF
- OSOK causal: para mié–vie, `sign(cierre D1 del día anterior − apertura semanal)`.
  El spec dice `close[Wed]` pero usar el cierre del propio día al operar su
  mañana sería look-ahead; se usa el último cierre disponible. Lun–mar: None.
- El "override" de OSOK (toma del extremo semanal contrario con desplazamiento)
  NO está implementado en v1; anotado para v2.
- TGIF: lun–jue con ≥3 velas D1 en la misma dirección y el rango del jueves toca
  el high/low del miércoles o la apertura semanal.
- Asia Model.2 exige OSOK y que las 02:00 no hayan confirmado nada (ni ASIA1 ni
  un LR con confirmación en 02:00). Tal como está en el spec dispara casi todos
  los mié–vie sin confirmación; la prioridad lo relega, pero es muy frecuente.

## Estado del calendario (fase 1)
- `status` = `detected | no_model | conflict | no_session`. Los estados
  `traded / detected_no_fill` requieren la simulación (fase 2).
- `no_session` = faltan ≥2 horas núcleo (01:00–09:00) o no hay rango de Asia.
- `conflict` = NYC1 y NYR1 detectados el mismo día en direcciones opuestas.
  Otras competiciones (LR21+LR1+ASIA1 el mismo día) van en `notes`.
- LR2.2 detectado sin LR previo bloquea las continuaciones NY de ese día (spec).
- NYC2 solo aparece si LR1 y NYC1 existen ese día (aceptación del spec).

## Hallazgos para la auditoría (no decisiones, observaciones)
1. **Frecuencia**: con las reglas literales del spec, un modelo de Londres arma
   en ~92% de los días (LR1 161, LR21 79 de 259 operables). Londres rompe el
   rango de Asia casi a diario y la confirmación OB+desplazamiento en M15 casi
   siempre existe. Si Josh no opera a diario, el filtro real está fuera de estos
   detectores (OSOK/discrecional) o los raids exigen algo más (p. ej. primer
   toque, magnitud mínima del desplazamiento).
2. Los raids no exigen "primer toque": el 2025-03-05 las 00:00 ya habían tomado
   el AH y aun así el raid de las 03:00 arma LR1 corto contra un día
   fuertemente alcista.
3. LR21 con PDH/PDL incluidos es responsable de buena parte de sus 79 días.
   Si debe limitarse a AH/AL, es un cambio de una línea.
