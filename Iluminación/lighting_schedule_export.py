# -*- coding: utf-8 -*-

import importlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import FreeCAD as App


TAG = "[ILUM_SHEET]"
CALC_GROUP_LABEL = "Hojas de Calculo"
ROOM_SHEET_NAME = "Tabla_Iluminacion"
ROOM_SHEET_LABEL = "Tabla Iluminacion"
CIRCUIT_SHEET_NAME = "Tabla_Iluminacion_Circuitos"
CIRCUIT_SHEET_LABEL = "Tabla Iluminacion Circuitos"
DETAIL_SHEET_NAME = "Detalle_Iluminacion"
DETAIL_SHEET_LABEL = "Detalle Iluminacion"

ROOT_GROUP_ALIASES = {"electrico", "electric", "electricidad", "electrical"}
ILUM_GROUP_ALIASES = {"iluminacion", "iluminacion electrica", "lighting"}
ILUM_CONTAINER_ALIASES = ILUM_GROUP_ALIASES | {
    "circuitos de iluminacion",
    "circuitos iluminacion",
    "lighting circuits",
}
GENERIC_PATH_LABELS = {
    "electric",
    "electrico",
    "electricidad",
    "electrical",
    "iluminacion",
    "iluminacion electrica",
    "lighting",
    "circuitos",
    "circuitos de iluminacion",
    "circuitos iluminacion",
    "lighting circuits",
    "recintos",
    "areas",
    "area",
    "luminarias",
    "luminarias importadas",
    "luminarias_importadas",
    "luminarias link masters",
    "apagadores",
    "huerfanas",
    "csv sketch import",
    "csv_sketch_import",
    "puntos csv por tipo",
    "referencias csv",
}
LUMINARIA_TEXT_TOKENS = (
    "luminaria",
    "lampara",
    "lamp",
    "panel led",
    "panelled",
    "cascada",
    "60x60",
    "hermetica",
)
IGNORE_TOKENS = {
    "",
    "-",
    "_",
    "na",
    "n/a",
    "none",
    "null",
    "sin",
    "sin_dato",
    "sin_datos",
    "sin_info",
}
CIRCUIT_PROPS = (
    "CircuitoID",
    "Circuito",
    "CircuitID",
    "Circuit",
    "CircuitName",
    "CircuitoNombre",
)
AREA_PROPS = (
    "Recinto",
    "Area",
    "AreaID",
    "AreaNombre",
    "Habitacion",
    "Local",
    "Zona",
    "Espacio",
    "Ambiente",
)
SWITCH_PROPS = (
    "ApagadorID",
    "Apagador",
    "SwitchID",
    "Switch",
    "InterruptorID",
    "Interruptor",
    "ControlID",
    "Control",
)
PANEL_PROPS = ("Panel", "PanelID", "PanelName", "Tablero", "TableroID", "TableroNombre")
POWER_PROPS = (
    "Power",
    "Potencia",
    "W",
    "Watts",
    "PowerVA",
    "PotenciaVA",
    "VA",
    "VA_each",
    "VA_direct",
    "PotenciaInstalada",
)
LUMEN_PROPS = (
    "Lumens",
    "Lumen",
    "Lm",
    "FlujoLuminoso",
    "Flujo",
    "LuminousFlux",
    "FluxLm",
)
HEIGHT_PROPS = ("AlturaRel", "Altura", "Height", "Elevation", "Elevacion", "Z")
TYPE_PROPS = ("TipoLuminaria", "KeyRegistro", "Tipo", "TipoLogico", "Categoria")

FALLBACK_CATALOG = {
    "luminaria60x60": {"power_w": 40.0, "lumens": 4000.0, "type_name": "Luminaria 60x60"},
}

TYPE_HINT_OVERRIDES = (
    {
        "tokens": ("panelredondo", "panel redondo", "redondo", "cascada"),
        "power_w": 18.0,
        "type_name": "Panel redondo / Cascada",
    },
    {
        "tokens": ("luminaria60x60", "60x60", "panel led p27540 36", "luminaria hermetica"),
        "power_w": 40.0,
        "lumens": 4000.0,
        "type_name": "Luminaria 60x60",
    },
)

RECINTO_SHEET_ALIASES = (
    "DatosRecintos",
    "Datos Recintos",
    "Datos_Recintos",
    "Hoja_Recintos",
    "Recintos",
)

ILUMINANCIA_RECOMENDADA = {
    "oficina": 500.0,
    "pasillo": 50.0,
    "servicio sanitario": 100.0,
    "sala de reuniones": 300.0,
    "bodega": 70.0,
    "cocina": 300.0,
    "caja": 500.0,
    "plataforma": 500.0,
    "sala de espera": 200.0,
    "archivo": 400.0,
    "cochera": 50.0,
    "parqueo": 20.0,
    "exteriores": 20.0,
    "trabajo minucioso": 750.0,
    "taller": 200.0,
    "dormitorio": 200.0,
}

FACTOR_UTILIZACION = 0.8
FACTOR_MANTENIMIENTO = 0.7


def _info(msg):
    App.Console.PrintMessage(f"{TAG}[INFO] {msg}\n")


def _warn(msg):
    App.Console.PrintWarning(f"{TAG}[WARN] {msg}\n")


def _err(msg):
    App.Console.PrintError(f"{TAG}[ERROR] {msg}\n")


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _normalize(text):
    s = _safe_text(text).strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\\", "/")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _norm_key(text):
    return re.sub(r"[^a-z0-9]+", "", _normalize(text))


def _valid_token(text):
    norm = _normalize(text)
    if not norm:
        return False
    if norm in IGNORE_TOKENS:
        return False
    return True


