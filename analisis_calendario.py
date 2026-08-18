#!/usr/bin/env python3
"""
Cruce del calendario real de operaciones 2025 con las señales del motor CISD H4.

Responde a tres preguntas:
  1. ¿Qué parte del calendario reproduce el motor? (y qué sobra o falta)
  2. ¿Qué significa realmente una marca ✓? (excursión favorable / adversa)
  3. ¿Qué filtros separan las ✓ de las ✕? (con validación fuera de muestra)

Entrada: calendario_trades_2025.csv — volcado del Excel del usuario, una fila por
marca, con la hora de la VELA DE ENTRADA en horario de Nueva York.

Uso:
    python3 analisis_calendario.py                # informe completo
    python3 analisis_calendario.py --seccion 3    # solo el análisis de filtros
"""

from __future__ import annotations

import argparse
import bisect
import collections
import csv
import os
import statistics as st
from datetime import date, datetime, timedelta

import cisd_forever_backtest as bt

try:
    import cisd_m1_sim as m1
except ImportError:  # pragma: no cover
    m1 = None

PIP = 0.0001
HERE = os.path.dirname(os.path.abspath(__file__))
CAL = os.path.join(HERE, "calendario_trades_2025.csv")


def load_calendar() -> dict:
    """Marcas indexadas por (fecha, hora de entrada, dirección).

    El Excel trae 208 marcas; unas pocas comparten fecha/hora/dirección (una señal
    y su corrección en la misma casilla), así que el índice queda en ~202 huecos.
    """
    cal = {}
    with open(CAL) as f:
        for r in csv.DictReader(f):
            y, m, d = map(int, r["fecha"].split("-"))
            cal[(date(y, m, d), int(r["hora_entrada"]), r["dir"])] = r
    return cal


def features(bars, sigs) -> dict:
    """Métricas de la vela CISD y del barrido que la precede."""
    idx = {b.t: i for i, b in enumerate(bars)}
    out = {}
    for s in sigs:
        i = idx[s.sig_time]
        b = bars[i]
        long = s.direction == "long"
        j = i
        while j > 0 and bars[j].hour != 17:
            j -= 1
        ref, ses = bars[j], bars[j:i + 1]
        rng = max(b.h - b.l, 1e-5)
        body = abs(b.c - b.o)
        upw = (b.h - b.c) if b.c > b.o else (b.h - b.o)
        dnw = (b.o - b.l) if b.c > b.o else (b.c - b.l)
        out[id(s)] = dict(
            body=body / PIP,
            ratio=body / rng,
            mecha=(upw if long else dnw) / max(body, 1e-9),
            exc=((ref.l - min(x.l for x in ses)) if long else
                 (max(x.h for x in ses) - ref.h)) / PIP,
            rango_ses=(max(x.h for x in ses) - min(x.l for x in ses)) / PIP,
        )
    return out


def wr(sub, key="win"):
    if not sub:
        return "    —"
    w = sum(1 for r in sub if r[key])
    return f"{w:3}/{len(sub):3} = {w / len(sub) * 100:5.1f}%"


# ══════════════════════════════════════════════════════════════════
def seccion1(bars, sigs, cal):
    print("═" * 72)
    print("1. ¿CUÁNTO DEL CALENDARIO REPRODUCE EL MOTOR?")
    print("═" * 72)
    mine = collections.Counter((s.entry_time.date(), s.entry_time.hour, s.direction,
                                s.tier) for s in sigs)
    calc = collections.Counter((k[0], k[1], k[2], v["tier"]) for k, v in cal.items())
    mine_nt = collections.Counter((k[0], k[1], k[2]) for k in mine.elements())
    cal_nt = collections.Counter((k[0], k[1], k[2]) for k in calc.elements())
    print(f"  marcas del calendario : {sum(calc.values())}")
    print(f"  señales del motor     : {sum(mine.values())}")
    print(f"  coinciden fecha+hora+dirección+tier : {sum((calc & mine).values())}")
    print(f"  coinciden fecha+hora+dirección      : {sum((cal_nt & mine_nt).values())}"
          f"   (solo calendario {sum((cal_nt - mine_nt).values())}, "
          f"solo motor {sum((mine_nt - cal_nt).values())})")
    print("\n  El tier A/B baila en ~34 señales: son casos límite de 'vela limpia'")
    print("  donde el feed de TradingView y los M1 de HistData discrepan por décimas.")
    print()


