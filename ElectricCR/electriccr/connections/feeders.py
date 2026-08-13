# -*- coding: utf-8 -*-
"""Motor general de alimentadores ElectricCR.

Conecta circuitos, tableros secundarios, desconectores e interruptores con su
tablero asignado. Sustituye la geometria especializada de TP, TCOM y HVAC.
Las guias son opcionales: GUIADO cuando se suministran y DIRECTO en cualquier
otro caso. Compatible con FreeCAD 1.1.3. Creado: 2026-08-08 18:01 CST.
Advertencia: TP/TCOM son datos; no agregar ramas geometricas por su nombre.
"""

import json
import re

import FreeCAD as App

from . import assignments, panels, ports, routing


TAG = "[ElectricCR][FEEDER]"
GENERATED_BY = "ElectricCR.Connections.Feeders.v1"
LEGACY_GENERATORS = {
    "Conectar_Circuitos_TP_a_Cara_Superior_Tablero",
    "Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero",
    "ConectarTablerosCaraSuperior",
}
DEFAULT_CONFIG = {
    "route_z": 3400.0,
    "lane_spacing": 50.0,
    "approach_clearance": 300.0,
    "bend_radius": 100.0,
    "port_stub": 80.0,
    "diameter": 22.2,
}


def _log(message):
    App.Console.PrintMessage("{} {}\n".format(TAG, message))


def _warn(message):
    App.Console.PrintWarning("{} {}\n".format(TAG, message))


def _ensure(obj, ptype, name, group, description):
    if name not in set(getattr(obj, "PropertiesList", []) or []):
        obj.addProperty(ptype, name, group, description)


def _unique_name(doc, prefix):
    if doc.getObject(prefix) is None:
        return prefix
    index = 1
    while doc.getObject("{}_{:03d}".format(prefix, index)) is not None:
        index += 1
    return "{}_{:03d}".format(prefix, index)


def _natural_key(value):
    parts = re.split(r"(\d+)", panels.text(value))
    return tuple((0, int(part)) if part.isdigit() else (1, panels.normalized(part)) for part in parts)


def _is_octagonal_box(obj):
    if obj is None or panels.is_group(obj) or panels.is_library_object(obj):
        return False
    if panels.text(getattr(obj, "Tipo", "")) == "EMT_Octagon_Box":
        return True
    probe = panels.normalized("{} {}".format(getattr(obj, "Name", ""), getattr(obj, "Label", "")))
    return "PuertosJSON" in set(getattr(obj, "PropertiesList", []) or []) and "octogonal" in probe


def _walk_group(group, seen=None):
    seen = set() if seen is None else seen
    if group is None or group.Name in seen:
        return []
    seen.add(group.Name)
    result = []
    for child in list(getattr(group, "Group", []) or []):
        result.append(child)
        if panels.is_group(child):
            result.extend(_walk_group(child, seen))
    return result


def _box_mentions_circuit(box, cid):
    try:
        values = json.loads(panels.text(getattr(box, "CircuitosJSON", "[]")))
    except Exception:
        return False
    return isinstance(values, list) and any(panels.text(value).split("|")[0].strip() == cid for value in values)


def boxes_for_circuit(doc, circuit_group, cid=None):
    cid = cid or assignments.circuit_id(circuit_group)
    result = []
    seen = set()
    try:
        assigned = list(getattr(circuit_group, "CajasOctogonalesAsignadas", []) or [])
    except Exception:
        assigned = []
    for obj in assigned + _walk_group(circuit_group):
        if _is_octagonal_box(obj) and obj.Name not in seen:
            seen.add(obj.Name)
            result.append(obj)
    if cid:
        for obj in list(doc.Objects):
            if _is_octagonal_box(obj) and obj.Name not in seen and _box_mentions_circuit(obj, cid):
                seen.add(obj.Name)
                result.append(obj)
    return result


def candidate_circuit_groups(doc, prefix=None):
    wanted = panels.text(prefix).strip().upper()
    result = []
    seen_ids = set()
    for obj in list(doc.Objects):
        if not panels.is_group(obj):
            continue
        cid = assignments.circuit_id(obj)
        if not cid or (wanted and assignments.circuit_prefix(cid) != wanted):
            continue
        boxes = boxes_for_circuit(doc, obj, cid)
        if not boxes:
            continue
        # Cuando hay duplicados logicos, conservar el grupo con mas cajas.
        prior = next((item for item in result if item[0] == cid), None)
        if prior is None:
            result.append((cid, obj, boxes))
            seen_ids.add(cid)
        elif len(boxes) > len(prior[2]):
            result[result.index(prior)] = (cid, obj, boxes)
    result.sort(key=lambda item: _natural_key(item[0]))
    return result