def _is_group(obj):
    if obj is None:
        return False
    try:
        if obj.isDerivedFrom("App::DocumentObjectGroup"):
            return True
    except Exception:
        pass
    try:
        if obj.isDerivedFrom("App::Part"):
            return True
    except Exception:
        pass
    return hasattr(obj, "Group")


def _is_conexiones_group(obj):
    label = _normalize(getattr(obj, "Label", ""))
    name = _normalize(getattr(obj, "Name", ""))
    return label.startswith("conexiones") or name.startswith("conexiones")


def _sources(obj):
    if obj is None:
        return
    yield obj
    linked = None
    try:
        linked = getattr(obj, "LinkedObject", None)
    except Exception:
        linked = None
    if linked is None:
        try:
            linked = getattr(obj, "Link", None)
        except Exception:
            linked = None
    if linked is not None and linked is not obj:
        yield linked


def _get_prop(obj, prop_name, default=None):
    for source in _sources(obj):
        try:
            if hasattr(source, prop_name):
                return getattr(source, prop_name)
        except Exception:
            pass
        try:
            props = getattr(source, "PropertiesList", []) or []
            if prop_name in props:
                return source.getPropertyByName(prop_name)
        except Exception:
            pass
    return default


def _first_text_prop(obj, names):
    for name in names:
        value = _safe_text(_get_prop(obj, name, "")).strip()
        if _valid_token(value):
            return value, name
    return "", ""


def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        pass
    try:
        return float(getattr(value, "Value", default))
    except Exception:
        pass
    txt = _safe_text(value).strip().strip('"').replace(" ", "")
    if not txt:
        return default
    if "," in txt and "." not in txt:
        txt = txt.replace(",", ".")
    elif "," in txt and "." in txt and txt.rfind(",") > txt.rfind("."):
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt and "." in txt:
        txt = txt.replace(",", "")
    try:
        return float(txt)
    except Exception:
        return default


def _first_positive_prop(obj, names):
    for name in names:
        value = _to_float(_get_prop(obj, name, None), 0.0)
        if value > 0:
            return value, name
    return 0.0, ""


def _is_link(obj):
    try:
        if str(getattr(obj, "TypeId", "") or "") == "App::Link":
            return True
    except Exception:
        pass
    return hasattr(obj, "LinkedObject") or hasattr(obj, "Link")


def _this_dir():
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()


def _registry_path_candidates():
    here = _this_dir()
    candidates = [here.parent / "Resources" / "registry" / "registry_electric.json"]
    try:
        user_macro = Path(App.getUserMacroDir())
        candidates.append(user_macro / "Resources" / "registry" / "registry_electric.json")
    except Exception:
        pass
    unique = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _load_registry():
    for path in _registry_path_candidates():
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            _warn(f"No se pudo leer registro '{path}': {exc}")
    return {"types": {}}


def _registry_type_info(registry, token):
    reg_types = (registry or {}).get("types") or {}
    raw = _safe_text(token).strip()
    if raw in reg_types:
        return reg_types.get(raw) or {}
    wanted = _norm_key(raw)
    if not wanted:
        return {}
    for key, info in reg_types.items():
        if _norm_key(key) == wanted:
            return info or {}
    return {}


def _catalog_info_for_object(obj, registry):
    text_blobs = [
        _safe_text(_get_prop(obj, "TipoLuminaria", "")).strip(),
        _safe_text(_get_prop(obj, "KeyRegistro", "")).strip(),
        _safe_text(getattr(obj, "Label", "")).strip(),
        _safe_text(getattr(obj, "Name", "")).strip(),
    ]
    combined = " ".join(blob for blob in text_blobs if blob)
    combined_norm = _normalize(combined)
    combined_key = _norm_key(combined)

    for override in TYPE_HINT_OVERRIDES:
        tokens = override.get("tokens") or ()
        if any((_normalize(tok) and _normalize(tok) in combined_norm) or (_norm_key(tok) and _norm_key(tok) in combined_key) for tok in tokens):
            return dict(override), combined or "override"

    candidates = [
        _safe_text(_get_prop(obj, "KeyRegistro", "")).strip(),
        _safe_text(_get_prop(obj, "TipoLuminaria", "")).strip(),
        _safe_text(getattr(obj, "Label", "")).strip(),
        _safe_text(getattr(obj, "Name", "")).strip(),
    ]
    for token in candidates:
        info = _registry_type_info(registry, token)
        electrical = info.get("electrical") if isinstance(info, dict) else None
        if isinstance(electrical, dict) and electrical:
            return electrical, token
        fallback = FALLBACK_CATALOG.get(_norm_key(token))
        if fallback:
            return fallback, token
    return {}, ""


def _load_classifier():
    try:
        import component_classifier as mod
        return importlib.reload(mod)
    except Exception:
        pass
    try:
        con_dir = _this_dir().parent / "Conectar"
        if con_dir.is_dir() and str(con_dir) not in sys.path:
            sys.path.insert(0, str(con_dir))
        import component_classifier as mod
        return importlib.reload(mod)
    except Exception:
        return None


def _is_luminaria(obj, classifier):
    if obj is None or _is_group(obj):
        return False
    if classifier is not None:
        for source in _sources(obj):
            try:
                if classifier.get_component_type(source) == "Luminaria":
                    return True
            except Exception:
                pass

    text_parts = []
    for source in _sources(obj):
        text_parts.extend([
            getattr(source, "Label", ""),
            getattr(source, "Name", ""),
            _get_prop(source, "TipoLuminaria", ""),
            _get_prop(source, "KeyRegistro", ""),
        ])
    text = _normalize(" ".join(_safe_text(part) for part in text_parts if _safe_text(part)))

    for prop_name in ("Tipo", "TipoLogico", "Categoria"):
        value = _normalize(_get_prop(obj, prop_name, ""))
        if value == "luminaria" or "luminaria" in value:
            return True
    key = _normalize(_get_prop(obj, "KeyRegistro", ""))
    if any(token in key for token in LUMINARIA_TEXT_TOKENS):
        return True
    if not any(token in text for token in LUMINARIA_TEXT_TOKENS):
        return False
    if _is_link(obj):
        return True
    return False


