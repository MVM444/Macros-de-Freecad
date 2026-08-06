"""Compatibility helpers for Draft Text restore behavior in FreeCAD 1.1.

FreeCAD 1.1's Draft Text proxy may receive ``onDocumentRestored`` before its
serialized state has populated ``stored_type``.  MEP uses Draft Text for
vector labels, so initialize that harmless transient attribute defensively.
"""


def _draft_text_class():
    try:
        from draftobjects.text import Text

        return Text
    except Exception:
        return None


def patch_draft_text_class():
    """Make an early Draft Text restore callback safe and idempotent."""

    text_class = _draft_text_class()
    if text_class is None:
        return False
    if not hasattr(text_class, "stored_type"):
        text_class.stored_type = None
    return True


def is_draft_text_object(obj):
    if obj is None:
        return False
    proxy = getattr(obj, "Proxy", None)
    text_class = _draft_text_class()
    if proxy is None or text_class is None:
        return False
    try:
        return isinstance(proxy, text_class)
    except Exception:
        proxy_type = type(proxy)
        return (
            proxy_type.__name__ == "Text"
            and str(getattr(proxy_type, "__module__", "") or "").startswith("draftobjects.text")
        )


def ensure_text_proxy_state(obj):
    """Initialize missing per-instance restore state on one Draft Text."""

    patch_draft_text_class()
    if not is_draft_text_object(obj):
        return False
    proxy = getattr(obj, "Proxy", None)
    try:
        attrs = getattr(proxy, "__dict__", {})
        if "stored_type" not in attrs:
            proxy.stored_type = None
            return True
    except Exception:
        return False
    return False


def repair_document(doc, mep_only=True):
    """Repair Draft Text runtime state without changing model properties."""

    if doc is None:
        return 0
    repaired = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if mep_only:
            props = list(getattr(obj, "PropertiesList", []) or [])
            if "MEPType" not in props:
                continue
            try:
                mep_type = str(getattr(obj, "MEPType", "") or "")
            except Exception:
                mep_type = ""
            if not mep_type.startswith("HVAC"):
                continue
        if ensure_text_proxy_state(obj):
            repaired += 1
    return repaired


PATCH_APPLIED = patch_draft_text_class()
