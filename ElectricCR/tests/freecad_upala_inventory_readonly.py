"""Read-only inventory of the controlled Upala source document."""

from __future__ import annotations

import json
import sys

import FreeCAD as App


def _text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _properties(obj):
    return set(getattr(obj, "PropertiesList", []) or [])


def _link_name(obj, name):
    value = getattr(obj, name, None) if name in _properties(obj) else None
    return _text(getattr(value, "Name", ""))


def _placement(obj):
    value = obj.Placement
    return [
        round(float(value.Base.x), 6),
        round(float(value.Base.y), 6),
        round(float(value.Base.z), 6),
        [round(float(item), 12) for item in value.Rotation.Q],
    ]


def inspect(path):
    doc = App.openDocument(path)
    try:
        devices = []
        doors = []
        spaces = []
        named_rectangle006 = []
        for obj in list(doc.Objects):
            props = _properties(obj)
            tipo = _text(getattr(obj, "Tipo", "")) if "Tipo" in props else ""
            key = _text(getattr(obj, "KeyRegistro", "")) if "KeyRegistro" in props else ""
            if obj.TypeId == "App::Link" and (
                tipo in ("Toma", "Apagador")
                or key in ("Tomacorriente_120V", "Apagador_Simple")
            ):
                devices.append({
                    "name": obj.Name,
                    "label": _text(obj.Label),
                    "tipo": tipo,
                    "key": key,
                    "contract": _text(getattr(obj, "RepresentationContract", "")),
                    "master": _text(getattr(getattr(obj, "LinkedObject", None), "Name", "")),
                    "door": _link_name(obj, "PuertaOrigen"),
                    "source_element": _link_name(obj, "ElementoOrigen"),
                    "wall": _link_name(obj, "MuroReferencia") or _link_name(obj, "ECR_SourceWall"),
                    "area": _link_name(obj, "AreaRecinto"),
                    "space": _link_name(obj, "Space"),
                    "height": float(getattr(obj, "AlturaRel", 0.0)),
                    "placement": _placement(obj),
                    "door_key": _text(getattr(obj, "ECR_DoorKey", "")),
                    "generated_by": _text(getattr(obj, "ECR_GeneradoPor", "")),
                    "room": _text(getattr(obj, "Recinto", "")),
                })

            ifc = _text(getattr(obj, "IfcType", "")).strip().lower()
            proxy_type = _text(getattr(getattr(obj, "Proxy", None), "Type", "")).strip().lower()
            if obj.TypeId == "Arch::Door" or ifc in ("door", "opening element"):
                doors.append({
                    "name": obj.Name,
                    "label": _text(obj.Label),
                    "type_id": obj.TypeId,
                    "ifc": ifc,
                    "base": _link_name(obj, "Base"),
                    "target_room": _link_name(obj, "FA_TargetRoom"),
                    "target_room_name": _text(getattr(obj, "FA_TargetRoomName", "")),
                    "width": float(getattr(getattr(obj, "Width", 0.0), "Value", getattr(obj, "Width", 0.0)) or 0.0),
                })
            if ifc.replace(" ", "") == "space" or proxy_type == "space":
                spaces.append({"name": obj.Name, "label": _text(obj.Label), "ifc": ifc})
            if obj.Name == "Rectangle006" or _text(obj.Label) == "Rectangle006":
                row = {
                    "name": obj.Name,
                    "label": _text(obj.Label),
                    "type_id": obj.TypeId,
                    "ifc": ifc,
                    "proxy": proxy_type,
                    "placement": _placement(obj),
                    "properties": sorted(props),
                }
                try:
                    box = obj.Shape.BoundBox
                    row["shape"] = {
                        "volume": round(float(obj.Shape.Volume), 6),
                        "bound_box": [round(float(value), 6) for value in (
                            box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax
                        )],
                    }
                except Exception as exc:
                    row["shape_error"] = _text(exc)
                named_rectangle006.append(row)

        contracts = {}
        for item in devices:
            key = item["contract"] or "<missing>"
            contracts[key] = contracts.get(key, 0) + 1
        result = {
            "freecad_version": ".".join(App.Version()[:3]),
            "document": doc.Name,
            "label": _text(doc.Label),
            "file": _text(doc.FileName),
            "object_count": len(doc.Objects),
            "outlet_count": len([item for item in devices if item["tipo"] == "Toma"]),
            "switch_count": len([item for item in devices if item["tipo"] == "Apagador"]),
            "contracts": contracts,
            "doors": doors,
            "spaces": spaces,
            "rectangle006": named_rectangle006,
            "switch_rectangle006": [
                item for item in devices
                if item["label"].strip().casefold() == "apagador - rectangle006"
                or item["door"] == "Rectangle006"
                or item["area"] == "Rectangle006"
            ],
        }
        print("ECR_UPALA_INVENTORY " + json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    inspect(sys.argv[1])