def _find_group_by_aliases(doc, aliases):
    wants = {_norm_key(alias) for alias in aliases if alias}
    for obj in getattr(doc, "Objects", []) or []:
        if not _is_group(obj):
            continue
        keys = {_norm_key(getattr(obj, "Label", "")), _norm_key(getattr(obj, "Name", ""))}
        if any(key in wants for key in keys if key):
            return obj
    return None


def _doc_name_token(text, fallback="Grupo"):
    raw = _safe_text(text).strip()
    if raw:
        raw = unicodedata.normalize("NFKD", raw)
        raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    token = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")
    if not token:
        token = fallback
    if not re.match(r"^[A-Za-z_]", token):
        token = f"{fallback}_{token}"
    return token[:60]


def _unique_doc_name(doc, base_name):
    base = _doc_name_token(base_name, "Grupo")
    if doc.getObject(base) is None:
        return base
    idx = 2
    while True:
        candidate = f"{base}_{idx:02d}"
        if doc.getObject(candidate) is None:
            return candidate
        idx += 1


def _group_key_matches(obj, aliases, allow_contains=False):
    wants = {_norm_key(alias) for alias in aliases if alias}
    if not wants:
        return False
    keys = {_norm_key(getattr(obj, "Label", "")), _norm_key(getattr(obj, "Name", ""))}
    for key in keys:
        if not key:
            continue
        if key in wants:
            return True
        if allow_contains and any(want and want in key for want in wants):
            return True
    return False


def _iter_descendant_groups(group):
    seen = set()
    stack = list(getattr(group, "Group", []) or [])
    while stack:
        obj = stack.pop()
        if not _is_group(obj):
            continue
        key = getattr(obj, "Name", None) or id(obj)
        if key in seen:
            continue
        seen.add(key)
        yield obj
        stack.extend(getattr(obj, "Group", []) or [])


def _find_descendant_group_by_aliases(group, aliases, allow_contains=False):
    for child in _iter_descendant_groups(group):
        if _group_key_matches(child, aliases, allow_contains=allow_contains):
            return child
    return None


def _group_display_name(obj):
    label = _safe_text(getattr(obj, "Label", "")).strip()
    name = _safe_text(getattr(obj, "Name", "")).strip()
    if label and name and label != name:
        return f"{label} ({name})"
    return label or name or "<sin nombre>"


def _diagnostic_group_labels(doc, limit=12):
    hinted = []
    generic = []
    for obj in getattr(doc, "Objects", []) or []:
        if not _is_group(obj):
            continue
        label = _safe_text(getattr(obj, "Label", ""))
        name = _safe_text(getattr(obj, "Name", ""))
        key = _norm_key(f"{label} {name}")
        display = _group_display_name(obj)
        if any(token in key for token in ("iluminacion", "luminaria", "lighting", "luz")):
            hinted.append(display)
        elif len(generic) < limit:
            generic.append(display)
    picked = hinted or generic
    return picked[:limit]


def _ensure_project_root_group(doc):
    root = _find_group_by_aliases(doc, ROOT_GROUP_ALIASES)
    if root is not None:
        return root
    for name in ("Electric", "electrico"):
        try:
            obj = doc.getObject(name)
        except Exception:
            obj = None
        if _is_group(obj):
            return obj
    name = _unique_doc_name(doc, "Electric")
    root = doc.addObject("App::DocumentObjectGroup", name)
    root.Label = "Electric"
    _warn("No se encontro grupo raiz electrico; se creo '{}'.".format(_group_display_name(root)))
    return root


def _ensure_child_group(doc, parent, label, name_prefix):
    for child in getattr(parent, "Group", []) or []:
        if _is_group(child) and _group_key_matches(child, [label]):
            return child
    name = _unique_doc_name(doc, "{}_{}".format(name_prefix, _doc_name_token(label, "Grupo")))
    group = doc.addObject("App::DocumentObjectGroup", name)
    group.Label = _safe_text(label).strip() or "Grupo"
    try:
        parent.addObject(group)
    except Exception:
        pass
    return group


def _ensure_iluminacion_group(doc):
    root = _ensure_project_root_group(doc)
    group = _ensure_child_group(doc, root, "ILUMINACION", "ILUMINACION")
    _warn("No se encontro grupo de Iluminacion; se creo '{}' bajo '{}'.".format(
        _group_display_name(group),
        _group_display_name(root),
    ))
    return group


def _find_iluminacion_root(doc):
    root = _find_group_by_aliases(doc, ROOT_GROUP_ALIASES)
    if root is not None:
        found = _find_descendant_group_by_aliases(root, ILUM_GROUP_ALIASES)
        if found is not None:
            return found
        found = _find_descendant_group_by_aliases(root, ILUM_CONTAINER_ALIASES)
        if found is not None:
            return found
        found = _find_descendant_group_by_aliases(root, {"iluminacion"}, allow_contains=True)
        if found is not None:
            return found

    found = _find_group_by_aliases(doc, ILUM_GROUP_ALIASES)
    if found is not None:
        return found
    found = _find_group_by_aliases(doc, ILUM_CONTAINER_ALIASES)
    if found is not None:
        return found
    for obj in getattr(doc, "Objects", []) or []:
        if _is_group(obj) and _group_key_matches(obj, {"iluminacion"}, allow_contains=True):
            return obj

    return _ensure_iluminacion_group(doc)


