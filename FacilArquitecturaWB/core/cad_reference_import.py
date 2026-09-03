"""Reusable DWG/DXF reference import for FacilArquitecturaWB.

Descripcion: convierte DWG con el convertidor configurado por FreeCAD, corrige la
escala segun la unidad real elegida e importa en un documento nuevo sin guardar.
Fecha: 2026-07-31
Version: 0.1.0
Instrucciones: nunca usar la etiqueta visible como nombre interno del documento.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import tempfile
import time
from pathlib import Path

from .freecad_compat import dxf_waitcursor_workaround

try:
    import FreeCAD as App
except ImportError:  # Permite probar las funciones puras fuera de FreeCAD.
    App = None


UNIT_FACTORS_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
}

INSUNITS_FACTORS_MM = {
    1: 25.4,  # pulgadas
    2: 304.8,  # pies
    3: 1609344.0,  # millas
    4: 1.0,  # milimetros
    5: 10.0,  # centimetros
    6: 1000.0,  # metros
    7: 1000000.0,  # kilometros
    8: 0.0000254,  # micropulgadas
    9: 0.0254,  # mils
    10: 914.4,  # yardas
    11: 0.0000001,  # angstroms
    12: 0.000001,  # nanometros
    13: 0.001,  # micras
    14: 100.0,  # decimetros
}


IMPORT_PROFILE = {
    "dxfUseLegacyImporter": ("Boolean", False),
    "dxfImportAsDraft": ("Boolean", False),
    "dxfImportAsPrimitives": ("Boolean", False),
    "dxfImportAsShapes": ("Boolean", False),
    "dxfImportAsFused": ("Boolean", True),
    "DxfImportMode": ("Integer", 3),
    "dxftext": ("Boolean", True),
    "dxflayout": ("Boolean", True),
    "dxfstarblocks": ("Boolean", True),
    "dxfUseDraftVisGroups": ("Boolean", True),
}


def _import_log(stage, started=None, **details):
    fields = []
    if started is not None:
        fields.append("elapsed=%.6fs" % (time.perf_counter() - started))
    fields.extend("%s=%s" % (key, details[key]) for key in sorted(details))
    suffix = " | " + " | ".join(fields) if fields else ""
    message = "[FACILARQ][IMPORT] %s%s\n" % (stage, suffix)
    if App is not None:
        App.Console.PrintMessage(message)
    return message


def _preference_contents(prefs):
    try:
        return {str(name): (str(kind), value) for kind, name, value in prefs.GetContents()}
    except Exception:
        return {}


def _snapshot_preferences(prefs, names):
    contents = _preference_contents(prefs)
    return {name: contents.get(name) for name in names}


def _set_preference(prefs, name, kind, value):
    setters = {
        "Boolean": prefs.SetBool,
        "Integer": prefs.SetInt,
        "Float": prefs.SetFloat,
        "String": prefs.SetString,
    }
    setters[kind](name, value)


def _remove_preference(prefs, name, kind):
    removers = {
        "Boolean": "RemBool",
        "Integer": "RemInt",
        "Float": "RemFloat",
        "String": "RemString",
    }
    remover = getattr(prefs, removers[kind], None)
    if remover is not None:
        remover(name)


def _restore_preferences(prefs, snapshot, kinds):
    for name, previous in snapshot.items():
        if previous is None:
            _remove_preference(prefs, name, kinds[name])
            continue
        kind, value = previous
        _set_preference(prefs, name, kind, value)


def _apply_import_profile(prefs, manual_scale):
    profile = dict(IMPORT_PROFILE)
    profile["dxfScaling"] = ("Float", float(manual_scale))
    profile["dxfShowDialog"] = ("Boolean", False)
    for name, (kind, value) in profile.items():
        _set_preference(prefs, name, kind, value)
    return profile


def _profile_values(prefs, profile):
    contents = _preference_contents(prefs)
    return {name: contents.get(name, (kind, None))[1] for name, (kind, _value) in profile.items()}


def _iter_dxf_pairs(path):
    with open(path, "r", encoding="latin-1", errors="replace") as stream:
        while True:
            code_line = stream.readline()
            if not code_line:
                return
            value_line = stream.readline()
            if not value_line:
                return
            try:
                code = int(code_line.strip())
            except ValueError:
                continue
            yield code, value_line.rstrip("\r\n")


def read_dxf_header_units(path):
    """Return INSUNITS and MEASUREMENT values from a DXF header."""
    section = None
    expect_section_name = False
    current_variable = None
    result = {"insunits": None, "measurement": None}

    for code, value in _iter_dxf_pairs(path):
        if code == 0 and value == "SECTION":
            expect_section_name = True
            current_variable = None
            continue
        if expect_section_name:
            section = value if code == 2 else None
            expect_section_name = False
            continue
        if code == 0 and value == "ENDSEC":
            if section == "HEADER":
                break
            section = None
            current_variable = None
            continue
        if section != "HEADER":
            continue
        if code == 9:
            current_variable = value
            continue
        if current_variable not in ("$INSUNITS", "$MEASUREMENT"):
            continue
        try:
            number = int(value.strip())
        except ValueError:
            continue
        if current_variable == "$INSUNITS":
            result["insunits"] = number
        else:
            result["measurement"] = number
        current_variable = None

    return result


def automatic_mm_per_unit(insunits=None, measurement=None):
    """Replicate the unit factor used by FreeCAD's Draft DXF importer."""
    try:
        unit_code = int(insunits or 0)
    except (TypeError, ValueError):
        unit_code = 0
    if unit_code in INSUNITS_FACTORS_MM:
        return float(INSUNITS_FACTORS_MM[unit_code])
    if unit_code == 0:
        if measurement == 0:
            return 25.4
        return 1.0
    return 1.0


