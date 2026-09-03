"""FreeCAD adapter for ElementDataCore and Spreadsheet_Puertas.

Nombre: door_table_utils.py
Proposito: extraer, validar, transferir y aplicar propiedades de puertas BIM nativas.
Funcionamiento: el Sketch destino manda en posicion/orientacion/ancho; la tabla manda
sobre tipo, altura, bisagra, sentido de apertura y datos descriptivos. Hosts y Level se
resuelven nuevamente en el documento destino.
FreeCAD objetivo: 1.1.3.
Version: 0.4.0.
Fecha y hora: 2026-09-01 15:25 America/Costa_Rica.
Mantenimiento: conservar JSON-compatible, dry_run por defecto y proteccion de puertas
manuales. Nuevos tipos deben registrarse como preset FreeCAD o factory explicita.
"""

from __future__ import annotations

import math

import FreeCAD

from .element_data_core import (
    CATEGORY_DOORS,
    SCHEMA_VERSION,
    build_table_data,
    plan_application,
    validate_records,
)
from .bim_structure_utils import ensure_auxiliary_parent, ensure_bim_structure
from .door_type_utils import (
    DOUBLE_DOOR_GENERATOR,
    DOUBLE_DOOR_SPEC_ID,
    TYPE_SOURCE_DOUBLE,
    TYPE_SOURCE_NATIVE,
    door_preset_name,
    is_special_fa_double_door,
    resolve_door_type,
)
from .double_door_bim import create_double_door_bim, normalized_parameters
from .opening_utils import (
    GENERATED_BY_DOORS,
    LEGACY_GENERATORS,
    apply_door_corner_metadata,
    create_native_door_from_axis_plan,
    is_bim_wall,
    native_door_opening_mode,
    resolve_door_corner_snap,
    resolve_door_native_mode,
    select_best_host,
    sketch_segments,
    wall_source_segments,
)
from .project_structure import set_prop


SHEET_NAME = "Spreadsheet_Puertas"
SHEET_LABEL = "Tabla de puertas"
TABLE_GENERATOR = "FA_DoorTable"
DEFAULT_HOST_TOLERANCE_MM = 250.0

COLUMNS = (
    ("A", "ElementID", "ElementID"),
    ("B", "SourceSketch", "SourceSketch"),
    ("C", "GeometryIndex", "GeometryIndex"),
    ("D", "CenterX", "CenterX"),
    ("E", "CenterY", "CenterY"),
    ("F", "WidthSketch", "Length"),
    ("G", "AngleDeg", "AngleDeg"),
    ("H", "Height", "Height"),
    ("I", "DoorType", "DoorType"),
    ("J", "TypeSource", "TypeSource"),
    ("K", "TypeRef", "TypeRef"),
    ("L", "Preset", "Preset"),
    ("M", "LeafCount", "LeafCount"),
    ("N", "HingeEndpoint", "HingeEndpoint"),
    ("O", "HingePointX", "HingePointX"),
    ("P", "HingePointY", "HingePointY"),
    ("Q", "OpeningSide", "OpeningSide"),
    ("R", "OpensInward", "OpensInward"),
    ("S", "Opening", "Opening"),
    ("T", "Room", "RoomKey"),
    ("U", "Level", "LevelKey"),
    ("V", "Status", "Status"),
    ("W", "Notes", "Notes"),
    ("X", "Frame", "Frame"),
    ("Y", "Offset", "Offset"),
    ("Z", "IfcType", "IfcType"),
    ("AA", "SchemaVersion", "SchemaVersion"),
)


def ensure_door_table(doc):
    """Create/reuse the canonical door table in the native BIM support tree when possible."""
    sheet = doc.getObject(SHEET_NAME)
    if sheet is not None and sheet.TypeId != "Spreadsheet::Sheet":
        raise RuntimeError("%s existe pero no es una Spreadsheet" % SHEET_NAME)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", SHEET_NAME)
        sheet.Label = SHEET_LABEL
    support_parent, _level = ensure_auxiliary_parent(doc, [sheet], legacy_key="tables")
    try:
        if sheet not in list(getattr(support_parent, "Group", []) or []):
            support_parent.addObject(sheet)
    except Exception:
        pass
    _tag_sheet(sheet)
    if not _cell_text(sheet, "A1"):
        _write_headers(sheet)
    return sheet


def write_door_records(sheet, records, statuses=None):
    data = build_table_data(CATEGORY_DOORS, records)
    statuses = dict(statuses or {})
    sheet.clearAll()
    _write_headers(sheet)
    for row_number, record in enumerate(data, start=2):
        for column, _header, field in COLUMNS:
            value = statuses.get(row_number - 2, "") if field == "Status" else record.get(field)
            if value is None or value == "":
                continue
            sheet.set("%s%d" % (column, row_number), _format_cell_value(field, value))
    _tag_sheet(sheet)
    sheet.recompute()
    return data


