import re
import json
import unicodedata


KNOWN_TYPES = (
    "Toma",
    "Apagador",
    "Luminaria",
    "Sensor",
    "Rociador",
    "Altavoz",
    "Camara",
)

KNOWN_ENDPOINT_KINDS = (
    "Octogonal",
    "Cuadrada",
    "Luminaria",
    "Otro",
)


_TYPE_MAP = {
    "toma": "Toma",
    "tomacorriente": "Toma",
    "enchufe": "Toma",
    "apagador": "Apagador",
    "interruptor": "Apagador",
    "switch": "Apagador",
    "luminaria": "Luminaria",
    "lampara": "Luminaria",
    "sensor": "Sensor",
    "rociador": "Rociador",
    "sprinkler": "Rociador",
    "altavoz": "Altavoz",
    "parlante": "Altavoz",
    "camara": "Camara",
    "camera": "Camara",
}

_ENDPOINT_MAP = {
    "octogonal": "Octogonal",
    "octagonal": "Octogonal",
    "octagono": "Octogonal",
    "octagon": "Octogonal",
    "cuadrada": "Cuadrada",
    "cuadrado": "Cuadrada",
    "square": "Cuadrada",
    "4x4": "Cuadrada",
    "rectangular": "Cuadrada",
    "luminaria": "Luminaria",
    "lampara": "Luminaria",
    "luz": "Luminaria",
    "otro": "Otro",
}

_TEXT_ATTRS = (
    "Tipo",
    "TipoLogico",
    "Categoria",
    "Label",
    "Name",
    "KeyRegistro",
    "EtiquetaPlano",
    "CajaOrigenName",
    "CajaOrigenKey",
    "EndpointKind",
    "TipoEndpoint",
    "TipoCaja",
)


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _strip_accents(text):
    s = _safe_text(text)
    if not s:
        return ""
    try:
        s = unicodedata.normalize("NFKD", s)
        return "".join(ch for ch in s if not unicodedata.combining(ch))
    except Exception:
        return s


def _normalize_key(text):
    s = _strip_accents(text).strip().lower()
    if not s:
        return ""
    s = s.replace("-", "_")
    s = re.sub(r"\s+", "_", s)
    return s


def _norm_blob(text):
    s = _normalize_key(text)
    if not s:
        return ""
    s = s.replace("_", "")
    return s


def _is_group_obj(obj):
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


def _type_from_csv_kind(value):
    s = _normalize_key(value)
    if not s:
        return None

    # Assistant CSV "ceiling" items are luminarias.
    if s in ("techo", "cielo", "luz", "iluminacion"):
        return "Luminaria"
    if ("panel" in s) or ("lamp" in s):
        return "Luminaria"

    # Non-semantic assistant states.
    if s in ("otro", "__auto__", "__pending__", "pending", "pendiente", "skip"):
        return None

    t = normalize_type(s)
    if t:
        return t
    return None


def normalize_type(value):
    s = _normalize_key(value)
    if not s:
        return None
    if s in _TYPE_MAP:
        return _TYPE_MAP[s]
    for key, canon in _TYPE_MAP.items():
        if key in s:
            return canon
    return None


def normalize_endpoint_kind(value):
    s = _normalize_key(value)
    if not s:
        return None
    if s in _ENDPOINT_MAP:
        return _ENDPOINT_MAP[s]
    for key, canon in _ENDPOINT_MAP.items():
        if key in s:
            return canon
    return None


def get_component_type(obj):
    if obj is None:
        return None

    # 1) Tipo explicito (nuevo esquema ElectricCR)
    try:
        if hasattr(obj, "Tipo"):
            t = normalize_type(getattr(obj, "Tipo"))
            if t:
                return t
    except Exception:
        pass

    # 2) Tipo alterno
    for attr in ("TipoLogico", "Categoria"):
        try:
            if hasattr(obj, attr):
                t = normalize_type(getattr(obj, attr))
                if t:
                    return t
        except Exception:
            pass

    # 2.5) CsvKind from CSV assistants.
    for attr in ("CsvKind", "CsvTipo", "TipoCSV", "CsvCategory"):
        try:
            if hasattr(obj, attr):
                t = _type_from_csv_kind(getattr(obj, attr))
                if t:
                    return t
        except Exception:
            pass

    # 3) Registro y metadatos
    for attr in ("KeyRegistro", "EtiquetaPlano", "CircuitoID", "RecursoProto2D", "RecursoProto3D"):
        try:
            if hasattr(obj, attr):
                t = normalize_type(getattr(obj, attr))
                if t:
                    return t
        except Exception:
            pass

    # 4) Proxy / clase (legacy FeaturePython)
    try:
        proxy = getattr(obj, "Proxy", None)
        if proxy is not None:
            cls = proxy.__class__.__name__
            t = normalize_type(cls)
            if t:
                return t
    except Exception:
        pass

    # 5) Label/Name (legacy por nombre)
    lbl = _safe_text(getattr(obj, "Label", ""))
    name = _safe_text(getattr(obj, "Name", ""))
    t = normalize_type(f"{lbl} {name}")
    if t:
        return t

    return None


