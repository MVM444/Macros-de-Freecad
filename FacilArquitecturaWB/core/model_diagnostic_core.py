"""FA model diagnostic - independent analysis core.

Name: model_diagnostic_core.py
Purpose: analyze a JSON-compatible snapshot of a FreeCAD document and render a
human-readable diagnostic report without importing FreeCAD, FreeCADGui or Qt.
Main behavior: classify structural findings, especially hierarchy, invalid
states, repeated visual parents and FA stair relationships; produce deterministic
Markdown suitable for GPT/Codex feedback.
Future modifications: keep this module FreeCAD/GUI independent; add new checks as
pure functions over the snapshot schema and avoid mutating the input payload.
Version: 0.2.2
Date and time: 2026-09-15 15:20 America/Costa_Rica
FreeCAD target: 1.1.3 (snapshot consumer only).
"""

from __future__ import annotations

import json
from collections import defaultdict
from copy import deepcopy

SCHEMA = "FA_MODEL_DIAGNOSTIC/1"
SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2, "OK": 3}


def _text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _objects(snapshot):
    return list((snapshot or {}).get("objects", []) or [])


def _object_index(snapshot):
    return {str(obj.get("name") or ""): obj for obj in _objects(snapshot) if obj.get("name")}


def _relation_map(snapshot):
    """Return {(source_name, field): [target_name, ...]} from flat relation rows."""
    result = {}
    for row in list((snapshot or {}).get("relations", []) or []):
        source = _text(row.get("source"))
        field = _text(row.get("field"))
        targets = []
        for item in list(row.get("targets", []) or []):
            if isinstance(item, dict):
                name = _text(item.get("name"))
            else:
                name = _text(item)
            if name:
                targets.append(name)
        result[(source, field)] = targets
    return result


def _finding(severity, code, message, objects=None, data=None):
    return {
        "severity": str(severity),
        "code": str(code),
        "message": str(message),
        "objects": list(objects or []),
        "data": dict(data or {}),
    }


def _capture_errors(snapshot):
    findings = []
    for item in list((snapshot or {}).get("capture_errors", []) or []):
        findings.append(
            _finding(
                "ERROR",
                "CAPTURE_READ_ERROR",
                "La captura encontro un error de lectura: %s" % _text(item.get("message") or item),
                objects=[_text(item.get("object"))] if isinstance(item, dict) and item.get("object") else [],
            )
        )
    return findings


def _object_state_findings(snapshot):
    findings = []
    for obj in _objects(snapshot):
        states = [str(value) for value in list(obj.get("state", []) or [])]
        bad = [value for value in states if any(token in value.lower() for token in ("error", "invalid"))]
        if bad:
            findings.append(
                _finding(
                    "ERROR",
                    "OBJECT_STATE_ERROR",
                    "%s <%s> reporta estado %s."
                    % (_text(obj.get("label")) or _text(obj.get("name")), _text(obj.get("name")), ", ".join(bad)),
                    objects=[_text(obj.get("name"))],
                    data={"state": bad},
                )
            )
    return findings


def _tree_findings(snapshot):
    findings = []
    for cycle in list((snapshot or {}).get("tree_cycles", []) or []):
        path = list(cycle.get("path", []) or []) if isinstance(cycle, dict) else []
        findings.append(
            _finding(
                "ERROR",
                "TREE_CYCLE",
                "Se detecto un ciclo en la jerarquia visual%s."
                % (": " + " -> ".join(path) if path else ""),
                objects=path,
            )
        )
    for obj in _objects(snapshot):
        parents = list(obj.get("tree_parents", []) or [])
        if len(parents) > 1:
            findings.append(
                _finding(
                    "WARN",
                    "MULTIPLE_TREE_PARENTS",
                    "%s <%s> aparece reclamado por varios padres visuales: %s."
                    % (
                        _text(obj.get("label")) or _text(obj.get("name")),
                        _text(obj.get("name")),
                        ", ".join(parents),
                    ),
                    objects=[_text(obj.get("name"))] + parents,
                )
            )
    return findings


