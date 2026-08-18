#!/usr/bin/env python3
"""
Motor de entradas del Forever Model, portado del Pine a Python.

Genera las entradas *propias* del modelo (no como filtro del CISD):

    FVG del timeframe superior  →  pivotes ICT por tiers (ST/IT/LT) dentro del FVG
    →  barrido de un pivote     →  vela de desplazamiento = order block
    →  confirmación por cierre a través del open del OB
    →  entrada cuando el precio vuelve al OB

Alineación por defecto: LTF = H4, HTF = diario (sesión FX 17:00 NY), que es la
que permite comparar con el motor CISD H4.

Limitación deliberada: **la puerta SMT no se aplica** (haría falta el par
correlacionado, y el repo solo tiene EURUSD). Sin ella el modelo produce MÁS
entradas de las reales, así que cualquier solape que se mida es un techo.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

import cisd_forever_backtest as bt

PIP = 0.0001


# ══════════════════════════════════════════════════════════════════
@dataclass
class Pivot:
    price: float
    t: datetime


@dataclass
class Anchor:
    price: float
    t: datetime
    swept: bool = False


@dataclass
class OB:
    open_price: float
    t: datetime
    pivot_price: float
    pivot_t: datetime
    sc_high: float
    sc_low: float
    confirmed_t: datetime | None = None
    entry_t: datetime | None = None
    sl: float = 0.0
    target: float = 0.0
    filled: bool = False
    target_hit: bool = False
    dead: bool = False
    rec: dict | None = None      # registro de la operación asociada


@dataclass
class FVG:
    hi: float
    lo: float
    bull: bool
    erl: float
    pivot_lvl: float | None
    created_t: datetime
    mitigated: bool = False
    done: bool = False
    st: list = field(default_factory=list)        # pivotes de máximos: tier corto
    it: list = field(default_factory=list)
    lt: list = field(default_factory=list)
    st_anc: list = field(default_factory=list)    # anclas de máximos
    it_anc: list = field(default_factory=list)
    lt_anc: list = field(default_factory=list)
    st_l: list = field(default_factory=list)      # lo mismo para mínimos
    it_l: list = field(default_factory=list)
    lt_l: list = field(default_factory=list)
    st_anc_l: list = field(default_factory=list)
    it_anc_l: list = field(default_factory=list)
    lt_anc_l: list = field(default_factory=list)
    pending: list = field(default_factory=list)
    confirmed: list = field(default_factory=list)


# ── pivotes ICT ───────────────────────────────────────────────────
def promote_level(src: list, dst: list, is_high: bool) -> None:
    """Un pivote del tier N asciende cuando queda rodeado por dos más bajos."""
    if len(src) > 2:
        y1, y2, y3 = src[-1].price, src[-2].price, src[-3].price
        ok = (y1 < y2 and y2 > y3) if is_high else (y1 > y2 and y2 < y3)
        if ok:
            cand = src[-2]
            if not dst or dst[-1].price != cand.price:
                dst.append(Pivot(cand.price, cand.t))
                src.pop(-2)


def promote_anchor(src: list, dst: list, t: datetime) -> None:
    for k in range(len(src) - 1, -1, -1):
        if src[k].t == t and not src[k].swept:
            a = src.pop(k)
            dst.append(Anchor(a.price, a.t, False))
            return


def ict_swing(f: FVG, bars, i: int, is_high: bool) -> None:
    """Réplica de f_ictSwing: detecta el pivote en [1] y lo hace ascender de tier."""
    if i < 3:
        return
    prev = bars[i - 1]
    price = prev.h if is_high else prev.l
    win = bars[i - 2:i + 1]                      # las 3 últimas velas
    extreme = max(x.h for x in win) if is_high else min(x.l for x in win)
    st, it, lt = (f.st, f.it, f.lt) if is_high else (f.st_l, f.it_l, f.lt_l)
    st_a, it_a, lt_a = (f.st_anc, f.it_anc, f.lt_anc) if is_high else (f.st_anc_l, f.it_anc_l, f.lt_anc_l)
    if (prev.h if is_high else prev.l) == extreme:
        st.append(Pivot(price, prev.t))
        st_a.append(Anchor(price, prev.t, False))
    promote_level(st, it, is_high)
    promote_level(it, lt, is_high)
    if len(st) > 2 and it and it[-1].t == st[-2].t:
        promote_anchor(st_a, it_a, st[-2].t)
    if len(it) > 2 and lt and lt[-1].t == it[-2].t:
        promote_anchor(it_a, lt_a, it[-2].t)


def clean_tier(anchors: list, bar, is_bull: bool) -> None:
    for k in range(len(anchors) - 1, -1, -1):
        a = anchors[k]
        if not a.swept and ((bar.l < a.price) if is_bull else (bar.h > a.price)):
            a.swept = True
        if a.swept:
            anchors.pop(k)


def sweep_tier(anchors: list, pending: list, bar, is_bull: bool) -> bool:
    best = None
    for k in range(len(anchors) - 1, -1, -1):
        a = anchors[k]
        hit = (bar.l < a.price) if is_bull else (bar.h > a.price)
        if not a.swept and hit:
            a.swept = True
            if best is None or ((a.price < best.price) if is_bull else (a.price > best.price)):
                best = a
        if a.swept:
            anchors.pop(k)
    if best is None:
        return False
    rng = bar.h - bar.l
    body = abs(bar.c - bar.o)
    desplaza = rng > 0 and body * 100 / rng >= 50 and ((bar.c < bar.o) if is_bull else (bar.c > bar.o))
    if desplaza:
        pending.append(OB(bar.o, bar.t, best.price, best.t, bar.h, bar.l))
    return True


def process_sweeps(f: FVG, bar) -> None:
    is_bull = f.bull
    lt_a, it_a, st_a = ((f.lt_anc, f.it_anc, f.st_anc) if not is_bull
                        else (f.lt_anc_l, f.it_anc_l, f.st_anc_l))
    if sweep_tier(lt_a, f.pending, bar, is_bull):
        clean_tier(it_a, bar, is_bull)
        clean_tier(st_a, bar, is_bull)
    elif sweep_tier(it_a, f.pending, bar, is_bull):
        clean_tier(st_a, bar, is_bull)
    else:
        sweep_tier(st_a, f.pending, bar, is_bull)


# ══════════════════════════════════════════════════════════════════
def daily_sessions(bars):
    """Sesiones FX 17:00→17:00 a partir de las velas H4."""
    out = []
    cur = None
    for i, b in enumerate(bars):
        if b.hour == 17 or cur is None:
            if cur is not None:
                out.append(cur)
            cur = dict(o=b.o, h=b.h, l=b.l, c=b.c, t=b.t, first=i, last=i)
        else:
            cur["h"] = max(cur["h"], b.h)
            cur["l"] = min(cur["l"], b.l)
            cur["c"] = b.c
            cur["last"] = i
    if cur:
        out.append(cur)
    return out


def htf_pivots(sessions):
    """ta.pivothigh/low(1,1) sobre la serie diaria, latcheados como en el Pine."""
    ph = [None] * len(sessions)
    pl = [None] * len(sessions)
    last_h = last_l = None
    for k in range(len(sessions)):
        if 1 <= k - 1 < len(sessions) - 1:
            a, b, c = sessions[k - 2], sessions[k - 1], sessions[k]
            if b["h"] > a["h"] and b["h"] > c["h"]:
                last_h = b["h"]
            if b["l"] < a["l"] and b["l"] < c["l"]:
                last_l = b["l"]
        ph[k], pl[k] = last_h, last_l
    return ph, pl


def run_forever(bars, min_proj: float = 2.0, max_fvgs: int = 50, bias: str = "Neutral"):
    """Devuelve la lista de OB confirmados con su momento de entrada."""
    sess = daily_sessions(bars)
    ph, pl = htf_pivots(sess)
    sess_of_bar = {}
    for si, s in enumerate(sess):
        for i in range(s["first"], s["last"] + 1):
            sess_of_bar[i] = si

    fvgs: list[FVG] = []
    trades = []

    for i, b in enumerate(bars):
        si = sess_of_bar[i]
        new_session = (i == sess[si]["first"])

        # ── nueva vela HTF: nacimiento y muerte de FVGs
        if new_session and si >= 3:
            d1, d2, d3 = sess[si - 1], sess[si - 2], sess[si - 3]
            for f in list(fvgs):
                if not any(ob.confirmed_t and not ob.target_hit and not ob.dead for ob in f.confirmed):
                    if (d1["c"] < f.lo) if f.bull else (d1["c"] > f.hi):
                        fvgs.remove(f)
            for is_bull in (True, False):
                gap = (d1["l"] > d3["h"]) if is_bull else (d1["h"] < d3["l"])
                if not gap:
                    continue
                if bias == "Bullish" and not is_bull:
                    continue
                if bias == "Bearish" and is_bull:
                    continue
                hi = d1["l"] if is_bull else d3["l"]
                lo = d3["h"] if is_bull else d1["h"]
                erl = max(d1["h"], d2["h"]) if is_bull else min(d1["l"], d2["l"])
                piv = pl[si - 1] if is_bull else ph[si - 1]
                if piv is not None and not ((piv < lo) if is_bull else (piv > hi)):
                    piv = None
                f = FVG(hi=hi, lo=lo, bull=is_bull, erl=erl, pivot_lvl=piv, created_t=b.t)
                # sembrado de pivotes desde la apertura de la vela HTF más antigua
                start = sess[si - 3]["first"]
                for j in range(start + 1, i - 1):
                    if bars[j].h > bars[j - 1].h and bars[j].h > bars[j + 1].h:
                        f.st_anc.append(Anchor(bars[j].h, bars[j].t, False))
                        f.st.append(Pivot(bars[j].h, bars[j].t))
                    if bars[j].l < bars[j - 1].l and bars[j].l < bars[j + 1].l:
                        f.st_anc_l.append(Anchor(bars[j].l, bars[j].t, False))
                        f.st_l.append(Pivot(bars[j].l, bars[j].t))
                fvgs.append(f)
            while len(fvgs) > max_fvgs:
                fvgs.pop(0)

        # ── ciclo de vida de cada FVG sobre la vela LTF actual
        for f in list(fvgs):
            activo = any(ob.confirmed_t and not ob.target_hit and not ob.dead for ob in f.confirmed)
            if not activo:
                if not f.mitigated:
                    f.erl = max(f.erl, b.h) if f.bull else min(f.erl, b.l)
                    if (b.l < f.hi) if f.bull else (b.h > f.lo):
                        f.mitigated = True
                if f.mitigated and ((b.h > f.erl) if f.bull else (b.l < f.erl)):
                    fvgs.remove(f)
                    continue
                if f.pivot_lvl is not None and ((b.l < f.pivot_lvl) if f.bull else (b.h > f.pivot_lvl)):
                    fvgs.remove(f)
                    continue

            if not f.done:
                ict_swing(f, bars, i, True)
                ict_swing(f, bars, i, False)
                process_sweeps(f, b)

                # confirmación: la vela anterior cerró a través del open del OB
                if i > 0:
                    prev_c = bars[i - 1].c
                    plotted = False
                    for ob in list(f.pending):
                        if b.t > ob.t and ((prev_c > ob.open_price) if f.bull else (prev_c < ob.open_price)):
                            if not plotted:
                                plotted = True
                                ob.confirmed_t = b.t
                                ob.sl = ob.sc_low if f.bull else ob.sc_high
                                risk = abs(ob.open_price - ob.sl)
                                ob.target = (ob.open_price + risk * min_proj if f.bull
                                             else ob.open_price - risk * min_proj)
                                f.confirmed.append(ob)
                            f.pending.remove(ob)

            # gestión de los OB confirmados
            for ob in f.confirmed:
                if ob.target_hit or ob.dead or ob.confirmed_t is None or b.t <= ob.confirmed_t:
                    continue
                if not ob.filled:
                    if (b.l <= ob.open_price) if f.bull else (b.h >= ob.open_price):
                        ob.filled = True
                        ob.entry_t = b.t
                        ob.rec = dict(dir="long" if f.bull else "short",
                                      confirm_t=ob.confirmed_t, entry_t=b.t,
                                      entry=ob.open_price, sl=ob.sl, target=ob.target,
                                      fvg_hi=f.hi, fvg_lo=f.lo)
                        trades.append(ob.rec)
                if ob.filled and ob.rec is not None and "result" not in ob.rec:
                    if (b.l < ob.sl) if f.bull else (b.h > ob.sl):
                        ob.dead = True
                        ob.rec["result"] = "SL"
                        ob.rec["exit_t"] = b.t
                    elif (b.h >= ob.target) if f.bull else (b.l <= ob.target):
                        ob.target_hit = True
                        f.done = True
                        ob.rec["result"] = "TP"
                        ob.rec["exit_t"] = b.t
    return trades


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--proj", type=float, default=2.0)
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    years = bt.parse_years(a.years)
    here = os.path.dirname(os.path.abspath(__file__))
    bars = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), here)
    trades = [t for t in run_forever(bars, a.proj) if t["entry_t"].year in years]
    print(f"Forever Model (LTF H4 / HTF diario, sin puerta SMT) — {a.years}")
    print(f"  entradas: {len(trades)}   "
          f"TP {sum(1 for t in trades if t.get('result') == 'TP')}   "
          f"SL {sum(1 for t in trades if t.get('result') == 'SL')}   "
          f"abiertas {sum(1 for t in trades if 'result' not in t)}")
    for t in trades[:15]:
        print(f"   confirmación {t['confirm_t']:%Y-%m-%d %H:%M}  entrada {t['entry_t']:%Y-%m-%d %H:%M}  "
              f"{t['dir']:5} {t.get('result', '—')}")
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["confirmacion", "entrada", "dir", "entry", "sl", "target", "resultado"])
            for t in trades:
                w.writerow([t["confirm_t"], t["entry_t"], t["dir"], round(t["entry"], 5),
                            round(t["sl"], 5), round(t["target"], 5), t.get("result", "abierta")])
        print(f"CSV: {a.csv}")


if __name__ == "__main__":
    main()
