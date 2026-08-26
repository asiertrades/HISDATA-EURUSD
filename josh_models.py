# -*- coding: utf-8 -*-
"""
Modelos de Josh sobre EURUSD — deteccion diaria (spec JOSH_EURUSD_2025_BACKTEST_SPEC.md v1.0).

Solo detectores + calendario diario. La simulacion de entradas se hace en un
paso posterior, cuando el calendario este auditado.

Datos: DAT_ASCII_EURUSD_M1_YYYY.csv (timestamps en hora de Nueva York, DST
incluido — validado previamente en este repo contra las sesiones de TradingView).

Convenciones fijadas aqui (ver josh_assumptions.md para la lista completa):
- Vela H1 de la hora X = barras M1 con timestamp en [X:00, X:59].
- Asia = 20:00-23:59 NY de la tarde anterior (4 velas H1).
- LDNH/LDNL = extremos de 02:00-07:59 NY (ventana por defecto del spec).
- PDH/PDL = dia natural NY anterior con datos (00:00-23:59).
- D1 para OSOK/TGIF = dia natural NY (00:00-23:59).
- Apertura semanal = primer tick del domingo 17:00 NY.
- "Toma" un nivel = extremo estrictamente mas alla (high > nivel / low < nivel).
- "Confirma" un raid de un alto = cierre bajista y cierre de vuelta por debajo
  del nivel raideado (espejo para bajos).
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

PIP = 0.0001
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


# ──────────────────────────────────────────────────────────────────
# DATOS
# ──────────────────────────────────────────────────────────────────
@dataclass
class Bar:
    t: datetime      # apertura
    o: float
    h: float
    l: float
    c: float

    @property
    def alcista(self) -> bool:
        return self.c > self.o

    @property
    def bajista(self) -> bool:
        return self.c < self.o

    @property
    def cuerpo(self) -> float:
        return abs(self.c - self.o)

    @property
    def rango(self) -> float:
        return max(self.h - self.l, 1e-9)


def carga_m1(anos: list[int]) -> list[Bar]:
    bars: list[Bar] = []
    for ano in anos:
        ruta = os.path.join(DATA_DIR, f"DAT_ASCII_EURUSD_M1_{ano}.csv")
        with open(ruta) as f:
            for linea in f:
                partes = linea.rstrip("\n").split(";")
                ts = datetime.strptime(partes[0], "%Y%m%d %H%M%S")
                bars.append(Bar(ts, float(partes[1]), float(partes[2]),
                                float(partes[3]), float(partes[4])))
    bars.sort(key=lambda b: b.t)
    return bars


def _agrega(bars: list[Bar], clave) -> list[Bar]:
    out: list[Bar] = []
    actual: Optional[Bar] = None
    k_actual = None
    for b in bars:
        k = clave(b.t)
        if k != k_actual:
            if actual is not None:
                out.append(actual)
            actual = Bar(k, b.o, b.h, b.l, b.c)
            k_actual = k
        else:
            actual.h = max(actual.h, b.h)
            actual.l = min(actual.l, b.l)
            actual.c = b.c
    if actual is not None:
        out.append(actual)
    return out


def a_h1(m1: list[Bar]) -> list[Bar]:
    return _agrega(m1, lambda t: t.replace(minute=0, second=0))


def a_m15(m1: list[Bar]) -> list[Bar]:
    return _agrega(m1, lambda t: t.replace(minute=(t.minute // 15) * 15, second=0))


def a_d1(m1: list[Bar]) -> list[Bar]:
    # dia natural NY 00:00-23:59 (asuncion documentada)
    return _agrega(m1, lambda t: t.replace(hour=0, minute=0, second=0))


# ──────────────────────────────────────────────────────────────────
# NIVELES DE SESION POR DIA
# ──────────────────────────────────────────────────────────────────
@dataclass
class Niveles:
    fecha: date
    asia_h: Optional[float] = None
    asia_l: Optional[float] = None
    pdh: Optional[float] = None
    pdl: Optional[float] = None
    apertura_semanal: Optional[float] = None
    # se rellenan segun avanza el dia
    ldn_h: Optional[float] = None
    ldn_l: Optional[float] = None


def construye_indices(h1: list[Bar], d1: list[Bar]):
    """Indices por fecha para acceso rapido."""
    h1_por_dia: dict[date, dict[int, Bar]] = {}
    for b in h1:
        h1_por_dia.setdefault(b.t.date(), {})[b.t.hour] = b
    d1_por_dia: dict[date, Bar] = {b.t.date(): b for b in d1}
    return h1_por_dia, d1_por_dia


def niveles_del_dia(fecha: date, h1_por_dia, d1_por_dia) -> Niveles:
    n = Niveles(fecha)
    # Asia: 20:00-23:00 del dia anterior (natural)
    prev = fecha - timedelta(days=1)
    asia = [h1_por_dia.get(prev, {}).get(h) for h in (20, 21, 22, 23)]
    asia = [b for b in asia if b is not None]
    if asia:
        n.asia_h = max(b.h for b in asia)
        n.asia_l = min(b.l for b in asia)
    # PDH/PDL: dia natural anterior con datos (retrocede hasta 4 dias por festivos)
    for k in range(1, 5):
        d = fecha - timedelta(days=k)
        if d in d1_por_dia:
            n.pdh = d1_por_dia[d].h
            n.pdl = d1_por_dia[d].l
            break
    # apertura semanal: primer dato del domingo (17:00) de esta semana;
    # si el propio dia es domingo, su apertura
    dow = fecha.weekday()  # lunes=0 ... domingo=6
    domingo = fecha if dow == 6 else fecha - timedelta(days=dow + 1)
    if domingo in d1_por_dia:
        n.apertura_semanal = d1_por_dia[domingo].o
    # LDNH/LDNL 02:00-07:59 del propio dia
    ldn = [h1_por_dia.get(fecha, {}).get(h) for h in range(2, 8)]
    ldn = [b for b in ldn if b is not None]
    if ldn:
        n.ldn_h = max(b.h for b in ldn)
        n.ldn_l = min(b.l for b in ldn)
    return n


# ──────────────────────────────────────────────────────────────────
# FILTROS NARRATIVOS: OSOK Y TGIF
# ──────────────────────────────────────────────────────────────────
def osok_del_dia(fecha: date, d1_por_dia, apertura_semanal) -> Optional[int]:
    """Causal: para mie-vie, signo(cierre D1 del dia anterior - apertura semanal).

    Lun-mar -> None (osok=session_only). Devuelve +1 / -1 / None.
    """
    if fecha.weekday() < 2 or apertura_semanal is None:
        return None
    for k in range(1, 4):
        d = fecha - timedelta(days=k)
        if d in d1_por_dia and d.weekday() < 5:
            dif = d1_por_dia[d].c - apertura_semanal
            if abs(dif) < 1e-9:
                return None
            return 1 if dif > 0 else -1
    return None


def tgif_del_dia(fecha: date, d1_por_dia, niveles: Niveles) -> tuple[bool, Optional[int]]:
    """Solo viernes. Lun-jue mayoria (>=3) en una direccion y el jueves
    interactua con un PD array (PDH/PDL del miercoles o apertura semanal).
    Devuelve (tgif, direccion_buscada) con +1=largos, -1=cortos.
    """
    if fecha.weekday() != 4:
        return False, None
    dias = [fecha - timedelta(days=k) for k in (4, 3, 2, 1)]  # lun..jue
    velas = [d1_por_dia.get(d) for d in dias]
    if any(v is None for v in velas):
        return False, None
    bajistas = sum(1 for v in velas if v.bajista)
    alcistas = sum(1 for v in velas if v.alcista)
    jue = velas[3]
    mie = velas[2]
    toca_pd = False
    for nivel in (mie.h, mie.l, niveles.apertura_semanal):
        if nivel is not None and jue.l <= nivel <= jue.h:
            toca_pd = True
    if bajistas >= 3 and toca_pd:
        return True, 1   # viernes buscamos largos
    if alcistas >= 3 and toca_pd:
        return True, -1  # viernes buscamos cortos
    return False, None


# ──────────────────────────────────────────────────────────────────
# DETECTORES
# ──────────────────────────────────────────────────────────────────
@dataclass
class Deteccion:
    modelo: str            # LR21 | LR1 | ASIA1 | ASIA2 | LR22 | NYR2 | NYC1 | NYR1 | NYC2
    direccion: int         # 1 largo, -1 corto
    hora_entrada: int      # hora NY de la apertura H1 de entrada (LR22: 4 -> 04:45)
    sl: float
    nivel_raid: Optional[float] = None
    notas: str = ""


def _toma_alto(b: Bar, nivel: Optional[float]) -> bool:
    return nivel is not None and b.h > nivel


def _toma_bajo(b: Bar, nivel: Optional[float]) -> bool:
    return nivel is not None and b.l < nivel


def _confirma_corto(b: Bar, nivel: float) -> bool:
    # cierre bajista y de vuelta por debajo del nivel raideado
    return b.bajista and b.c < nivel


def _confirma_largo(b: Bar, nivel: float) -> bool:
    return b.alcista and b.c > nivel


def detecta_lr21(h1d: dict[int, Bar], n: Niveles) -> Optional[Deteccion]:
    """London Reversal 2.1: 01:00 toma AH/AL (o PDH/PDL); 02:00 DEBE confirmar."""
    b1, b2 = h1d.get(1), h1d.get(2)
    if b1 is None or b2 is None:
        return None
    # lado alto
    for nivel, etiqueta in ((n.asia_h, "AH"), (n.pdh, "PDH")):
        if _toma_alto(b1, nivel) and _confirma_corto(b2, nivel):
            sl = max(nivel, b1.h)
            return Deteccion("LR21", -1, 3, sl, nivel, f"raid {etiqueta} 01:00, confirma 02:00")
    for nivel, etiqueta in ((n.asia_l, "AL"), (n.pdl, "PDL")):
        if _toma_bajo(b1, nivel) and _confirma_largo(b2, nivel):
            sl = min(nivel, b1.l)
            return Deteccion("LR21", 1, 3, sl, nivel, f"raid {etiqueta} 01:00, confirma 02:00")
    return None


def _confirma_ob_desplaz(m15h: list[Bar], nivel: float, direccion: int) -> bool:
    """Confirmacion del spec para LR1: OB + desplazamiento tras el raid, en los
    M15 de la hora del raid. Para un corto: tras el M15 que toma el nivel, un
    M15 bajista cierra por debajo del low del M15 del raid (desplazamiento) y
    existe un M15 alcista previo al desplazamiento (el OB)."""
    idx_raid = None
    for i, b in enumerate(m15h):
        if (direccion == -1 and b.h > nivel) or (direccion == 1 and b.l < nivel):
            idx_raid = i
            break
    if idx_raid is None:
        return False
    for j in range(idx_raid + 1, len(m15h)):
        b = m15h[j]
        if direccion == -1 and b.bajista and b.c < m15h[idx_raid].l:
            if any(m15h[k].alcista for k in range(0, j)):
                return True
        if direccion == 1 and b.alcista and b.c > m15h[idx_raid].h:
            if any(m15h[k].bajista for k in range(0, j)):
                return True
    return False


def detecta_lr1(h1d: dict[int, Bar], n: Niveles, h4_prev: list[Bar],
                m15_por_hora: Optional[dict[int, list[Bar]]] = None) -> Optional[Deteccion]:
    """London Reversal.1: 02:00 o 03:00 toma AH/AL; confirmacion = OB +
    desplazamiento tras el raid (M15 de la hora del raid, spec §3.2). Si no hay
    M15 disponible, cae al proxy H1: la vela del raid cierra de vuelta dentro.
    Excepcion: raid a las 03:00 sin confirmacion -> variante 04:00 primer M15."""
    for hora in (2, 3):
        b = h1d.get(hora)
        if b is None:
            continue
        entrada = hora + 1
        m15h = (m15_por_hora or {}).get(hora)
        if _toma_alto(b, n.asia_h):
            if m15h:
                conf = _confirma_ob_desplaz(m15h, n.asia_h, -1)
            else:
                conf = _confirma_corto(b, n.asia_h)
            h4c = _h4_contra(h4_prev, -1)
            if conf:
                return Deteccion("LR1", -1, entrada, n.asia_h, n.asia_h,
                                 f"raid AH {hora:02d}:00" + ("" if h4c else ", sin filtro H4"))
            if hora == 3:
                return Deteccion("LR1", -1, 4, n.asia_h, n.asia_h,
                                 "excepcion: raid AH 03:00 sin confirmar, entrada 1er M15 de 04:00")
        if _toma_bajo(b, n.asia_l):
            if m15h:
                conf = _confirma_ob_desplaz(m15h, n.asia_l, 1)
            else:
                conf = _confirma_largo(b, n.asia_l)
            h4c = _h4_contra(h4_prev, 1)
            if conf:
                return Deteccion("LR1", 1, entrada, n.asia_l, n.asia_l,
                                 f"raid AL {hora:02d}:00" + ("" if h4c else ", sin filtro H4"))
            if hora == 3:
                return Deteccion("LR1", 1, 4, n.asia_l, n.asia_l,
                                 "excepcion: raid AL 03:00 sin confirmar, entrada 1er M15 de 04:00")
    return None


def _h4_contra(h4_prev: list[Bar], direccion: int) -> bool:
    """Filtro suave: las dos H4 previas preferiblemente CONTRA el giro."""
    if len(h4_prev) < 2:
        return False
    a, b = h4_prev[-2], h4_prev[-1]
    if direccion == -1:
        return a.alcista and b.alcista
    return a.bajista and b.bajista


def detecta_asia1(h1d: dict[int, Bar], n: Niveles) -> Optional[Deteccion]:
    """Asia Model.1: un extremo de Asia barrido en 00:00-02:00 y la vela de
    02:00 confirma la manipulacion. Entrada 03:00, SL en el extremo de 02:00."""
    b2 = h1d.get(2)
    if b2 is None or n.asia_h is None:
        return None
    barrio_alto = any(_toma_alto(h1d[h], n.asia_h) for h in (0, 1, 2) if h in h1d)
    barrio_bajo = any(_toma_bajo(h1d[h], n.asia_l) for h in (0, 1, 2) if h in h1d)
    if barrio_alto and _confirma_corto(b2, n.asia_h):
        return Deteccion("ASIA1", -1, 3, b2.h, n.asia_h, "AH barrido, 02:00 confirma")
    if barrio_bajo and _confirma_largo(b2, n.asia_l):
        return Deteccion("ASIA1", 1, 3, b2.l, n.asia_l, "AL barrido, 02:00 confirma")
    return None


def detecta_asia2(h1d: dict[int, Bar], n: Niveles, osok: Optional[int]) -> Optional[Deteccion]:
    """Asia Model.2: requiere OSOK; 02:00 no confirma (permitido).
    Entrada 03:00 en direccion OSOK, SL en el extremo de Asia."""
    if osok is None or n.asia_h is None:
        return None
    sl = n.asia_h if osok == -1 else n.asia_l
    return Deteccion("ASIA2", osok, 3, sl, None, "direccion OSOK, SL en extremo de Asia")


def detecta_lr22(h1d: dict[int, Bar], n: Niveles) -> Optional[Deteccion]:
    """London Reversal 2.2: 04:00 toma AH/AL. Entrada 04:45-04:55 (M15)."""
    b4 = h1d.get(4)
    if b4 is None:
        return None
    if _toma_alto(b4, n.asia_h):
        return Deteccion("LR22", -1, 4, n.asia_h, n.asia_h, "raid AH 04:00, entrada 04:45 M15")
    if _toma_bajo(b4, n.asia_l):
        return Deteccion("LR22", 1, 4, n.asia_l, n.asia_l, "raid AL 04:00, entrada 04:45 M15")
    return None


def detecta_nyr2(h1d: dict[int, Bar], n: Niveles) -> Optional[Deteccion]:
    """NY Reversal.2: el extremo del dia (00:00-07:59) se forma a las 05/06/07,
    hay OB H1 antes de las 08:00 y luego desplazamiento."""
    horas = [h for h in range(0, 8) if h in h1d]
    if not horas:
        return None
    alto_dia = max(h1d[h].h for h in horas)
    bajo_dia = min(h1d[h].l for h in horas)
    hora_alto = max((h for h in horas if h1d[h].h == alto_dia), default=None)
    hora_bajo = max((h for h in horas if h1d[h].l == bajo_dia), default=None)

    def busca(hora_ext: int, direccion: int) -> Optional[Deteccion]:
        if hora_ext not in (5, 6, 7):
            return None
        # desplazamiento tras el extremo: alguna H1 posterior (<=07:00) cierra en
        # la direccion del giro con cuerpo >= 50% del rango y cierra mas alla del
        # extremo de la vela previa
        for h in range(hora_ext, 8):
            b = h1d.get(h)
            prev = h1d.get(h - 1)
            if b is None or prev is None:
                continue
            if direccion == -1 and b.bajista and b.cuerpo >= 0.5 * b.rango and b.c < prev.l:
                ob = _ultimo_ob(h1d, h, direccion)
                if ob is not None:
                    b7 = h1d.get(7)
                    sl = b7.h if (b7 and direccion == -1) else (b7.l if b7 else None)
                    if sl is None:
                        return None
                    return Deteccion("NYR2", -1, 8, sl, alto_dia,
                                     f"alto del dia a las {hora_ext:02d}:00, desplaz. {h:02d}:00, OB {ob:02d}:00")
            if direccion == 1 and b.alcista and b.cuerpo >= 0.5 * b.rango and b.c > prev.h:
                ob = _ultimo_ob(h1d, h, direccion)
                if ob is not None:
                    b7 = h1d.get(7)
                    sl = b7.l if b7 else None
                    if sl is None:
                        return None
                    return Deteccion("NYR2", 1, 8, sl, bajo_dia,
                                     f"bajo del dia a las {hora_ext:02d}:00, desplaz. {h:02d}:00, OB {ob:02d}:00")
        return None

    d = busca(hora_alto, -1)
    if d:
        return d
    return busca(hora_bajo, 1)


def _ultimo_ob(h1d: dict[int, Bar], hora_desplaz: int, direccion: int) -> Optional[int]:
    """Ultima H1 de color contrario antes de la vela de desplazamiento."""
    for h in range(hora_desplaz - 1, -1, -1):
        b = h1d.get(h)
        if b is None:
            continue
        if direccion == -1 and b.alcista:
            return h
        if direccion == 1 and b.bajista:
            return h
    return None


def detecta_lrlr(h1d: dict[int, Bar], direccion_ldn: int) -> tuple[bool, Optional[float]]:
    """LRLR: pullback del movimiento de Londres fuera de killzone (05-07).
    Devuelve (existe, extremo_del_pullback)."""
    barras = [h1d[h] for h in (5, 6, 7) if h in h1d]
    if not barras:
        return False, None
    if direccion_ldn == -1:
        contra = [b for b in barras if b.alcista]
        if contra:
            return True, max(b.h for b in barras)
    else:
        contra = [b for b in barras if b.bajista]
        if contra:
            return True, min(b.l for b in barras)
    return False, None


def detecta_nyc1(h1d: dict[int, Bar], n: Niveles, ldn: Optional[Deteccion]) -> Optional[Deteccion]:
    """NY Continuation.1: London Reversal previo (LR1 preferente, extremo de
    Londres a las 03:00/04:00) + LRLR. Entrada 08:00 (o 09:00)."""
    if ldn is None or ldn.modelo not in ("LR1", "LR21"):
        return None
    # extremo de Londres en 03:00 o 04:00
    horas_ldn = [h for h in range(2, 8) if h in h1d]
    if not horas_ldn:
        return None
    if ldn.direccion == -1:
        ext_nivel = max(h1d[h].h for h in horas_ldn)
        hora_ext = max(h for h in horas_ldn if h1d[h].h == ext_nivel)
        sl = n.ldn_h
    else:
        ext_nivel = min(h1d[h].l for h in horas_ldn)
        hora_ext = max(h for h in horas_ldn if h1d[h].l == ext_nivel)
        sl = n.ldn_l
    if hora_ext not in (2, 3, 4):
        return None
    existe, pullback = detecta_lrlr(h1d, ldn.direccion)
    if not existe or sl is None:
        return None
    nota = f"continua LR direccion {'corto' if ldn.direccion==-1 else 'largo'}, LRLR={pullback:.5f}"
    d = Deteccion("NYC1", ldn.direccion, 8, sl, pullback, nota)
    return d


def detecta_nyr1(h1d: dict[int, Bar], n: Niveles) -> Optional[Deteccion]:
    """NY Reversal.1: 08:00 o 09:00 toma LDNH/LDNL y cierra de vuelta dentro."""
    # a diferencia de los raids de Londres, aqui el spec solo pide "cierra de
    # vuelta dentro / contexto de rechazo": no se exige color de vela
    for hora in (8, 9):
        b = h1d.get(hora)
        if b is None:
            continue
        entrada = hora + 1
        if _toma_alto(b, n.ldn_h) and b.c < n.ldn_h:
            return Deteccion("NYR1", -1, entrada, b.h, n.ldn_h, f"raid LDNH {hora:02d}:00")
        if _toma_bajo(b, n.ldn_l) and b.c > n.ldn_l:
            return Deteccion("NYR1", 1, entrada, b.l, n.ldn_l, f"raid LDNL {hora:02d}:00")
    return None


def detecta_nyc2(ldn: Optional[Deteccion], nyc1: Optional[Deteccion],
                 hay_noticia: bool) -> Optional[Deteccion]:
    """NY Continuation.2: solo si el dia ya tiene LR1 y NYC1. Tercer trade.
    Riesgo 0.5R. Con noticia, va envuelto en el News Protocol."""
    if ldn is None or ldn.modelo != "LR1" or nyc1 is None:
        return None
    nota = "3er trade, 0.5R" + (", news protocol" if hay_noticia else "")
    return Deteccion("NYC2", nyc1.direccion, 9, nyc1.sl, None, nota)