def _level_findings(snapshot, index):
    findings = []
    storeys = [obj for obj in _objects(snapshot) if _text(obj.get("ifc_type")).lower() == "building storey"]
    buildings = [obj for obj in _objects(snapshot) if _text(obj.get("ifc_type")).lower() == "building"]

    for storey in storeys:
        parents = list(storey.get("tree_parents", []) or [])
        building_parents = [name for name in parents if _text(index.get(name, {}).get("ifc_type")).lower() == "building"]
        if not building_parents:
            findings.append(
                _finding(
                    "WARN",
                    "STOREY_WITHOUT_BUILDING_PARENT",
                    "%s <%s> es Building Storey pero no tiene un Building como padre visual."
                    % (_text(storey.get("label")) or _text(storey.get("name")), _text(storey.get("name"))),
                    objects=[_text(storey.get("name"))],
                )
            )

    for building in buildings:
        name = _text(building.get("name"))
        child_storeys = [
            obj for obj in storeys if name in list(obj.get("tree_parents", []) or [])
        ]
        findings.append(
            _finding(
                "OK",
                "BUILDING_STOREY_COUNT",
                "%s <%s> contiene %d Level(s) BIM nativo(s)."
                % (_text(building.get("label")) or name, name, len(child_storeys)),
                objects=[name] + [_text(obj.get("name")) for obj in child_storeys],
                data={"count": len(child_storeys)},
            )
        )
    return findings


def _duplicate_label_findings(snapshot):
    groups = defaultdict(list)
    for obj in _objects(snapshot):
        label = _text(obj.get("label")).strip()
        type_id = _text(obj.get("type_id")).strip()
        if label:
            groups[(label, type_id)].append(_text(obj.get("name")))
    findings = []
    for (label, type_id), names in sorted(groups.items()):
        if len(names) <= 1:
            continue
        findings.append(
            _finding(
                "INFO",
                "DUPLICATE_VISIBLE_LABEL",
                "La etiqueta visible '%s' se repite %d veces para Type=%s. Puede ser intencional; revise si dificulta identificar objetos."
                % (label, len(names), type_id or "?"),
                objects=names,
                data={"label": label, "type_id": type_id, "count": len(names)},
            )
        )
    return findings


