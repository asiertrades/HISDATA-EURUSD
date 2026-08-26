# -*- coding: utf-8 -*-
"""
Auditoria del calendario de detectores contra los trades etiquetados de Josh
(josh_eurusd_2025_labeled_trades.csv, extraidos de sus posts publicos).

Reglas del cruce:
- label_quality == explicit_model  -> ground truth de calendario.
- session_hours_only_*             -> pistas, no labels cerrados.
- missed_opportunity_stated        -> la oportunidad existia; no es trade tomado.
- Los dias de 2025 sin post NO se consideran vacios: la frecuencia del detector
  se reporta como contexto, no como false-positive por dia.

Veredictos por fila:
  PRIMARY_MATCH  la familia etiquetada es el modelo primario del detector
  FAMILY_MATCH   la familia esta detectada ese dia, pero no como primario
  MISSED         la familia NO esta detectada ese dia (fallo del detector)
  NO_SESSION     el dia no tiene sesion evaluable
  UNMAPPED       la etiqueta no corresponde a ningun modelo del spec
"""
from __future__ import annotations

import csv
import re
from datetime import datetime

from josh_calendario import carga_todo, evalua_dia

FAMILIAS = {
    "asia": {"ASIA1", "ASIA2"},
    "london_reversal": {"LR1", "LR21", "LR22"},
    "ny_reversal": {"NYR1", "NYR2"},
    "ny_continuation": {"NYC1", "NYC2"},
}

# horas relevantes por modelo (raid + entrada) para el cruce con las horas del post
HORAS_MODELO = {
    "LR21": {1, 2, 3}, "LR1": {2, 3, 4}, "ASIA1": {2, 3}, "ASIA2": {2, 3},
    "LR22": {4, 5}, "NYR2": {5, 6, 7, 8}, "NYC1": {8, 9},
    "NYR1": {8, 9, 10}, "NYC2": {9, 10},
}


def familias_de(texto: str) -> list[str]:
    t = texto.lower()
    fams = []
    if "asia" in t:
        fams.append("asia")
    if "london reversal" in t or "london" in t and "reversal" in t:
        fams.append("london_reversal")
    if "ny reversal" in t:
        fams.append("ny_reversal")
    if "ny continuation" in t or "continuation.1" in t:
        fams.append("ny_continuation")
    if "london continuation" in t:
        fams.append("_london_continuation")  # no existe en el spec
    return fams


def horas_de(texto: str) -> set[int]:
    horas = set()
    for m in re.finditer(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", texto, re.I):
        h = int(m.group(1))
        if m.group(3) and m.group(3).upper() == "PM" and h != 12:
            h += 12
        if 0 <= h <= 16:
            horas.add(h)
    return horas


def audita():
    _, h1, d1, h4, h1_por_dia, d1_por_dia, m15dh = carga_todo()

    filas_out = []
    with open("josh_eurusd_2025_labeled_trades.csv") as f:
        etiquetas = list(csv.DictReader(f))

    for e in etiquetas:
        fecha = datetime.strptime(e["date"], "%Y-%m-%d").date()
        calidad = e["label_quality"]
        fams = familias_de(e["mapped_notion_model"])
        horas_post = horas_de(e["entry_hours_mentioned"] or "")
        dir_post = {"long": 1, "short": -1}.get(e["direction_if_stated"])

        fila_cal, det = evalua_dia(fecha, h1_por_dia, d1_por_dia, h4, m15dh)
        detectados = list(det.keys()) if det else []
        primario = fila_cal["primary_model"]

        if fila_cal["status"] == "no_session":
            veredicto = "NO_SESSION"
        elif not fams:
            veredicto = "UNMAPPED"
        elif fams == ["_london_continuation"]:
            veredicto = "UNMAPPED"
        else:
            fams_reales = [f for f in fams if f in FAMILIAS]
            todo_detectado, primario_ok = True, False
            for fam in fams_reales:
                modelos = FAMILIAS[fam] & set(detectados)
                if not modelos:
                    todo_detectado = False
                if primario in FAMILIAS[fam]:
                    primario_ok = True
            if not fams_reales:
                veredicto = "UNMAPPED"
            elif todo_detectado and primario_ok:
                veredicto = "PRIMARY_MATCH"
            elif todo_detectado:
                veredicto = "FAMILY_MATCH"
            else:
                veredicto = "MISSED"

        # direccion y hora, informativos
        dir_ok = ""
        hora_ok = ""
        if det and fams:
            modelos_fam = set()
            for fam in fams:
                modelos_fam |= FAMILIAS.get(fam, set())
            candidatos = [m for m in detectados if m in modelos_fam]
            if candidatos:
                if dir_post is not None:
                    dir_ok = "si" if any(det[m].direccion == dir_post for m in candidatos) else "NO"
                if horas_post:
                    hora_ok = "si" if any(horas_post & HORAS_MODELO[m] for m in candidatos) else "NO"

        filas_out.append({
            "date": e["date"], "weekday": e["weekday"], "label_quality": calidad,
            "josh_model": e["mapped_notion_model"], "josh_dir": e["direction_if_stated"],
            "josh_hours": e["entry_hours_mentioned"],
            "detected": ">".join(detectados), "primary": primario,
            "verdict": veredicto, "dir_match": dir_ok, "hour_match": hora_ok,
            "excerpt": e["raw_excerpt"][:60],
        })

    with open("josh_audit_vs_labels.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas_out[0].keys()))
        w.writeheader()
        w.writerows(filas_out)

    # ── resumen ──
    from collections import Counter
    explicitos = [r for r in filas_out if r["label_quality"] == "explicit_model"]
    pistas = [r for r in filas_out if r["label_quality"].startswith("session_hours")]
    print("═══ GROUND TRUTH (explicit_model,", len(explicitos), "dias) ═══")
    print(dict(Counter(r["verdict"] for r in explicitos)))
    print("direccion (cuando Josh la da):", dict(Counter(r["dir_match"] for r in explicitos if r["dir_match"])))
    print("hora (cuando Josh la da):     ", dict(Counter(r["hour_match"] for r in explicitos if r["hour_match"])))
    print()
    for r in explicitos:
        marca = {"PRIMARY_MATCH": "OK ", "FAMILY_MATCH": "ok-", "MISSED": "XXX",
                 "UNMAPPED": "?? ", "NO_SESSION": "-- "}[r["verdict"]]
        extra = []
        if r["dir_match"]: extra.append(f"dir:{r['dir_match']}")
        if r["hour_match"]: extra.append(f"hora:{r['hour_match']}")
        print(f"{marca} {r['date']} {r['weekday'][:3]}  josh={r['josh_model'][:38]:38s}"
              f" det={r['detected'][:34]:34s} prim={r['primary']:5s} {' '.join(extra)}")
    print()
    print("═══ PISTAS (session_hours_only,", len(pistas), "dias) ═══")
    print(dict(Counter(r["verdict"] for r in pistas)))
    for r in filas_out:
        if r["label_quality"] == "missed_opportunity_stated":
            print(f"\n(oportunidad perdida segun Josh) {r['date']}: det={r['detected']} prim={r['primary']}")
    print("\n-> josh_audit_vs_labels.csv")


if __name__ == "__main__":
    audita()
