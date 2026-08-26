# -*- coding: utf-8 -*-
"""
Calendario diario 2025 de los modelos de Josh (spec §5 y §7.1).

Uso:
    python3 josh_calendario.py                  # genera josh_daily_calendar_2025.csv
    python3 josh_calendario.py --dia 2025-03-05 # detalle H1 de un dia para auditar
    python3 josh_calendario.py --semana 2025-03-03  # semana completa para auditar
"""
from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timedelta

from josh_models import (
    Bar, Deteccion, Niveles, a_d1, a_h1, a_m15, carga_m1, construye_indices,
    detecta_asia1, detecta_asia2, detecta_lr1, detecta_lr21, detecta_lr22,
    detecta_nyc1, detecta_nyc2, detecta_nyr1, detecta_nyr2,
    niveles_del_dia, osok_del_dia, tgif_del_dia, PIP,
)

SALIDA = "josh_daily_calendar_2025.csv"


def bucket_h4(t: datetime) -> datetime:
    """Buckets H4 de FX: 17,21,1,5,9,13 NY (misma logica que el motor CISD)."""
    h = t.hour
    if h >= 17:
        base = 17
        d = t.date()
    elif h >= 13:
        base = 13
        d = t.date()
    elif h >= 9:
        base = 9
        d = t.date()
    elif h >= 5:
        base = 5
        d = t.date()
    elif h >= 1:
        base = 1
        d = t.date()
    else:
        base = 21
        d = t.date() - timedelta(days=1)
    return datetime(d.year, d.month, d.day, base)


def a_h4(m1: list[Bar]) -> list[Bar]:
    from josh_models import _agrega
    return _agrega(m1, bucket_h4)


def h4_previas(h4: list[Bar], fecha: date, hora_raid: int) -> list[Bar]:
    """Las dos H4 cerradas antes de la vela H4 que contiene la hora del raid."""
    corte = datetime(fecha.year, fecha.month, fecha.day, hora_raid)
    b_corte = bucket_h4(corte)
    previas = [b for b in h4 if b.t < b_corte]
    return previas[-2:]


PRIORIDAD = ["LR21", "LR1", "ASIA1", "ASIA2", "LR22", "NYR2", "NYC1", "NYR1", "NYC2"]


