"""X3D exporter helpers for Game Engine Export WB.

Descripcion rapida: exporta via FreeCADGui y aplica conversion fija de ejes.
Fecha y hora: 2026-03-11 17:50 UTC.
Instrucciones clave:
- Mantener logs con prefijo [GAMEEXPORT].
- Aplicar siempre mm->m (0.001) y rotacion -90 en X para pasar Z-up a Y-up.
- Soportar salida X3D comprimida (gzip) sin romper decode UTF-8.
"""

from __future__ import annotations

import gzip
import math
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import xml.etree.ElementTree as ET


LOG_PREFIX = "[GAMEEXPORT] "
SCALE_VECTOR = "0.001 0.001 0.001"
ROTATION_VECTOR = "1 0 0 -1.57079632679"
TRANSFORM_DEF = "FreeCAD_mm_to_m"
X3D_DOCTYPE = '<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 3.2//EN" "http://www.web3d.org/specifications/x3d-3.2.dtd">'
DEFAULT_NAV_SPEED = 2.0
DEFAULT_EYE_HEIGHT_MM = 1600.0


def export_to_x3d(
    objects: Iterable[object],
    output_path: Path,
    gamestart_meta: Optional[Dict[str, object]] = None,
    lighting_cfg: Optional[Dict[str, object]] = None,
) -> Path:
    """Export selected objects to X3D and run postprocessing."""
    FreeCAD = __import__("FreeCAD")
    FreeCADGui = __import__("FreeCADGui")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    object_list = [obj for obj in objects if obj is not None]
    if not object_list:
        raise ValueError("No objects provided for export")

    diag = diagnose_export_candidates(object_list, log=True)
    exportable = diag["exportable"]
    skipped = diag["skipped"]

    if not exportable:
        raise ValueError("No exportable geometry found in selection")

    FreeCAD.Console.PrintMessage(
        LOG_PREFIX + f"Exporting {len(exportable)} objects to {out_path}\n"
    )
    FreeCADGui.export(exportable, str(out_path))
    decorate_x3d(out_path, gamestart_meta, lighting_cfg)
    return out_path


def diagnose_export_candidates(
    objects: Iterable[object], log: bool = False, max_rows: int = 25
) -> Dict[str, object]:
    """Return exportability diagnostics for the provided objects."""
    object_list = [obj for obj in objects if obj is not None]
    exportable, skipped = _split_exportables(object_list)
    if log and skipped:
        _log_skipped_objects(skipped, max_rows=max_rows)
    return {
        "total": len(object_list),
        "exportable": exportable,
        "skipped": skipped,
    }


def decorate_x3d(
    path: Path,
    gamestart_meta: Optional[Dict[str, object]] = None,
    lighting_cfg: Optional[Dict[str, object]] = None,
) -> None:
    """Apply mandatory axis conversion and keep output format (plain/gzip)."""
    FreeCAD = __import__("FreeCAD")

    file_path = Path(path)
    if not file_path.exists():
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"decorate_x3d skipped, file missing: {file_path}\n")
        return

    target_gzip = file_path.suffix.lower() == ".x3dz"
    xml_text, was_gzip = _read_x3d_text(file_path)
    if xml_text is None:
        # Fallback: if FreeCAD emitted gzip into .x3d, always convert to plain XML bytes.
        if was_gzip and not target_gzip:
            _force_gzip_to_plain(file_path)
        return

    doctype_line = _extract_doctype(xml_text)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"decorate_x3d parse failed: {exc}\n")
        if was_gzip and not target_gzip:
            _write_x3d_text(file_path, xml_text, False)
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "Wrote plain .x3d after parse warning to avoid invalid-character load errors.\n"
            )
        return

    namespace = _detect_namespace(root.tag)

    def q(tag: str) -> str:
        return f"{{{namespace}}}{tag}" if namespace else tag

    scene = root.find(q("Scene"))
    if scene is None:
        # Fallback in case of unusual root nesting.
        for node in root.iter():
            if _local_name(node.tag) == "Scene":
                scene = node
                break
    if scene is None:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + "decorate_x3d skipped: Scene node not found\n")
        if was_gzip and not target_gzip:
            _write_x3d_text(file_path, xml_text, False)
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "Wrote plain .x3d (no Scene found) to avoid invalid-character load errors.\n"
            )
        return

    navigation_cfg = _normalize_navigation_cfg(lighting_cfg)
    _ensure_background(scene, q)
    _ensure_navigation(scene, q, navigation_cfg)
    _apply_mm_to_m_axis_transform(scene, q)
    _insert_viewpoint(scene, q, gamestart_meta, navigation_cfg)

    if gamestart_meta or lighting_cfg:
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Decoration note: GameStart/lights metadata received; axis conversion applied.\n"
        )

    xml_out = _serialize_xml(root, doctype_line)

    if was_gzip and not target_gzip:
        FreeCAD.Console.PrintWarning(
            LOG_PREFIX + "Input payload is gzip but extension is .x3d; writing plain XML to keep parser compatibility.\n"
        )
    elif (not was_gzip) and target_gzip:
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Target extension .x3dz detected; writing gzip payload.\n")

    _write_x3d_text(file_path, xml_out, target_gzip)
    FreeCAD.Console.PrintMessage(LOG_PREFIX + "Applied axis fix (mm->m + -90X) successfully\n")


