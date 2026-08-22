#!/usr/bin/env python3
"""
CISD H4 (dirección y ventana) + order block M15 (entrada).

Variante de `combo_cisd_unicorn.py` que cambia el detector de zona: en vez del
breaker por pivote del Unicorn, usa el **order block** al estilo del propio
motor CISD — la última vela contraria cuyo open atraviesa el precio con una
vela de desplazamiento (`ob_entry.py`).

    entrada      → orden límite en el OPEN del order block
    invalidación → extremo del order block (mínimo en largos) menos un pip
    objetivo     → múltiplo de R

Cada operación se camina minuto a minuto sobre los M1 del repo.

Uso:
    python3 combo_cisd_ob.py --years 2025
    python3 combo_cisd_ob.py --years 2005-2025 --r 3 --coste 1.5 --csv ops.csv
"""

from __future__ import annotations

import argparse
import bisect
import csv
import os
import statistics as st
from datetime import date, timedelta

import cisd_forever_backtest as bt
import cisd_m1_sim as m1sim
import combo_cisd_unicorn as cu
import ltf_bars
import ob_entry

HERE = os.path.dirname(os.path.abspath(__file__))
PIP = 0.0001


def run(years, ventana_h=4.0, lookback_h=4.0, r_target=3.0, min_risk_p=4.0,
        coste_p=1.0, ob_min_body=1.0, min_desp=0.0, entrada="open",
        max_hours=24.0, tf_min=15, calidad=False, verbose=True):
    bars_h4 = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), HERE)
    p = bt.Params(qOn=calidad)
    sigs = [s for s in bt.run_engine(bars_h4, p)
            if s.entry_time.year in years and (s.quality_ok or not calidad)]
    ops = []
    for y in years:
        ysig = [s for s in sigs if s.entry_time.year == y]
        if not ysig:
            continue
        b15 = ltf_bars.load(tf_min, [y - 1, y], HERE)
        m1 = m1sim.load_m1(y, HERE)
        if not b15 or not m1[0]:
            continue
        idx15 = {b.t: i for i, b in enumerate(b15)}
        obs = [o for o in ob_entry.find_obs(b15, min_body_p=ob_min_body)
               if o.desplazamiento_p >= min_desp]
        byd = {True: [o for o in obs if o.is_bull], False: [o for o in obs if not o.is_bull]}
        arr = {k: [o.activation_t for o in v] for k, v in byd.items()}

        for sig in ysig:
            long = sig.direction == "long"
            ini = sig.entry_time - timedelta(hours=lookback_h)
            fin = sig.entry_time + timedelta(hours=ventana_h)
            lst = byd[long]
            k = bisect.bisect_left(arr[long], ini)
            hecho = None
            while k < len(lst) and lst[k].activation_t < fin:
                o = lst[k]
                j = idx15.get(o.activation_t)
                if j is not None:
                    niv, sl = o.entrada(entrada), o.stop(1.0)
                    risk = abs(niv - sl)
                    if risk >= min_risk_p * PIP:
                        for jj in range(j + 1, len(b15)):
                            if b15[jj].t >= fin:
                                break
                            if b15[jj].t < sig.entry_time:
                                continue
                            if (b15[jj].l <= niv) if o.is_bull else (b15[jj].h >= niv):
                                tp = niv + r_target * risk if o.is_bull else niv - r_target * risk
                                res, r, exit_t = cu.simular(m1, b15[jj].t, niv, sl, tp, max_hours)
                                if res not in ("sin datos", "sin llenar"):
                                    hecho = dict(sig=sig, ob=o, fill=b15[jj].t, entry=niv,
                                                 sl=sl, tp=tp, riesgo_p=risk / PIP,
                                                 result=res, r=r,
                                                 r_neto=r - coste_p * PIP / risk, exit=exit_t)
                                break
                if hecho:
                    break
                k += 1
            ops.append(hecho or dict(sig=sig, ob=None, result="sin OB", r=0.0, r_neto=0.0))
        if verbose:
            print(f"  {y} procesado", flush=True)
    return ops


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--r", type=float, default=3.0)
    ap.add_argument("--riesgo-min", type=float, default=4.0)
    ap.add_argument("--coste", type=float, default=1.0)
    ap.add_argument("--ob-cuerpo", type=float, default=1.0, help="cuerpo mínimo del OB en pips")
    ap.add_argument("--desplazamiento", type=float, default=0.0,
                    help="cuerpo mínimo de la vela que rompe el OB, en pips")
    ap.add_argument("--entrada", default="open", choices=["open", "mitad", "extremo"])
    ap.add_argument("--tf", type=int, default=15, choices=[5, 15])
    ap.add_argument("--calidad", action="store_true", help="solo señales que pasan el filtro de calidad")
    ap.add_argument("--csv", default="")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    years = bt.parse_years(a.years)
    ops = run(years, r_target=a.r, min_risk_p=a.riesgo_min, coste_p=a.coste,
              ob_min_body=a.ob_cuerpo, min_desp=a.desplazamiento, entrada=a.entrada,
              tf_min=a.tf, calidad=a.calidad, verbose=not a.quiet)

    hechas = [o for o in ops if o["result"] in ("TP", "SL", "tiempo")]
    print(f"\nCISD H4 + order block M{a.tf} · entrada en el {a.entrada} · TP {a.r}R · "
          f"coste {a.coste} pip · riesgo mín {a.riesgo_min} p")
    print(f"  señales {len(ops)}   con entrada {len(hechas)} ({len(hechas)/max(len(ops),1)*100:.0f} %)")
    if hechas:
        w = sum(1 for o in hechas if o["r"] > 0)
        R = sum(o["r"] for o in hechas)
        Rn = sum(o["r_neto"] for o in hechas)
        print(f"  WR {w/len(hechas)*100:.1f} %   R/op bruto {R/len(hechas):+.3f}   neto {Rn/len(hechas):+.3f}"
              f"   R total neto {Rn:+.1f}   riesgo mediano {st.median(o['riesgo_p'] for o in hechas):.1f} pips")
        for tier in ("A", "B", "Corr"):
            sub = [o for o in hechas if o["sig"].tier == tier]
            if sub:
                print(f"     tier {tier:4} ops {len(sub):4}  "
                      f"WR {sum(1 for o in sub if o['r']>0)/len(sub)*100:5.1f} %  "
                      f"R neto {sum(o['r_neto'] for o in sub):+7.1f}")
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["senal", "entrada_h4", "dir", "tier", "ob", "ob_open", "ob_extremo",
                        "fill", "entry", "sl", "tp", "riesgo_p", "resultado", "R", "R_neto"])
            for o in ops:
                ob = o.get("ob")
                w.writerow([o["sig"].sig_time, o["sig"].entry_time, o["sig"].direction, o["sig"].tier,
                            ob.ob_t if ob else "", round(ob.ob_open, 5) if ob else "",
                            round(ob.ob_low if ob and ob.is_bull else (ob.ob_high if ob else 0), 5) if ob else "",
                            o.get("fill", ""), round(o.get("entry", 0), 5), round(o.get("sl", 0), 5),
                            round(o.get("tp", 0), 5), round(o.get("riesgo_p", 0), 1),
                            o["result"], o["r"], round(o["r_neto"], 3)])
        print(f"\nCSV: {a.csv}")


if __name__ == "__main__":
    main()
