#!/usr/bin/env python3
"""
Entrada por breaker con stop en el OB de origen — el método de Asier.

Reglas, extraídas caso a caso sobre operaciones reales de diciembre de 2025:

  ZONA        cada vela que precede a un desplazamiento es un order block. Su
              zona es el rango completo de la vela, mechas incluidas.
  POLARIDAD   un OB alcista (vela bajista en la base de una subida) es soporte;
              uno bajista (vela alcista antes de una caída) es resistencia. Si
              el precio cierra al otro lado, la zona **cambia de polaridad**:
              eso es el breaker. Puede voltear más de una vez.
  ENTRADA     primer toque del rango de la zona breaker más cercana en el
              sentido del trade — el borde de la vela, no su cuerpo.
  STOP        más allá del extremo de la siguiente zona en la cadena (el OB que
              originó el impulso a favor). Si eso da más riesgo del tope, se
              aprieta al *open* de esa zona; si aún no cabe, se descarta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PIP = 0.0001


@dataclass
class Zona:
    t: datetime
    o: float
    h: float
    l: float
    c: float
    vela_alcista: bool
    polaridad: str          # "soporte" | "resistencia"
    volteada_t: datetime | None = None
    cuerpo_p: float = 0.0

    @property
    def borde_inferior(self) -> float:
        return self.l

    @property
    def borde_superior(self) -> float:
        return self.h


def detecta_zonas(bars, cuerpo_min_ratio: float = 1.0, ventana_mediana: int = 20,
                  instantes=None):
    """instantes: conjunto de timestamps en los que capturar el estado.

    Se copia la zona al capturar: guardar la referencia daría la polaridad final
    de la serie, no la que había en ese momento.
    """
    """Devuelve, para cada vela, la lista de zonas vivas con su polaridad actual.

    Una vela es order block cuando otra posterior cierra a través de su open:
    la que cierra al alza convierte a la bajista previa en soporte; la que
    cierra a la baja convierte a la alcista previa en resistencia.
    """

    zonas: list[Zona] = []
    estados: dict = {}
    ult_alcista = ult_bajista = None
    cuerpos: list[float] = []

    for b in bars:
        cuerpo = abs(b.c - b.o)
        med = sorted(cuerpos[-ventana_mediana:])[len(cuerpos[-ventana_mediana:]) // 2] if len(cuerpos) >= 5 else 0.0
        significativa = cuerpo >= cuerpo_min_ratio * med if med > 0 else True

        # activación: una vela cierra a través del open del OB contrario
        if b.c > b.o and ult_bajista is not None and b.c > ult_bajista.o:
            ult_bajista.polaridad = "soporte"
            if ult_bajista not in zonas:
                zonas.append(ult_bajista)
            ult_bajista = None
        if b.c < b.o and ult_alcista is not None and b.c < ult_alcista.o:
            ult_alcista.polaridad = "resistencia"
            if ult_alcista not in zonas:
                zonas.append(ult_alcista)
            ult_alcista = None

        # volteo de polaridad: el precio cierra al otro lado de una zona viva
        for z in zonas:
            if z.polaridad == "soporte" and b.c < z.l:
                z.polaridad, z.volteada_t = "resistencia", b.t
            elif z.polaridad == "resistencia" and b.c > z.h:
                z.polaridad, z.volteada_t = "soporte", b.t

        if instantes is None or b.t in instantes:
            estados[b.t] = [Zona(z.t, z.o, z.h, z.l, z.c, z.vela_alcista,
                                 z.polaridad, z.volteada_t, z.cuerpo_p) for z in zonas]

        cuerpos.append(cuerpo)
        # la vela actual pasa a ser candidata a OB
        if significativa:
            z = Zona(b.t, b.o, b.h, b.l, b.c, b.c > b.o, "", None, cuerpo / PIP)
            if b.c > b.o:
                ult_alcista = z
            elif b.c < b.o:
                ult_bajista = z
        # limpieza: como mucho 60 zonas vivas
        if len(zonas) > 60:
            del zonas[:-60]

    return estados


def elige_entrada(zonas_vivas, precio, es_largo, tope_riesgo_p=12.0, colchon_p=1.0,
                  max_dist_p=25.0, ahora=None, frescura_h=24.0):
    """Breaker = la zona volteada MÁS RECIENTEMENTE en el sentido del trade.

    No la más cercana: la que acaba de cambiar de polaridad, que es la que marca
    la estructura vigente. El stop va en la siguiente zona de la cadena.
    """
    # solo zonas formadas recientemente: las viejas se voltean una y otra vez
    # cada vez que el precio las cruza y dejan de representar la estructura viva
    frescas = zonas_vivas
    if ahora is not None:
        frescas = [z for z in zonas_vivas
                   if (ahora - z.t).total_seconds() <= frescura_h * 3600]
    if es_largo:
        cand = [z for z in frescas if z.polaridad == "soporte" and z.h <= precio
                and (precio - z.h) <= max_dist_p * PIP]
        cand.sort(key=lambda z: -z.h)          # la más cercana por debajo
    else:
        cand = [z for z in frescas if z.polaridad == "resistencia" and z.l >= precio
                and (z.l - precio) <= max_dist_p * PIP]
        cand.sort(key=lambda z: z.l)           # la más cercana por encima
    if not cand:
        return None
    breaker = cand[0]
    entrada = breaker.h if es_largo else breaker.l

    # zona siguiente en la cadena: el OB que originó el impulso a favor
    if es_largo:
        detras = [z for z in frescas if z.h < breaker.l]
    else:
        detras = [z for z in frescas if z.l > breaker.h]
    detras.sort(key=lambda z: -z.h if es_largo else z.l)
    siguiente = detras[0] if detras else None

    opciones = []
    if siguiente is not None:
        opciones.append(siguiente.l - colchon_p * PIP if es_largo else siguiente.h + colchon_p * PIP)
        opciones.append(siguiente.o)          # apretado al open, como en el 15/12
    opciones.append(breaker.l - colchon_p * PIP if es_largo else breaker.h + colchon_p * PIP)

    for sl in opciones:
        riesgo = abs(entrada - sl)
        if 0 < riesgo <= tope_riesgo_p * PIP:
            return dict(breaker=breaker, siguiente=siguiente, entrada=entrada,
                        sl=sl, riesgo_p=riesgo / PIP)
    return None