def _collect_object_paths(root_group):
    entries = []
    seen_groups = set()
    seen_objects = set()
    stack = [(root_group, [])]
    while stack:
        group, path = stack.pop()
        gkey = getattr(group, "Name", None) or id(group)
        if gkey in seen_groups:
            continue
        seen_groups.add(gkey)
        for child in getattr(group, "Group", []) or []:
            if _is_group(child):
                if _is_conexiones_group(child):
                    continue
                stack.append((child, path + [child]))
                continue
            okey = getattr(child, "Name", None) or id(child)
            if okey in seen_objects:
                continue
            seen_objects.add(okey)
            entries.append((child, list(path)))
    return entries


def _ancestor_group_paths(obj, max_depth=16):
    paths = []

    def walk(current, path, seen, depth):
        if depth > max_depth:
            paths.append(path)
            return
        parents = []
        for parent in getattr(current, "InList", []) or []:
            if not _is_group(parent):
                continue
            key = getattr(parent, "Name", None) or id(parent)
            if key in seen:
                continue
            parents.append(parent)
        if not parents:
            paths.append(path)
            return
        for parent in parents:
            key = getattr(parent, "Name", None) or id(parent)
            walk(parent, [parent] + path, seen | {key}, depth + 1)

    walk(obj, [], set(), 0)
    return paths


def _best_path_for_object(obj):
    paths = _ancestor_group_paths(obj)
    if not paths:
        return []

    def score(path):
        keys = {_norm_key(getattr(group, "Label", "")) for group in path}
        keys.update(_norm_key(getattr(group, "Name", "")) for group in path)
        has_ilum = any("iluminacion" in key or "lighting" in key for key in keys if key)
        meaningful = len(_meaningful_path_labels(path))
        return (1 if has_ilum else 0, meaningful, len(path))

    return max(paths, key=score)


def _collect_document_luminaria_paths(doc, classifier):
    entries = []
    seen = set()
    for obj in getattr(doc, "Objects", []) or []:
        if _is_group(obj):
            continue
        if getattr(obj, "TypeId", "") == "Spreadsheet::Sheet":
            continue
        if not _is_luminaria(obj, classifier):
            continue
        key = getattr(obj, "Name", None) or id(obj)
        if key in seen:
            continue
        seen.add(key)
        entries.append((obj, _best_path_for_object(obj)))
    return entries


def _meaningful_path_labels(path_groups):
    labels = []
    for group in path_groups:
        label = _safe_text(getattr(group, "Label", getattr(group, "Name", ""))).strip()
        norm = _normalize(label)
        if not norm or norm in GENERIC_PATH_LABELS:
            continue
        labels.append(label)
    return labels


def _infer_circuit_from_path(path_groups):
    labels = _meaningful_path_labels(path_groups)
    return labels[0] if labels else ""


def _infer_recinto_from_path(path_groups):
    labels = _meaningful_path_labels(path_groups)
    return labels[1] if len(labels) >= 2 else ""


def _infer_switch_from_path(path_groups):
    labels = _meaningful_path_labels(path_groups)
    return labels[2] if len(labels) >= 3 else ""


def _infer_panel_name(circuit_name):
    circuit = _safe_text(circuit_name).strip()
    if not circuit:
        return ""
    match = re.match(r"^([A-Za-z]{1,10})[-_ ]*\d+", circuit)
    if not match:
        return ""
    token = _safe_text(match.group(1)).strip()
    if _norm_key(token) in {"circuito", "circuit", "ckt"}:
        return ""
    return token.upper()


def _placement_base(obj):
    try:
        return getattr(getattr(obj, "Placement", None), "Base", App.Vector())
    except Exception:
        return App.Vector()


def _height_mm(obj):
    for name in HEIGHT_PROPS:
        value = _to_float(_get_prop(obj, name, None), 0.0)
        if value > 0:
            return value
    return 0.0


def _resolve_power(obj, registry):
    value, source = _first_positive_prop(obj, POWER_PROPS)
    if value > 0:
        return value, source
    catalog, token = _catalog_info_for_object(obj, registry)
    value = _to_float(
        catalog.get("power_w", catalog.get("power", catalog.get("watts", 0.0))),
        0.0,
    )
    if value > 0:
        return value, f"catalogo:{token or 'registro'}"
    return 0.0, ""


def _resolve_lumens(obj, registry):
    value, source = _first_positive_prop(obj, LUMEN_PROPS)
    if value > 0:
        return value, source
    catalog, token = _catalog_info_for_object(obj, registry)
    value = _to_float(
        catalog.get("lumens", catalog.get("lumen", catalog.get("luminous_flux_lm", 0.0))),
        0.0,
    )
    if value > 0:
        return value, f"catalogo:{token or 'registro'}"
    return 0.0, ""


def _sheet_key(obj):
    return (
        _norm_key(getattr(obj, "Name", "")),
        _norm_key(getattr(obj, "Label", "")),
    )


def _sheet_text(sheet, addr):
    try:
        return _safe_text(sheet.get(addr)).strip().strip('"')
    except Exception:
        return ""


def _canonical_recinto_key(value):
    txt = _safe_text(value).strip()
    if txt.startswith("'"):
        txt = txt[1:].strip()
    txt = re.sub(r"\s+", " ", txt).strip()
    match = re.match(r"^(.*?)(?:[\s_\-]*)(\d{3,})$", txt)
    if match:
        base = _safe_text(match.group(1)).strip(" _-")
        if base:
            txt = base
    return _norm_key(txt)


def _find_sheet_by_aliases(doc, aliases):
    wanted = {_norm_key(alias) for alias in aliases if alias}
    for obj in getattr(doc, "Objects", []) or []:
        if getattr(obj, "TypeId", "") != "Spreadsheet::Sheet":
            continue
        keys = _sheet_key(obj)
        if any(key in wanted for key in keys if key):
            return obj
    return None


