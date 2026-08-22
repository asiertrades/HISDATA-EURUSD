#!/usr/bin/env python3
"""
Motor del Unicorn Model portado a Python, para timeframes bajos (M5 / M15).

Secuencia del modelo:

    barrido de liquidez  →  breaker (racha de velas en el último pivote)
    →  activación: cierre a través del breaker
    →  entrada: retesteo del borde de la zona
    →  invalidación: extremo opuesto del breaker  (o extremo de la manipulación)

"Unicorn" = el breaker se solapa con un FVG formado entre el barrido y la
activación. Sin ese solape el setup es un breaker a secas.

Fuentes de liquidez implementadas (las del mapeo automático para M15):
    · máximo/mínimo de la vela H4 anterior
    · máximo/mínimo del día anterior (sesión FX 17:00→17:00)
    · máximos/mínimos de sesión: Asia, Londres, NY AM, NY PM
    · pivotes swing (3,3) del propio timeframe
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

PIP = 0.0001
SESSIONS = {                      # hora de Nueva York
    "Asia":   (20, 0, 24, 0),
    "London": (2, 0, 5, 0),
    "NY AM":  (9, 30, 12, 0),
    "NY PM":  (13, 30, 16, 0),
}


@dataclass
class Level:
    price: float
    is_high: bool
    label: str
    born: datetime


@dataclass
class Setup:
    is_bull: bool
    is_unicorn: bool
    sweep_label: str
    sweep_level: float
    sweep_t: datetime
    zone_top: float
    zone_bot: float
    manip_extreme: float
    activation_t: datetime
    activation_close: float
    entry: float
    entry_t: datetime | None = None
    sl: float = 0.0
    tp: float = 0.0
    result: str = ""
    r: float = 0.0
    exit_t: datetime | None = None


def _in_session(t: datetime, name: str) -> bool:
    h1, m1, h2, m2 = SESSIONS[name]
    mins = t.hour * 60 + t.minute
    a, b = h1 * 60 + m1, h2 * 60 + m2
    return a <= mins < b


def _pivots(bars, i: int, length: int = 3):
    """Pivote confirmado en la vela i-length (equivale a ta.pivothigh/low(3,3))."""
    k = i - length
    if k - length < 0:
        return None, None
    win = bars[k - length:k + length + 1]
    hi = bars[k].h if all(bars[k].h >= x.h for x in win) else None
    lo = bars[k].l if all(bars[k].l <= x.l for x in win) else None
    return hi, lo


def _breaker(bars, i: int, pivot_idx: int, is_bull: bool):
    """Racha de velas del mismo signo que termina en el pivote (f_findBullBB/BearBB)."""
    if pivot_idx is None or pivot_idx < 0 or pivot_idx >= i:
        return None, None
    top = bot = None
    j = pivot_idx
    n = 0
    while j >= 0 and n < 9:
        b = bars[j]
        same = (b.c > b.o) if is_bull else (b.c < b.o)
        if same:
            top = b.h if top is None else max(top, b.h)
            bot = b.l if bot is None else min(bot, b.l)
            n += 1
            j -= 1
        else:
            break
    if top is None:                       # sin racha: la propia vela del pivote
        top, bot = bars[pivot_idx].h, bars[pivot_idx].l
    return top, bot


def _fvg_overlap(bars, start_i: int, end_i: int, top: float, bot: float, is_bull: bool) -> bool:
    """¿Hay un FVG de 3 velas, entre el barrido y la activación, que solape el breaker?"""
    for k in range(max(start_i + 2, 2), end_i + 1):
        if is_bull and bars[k].l > bars[k - 2].h:
            ft, fb = bars[k].l, bars[k - 2].h
        elif not is_bull and bars[k].h < bars[k - 2].l:
            ft, fb = bars[k - 2].l, bars[k].h
        else:
            continue
        if ft >= bot and fb <= top:
            return True
    return False


def find_setups(bars, h4_bars=None, max_bars_after_sweep: int = 25,
                unicorn_only: bool = True, use_swings: bool = True):
    """Recorre las velas LTF y devuelve los setups activados."""
    idx_by_t = {b.t: i for i, b in enumerate(bars)}
    setups: list[Setup] = []

    # ── niveles de referencia H4 y diarios
    h4_levels: list[tuple[datetime, float, float]] = []
    if h4_bars:
        for k in range(1, len(h4_bars)):
            h4_levels.append((h4_bars[k].t, h4_bars[k - 1].h, h4_bars[k - 1].l))
    h4_at = {t: (hi, lo) for t, hi, lo in h4_levels}

    live: list[Level] = []
    cur_h4 = None
    prev_day = None
    day_hi = day_lo = None
    day_key = None
    sess_state: dict[str, list] = {k: [None, None, None] for k in SESSIONS}  # hi, lo, activa

    # constructor pendiente por dirección
    bld = {True: None, False: None}       # True = alcista

    last_piv_hi_idx = last_piv_lo_idx = None

    for i, b in enumerate(bars):
        # ── nueva vela H4: el máximo/mínimo de la anterior pasa a ser liquidez
        if b.t in h4_at:
            hi, lo = h4_at[b.t]
            cur_h4 = (hi, lo)
            live = [x for x in live if x.label != "H4"]
            live.append(Level(hi, True, "H4", b.t))
            live.append(Level(lo, False, "H4", b.t))

        # ── nueva sesión diaria (17:00 NY)
        k_day = (b.t - timedelta(hours=17)).date()
        if k_day != day_key:
            if day_hi is not None:
                prev_day = (day_hi, day_lo)
                live = [x for x in live if x.label != "1D"]
                live.append(Level(day_hi, True, "1D", b.t))
                live.append(Level(day_lo, False, "1D", b.t))
            day_key, day_hi, day_lo = k_day, b.h, b.l
        else:
            day_hi, day_lo = max(day_hi, b.h), min(day_lo, b.l)

        # ── sesiones intradía
        for name in SESSIONS:
            st = sess_state[name]
            inside = _in_session(b.t, name)
            if inside:
                if not st[2]:
                    st[0], st[1], st[2] = b.h, b.l, True
                else:
                    st[0], st[1] = max(st[0], b.h), min(st[1], b.l)
            elif st[2]:
                st[2] = False
                live.append(Level(st[0], True, name, b.t))
                live.append(Level(st[1], False, name, b.t))

        # ── pivotes swing del propio TF
        if use_swings:
            ph, pl = _pivots(bars, i)
            if ph is not None:
                last_piv_hi_idx = i - 3
                live.append(Level(ph, True, "Swing", b.t))
            if pl is not None:
                last_piv_lo_idx = i - 3
                live.append(Level(pl, False, "Swing", b.t))
        else:
            ph, pl = _pivots(bars, i)
            if ph is not None:
                last_piv_hi_idx = i - 3
            if pl is not None:
                last_piv_lo_idx = i - 3

        live = [x for x in live if (b.t - x.born) < timedelta(days=5)]

        # ── barridos
        for is_bull in (True, False):
            hit = None
            for lv in list(live):
                if is_bull and not lv.is_high and b.l <= lv.price:
                    hit = lv
                    live.remove(lv)
                elif (not is_bull) and lv.is_high and b.h >= lv.price:
                    hit = lv
                    live.remove(lv)
                if hit is not None:
                    break
            if hit is None:
                continue
            piv = last_piv_hi_idx if is_bull else last_piv_lo_idx
            top, bot = _breaker(bars, i, piv, is_bull)
            if top is None:
                continue
            bld[is_bull] = dict(sweep_i=i, level=hit.price, label=hit.label,
                                top=top, bot=bot,
                                manip=b.l if is_bull else b.h)

        # ── caducidad y activación
        for is_bull in (True, False):
            st = bld[is_bull]
            if st is None:
                continue
            if i - st["sweep_i"] > max_bars_after_sweep:
                bld[is_bull] = None
                continue
            if i <= st["sweep_i"]:
                continue
            st["manip"] = min(st["manip"], b.l) if is_bull else max(st["manip"], b.h)
            activa = (b.c > st["top"] and b.c > b.o) if is_bull else (b.c < st["bot"] and b.c < b.o)
            if not activa:
                continue
            uni = _fvg_overlap(bars, st["sweep_i"], i, st["top"], st["bot"], is_bull)
            if unicorn_only and not uni:
                bld[is_bull] = None
                continue
            setups.append(Setup(
                is_bull=is_bull, is_unicorn=uni, sweep_label=st["label"],
                sweep_level=st["level"], sweep_t=bars[st["sweep_i"]].t,
                zone_top=st["top"], zone_bot=st["bot"], manip_extreme=st["manip"],
                activation_t=b.t, activation_close=b.c,
                entry=st["top"] if is_bull else st["bot"]))
            bld[is_bull] = None

    return setups
