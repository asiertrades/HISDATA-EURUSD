#!/usr/bin/env python3
"""Construcción y caché de velas LTF (M5 / M15) a partir de los M1 del repo."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))


@dataclass
class LBar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def _cache_path(minutes: int) -> str:
    return os.path.join(HERE, f"m{minutes}_eurusd_cache.csv")


def build(minutes: int, years: list[int], data_dir: str = HERE) -> None:
    rows = []
    cur_key = None
    o = h = l = c = 0.0
    for y in years:
        path = os.path.join(data_dir, f"DAT_ASCII_EURUSD_M1_{y}.csv")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                parts = line.rstrip("\n").split(";")
                if len(parts) < 5:
                    continue
                ts = datetime.strptime(parts[0], "%Y%m%d %H%M%S")
                key = ts.replace(minute=(ts.minute // minutes) * minutes, second=0, microsecond=0)
                po, ph, pl, pc = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                if key != cur_key:
                    if cur_key is not None:
                        rows.append((cur_key, o, h, l, c))
                    cur_key, o, h, l, c = key, po, ph, pl, pc
                else:
                    h, l, c = max(h, ph), min(l, pl), pc
    if cur_key is not None:
        rows.append((cur_key, o, h, l, c))
    with open(_cache_path(minutes), "w", newline="") as f:
        w = csv.writer(f)
        for t, o, h, l, c in rows:
            w.writerow([t.strftime("%Y%m%d%H%M"), f"{o:.5f}", f"{h:.5f}", f"{l:.5f}", f"{c:.5f}"])


def load(minutes: int, years: list[int], data_dir: str = HERE) -> list[LBar]:
    path = _cache_path(minutes)
    if not os.path.exists(path):
        build(minutes, list(range(2000, 2026)), data_dir)
    out = []
    want = set(years)
    with open(path) as f:
        for row in csv.reader(f):
            t = datetime.strptime(row[0], "%Y%m%d%H%M")
            if t.year in want:
                out.append(LBar(t, float(row[1]), float(row[2]), float(row[3]), float(row[4])))
    return out


if __name__ == "__main__":
    import sys
    mins = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    yrs = [int(y) for y in sys.argv[2:]] or [2025]
    build(mins, list(range(2000, 2026)))
    b = load(mins, yrs)
    print(f"M{mins}: {len(b)} velas para {yrs}   primera {b[0].t}  última {b[-1].t}")