def _load_recinto_data(doc):
    sheet = _find_sheet_by_aliases(doc, RECINTO_SHEET_ALIASES)
    if sheet is None:
        return {}

    rows = {}
    row_count = int(getattr(sheet, "RowCount", 0) or 0)
    max_rows = row_count if row_count > 0 else 500
    for row in range(2, max_rows + 1):
        recinto = _sheet_text(sheet, f"A{row}")
        if not recinto:
            continue
        key = _canonical_recinto_key(recinto)
        if not key:
            continue
        rows[key] = {
            "recinto": recinto,
            "area_m2": _to_float(_sheet_text(sheet, f"B{row}"), 0.0),
            "largo_m": _to_float(_sheet_text(sheet, f"C{row}"), 0.0),
            "ancho_m": _to_float(_sheet_text(sheet, f"D{row}"), 0.0),
            "altura_m": _to_float(_sheet_text(sheet, f"E{row}"), 0.0),
            "descripcion": _sheet_text(sheet, f"H{row}"),
        }
    return rows


def _recommended_lux(description):
    key = _normalize(description)
    if not key:
        return 300.0
    return ILUMINANCIA_RECOMENDADA.get(key, 300.0)


def _clear_sheet(sheet, max_rows=800, max_cols=40):
    try:
        sheet.clearAll()
        return
    except Exception:
        pass
    for row in range(1, int(max_rows) + 1):
        for col in range(1, int(max_cols) + 1):
            try:
                sheet.set(f"{_col_letter(col)}{row}", "")
            except Exception:
                pass


def _col_letter(idx):
    out = ""
    num = int(idx)
    while num > 0:
        num, rem = divmod(num - 1, 26)
        out = chr(65 + rem) + out
    return out or "A"


def _set_text(sheet, addr, value):
    text = _safe_text(value)
    if text.startswith("="):
        text = "'" + text
    sheet.set(addr, text)


def _set_number(sheet, addr, value, decimals=2):
    try:
        sheet.set(addr, f"{float(value):.{int(decimals)}f}")
    except Exception:
        sheet.set(addr, "")


def _find_group_by_key(doc, wanted_key):
    for obj in getattr(doc, "Objects", []) or []:
        if not _is_group(obj):
            continue
        if _norm_key(getattr(obj, "Label", "")) == wanted_key:
            return obj
        if _norm_key(getattr(obj, "Name", "")) == wanted_key:
            return obj
    return None


def _create_group(doc, label):
    token = re.sub(r"[^0-9A-Za-z_]+", "_", _safe_text(label)).strip("_") or "Grupo"
    name = token
    index = 2
    while doc.getObject(name) is not None:
        name = f"{token}_{index}"
        index += 1
    group = doc.addObject("App::DocumentObjectGroup", name)
    group.Label = label
    return group


def _ensure_calculation_group(doc):
    for candidate in ("Hojas de Calculo", "Hojas de Cálculo", "Hojas_Calculo"):
        group = _find_group_by_key(doc, _norm_key(candidate))
        if group is not None:
            try:
                group.Label = CALC_GROUP_LABEL
            except Exception:
                pass
            return group
    legacy = _find_group_by_key(doc, _norm_key("Calculos"))
    if legacy is not None:
        try:
            legacy.Label = CALC_GROUP_LABEL
        except Exception:
            pass
        return legacy
    return _create_group(doc, CALC_GROUP_LABEL)


def _add_to_group(group, obj):
    if group is None or obj is None:
        return
    try:
        if obj not in (getattr(group, "Group", []) or []):
            group.addObject(obj)
    except Exception:
        pass


def _ensure_sheet(doc, name, label, calc_group):
    sheet = doc.getObject(name)
    if sheet is None:
        for obj in getattr(doc, "Objects", []) or []:
            if getattr(obj, "TypeId", "") != "Spreadsheet::Sheet":
                continue
            name_key, label_key = _sheet_key(obj)
            if name_key == _norm_key(name) or label_key == _norm_key(label):
                sheet = obj
                break
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", name)
    _clear_sheet(sheet)
    try:
        sheet.Label = label
    except Exception:
        pass
    _add_to_group(calc_group, sheet)
    return sheet


def _build_item(obj, path_groups, registry):
    circuit_prop, _ = _first_text_prop(obj, CIRCUIT_PROPS)
    recinto_prop, _ = _first_text_prop(obj, AREA_PROPS)
    switch_prop, _ = _first_text_prop(obj, SWITCH_PROPS)
    panel_prop, _ = _first_text_prop(obj, PANEL_PROPS)
    key_registro = _safe_text(_get_prop(obj, "KeyRegistro", "")).strip()
    type_display, _ = _first_text_prop(obj, TYPE_PROPS)

    circuit_name = circuit_prop or _infer_circuit_from_path(path_groups) or "Sin_Circuito"
    recinto_name = recinto_prop or _infer_recinto_from_path(path_groups) or ""
    switch_name = switch_prop or _infer_switch_from_path(path_groups) or ""
    panel_name = panel_prop or _infer_panel_name(circuit_name)

    base = _placement_base(obj)
    altura_rel_mm = _height_mm(obj)
    z_base_mm = _to_float(getattr(base, "z", 0.0), 0.0)
    x_mm = _to_float(getattr(base, "x", 0.0), 0.0)
    y_mm = _to_float(getattr(base, "y", 0.0), 0.0)
    z_total_mm = z_base_mm + altura_rel_mm if altura_rel_mm > 0 else z_base_mm

    power_w, power_source = _resolve_power(obj, registry)
    lumens, lumens_source = _resolve_lumens(obj, registry)

    return {
        "circuit": _safe_text(circuit_name).strip() or "Sin_Circuito",
        "panel": _safe_text(panel_name).strip(),
        "recinto": _safe_text(recinto_name).strip(),
        "switch": _safe_text(switch_name).strip(),
        "label": _safe_text(getattr(obj, "Label", "")).strip(),
        "name": _safe_text(getattr(obj, "Name", "")).strip(),
        "circuit_prop": _safe_text(circuit_prop).strip(),
        "key_registro": key_registro,
        "type_display": type_display or key_registro or _safe_text(getattr(obj, "Label", "")).strip(),
        "altura_rel_mm": altura_rel_mm,
        "z_base_mm": z_base_mm,
        "z_total_mm": z_total_mm,
        "x_mm": x_mm,
        "y_mm": y_mm,
        "power_w": power_w,
        "power_source": power_source,
        "lumens": lumens,
        "lumens_source": lumens_source,
    }