def _route_group(doc, kind):
    root = doc.getObject("ElectricCR_Conexiones")
    if root is None:
        root = doc.addObject("App::DocumentObjectGroup", "ElectricCR_Conexiones")
        root.Label = "Conexiones ElectricCR"
    name = "ElectricCR_{}".format(kind)
    group = doc.getObject(name)
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", name)
        group.Label = kind
    if group not in list(getattr(root, "Group", []) or []):
        root.addObject(group)
    return group


def _move_to_route_group(route, group):
    for parent in list(getattr(route, "InList", []) or []):
        if parent is group or not panels.is_group(parent):
            continue
        try:
            parent.removeObject(route)
        except Exception:
            pass
    if route not in list(getattr(group, "Group", []) or []):
        group.addObject(route)


def _cleanup_empty_legacy_groups(doc):
    for group in list(doc.Objects):
        if not panels.is_group(group) or list(getattr(group, "Group", []) or []):
            continue
        generated = panels.text(getattr(group, "GeneradoPor", ""))
        label = panels.normalized(getattr(group, "Label", ""))
        if generated in LEGACY_GENERATORS and ("alimentador" in label or "ramal" in label):
            try:
                doc.removeObject(group.Name)
            except Exception:
                pass


def _same_panel(route, panel):
    for name in ("Panel", "TableroDestino"):
        try:
            linked = getattr(route, name)
            if linked is panel:
                return True
        except Exception:
            pass
    return False


def _find_circuit_route(doc, cid, panel):
    matches = []
    for obj in list(doc.Objects):
        if panels.is_group(obj) or panels.text(getattr(obj, "CircuitoID", "")) != cid:
            continue
        generated = panels.text(getattr(obj, "GeneradoPor", ""))
        if generated != GENERATED_BY and generated not in LEGACY_GENERATORS:
            continue
        if _same_panel(obj, panel) or generated in LEGACY_GENERATORS:
            matches.append(obj)
    matches.sort(key=lambda obj: (0 if panels.text(getattr(obj, "GeneradoPor", "")) == GENERATED_BY else 1, obj.Name))
    return matches[0] if matches else None


def _existing_source_box(route, boxes):
    try:
        box = getattr(route, "CajaOrigen", None)
        if box in boxes:
            return box
    except Exception:
        pass
    return None


def _source_box(group, boxes, panel, existing=None):
    for name in ("CajaAlimentadora", "CajaOrigen", "FeederBox"):
        try:
            value = getattr(group, name)
            if value in boxes:
                return value
        except Exception:
            pass
    preserved = _existing_source_box(existing, boxes) if existing is not None else None
    if preserved is not None:
        return preserved
    target = panels.top_center(panel)
    return min(boxes, key=lambda box: box.Shape.BoundBox.Center.distanceToPoint(target))


def _configuration(cfg):
    result = dict(DEFAULT_CONFIG)
    result.update(dict(cfg or {}))
    for key in DEFAULT_CONFIG:
        result[key] = float(result[key])
    return result


def _style(route, color=(1.0, 0.38, 0.05)):
    try:
        route.ViewObject.LineColor = color
        route.ViewObject.PointColor = color
        route.ViewObject.ShapeColor = color
        route.ViewObject.LineWidth = 3.5
    except Exception:
        pass