def read_door_records(sheet):
    records = []
    for row in range(2, _last_used_row(sheet) + 1):
        raw = {}
        for column, _header, field in COLUMNS:
            if field == "Status":
                continue
            raw[field] = _cell_text(sheet, "%s%d" % (column, row))
        if not any(str(value or "").strip() for value in raw.values()):
            continue
        for field in (
            "CenterX", "CenterY", "Length", "AngleDeg", "Height", "HingePointX",
            "HingePointY", "Opening", "Frame", "Offset",
        ):
            raw[field] = _parse_number(raw.get(field))
        raw["GeometryIndex"] = _parse_int(raw.get("GeometryIndex"))
        raw["LeafCount"] = _parse_int(raw.get("LeafCount"))
        raw["SchemaVersion"] = _parse_int(raw.get("SchemaVersion")) or SCHEMA_VERSION
        raw["OpensInward"] = _parse_bool(raw.get("OpensInward"))
        records.append(raw)
    return build_table_data(CATEGORY_DOORS, records)


def update_validation_statuses(sheet, report):
    for entry in report.get("entries", []):
        sheet.set("V%d" % (int(entry["row_index"]) + 2), str(entry["status"]))
    sheet.recompute()


def geometry_records_from_sketches(sketches):
    records = []
    for sketch in _unique_objects(sketches):
        for item in sketch_segments(sketch):
            segment = item["segment"]
            dx = segment[3] - segment[0]
            dy = segment[4] - segment[1]
            records.append(
                {
                    "SourceSketch": str(sketch.Name),
                    "GeometryIndex": int(item["index"]),
                    "CenterX": (segment[0] + segment[3]) * 0.5,
                    "CenterY": (segment[1] + segment[4]) * 0.5,
                    "Length": math.hypot(dx, dy),
                    "AngleDeg": math.degrees(math.atan2(dy, dx)) % 180.0,
                    "FirstX": float(segment[0]),
                    "FirstY": float(segment[1]),
                    "SecondX": float(segment[3]),
                    "SecondY": float(segment[4]),
                }
            )
    return records


def extract_door_records(doc):
    doors = [obj for obj in list(doc.Objects) if is_native_door(obj)]
    doors.sort(key=lambda obj: (str(getattr(obj, "Tag", "") or ""), obj.Name))
    records = []
    for index, door in enumerate(doors, start=1):
        source = getattr(door, "FA_SourceSketch", None) or getattr(door, "FA_SourceDoorAxes", None)
        geometry_index = _property_int(door, "FA_SourceGeometryIndex")
        geometry = _geometry_for_door(door, source, geometry_index)
        type_data = _type_from_door(door)
        hinge_endpoint = str(getattr(door, "FA_HingeEndpoint", "") or "").strip().upper()
        if not hinge_endpoint:
            hinge_endpoint = "BOTH" if type_data["LeafCount"] > 1 else "START"
        hinge_point = getattr(door, "FA_HingePoint", None)
        hx, hy = _vector_xy(hinge_point)
        if hx is None:
            if hinge_endpoint == "END":
                hx, hy = geometry.get("SecondX"), geometry.get("SecondY")
            else:
                hx, hy = geometry.get("FirstX"), geometry.get("FirstY")
        opening_side = str(getattr(door, "FA_OpeningSide", "") or "").strip().upper()
        if not opening_side:
            opening_side = _opening_side_from_normal(door, geometry)
        records.append(
            {
                "SchemaVersion": SCHEMA_VERSION,
                "ElementID": _element_id(door, index),
                "Category": CATEGORY_DOORS,
                "SourceSketch": str(getattr(source, "Name", "") or ""),
                "GeometryIndex": geometry_index,
                "CenterX": geometry.get("CenterX"),
                "CenterY": geometry.get("CenterY"),
                "Length": geometry.get("Length") or _quantity(door, "Width"),
                "AngleDeg": geometry.get("AngleDeg"),
                "Height": _quantity(door, "Height"),
                "DoorType": type_data["DoorType"],
                "TypeSource": type_data["TypeSource"],
                "TypeRef": type_data["TypeRef"],
                "Preset": type_data["Preset"],
                "LeafCount": type_data["LeafCount"],
                "HingeEndpoint": hinge_endpoint,
                "HingePointX": hx,
                "HingePointY": hy,
                "OpeningSide": opening_side,
                "OpensInward": _optional_bool_property(door, "FA_OpensInward"),
                "Opening": _quantity(door, "Opening"),
                "Frame": _quantity(door, "Frame"),
                "Offset": _quantity(door, "Offset"),
                "IfcType": "Door",
                "RoomKey": str(getattr(door, "FA_TargetRoomName", "") or getattr(door, "FA_RoomKey", "") or ""),
                "LevelKey": _level_key(door),
                "GeneratedBy": str(getattr(door, "FA_GeneratedBy", "") or ""),
                "Notes": str(getattr(door, "FA_TableNotes", "") or getattr(door, "Description", "") or ""),
            }
        )
    return build_table_data(CATEGORY_DOORS, records)


