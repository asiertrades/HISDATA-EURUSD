#!/usr/bin/env python3
"""
¿Cuántas señales del CISD se pueden anticipar dentro de la vela, y a qué precio
en señales falsas?

Recorre el motor CISD normal y, en cada vela de hora válida (21:00 / 01:00 /
05:00 NY), evalúa la señal como si la vela cerrase en cada una de sus 16 velas
M15. Eso da la "señal provisional". Después compara:

    anticipada y confirmada al cierre  → adelanto limpio
    anticipada y NO confirmada         → RUIDO: señal falsa que hoy no existe
    confirmada sin haber sido anticipada → no se podía adelantar

Opcionalmente exige además que exista un setup Unicorn M15 en esa dirección
(el que da la entrada), que es como se operaría de verdad.
"""

from __future__ import annotations

import argparse
import collections
import os
from datetime import timedelta

import cisd_forever_backtest as bt
import ltf_bars
import unicorn_engine as ue

HERE = os.path.dirname(os.path.abspath(__file__))
PIP = 0.0001


_CACHE = {}


def analizar(years, p: bt.Params, exigir_unicorn: bool, verbose=True,
             desde_min: int = 0, calidad: bool = False):
    clave = tuple(years)
    if clave in _CACHE:
        bars, m15, setups_dir = _CACHE[clave]
    else:
        bars = bt.load_h4_cached(sorted(set(years) | {min(years) - 1}), HERE)
        m15 = {}
        setups_dir = {}
        for y in years:
            b15 = ltf_bars.load(15, [y - 1, y], HERE)
            m15[y] = b15
            st = ue.find_setups(b15, bars, unicorn_only=False)
            setups_dir[y] = {"long": sorted([s for s in st if s.is_bull], key=lambda x: x.activation_t),
                             "short": sorted([s for s in st if not s.is_bull], key=lambda x: x.activation_t)}
        _CACHE[clave] = (bars, m15, setups_dir)
    # índice de velas M15 por vela H4
    m15_por_h4 = collections.defaultdict(list)
    for y, b15 in m15.items():
        for b in b15:
            clave = b.t.replace(minute=0) - timedelta(hours=(b.t.hour - 17) % 4)
            m15_por_h4[clave].append(b)
    for k in m15_por_h4:
        m15_por_h4[k].sort(key=lambda x: x.t)

    eventos = []          # una fila por vela H4 de hora válida

    # ── estado del motor (idéntico a run_engine) ─────────────────
    refH = refL = None
    sesHi = sesLo = None
    lBullO = lBullL = lBearO = lBearH = None
    aBullO = aBearO = None
    sessHi = sessLo = None
    sess17Open = None
    prevNet = None
    sweptH = sweptL = False
    fABear = fABull = fBBear = fBBull = False
    doubtBear = doubtBull = False
    dBearOBo = dBullOBo = None

    for i, b in enumerate(bars):
        rng = max(b.h - b.l, 1e-5)
        body = abs(b.c - b.o)
        bodyR = body / rng
        isBull, isBear = b.c > b.o, b.c < b.o
        upWick = (b.h - b.c) if isBull else (b.h - b.o)
        dnWick = (b.o - b.l) if isBull else (b.c - b.l)
        is17 = b.hour == 17

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
        elif sesHi is not None:
            sesHi, sesLo = max(sesHi, b.h), min(sesLo, b.l)

        validCISD = b.hour in (21, 1, 5) or (p.hour9 and b.hour == 9)
        doneA = (fABear and fABull) if p.perDir else (fABear or fABull)

        # ── evaluación PROVISIONAL dentro de la vela ──────────────
        antic = {}
        if validCISD and b.t.year in years and refH is not None:
            estado = dict(sweptH=sweptH, sweptL=sweptL, doneA=doneA,
                          fABear=fABear, fABull=fABull, fBBear=fBBear, fBBull=fBBull,
                          doubtBear=doubtBear, doubtBull=doubtBull,
                          dBearOBo=dBearOBo, dBullOBo=dBullOBo,
                          lBullO=lBullO, lBullL=lBullL, lBearO=lBearO, lBearH=lBearH,
                          aBullO=aBullO, aBearO=aBearO)
            antic = _provisional(b, m15_por_h4.get(b.t, []), estado, p, refH, refL,
                                 sessHi, sessLo, prevNet,
                                 setups_dir.get(b.t.year, {}), exigir_unicorn,
                                 desde_min, calidad)

        # ── motor real, tal cual ──────────────────────────────────
        if refH is not None and bodyR >= p.obMinBody:
            if isBull:
                lBullO, lBullL = b.o, b.l
            if isBear:
                lBearO, lBearH = b.o, b.h
        if refH is not None and not doneA:
            if not sweptH and b.h > refH:
                sweptH = True
            if not sweptL and b.l < refL:
                sweptL = True

        bearSig = bullSig = bearSigB = bullSigB = False
        fABearBar = fABullBar = False
        if not doneA and validCISD:
            if doubtBear and not fABear:
                if isBear and bodyR >= p.cisdMinBody and dnWick < body:
                    bearSig = True; fABear = fABearBar = True; doubtBear = False
                elif p.doubtPersist:
                    if isBull:
                        doubtBear = False
                else:
                    doubtBear = False
            if doubtBull and not fABull:
                if isBull and bodyR >= p.cisdMinBody and upWick < body:
                    bullSig = True; fABull = fABullBar = True; doubtBull = False
                elif p.doubtPersist:
                    if isBear:
                        doubtBull = False
                else:
                    doubtBull = False
        doneA = (fABear and fABull) if p.perDir else (fABear or fABull)

        if not doneA and validCISD:
            if sweptH and lBullO is not None and not fABear and isBear and b.c < lBullO:
                r = body / max(body + dnWick, 1e-5)
                if r >= p.cisdMinBody and dnWick < body and b.c < lBullL:
                    bearSig = True; fABear = fABearBar = True
                elif not doubtBear:
                    doubtBear, dBearOBo = True, lBullO
            doneA2 = (fABear and fABull) if p.perDir else (fABear or fABull)
            if not doneA2 and sweptL and lBearO is not None and not fABull and isBull and b.c > lBearO:
                r = body / max(body + upWick, 1e-5)
                if r >= p.cisdMinBody and upWick < body and b.c > lBearH:
                    bullSig = True; fABull = fABullBar = True
                elif not doubtBull:
                    doubtBull, dBullOBo = True, lBearO

        entryFri = b.dow == 6
        if (p.tierB and validCISD and (sweptH or sweptL)
                and not (p.noBFri and entryFri) and not (p.noB21 and b.hour == 21)):
            wOKb = (not p.bWick) or dnWick < body
            wOKl = (not p.bWick) or upWick < body
            rOKb = (not p.bRango) or (sessLo is not None and b.c < sessLo)
            rOKl = (not p.bRango) or (sessHi is not None and b.c > sessHi)
            pOKb = (not p.bPrevDay) or prevNet is None or prevNet < p.bPrevPips * PIP
            pOKl = (not p.bPrevDay) or prevNet is None or prevNet > -p.bPrevPips * PIP
            if (not fABear and not fBBear and not fABearBar and aBullO is not None
                    and isBear and b.c < aBullO and wOKb and rOKb and pOKb):
                bearSigB = True; fBBear = True
            if (not fABull and not fBBull and not fABullBar and aBearO is not None
                    and isBull and b.c > aBearO and wOKl and rOKl and pOKl):
                bullSigB = True; fBBull = True

        if refH is not None and body >= p.bMinBody * PIP:
            if isBull:
                aBullO = b.o
            if isBear:
                aBearO = b.o
        if is17:
            sessHi, sessLo = b.h, b.l
        elif sessHi is not None:
            sessHi, sessLo = max(sessHi, b.h), min(sessLo, b.l)

        if validCISD and b.t.year in years:
            conf = {"short": bearSig or bearSigB, "long": bullSig or bullSigB}
            eventos.append(dict(t=b.t, confirmada=conf, anticipada=antic))

    return eventos