def _write_detail_sheet(sheet, items):
    headers = [
        "Circuito",
        "Panel/Tablero",
        "Recinto",
        "Apagador",
        "Luminaria_Label",
        "Luminaria_Name",
        "CircuitoID_Prop",
        "KeyRegistro",
        "Tipo_Luminaria",
        "AlturaRel_mm",
        "Z_Base_mm",
        "Z_Total_mm",
        "X_mm",
        "Y_mm",
        "Potencia_W",
        "Fuente_Potencia",
        "Flujo_lm",
        "Fuente_Flujo",
    ]
    for idx, header in enumerate(headers, start=1):
        _set_text(sheet, f"{_col_letter(idx)}1", header)

    row = 2
    for item in sorted(items, key=lambda entry: (_normalize(entry["circuit"]), _normalize(entry["recinto"]), _normalize(entry["label"]))):
        _set_text(sheet, f"A{row}", item["circuit"])
        _set_text(sheet, f"B{row}", item["panel"])
        _set_text(sheet, f"C{row}", item["recinto"])
        _set_text(sheet, f"D{row}", item["switch"])
        _set_text(sheet, f"E{row}", item["label"])
        _set_text(sheet, f"F{row}", item["name"])
        _set_text(sheet, f"G{row}", item["circuit_prop"])
        _set_text(sheet, f"H{row}", item["key_registro"])
        _set_text(sheet, f"I{row}", item["type_display"])
        _set_number(sheet, f"J{row}", item["altura_rel_mm"], decimals=2)
        _set_number(sheet, f"K{row}", item["z_base_mm"], decimals=2)
        _set_number(sheet, f"L{row}", item["z_total_mm"], decimals=2)
        _set_number(sheet, f"M{row}", item["x_mm"], decimals=2)
        _set_number(sheet, f"N{row}", item["y_mm"], decimals=2)
        if item["power_w"] > 0:
            _set_number(sheet, f"O{row}", item["power_w"], decimals=2)
        else:
            _set_text(sheet, f"O{row}", "")
        _set_text(sheet, f"P{row}", item["power_source"])
        if item["lumens"] > 0:
            _set_number(sheet, f"Q{row}", item["lumens"], decimals=2)
        else:
            _set_text(sheet, f"Q{row}", "")
        _set_text(sheet, f"R{row}", item["lumens_source"])
        row += 1
    return row


def _write_circuit_sheet(sheet, items, recinto_data, source_group_label):
    headers = [
        "Circuito",
        "Panel/Tablero",
        "Cantidad Luminarias",
        "Potencia Unitaria Prom (W)",
        "Potencia Total (W)",
        "Flujo Unitario Prom (lm)",
        "Flujo Total (lm)",
        "Recintos",
        "Descripcion",
        "Apagadores",
        "Tipos/Registro",
        "Con Potencia",
        "Sin Potencia",
        "Altura Prom (m)",
    ]
    for idx, header in enumerate(headers, start=1):
        _set_text(sheet, f"{_col_letter(idx)}1", header)

    groups = defaultdict(list)
    for item in items:
        groups[item["circuit"]].append(item)

    row = 2
    total_with_power = 0
    total_without_power = 0
    total_with_flux = 0
    total_power = 0.0
    total_flux = 0.0

    for circuit in sorted(groups.keys(), key=lambda value: (_normalize(value) == "sin_circuito", _normalize(value))):
        circuit_items = groups[circuit]
        count = len(circuit_items)
        panel = ""
        panel_values = [item["panel"] for item in circuit_items if _valid_token(item["panel"])]
        if panel_values:
            panel = Counter(panel_values).most_common(1)[0][0]

        with_power_items = [item for item in circuit_items if item["power_w"] > 0]
        with_flux_items = [item for item in circuit_items if item["lumens"] > 0]
        total_power_circuit = sum(item["power_w"] for item in with_power_items)
        total_flux_circuit = sum(item["lumens"] for item in with_flux_items)
        avg_power = (total_power_circuit / len(with_power_items)) if with_power_items else 0.0
        avg_flux = (total_flux_circuit / len(with_flux_items)) if with_flux_items else 0.0
        alturas = [item["z_total_mm"] for item in circuit_items if item["z_total_mm"] > 0]
        altura_prom_m = ((sum(alturas) / float(len(alturas))) / 1000.0) if alturas else 0.0

        recintos = sorted({_safe_text(item["recinto"]).strip() for item in circuit_items if _valid_token(item["recinto"])})
        descripciones = []
        for recinto_name in recintos:
            recinto_key = _canonical_recinto_key(recinto_name)
            room_meta = recinto_data.get(recinto_key, {})
            descripcion = _safe_text(room_meta.get("descripcion", "")).strip()
            if _valid_token(descripcion):
                descripciones.append(descripcion)
        descripciones = sorted(set(descripciones), key=lambda value: _normalize(value))
        switches = sorted({_safe_text(item["switch"]).strip() for item in circuit_items if _valid_token(item["switch"])})
        tipos = sorted({_safe_text(item["type_display"]).strip() for item in circuit_items if _valid_token(item["type_display"])})

        with_power = len(with_power_items)
        without_power = count - with_power
        total_with_power += with_power
        total_without_power += without_power
        total_with_flux += len(with_flux_items)
        total_power += total_power_circuit
        total_flux += total_flux_circuit

        _set_text(sheet, f"A{row}", circuit)
        _set_text(sheet, f"B{row}", panel)
        _set_number(sheet, f"C{row}", count, decimals=0)
        if with_power_items:
            _set_number(sheet, f"D{row}", avg_power, decimals=2)
            _set_number(sheet, f"E{row}", total_power_circuit, decimals=2)
        else:
            _set_text(sheet, f"D{row}", "")
            _set_text(sheet, f"E{row}", "")
        if with_flux_items:
            _set_number(sheet, f"F{row}", avg_flux, decimals=2)
            _set_number(sheet, f"G{row}", total_flux_circuit, decimals=2)
        else:
            _set_text(sheet, f"F{row}", "")
            _set_text(sheet, f"G{row}", "")
        _set_text(sheet, f"H{row}", ", ".join(recintos))
        _set_text(sheet, f"I{row}", ", ".join(descripciones))
        _set_text(sheet, f"J{row}", ", ".join(switches))
        _set_text(sheet, f"K{row}", ", ".join(tipos))
        _set_number(sheet, f"L{row}", with_power, decimals=0)
        _set_number(sheet, f"M{row}", without_power, decimals=0)
        if altura_prom_m > 0:
            _set_number(sheet, f"N{row}", altura_prom_m, decimals=2)
        else:
            _set_text(sheet, f"N{row}", "")
        row += 1

    _set_text(sheet, f"A{row}", "TOTAL")
    _set_number(sheet, f"C{row}", len(items), decimals=0)
    if total_with_power > 0:
        _set_number(sheet, f"E{row}", total_power, decimals=2)
    if total_with_flux > 0:
        _set_number(sheet, f"G{row}", total_flux, decimals=2)
    _set_number(sheet, f"L{row}", total_with_power, decimals=0)
    _set_number(sheet, f"M{row}", total_without_power, decimals=0)

    _set_text(sheet, "P1", "Resumen")
    _set_text(sheet, "P2", "Grupo fuente")
    _set_text(sheet, "Q2", source_group_label)
    _set_text(sheet, "P3", "Circuitos")
    _set_number(sheet, "Q3", len(groups), decimals=0)
    _set_text(sheet, "P4", "Luminarias")
    _set_number(sheet, "Q4", len(items), decimals=0)
    _set_text(sheet, "P5", "Con potencia")
    _set_number(sheet, "Q5", total_with_power, decimals=0)
    _set_text(sheet, "P6", "Sin potencia")
    _set_number(sheet, "Q6", total_without_power, decimals=0)
    _set_text(sheet, "P7", "Con flujo")
    _set_number(sheet, "Q7", total_with_flux, decimals=0)

    return row