def validate_door_records(records, sketches, tolerance=None):
    return validate_records(CATEGORY_DOORS, records, geometry_records_from_sketches(sketches), tolerance=tolerance)


def apply_door_records(
    doc,
    target_container,
    records,
    sketches,
    walls,
    dry_run=True,
    tolerance=None,
    host_tolerance_mm=DEFAULT_HOST_TOLERANCE_MM,
):
    """Plan/apply door rows conservatively, protecting manual doors."""
    sketches = _unique_objects(sketches)
    walls = [wall for wall in _unique_objects(walls) if is_bim_wall(wall)]
    geometry = geometry_records_from_sketches(sketches)
    plan = plan_application(CATEGORY_DOORS, records, geometry, tolerance=tolerance)
    source_map = {str(item.Name): item for item in sketches}
    segment_map = {
        (str(source.Name), int(item["index"])): item
        for source in sketches
        for item in sketch_segments(source)
    }
    wall_records = [
        {"wall": wall, "segments": [item["segment"] for item in wall_source_segments(wall)]}
        for wall in walls
    ]
    wall_records = [item for item in wall_records if item["segments"]]
    actions = []
    for item in plan["plans"]:
        geom = item["geometry"]
        source = source_map.get(str(geom["SourceSketch"]))
        axis = segment_map.get((str(geom["SourceSketch"]), int(geom["GeometryIndex"])))
        if source is None or axis is None:
            actions.append(_skipped_action(item, "NO_MATCH", "Sketch destino no disponible"))
            continue
        selection = select_best_host(axis["segment"], wall_records, float(host_tolerance_mm))
        if selection["ambiguous"]:
            actions.append(_skipped_action(item, "AMBIGUO", "Muro anfitrion ambiguo"))
            continue
        match = selection["match"]
        if match is None:
            actions.append(_skipped_action(item, "NO_MATCH", "Sin muro anfitrion compatible"))
            continue
        try:
            values = _door_values(item["record"], geom)
        except Exception as exc:
            actions.append(_skipped_action(item, "NO_MATCH", str(exc)))
            continue
        corner_plan = resolve_door_corner_snap(match, wall_records)
        corner_conflict = ""
        if corner_plan.get("applied") or corner_plan.get("swing_resolved"):
            values, corner_conflict = _merge_corner_plan(values, corner_plan)
            if not corner_conflict:
                if corner_plan.get("applied"):
                    match = corner_plan["match"]
                values["corner_snap"] = corner_plan
            else:
                corner_plan = dict(corner_plan)
                corner_plan["applied"] = False
                corner_plan["reason"] = "tabla explicita conserva bisagra/apertura: %s" % corner_conflict
        existing = _find_generated_door(doc, source, int(axis["index"]))
        conflict = _find_manual_element_id_conflict(doc, values["element_id"], existing)
        if conflict is not None:
            actions.append(_skipped_action(item, "AMBIGUO", "ElementID ya pertenece a una puerta manual: %s" % conflict.Label))
            continue
        action = "KEEP" if existing is not None and _door_matches(existing, values, match, corner_plan) else ("REPLACE" if existing is not None else "CREATE")
        actions.append(
            {
                "row_index": item["row_index"],
                "element_id": values["element_id"],
                "status": item["status"],
                "action": action,
                "record": item["record"],
                "source": source,
                "axis": axis,
                "match": match,
                "values": values,
                "existing": existing,
                "corner_plan": corner_plan,
                "corner_conflict": corner_conflict,
            }
        )

    report = _json_report(plan, actions, dry_run=dry_run)
    if dry_run:
        return report
    executable = [item for item in actions if item["action"] in ("CREATE", "REPLACE")]
    if not executable:
        report["dry_run"] = False
        return report

    resolved_container = target_container or ensure_bim_structure(doc)["level"]
    transaction_open = False
    created = []
    try:
        doc.openTransaction("FA Aplicar tabla de puertas")
        transaction_open = True
        for item in executable:
            values = item["values"]
            if values["type"]["TypeSource"] == TYPE_SOURCE_DOUBLE:
                new = _create_double_from_plan(doc, resolved_container, item, values)
            else:
                new = create_native_door_from_axis_plan(
                    doc,
                    resolved_container,
                    item["source"],
                    item["axis"],
                    item["match"],
                    values["height"],
                    preset=values["type"]["Preset"],
                    opening_percent=values["opening"],
                    frame_mm=values["frame"],
                    offset_mm=values["offset"],
                    element_id=values["element_id"],
                    hinge_endpoint=values["hinge_endpoint"],
                    opening_side=values["opening_side"],
                    opens_inward=values["opens_inward"],
                )
            _apply_transfer_metadata(new, item["record"], item["source"], item["axis"], values, previous=item["existing"], match=item["match"])
            created.append((item, new))
        doc.recompute()
        for item, new in created:
            if getattr(new, "Base", None) is None or list(getattr(new, "Hosts", []) or []) != [item["match"]["wall"]]:
                raise RuntimeError("La nueva puerta no conservo Base/Hosts")
            subvolume = new.Proxy.getSubVolume(new, host=item["match"]["wall"])
            if subvolume is None or float(subvolume.Volume) <= 1.0:
                raise RuntimeError("La nueva puerta no produce un subvolumen valido")
        for item, _new in created:
            if item["existing"] is not None:
                _remove_generated_door(doc, item["existing"])
        for item, _new in created:
            item["match"]["wall"].touch()
        doc.recompute()
        doc.commitTransaction()
        transaction_open = False
    except Exception:
        if transaction_open:
            doc.abortTransaction()
        raise
    report = _json_report(plan, actions, dry_run=False)
    report["created_objects"] = [new.Name for _item, new in created]
    return report