def manual_scaling_for(unit_key, insunits=None, measurement=None):
    """Return the manual Draft scale needed for the selected real drawing unit."""
    key = str(unit_key or "auto").strip().lower()
    if key == "auto":
        return 1.0
    if key not in UNIT_FACTORS_MM:
        raise ValueError("Unidad CAD no soportada: %s" % unit_key)
    automatic = automatic_mm_per_unit(insunits, measurement)
    return float(UNIT_FACTORS_MM[key]) / float(automatic or 1.0)


def resolved_mm_per_unit(unit_key, insunits=None, measurement=None):
    automatic = automatic_mm_per_unit(insunits, measurement)
    return automatic * manual_scaling_for(unit_key, insunits, measurement)


def safe_document_name(label):
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(label or "Referencia_CAD")).strip("_")
    if not text:
        text = "Referencia_CAD"
    if text[0].isdigit():
        text = "CAD_" + text
    return text


def unique_document_name(label, existing_names):
    base = safe_document_name(label)
    existing = {str(name) for name in (existing_names or ())}
    if base not in existing:
        return base
    index = 2
    while "%s_%03d" % (base, index) in existing:
        index += 1
    return "%s_%03d" % (base, index)


def _require_freecad():
    if App is None:
        raise RuntimeError("Este flujo debe ejecutarse dentro de FreeCAD.")


def _convert_to_dxf(source):
    suffix = source.suffix.lower()
    if suffix == ".dxf":
        return source, False
    if suffix != ".dwg":
        raise ValueError("Seleccione un archivo DWG o DXF.")

    import importDWG

    converted = importDWG.convertToDxf(str(source))
    if not converted or not os.path.isfile(converted):
        raise RuntimeError(
            "No fue posible convertir el DWG. Revise el convertidor ODA configurado en FreeCAD."
        )
    return Path(converted), True


def _cleanup_temporary_conversion(source, converted, is_temporary):
    if not is_temporary:
        return
    try:
        source = Path(source).resolve()
        converted = Path(converted).resolve()
        temp_root = Path(tempfile.gettempdir()).resolve()
        common = os.path.commonpath((str(temp_root), str(converted.parent)))
        if os.path.normcase(common) != os.path.normcase(str(temp_root)):
            return
        if converted.parent == source.parent or converted.stem != source.stem:
            return
        converted.unlink(missing_ok=True)
        try:
            converted.parent.rmdir()
        except OSError:
            pass
    except Exception:
        pass


