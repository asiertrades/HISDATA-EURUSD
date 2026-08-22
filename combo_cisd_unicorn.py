#!/usr/bin/env python3
"""
CISD H4 (dirección y ventana) + Unicorn M15 (entrada afinada).

    El CISD dice QUÉ y CUÁNDO: dirección y la vela de entrada (05:00 / 09:00 NY).
    El Unicorn dice DÓNDE: retesteo del breaker M15, con el stop en su extremo.

La operación se camina minuto a minuto sobre los M1 del repo, así que el orden
intra-vela (¿stop u objetivo primero?) se resuelve de verdad — imprescindible
con stops de 8-10 pips.

Uso:
    python3 combo_cisd_unicorn.py --years 2025
    python3 combo_cisd_unicorn.py --years 2015-2025 --ventana 4 --r 3
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
import ltf_bars
import unicorn_engine as ue

HERE = os.path.dirname(os.path.abspath(__file__))
PIP = 0.0001


def nivel_entrada(s, modo):
    """Dónde se coloca la orden límite dentro del breaker."""
    if modo == "mitad":
        return (s.zone_top + s.zone_bot) / 2
    if modo == "lejano":
        return s.zone_bot if s.is_bull else s.zone_top
    return s.entry          # "borde": primer contacto con la zona


def simular(m1, entry_t, entry, sl, tp, max_hours):
    """Camina los M1 desde entry_t: devuelve (resultado, R, salida)."""
    ts, mo, mh, ml, mc = m1
    i = bisect.bisect_left(ts, entry_t)
    end = bisect.bisect_left(ts, entry_t + timedelta(hours=max_hours))
    if i >= end:
        return "sin datos", 0.0, None
    long = tp > entry
    risk = max(abs(entry - sl), PIP * 0.5)
    for j in range(i, end):
        hit_sl = ml[j] <= sl if long else mh[j] >= sl
        hit_tp = mh[j] >= tp if long else ml[j] <= tp
        if hit_sl:
            return "SL", -1.0, ts[j]
        if hit_tp:
            return "TP", abs(tp - entry) / risk, ts[j]
    last = mc[end - 1]
    return "tiempo", ((last - entry) if long else (entry - last)) / risk, ts[end - 1]


def run(years, ventana_h, r_target, sl_mode, buffer_p, max_hours, unicorn_only, verbose,
        lookback_h=4.0, entry_mode='mitad', min_risk_p=4.0, coste_p=1.0, tf_min=15):
    bars_h4 = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), HERE)
    sigs = [s for s in bt.run_engine(bars_h4, bt.Params()) if s.entry_time.year in years]

    ops = []
    for y in years:
        b15 = ltf_bars.load(tf_min, [y - 1, y], HERE)
        if not b15:
            continue
        # fuentes de liquidez según el timeframe: en M5 entra también la H1
        fuentes = [("H4", bars_h4)] if tf_min >= 15 else [("1H", ltf_bars.agrupar(b15, 60)), ("H4", bars_h4)]
        setups = ue.find_setups(b15, bars_h4, unicorn_only=unicorn_only, htf_sources=fuentes)
        by_dir = {"long": [s for s in setups if s.is_bull],
                  "short": [s for s in setups if not s.is_bull]}
        for k in by_dir:
            by_dir[k].sort(key=lambda s: s.activation_t)
        t15 = {True: [s.activation_t for s in by_dir["long"]],
               False: [s.activation_t for s in by_dir["short"]]}
        m1 = m1sim.load_m1(y, HERE)
        if not m1[0]:
            continue
        idx15 = {b.t: i for i, b in enumerate(b15)}

        for sig in [s for s in sigs if s.entry_time.year == y]:
            # el barrido y el desplazamiento M15 suelen ocurrir dentro de la propia
            # vela CISD; el retesteo, en la vela de entrada
            ini = sig.entry_time - timedelta(hours=lookback_h)
            fin = sig.entry_time + timedelta(hours=ventana_h)
            lst = by_dir[sig.direction]
            arr = t15[sig.direction == "long"]
            k = bisect.bisect_left(arr, ini)
            elegido = None
            fill_t = None
            while k < len(lst) and lst[k].activation_t < fin:
                s = lst[k]
                # retesteo del borde de la zona dentro de la ventana
                j = idx15.get(s.activation_t)
                if j is not None:
                    for jj in range(j + 1, len(b15)):
                        if b15[jj].t >= fin:
                            break
                        if b15[jj].t < sig.entry_time:      # el fill no puede ser previo a la entrada
                            continue
                        nivel = nivel_entrada(s, entry_mode)
                        tocado = (b15[jj].l <= nivel) if s.is_bull else (b15[jj].h >= nivel)
                        if tocado:
                            elegido, fill_t = s, b15[jj].t
                            break
                if elegido is not None:
                    break
                k += 1

            if elegido is None:
                ops.append(dict(sig=sig, setup=None, result="sin setup", r=0.0))
                continue

            s = elegido
            if sl_mode == "breaker":
                sl = (s.zone_bot - buffer_p * PIP) if s.is_bull else (s.zone_top + buffer_p * PIP)
            else:  # extremo de la manipulación
                sl = (s.manip_extreme - buffer_p * PIP) if s.is_bull else (s.manip_extreme + buffer_p * PIP)
            entry = nivel_entrada(s, entry_mode)
            risk = abs(entry - sl)
            if risk < min_risk_p * PIP:      # stops irreales frente al spread
                ops.append(dict(sig=sig, setup=None, result="riesgo mínimo", r=0.0))
                continue
            tp = entry + r_target * risk if s.is_bull else entry - r_target * risk
            res, r, exit_t = simular(m1, fill_t, entry, sl, tp, max_hours)
            r_neto = r - coste_p * PIP / risk
            ops.append(dict(sig=sig, setup=s, fill_t=fill_t, entry=entry, sl=sl, tp=tp,
                            result=res, r=r, r_neto=r_neto, riesgo_p=risk / PIP, exit_t=exit_t))
        if verbose:
            print(f"  {y} procesado", flush=True)
    return ops


def resumen(ops, etiqueta):
    hechas = [o for o in ops if o["result"] in ("TP", "SL", "tiempo")]
    sin = sum(1 for o in ops if o["result"] in ("sin setup", "riesgo mínimo"))
    print(f"\n{etiqueta}")
    print(f"  señales CISD {len(ops)}   con entrada Unicorn {len(hechas)} "
          f"({len(hechas) / max(len(ops), 1) * 100:.0f} %)   sin setup {sin}")
    if not hechas:
        return
    w = [o for o in hechas if o["r"] > 0]
    R = sum(o["r"] for o in hechas)
    Rn = sum(o["r_neto"] for o in hechas)
    print(f"  WR {len(w) / len(hechas) * 100:.1f} %   R/op bruto {R / len(hechas):+.3f}   "
          f"neto {Rn / len(hechas):+.3f}   R total neto {Rn:+.1f}   "
          f"riesgo mediano {st.median(o['riesgo_p'] for o in hechas):.1f} pips")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--ventana", type=float, default=4.0, help="horas desde la apertura de la vela de entrada")
    ap.add_argument("--lookback", type=float, default=4.0,
                    help="horas previas a la entrada en las que el setup puede activarse")
    ap.add_argument("--r", type=float, default=1.5)
    ap.add_argument("--sl", default="breaker", choices=["breaker", "manipulacion"])
    ap.add_argument("--buffer", type=float, default=1.0, help="pips de colchón bajo el extremo")
    ap.add_argument("--entrada", default="mitad", choices=["borde", "mitad", "lejano"],
                    help="'mitad' = línea del 50 % del breaker (la que el Unicorn ya dibuja)")
    ap.add_argument("--tf", type=int, default=15, choices=[5, 15], help="timeframe del Unicorn")
    ap.add_argument("--riesgo-min", type=float, default=4.0, help="pips mínimos de stop")
    ap.add_argument("--coste", type=float, default=1.0, help="pips de spread+slippage por operación")
    ap.add_argument("--max-horas", type=float, default=24.0)
    ap.add_argument("--solo-unicorn", action="store_true",
                    help="exigir el solape con FVG (por defecto valen también los breakers sin FVG: "
                         "rinden igual y doblan la muestra)")
    ap.add_argument("--csv", default="")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    years = bt.parse_years(a.years)
    ops = run(years, a.ventana, a.r, a.sl, a.buffer, a.max_horas, a.solo_unicorn, not a.quiet,
              a.lookback, a.entrada, a.riesgo_min, a.coste, a.tf)
    resumen(ops, f"CISD H4 + Unicorn M{a.tf} · activación −{a.lookback} h → +{a.ventana} h · SL {a.sl} · TP {a.r}R")

    hechas = [o for o in ops if o["result"] in ("TP", "SL", "tiempo")]
    for tier in ("A", "B", "Corr"):
        sub = [o for o in hechas if o["sig"].tier == tier]
        if sub:
            w = [o for o in sub if o["r"] > 0]
            print(f"     tier {tier:4} ops {len(sub):4}  WR {len(w) / len(sub) * 100:5.1f} %  "
                  f"R {sum(o['r'] for o in sub):+7.1f}")

    cal_path = os.path.join(HERE, "calendario_trades_2025.csv")
    if os.path.exists(cal_path):
        cal = {}
        with open(cal_path) as f:
            for r in csv.DictReader(f):
                y, m, d = map(int, r["fecha"].split("-"))
                if r["resultado"] in ("win", "loss"):
                    cal[(date(y, m, d), int(r["hora_entrada"]), r["dir"])] = r["resultado"]
        pares = [(cal[k], o) for o in hechas
                 if (k := (o["sig"].entry_time.date(), o["sig"].entry_time.hour,
                           o["sig"].direction)) in cal]
        if pares:
            ac = sum(1 for m, o in pares if (m == "win") == (o["r"] > 0))
            print(f"\n  Contraste con el calendario 2025: n={len(pares)}  "
                  f"coincide con tu marca {ac / len(pares) * 100:.1f} %  "
                  f"(tu acierto {sum(1 for m, _ in pares if m == 'win') / len(pares) * 100:.1f} %, "
                  f"simulado {sum(1 for _, o in pares if o['r'] > 0) / len(pares) * 100:.1f} %)")

    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["senal_cisd", "entrada_cisd", "dir", "tier", "activacion_unicorn",
                        "fill", "entry", "sl", "tp", "riesgo_pips", "barrido", "resultado", "R"])
            for o in ops:
                s = o.get("setup")
                w.writerow([o["sig"].sig_time, o["sig"].entry_time, o["sig"].direction, o["sig"].tier,
                            s.activation_t if s else "", o.get("fill_t", ""),
                            round(o.get("entry", 0), 5), round(o.get("sl", 0), 5),
                            round(o.get("tp", 0), 5), round(o.get("riesgo_p", 0), 1),
                            s.sweep_label if s else "", o["result"], o["r"]])
        print(f"\nCSV: {a.csv}")


if __name__ == "__main__":
    main()