def _provisional(b, velas15, e, p, refH, refL, sessHi, sessLo, prevNet, setups, exigir_unicorn,
                 desde_min=0, calidad=False):
    """Evalúa la señal como si la vela H4 cerrase en cada M15. Devuelve la primera."""
    out = {}
    if not velas15:
        return out
    hi = lo = None
    sweptH, sweptL = e["sweptH"], e["sweptL"]
    for v in velas15[:-1]:            # la última M15 es el cierre real: no es anticipación
        hi = v.h if hi is None else max(hi, v.h)
        lo = v.l if lo is None else min(lo, v.l)
        c = v.c
        if hi > refH:
            sweptH = True
            if lo < refL:
                sweptL = True
        elif lo < refL:
            sweptL = True
        if (v.t - b.t).total_seconds() / 60 < desde_min:
            continue
        body = abs(c - b.o)
        rng = max(hi - lo, 1e-5)
        bodyR = body / rng
        if calidad and (body / PIP < 20 or bodyR < 0.50):
            continue
        isBull, isBear = c > b.o, c < b.o
        upW = (hi - c) if isBull else (hi - b.o)
        dnW = (b.o - lo) if isBull else (c - lo)

        doneA = (e["fABear"] and e["fABull"]) if p.perDir else (e["fABear"] or e["fABull"])
        for direc in ("short", "long"):
            if direc in out:
                continue
            bull = direc == "long"
            if not doneA:
                # tier A
                ob = e["lBearO"] if bull else e["lBullO"]
                obx = e["lBearH"] if bull else e["lBullL"]
                swept = sweptL if bull else sweptH
                yaf = e["fABull"] if bull else e["fABear"]
                if swept and ob is not None and not yaf and ((isBull and c > ob) if bull else (isBear and c < ob)):
                    r = body / max(body + (upW if bull else dnW), 1e-5)
                    limpio = (r >= p.cisdMinBody and (upW if bull else dnW) < body
                              and ((c > obx) if bull else (c < obx)))
                    if limpio:
                        out[direc] = dict(t=v.t, tier="A", precio=c)
                        continue
            # tier B
            if p.tierB and (sweptH or sweptL) and not (p.noBFri and b.dow == 6) and not (p.noB21 and b.hour == 21):
                obb = e["aBearO"] if bull else e["aBullO"]
                yaf = e["fBBull"] or e["fABull"] if bull else e["fBBear"] or e["fABear"]
                wick_ok = (not p.bWick) or ((upW if bull else dnW) < body)
                if obb is not None and not yaf and wick_ok and ((isBull and c > obb) if bull else (isBear and c < obb)):
                    out[direc] = dict(t=v.t, tier="B", precio=c)
    if exigir_unicorn and out:
        for direc in list(out):
            lst = setups.get(direc, [])
            ok = any(b.t <= s.activation_t <= out[direc]["t"] + timedelta(minutes=15) for s in lst)
            if not ok:
                del out[direc]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2025")
    ap.add_argument("--unicorn", action="store_true",
                    help="exigir además un setup Unicorn M15 en la misma dirección")
    ap.add_argument("--desde-minuto", type=int, default=0,
                    help="ignorar los disparos anteriores a este minuto de la vela H4")
    ap.add_argument("--calidad", action="store_true",
                    help="exigir que la vela provisional ya cumpla el filtro de calidad")
    ap.add_argument("--matriz", action="store_true", help="tabla de compromiso cobertura/ruido")
    a = ap.parse_args()
    years = bt.parse_years(a.years)
    if a.matriz:
        print(f"Compromiso cobertura / ruido — {a.years}\n")
        print(f"{'variante':46} {'buenas':>7} {'cobertura':>10} {'ruido':>7} {'fiabilidad':>11} {'adelanto':>9}")
        for uni in (False, True):
            for dm in (0, 120, 180):
                for cal in (False, True):
                    ev2 = analizar(years, bt.Params(), uni, False, dm, cal)
                    ok = ru = 0
                    ade = []
                    conf = 0
                    for x in ev2:
                        for d in ("long", "short"):
                            if x["confirmada"][d]:
                                conf += 1
                            if d in x["anticipada"]:
                                if x["confirmada"][d]:
                                    ok += 1
                                    ade.append((x["t"] + timedelta(hours=4) - x["anticipada"][d]["t"]
                                                - timedelta(minutes=15)).total_seconds() / 60)
                                else:
                                    ru += 1
                    if ok + ru == 0:
                        continue
                    import statistics as _st
                    nom = ("Unicorn" if uni else "solo CISD provisional")
                    nom += f" · desde min {dm}" if dm else ""
                    nom += " · calidad" if cal else ""
                    print(f"{nom:46} {ok:7} {ok / max(conf,1) * 100:9.0f}% {ru:7} "
                          f"{ok / (ok + ru) * 100:10.1f}% {(_st.median(ade) if ade else 0):8.0f}m")
        return
    ev = analizar(years, bt.Params(), a.unicorn, True, a.desde_minuto, a.calidad)

    tot_conf = sum(1 for x in ev for d in ("long", "short") if x["confirmada"][d])
    tot_ant = sum(1 for x in ev for d in ("long", "short") if d in x["anticipada"])
    aciertos = ruido = perdidas = 0
    adelanto = []
    for x in ev:
        for d in ("long", "short"):
            ant = d in x["anticipada"]
            con = x["confirmada"][d]
            if ant and con:
                aciertos += 1
                adelanto.append((x["t"] + timedelta(hours=4) - x["anticipada"][d]["t"] - timedelta(minutes=15)).total_seconds() / 60)
            elif ant and not con:
                ruido += 1
            elif con and not ant:
                perdidas += 1

    print(f"═══ Anticipación del CISD dentro de la vela — {a.years}"
          f"{' (exigiendo setup Unicorn M15)' if a.unicorn else ''} ═══\n")
    print(f"  velas H4 de hora válida analizadas : {len(ev)}")
    print(f"  señales CISD reales (al cierre)    : {tot_conf}")
    print(f"  disparos anticipados               : {tot_ant}\n")
    print(f"  ✓ anticipadas y confirmadas        : {aciertos:4}  "
          f"({aciertos / max(tot_conf, 1) * 100:.0f} % de las señales reales)")
    print(f"  ✗ anticipadas y NO confirmadas     : {ruido:4}  ← ruido añadido")
    print(f"  · confirmadas sin anticipar        : {perdidas:4}")
    if tot_ant:
        print(f"\n  fiabilidad del disparo anticipado  : {aciertos / tot_ant * 100:.1f} %")
        print(f"  ruido por cada señal buena         : {ruido / max(aciertos, 1):.2f}")
    if adelanto:
        import statistics as st
        print(f"  adelanto mediano sobre el cierre   : {st.median(adelanto):.0f} min "
              f"(máx {max(adelanto):.0f})")


if __name__ == "__main__":
    main()
