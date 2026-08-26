# -*- coding: utf-8 -*-
"""Tests de los detectores con velas sinteticas (spec §9.4). Ejecutar:
    python3 josh_tests.py
"""
from datetime import date, datetime

from josh_models import (
    Bar, Niveles, detecta_asia1, detecta_asia2, detecta_lr1, detecta_lr21,
    detecta_lr22, detecta_lrlr, detecta_nyc1, detecta_nyc2, detecta_nyr1,
    detecta_nyr2,
)

F = date(2025, 6, 4)  # miercoles cualquiera


def bar(h, o, hi, lo, c):
    return Bar(datetime(2025, 6, 4, h), o, hi, lo, c)


def niveles(**kw):
    n = Niveles(F, asia_h=1.1000, asia_l=1.0950, pdh=1.1020, pdl=1.0930,
                ldn_h=1.1010, ldn_l=1.0940, apertura_semanal=1.0980)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


ok = fallos = 0
def check(nombre, cond):
    global ok, fallos
    if cond:
        ok += 1
    else:
        fallos += 1
        print(f"FALLO: {nombre}")


# ── LR2.1 ─────────────────────────────────────────────────────────
# 01:00 toma AH, 02:00 confirma (bajista y cierra bajo AH) -> corto, entrada 03
h1d = {1: bar(1, 1.0990, 1.1005, 1.0988, 1.1002),   # toma AH=1.1000
       2: bar(2, 1.1002, 1.1003, 1.0985, 1.0987)}   # bajista, cierra < AH
d = detecta_lr21(h1d, niveles())
check("LR21 corto detectado", d is not None and d.direccion == -1 and d.hora_entrada == 3)
check("LR21 SL = extremo raid", d is not None and abs(d.sl - 1.1005) < 1e-9)

# 02:00 NO confirma (cierra alcista) -> nada (aceptacion: LR2.1 nunca sin confirm 02:00)
h1d2 = {1: bar(1, 1.0990, 1.1005, 1.0988, 1.1002),
        2: bar(2, 1.1002, 1.1015, 1.1000, 1.1012)}
check("LR21 sin confirmacion de 02:00 no dispara", detecta_lr21(h1d2, niveles()) is None)

# ── LR1 ───────────────────────────────────────────────────────────
# 02:00 toma AH y cierra de vuelta dentro -> corto entrada 03:00, SL en AH
h1d = {2: bar(2, 1.0995, 1.1008, 1.0990, 1.0993)}
d = detecta_lr1(h1d, niveles(), [])
check("LR1 raid 02:00 -> entrada 03:00", d is not None and d.direccion == -1 and d.hora_entrada == 3)
check("LR1 SL en AH", d is not None and abs(d.sl - 1.1000) < 1e-9)

# 03:00 toma AL y cierra de vuelta dentro -> largo entrada 04:00
h1d = {3: bar(3, 1.0955, 1.0958, 1.0942, 1.0960)}
d = detecta_lr1(h1d, niveles(), [])
check("LR1 raid 03:00 -> entrada 04:00", d is not None and d.direccion == 1 and d.hora_entrada == 4)

# 03:00 toma AH SIN confirmar -> excepcion, entrada 04:00 (1er M15)
h1d = {3: bar(3, 1.0995, 1.1008, 1.0994, 1.1006)}  # cierra por encima de AH
d = detecta_lr1(h1d, niveles(), [])
check("LR1 excepcion 03:00 sin confirmar", d is not None and "excepcion" in d.notas and d.hora_entrada == 4)

# 02:00 toma AH sin confirmar -> nada (la excepcion es solo para 03:00)
h1d = {2: bar(2, 1.0995, 1.1008, 1.0994, 1.1006)}
check("LR1 02:00 sin confirmar no dispara", detecta_lr1(h1d, niveles(), []) is None)

# ── ASIA1 ─────────────────────────────────────────────────────────
# 00:00 barre AH, 02:00 confirma bajista bajo AH -> corto, SL = high de 02:00
h1d = {0: bar(0, 1.0990, 1.1004, 1.0988, 1.0996),
       1: bar(1, 1.0996, 1.0999, 1.0990, 1.0992),
       2: bar(2, 1.0992, 1.0997, 1.0980, 1.0982)}