def _apply_mm_to_m_axis_transform(scene, q) -> None:
    """Wrap scene geometry into a canonical transform for engine coordinates."""
    preserved = {q("Background"), q("NavigationInfo"), q("Viewpoint")}

    transform = None
    for child in list(scene):
        if child.tag == q("Transform") and child.attrib.get("DEF") == TRANSFORM_DEF:
            transform = child
            break

    if transform is None:
        transform = ET.Element(q("Transform"))
    else:
        scene.remove(transform)

    transform.attrib["DEF"] = TRANSFORM_DEF
    transform.attrib["scale"] = SCALE_VECTOR
    transform.attrib["rotation"] = ROTATION_VECTOR

    for existing in list(transform):
        transform.remove(existing)

    geometry_children = []
    for child in list(scene):
        if child.tag in preserved:
            continue
        scene.remove(child)
        geometry_children.append(child)

    for child in geometry_children:
        transform.append(child)

    # Place transform after preserved config nodes.
    scene.append(transform)


def _normalize_navigation_cfg(lighting_cfg: Optional[Dict[str, object]]) -> Dict[str, float]:
    nav = {}
    if isinstance(lighting_cfg, dict):
        candidate = lighting_cfg.get("navigation")
        if isinstance(candidate, dict):
            nav = candidate
    speed = float(nav.get("speed", DEFAULT_NAV_SPEED))
    eye_height_mm = float(nav.get("eye_height_mm", DEFAULT_EYE_HEIGHT_MM))
    speed = max(0.1, min(10000.0, speed))
    eye_height_mm = max(100.0, min(5000.0, eye_height_mm))
    return {"speed": speed, "eye_height_mm": eye_height_mm}


def _ensure_background(scene, q) -> None:
    if any(child.tag == q("Background") for child in list(scene)):
        return
    scene.insert(0, ET.Element(q("Background"), {"skyColor": "0.05 0.08 0.15"}))


def _ensure_navigation(scene, q, nav_cfg: Dict[str, float]) -> None:
    eye_height_m = nav_cfg["eye_height_mm"] * 0.001
    attrs = {
        "DEF": "GameExport_Navigation",
        "avatarSize": f"0.25 {eye_height_m:.3f} 0.75",
        "speed": f"{nav_cfg['speed']:.3f}",
        "headlight": "false",
        "type": '"WALK" "ANY"',
    }

    existing = None
    for child in list(scene):
        if child.tag == q("NavigationInfo"):
            existing = child
            break
    if existing is None:
        insert_index = 1 if scene and scene[0].tag == q("Background") else 0
        scene.insert(insert_index, ET.Element(q("NavigationInfo"), attrs))
    else:
        existing.attrib.update(attrs)