def _placement_bounds(objects):
    positions = []
    for obj in objects:
        try:
            point = obj.Placement.Base
            if abs(point.x) + abs(point.y) + abs(point.z) <= 1e-9:
                continue
            positions.append((float(point.x), float(point.y), float(point.z)))
        except Exception:
            continue
    if not positions:
        return None
    return {
        "min_mm": [min(row[index] for row in positions) for index in range(3)],
        "max_mm": [max(row[index] for row in positions) for index in range(3)],
    }


def _add_metadata(doc, source, unit_key, header, manual_scale, imported_count):
    metadata = doc.addObject("App::FeaturePython", "FA_CADImportMetadata")
    metadata.Label = "FA Importacion CAD"
    properties = (
        ("App::PropertyString", "FA_GeneratedBy", "Facil Arquitectura"),
        ("App::PropertyString", "FA_SourcePath", "Facil Arquitectura"),
        ("App::PropertyString", "FA_SourceUnit", "Facil Arquitectura"),
        ("App::PropertyInteger", "FA_HeaderInsUnits", "Facil Arquitectura"),
        ("App::PropertyFloat", "FA_ManualScale", "Facil Arquitectura"),
        ("App::PropertyFloat", "FA_ResolvedMMPerUnit", "Facil Arquitectura"),
        ("App::PropertyInteger", "FA_ImportedObjectCount", "Facil Arquitectura"),
        ("App::PropertyString", "FA_ImportedAt", "Facil Arquitectura"),
    )
    for property_type, name, group in properties:
        try:
            metadata.addProperty(property_type, name, group)
        except Exception:
            pass
    metadata.FA_GeneratedBy = "FA_ImportCADReference"
    metadata.FA_SourcePath = str(source)
    metadata.FA_SourceUnit = str(unit_key)
    metadata.FA_HeaderInsUnits = int(header.get("insunits") or 0)
    metadata.FA_ManualScale = float(manual_scale)
    metadata.FA_ResolvedMMPerUnit = float(
        resolved_mm_per_unit(unit_key, header.get("insunits"), header.get("measurement"))
    )
    metadata.FA_ImportedObjectCount = int(imported_count)
    metadata.FA_ImportedAt = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        metadata.ViewObject.Visibility = False
    except Exception:
        pass
    return metadata


def _insert_dxf_with_compat(import_dxf_module, converted, document_name):
    """Run one Draft DXF insertion through the isolated compatibility layer."""
    with dxf_waitcursor_workaround(import_dxf_module=import_dxf_module):
        return import_dxf_module.insert(str(converted), document_name)