def _write_common(route, points, cid, panel, face_index, slot_index, slot_count, mode, guide):
    definitions = (
        ("App::PropertyString", "Tipo", "ElectricCR", "Tipo logico"),
        ("App::PropertyString", "GeneradoPor", "ElectricCR", "Motor generador"),
        ("App::PropertyString", "CircuitoID", "ElectricCR", "Circuito"),
        ("App::PropertyLink", "Panel", "Vinculos", "Tablero del circuito"),
        ("App::PropertyLink", "TableroDestino", "Vinculos", "Alias de tablero destino"),
        ("App::PropertyVector", "PuntoOrigen", "Geometria", "Punto inicial"),
        ("App::PropertyVector", "PuntoDestino", "Geometria", "Punto final"),
        ("App::PropertyVectorList", "Points", "Geometria", "Eje de ruta"),
        ("App::PropertyString", "CaraTablero", "Tablero", "Cara usada"),
        ("App::PropertyInteger", "FaceIndexTablero", "Tablero", "Indice de cara"),
        ("App::PropertyInteger", "SlotTablero", "Tablero", "Ranura uno basada"),
        ("App::PropertyInteger", "CantidadSlotsTablero", "Tablero", "Cantidad de llegadas"),
        ("App::PropertyString", "ModoRuteo", "Ruta", "GUIADO o DIRECTO"),
        ("App::PropertyLink", "RutaGuia", "Ruta", "Guia seleccionada"),
        ("App::PropertyString", "RutaJSON", "Ruta", "Puntos mundiales"),
        ("App::PropertyString", "EstadoConexion", "Ruta", "Estado"),
        ("App::PropertyFloat", "Longitud_m", "Calculo", "Longitud en metros"),
    )
    for definition in definitions:
        _ensure(route, *definition)
    route.GeneradoPor = GENERATED_BY
    route.CircuitoID = cid
    route.Panel = panel
    route.TableroDestino = panel
    route.PuntoOrigen = App.Vector(points[0])
    route.PuntoDestino = App.Vector(points[-1])
    route.Points = [App.Vector(point) for point in points]
    route.CaraTablero = "Top"
    route.FaceIndexTablero = int(face_index)
    route.SlotTablero = int(slot_index) + 1
    route.CantidadSlotsTablero = int(slot_count)
    route.ModoRuteo = mode
    route.RutaGuia = guide
    route.RutaJSON = json.dumps([[p.x, p.y, p.z] for p in points], separators=(",", ":"))
    route.EstadoConexion = "Conectado"
    route.Longitud_m = float(route.Shape.Length) / 1000.0


def _write_circuit_route(doc, job, points, mode, guide, cfg):
    route = job["existing"]
    created = route is None
    if route is None:
        token = re.sub(r"[^0-9A-Za-z_]+", "_", job["circuit_id"])
        route = doc.addObject("Part::Feature", _unique_name(doc, "Alimentador_" + token))
    group = _route_group(doc, "Alimentadores")
    _move_to_route_group(route, group)
    route.Shape = routing.rounded_wire(points, cfg["bend_radius"])
    route.Label = "Alimentador {} -> {}".format(job["circuit_id"], panels.panel_code(job["panel"]))
    _write_common(
        route,
        points,
        job["circuit_id"],
        job["panel"],
        job["face_index"],
        job["slot_index"],
        job["slot_count"],
        mode,
        guide,
    )
    _ensure(route, "App::PropertyLink", "Circuit", "Vinculos", "Objeto o grupo de circuito")
    _ensure(route, "App::PropertyLink", "CajaOrigen", "Vinculos", "Caja octagonal de origen")
    _ensure(route, "App::PropertyLink", "Origen", "Vinculos", "Origen generico")
    _ensure(route, "App::PropertyString", "PuertoOrigen", "Puertos", "Puerto de caja")
    _ensure(route, "App::PropertyFloat", "AlturaRuta", "Ruta", "Cota de distribucion")
    route.Tipo = "AlimentadorCircuito"
    route.Circuit = job["circuit_group"]
    route.CajaOrigen = job["source_box"]
    route.Origen = job["source_box"]
    route.PuertoOrigen = job["source_port"]["name"]
    route.AlturaRuta = cfg["route_z"]
    _style(route)
    return route, created


def _selected_group_set(circuit_groups):
    return {obj.Name for obj in list(circuit_groups or []) if panels.is_group(obj)}


