"""Matriz unificada de estrategias de conexión por tipo de endpoint.

Tipos de endpoint soportados:
- Octogonal
- Cuadrada
- Luminaria
- Otro
"""

from typing import Dict, Tuple, Optional

try:
    import component_classifier as _cc  # type: ignore
except Exception:
    _cc = None


_KIND_ORDER = {
    "Octogonal": 0,
    "Cuadrada": 1,
    "Luminaria": 2,
    "Otro": 3,
}


_RULES: Dict[Tuple[str, str], Dict[str, object]] = {
    ("Octogonal", "Octogonal"): {
        "preferred": "octo_45",
        "allowed": ("octo_45", "octo_direct", "orthogonal_l", "snake"),
        "label": "Octogonales entre si",
    },
    ("Octogonal", "Cuadrada"): {
        "preferred": "octo_45",
        "allowed": ("octo_45", "orthogonal_l", "snake"),
        "label": "Octogonal con caja cuadrada",
    },
    ("Cuadrada", "Cuadrada"): {
        "preferred": "orthogonal_l",
        "allowed": ("orthogonal_l", "snake"),
        "label": "Cajas cuadradas entre si",
    },
    ("Octogonal", "Luminaria"): {
        "preferred": "spline_diag",
        "allowed": ("spline_diag", "spline"),
        "label": "Octogonal con luminaria",
    },
    ("Cuadrada", "Luminaria"): {
        "preferred": "spline",
        "allowed": ("spline", "orthogonal_l"),
        "label": "Cuadrada con luminaria",
    },
    ("Octogonal", "Otro"): {
        "preferred": "spline_diag",
        "allowed": ("spline_diag", "orthogonal_l", "spline"),
        "label": "Octogonal con otros objetos",
    },
    ("Cuadrada", "Otro"): {
        "preferred": "orthogonal_l",
        "allowed": ("orthogonal_l", "snake", "spline"),
        "label": "Cuadrada con otros objetos",
    },
    ("Luminaria", "Otro"): {
        "preferred": "spline",
        "allowed": ("spline",),
        "label": "Luminaria con otros objetos",
    },
    ("Otro", "Otro"): {
        "preferred": "orthogonal_l",
        "allowed": ("orthogonal_l", "spline", "snake"),
        "label": "Otros objetos entre si",
    },
}


def _safe_text(value) -> str:
    try:
        return str(value or "")
    except Exception:
        return ""


def normalize_endpoint_kind(value) -> Optional[str]:
    txt = _safe_text(value).strip()
    if not txt:
        return None
    if _cc is not None and hasattr(_cc, "normalize_endpoint_kind"):
        try:
            return _cc.normalize_endpoint_kind(txt)
        except Exception:
            pass
    txt_low = txt.lower()
    if txt_low.startswith("oct"):
        return "Octogonal"
    if txt_low.startswith("cuad") or ("square" in txt_low):
        return "Cuadrada"
    if txt_low.startswith("lum"):
        return "Luminaria"
    if txt_low.startswith("otro"):
        return "Otro"
    return None


def classify_endpoint(obj) -> Optional[str]:
    if _cc is not None and hasattr(_cc, "get_endpoint_kind"):
        try:
            return _cc.get_endpoint_kind(obj)
        except Exception:
            return None
    return None


def _pair_key(kind_a, kind_b) -> Optional[Tuple[str, str]]:
    a = normalize_endpoint_kind(kind_a)
    b = normalize_endpoint_kind(kind_b)
    if not a or not b:
        return None
    ka = _KIND_ORDER.get(a, 999)
    kb = _KIND_ORDER.get(b, 999)
    if ka <= kb:
        return (a, b)
    return (b, a)


def get_connection_rule(kind_a, kind_b) -> Optional[Dict[str, object]]:
    key = _pair_key(kind_a, kind_b)
    if key is None:
        return None
    return _RULES.get(key)


def is_supported_connection(kind_a, kind_b) -> bool:
    return get_connection_rule(kind_a, kind_b) is not None


def allowed_strategies(kind_a, kind_b):
    rule = get_connection_rule(kind_a, kind_b)
    if not rule:
        return ()
    return tuple(rule.get("allowed", ()) or ())


def preferred_strategy(kind_a, kind_b) -> Optional[str]:
    rule = get_connection_rule(kind_a, kind_b)
    if not rule:
        return None
    pref = _safe_text(rule.get("preferred", "")).strip()
    return pref or None


def classify_pair(obj_a, obj_b):
    return classify_endpoint(obj_a), classify_endpoint(obj_b)
