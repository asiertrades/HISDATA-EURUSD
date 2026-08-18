#!/usr/bin/env python3
"""
Simulación a resolución de minuto de las señales del motor CISD H4.

El backtester en H4 no puede resolver el orden intra-vela (¿tocó antes el stop o
el objetivo?), y con entradas en retroceso y stops ajustados eso lo decide todo.
Aquí cada operación se camina minuto a minuto sobre los M1 del repo:

  1. desde la apertura de la vela de entrada se busca el retroceso (orden límite)
  2. una vez dentro, se recorre el precio minuto a minuto hasta SL, TP o tiempo

Uso:
    python3 cisd_m1_sim.py --years 2025 --entry-offset 6 --sl-pips 10 --r 2.5
    python3 cisd_m1_sim.py --years 2001-2025 --entry-offset 6 --sl-pips 10 --r 2.5 --csv ops.csv
"""

from __future__ import annotations

import argparse
import bisect
import csv
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import cisd_forever_backtest as bt

PIP = 0.0001


@dataclass
class Trade:
    sig_time: datetime
    entry_time: datetime
    direction: str
    tier: str
    fill_time: datetime | None
    entry: float
    sl: float
    tp: float
    result: str
    r: float
    mfe: float          # máxima excursión favorable en pips antes de cerrar
    mae: float


def load_m1(year: int, data_dir: str):
    path = os.path.join(data_dir, f"DAT_ASCII_EURUSD_M1_{year}.csv")
    ts, o, h, l, c = [], [], [], [], []
    if not os.path.exists(path):
        return ts, o, h, l, c
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split(";")
            if len(parts) < 5:
                continue
            ts.append(datetime.strptime(parts[0], "%Y%m%d %H%M%S"))
            o.append(float(parts[1])); h.append(float(parts[2]))
            l.append(float(parts[3])); c.append(float(parts[4]))
    return ts, o, h, l, c


def simulate_m1(signals, year_data, entry_offset: float, sl_pips: float,
                r_target: float, max_hours: int, sl_mode: str) -> list[Trade]:
    ts, mo, mh, ml, mc = year_data
    out: list[Trade] = []
    for s in signals:
        start = bisect.bisect_left(ts, s.entry_time)
        end = bisect.bisect_left(ts, s.entry_time + timedelta(hours=max_hours))
        if start >= len(ts) or start >= end:
            continue
        long = s.direction == "long"
        limit = (s.sig_close - entry_offset * PIP) if long else (s.sig_close + entry_offset * PIP)
        if entry_offset <= 0:
            limit = mo[start]

        entry = None
        fill_i = None
        for i in range(start, end):
            if entry_offset <= 0:
                entry, fill_i = mo[start], start
                break
            if (ml[i] <= limit) if long else (mh[i] >= limit):
                entry, fill_i = limit, i
                break
        if entry is None:
            out.append(Trade(s.sig_time, s.entry_time, s.direction, s.tier, None,
                             0.0, 0.0, 0.0, "sin entrada", 0.0, 0.0, 0.0))
            continue

        if sl_mode == "pips":
            sl = entry - sl_pips * PIP if long else entry + sl_pips * PIP
        elif sl_mode == "extremo":
            sl = s.lo if long else s.hi
        else:   # "senal": extremo de la vela CISD más un colchón mínimo
            sl = min(s.lo, entry - sl_pips * PIP) if long else max(s.hi, entry + sl_pips * PIP)
        risk = max(abs(entry - sl), PIP)
        tp = entry + r_target * risk if long else entry - r_target * risk

        result, r = "tiempo", 0.0
        mfe = mae = 0.0
        last = mc[end - 1]
        for i in range(fill_i, end):
            fav = (mh[i] - entry) if long else (entry - ml[i])
            adv = (entry - ml[i]) if long else (mh[i] - entry)
            mfe = max(mfe, fav / PIP)
            mae = max(mae, adv / PIP)
            hit_sl = ml[i] <= sl if long else mh[i] >= sl
            hit_tp = mh[i] >= tp if long else ml[i] <= tp
            if hit_sl and hit_tp:
                # dentro del mismo minuto: se asume el peor caso
                result, r = "SL", -1.0
                break
            if hit_sl:
                result, r = "SL", -1.0
                break
            if hit_tp:
                result, r = "TP", r_target
                break
        else:
            r = ((last - entry) if long else (entry - last)) / risk
        out.append(Trade(s.sig_time, s.entry_time, s.direction, s.tier,
                         ts[fill_i], entry, sl, tp, result, round(r, 3),
                         round(mfe, 1), round(mae, 1)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--data-dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--entry-offset", type=float, default=6.0,
                    help="pips de retroceso desde el cierre del CISD (0 = a mercado)")
    ap.add_argument("--sl-pips", type=float, default=10.0)
    ap.add_argument("--sl-mode", default="pips", choices=["pips", "extremo", "senal"])
    ap.add_argument("--r", type=float, default=2.5)
    ap.add_argument("--max-hours", type=int, default=24)
    ap.add_argument("--hour9", action="store_true")
    ap.add_argument("--csv", default="")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    years = bt.parse_years(args.years)
    bars = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), args.data_dir)
    sigs = bt.run_engine(bars, bt.Params(hour9=args.hour9))

    trades: list[Trade] = []
    for y in years:
        ysig = [s for s in sigs if s.entry_time.year == y]
        if not ysig:
            continue
        data = load_m1(y, args.data_dir)
        if not data[0]:
            continue
        trades.extend(simulate_m1(ysig, data, args.entry_offset, args.sl_pips,
                                  args.r, args.max_hours, args.sl_mode))

    done = [t for t in trades if t.result in ("TP", "SL", "tiempo")]
    wins = [t for t in done if t.r > 0]
    if not args.quiet:
        for t in trades[:40]:
            print(f"{t.entry_time:%Y-%m-%d %H:%M} {t.direction:5} {t.tier:4} "
                  f"{t.result:11} R={t.r:+5.2f} MFE={t.mfe:5.1f}p MAE={t.mae:5.1f}p")
    print(f"\nAños {args.years} · retroceso {args.entry_offset}p · SL {args.sl_mode} "
          f"{args.sl_pips}p · TP {args.r}R · máx {args.max_hours}h")
    print(f"Señales {len(trades)}  operadas {len(done)}  sin entrada "
          f"{sum(1 for t in trades if t.result == 'sin entrada')}")
    if done:
        print(f"WR {len(wins) / len(done) * 100:.1f}%   R total {sum(t.r for t in done):+.1f}   "
              f"R/op {sum(t.r for t in done) / len(done):+.3f}")
        for tier in ("A", "B", "Corr"):
            sub = [t for t in done if t.tier == tier]
            if sub:
                w = [t for t in sub if t.r > 0]
                print(f"   tier {tier:4} ops {len(sub):4}  WR {len(w) / len(sub) * 100:5.1f}%  "
                      f"R {sum(t.r for t in sub):+7.1f}")
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["senal", "entrada", "dir", "tier", "fill", "entry", "sl", "tp",
                        "resultado", "R", "MFE_p", "MAE_p"])
            for t in trades:
                w.writerow([t.sig_time, t.entry_time, t.direction, t.tier, t.fill_time,
                            round(t.entry, 5), round(t.sl, 5), round(t.tp, 5),
                            t.result, t.r, t.mfe, t.mae])
        print(f"CSV: {args.csv}")


if __name__ == "__main__":
    main()