def export_table_native(sheet, filename):
    sheet.exportFile(str(filename))
    return str(filename)


def import_table_native(doc, filename):
    sheet = ensure_door_table(doc)
    sheet.clearAll()
    sheet.importFile(str(filename))
    _tag_sheet(sheet)
    _ensure_table_group(doc, sheet)
    sheet.recompute()
    return sheet


def is_native_door(obj):
    if str(getattr(obj, "IfcType", "") or "") != "Door":
        return False
    proxy = getattr(obj, "Proxy", None)
    return str(getattr(proxy.__class__, "__module__", "") or "") == "ArchWindow"


def _door_values(record, geometry):
    resolved = resolve_door_type(
        record.get("DoorType"), record.get("TypeSource"), record.get("TypeRef"),
        record.get("Preset"), record.get("LeafCount"),
    )
    hinge = str(record.get("HingeEndpoint") or "AUTO").strip().upper()
    if resolved["LeafCount"] > 1:
        hinge = "BOTH"
    if hinge not in ("AUTO", "START", "END", "BOTH"):
        hinge = "AUTO"
    side = str(record.get("OpeningSide") or "AUTO").strip().upper()
    if side not in ("AUTO", "LEFT", "RIGHT", "IN", "OUT"):
        side = "AUTO"
    return {
        "element_id": str(record.get("ElementID") or "").strip(),
        "width": float(geometry["Length"]),
        "height": float(record.get("Height") if record.get("Height") is not None else 2100.0),
        "type": resolved,
        "hinge_endpoint": hinge,
        "opening_side": side,
        "opens_inward": record.get("OpensInward"),
        "opening": float(record.get("Opening") if record.get("Opening") is not None else 100.0),
        "frame": float(record.get("Frame") if record.get("Frame") is not None else 50.0),
        "offset": float(record.get("Offset") if record.get("Offset") is not None else 0.0),
    }


def _merge_corner_plan(values, corner_plan):
    """Apply automatic corner semantics only when the table does not contradict them."""
    result = dict(values)
    plan = dict(corner_plan or {})
    if not plan.get("applied") and not plan.get("swing_resolved"):
        return result, ""
    leaf_count = int(result.get("type", {}).get("LeafCount", 1) or 1)
    conflicts = []
    hinge = str(result.get("hinge_endpoint") or "AUTO").upper()
    plan_hinge = str(plan.get("hinge_endpoint") or "AUTO").upper()
    if leaf_count <= 1 and plan_hinge != "AUTO" and hinge not in ("AUTO", plan_hinge):
        conflicts.append("HingeEndpoint=%s" % hinge)
    side = str(result.get("opening_side") or "AUTO").upper()
    plan_side = str(plan.get("opening_side") or "AUTO").upper()
    if plan_side != "AUTO" and side not in ("AUTO", plan_side):
        conflicts.append("OpeningSide=%s" % side)
    inward = result.get("opens_inward")
    if plan.get("opens_inward") is True and inward is False:
        conflicts.append("OpensInward=False")
    if conflicts:
        return result, ", ".join(conflicts)
    if leaf_count <= 1 and hinge == "AUTO" and plan_hinge != "AUTO":
        result["hinge_endpoint"] = str(plan["hinge_endpoint"])
    if side == "AUTO" and plan_side != "AUTO":
        result["opening_side"] = str(plan["opening_side"])
    if inward is None and plan.get("opens_inward") is not None:
        result["opens_inward"] = True
    return result, ""