def _insert_viewpoint(scene, q, meta: Optional[Dict[str, object]], nav_cfg: Dict[str, float]) -> None:
    FreeCAD = __import__("FreeCAD")

    eye_height_mm = float(nav_cfg.get("eye_height_mm", DEFAULT_EYE_HEIGHT_MM))
    position_mm = (0.0, -6000.0, 0.0)
    orientation = (0.0, 0.0, 1.0, 0.0)
    description = "GameStart"
    fov_rad = math.radians(60.0)

    if isinstance(meta, dict):
        if isinstance(meta.get("position_mm"), (list, tuple)) and len(meta.get("position_mm")) == 3:
            p = meta["position_mm"]
            position_mm = (float(p[0]), float(p[1]), float(p[2]))
        if isinstance(meta.get("orientation"), (list, tuple)) and len(meta.get("orientation")) == 4:
            o = meta["orientation"]
            orientation = (float(o[0]), float(o[1]), float(o[2]), float(o[3]))
        description = str(meta.get("description", description))
        fov_rad = float(meta.get("fov_rad", fov_rad))
        if "height_offset_mm" in meta:
            try:
                eye_height_mm = float(meta["height_offset_mm"])
            except Exception:
                pass

    pos_vec = FreeCAD.Vector(position_mm[0], position_mm[1], position_mm[2] + eye_height_mm)
    transform_rot = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), -90.0)
    pos_rot = transform_rot.multVec(pos_vec)
    position_m = (pos_rot.x * 0.001, pos_rot.y * 0.001, pos_rot.z * 0.001)

    axis_vec = FreeCAD.Vector(orientation[0], orientation[1], orientation[2])
    angle_rad = float(orientation[3])
    if axis_vec.Length == 0.0 or abs(angle_rad) < 1e-9:
        view_rot = FreeCAD.Rotation()
    else:
        view_rot = FreeCAD.Rotation(axis_vec, math.degrees(angle_rad))
    final_rot = transform_rot.multiply(view_rot)
    axis = final_rot.Axis
    if axis.Length == 0.0:
        axis = FreeCAD.Vector(0, 1, 0)
    else:
        axis.normalize()
    final_angle_rad = math.radians(final_rot.Angle)

    attrs = {
        "DEF": "GameExport_Viewpoint",
        "description": description,
        "position": f"{position_m[0]:.6f} {position_m[1]:.6f} {position_m[2]:.6f}",
        "orientation": f"{axis.x:.6f} {axis.y:.6f} {axis.z:.6f} {final_angle_rad:.6f}",
        "fieldOfView": f"{fov_rad:.6f}",
        "jump": "true",
    }

    for child in list(scene):
        if child.tag == q("Viewpoint") and child.attrib.get("DEF") == "GameExport_Viewpoint":
            scene.remove(child)

    insert_index = 0
    for idx, child in enumerate(scene):
        if child.tag in {q("Background"), q("NavigationInfo")}:
            insert_index = idx + 1
    scene.insert(insert_index, ET.Element(q("Viewpoint"), attrs))


def _read_x3d_text(path: Path) -> tuple[Optional[str], bool]:
    FreeCAD = __import__("FreeCAD")
    try:
        raw = path.read_bytes()
    except Exception as exc:  # pragma: no cover - IO guard
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"read failed: {exc}\n")
        return None, False

    is_gzip = len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B
    payload = raw
    if is_gzip:
        try:
            payload = gzip.decompress(raw)
            FreeCAD.Console.PrintMessage(LOG_PREFIX + "Compressed X3D detected; applying fix\n")
        except Exception as exc:
            FreeCAD.Console.PrintWarning(LOG_PREFIX + f"gzip decompress failed: {exc}\n")
            return None, True

    try:
        return payload.decode("utf-8"), is_gzip
    except UnicodeDecodeError as exc:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"UTF-8 decode failed: {exc}\n")
        return None, is_gzip