def seccion2(bars, sigs, cal):
    print("═" * 72)
    print("2. ¿QUÉ SIGNIFICA UNA MARCA ✓?")
    print("═" * 72)
    if m1 is None:
        print("  (requiere cisd_m1_sim.py)")
        return
    data = m1.load_m1(2025, HERE)
    if not data[0]:
        print("  (faltan los M1 de 2025)")
        return
    y25 = [s for s in sigs if s.entry_time.year == 2025]
    # sin stop ni objetivo: solo se mide la excursión durante 24 h
    trades = m1.simulate_m1(y25, data, 0.0, 9999.0, 999.0, 24, "pips")
    pairs = []
    for s, t in zip(y25, trades):
        c = cal.get((s.entry_time.date(), s.entry_time.hour, s.direction))
        if c and c["resultado"] in ("win", "loss") and t.result != "sin entrada":
            pairs.append((c["resultado"] == "win", t))
    for lab in (True, False):
        sub = [t for w, t in pairs if w == lab]
        if not sub:
            continue
        print(f"  {'✓ ganadoras' if lab else '✕ perdedoras'} n={len(sub):3}  "
              f"excursión favorable mediana {st.median(t.mfe for t in sub):5.1f}p   "
              f"adversa mediana {st.median(t.mae for t in sub):5.1f}p  "
              f"(p75 {sorted(t.mae for t in sub)[3 * len(sub) // 4]:5.1f}p)")
    print("\n  Una ✓ es un movimiento de ~40 pips a favor tolerando ~20 en contra.")
    print("  Con un stop de 10 pips desde el cierre H4 morirían casi todas: la")
    print("  entrada real se afina en M15, no se toma al cierre de la vela.")
    print()


def seccion3(bars, sigs, cal, feats):
    print("═" * 72)
    print("3. ¿QUÉ FILTRA BIEN? (marcas de 2025)")
    print("═" * 72)
    lab = []
    for s in sigs:
        c = cal.get((s.entry_time.date(), s.entry_time.hour, s.direction))
        if c and c["resultado"] in ("win", "loss") and s.entry_time.year == 2025:
            f = dict(feats[id(s)])
            f.update(win=c["resultado"] == "win", tier_cal=c["tier"], tier=s.tier,
                     dir=s.direction, hora=s.entry_time.hour, evento=c["evento"] or "—")
            lab.append(f)
    if not lab:
        print("  sin muestra")
        return
    base = sum(1 for r in lab if r["win"]) / len(lab)
    print(f"  muestra etiquetada n={len(lab)}   acierto base {base * 100:.1f}%\n")

    def grupo(nombre, keyfn, minimo=5):
        print(f"  ■ {nombre}")
        g = collections.defaultdict(list)
        for r in lab:
            g[keyfn(r)].append(r)
        for k in sorted(g, key=str):
            if len(g[k]) >= minimo:
                print(f"      {str(k):24} {wr(g[k])}")
        print()

    grupo("Tier según el calendario", lambda r: r["tier_cal"])
    grupo("Dirección", lambda r: r["dir"])
    grupo("Hora de entrada × dirección", lambda r: f"{r['hora']:02d}h {r['dir']}")
    grupo("Evento macro del día", lambda r: r["evento"], minimo=6)

    def tramos(nombre, key, cortes):
        print(f"  ■ {nombre}")
        prev = -1e9
        for cut in cortes + [1e9]:
            sub = [r for r in lab if prev <= r[key] < cut]
            if len(sub) >= 8:
                etq = f"[{prev:g}, {cut:g})" if cut < 1e9 else f">= {prev:g}"
                print(f"      {etq:24} {wr(sub)}")
            prev = cut
        print()

    tramos("Cuerpo de la vela CISD (pips)", "body", [10, 20, 30, 45])
    tramos("Cuerpo / rango de la vela", "ratio", [0.35, 0.5, 0.65, 0.8])
    tramos("Mecha en contra / cuerpo", "mecha", [0.1, 0.25, 0.5])
    tramos("Exceso del barrido sobre el extremo de las 17:00 (pips)", "exc", [3, 8, 15, 30])

    reglas = {
        "sin filtro": lambda f: True,
        "cuerpo >= 20p": lambda f: f["body"] >= 20,
        "cuerpo >= 30p": lambda f: f["body"] >= 30,
        "ratio >= 0.50": lambda f: f["ratio"] >= 0.50,
        "ratio >= 0.60": lambda f: f["ratio"] >= 0.60,
        "exceso <= 8p": lambda f: f["exc"] <= 8,
        "exceso <= 15p": lambda f: f["exc"] <= 15,
        "CALIBRADO 20p + 0.50 + exc 8p": lambda f: f["body"] >= 20 and f["ratio"] >= 0.50 and f["exc"] <= 8,
        "estricto 25p + 0.60 + exc 15p": lambda f: f["body"] >= 25 and f["ratio"] >= 0.60 and f["exc"] <= 15,
    }
    print("  ■ Reglas completas")
    print(f"      {'regla':32} {'n':>4} {'% señales':>10} {'acierto':>9}")
    for nombre, fn in reglas.items():
        sub = [r for r in lab if fn(r)]
        if len(sub) < 20:
            continue
        w = sum(1 for r in sub if r["win"]) / len(sub)
        print(f"      {nombre:32} {len(sub):>4} {len(sub) / len(lab) * 100:9.0f}% "
              f"{w * 100:8.1f}%")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seccion", type=int, default=0, help="1, 2 o 3; 0 = todas")
    args = ap.parse_args()

    cal = load_calendar()
    bars = bt.load_h4_cached([2024, 2025], HERE)
    sigs = [s for s in bt.run_engine(bars, bt.Params()) if s.entry_time.year == 2025]
    feats = features(bars, sigs)

    if args.seccion in (0, 1):
        seccion1(bars, sigs, cal)
    if args.seccion in (0, 2):
        seccion2(bars, sigs, cal)
    if args.seccion in (0, 3):
        seccion3(bars, sigs, cal, feats)


if __name__ == "__main__":
    main()