def _create_double_from_plan(doc, target_container, item, values):
    match = item["match"]
    first = match["projected_first"]
    second = match["projected_second"]
    center = ((first[0] + second[0]) * 0.5, (first[1] + second[1]) * 0.5)
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    angle = math.degrees(math.atan2(dy, dx))
    placement = FreeCAD.Placement(
        FreeCAD.Vector(float(center[0]), float(center[1]), float(match.get("wall_z", 0.0))),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), angle),
    )
    length = math.hypot(dx, dy) or 1.0
    normal = (-dy / length, dx / length, 0.0)
    if values["opening_side"] == "RIGHT":
        normal = (-normal[0], -normal[1], 0.0)
    params = normalized_parameters({"width_mm": values["width"], "height_mm": values["height"]})
    door, _profile = create_double_door_bim(
        doc,
        placement=placement,
        host=match["wall"],
        target_container=target_container,
        parameters=params,
        opening=values["opening"],
        label="Puerta doble BIM - %s" % values["element_id"],
        host_context={
            "normal": normal,
            "segment_index": int(match.get("reference_segment_index", -1)),
            "wall_width_mm": _quantity(match["wall"], "Width") or 0.0,
        },
    )
    if hasattr(door, "Normal") and values["opening_side"] in ("LEFT", "RIGHT"):
        door.Normal = FreeCAD.Vector(*normal)
    apply_door_corner_metadata(door, values.get("corner_snap"))
    return door


def _type_from_door(door):
    if is_special_fa_double_door(door):
        return {"DoorType": "DoubleDoor", "TypeSource": TYPE_SOURCE_DOUBLE, "TypeRef": DOUBLE_DOOR_SPEC_ID, "Preset": "Double leaf glazed Europa", "LeafCount": max(2, _property_int(door, "LeafCount") or 2)}
    preset = door_preset_name(door)
    door_type = str(getattr(door, "FA_DoorType", "") or preset or "Simple door")
    return {"DoorType": door_type, "TypeSource": TYPE_SOURCE_NATIVE, "TypeRef": preset, "Preset": preset, "LeafCount": max(1, _property_int(door, "LeafCount") or 1)}


def _door_matches(door, values, match, corner_plan=None):
    wall = match["wall"]
    if list(getattr(door, "Hosts", []) or []) != [wall]:
        return False
    if abs((_quantity(door, "Width") or -1) - values["width"]) > 0.01 or abs((_quantity(door, "Height") or -1) - values["height"]) > 0.01:
        return False
    if abs((_quantity(door, "Opening") or 0.0) - values["opening"]) > 0.01:
        return False
    current = _type_from_door(door)
    if current["TypeSource"] != values["type"]["TypeSource"] or current["TypeRef"] != values["type"]["TypeRef"]:
        return False
    hinge = str(getattr(door, "FA_HingeEndpoint", "AUTO") or "AUTO").upper()
    side = str(getattr(door, "FA_OpeningSide", "AUTO") or "AUTO").upper()
    if values["hinge_endpoint"] not in ("AUTO", "BOTH") and hinge != values["hinge_endpoint"]:
        return False
    if values["opening_side"] != "AUTO" and side != values["opening_side"]:
        return False
    if (
        values.get("type", {}).get("TypeSource") == TYPE_SOURCE_NATIVE
        and values.get("hinge_endpoint") in ("START", "END")
        and values.get("opening_side") in ("LEFT", "RIGHT")
    ):
        segment = tuple(match["projected_first"]) + tuple(match["projected_second"])
        hinge_point = match["projected_second"] if values["hinge_endpoint"] == "END" else match["projected_first"]
        expected_mode = resolve_door_native_mode(segment, hinge_point, values["opening_side"])
        if expected_mode.get("resolved") and native_door_opening_mode(door) != expected_mode["mode"]:
            return False
    expected_inward = values.get("opens_inward")
    if expected_inward is not None:
        current_inward = _optional_bool_property(door, "FA_OpensInward")
        if current_inward is None or bool(current_inward) != bool(expected_inward):
            return False
    plan = dict(corner_plan or {})
    expected_corner = bool(plan.get("applied"))
    current_corner = bool(getattr(door, "FA_CornerSnapped", False))
    if expected_corner != current_corner:
        return False
    if expected_corner:
        expected_side_wall = plan.get("side_wall")
        if expected_side_wall is not None:
            stored_side_wall = getattr(door, "FA_CornerWall", None)
            if stored_side_wall is not expected_side_wall and str(stored_side_wall or "") != str(
                getattr(expected_side_wall, "Name", "") or ""
            ):
                return False
        try:
            current_shift = float(getattr(door, "FA_CornerShift_mm", 0.0))
        except Exception:
            current_shift = 0.0
        if abs(current_shift - float(plan.get("shift_mm") or 0.0)) > 0.5:
            return False
        if values.get("hinge_endpoint") in ("START", "END"):
            hinge_point = getattr(door, "FA_HingePoint", None)
            expected_point = plan.get("hinge_point")
            if hinge_point is None or not expected_point:
                return False
            if math.hypot(float(hinge_point.x) - float(expected_point[0]), float(hinge_point.y) - float(expected_point[1])) > 0.5:
                return False
    return True


