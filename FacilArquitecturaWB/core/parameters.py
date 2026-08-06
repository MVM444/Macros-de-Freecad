"""Spreadsheet parameter helpers for FacilArquitecturaWB.

Descripcion: crea y lee Spreadsheet_Parametros sin borrar valores existentes.
Fecha: 2026-07-25
Version: 0.4.2
Instrucciones: conservar valores del usuario cuando la hoja ya existe.
"""

from __future__ import annotations

import FreeCAD

from .constants import DEFAULT_PARAMETERS, PARAM_SHEET_NAME
from .project_structure import find_by_name_or_label, msg, set_prop, warn


def _cell(row: int, column: str) -> str:
    return "%s%d" % (column, row)


def ensure_parameter_sheet(doc, parent_group=None):
    """Create or update Spreadsheet_Parametros."""
    sheet = find_by_name_or_label(doc, PARAM_SHEET_NAME, PARAM_SHEET_NAME)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", PARAM_SHEET_NAME)
        sheet.Label = PARAM_SHEET_NAME
        msg("Hoja de parametros creada: %s" % PARAM_SHEET_NAME)
        try:
            sheet.set("A1", "Parametro")
            sheet.set("B1", "Valor_mm")
            sheet.set("C1", "Notas")
        except Exception as exc:
            warn("No se pudo escribir encabezado de parametros: %s" % exc)
    else:
        msg("Hoja de parametros existente: %s" % PARAM_SHEET_NAME)

    existing = _read_parameter_rows(sheet)
    row = max(existing.values(), default=1) + 1
    for key, default_value in DEFAULT_PARAMETERS:
        if key in existing:
            continue
        _write_parameter(sheet, row, key, default_value)
        row += 1

    set_prop(sheet, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "parameters")
    try:
        if parent_group is not None and sheet not in list(getattr(parent_group, "Group", []) or []):
            parent_group.addObject(sheet)
    except Exception:
        pass
    return sheet


def _read_parameter_rows(sheet):
    result = {}
    for row in range(2, 200):
        try:
            key = str(sheet.get(_cell(row, "A")) or "").strip()
        except Exception:
            key = ""
        if key:
            result[key] = row
    return result


def _write_parameter(sheet, row: int, key: str, value: float) -> None:
    try:
        sheet.set(_cell(row, "A"), key)
        sheet.set(_cell(row, "B"), str(float(value)))
        sheet.set(_cell(row, "C"), "Parametro base Facil Arquitectura")
        try:
            sheet.setAlias(_cell(row, "B"), key)
        except Exception:
            pass
        msg("Parametro creado: %s = %s" % (key, value))
    except Exception as exc:
        warn("No se pudo crear parametro %s: %s" % (key, exc))


def get_parameter(sheet, key: str, default_value: float) -> float:
    """Read parameter by alias or by table row."""
    try:
        value = sheet.get(key)
        if value not in (None, ""):
            return float(value)
    except Exception:
        pass
    for row in range(2, 200):
        try:
            row_key = str(sheet.get(_cell(row, "A")) or "").strip()
            if row_key == key:
                return float(sheet.get(_cell(row, "B")))
        except Exception:
            continue
    return float(default_value)


def read_parameters(sheet) -> dict:
    """Return all known default parameters with current values."""
    return {key: get_parameter(sheet, key, default) for key, default in DEFAULT_PARAMETERS}