d = detecta_asia1(h1d, niveles())
check("ASIA1 corto", d is not None and d.direccion == -1 and d.hora_entrada == 3)
check("ASIA1 SL = extremo 02:00", d is not None and abs(d.sl - 1.0997) < 1e-9)

# sin barrido de Asia -> nada
h1d = {0: bar(0, 1.0990, 1.0995, 1.0988, 1.0992),
       2: bar(2, 1.0992, 1.0994, 1.0980, 1.0982)}
check("ASIA1 sin barrido no dispara", detecta_asia1(h1d, niveles()) is None)

# ── ASIA2 ─────────────────────────────────────────────────────────
d = detecta_asia2({}, niveles(), None)
check("ASIA2 sin OSOK nunca dispara", d is None)  # aceptacion del spec
d = detecta_asia2({}, niveles(), -1)
check("ASIA2 corto con OSOK, SL en AH", d is not None and abs(d.sl - 1.1000) < 1e-9)

# ── LR2.2 ─────────────────────────────────────────────────────────
h1d = {4: bar(4, 1.0955, 1.0958, 1.0945, 1.0952)}  # toma AL
d = detecta_lr22(h1d, niveles())
check("LR22 largo tras raid AL 04:00", d is not None and d.direccion == 1)

# ── NYR2 ──────────────────────────────────────────────────────────
# alto del dia a las 05:00, desplazamiento bajista a las 06:00 con OB previo
h1d = {3: bar(3, 1.0970, 1.0980, 1.0968, 1.0978),   # alcista (OB)
       4: bar(4, 1.0978, 1.0990, 1.0976, 1.0988),   # alcista
       5: bar(5, 1.0988, 1.1012, 1.0986, 1.0995),   # alto del dia
       6: bar(6, 1.0995, 1.0996, 1.0975, 1.0977),   # desplaz.: bajista, cierra < low de 05
       7: bar(7, 1.0977, 1.0983, 1.0972, 1.0975)}
d = detecta_nyr2(h1d, niveles())
check("NYR2 corto entrada 08:00", d is not None and d.direccion == -1 and d.hora_entrada == 8)
check("NYR2 SL sobre 07:00", d is not None and abs(d.sl - 1.0983) < 1e-9)

# extremo a las 03:00 -> no dispara
h1d2 = dict(h1d)
h1d2[3] = bar(3, 1.0970, 1.1020, 1.0968, 1.0978)
check("NYR2 extremo fuera de 05-07 no dispara", detecta_nyr2(h1d2, niveles()) is None)

# ── LRLR + NYC1 ───────────────────────────────────────────────────
from josh_models import Deteccion
ldn = Deteccion("LR1", -1, 3, 1.1000, 1.1000, "raid AH 02:00")
# Londres: extremo (alto) a las 02:00-04:00; pullback alcista a las 06:00
h1d = {2: bar(2, 1.0995, 1.1008, 1.0990, 1.0993),
       3: bar(3, 1.0993, 1.0995, 1.0975, 1.0978),
       4: bar(4, 1.0978, 1.0980, 1.0965, 1.0968),
       5: bar(5, 1.0968, 1.0972, 1.0962, 1.0966),
       6: bar(6, 1.0966, 1.0979, 1.0964, 1.0975),   # pullback alcista fuera de KZ
       7: bar(7, 1.0975, 1.0977, 1.0968, 1.0970)}
existe, pb = detecta_lrlr(h1d, -1)
check("LRLR detectado", existe and abs(pb - 1.0979) < 1e-9)
d = detecta_nyc1(h1d, niveles(ldn_h=1.1008), ldn)
check("NYC1 corto entrada 08:00", d is not None and d.direccion == -1 and d.hora_entrada == 8)

# sin pullback (todo bajista 05-07) -> NYC1 no dispara
h1d2 = dict(h1d)
h1d2[6] = bar(6, 1.0966, 1.0968, 1.0955, 1.0958)
check("NYC1 sin LRLR no dispara", detecta_nyc1(h1d2, niveles(ldn_h=1.1008), ldn) is None)

# extremo de Londres a las 05:00+ -> no dispara
h1d3 = dict(h1d)
h1d3[5] = bar(5, 1.0968, 1.1015, 1.0962, 1.0966)
check("NYC1 extremo Londres tardio no dispara", detecta_nyc1(h1d3, niveles(ldn_h=1.1015), ldn) is None)