def _stair_findings(snapshot, index, relation_map):
    findings = []
    stair_groups = defaultdict(list)
    masters = []

    for obj in _objects(snapshot):
        name = _text(obj.get("name"))
        generated_by = _text((obj.get("properties") or {}).get("FA_GeneratedBy"))
        if not generated_by.startswith("FA_StairBetweenSlabs"):
            continue
        props = dict(obj.get("properties", {}) or {})
        lower = relation_map.get((name, "FA_LowerSlab"), [])
        upper = relation_map.get((name, "FA_UpperSlab"), [])
        if not lower and _text(props.get("FA_LowerSlabName")):
            lower = [_text(props.get("FA_LowerSlabName"))]
        if not upper and _text(props.get("FA_UpperSlabName")):
            upper = [_text(props.get("FA_UpperSlabName"))]
        if not lower or not upper:
            continue
        masters.append(obj)
        key = (lower[0], upper[0])
        stair_groups[key].append(name)

    for (lower, upper), names in sorted(stair_groups.items()):
        if len(names) > 1:
            findings.append(
                _finding(
                    "WARN",
                    "DUPLICATE_STAIRS_SAME_SLABS",
                    "Se detectaron %d escaleras FA entre las mismas losas (%s -> %s): %s."
                    % (len(names), lower, upper, ", ".join(names)),
                    objects=[lower, upper] + names,
                    data={"lower_slab": lower, "upper_slab": upper, "count": len(names)},
                )
            )

    for master in masters:
        name = _text(master.get("name"))
        props = dict(master.get("properties", {}) or {})
        lower_levels = relation_map.get((name, "FA_LowerLevel"), [])
        upper_levels = relation_map.get((name, "FA_UpperLevel"), [])
        if not lower_levels and _text(props.get("FA_LowerLevelName")):
            lower_levels = [_text(props.get("FA_LowerLevelName"))]
        if not upper_levels and _text(props.get("FA_UpperLevelName")):
            upper_levels = [_text(props.get("FA_UpperLevelName"))]
        if not lower_levels or not upper_levels:
            findings.append(
                _finding(
                    "WARN",
                    "STAIR_LEVEL_CONTEXT_INCOMPLETE",
                    "%s <%s> no conserva ambos enlaces FA_LowerLevel/FA_UpperLevel."
                    % (_text(master.get("label")) or name, name),
                    objects=[name] + lower_levels + upper_levels,
                )
            )
        elif lower_levels[0] == upper_levels[0]:
            findings.append(
                _finding(
                    "WARN",
                    "STAIR_LEVELS_ARE_SAME",
                    "%s <%s> enlaza el mismo Level como inferior y superior: %s."
                    % (_text(master.get("label")) or name, name, lower_levels[0]),
                    objects=[name, lower_levels[0]],
                )
            )
        else:
            findings.append(
                _finding(
                    "OK",
                    "STAIR_CONNECTS_TWO_LEVELS",
                    "%s <%s> conserva contexto entre %s y %s."
                    % (_text(master.get("label")) or name, name, lower_levels[0], upper_levels[0]),
                    objects=[name, lower_levels[0], upper_levels[0]],
                )
            )

        source_names = relation_map.get((name, "FA_SourceWire"), [])
        for source_name in source_names:
            source = index.get(source_name, {})
            if source and bool(source.get("is_root")):
                findings.append(
                    _finding(
                        "WARN",
                        "STAIR_SOURCE_IS_ROOT",
                        "El Wire/Sketch fuente %s de %s permanece como raiz del documento, fuera de la jerarquia BIM."
                        % (source_name, name),
                        objects=[name, source_name],
                    )
                )

        slab_status = _text(props.get("FA_SlabOpeningStatus"))
        if slab_status:
            opening_targets = relation_map.get((name, "FA_SlabOpening"), [])
            if not opening_targets and _text(props.get("FA_SlabOpeningName")):
                opening_targets = [_text(props.get("FA_SlabOpeningName"))]
            upper_targets = relation_map.get((name, "FA_UpperSlab"), [])
            if not upper_targets and _text(props.get("FA_UpperSlabName")):
                upper_targets = [_text(props.get("FA_UpperSlabName"))]
            upper_subtractions = relation_map.get((upper_targets[0], "Subtractions"), []) if upper_targets else []
            if slab_status == "native_subtraction_applied" and opening_targets and opening_targets[0] in upper_subtractions:
                findings.append(
                    _finding(
                        "OK",
                        "STAIR_SLAB_OPENING_APPLIED",
                        "%s <%s> conserva un buque nativo dentro de Subtractions de la losa superior."
                        % (_text(master.get("label")) or name, name),
                        objects=[name] + upper_targets + opening_targets,
                    )
                )
            else:
                findings.append(
                    _finding(
                        "WARN",
                        "STAIR_SLAB_OPENING_INCOMPLETE",
                        "%s <%s> declara hueco de losa '%s' pero no se pudo confirmar la Subtraction nativa."
                        % (_text(master.get("label")) or name, name, slab_status),
                        objects=[name] + upper_targets + opening_targets,
                    )
                )

        ceiling_status = _text(props.get("FA_CeilingExclusionStatus"))
        if ceiling_status:
            ceiling_objects = relation_map.get((name, "FA_CeilingObjects"), [])
            if not ceiling_objects and _text(props.get("FA_CeilingObjectNamesJSON")):
                try:
                    ceiling_objects = [
                        _text(value)
                        for value in json.loads(_text(props.get("FA_CeilingObjectNamesJSON")))
                        if _text(value)
                    ]
                except Exception:
                    ceiling_objects = []
            ceiling_plan = relation_map.get((name, "FA_CeilingExclusionPlan"), [])
            if ceiling_status == "generator_exclusion_applied" and ceiling_objects and ceiling_plan:
                findings.append(
                    _finding(
                        "OK",
                        "STAIR_CEILING_EXCLUSION_APPLIED",
                        "%s <%s> conserva exclusion real de cielorraso y su PLAN documental."
                        % (_text(master.get("label")) or name, name),
                        objects=[name] + ceiling_objects + ceiling_plan,
                    )
                )
            else:
                findings.append(
                    _finding(
                        "WARN",
                        "STAIR_CEILING_EXCLUSION_INCOMPLETE",
                        "%s <%s> declara exclusion de cielorraso '%s' pero faltan relaciones de aplicacion/documentacion."
                        % (_text(master.get("label")) or name, name, ceiling_status),
                        objects=[name] + ceiling_objects + ceiling_plan,
                    )
                )

    return findings


def analyze_snapshot(snapshot):
    """Return a deterministic diagnostic payload from one JSON-compatible snapshot."""
    snapshot = deepcopy(snapshot or {})
    index = _object_index(snapshot)
    relation_map = _relation_map(snapshot)

    findings = []
    findings.extend(_capture_errors(snapshot))
    findings.extend(_object_state_findings(snapshot))
    findings.extend(_tree_findings(snapshot))
    findings.extend(_level_findings(snapshot, index))
    findings.extend(_stair_findings(snapshot, index, relation_map))
    findings.extend(_duplicate_label_findings(snapshot))

    findings.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(item.get("severity"), 99),
            _text(item.get("code")),
            _text(item.get("message")),
        )
    )
    counts = {severity: 0 for severity in ("ERROR", "WARN", "INFO", "OK")}
    for item in findings:
        severity = str(item.get("severity") or "INFO")
        counts[severity] = counts.get(severity, 0) + 1

    return {
        "schema": SCHEMA,
        "findings": findings,
        "counts": counts,
        "object_count": len(_objects(snapshot)),
        "root_count": len(list(snapshot.get("roots", []) or [])),
    }


def _node_line(node, depth):
    return "%s- %s | Name=%s | Type=%s | visible=%s" % (
        "  " * int(depth),
        _text(node.get("label")) or _text(node.get("name")),
        _text(node.get("name")),
        _text(node.get("type_id")),
        node.get("visibility"),
    )