def _apply_transfer_metadata(door, record, source, axis, values, previous=None, match=None):
    if previous is not None:
        door.Label = previous.Label
        for name in ("Description", "Tag", "Material"):
            if hasattr(previous, name) and hasattr(door, name):
                try:
                    setattr(door, name, getattr(previous, name))
                except Exception:
                    pass
    element_id = values["element_id"]
    if element_id and hasattr(door, "Tag"):
        door.Tag = element_id
    set_prop(door, "App::PropertyString", "FA_ElementID", "FacilArquitectura", "Identificador transferible", element_id)
    set_prop(door, "App::PropertyLink", "FA_SourceSketch", "FacilArquitectura", "Sketch fuente", source)
    set_prop(door, "App::PropertyInteger", "FA_SourceGeometryIndex", "FacilArquitectura", "Indice geometrico fuente", int(axis["index"]))
    set_prop(door, "App::PropertyString", "FA_DoorType", "FacilArquitectura", "Tipo logico transferible", values["type"]["DoorType"])
    set_prop(door, "App::PropertyString", "FA_DoorTypeSource", "FacilArquitectura", "Mecanismo del tipo", values["type"]["TypeSource"])
    set_prop(door, "App::PropertyString", "FA_DoorTypeRef", "FacilArquitectura", "Referencia estable del tipo", values["type"]["TypeRef"])
    set_prop(door, "App::PropertyString", "FA_HingeEndpoint", "FacilArquitectura", "Extremo de bisagra transferible", values["hinge_endpoint"])
    if values["hinge_endpoint"] in ("START", "END"):
        if match is not None:
            point = match["projected_second"] if values["hinge_endpoint"] == "END" else match["projected_first"]
            hx, hy = point[0], point[1]
        else:
            geom = geometry_records_from_sketches([source])
            current = next((g for g in geom if int(g["GeometryIndex"]) == int(axis["index"])), None)
            if current is None:
                hx = hy = None
            elif values["hinge_endpoint"] == "END":
                hx, hy = current["SecondX"], current["SecondY"]
            else:
                hx, hy = current["FirstX"], current["FirstY"]
        if hx is not None and hy is not None:
            set_prop(door, "App::PropertyVector", "FA_HingePoint", "FacilArquitectura", "Punto global de bisagra", FreeCAD.Vector(float(hx), float(hy), float(getattr(door.Placement.Base, "z", 0.0))))
    apply_door_corner_metadata(door, values.get("corner_snap"))
    set_prop(door, "App::PropertyString", "FA_OpeningSide", "FacilArquitectura", "Lado de apertura respecto al eje", values["opening_side"])
    if values["opens_inward"] is not None:
        set_prop(door, "App::PropertyBool", "FA_OpensInward", "FacilArquitectura", "Abre hacia el recinto", bool(values["opens_inward"]))
    set_prop(door, "App::PropertyString", "FA_RoomKey", "FacilArquitectura", "Recinto descriptivo", str(record.get("RoomKey") or ""))
    set_prop(door, "App::PropertyString", "FA_LevelKey", "FacilArquitectura", "Nivel descriptivo", str(record.get("LevelKey") or ""))
    set_prop(door, "App::PropertyString", "FA_TableNotes", "FacilArquitectura", "Notas de tabla", str(record.get("Notes") or ""))
    set_prop(door, "App::PropertyInteger", "FA_ElementDataSchema", "FacilArquitectura", "Version de esquema", SCHEMA_VERSION)
    set_prop(door, "App::PropertyString", "FA_TableGeneratedBy", "FacilArquitectura", "Herramienta de tabla", TABLE_GENERATOR)