def connect_circuit_feeders(doc, circuit_groups=None, forced_panel=None, panel_code=None, guides=None, cfg=None, circuit_prefix=None):
    """Crea o actualiza alimentadores de grupos de circuito.

    ``guides`` solo se usa cuando se entrega explicitamente. Si ninguna guia
    resulta aplicable, el mismo trabajo continua en modo DIRECTO.
    """
    cfg = _configuration(cfg)
    if forced_panel is None and panel_code:
        forced_panel = panels.find_panel_by_token(doc, panel_code)
    selected_names = _selected_group_set(circuit_groups)
    all_candidates = candidate_circuit_groups(doc, prefix=circuit_prefix)
    candidates = [item for item in all_candidates if not selected_names or item[1].Name in selected_names]
    requested_ids = {panels.text(value).strip() for value in list(cfg.get("circuit_ids", []) or []) if panels.text(value).strip()}
    if requested_ids:
        candidates = [item for item in candidates if item[0] in requested_ids]
    if not candidates:
        return {"routes": [], "created": 0, "updated": 0, "skipped": [], "errors": ["No se encontraron circuitos con cajas"]}

    jobs = []
    skipped = []
    for cid, group, boxes in candidates:
        panel, source = assignments.resolve_circuit_panel(doc, group, forced_panel=forced_panel)
        if panel is None:
            skipped.append("{}: sin tablero asignado".format(cid))
            continue
        existing = _find_circuit_route(doc, cid, panel)
        source_box = _source_box(group, boxes, panel, existing=existing)
        jobs.append({
            "circuit_id": cid,
            "circuit_group": group,
            "boxes": boxes,
            "panel": panel,
            "assignment_source": source,
            "existing": existing,
            "source_box": source_box,
        })
    if not jobs:
        return {"routes": [], "created": 0, "updated": 0, "skipped": skipped, "errors": []}

    by_panel = {}
    for job in jobs:
        by_panel.setdefault(job["panel"].Name, []).append(job)

    all_boxes = list({box.Name: box for job in jobs for box in job["boxes"]}.values())
    occupied = ports.occupied_port_map(doc, all_boxes, ignored_generators={GENERATED_BY} | LEGACY_GENERATORS)
    for panel_name, panel_jobs in by_panel.items():
        panel = panel_jobs[0]["panel"]
        all_keys = []
        for cid, group, _boxes in all_candidates:
            candidate_panel, _source = assignments.resolve_circuit_panel(doc, group, forced_panel=forced_panel)
            if candidate_panel is panel:
                all_keys.append(cid)
        all_keys = sorted(set(all_keys), key=_natural_key)
        slot_map = {cid: index for index, cid in enumerate(all_keys)}
        distributed = panels.distributed_top_points(panel, len(all_keys))
        for job in panel_jobs:
            slot_index = slot_map[job["circuit_id"]]
            destination, face_index = distributed[slot_index]
            chosen = ports.choose_port(job["source_box"], destination, occupied.get(job["source_box"].Name, set()))
            occupied.setdefault(job["source_box"].Name, set()).add(chosen["name"])
            job.update({
                "slot_index": slot_index,
                "slot_count": len(all_keys),
                "destination": destination,
                "face_index": face_index,
                "source_port": chosen,
            })

    created = updated = 0
    routes = []
    errors = []
    doc.openTransaction("ElectricCR: conectar alimentadores generales")
    try:
        for panel_name, panel_jobs in by_panel.items():
            panel_jobs.sort(key=lambda item: _natural_key(item["circuit_id"]))
            for rank, job in enumerate(panel_jobs):
                source = job["source_port"]["point"]
                direction = job["source_port"]["dir"]
                guided = routing.guided_route(
                    source,
                    direction,
                    job["destination"],
                    list(guides or []),
                    job["slot_index"],
                    job["slot_count"],
                    cfg,
                ) if guides else None
                if guided is not None:
                    points, guide = guided
                    mode = "GUIADO"
                    side = "GUIA"
                else:
                    points, side = routing.direct_circuit_route(
                        source,
                        direction,
                        job["destination"],
                        job["panel"].Shape.BoundBox,
                        job["slot_index"],
                        cfg,
                    )
                    guide = None
                    mode = "DIRECTO"
                route, was_created = _write_circuit_route(doc, job, points, mode, guide, cfg)
                routes.append(route)
                created += int(was_created)
                updated += int(not was_created)
                _log(
                    "Circuito={} Origen={} Destino={} Modo={} Guia={} Puerto={} Cara=Top/Face{} Slot={}/{} Lado={} Resultado={}".format(
                        job["circuit_id"],
                        job["source_box"].Name,
                        panels.panel_code(job["panel"]),
                        mode,
                        getattr(guide, "Name", "-") if guide is not None else "-",
                        job["source_port"]["name"],
                        job["face_index"],
                        job["slot_index"] + 1,
                        job["slot_count"],
                        side,
                        "CREADO" if was_created else "ACTUALIZADO",
                    )
                )
        _cleanup_empty_legacy_groups(doc)
        doc.recompute()
        doc.commitTransaction()
    except Exception as exc:
        try:
            doc.abortTransaction()
        except Exception:
            pass
        errors.append(panels.text(exc))
        _warn("Fallo general: {}".format(exc))
        return {"routes": [], "created": 0, "updated": 0, "skipped": skipped, "errors": errors}
    return {"routes": routes, "created": created, "updated": updated, "skipped": skipped, "errors": errors}


def _equipment_destination(route):
    for name in ("Destino", "EquipoDestino", "TableroDestino"):
        try:
            value = getattr(route, name)
            if value is not None:
                return value
        except Exception:
            pass
    return None


def _find_equipment_route(doc, equipment):
    for obj in list(doc.Objects):
        generated = panels.text(getattr(obj, "GeneradoPor", ""))
        if generated != GENERATED_BY and generated not in LEGACY_GENERATORS:
            continue
        if _equipment_destination(obj) is equipment:
            return obj
    return None