def _write_x3d_text(path: Path, text: str, as_gzip: bool) -> None:
    payload = text.encode("utf-8")
    if as_gzip:
        payload = gzip.compress(payload)
    path.write_bytes(payload)


def _force_gzip_to_plain(path: Path) -> None:
    FreeCAD = __import__("FreeCAD")
    try:
        raw = path.read_bytes()
        if len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B:
            decompressed = gzip.decompress(raw)
            path.write_bytes(decompressed)
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "Forced gzip->plain conversion for .x3d to avoid invalid-character load errors.\n"
            )
    except Exception as exc:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"force gzip->plain failed: {exc}\n")


def _serialize_xml(root: ET.Element, doctype_line: str) -> str:
    buf = BytesIO()
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)
    text = buf.getvalue().decode("utf-8")

    if doctype_line and doctype_line not in text:
        lines = text.splitlines()
        if lines and lines[0].startswith("<?xml"):
            lines.insert(1, doctype_line)
        else:
            lines.insert(0, doctype_line)
        text = "\n".join(lines) + "\n"
    return text


def _extract_doctype(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<!DOCTYPE"):
            # FreeCAD sometimes emits XHTML doctype; normalize to X3D for compatibility.
            return X3D_DOCTYPE
    return X3D_DOCTYPE


def _detect_namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[0][1:]
    return ""


def _local_name(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _split_exportables(objects: Iterable[object]) -> Tuple[List[object], List[Tuple[str, str, str]]]:
    exportable: List[object] = []
    skipped: List[Tuple[str, str, str]] = []
    for obj in objects:
        ok, reason = _is_exportable_object(obj)
        if ok:
            exportable.append(obj)
            continue
        label = getattr(obj, "Label", "") or getattr(obj, "Name", "Unknown")
        type_id = getattr(obj, "TypeId", "UnknownType")
        skipped.append((label, type_id, reason))
    return exportable, skipped


def _log_skipped_objects(skipped: List[Tuple[str, str, str]], max_rows: int = 25) -> None:
    FreeCAD = __import__("FreeCAD")
    FreeCAD.Console.PrintWarning(
        LOG_PREFIX + f"Skipping {len(skipped)} non-exportable objects (showing up to {max_rows})\n"
    )
    for label, type_id, reason in skipped[:max_rows]:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"SKIP: {label} [{type_id}] -> {reason}\n")
    if len(skipped) > max_rows:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + f"... and {len(skipped) - max_rows} more skipped\n")


def _is_exportable_object(obj: object) -> Tuple[bool, str]:
    type_id = str(getattr(obj, "TypeId", "") or "")

    non_geo_prefixes = (
        "App::DocumentObjectGroup",
        "App::Origin",
        "App::GeoFeatureGroupExtension",
        "Spreadsheet::",
        "TechDraw::",
        "Drawing::",
        "Path::",
        "Sketcher::SketchObject",
    )
    if any(type_id.startswith(prefix) for prefix in non_geo_prefixes):
        return False, "non-geometry helper/container"

    if hasattr(obj, "Shape"):
        try:
            shape = getattr(obj, "Shape")
            if shape is not None and hasattr(shape, "isNull") and not shape.isNull():
                return True, ""
        except Exception:
            pass

    if hasattr(obj, "Mesh"):
        try:
            mesh = getattr(obj, "Mesh")
            facets = int(getattr(mesh, "CountFacets", 0))
            if facets > 0:
                return True, ""
        except Exception:
            pass

    if hasattr(obj, "Points"):
        try:
            pts = getattr(obj, "Points")
            count = int(getattr(pts, "CountPoints", 0))
            if count > 0:
                return True, ""
        except Exception:
            pass

    if hasattr(obj, "Group") and not (hasattr(obj, "Shape") or hasattr(obj, "Mesh")):
        return False, "group/container without exportable geometry"

    if type_id:
        return False, "unsupported or empty geometry for X3D export"
    return False, "unknown object type"


__all__: List[str] = ["export_to_x3d", "decorate_x3d", "diagnose_export_candidates"]
