"""HVAC validation helpers for model consistency checks."""

import FreeCAD as App

from . import hvac_condensing
from . import hvac_equipment
from . import hvac_ports
from . import hvac_project
from . import hvac_route
from . import hvac_space

LOG_PREFIX = "[MEP-HVAC][Validate] "


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _to_float(value, default=0.0):
    try:
        if hasattr(value, "Value"):
            return float(value.Value)
        return float(value)
    except Exception:
        return float(default)


def _obj_name(obj):
    if obj is None:
        return "(None)"
    return str(getattr(obj, "Name", "") or "(SinNombre)")


def _refresh_document_state(doc):
    project = hvac_project.get_or_create_project(doc)
    if project is not None:
        hvac_project.recalculate_project(project)

    hvac_ports.sanitize_all_ports(doc)

    for space in hvac_space.find_spaces(doc):
        if project is not None and "Project" in space.PropertiesList and getattr(space, "Project", None) is None:
            space.Project = project
        hvac_space.calculate_space_load(space, project=project)

    for equipment in hvac_equipment.find_equipments(doc):
        hvac_equipment.update_equipment_ports(equipment)
        hvac_equipment.update_equipment_coverage(equipment)

    for condenser in hvac_condensing.find_condensers(doc):
        hvac_condensing.recalculate_condenser(condenser)

    hvac_route.update_all_routes(doc)


def _coverage_pct_for_space(space_obj, equipments):
    load = _to_float(getattr(space_obj, "CoolingLoadBTU", 0.0), 0.0)
    if load <= 0.0:
        return 0.0
    capacity = 0.0
    for equipment in equipments:
        if getattr(equipment, "Space", None) == space_obj:
            capacity += _to_float(getattr(equipment, "CapacityBTU", 0.0), 0.0)
    return round((capacity / load) * 100.0, 2)


def validate_document(doc=None, recalc_first=True):
    """Validate HVAC consistency and return report dict."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo para validar")
        return {
            "ok": False,
            "errors": 1,
            "warnings": 0,
            "infos": 0,
            "issues": [{"severity": "ERROR", "message": "No hay documento activo"}],
        }

    if recalc_first:
        _refresh_document_state(doc)

    issues = []

    def add_issue(severity, message, obj=None):
        text = "{0} :: {1}".format(_obj_name(obj), message) if obj is not None else message
        issues.append({"severity": severity, "message": text, "object": _obj_name(obj)})
        log("{0}: {1}".format(severity, text))

    spaces = hvac_space.find_spaces(doc)
    equipments = hvac_equipment.find_equipments(doc)
    condensers = hvac_condensing.find_condensers(doc)
    routes = hvac_route.find_routes(doc)
    ports = hvac_ports.find_ports(doc)

    if not spaces:
        add_issue("WARNING", "No se encontraron recintos HVAC")

    for space in spaces:
        load = _to_float(getattr(space, "CoolingLoadBTU", 0.0), 0.0)
        if load <= 0.0:
            add_issue("ERROR", "Carga de recinto no valida (<= 0 BTU/h)", space)
            continue

        coverage = _coverage_pct_for_space(space, equipments)
        if coverage < 90.0:
            add_issue("WARNING", "Cobertura de recinto baja ({0}%)".format(round(coverage, 1)), space)
        elif coverage > 140.0:
            add_issue("WARNING", "Cobertura de recinto alta ({0}%)".format(round(coverage, 1)), space)

    for equipment in equipments:
        if getattr(equipment, "Space", None) is None:
            add_issue("WARNING", "Evaporadora sin recinto asociado", equipment)
        capacity = _to_float(getattr(equipment, "CapacityBTU", 0.0), 0.0)
        if capacity <= 0.0:
            add_issue("ERROR", "Evaporadora con capacidad no valida (<= 0 BTU/h)", equipment)

    for condenser in condensers:
        units = list(getattr(condenser, "ConnectedUnits", []) or [])
        capacity = _to_float(getattr(condenser, "CapacityBTU", 0.0), 0.0)
        coverage = _to_float(getattr(condenser, "CoveragePct", 0.0), 0.0)
        if capacity <= 0.0:
            add_issue("ERROR", "Condensadora con capacidad no valida (<= 0 BTU/h)", condenser)
        if not units and not bool(getattr(condenser, "AutoCollect", True)):
            add_issue("WARNING", "Condensadora sin evaporadoras asignadas y AutoCollect desactivado", condenser)
        if units and coverage < 100.0:
            add_issue("WARNING", "Condensadora insuficiente ({0}%)".format(round(coverage, 1)), condenser)

    for route in routes:
        start_port = getattr(route, "StartPort", None)
        end_port = getattr(route, "EndPort", None)
        length = _to_float(getattr(route, "Length", 0.0), 0.0)
        if start_port is None or end_port is None:
            add_issue("ERROR", "Ruta sin puertos de inicio/fin", route)
            continue
        if not hvac_ports.validate_port_pair(start_port, end_port):
            add_issue("ERROR", "Ruta con puertos incompatibles", route)
        if length <= 0.0:
            add_issue("WARNING", "Ruta con longitud no valida (<= 0 m)", route)

    for port in ports:
        other_name = str(getattr(port, "ConnectedToName", "") or "")
        if not other_name:
            continue
        target = hvac_ports.get_connected_port(port)
        if target is None:
            add_issue("ERROR", "Puerto conectado a objeto inexistente: {0}".format(other_name), port)
            continue
        if not hvac_ports.validate_port_pair(port, target):
            add_issue("ERROR", "Puerto conectado a tipo incompatible", port)

    errors = len([issue for issue in issues if issue["severity"] == "ERROR"])
    warnings = len([issue for issue in issues if issue["severity"] == "WARNING"])
    infos = len([issue for issue in issues if issue["severity"] == "INFO"])
    ok = errors == 0

    log(
        "Resumen validacion -> errores={0}, advertencias={1}, info={2}".format(
            errors,
            warnings,
            infos,
        )
    )

    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "issues": issues,
    }
