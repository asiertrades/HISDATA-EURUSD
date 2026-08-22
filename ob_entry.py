#!/usr/bin/env python3
"""
Detector de order blocks en LTF, al estilo del propio CISD.

En vez del breaker por pivote del Unicorn, la zona de entrada es el **order
block**: la última vela contraria cuyo open atraviesa el precio con una vela de
desplazamiento. Es la misma definición que usa el motor CISD en H4
(`_lBullO` / `_aBullO`), llevada a M15 o M5.

    long : última vela BAJISTA cuyo open cierra por encima una vela alcista
    short: última vela ALCISTA cuyo open cierra por debajo una vela bajista

    entrada      → retesteo del open del OB (o de su 50 %)
    invalidación → extremo del OB (mínimo para largos, máximo para cortos)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PIP = 0.0001


@dataclass
class OBSetup:
    is_bull: bool
    ob_open: float
    ob_high: float
    ob_low: float
    ob_t: datetime
    activation_t: datetime
    activation_close: float
    desplazamiento_p: float          # cuerpo de la vela que rompe, en pips

    def entrada(self, modo: str) -> float:
        if modo == "mitad":
            return (self.ob_open + (self.ob_low if self.is_bull else self.ob_high)) / 2
        if modo == "extremo":
            return self.ob_low if self.is_bull else self.ob_high
        return self.ob_open           # "open": el retesteo clásico

    def stop(self, buffer_p: float = 1.0) -> float:
        return (self.ob_low - buffer_p * PIP) if self.is_bull else (self.ob_high + buffer_p * PIP)


def find_obs(bars, min_body_p: float = 1.0, min_body_ratio: float = 0.0,
             min_desplazamiento_p: float = 0.0):
    """Recorre las velas LTF y devuelve los setups de order block activados."""
    setups: list[OBSetup] = []
    last_bear = None          # (open, high, low, t) — candidata para largos
    last_bull = None          # candidata para cortos

    for b in bars:
        cuerpo = abs(b.c - b.o)
        rango = max(b.h - b.l, 1e-9)
        alcista, bajista = b.c > b.o, b.c < b.o

        # activación: la vela actual cierra a través del open del OB contrario
        if alcista and last_bear is not None and b.c > last_bear[0]:
            if cuerpo / PIP >= min_desplazamiento_p:
                setups.append(OBSetup(True, last_bear[0], last_bear[1], last_bear[2],
                                      last_bear[3], b.t, b.c, cuerpo / PIP))
            last_bear = None
        if bajista and last_bull is not None and b.c < last_bull[0]:
            if cuerpo / PIP >= min_desplazamiento_p:
                setups.append(OBSetup(False, last_bull[0], last_bull[1], last_bull[2],
                                      last_bull[3], b.t, b.c, cuerpo / PIP))
            last_bull = None

        # actualización del OB candidato (al final, como en el motor CISD)
        if cuerpo / PIP >= min_body_p and cuerpo / rango >= min_body_ratio:
            if alcista:
                last_bull = (b.o, b.h, b.l, b.t)
            elif bajista:
                last_bear = (b.o, b.h, b.l, b.t)

    return setups
