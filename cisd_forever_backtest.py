#!/usr/bin/env python3
"""
Backtester del motor CISD H4 (+ módulos Forever Model) sobre los CSV M1 del repo.

Replica bar a bar la lógica de "CLAUDE CISD H4 v5" tal cual está en Pine, para
poder contrastar las señales con el calendario real de operaciones y afinar los
parámetros antes de tocar el indicador.

Datos: DAT_ASCII_EURUSD_M1_YYYY.csv  (timestamps en hora de Nueva York, con DST:
la apertura semanal cae siempre a las 17:00, invierno y verano).

Velas H4 alineadas a la sesión FX (17, 21, 01, 05, 09, 13 NY), igual que TradingView.

Uso:
    python3 cisd_forever_backtest.py --years 2025
    python3 cisd_forever_backtest.py --years 2000-2025 --csv trades.csv
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

PIP = 0.0001
MINTICK = 0.00001
BAR_HOURS = (17, 21, 1, 5, 9, 13)


# ══════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════
@dataclass
class Bar:
    t: datetime          # apertura de la vela (hora NY)
    o: float
    h: float
    l: float
    c: float
    hour: int
    dow: int             # día de la semana del CIERRE (como dayofweek(time_close))


def bucket_start(ts: datetime) -> datetime:
    """Inicio de la vela H4 (sesión FX 17:00 NY) a la que pertenece el minuto."""
    h = ts.hour
    if h >= 17:
        base = ts.replace(hour=17, minute=0, second=0, microsecond=0)
    elif h >= 13:
        base = ts.replace(hour=13, minute=0, second=0, microsecond=0)
    elif h >= 9:
        base = ts.replace(hour=9, minute=0, second=0, microsecond=0)
    elif h >= 5:
        base = ts.replace(hour=5, minute=0, second=0, microsecond=0)
    elif h >= 1:
        base = ts.replace(hour=1, minute=0, second=0, microsecond=0)
    else:  # 00:xx pertenece a la vela de las 21:00 del día anterior
        base = (ts - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
    return base


CACHE_NAME = "h4_eurusd_cache.csv"


def load_h4_cached(years: list[int], data_dir: str) -> list[Bar]:
    """Velas H4 con caché en disco: la primera llamada construye el CSV desde los M1."""
    cache = os.path.join(data_dir, CACHE_NAME)
    if not os.path.exists(cache):
        all_years = list(range(2000, 2026))
        bars = load_h4(all_years, data_dir)
        with open(cache, "w", newline="") as f:
            w = csv.writer(f)
            for b in bars:
                w.writerow([b.t.strftime("%Y%m%d%H%M"), f"{b.o:.5f}", f"{b.h:.5f}",
                            f"{b.l:.5f}", f"{b.c:.5f}"])
    out: list[Bar] = []
    wanted = set(years)
    with open(cache) as f:
        for row in csv.reader(f):
            t = datetime.strptime(row[0], "%Y%m%d%H%M")
            if t.year in wanted:
                out.append(_mk_bar(t, float(row[1]), float(row[2]), float(row[3]), float(row[4])))
    return out


def load_h4(years: list[int], data_dir: str) -> list[Bar]:
    bars: list[Bar] = []
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
                po, ph, pl, pc = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                key = bucket_start(ts)
                if key != cur_key:
                    if cur_key is not None:
                        bars.append(_mk_bar(cur_key, o, h, l, c))
                    cur_key, o, h, l, c = key, po, ph, pl, pc
                else:
                    h = max(h, ph)
                    l = min(l, pl)
                    c = pc
    if cur_key is not None:
        bars.append(_mk_bar(cur_key, o, h, l, c))
    return bars


def _mk_bar(t: datetime, o: float, h: float, l: float, c: float) -> Bar:
    close_t = t + timedelta(hours=4)
    # dayofweek de Pine: domingo=1 ... sábado=7 ; aquí solo se usa "es viernes"
    return Bar(t=t, o=o, h=h, l=l, c=c, hour=t.hour, dow=(close_t.weekday() + 1) % 7 + 1)


# ══════════════════════════════════════════════════════════════════
# PARÁMETROS (mismos nombres/valores que los inputs del indicador)
# ══════════════════════════════════════════════════════════════════
@dataclass
class Params:
    obMinBody: float = 0.40
    cisdMinBody: float = 0.55
    perDir: bool = True
    doubtPersist: bool = True
    hour9: bool = False
    tierB: bool = True
    bMinBody: float = 1.0
    noBFri: bool = True
    noB21: bool = True
    bWick: bool = True
    bRango: bool = False
    bPrevDay: bool = False
    bPrevPips: float = 40.0
    # ── módulos Forever Model
    fvgMode: str = "Off"          # Off | Señal dentro de FVG | FVG activo a favor
    fvgMax: int = 8
    # ── filtro de calidad (calibrado con el calendario 2025)
    qOn: bool = False
    qMinBodyPips: float = 20.0    # cuerpo mínimo de la vela CISD
    qMinBodyRatio: float = 0.50   # cuerpo / rango de la vela
    qMaxWick: float = 9.99        # mecha en contra / cuerpo (9.99 = desactivado)
    qMaxSweepExc: float = 8.0     # pips que el barrido excede el extremo de las 17:00
    # ── gestión
    entryMode: str = "open"       # open | zone
    slMode: str = "map"           # map | extremo | ob | pips
    slPips: float = 10.0          # solo para slMode="pips"
    tpMode: str = "R"             # R | erl_sesion | erl_fvg
    rTarget: float = 2.0
    maxBars: int = 6
    zoneBars: int = 3
    simCorr: bool = True
    singleTrade: bool = False     # True = una operación a la vez (como en el gráfico)
    tiers: tuple = ("A", "B", "Corr")


@dataclass
class Signal:
    sig_time: datetime
    entry_time: datetime
    direction: str      # long | short
    tier: str           # A | B | Corr
    sig_close: float
    body: float
    atr6: float
    ob: float | None
    hi: float
    lo: float
    # resultado (se rellena en la simulación)
    result: str = ""
    r: float = 0.0
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    fvg_ok: bool = True
    quality_ok: bool = True
    q_body: float = 0.0
    q_ratio: float = 0.0
    q_wick: float = 0.0
    q_exc: float = 0.0


# ══════════════════════════════════════════════════════════════════
# FVG DIARIO (Forever Model, para el filtro opcional)
# ══════════════════════════════════════════════════════════════════
@dataclass
class FVG:
    hi: float
    lo: float
    bull: bool
    mitigated: bool = False
    erl: float = 0.0


def daily_from_h4(bars: list[Bar]) -> list[tuple[int, float, float, float, float]]:
    """Devuelve (idx_ultima_vela_h4, o, h, l, c) por sesión diaria 17:00→17:00."""
    out = []
    o = h = l = c = None
    last_idx = -1
    for i, b in enumerate(bars):
        if b.hour == 17 or o is None:
            if o is not None:
                out.append((last_idx, o, h, l, c))
            o, h, l, c = b.o, b.h, b.l, b.c
        else:
            h, l, c = max(h, b.h), min(l, b.l), b.c
        last_idx = i
    if o is not None:
        out.append((last_idx, o, h, l, c))
    return out


# ══════════════════════════════════════════════════════════════════
# MOTOR CISD (traducción literal del Pine)
# ══════════════════════════════════════════════════════════════════
def run_engine(bars: list[Bar], p: Params) -> list[Signal]:
    signals: list[Signal] = []

    # FVG diarios (solo si el filtro está activo)
    fvgs: list[FVG] = []
    dailies = daily_from_h4(bars)
    daily_close_at: dict[int, int] = {}   # idx h4 -> índice de sesión que cierra ahí
    for di, (idx, *_rest) in enumerate(dailies):
        daily_close_at[idx] = di

    refH = refL = None
    sesHi = sesLo = None          # extremos de la sesión (para el exceso del barrido)
    lBullO = lBullL = lBearO = lBearH = None
    aBullO = aBearO = None
    sessHi = sessLo = None
    sess17Open = None
    prevNet = None
    sweptH = sweptL = False
    fABear = fABull = fBBear = fBBull = False
    doubtBear = doubtBull = False
    dBearOBo = dBullOBo = None
    sigBearHi = sigBearOp = sigBullLo = sigBullOp = None
    prev_bearSig = prev_bullSig = False
    ranges: list[float] = []

    for i, b in enumerate(bars):
        rng = max(b.h - b.l, 0.00001)
        body = abs(b.c - b.o)
        bodyR = body / rng
        isBull = b.c > b.o
        isBear = b.c < b.o
        upWick = (b.h - b.c) if isBull else (b.h - b.o)
        dnWick = (b.o - b.l) if isBull else (b.c - b.l)
        atr6 = sum(ranges[-6:]) / 6 if len(ranges) >= 6 else rng

        bearSig = bullSig = bearSigB = bullSigB = False
        corrBull = corrBear = False
        obBear = obBull = None

        is17 = b.hour == 17

        # ── STEP 1: reset de sesión
        if is17:
            prevNet = None if sess17Open is None else bars[i - 1].c - sess17Open
            sess17Open = b.o
            refH, refL = b.h, b.l
            sesHi, sesLo = b.h, b.l
            sweptH = sweptL = False
            fABear = fABull = fBBear = fBBull = False
            doubtBear = doubtBull = False
            dBearOBo = dBullOBo = None
            lBullO = lBullL = lBearO = lBearH = None
            aBullO = aBearO = None

        if sesHi is not None and not is17:
            sesHi, sesLo = max(sesHi, b.h), min(sesLo, b.l)

        doneA = (fABear and fABull) if p.perDir else (fABear or fABull)

        # ── STEP 2: OB tier A
        if refH is not None and bodyR >= p.obMinBody:
            if isBull:
                lBullO, lBullL = b.o, b.l
            if isBear:
                lBearO, lBearH = b.o, b.h

        # ── STEP 3: barridos
        if refH is not None and not doneA:
            if not sweptH and b.h > refH:
                sweptH = True
            if not sweptL and b.l < refL:
                sweptL = True

        validCISD = b.hour in (21, 1, 5) or (p.hour9 and b.hour == 9)
        fABearBar = fABullBar = False

        # ── STEP 5: resolución de dudosos
        if not doneA and validCISD:
            if doubtBear and not fABear:
                if isBear and bodyR >= p.cisdMinBody and dnWick < body:
                    bearSig = True
                    fABear = fABearBar = True
                    doubtBear = False
                    sigBearHi, sigBearOp = b.h, b.o
                    obBear = dBearOBo
                elif p.doubtPersist:
                    if isBull:
                        doubtBear = False
                else:
                    doubtBear = False
            if doubtBull and not fABull:
                if isBull and bodyR >= p.cisdMinBody and upWick < body:
                    bullSig = True
                    fABull = fABullBar = True
                    doubtBull = False
                    sigBullLo, sigBullOp = b.l, b.o
                    obBull = dBullOBo
                elif p.doubtPersist:
                    if isBear:
                        doubtBull = False
                else:
                    doubtBull = False

        doneA = (fABear and fABull) if p.perDir else (fABear or fABull)

        # ── STEP 4: CISD tier A
        if not doneA and validCISD:
            if sweptH and lBullO is not None and not fABear:
                if isBear and b.c < lBullO:
                    bearBodyR = body / max(body + dnWick, 0.00001)
                    clean = bearBodyR >= p.cisdMinBody and dnWick < body and b.c < lBullL
                    if clean:
                        bearSig = True
                        fABear = fABearBar = True
                        sigBearHi, sigBearOp = b.h, b.o
                        obBear = lBullO
                    elif not doubtBear:
                        doubtBear = True
                        dBearOBo = lBullO

            doneA2 = (fABear and fABull) if p.perDir else (fABear or fABull)

            if not doneA2 and sweptL and lBearO is not None and not fABull:
                if isBull and b.c > lBearO:
                    bullBodyR = body / max(body + upWick, 0.00001)
                    clean = bullBodyR >= p.cisdMinBody and upWick < body and b.c > lBearH
                    if clean:
                        bullSig = True
                        fABull = fABullBar = True
                        sigBullLo, sigBullOp = b.l, b.o
                        obBull = lBearO
                    elif not doubtBull:
                        doubtBull = True
                        dBullOBo = lBearO

        # ── STEP 6: tier B universal
        entryFri = b.dow == 6   # dayofweek.friday en Pine
        if (p.tierB and validCISD and (sweptH or sweptL)
                and not (p.noBFri and entryFri) and not (p.noB21 and b.hour == 21)):
            wickOKbear = (not p.bWick) or dnWick < body
            wickOKbull = (not p.bWick) or upWick < body
            rangoOKbear = (not p.bRango) or (sessLo is not None and b.c < sessLo)
            rangoOKbull = (not p.bRango) or (sessHi is not None and b.c > sessHi)
            prevOKbear = (not p.bPrevDay) or prevNet is None or prevNet < p.bPrevPips * PIP
            prevOKbull = (not p.bPrevDay) or prevNet is None or prevNet > -p.bPrevPips * PIP
            if (not fABear and not fBBear and not fABearBar and aBullO is not None
                    and isBear and b.c < aBullO and wickOKbear and rangoOKbear and prevOKbear):
                bearSigB = True
                fBBear = True
                obBear = aBullO
            if (not fABull and not fBBull and not fABullBar and aBearO is not None
                    and isBull and b.c > aBearO and wickOKbull and rangoOKbull and prevOKbull):
                bullSigB = True
                fBBull = True
                obBull = aBearO

        # ── OB tier B (se actualiza al final)
        if refH is not None and body >= p.bMinBody * PIP:
            if isBull:
                aBullO = b.o
            if isBear:
                aBearO = b.o

        # ── rango de sesión (se actualiza al final)
        if is17:
            sessHi, sessLo = b.h, b.l
        elif sessHi is not None:
            sessHi, sessLo = max(sessHi, b.h), min(sessLo, b.l)

        # ── correcciones
        if prev_bearSig and sigBearHi is not None and (b.h > sigBearHi or b.c > sigBearOp):
            corrBull = True
        if prev_bullSig and sigBullLo is not None and (b.l < sigBullLo or b.c < sigBullOp):
            corrBear = True

        # ── FVG diario: mantenimiento (después de cerrar la vela)
        if p.fvgMode != "Off":
            _update_fvgs(fvgs, b, p)
            di = daily_close_at.get(i)
            if di is not None and di >= 3:
                _, _, h1, l1, c1 = dailies[di]
                _, _, h2, l2, _ = dailies[di - 1]
                _, _, h3, l3, _ = dailies[di - 2]
                if l1 > h3:
                    fvgs.append(FVG(hi=l1, lo=h3, bull=True, erl=max(h1, h2)))
                if h1 < l3:
                    fvgs.append(FVG(hi=l3, lo=h1, bull=False, erl=min(l1, l2)))
                while len(fvgs) > p.fvgMax:
                    fvgs.pop(0)

        # ── registrar señales
        if i + 1 < len(bars):
            nxt = bars[i + 1]
            for flag, direction, tier in (
                (bearSig, "short", "A"), (bullSig, "long", "A"),
                (bearSigB, "short", "B"), (bullSigB, "long", "B"),
                (corrBear, "short", "Corr"), (corrBull, "long", "Corr"),
            ):
                if not flag:
                    continue
                if tier == "Corr" and not p.simCorr:
                    continue
                ob = obBull if direction == "long" else obBear
                fvg_ok = _fvg_filter(fvgs, direction == "long", b, p)
                is_long = direction == "long"
                q_body = body / PIP
                q_ratio = bodyR
                q_wick = (upWick if is_long else dnWick) / max(body, 1e-9)
                q_exc = ((refL - sesLo) if is_long else (sesHi - refH)) / PIP if refH is not None else 0.0
                quality_ok = (not p.qOn) or (
                    q_body >= p.qMinBodyPips and q_ratio >= p.qMinBodyRatio
                    and q_wick <= p.qMaxWick and q_exc <= p.qMaxSweepExc)
                signals.append(Signal(
                    sig_time=b.t, entry_time=nxt.t, direction=direction, tier=tier,
                    sig_close=b.c, body=body, atr6=atr6, ob=ob, hi=b.h, lo=b.l,
                    fvg_ok=fvg_ok, quality_ok=quality_ok,
                    q_body=q_body, q_ratio=q_ratio, q_wick=q_wick, q_exc=q_exc,
                ))

        prev_bearSig, prev_bullSig = bearSig, bullSig
        ranges.append(rng)

    return signals


def _update_fvgs(fvgs: list[FVG], b: Bar, p: Params) -> None:
    for f in list(fvgs):
        if not f.mitigated:
            f.erl = max(f.erl, b.h) if f.bull else min(f.erl, b.l)
            if (b.l <= f.hi) if f.bull else (b.h >= f.lo):
                f.mitigated = True
        elif (b.h > f.erl) if f.bull else (b.l < f.erl):
            fvgs.remove(f)


def _fvg_filter(fvgs: list[FVG], want_bull: bool, b: Bar, p: Params) -> bool:
    if p.fvgMode == "Off":
        return True
    same = [f for f in fvgs if f.bull == want_bull]
    if p.fvgMode == "FVG activo a favor":
        return len(same) > 0
    if p.fvgMode == "Señal dentro de FVG":
        return any(b.l <= f.hi and b.h >= f.lo for f in same)
    return True


# ══════════════════════════════════════════════════════════════════
# SIMULACIÓN DE OPERACIONES
# ══════════════════════════════════════════════════════════════════
def simulate(bars: list[Bar], signals: list[Signal], p: Params) -> list[Signal]:
    idx_of = {b.t: i for i, b in enumerate(bars)}
    sess_extremes = _session_extremes(bars)
    out: list[Signal] = []
    busy_until = -1

    for s in signals:
        if s.tier not in p.tiers:
            s.result = "excluida"
            out.append(s)
            continue
        if not s.fvg_ok or not s.quality_ok:
            s.result = "filtrada"
            out.append(s)
            continue
        si = idx_of[s.sig_time]
        if p.singleTrade and si <= busy_until:
            s.result = "solapada"
            out.append(s)
            continue

        a6 = s.atr6 if s.atr6 else (s.hi - s.lo)
        bd = max(s.body, a6 * 0.20, PIP * 2)
        sz = bd / max(a6, MINTICK)
        f1 = 0.25 if sz >= 1.5 else (0.40 if sz >= 0.75 else 0.55)
        f2 = 0.45 if sz >= 1.5 else (0.65 if sz >= 0.75 else 0.90)
        fi = 0.65 if sz >= 1.5 else 1.00
        long = s.direction == "long"

        if p.slMode == "map":
            sl = s.sig_close - fi * bd if long else s.sig_close + fi * bd
        elif p.slMode == "pips":
            sl = s.sig_close - p.slPips * PIP if long else s.sig_close + p.slPips * PIP
        elif p.slMode == "extremo":
            sl = s.lo if long else s.hi
        else:
            sl = s.ob if s.ob is not None else None
            if sl is None or (sl >= s.sig_close if long else sl <= s.sig_close):
                sl = s.sig_close - fi * bd if long else s.sig_close + fi * bd

        limit = s.sig_close - (f1 + f2) / 2 * bd if long else s.sig_close + (f1 + f2) / 2 * bd

        # ── ejecución
        entry = None
        fill_i = None
        for j in range(si + 1, min(si + 1 + p.zoneBars, len(bars))):
            bar = bars[j]
            if p.entryMode == "open":
                entry, fill_i = bar.o, j
                break
            touched = bar.l <= limit if long else bar.h >= limit
            if touched:
                entry, fill_i = limit, j
                break
        if entry is None:
            s.result = "sin entrada"
            out.append(s)
            continue

        risk = max(abs(entry - sl), MINTICK)
        tp = entry + p.rTarget * risk if long else entry - p.rTarget * risk
        if p.tpMode == "erl_sesion":
            hi, lo = sess_extremes[fill_i]
            erl = hi if long else lo
            if erl is not None and ((erl - entry) if long else (entry - erl)) >= 0.5 * risk:
                tp = erl

        s.entry, s.sl, s.tp = entry, sl, tp
        result, r, exit_i = "tiempo", 0.0, min(fill_i + p.maxBars, len(bars) - 1)
        for j in range(fill_i, min(fill_i + p.maxBars + 1, len(bars))):
            bar = bars[j]
            hit_sl = bar.l <= sl if long else bar.h >= sl
            hit_tp = bar.h >= tp if long else bar.l <= tp
            if hit_sl:
                result, r, exit_i = "SL", -1.0, j
                break
            if hit_tp:
                result, r, exit_i = "TP", abs(tp - entry) / risk, j
                break
        else:
            bar = bars[exit_i]
            r = ((bar.c - entry) if long else (entry - bar.c)) / risk
            result = "tiempo"
        s.result, s.r = result, round(r, 3)
        busy_until = exit_i
        out.append(s)
    return out


def _session_extremes(bars: list[Bar]) -> list[tuple[float | None, float | None]]:
    out = []
    hi = lo = None
    for b in bars:
        if b.hour == 17 or hi is None:
            hi, lo = b.h, b.l
        else:
            hi, lo = max(hi, b.h), min(lo, b.l)
        out.append((hi, lo))
    return out


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════
def parse_years(spec: str) -> list[int]:
    years: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            a, b = chunk.split("-")
            years.extend(range(int(a), int(b) + 1))
        else:
            years.append(int(chunk))
    return years


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--data-dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--csv", default="")
    ap.add_argument("--fvg", default="Off",
                    choices=["Off", "Señal dentro de FVG", "FVG activo a favor"])
    ap.add_argument("--entry", default="open", choices=["open", "zone"])
    ap.add_argument("--sl", default="map", choices=["map", "extremo", "ob", "pips"])
    ap.add_argument("--sl-pips", type=float, default=10.0)
    ap.add_argument("--tp", default="R", choices=["R", "erl_sesion"])
    ap.add_argument("--r", type=float, default=2.0)
    ap.add_argument("--max-bars", type=int, default=6)
    ap.add_argument("--hour9", action="store_true")
    ap.add_argument("--no-corr", action="store_true")
    ap.add_argument("--no-tierb", action="store_true")
    ap.add_argument("--single-trade", action="store_true",
                    help="una operación a la vez (por defecto se evalúa cada señal por separado)")
    ap.add_argument("--tiers", default="A,B,Corr")
    ap.add_argument("--calidad", action="store_true",
                    help="activa el filtro de calidad calibrado con el calendario 2025")
    ap.add_argument("--q-body", type=float, default=20.0)
    ap.add_argument("--q-ratio", type=float, default=0.50)
    ap.add_argument("--q-wick", type=float, default=9.99)
    ap.add_argument("--q-exc", type=float, default=8.0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    years = parse_years(args.years)
    # una vela extra de contexto: se carga el año anterior si existe
    load_years = sorted(set(years) | {min(years) - 1})
    bars = load_h4_cached(load_years, args.data_dir)

    p = Params(fvgMode=args.fvg, entryMode=args.entry, slMode=args.sl, slPips=args.sl_pips, tpMode=args.tp,
               rTarget=args.r, maxBars=args.max_bars, hour9=args.hour9,
               simCorr=not args.no_corr, tierB=not args.no_tierb,
               singleTrade=args.single_trade,
               tiers=tuple(t.strip() for t in args.tiers.split(",")),
               qOn=args.calidad, qMinBodyPips=args.q_body, qMinBodyRatio=args.q_ratio,
               qMaxWick=args.q_wick, qMaxSweepExc=args.q_exc)

    sigs = run_engine(bars, p)
    sigs = simulate(bars, sigs, p)
    sigs = [s for s in sigs if s.sig_time.year in years]

    if not args.quiet:
        print(f"{'Señal (NY)':17} {'Entrada (NY)':17} {'Dir':6} {'Tier':5} {'Res':10} {'R':>6}")
        print("-" * 70)
        for s in sigs:
            print(f"{s.sig_time:%Y-%m-%d %H:%M}  {s.entry_time:%Y-%m-%d %H:%M}  "
                  f"{s.direction:6} {s.tier:5} {s.result:10} {s.r:>6.2f}")

    traded = [s for s in sigs if s.result in ("TP", "SL", "tiempo")]
    wins = [s for s in traded if s.r > 0]
    print()
    print(f"Años: {args.years}   Velas H4: {len(bars)}")
    print(f"Señales: {len(sigs)}   Operadas: {len(traded)}   "
          f"Sin entrada: {sum(1 for s in sigs if s.result == 'sin entrada')}   "
          f"Solapadas: {sum(1 for s in sigs if s.result == 'solapada')}   "
          f"Filtradas: {sum(1 for s in sigs if s.result == 'filtrada')}")
    if traded:
        print(f"WR: {len(wins) / len(traded) * 100:.1f}%   R total: {sum(s.r for s in traded):+.1f}   "
              f"R medio: {sum(s.r for s in traded) / len(traded):+.2f}")
    for tier in ("A", "B", "Corr"):
        t = [s for s in traded if s.tier == tier]
        if t:
            w = [s for s in t if s.r > 0]
            print(f"  Tier {tier:4} ops {len(t):4}  WR {len(w) / len(t) * 100:5.1f}%  "
                  f"R {sum(s.r for s in t):+7.1f}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["senal_ny", "entrada_ny", "dir", "tier", "resultado", "R",
                        "entry", "sl", "tp", "close_senal"])
            for s in sigs:
                w.writerow([s.sig_time.strftime("%Y-%m-%d %H:%M"),
                            s.entry_time.strftime("%Y-%m-%d %H:%M"),
                            s.direction, s.tier, s.result, s.r,
                            round(s.entry, 5), round(s.sl, 5), round(s.tp, 5), round(s.sig_close, 5)])
        print(f"\nCSV: {args.csv}")


if __name__ == "__main__":
    main()