def _write_room_sheet(sheet, items, recinto_data, source_group_label):
    headers = [
        "Recinto",
        "Area (m2)",
        "Largo (m)",
        "Ancho (m)",
        "Altura Recinto (m)",
        "Descripcion",
        "Circuitos",
        "Cantidad Luminarias",
        "Potencia Total (W)",
        "Flujo Total (lm)",
        "Iluminancia Objetivo (Lux)",
        "E Final (Lux)",
        "% Iluminacion Recomendada",
        "Tipos/Registro",
        "Apagadores",
        "Con Potencia",
        "Sin Potencia",
    ]
    for idx, header in enumerate(headers, start=1):
        _set_text(sheet, f"{_col_letter(idx)}1", header)

    groups = defaultdict(list)
    for item in items:
        key = _canonical_recinto_key(item["recinto"]) or "sinrecinto"
        groups[key].append(item)

    ordered_keys = sorted(
        groups.keys(),
        key=lambda value: (value == "sinrecinto", _normalize(groups[value][0]["recinto"] if groups[value] else value)),
    )

    row = 2
    total_with_power = 0
    total_without_power = 0
    total_power = 0.0
    total_flux = 0.0

    for key in ordered_keys:
        room_items = groups[key]
        room_name = ""
        for candidate in room_items:
            if _valid_token(candidate["recinto"]):
                room_name = candidate["recinto"]
                break
        if not room_name:
            room_name = "Sin Recinto"

        room_meta = recinto_data.get(key, {})
        area_m2 = _to_float(room_meta.get("area_m2", 0.0), 0.0)
        largo_m = _to_float(room_meta.get("largo_m", 0.0), 0.0)
        ancho_m = _to_float(room_meta.get("ancho_m", 0.0), 0.0)
        altura_m = _to_float(room_meta.get("altura_m", 0.0), 0.0)
        descripcion = _safe_text(room_meta.get("descripcion", "")).strip()

        count = len(room_items)
        with_power_items = [item for item in room_items if item["power_w"] > 0]
        with_flux_items = [item for item in room_items if item["lumens"] > 0]
        power_total = sum(item["power_w"] for item in with_power_items)
        flux_total = sum(item["lumens"] for item in with_flux_items)
        total_power += power_total
        total_flux += flux_total

        with_power = len(with_power_items)
        without_power = count - with_power
        total_with_power += with_power
        total_without_power += without_power

        circuits = sorted({_safe_text(item["circuit"]).strip() for item in room_items if _valid_token(item["circuit"])})
        switches = sorted({_safe_text(item["switch"]).strip() for item in room_items if _valid_token(item["switch"])})
        tipos = sorted({_safe_text(item["type_display"]).strip() for item in room_items if _valid_token(item["type_display"])})

        lux_target = _recommended_lux(descripcion)
        e_final = 0.0
        pct = 0.0
        if area_m2 > 0 and flux_total > 0:
            e_final = (flux_total / area_m2) * FACTOR_UTILIZACION * FACTOR_MANTENIMIENTO
            if lux_target > 0:
                pct = (e_final / lux_target) * 100.0

        _set_text(sheet, f"A{row}", room_name)
        if area_m2 > 0:
            _set_number(sheet, f"B{row}", area_m2, decimals=2)
        if largo_m > 0:
            _set_number(sheet, f"C{row}", largo_m, decimals=2)
        if ancho_m > 0:
            _set_number(sheet, f"D{row}", ancho_m, decimals=2)
        if altura_m > 0:
            _set_number(sheet, f"E{row}", altura_m, decimals=2)
        _set_text(sheet, f"F{row}", descripcion)
        _set_text(sheet, f"G{row}", ", ".join(circuits))
        _set_number(sheet, f"H{row}", count, decimals=0)
        if power_total > 0:
            _set_number(sheet, f"I{row}", power_total, decimals=2)
        else:
            _set_text(sheet, f"I{row}", "")
        if flux_total > 0:
            _set_number(sheet, f"J{row}", flux_total, decimals=2)
        else:
            _set_text(sheet, f"J{row}", "")
        _set_number(sheet, f"K{row}", lux_target, decimals=0)
        if e_final > 0:
            _set_number(sheet, f"L{row}", e_final, decimals=2)
            _set_number(sheet, f"M{row}", pct, decimals=2)
        else:
            _set_text(sheet, f"L{row}", "")
            _set_text(sheet, f"M{row}", "")
        _set_text(sheet, f"N{row}", ", ".join(tipos))
        _set_text(sheet, f"O{row}", ", ".join(switches))
        _set_number(sheet, f"P{row}", with_power, decimals=0)
        _set_number(sheet, f"Q{row}", without_power, decimals=0)
        row += 1

    _set_text(sheet, f"A{row}", "TOTAL")
    _set_number(sheet, f"H{row}", len(items), decimals=0)
    if total_power > 0:
        _set_number(sheet, f"I{row}", total_power, decimals=2)
    if total_flux > 0:
        _set_number(sheet, f"J{row}", total_flux, decimals=2)
    _set_number(sheet, f"P{row}", total_with_power, decimals=0)
    _set_number(sheet, f"Q{row}", total_without_power, decimals=0)

    _set_text(sheet, "S1", "Resumen")
    _set_text(sheet, "S2", "Grupo fuente")
    _set_text(sheet, "T2", source_group_label)
    _set_text(sheet, "S3", "Recintos")
    _set_number(sheet, "T3", len(groups), decimals=0)
    _set_text(sheet, "S4", "Luminarias")
    _set_number(sheet, "T4", len(items), decimals=0)
    _set_text(sheet, "S5", "Con potencia")
    _set_number(sheet, "T5", total_with_power, decimals=0)
    _set_text(sheet, "S6", "Sin potencia")
    _set_number(sheet, "T6", total_without_power, decimals=0)

    return row