def _text_blob_for_obj(obj):
    vals = []
    for attr in _TEXT_ATTRS:
        try:
            vals.append(_safe_text(getattr(obj, attr, "")))
        except Exception:
            pass
    try:
        linked = getattr(obj, "LinkedObject", None)
    except Exception:
        linked = None
    if linked is not None:
        for attr in _TEXT_ATTRS:
            try:
                vals.append(_safe_text(getattr(linked, attr, "")))
            except Exception:
                pass
    return _norm_blob(" ".join(vals))


def _ports_from_obj_json(obj):
    raw = _safe_text(getattr(obj, "PuertosJSON", "")).strip()
    if not raw:
        try:
            linked = getattr(obj, "LinkedObject", None)
        except Exception:
            linked = None
        if linked is not None:
            raw = _safe_text(getattr(linked, "PuertosJSON", "")).strip()
    if not raw:
        return []
    if not (raw.startswith("[") and raw.endswith("]")):
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append(item)
    return out


def _endpoint_kind_from_ports(obj):
    ports = _ports_from_obj_json(obj)
    if not ports:
        return None

    names = []
    for p in ports:
        n = _norm_blob(_safe_text(p.get("name", "")))
        if n:
            names.append(n)
    if any(n in ("northeast", "northwest", "southeast", "southwest", "ne", "nw", "se", "sw") for n in names):
        return "Octogonal"
    if any(n in ("north", "south", "east", "west", "n", "s", "e", "w") for n in names):
        return "Cuadrada"

    # Si tiene puertos pero no nombres claros, asumir caja.
    return "Otro"


def get_endpoint_kind(obj):
    """Clasifica un objeto para el módulo unificado de conexiones.

    Retorna: Octogonal | Cuadrada | Luminaria | Otro | None
    """
    if obj is None:
        return None
    if _is_group_obj(obj):
        return None

    # Evitar clasificar rutas/conexiones como endpoints conectables.
    try:
        if _normalize_key(getattr(obj, "Tipo", "")) in ("conduitpath", "conexion", "emt_flexible"):
            return None
    except Exception:
        pass

    # 1) Campo endpoint explícito si existe.
    for attr in ("EndpointKind", "TipoEndpoint", "TipoCaja"):
        try:
            kind = normalize_endpoint_kind(getattr(obj, attr, ""))
            if kind:
                return kind
        except Exception:
            pass

    # 2) Heurísticas por texto.
    blob = _text_blob_for_obj(obj)
    if any(tok in blob for tok in ("octogonal", "octagonal", "octagono", "octagon", "emtoctagonbox")):
        return "Octogonal"
    if any(tok in blob for tok in ("cuadrada", "cuadrado", "square", "rectangular", "caja4x4", "4x4")):
        return "Cuadrada"

    # 3) Heurística por puertos expuestos.
    kind_from_ports = _endpoint_kind_from_ports(obj)
    if kind_from_ports in ("Octogonal", "Cuadrada"):
        return kind_from_ports

    # 4) Tipo de componente.
    ctype = get_component_type(obj)
    if ctype == "Luminaria":
        return "Luminaria"
    if ctype in KNOWN_TYPES:
        return "Otro"

    # 5) Fallback por texto general.
    if any(tok in blob for tok in ("luminaria", "lampara", "iluminacion", "luz")):
        return "Luminaria"
    if any(tok in blob for tok in ("caja", "box", "junction", "emt")):
        return "Otro"

    return "Otro"


def is_known_component(obj):
    return get_component_type(obj) is not None


def is_type(obj, allowed_types):
    t = get_component_type(obj)
    if not t:
        return False
    allowed = set(_safe_text(x).strip() for x in (allowed_types or []) if _safe_text(x).strip())
    return t in allowed


def is_endpoint_kind(obj, allowed_kinds):
    kind = get_endpoint_kind(obj)
    if not kind:
        return False
    allowed = set(_safe_text(x).strip() for x in (allowed_kinds or []) if _safe_text(x).strip())
    return kind in allowed


def is_toma(obj):
    return get_component_type(obj) == "Toma"


def is_luminaria(obj):
    return get_endpoint_kind(obj) == "Luminaria"


def is_octogonal_endpoint(obj):
    return get_endpoint_kind(obj) == "Octogonal"


def is_cuadrada_endpoint(obj):
    return get_endpoint_kind(obj) == "Cuadrada"
