import re


KNOWN_TYPES = (
    "Toma",
    "Apagador",
    "Luminaria",
    "Sensor",
    "Rociador",
    "Altavoz",
    "Camara",
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


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _normalize_key(text):
    s = _safe_text(text).strip().lower()
    if not s:
        return ""
    s = s.replace("-", "_")
    s = re.sub(r"\s+", "_", s)
    return s


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


def is_known_component(obj):
    return get_component_type(obj) is not None


def is_type(obj, allowed_types):
    t = get_component_type(obj)
    if not t:
        return False
    allowed = set(_safe_text(x).strip() for x in (allowed_types or []) if _safe_text(x).strip())
    return t in allowed


def is_toma(obj):
    return get_component_type(obj) == "Toma"