def export_lighting_schedule():
    doc = App.ActiveDocument
    if doc is None:
        _err("No hay documento activo.")
        return False

    root = _find_iluminacion_root(doc)
    if root is None:
        _err("No se encontro el grupo de Iluminacion en el documento.")
        return False

    calc_group = _ensure_calculation_group(doc)
    room_sheet = _ensure_sheet(doc, ROOM_SHEET_NAME, ROOM_SHEET_LABEL, calc_group)
    circuit_sheet = _ensure_sheet(doc, CIRCUIT_SHEET_NAME, CIRCUIT_SHEET_LABEL, calc_group)
    detail_sheet = _ensure_sheet(doc, DETAIL_SHEET_NAME, DETAIL_SHEET_LABEL, calc_group)

    classifier = _load_classifier()
    registry = _load_registry()
    recinto_data = _load_recinto_data(doc)

    items = []
    for obj, path_groups in _collect_object_paths(root):
        if not _is_luminaria(obj, classifier):
            continue
        items.append(_build_item(obj, path_groups, registry))

    source_group_label = _safe_text(getattr(root, "Label", getattr(root, "Name", "Iluminacion")))
    if not items:
        fallback_entries = _collect_document_luminaria_paths(doc, classifier)
        if fallback_entries:
            _warn(
                "No se detectaron luminarias bajo '{}'; se encontraron {} luminaria(s) "
                "con busqueda en todo el documento.".format(source_group_label, len(fallback_entries))
            )
            items = [_build_item(obj, path_groups, registry) for obj, path_groups in fallback_entries]
            source_group_label = "Documento completo (fallback)"

    _write_room_sheet(room_sheet, items, recinto_data, source_group_label)
    _write_circuit_sheet(circuit_sheet, items, recinto_data, source_group_label)
    detail_end_row = _write_detail_sheet(detail_sheet, items)

    try:
        room_sheet.recompute()
        circuit_sheet.recompute()
        detail_sheet.recompute()
        doc.recompute()
    except Exception as exc:
        _warn(f"Recompute con advertencia: {exc}")

    if not items:
        _warn("No se detectaron luminarias bajo el grupo de Iluminacion.")
        hints = _diagnostic_group_labels(doc)
        if hints:
            _warn("Grupos candidatos visibles: {}.".format(", ".join(hints)))
        return True

    missing_power = sum(1 for item in items if item["power_w"] <= 0)
    _info(
        "Exportadas {} luminaria(s) en '{}', '{}' y '{}' dentro de '{}'. "
        "Filas detalle: {}. Sin potencia: {}.".format(
            len(items),
            ROOM_SHEET_LABEL,
            CIRCUIT_SHEET_LABEL,
            DETAIL_SHEET_LABEL,
            CALC_GROUP_LABEL,
            max(0, detail_end_row - 2),
            missing_power,
        )
    )
    if missing_power:
        _warn(
            "Hay luminarias sin potencia. La hoja resume bien el conteo por circuito, "
            "pero la potencia total dependera de las propiedades o del catalogo disponible."
        )
    return True