def render_tree_lines(roots):
    lines = []

    def walk(node, depth=0):
        lines.append(_node_line(node, depth))
        if node.get("loop"):
            lines.append("  " * (depth + 1) + "- [CICLO DETECTADO]")
            return
        for child in list(node.get("children", []) or []):
            walk(child, depth + 1)

    for root in list(roots or []):
        walk(root, 0)
        lines.append("")
    return lines


def _relation_target_text(target):
    if isinstance(target, dict):
        name = _text(target.get("name"))
        label = _text(target.get("label")) or name
        return "%s<%s>" % (label, name) if label and label != name else (name or label or "?")
    return _text(target)


def render_markdown(snapshot, diagnostic):
    """Render one self-contained Markdown report for human/GPT review."""
    meta = dict((snapshot or {}).get("meta", {}) or {})
    document = dict((snapshot or {}).get("document", {}) or {})
    counts = dict((diagnostic or {}).get("counts", {}) or {})

    lines = [
        "# FA Informe diagnostico",
        "",
        "Fecha: %s  " % (_text(meta.get("generated_at")) or "no registrada"),
        "FreeCAD: %s  " % (_text(meta.get("freecad_version")) or "no registrado"),
        "Facil Arquitectura: %s / build %s  " % (
            _text(meta.get("workbench_version")) or "?",
            _text(meta.get("workbench_build")) or "?",
        ),
        "Documento: %s (`%s`)  " % (
            _text(document.get("label")) or _text(document.get("name")),
            _text(document.get("name")),
        ),
        "Archivo: %s  " % (_text(document.get("file")) or "(no guardado)"),
        "Alcance: %s" % (_text(meta.get("scope")) or "documento_completo"),
        "Objetivo: %s" % (_text(meta.get("objective")) or "diagnostico general"),
        "",
        "## Resumen",
        "",
        "- Objetos analizados: **%d**" % int((diagnostic or {}).get("object_count", 0)),
        "- Raices visuales: **%d**" % int((diagnostic or {}).get("root_count", 0)),
        "- Errores: **%d**" % int(counts.get("ERROR", 0)),
        "- Advertencias: **%d**" % int(counts.get("WARN", 0)),
        "- Informativos: **%d**" % int(counts.get("INFO", 0)),
        "- Comprobaciones correctas: **%d**" % int(counts.get("OK", 0)),
        "",
        "## Hallazgos",
        "",
    ]

    findings = list((diagnostic or {}).get("findings", []) or [])
    if not findings:
        lines.append("- [OK] No se generaron hallazgos con las reglas actuales.")
    else:
        for item in findings:
            lines.append(
                "- [%s] `%s` — %s"
                % (_text(item.get("severity")), _text(item.get("code")), _text(item.get("message")))
            )

    lines.extend(["", "## Arbol del modelo", "", "```text"])
    lines.extend(render_tree_lines((snapshot or {}).get("roots", [])))
    lines.extend(["```", "", "## Relaciones internas", ""])

    relation_rows = list((snapshot or {}).get("relations", []) or [])
    if not relation_rows:
        lines.append("No se capturaron relaciones internas.")
    else:
        by_source = defaultdict(list)
        for row in relation_rows:
            by_source[_text(row.get("source"))].append(row)
        for source in sorted(by_source):
            obj = _object_index(snapshot).get(source, {})
            title = _text(obj.get("label")) or source
            parts = []
            for row in sorted(by_source[source], key=lambda item: _text(item.get("field"))):
                targets = ", ".join(_relation_target_text(target) for target in list(row.get("targets", []) or []))
                if targets:
                    parts.append("%s=[%s]" % (_text(row.get("field")), targets))
            if parts:
                lines.append("- %s | Name=%s | %s" % (title, source, " | ".join(parts)))

    lines.extend(
        [
            "",
            "## Uso para retroalimentacion",
            "",
            "Este informe fue generado en modo de solo lectura. Puede adjuntarse directamente a GPT/Codex para revisar la estructura del documento sin depender de una sesion MCP de lectura. MCP sigue siendo necesario para ejecutar cambios, consultar datos no incluidos o verificar comportamiento dinamico en FreeCAD.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_text(snapshot, diagnostic):
    """Render a plain-text compatibility report for legacy macro consumers."""
    markdown = render_markdown(snapshot, diagnostic)
    lines = []
    in_fence = False
    for raw in markdown.splitlines():
        line = raw
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            while line.startswith("#"):
                line = line[1:]
            line = line.lstrip()
            line = line.replace("**", "").replace("`", "")
        lines.append(line)
    return "\n".join(lines).rstrip() + "\n"