def import_cad_reference(source_path, unit_key="auto", fit_view=True):
    """Import a DWG/DXF into a new unsaved FreeCAD document.

    The active document is never used as the destination. Draft preferences are
    restored even if conversion or import fails.
    """
    _require_freecad()
    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(str(source))
    if source.suffix.lower() not in (".dwg", ".dxf"):
        raise ValueError("Seleccione un archivo DWG o DXF.")

    converted = None
    temporary = False
    doc = None
    result = None
    prefs = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
    profile_kinds = {name: kind for name, (kind, _value) in IMPORT_PROFILE.items()}
    profile_kinds.update({"dxfScaling": "Float", "dxfShowDialog": "Boolean"})
    preference_snapshot = _snapshot_preferences(prefs, profile_kinds)
    operation_started = time.perf_counter()
    _import_log("import_cad_reference inicio", source=source.name, fit_view=bool(fit_view))
    _import_log(
        "preferencias antes",
        values=json.dumps(
            {name: previous[1] if previous else None for name, previous in preference_snapshot.items()},
            ensure_ascii=True,
            sort_keys=True,
        ),
    )

    try:
        stage_started = time.perf_counter()
        _import_log("conversion DWG->DXF inicio", source=source.name)
        converted, temporary = _convert_to_dxf(source)
        _import_log(
            "conversion DWG->DXF fin",
            stage_started,
            converted=str(converted),
            temporary=bool(temporary),
        )
        header = read_dxf_header_units(converted)
        manual_scale = manual_scaling_for(
            unit_key,
            header.get("insunits"),
            header.get("measurement"),
        )
        profile = _apply_import_profile(prefs, manual_scale)
        _import_log(
            "preferencias activas",
            values=json.dumps(_profile_values(prefs, profile), ensure_ascii=True, sort_keys=True),
        )
        _import_log("DXF temporal", path=str(converted), retained_for_run=not temporary)

        internal_name = unique_document_name(source.stem, App.listDocuments().keys())
        doc = App.newDocument(internal_name)
        doc.Label = source.stem
        before_names = {obj.Name for obj in doc.Objects}

        import importDXF

        stage_started = time.perf_counter()
        _import_log("importDXF.insert inicio", document=doc.Name)
        _insert_dxf_with_compat(importDXF, converted, doc.Name)
        _import_log("importDXF.insert fin", stage_started, objects=len(doc.Objects))

        stage_started = time.perf_counter()
        _import_log("primer recompute inicio")
        doc.recompute()
        _import_log("primer recompute fin", stage_started)

        stage_started = time.perf_counter()
        _import_log("construccion imported inicio")
        imported = [obj for obj in doc.Objects if obj.Name not in before_names]
        _import_log("construccion imported fin", stage_started, objects=len(imported))
        if not imported:
            raise RuntimeError("La importacion no creo objetos en FreeCAD.")

        stage_started = time.perf_counter()
        _import_log("metadata inicio")
        metadata = _add_metadata(
            doc,
            source,
            unit_key,
            header,
            manual_scale,
            len(imported),
        )
        _import_log("metadata fin", stage_started)

        stage_started = time.perf_counter()
        _import_log("segundo recompute inicio")
        doc.recompute()
        _import_log("segundo recompute fin", stage_started)

        if fit_view and bool(getattr(App, "GuiUp", False)):
            try:
                import FreeCADGui as Gui

                stage_started = time.perf_counter()
                _import_log("viewTop inicio")
                Gui.activeDocument().activeView().viewTop()
                _import_log("viewTop fin", stage_started)

                stage_started = time.perf_counter()
                _import_log("fitAll inicio")
                Gui.activeDocument().activeView().fitAll()
                _import_log("fitAll fin", stage_started)
            except Exception:
                pass

        stage_started = time.perf_counter()
        _import_log("placement_bounds inicio")
        placement_bounds = _placement_bounds(imported)
        _import_log("placement_bounds fin", stage_started)
        result = {
            "document": doc,
            "metadata": metadata,
            "source": str(source),
            "converted_dxf": str(converted),
            "unit_key": str(unit_key),
            "header_insunits": header.get("insunits"),
            "header_measurement": header.get("measurement"),
            "manual_scale": float(manual_scale),
            "resolved_mm_per_unit": float(
                resolved_mm_per_unit(
                    unit_key,
                    header.get("insunits"),
                    header.get("measurement"),
                )
            ),
            "imported_object_count": len(imported),
            "placement_bounds": placement_bounds,
            "saved": bool(doc.FileName),
        }
        App.Console.PrintMessage(
            "[FACILARQ] Referencia CAD importada: %s | objetos=%d | 1 unidad=%.6g mm\n"
            % (source.name, len(imported), result["resolved_mm_per_unit"])
        )
    except Exception:
        if doc is not None:
            try:
                App.closeDocument(doc.Name)
            except Exception:
                pass
        raise
    finally:
        finally_started = time.perf_counter()
        _import_log("finally entrada")
        _restore_preferences(prefs, preference_snapshot, profile_kinds)
        _import_log("preferencias restauradas")
        if converted is not None:
            cleanup_started = time.perf_counter()
            _cleanup_temporary_conversion(source, converted, temporary)
            _import_log("limpieza conversion temporal fin", cleanup_started)
        _import_log("finally salida", finally_started)

    _import_log(
        "import_cad_reference retorno",
        operation_started,
        objects=result["imported_object_count"],
    )
    return result
