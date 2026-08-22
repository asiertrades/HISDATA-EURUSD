#!/usr/bin/env python3
"""
CISD H4 + entrada por breaker con stop en el OB de origen (método de Asier).

    entrada → primer toque del RANGO de la zona breaker más cercana en el
              sentido del trade (el borde de la vela, no su cuerpo)
    stop    → más allá del extremo de la siguiente zona de la cadena; si no
              cabe en el tope de riesgo, apretado a su open
    objetivo→ múltiplo de R (2R por defecto, que es el que usa Asier)

Uso:
    python3 combo_cisd_breaker.py --years 2025
    python3 combo_cisd_breaker.py --years 2025 --analisis-sl
"""

from __future__ import annotations

import argparse
import bisect
import csv
import os
import statistics as st
from datetime import date, timedelta

import breaker_entry as be
import cisd_forever_backtest as bt
import cisd_m1_sim as m1sim
import combo_cisd_unicorn as cu
import ltf_bars

HERE = os.path.dirname(os.path.abspath(__file__))
PIP = 0.0001


def run(years, r_target=2.0, ventana_h=4.0, coste_p=1.0, tope_riesgo_p=12.0,
        cuerpo_ratio=0.8, frescura_h=24.0, max_hours=24.0, verbose=True):
    bars_h4 = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), HERE)
    sigs = [s for s in bt.run_engine(bars_h4, bt.Params()) if s.entry_time.year in years]
    ops = []
    for y in years:
        ysig = [s for s in sigs if s.entry_time.year == y]
        if not ysig:
            continue
        b15 = ltf_bars.load(15, [y - 1, y], HERE)
        m1 = m1sim.load_m1(y, HERE)
        if not b15 or not m1[0]:
            continue
        idx15 = {b.t: i for i, b in enumerate(b15)}
        instantes = {s.entry_time for s in ysig}
        estados = be.detecta_zonas(b15, cuerpo_min_ratio=cuerpo_ratio, instantes=instantes)

        for sig in ysig:
            est = estados.get(sig.entry_time)
            i0 = idx15.get(sig.entry_time)
            if est is None or i0 is None:
                continue
            largo = sig.direction == "long"
            plan = be.elige_entrada(est, b15[i0].o, largo, tope_riesgo_p=tope_riesgo_p,
                                    ahora=sig.entry_time, frescura_h=frescura_h)
            if plan is None:
                ops.append(dict(sig=sig, result="sin zona", r=0.0, r_neto=0.0))
                continue
            niv, sl, risk = plan["entrada"], plan["sl"], plan["riesgo_p"] * PIP
            # el toque del rango de la zona, dentro de la ventana
            fill = None
            for jj in range(i0, len(b15)):
                if b15[jj].t >= sig.entry_time + timedelta(hours=ventana_h):
                    break
                if (b15[jj].l <= niv) if largo else (b15[jj].h >= niv):
                    fill = b15[jj].t
                    break
            if fill is None:
                ops.append(dict(sig=sig, plan=plan, result="sin toque", r=0.0, r_neto=0.0))
                continue
            tp = niv + r_target * risk if largo else niv - r_target * risk
            res, r, exit_t = cu.simular(m1, fill, niv, sl, tp, max_hours)
            if res in ("sin datos", "sin llenar"):
                ops.append(dict(sig=sig, plan=plan, result="sin datos", r=0.0, r_neto=0.0))
                continue
            ops.append(dict(sig=sig, plan=plan, fill=fill, entry=niv, sl=sl, tp=tp,
                            riesgo_p=risk / PIP, result=res, r=r,
                            r_neto=r - coste_p * PIP / risk, exit=exit_t, m1=m1, largo=largo))
        if verbose:
            print(f"  {y} procesado", flush=True)
    return ops


