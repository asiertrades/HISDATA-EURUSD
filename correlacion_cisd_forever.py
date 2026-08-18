#!/usr/bin/env python3
"""
¿Cuadran las entradas del CISD H4 con las del Forever Model?

Cruza las señales de los dos motores sobre las mismas velas y mide:
  · coincidencia exacta de vela y dirección
  · coincidencia dentro de la misma sesión FX (17:00→17:00)
  · contradicciones (los dos disparan en la misma sesión en sentidos opuestos)
  · si la confluencia mejora el acierto según el calendario real de 2025

Uso:
    python3 correlacion_cisd_forever.py --years 2025
    python3 correlacion_cisd_forever.py --years 2001-2025 --sin-calendario
"""

from __future__ import annotations

import argparse
import collections
import csv
import os
from datetime import date, timedelta

import cisd_forever_backtest as bt
import forever_model_engine as fm

HERE = os.path.dirname(os.path.abspath(__file__))


def session_key(t):
    """Etiqueta de la sesión FX a la que pertenece una vela (17:00 NY → 17:00)."""
    return (t - timedelta(hours=17)).date()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--tolerancia", type=int, default=2, help="velas H4 de margen")
    ap.add_argument("--sin-calendario", action="store_true")
    ap.add_argument("--calidad", action="store_true", help="CISD con el filtro de calidad")
    ap.add_argument("--causal", action="store_true",
                    help="mide la confluencia usando solo velas anteriores a la entrada")
    a = ap.parse_args()

    years = bt.parse_years(a.years)
    bars = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), HERE)
    idx = {b.t: i for i, b in enumerate(bars)}

    cisd = [s for s in bt.run_engine(bars, bt.Params(qOn=a.calidad))
            if s.entry_time.year in years and (s.quality_ok or not a.calidad)]
    fmt_raw = [t for t in fm.run_forever(bars) if t["entry_t"].year in years]
    # varios FVG solapados generan el mismo OB: se cuenta una vez
    seen, fmt = set(), []
    for t in fmt_raw:
        k = (t["entry_t"], t["dir"], round(t["entry"], 5))
        if k not in seen:
            seen.add(k)
            fmt.append(t)

    print("═" * 70)
    print(f"CISD H4 vs FOREVER MODEL — {a.years}")
    print("═" * 70)
    print(f"  entradas CISD          : {len(cisd)}")
    print(f"  entradas Forever Model : {len(fmt)}  (sin puerta SMT: es un techo)")
    print()

    fm_bar = collections.defaultdict(list)
    for t in fmt:
        fm_bar[(t["entry_t"], t["dir"])].append(t)
    fm_ses = collections.defaultdict(set)
    for t in fmt:
        fm_ses[session_key(t["entry_t"])].add(t["dir"])
    fm_idx = sorted({idx[t["entry_t"]] for t in fmt if t["entry_t"] in idx})
    fm_idx_dir = collections.defaultdict(set)
    for t in fmt:
        if t["entry_t"] in idx:
            fm_idx_dir[idx[t["entry_t"]]].add(t["dir"])

    exacta = sesion = cerca = contra = 0
    marcas = []
    for s in cisd:
        i = idx.get(s.entry_time)
        ex = (s.entry_time, s.direction) in fm_bar
        se = s.direction in fm_ses.get(session_key(s.entry_time), set())
        ce = any(s.direction in fm_idx_dir.get(i + d, set())
                 for d in range(-a.tolerancia, a.tolerancia + 1)) if i is not None else False
        op = ("long" if s.direction == "short" else "short") in fm_ses.get(session_key(s.entry_time), set())
        exacta += ex
        sesion += se
        cerca += ce
        contra += op and not se
        marcas.append((s, ex, se, ce))

    n = len(cisd)
    print(f"  misma vela y dirección                 : {exacta:4}  ({exacta / n * 100:.1f} %)")
    print(f"  misma sesión y dirección               : {sesion:4}  ({sesion / n * 100:.1f} %)")
    print(f"  ±{a.tolerancia} velas y misma dirección              : {cerca:4}  ({cerca / n * 100:.1f} %)")
    print(f"  el Forever Model dice lo contrario     : {contra:4}  ({contra / n * 100:.1f} %)")
    print(f"  sin rastro del Forever Model           : {n - cerca - contra:4}")
    print()

    # ── al revés
    cisd_ses = collections.defaultdict(set)
    for s in cisd:
        cisd_ses[session_key(s.entry_time)].add(s.direction)
    con_cisd = sum(1 for t in fmt if t["dir"] in cisd_ses.get(session_key(t["entry_t"]), set()))
    print(f"  entradas del Forever Model con un CISD en la misma sesión y sentido: "
          f"{con_cisd}/{len(fmt)} ({con_cisd / max(len(fmt), 1) * 100:.1f} %)")
    print()

    # ── solape horario
    print("  ■ Hora de entrada (vela H4, NY)")
    hc = collections.Counter(s.entry_time.hour for s in cisd)
    hf = collections.Counter(t["entry_t"].hour for t in fmt)
    print(f"      {'hora':>6} {'CISD':>7} {'Forever':>9}")
    for h in sorted(set(hc) | set(hf)):
        print(f"      {h:5}h {hc.get(h, 0):7} {hf.get(h, 0):9}")
    print()

    if a.causal:
        print("  ■ Confluencia usando SOLO velas anteriores a la entrada")
        sim = bt.simulate(bars, bt.run_engine(bars, bt.Params(slMode="extremo", rTarget=2.0)),
                          bt.Params(slMode="extremo", rTarget=2.0))
        done = [s for s in sim if s.result in ("TP", "SL", "tiempo") and s.entry_time.year in years]
        fill = collections.defaultdict(set)
        for t in fmt:
            if t["entry_t"] in idx:
                fill[idx[t["entry_t"]]].add(t["dir"])

        def grupo(nombre, fn):
            sub = [s for s in done if idx.get(s.entry_time) is not None
                   and fn(idx[s.entry_time], s.direction)]
            if len(sub) < 20:
                return
            print(f"      {nombre:44} n={len(sub):5}  "
                  f"WR {sum(1 for s in sub if s.r > 0) / len(sub) * 100:5.1f}%  "
                  f"R/op {sum(s.r for s in sub) / len(sub):+.3f}")

        grupo("todas", lambda i, d: True)
        grupo("OB llenado en las 3 velas previas, misma dir",
              lambda i, d: any(d in fill.get(i - k, set()) for k in (1, 2, 3)))
        grupo("OB llenado en las 6 velas previas, misma dir",
              lambda i, d: any(d in fill.get(i - k, set()) for k in range(1, 7)))
        grupo("OB llenado en las 6 previas, dir contraria",
              lambda i, d: any(("long" if d == "short" else "short") in fill.get(i - k, set())
                               for k in range(1, 7)))
        grupo("OB llenado en la MISMA vela de entrada (no operable)",
              lambda i, d: d in fill.get(i, set()))
        print()

    if a.sin_calendario or not os.path.exists(os.path.join(HERE, "calendario_trades_2025.csv")):
        return

    cal = {}
    with open(os.path.join(HERE, "calendario_trades_2025.csv")) as f:
        for r in csv.DictReader(f):
            y, m, d = map(int, r["fecha"].split("-"))
            cal[(date(y, m, d), int(r["hora_entrada"]), r["dir"])] = r

    print("  ■ AVISO sobre la confluencia en la propia vela de entrada")
    print("      Si el Forever Model llena su OB en la misma vela en la que entra el")
    print("      CISD, y en el mismo sentido, es que el precio se ha ido en contra de")
    print("      la entrada: el 'efecto' es una tautología, no información previa.")
    print("      Solo cuenta lo que se sabe ANTES de entrar (ver --causal).")
    print()
    print("  ■ ¿La confluencia mejora el acierto? (marcas reales de 2025)")
    for etiqueta, sel in (("con Forever Model (±%d velas)" % a.tolerancia, lambda m: m[3]),
                          ("sin Forever Model", lambda m: not m[3]),
                          ("misma sesión", lambda m: m[2]),
                          ("misma vela exacta", lambda m: m[1])):
        sub = []
        for m in marcas:
            if not sel(m):
                continue
            s = m[0]
            c = cal.get((s.entry_time.date(), s.entry_time.hour, s.direction))
            if c and c["resultado"] in ("win", "loss"):
                sub.append(c["resultado"] == "win")
        if len(sub) >= 5:
            print(f"      {etiqueta:34} n={len(sub):4}  acierto {sum(sub) / len(sub) * 100:5.1f} %")
    print()


if __name__ == "__main__":
    main()