def _find_generated_door(doc, source, index):
    generators = {GENERATED_BY_DOORS, DOUBLE_DOOR_GENERATOR} | set(LEGACY_GENERATORS["door"])
    for obj in list(doc.Objects):
        if not is_native_door(obj):
            continue
        if getattr(obj, "FA_SourceSketch", None) is not source:
            continue
        if _property_int(obj, "FA_SourceGeometryIndex") != int(index):
            continue
        generated = str(getattr(obj, "FA_GeneratedBy", "") or "")
        table_generated = str(getattr(obj, "FA_TableGeneratedBy", "") or "")
        if generated in generators or table_generated == TABLE_GENERATOR:
            return obj
    return None


def _find_manual_element_id_conflict(doc, element_id, generated_match=None):
    key = str(element_id or "").strip()
    if not key:
        return None
    for obj in list(doc.Objects):
        if obj is generated_match or not is_native_door(obj):
            continue
        candidate = str(getattr(obj, "FA_ElementID", "") or getattr(obj, "Tag", "") or "").strip()
        if candidate != key:
            continue
        if str(getattr(obj, "FA_TableGeneratedBy", "") or "") != TABLE_GENERATOR:
            return obj
    return None


def _remove_generated_door(doc, door):
    base = getattr(door, "Base", None) or getattr(door, "Profile", None)
    try:
        door.Hosts = []
    except Exception:
        pass
    door_name = getattr(door, "Name", "")
    base_name = getattr(base, "Name", "") if base is not None else ""
    if door_name and doc.getObject(door_name) is not None:
        doc.removeObject(door_name)
    if base_name and doc.getObject(base_name) is not None:
        doc.removeObject(base_name)


def _geometry_for_door(door, source, geometry_index):
    if source is not None and geometry_index is not None:
        for item in geometry_records_from_sketches([source]):
            if int(item["GeometryIndex"]) == int(geometry_index):
                return item
    width = _quantity(door, "Width") or 0.0
    base = getattr(door, "Base", None)
    try:
        placement = base.getGlobalPlacement() if base is not None else door.getGlobalPlacement()
    except Exception:
        placement = base.Placement if base is not None else door.Placement
    first = placement.multVec(FreeCAD.Vector(0, 0, 0))
    second = placement.multVec(FreeCAD.Vector(width, 0, 0))
    return {
        "CenterX": (first.x + second.x) * 0.5,
        "CenterY": (first.y + second.y) * 0.5,
        "Length": width,
        "AngleDeg": math.degrees(math.atan2(second.y - first.y, second.x - first.x)) % 180.0,
        "FirstX": first.x,
        "FirstY": first.y,
        "SecondX": second.x,
        "SecondY": second.y,
    }


def _opening_side_from_normal(door, geometry):
    if not geometry or geometry.get("FirstX") is None:
        return "AUTO"
    dx = float(geometry["SecondX"] - geometry["FirstX"])
    dy = float(geometry["SecondY"] - geometry["FirstY"])
    length = math.hypot(dx, dy)
    normal = getattr(door, "Normal", None)
    if length <= 1e-9 or normal is None:
        return "AUTO"
    left = (-dy / length, dx / length)
    dot = float(normal.x) * left[0] + float(normal.y) * left[1]
    return "LEFT" if dot >= 0.0 else "RIGHT"


def _write_headers(sheet):
    for column, header, _field in COLUMNS:
        sheet.set(column + "1", header)
    sheet.setStyle("A1:AA1", "bold", "add")
    for column, _header, _field in COLUMNS:
        try:
            sheet.setColumnWidth(column, 125 if column in ("A", "B", "I", "K", "L", "W") else 88)
        except Exception:
            pass