# ── NYR1 ──────────────────────────────────────────────────────────
h1d = {8: bar(8, 1.1000, 1.1014, 1.0998, 1.1004)}  # toma LDNH=1.1010, cierra dentro
d = detecta_nyr1(h1d, niveles())
check("NYR1 corto raid 08:00 -> entrada 09:00", d is not None and d.direccion == -1 and d.hora_entrada == 9)
h1d = {9: bar(9, 1.0950, 1.0952, 1.0935, 1.0946)}  # toma LDNL, cierra dentro
d = detecta_nyr1(h1d, niveles())
check("NYR1 largo raid 09:00 -> entrada 10:00", d is not None and d.direccion == 1 and d.hora_entrada == 10)
# raid sin cierre de vuelta dentro -> nada
h1d = {8: bar(8, 1.1000, 1.1014, 1.0998, 1.1012)}
check("NYR1 sin rechazo no dispara", detecta_nyr1(h1d, niveles()) is None)

# ── NYC2 ──────────────────────────────────────────────────────────
nyc1 = Deteccion("NYC1", -1, 8, 1.1008, 1.0979, "")
check("NYC2 requiere LR1+NYC1", detecta_nyc2(None, nyc1, False) is None)   # aceptacion
check("NYC2 no con LR21", detecta_nyc2(Deteccion("LR21", -1, 3, 1.1, None, ""), nyc1, False) is None)
d = detecta_nyc2(ldn, nyc1, False)
check("NYC2 dispara con LR1+NYC1, 0.5R", d is not None and "0.5R" in d.notas)

import sys

# ── confirmacion OB + desplazamiento (M15) para LR1 ───────────────
from josh_models import _confirma_ob_desplaz

def m15(h, m, o, hi, lo, c):
    return Bar(datetime(2025, 6, 4, h, m), o, hi, lo, c)

# corto sobre AH=1.1000: 02:15 toma el nivel, 02:45 desplaza bajo el low del raid,
# con un M15 alcista previo (OB)
velas = [m15(2, 0, 1.0990, 1.0996, 1.0988, 1.0995),   # alcista -> OB
         m15(2, 15, 1.0995, 1.1004, 1.0993, 1.0999),  # raid
         m15(2, 30, 1.0999, 1.1002, 1.0994, 1.0996),
         m15(2, 45, 1.0996, 1.0997, 1.0988, 1.0990)]  # bajista, cierra < 1.0993
check("OB+desplaz corto confirma", _confirma_ob_desplaz(velas, 1.1000, -1))

# sin desplazamiento (nada cierra bajo el low del raid) -> no confirma
velas2 = velas[:3] + [m15(2, 45, 1.0996, 1.0999, 1.0994, 1.0995)]
check("sin desplazamiento no confirma", not _confirma_ob_desplaz(velas2, 1.1000, -1))

# desplazamiento sin OB previo (todo bajista antes) -> no confirma
# nota: la vela del raid puede ser ella misma el OB; para anular el OB, todas
# las velas previas al desplazamiento (raid incluido) deben ser bajistas
velas3 = [m15(2, 0, 1.0996, 1.0997, 1.0989, 1.0990),  # bajista
          m15(2, 15, 1.0999, 1.1004, 1.0988, 1.0992), # raid con mecha, cierra bajista
          m15(2, 45, 1.0992, 1.0993, 1.0984, 1.0986)] # desplaz.
check("sin OB previo no confirma", not _confirma_ob_desplaz(velas3, 1.1000, -1))

# largo espejo sobre AL=1.0950
velasL = [m15(3, 0, 1.0960, 1.0962, 1.0953, 1.0955),  # bajista -> OB
          m15(3, 15, 1.0955, 1.0957, 1.0946, 1.0951), # raid AL
          m15(3, 30, 1.0951, 1.0960, 1.0950, 1.0959)] # alcista, cierra > high raid
check("OB+desplaz largo confirma", _confirma_ob_desplaz(velasL, 1.0950, 1))

print(f"total: {ok} OK, {fallos} fallos")
sys.exit(1 if fallos else 0)