def evalua_dia(fecha: date, h1_por_dia, d1_por_dia, h4: list[Bar],
               m15_por_dia_hora=None):
    """Devuelve el dict de fila del calendario para un dia."""
    h1d = h1_por_dia.get(fecha, {})
    fila = {
        "date": fecha.isoformat(),
        "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][fecha.weekday()],
        "osok_dir": "", "tgif": False,
        "news_0830": False, "news_1000": False,
        "asia_model": "none", "london_model": "none", "ny_model": "none",
        "sequence": "", "primary_model": "", "secondary_model": "",
        "status": "no_model", "notes": "",
    }
    notas = ["news_unavailable"]

    # sesion suficiente: necesita al menos las horas 01-09 y rango de Asia
    n = niveles_del_dia(fecha, h1_por_dia, d1_por_dia)
    horas_nucleo = [h for h in range(1, 10) if h in h1d]
    if len(horas_nucleo) < 8 or n.asia_h is None:
        fila["status"] = "no_session"
        fila["notes"] = ";".join(notas + ["faltan horas nucleo o rango de Asia"])
        return fila, None

    osok = osok_del_dia(fecha, d1_por_dia, n.apertura_semanal)
    tgif, tgif_dir = tgif_del_dia(fecha, d1_por_dia, n)
    fila["osok_dir"] = {1: "long", -1: "short", None: ""}[osok]
    fila["tgif"] = tgif

    hay_noticia = False  # sin calendario economico (documentado)

    # ── detecciones en orden temporal/prioridad ──
    det: dict[str, Deteccion] = {}
    d = detecta_lr21(h1d, n)
    if d: det["LR21"] = d
    hp = h4_previas(h4, fecha, 2)
    m15dh = (m15_por_dia_hora or {}).get(fecha, {})
    d = detecta_lr1(h1d, n, hp, m15dh)
    if d: det["LR1"] = d
    d = detecta_asia1(h1d, n)
    if d: det["ASIA1"] = d
    # ASIA2 solo si OSOK y las 02:00 NO confirmaron nada (ni ASIA1 ni un LR con
    # confirmacion en 02:00)
    confirmo_0200 = "ASIA1" in det or "LR21" in det or (
        "LR1" in det and "02:00" in det["LR1"].notas)
    if osok is not None and not confirmo_0200:
        d = detecta_asia2(h1d, n, osok)
        if d: det["ASIA2"] = d
    d = detecta_lr22(h1d, n)
    if d: det["LR22"] = d
    d = detecta_nyr2(h1d, n)
    if d: det["NYR2"] = d

    # Londres elegido (para follow-ons): primero por prioridad entre LR21/LR1
    ldn = det.get("LR21") or det.get("LR1")
    # LR22 bloquea continuaciones NY ese dia
    lr22_hoy = "LR22" in det and ldn is None
    if ldn is not None and not lr22_hoy:
        d = detecta_nyc1(h1d, n, ldn)
        if d: det["NYC1"] = d
    d = detecta_nyr1(h1d, n)
    if d: det["NYR1"] = d
    if "NYC1" in det:
        d = detecta_nyc2(det.get("LR1"), det.get("NYC1"), hay_noticia)
        if d: det["NYC2"] = d

    if not det:
        fila["notes"] = ";".join(notas)
        return fila, None

    # ── slots ──
    for m in ("ASIA1", "ASIA2"):
        if m in det:
            fila["asia_model"] = "1" if m == "ASIA1" else "2"
            break
    for m in ("LR21", "LR1", "LR22"):
        if m in det:
            fila["london_model"] = {"LR21": "LR21", "LR1": "LR1", "LR22": "LR22"}[m]
            break
    for m in ("NYR2", "NYC1", "NYR1", "NYC2"):
        if m in det:
            fila["ny_model"] = {"NYR2": "NYR2", "NYC1": "NYC1", "NYR1": "NYR1", "NYC2": "NYC2"}[m]
            break

    # ── primario / secundario por prioridad ──
    orden = [m for m in PRIORIDAD if m in det]
    fila["primary_model"] = orden[0]
    if len(orden) > 1:
        fila["secondary_model"] = orden[1]
    fila["sequence"] = ">".join(orden)
    fila["status"] = "detected"

    # ── conflictos ──
    conflicto = False
    if "NYC1" in det and "NYR1" in det and det["NYC1"].direccion != det["NYR1"].direccion:
        conflicto = True
        notas.append("conflicto NYC1/NYR1 en direcciones opuestas")
    primarios_ldn = [m for m in ("LR21", "LR1", "ASIA1") if m in det]
    if len(primarios_ldn) > 1:
        notas.append("compiten " + "+".join(primarios_ldn))
    if conflicto:
        fila["status"] = "conflict"

    if tgif and "NYR1" in det and det["NYR1"].direccion == tgif_dir:
        notas.append("tgif confluencia NYR1")
    if osok is not None:
        p = det[orden[0]]
        notas.append("with_osok" if p.direccion == osok else "against_osok")

    dirs = {m: ("L" if det[m].direccion == 1 else "S") for m in orden}
    notas.append("dirs " + ",".join(f"{m}:{dirs[m]}" for m in orden))
    fila["notes"] = ";".join(notas)
    return fila, det


def carga_todo():
    m1 = carga_m1([2024, 2025])
    m1 = [b for b in m1 if b.t >= datetime(2024, 11, 1)]
    h1 = a_h1(m1)
    d1 = a_d1(m1)
    h4 = a_h4(m1)
    m15 = a_m15(m1)
    h1_por_dia, d1_por_dia = construye_indices(h1, d1)
    m15_por_dia_hora: dict = {}
    for b in m15:
        m15_por_dia_hora.setdefault(b.t.date(), {}).setdefault(b.t.hour, []).append(b)
    return m1, h1, d1, h4, h1_por_dia, d1_por_dia, m15_por_dia_hora