def _tag_sheet(sheet):
    set_prop(sheet, "App::PropertyInteger", "FA_SchemaVersion", "FacilArquitectura", "Version del esquema", SCHEMA_VERSION)
    set_prop(sheet, "App::PropertyString", "FA_Category", "FacilArquitectura", "Categoria", CATEGORY_DOORS)
    set_prop(sheet, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", TABLE_GENERATOR)


def _ensure_table_group(doc, sheet):
    support_parent, _level = ensure_auxiliary_parent(doc, [sheet], legacy_key="tables")
    try:
        if sheet not in list(getattr(support_parent, "Group", []) or []):
            support_parent.addObject(sheet)
    except Exception:
        pass


def _last_used_row(sheet):
    try:
        cells = dict(sheet.getNonEmptyCells() or {})
        rows = [int("".join(ch for ch in address if ch.isdigit())) for address in cells if any(ch.isdigit() for ch in address)]
        if rows:
            return max(rows)
    except Exception:
        pass
    last, empty_run = 1, 0
    for row in range(2, 10002):
        if any(_cell_text(sheet, "%s%d" % (column, row)) for column, _header, _field in COLUMNS):
            last, empty_run = row, 0
        else:
            empty_run += 1
            if empty_run >= 25:
                break
    return last


def _cell_text(sheet, address):
    try:
        value = sheet.getContents(address)
    except Exception:
        try:
            value = sheet.get(address)
        except Exception:
            return ""
    text = str(value or "").strip()
    # Spreadsheet stores literal strings that could be parsed as expressions
    # with a leading apostrophe. ``getContents`` returns that escape marker;
    # it is not part of the user's ElementData value.
    return text[1:] if text.startswith("'") else text


def _format_cell_value(field, value):
    if field in ("CenterX", "CenterY", "Length", "AngleDeg", "Height", "HingePointX", "HingePointY", "Opening", "Frame", "Offset"):
        return ("%.6f" % float(value)).rstrip("0").rstrip(".")
    if field == "OpensInward":
        return "TRUE" if bool(value) else "FALSE"
    return str(value)


def _parse_number(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        try:
            return float(FreeCAD.Units.Quantity(text).Value)
        except Exception:
            return None


def _parse_int(value):
    number = _parse_number(value)
    return None if number is None else int(number)


def _parse_bool(value):
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in ("1", "true", "yes", "si", "sí"):
        return True
    if text in ("0", "false", "no"):
        return False
    return None


def _optional_bool_property(obj, name):
    if not hasattr(obj, name):
        return None
    try:
        return bool(getattr(obj, name))
    except Exception:
        return None


def _vector_xy(value):
    if value is None:
        return None, None
    try:
        return float(value.x), float(value.y)
    except Exception:
        return None, None


def _element_id(door, fallback_index):
    for name in ("FA_ElementID", "Tag"):
        value = str(getattr(door, name, "") or "").strip()
        if value:
            return value
    return "P-%03d" % int(fallback_index)


def _level_key(door):
    value = str(getattr(door, "FA_LevelKey", "") or getattr(door, "FA_TargetLevel", "") or "").strip()
    if value:
        return value
    for parent in list(getattr(door, "InList", []) or []):
        if str(getattr(parent, "IfcType", "") or "") == "Building Storey":
            return str(parent.Label)
    return ""


def _quantity(obj, name):
    if obj is None or not hasattr(obj, name):
        return None
    try:
        value = getattr(obj, name)
        return float(getattr(value, "Value", value))
    except Exception:
        return None


def _property_int(obj, name):
    try:
        return int(getattr(obj, name)) if hasattr(obj, name) else None
    except Exception:
        return None


def _unique_objects(objects):
    result, seen = [], set()
    for obj in objects or []:
        key = (str(getattr(getattr(obj, "Document", None), "Name", "")), str(getattr(obj, "Name", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(obj)
    return result


def _json_report(plan, actions, dry_run):
    serial_actions = []
    counts = {"CREATE": 0, "REPLACE": 0, "KEEP": 0, "SKIP": 0}
    for item in actions:
        action = item["action"]
        counts[action if action in counts else "SKIP"] += 1
        serial_actions.append(
            {
                "row_index": item["row_index"],
                "element_id": item.get("element_id", ""),
                "status": item["status"],
                "action": action,
                "reason": item.get("reason", ""),
                "source_sketch": getattr(item.get("source"), "Name", ""),
                "geometry_index": int(item.get("axis", {}).get("index", -1)) if item.get("axis") else None,
                "host": getattr(item.get("match", {}).get("wall"), "Name", "") if item.get("match") else "",
                "door_type": item.get("values", {}).get("type", {}).get("DoorType", ""),
                "corner_snapped": bool(item.get("corner_plan", {}).get("applied")),
                "corner_wall": str(item.get("corner_plan", {}).get("side_wall_label", "")),
                "corner_gap_before_mm": float(item.get("corner_plan", {}).get("snap_distance_mm", 0.0) or 0.0),
                "corner_conflict": str(item.get("corner_conflict", "")),
            }
        )
    return {
        "category": CATEGORY_DOORS,
        "dry_run": bool(dry_run),
        "validation": plan["validation"],
        "actions": serial_actions,
        "action_counts": counts,
        "skipped_validation_count": len(plan["skipped"]),
    }


def _skipped_action(item, status, reason):
    return {"row_index": item["row_index"], "element_id": item["record"].get("ElementID", ""), "status": status, "action": "SKIP", "reason": reason}