def analisis_sl(ops, r_target, extras=(2, 4, 6, 10, 15, 20)):
    """De las perdedoras: ¿cuántas se salvarían ampliando el stop?"""
    perdedoras = [o for o in ops if o.get("result") == "SL"]
    if not perdedoras:
        return
    print(f"\n■ De las {len(perdedoras)} perdedoras, ¿cuántas ganan ampliando el stop?")
    print(f"   {'stop +X pips':>14} {'salvadas':>9} {'% ':>6} {'riesgo medio':>13} {'R neto del grupo':>17}")
    base = sum(o["r_neto"] for o in perdedoras)
    print(f"   {'sin ampliar':>14} {0:9} {0:5.0f}% "
          f"{st.mean(o['riesgo_p'] for o in perdedoras):12.1f}p {base:+17.1f}")
    for extra in extras:
        salvadas = 0
        total = 0.0
        riesgos = []
        for o in perdedoras:
            largo = o["largo"]
            sl = o["sl"] - extra * PIP if largo else o["sl"] + extra * PIP
            risk = abs(o["entry"] - sl)
            tp = o["entry"] + r_target * risk if largo else o["entry"] - r_target * risk
            res, r, _ = cu.simular(o["m1"], o["fill"], o["entry"], sl, tp, 24.0)
            if res in ("sin datos", "sin llenar"):
                continue
            riesgos.append(risk / PIP)
            total += r - 1.0 * PIP / risk
            if r > 0:
                salvadas += 1
        if riesgos:
            print(f"   {extra:13}p {salvadas:9} {salvadas/len(perdedoras)*100:5.0f}% "
                  f"{st.mean(riesgos):12.1f}p {total:+17.1f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--r", type=float, default=2.0)
    ap.add_argument("--tope-riesgo", type=float, default=12.0)
    ap.add_argument("--cuerpo", type=float, default=0.8)
    ap.add_argument("--frescura", type=float, default=24.0)
    ap.add_argument("--coste", type=float, default=1.0)
    ap.add_argument("--analisis-sl", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    years = bt.parse_years(a.years)
    ops = run(years, r_target=a.r, coste_p=a.coste, tope_riesgo_p=a.tope_riesgo,
              cuerpo_ratio=a.cuerpo, frescura_h=a.frescura, verbose=not a.quiet)
    hechas = [o for o in ops if o["result"] in ("TP", "SL", "tiempo")]
    print(f"\nCISD H4 + breaker M15 · TP {a.r}R · tope de riesgo {a.tope_riesgo} p · coste {a.coste} p")
    print(f"  señales {len(ops)}   operadas {len(hechas)}   "
          f"sin zona {sum(1 for o in ops if o['result']=='sin zona')}   "
          f"sin toque {sum(1 for o in ops if o['result']=='sin toque')}")
    if hechas:
        w = sum(1 for o in hechas if o["r"] > 0)
        print(f"  WR {w/len(hechas)*100:.1f} %   R/op bruto {sum(o['r'] for o in hechas)/len(hechas):+.3f}   "
              f"neto {sum(o['r_neto'] for o in hechas)/len(hechas):+.3f}   "
              f"R total neto {sum(o['r_neto'] for o in hechas):+.1f}   "
              f"riesgo mediano {st.median(o['riesgo_p'] for o in hechas):.1f} p")
    cal_p = os.path.join(HERE, "calendario_trades_2025.csv")
    if os.path.exists(cal_p) and 2025 in years:
        cal = {}
        with open(cal_p) as f:
            for r_ in csv.DictReader(f):
                y, m, d = map(int, r_["fecha"].split("-"))
                if r_["resultado"] in ("win", "loss"):
                    cal[(date(y, m, d), int(r_["hora_entrada"]), r_["dir"])] = r_["resultado"]
        for etq, val in (("✓", "win"), ("✕", "loss")):
            sub = [o for o in hechas
                   if cal.get((o["sig"].entry_time.date(), o["sig"].entry_time.hour,
                               o["sig"].direction)) == val]
            if sub:
                print(f"    sobre tus {etq}: n={len(sub):3}  WR {sum(1 for o in sub if o['r']>0)/len(sub)*100:5.1f} %  "
                      f"R/op {sum(o['r_neto'] for o in sub)/len(sub):+.3f}")
    if a.analisis_sl:
        analisis_sl(hechas, a.r)


if __name__ == "__main__":
    main()