def genera_calendario():
    _, h1, d1, h4, h1_por_dia, d1_por_dia, m15dh = carga_todo()
    filas = []
    dia = date(2025, 1, 1)
    while dia <= date(2025, 12, 31):
        if dia.weekday() < 5:  # solo laborables
            fila, _ = evalua_dia(dia, h1_por_dia, d1_por_dia, h4, m15dh)
            filas.append(fila)
        dia += timedelta(days=1)
    campos = ["date", "weekday", "osok_dir", "tgif", "news_0830", "news_1000",
              "asia_model", "london_model", "ny_model", "sequence",
              "primary_model", "secondary_model", "status", "notes"]
    with open(SALIDA, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)
    # resumen
    from collections import Counter
    print(f"{len(filas)} dias -> {SALIDA}")
    print("status:", dict(Counter(f["status"] for f in filas)))
    print("primario:", dict(Counter(f["primary_model"] for f in filas if f["primary_model"])))
    print("londres:", dict(Counter(f["london_model"] for f in filas)))
    print("ny:", dict(Counter(f["ny_model"] for f in filas)))
    return filas


def imprime_dia(fecha: date):
    _, h1, d1, h4, h1_por_dia, d1_por_dia, m15dh = carga_todo()
    n = niveles_del_dia(fecha, h1_por_dia, d1_por_dia)
    h1d = h1_por_dia.get(fecha, {})
    print(f"── {fecha} ({['lun','mar','mie','jue','vie','sab','dom'][fecha.weekday()]}) ──")
    def fmt(x): return f"{x:.5f}" if x is not None else "  n/a  "
    print(f"AH {fmt(n.asia_h)}  AL {fmt(n.asia_l)}  PDH {fmt(n.pdh)}  PDL {fmt(n.pdl)}")
    print(f"LDNH {fmt(n.ldn_h)}  LDNL {fmt(n.ldn_l)}  W-open {fmt(n.apertura_semanal)}")
    for h in range(0, 17):
        b = h1d.get(h)
        if b is None:
            continue
        marcas = []
        if n.asia_h and b.h > n.asia_h: marcas.append(">AH")
        if n.asia_l and b.l < n.asia_l: marcas.append("<AL")
        if n.pdh and b.h > n.pdh: marcas.append(">PDH")
        if n.pdl and b.l < n.pdl: marcas.append("<PDL")
        if h >= 8:
            if n.ldn_h and b.h > n.ldn_h: marcas.append(">LDNH")
            if n.ldn_l and b.l < n.ldn_l: marcas.append("<LDNL")
        vela = "alcista" if b.c > b.o else ("bajista" if b.c < b.o else "doji")
        print(f"  {h:02d}:00  O {b.o:.5f}  H {b.h:.5f}  L {b.l:.5f}  C {b.c:.5f}"
              f"  {vela:7s} {' '.join(marcas)}")
    fila, det = evalua_dia(fecha, h1_por_dia, d1_por_dia, h4, m15dh)
    print(f"status={fila['status']}  sequence={fila['sequence'] or '-'}")
    if det:
        for m, dd in det.items():
            hora = "04:45" if m == "LR22" else f"{dd.hora_entrada:02d}:00"
            print(f"  {m:5s} {'LARGO' if dd.direccion==1 else 'CORTO'}  entrada {hora}"
                  f"  SL {dd.sl:.5f}  [{dd.notas}]")
    print(f"notes: {fila['notes']}")


def imprime_semana(lunes: date):
    d = lunes - timedelta(days=lunes.weekday())
    for k in range(5):
        imprime_dia(d + timedelta(days=k))
        print()


if __name__ == "__main__":
    if "--dia" in sys.argv:
        f = datetime.strptime(sys.argv[sys.argv.index("--dia") + 1], "%Y-%m-%d").date()
        imprime_dia(f)
    elif "--semana" in sys.argv:
        f = datetime.strptime(sys.argv[sys.argv.index("--semana") + 1], "%Y-%m-%d").date()
        imprime_semana(f)
    else:
        genera_calendario()
