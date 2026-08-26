# -*- coding: utf-8 -*-
"""
Replica 1:1 la logica del indicador JoshModels_H1.pine (un modelo por sesion,
Asia desde las 17:00, sin OSOK/ASIA2/NYC2) sobre 2025 y genera el Excel de
auditoria manual: el usuario rellena OK?/Explicacion por señal.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from josh_models import Bar, a_h1, carga_m1


def construye(fecha_ini: date, fecha_fin: date):
    m1 = carga_m1([2024, 2025])
    m1 = [b for b in m1 if b.t >= datetime(2024, 12, 20)]
    h1 = a_h1(m1)
    por_dia: dict[date, dict[int, Bar]] = {}
    for b in h1:
        por_dia.setdefault(b.t.date(), {})[b.t.hour] = b

    filas = []
    dia = fecha_ini
    while dia <= fecha_fin:
        if dia.weekday() < 5:
            filas.append(evalua(dia, por_dia))
        dia += timedelta(days=1)
    return filas


def _rango_dia_natural(h1d: dict[int, Bar]):
    if not h1d:
        return None, None
    return max(b.h for b in h1d.values()), min(b.l for b in h1d.values())


def evalua(fecha: date, por_dia) -> dict:
    h1d = por_dia.get(fecha, {})
    fila = {"fecha": fecha, "ldn": None, "ny": None, "nota": ""}

    nucleo = [h for h in range(1, 10) if h in h1d]
    prev = fecha - timedelta(days=1)
    asia = {h: b for h, b in por_dia.get(prev, {}).items() if h >= 17}
    if len(nucleo) < 8 or not asia:
        fila["nota"] = "sin sesion"
        return fila

    asiaH = max(b.h for b in asia.values())
    asiaL = min(b.l for b in asia.values())
    pdH = pdL = None
    for k in range(1, 5):
        d = fecha - timedelta(days=k)
        if d in por_dia:
            pdH, pdL = _rango_dia_natural(por_dia[d])
            break
    ldn_bars = [h1d[h] for h in range(2, 8) if h in h1d]
    ldnH = max(b.h for b in ldn_bars) if ldn_bars else None
    ldnL = min(b.l for b in ldn_bars) if ldn_bars else None

    ldn_modelo = ""   # para encadenar NYC1: solo LR21/LR1
    ldn_dir = 0

    def senal_ldn(cod, dire, ent, sl):
        fila["ldn"] = {"modelo": cod, "dir": dire, "entrada": ent, "sl": sl}

    def senal_ny(cod, dire, ent, sl):
        fila["ny"] = {"modelo": cod, "dir": dire, "entrada": ent, "sl": sl}

    # ── cierre de 02:00: LR21 > LR1(raid 2) > A1 ──
    b2 = h1d.get(2)
    b1 = h1d.get(1)
    if b2 is not None:
        # LR21
        if fila["ldn"] is None and b1 is not None:
            nivel_alto = asiaH if b1.h > asiaH else (pdH if (pdH is not None and b1.h > pdH) else None)
            nivel_bajo = asiaL if b1.l < asiaL else (pdL if (pdL is not None and b1.l < pdL) else None)
            if nivel_alto is not None and b2.bajista and b2.c < nivel_alto:
                senal_ldn("LR2.1", -1, "03:00", max(nivel_alto, b1.h))
                ldn_modelo, ldn_dir = "LR21", -1
            elif nivel_bajo is not None and b2.alcista and b2.c > nivel_bajo:
                senal_ldn("LR2.1", 1, "03:00", min(nivel_bajo, b1.l))
                ldn_modelo, ldn_dir = "LR21", 1
        # LR1 raid en la vela de 02:00 (proxy H1, como el indicador)
        if fila["ldn"] is None:
            if b2.h > asiaH and b2.bajista and b2.c < asiaH:
                senal_ldn("LR1", -1, "03:00", asiaH)
                ldn_modelo, ldn_dir = "LR1", -1
            elif b2.l < asiaL and b2.alcista and b2.c > asiaL:
                senal_ldn("LR1", 1, "03:00", asiaL)
                ldn_modelo, ldn_dir = "LR1", 1
        # A1
        if fila["ldn"] is None:
            barrio_alto = any(h1d[h].h > asiaH for h in (0, 1, 2) if h in h1d)
            barrio_bajo = any(h1d[h].l < asiaL for h in (0, 1, 2) if h in h1d)
            if barrio_alto and b2.bajista and b2.c < asiaH:
                senal_ldn("A1", -1, "03:00", b2.h)
            elif barrio_bajo and b2.alcista and b2.c > asiaL:
                senal_ldn("A1", 1, "03:00", b2.l)

    # ── cierre de 03:00: LR1 (confirmado o excepcion) ──
    b3 = h1d.get(3)
    if fila["ldn"] is None and b3 is not None:
        if b3.h > asiaH:
            conf = b3.bajista and b3.c < asiaH
            senal_ldn("LR1" if conf else "LR1*", -1, "04:00" if conf else "1er M15 04:00", asiaH)
            ldn_modelo, ldn_dir = "LR1", -1
        elif b3.l < asiaL:
            conf = b3.alcista and b3.c > asiaL
            senal_ldn("LR1" if conf else "LR1*", 1, "04:00" if conf else "1er M15 04:00", asiaL)
            ldn_modelo, ldn_dir = "LR1", 1

    # ── cierre de 04:00: LR2.2 (no encadena NYC1) ──
    b4 = h1d.get(4)
    if fila["ldn"] is None and b4 is not None:
        if b4.h > asiaH:
            senal_ldn("LR2.2", -1, "04:45", asiaH)
        elif b4.l < asiaL:
            senal_ldn("LR2.2", 1, "04:45", asiaL)

    # ── cierre de 07:00: NYR2 > NYC1 ──
    bars07 = [(h, h1d[h]) for h in range(0, 8) if h in h1d]
    if bars07:
        alto = max(b.h for _, b in bars07)
        bajo = min(b.l for _, b in bars07)
        hora_alto = max(h for h, b in bars07 if b.h >= alto)
        hora_bajo = max(h for h, b in bars07 if b.l <= bajo)
        horas = [h for h, _ in bars07]

        def nyr2(hora_ext, dire):
            if hora_ext < 5:
                return False
            for h in range(hora_ext, 8):
                if h not in h1d or (h - 1) not in h1d:
                    continue
                b, p = h1d[h], h1d[h - 1]
                cpo, rgo = b.cuerpo, b.rango
                if dire == -1 and b.bajista and cpo >= 0.5 * rgo and b.c < p.l:
                    if any(h1d[k].alcista for k in horas if k < h):
                        b7 = h1d.get(7)
                        if b7 is not None:
                            senal_ny("NYR2", -1, "08:00", b7.h)
                            return True
                if dire == 1 and b.alcista and cpo >= 0.5 * rgo and b.c > p.h:
                    if any(h1d[k].bajista for k in horas if k < h):
                        b7 = h1d.get(7)
                        if b7 is not None:
                            senal_ny("NYR2", 1, "08:00", b7.l)
                            return True
            return False

        if fila["ny"] is None:
            if not nyr2(hora_alto, -1):
                nyr2(hora_bajo, 1)

        # NYC1
        if fila["ny"] is None and ldn_modelo in ("LR21", "LR1") and ldnH is not None:
            horas27 = [(h, b) for h, b in bars07 if h >= 2]
            if horas27:
                if ldn_dir == -1:
                    ext = max(b.h for _, b in horas27)
                    hora_ext = max(h for h, b in horas27 if b.h >= ext)
                else:
                    ext = min(b.l for _, b in horas27)
                    hora_ext = max(h for h, b in horas27 if b.l <= ext)
                if hora_ext <= 4:
                    b57 = [(h, b) for h, b in bars07 if 5 <= h <= 7]
                    if b57:
                        if ldn_dir == -1:
                            lrlr = any(b.alcista for _, b in b57)
                            sl = ldnH
                        else:
                            lrlr = any(b.bajista for _, b in b57)
                            sl = ldnL
                        if lrlr:
                            senal_ny("NYC1", ldn_dir, "08:00", sl)

    # ── cierre de 08:00/09:00: NYR1 ──
    for h in (8, 9):
        if fila["ny"] is not None or ldnH is None:
            break
        b = h1d.get(h)
        if b is None:
            continue
        if b.h > ldnH and b.c < ldnH:
            senal_ny("NYR1", -1, "09:00" if h == 8 else "10:00", b.h)
        elif b.l < ldnL and b.c > ldnL:
            senal_ny("NYR1", 1, "09:00" if h == 8 else "10:00", b.l)

    return fila


if __name__ == "__main__":
    filas = construye(date(2025, 1, 1), date(2025, 12, 31))
    n_ldn = sum(1 for f in filas if f["ldn"])
    n_ny = sum(1 for f in filas if f["ny"])
    print(f"{len(filas)} dias, {n_ldn} señales Londres, {n_ny} señales NY,",
          f"{sum(1 for f in filas if f['nota'] == 'sin sesion')} sin sesion")