def _write_equipment_route(doc, record, points, face_index, slot_index, slot_count, mode, guide, cfg):
    equipment = record["object"]
    panel = record["panel"]
    route = _find_equipment_route(doc, equipment)
    created = route is None
    if route is None:
        token = re.sub(r"[^0-9A-Za-z_]+", "_", panels.panel_code(panel) + "_" + panels.panel_code(equipment))
        route = doc.addObject("Part::Feature", _unique_name(doc, "Alimentador_Equipo_" + token))
    group = _route_group(doc, "Alimentadores")
    _move_to_route_group(route, group)
    route.Shape = routing.rounded_wire(points, cfg["bend_radius"])
    route.Label = "Alimentador {} -> {} ({})".format(panels.panel_code(panel), panels.panel_code(equipment), record["circuit_id"])
    _write_common(route, points, record["circuit_id"], panel, face_index, slot_index, slot_count, mode, guide)
    for definition in (
        ("App::PropertyLink", "Origen", "Vinculos", "Tablero aguas arriba"),
        ("App::PropertyLink", "Destino", "Vinculos", "Equipo aguas abajo"),
        ("App::PropertyLink", "TableroOrigen", "Vinculos", "Alias de tablero origen"),
        ("App::PropertyLink", "EquipoDestino", "Vinculos", "Equipo alimentado"),
    ):
        _ensure(route, *definition)
    route.Tipo = "AlimentadorEquipo"
    route.Origen = panel
    route.Destino = equipment
    route.TableroOrigen = panel
    route.EquipoDestino = equipment
    # Compatibilidad: en este tipo de alimentador TableroDestino historicamente
    # almacenaba el equipo o tablero aguas abajo.
    route.TableroDestino = equipment
    _style(route, color=(1.0, 0.45, 0.05))
    return route, created


def connect_equipment_feeders(doc, records, guides=None, cfg=None):
    cfg = _configuration(cfg)
    valid = [record for record in list(records or []) if record.get("panel") is not None and record.get("circuit_id")]
    skipped = []
    for record in list(records or []):
        name = getattr(record.get("object"), "Name", "-")
        if record.get("panel") is None:
            skipped.append("{}: sin tablero asignado".format(name))
        elif not record.get("circuit_id"):
            skipped.append("{}: sin circuito asignado".format(name))
    by_panel = {}
    for record in valid:
        by_panel.setdefault(record["panel"].Name, []).append(record)
    routes = []
    created = updated = 0
    doc.openTransaction("ElectricCR: conectar equipos a tableros")
    try:
        for panel_name, panel_records in by_panel.items():
            panel_records.sort(key=lambda record: (_natural_key(record["circuit_id"]), _natural_key(getattr(record["object"], "Label", ""))))
            panel = panel_records[0]["panel"]
            distributed = panels.distributed_top_points(panel, len(panel_records))
            for index, record in enumerate(panel_records):
                source, face_index = distributed[index]
                destination = panels.top_center(record["object"])
                direction = ports.normalize_xy(destination - source)
                guided = routing.guided_route(source, direction, destination, list(guides or []), index, len(panel_records), cfg) if guides else None
                if guided is not None:
                    points, guide = guided
                    mode = "GUIADO"
                else:
                    points = routing.direct_equipment_route(source, destination, index, len(panel_records), cfg)
                    guide = None
                    mode = "DIRECTO"
                route, was_created = _write_equipment_route(
                    doc, record, points, face_index, index, len(panel_records), mode, guide, cfg
                )
                routes.append(route)
                created += int(was_created)
                updated += int(not was_created)
                _log(
                    "Circuito={} Origen={} Destino={} Modo={} Guia={} Puerto=Top Face={} Slot={}/{} Resultado={}".format(
                        record["circuit_id"],
                        panels.panel_code(panel),
                        getattr(record["object"], "Name", "-"),
                        mode,
                        getattr(guide, "Name", "-") if guide is not None else "-",
                        face_index,
                        index + 1,
                        len(panel_records),
                        "CREADO" if was_created else "ACTUALIZADO",
                    )
                )
        _cleanup_empty_legacy_groups(doc)
        doc.recompute()
        doc.commitTransaction()
    except Exception as exc:
        try:
            doc.abortTransaction()
        except Exception:
            pass
        _warn("Fallo general de equipos: {}".format(exc))
        return {"routes": [], "created": 0, "updated": 0, "skipped": skipped, "errors": [panels.text(exc)]}
    return {"routes": routes, "created": created, "updated": updated, "skipped": skipped, "errors": []}
