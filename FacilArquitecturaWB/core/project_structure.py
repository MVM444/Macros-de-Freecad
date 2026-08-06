"""Project structure helpers for FacilArquitecturaWB.

Descripcion: crea y localiza grupos base del proyecto.
Fecha: 2026-07-23
Version: 0.2.0
Instrucciones: las funciones deben ser idempotentes y no destruir trabajo del usuario.
"""

from __future__ import annotations

import FreeCAD

from .constants import BUILD_ID, CREATED_BY, GROUPS, LOG_PREFIX, ROOT_GROUP_NAME, VERSION


def msg(text: str) -> None:
    FreeCAD.Console.PrintMessage(LOG_PREFIX + str(text) + "\n")


def warn(text: str) -> None:
    FreeCAD.Console.PrintWarning(LOG_PREFIX + str(text) + "\n")


def err(text: str) -> None:
    FreeCAD.Console.PrintError(LOG_PREFIX + str(text) + "\n")


def active_or_new_document():
    """Return active document or create a new one."""
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("FacilArquitectura")
        msg("Documento nuevo creado: FacilArquitectura")
    return doc


def set_prop(obj, prop_type: str, name: str, group: str, desc: str, value) -> None:
    """Set a FreeCAD property without failing when the property already exists."""
    try:
        if not hasattr(obj, name):
            obj.addProperty(prop_type, name, group, desc)
        setattr(obj, name, value)
    except Exception as exc:
        warn("No se pudo asignar propiedad %s en %s: %s" % (name, getattr(obj, "Name", obj), exc))


def find_by_name_or_label(doc, name: str, label: str = ""):
    """Find object by internal Name or visible Label."""
    for obj in doc.Objects:
        if str(getattr(obj, "Name", "")) == name:
            return obj
        if label and str(getattr(obj, "Label", "")) == label:
            return obj
    return None


def ensure_group(doc, name: str, label: str, parent=None):
    """Create or reuse an App::DocumentObjectGroup."""
    obj = find_by_name_or_label(doc, name, label)
    if obj is None:
        obj = doc.addObject("App::DocumentObjectGroup", name)
        obj.Label = label
        msg("Grupo creado: %s" % label)
    else:
        msg("Grupo existente: %s" % label)
    if parent is not None:
        try:
            if obj not in list(getattr(parent, "Group", []) or []):
                parent.addObject(obj)
        except Exception:
            pass
    return obj


def ensure_project_structure(doc=None):
    """Create FA_Project and standard child groups."""
    doc = doc or active_or_new_document()
    root = ensure_group(doc, ROOT_GROUP_NAME, ROOT_GROUP_NAME)
    set_prop(root, "App::PropertyBool", "FA_Workbench", "FacilArquitectura", "Proyecto Facil Arquitectura", True)
    set_prop(root, "App::PropertyString", "FA_ProjectVersion", "FacilArquitectura", "Version del proyecto", VERSION)
    set_prop(
        root,
        "App::PropertyString",
        "FA_WorkbenchVersion",
        "FacilArquitectura",
        "Version del Workbench que actualizo el proyecto",
        VERSION,
    )
    set_prop(
        root,
        "App::PropertyString",
        "FA_WorkbenchBuild",
        "FacilArquitectura",
        "Compilacion exacta del Workbench",
        BUILD_ID,
    )
    set_prop(
        root,
        "App::PropertyString",
        "FA_Description",
        "FacilArquitectura",
        "Descripcion",
        "Base arquitectonica organizada para instalaciones electromecanicas",
    )
    set_prop(root, "App::PropertyString", "FA_CreatedBy", "FacilArquitectura", "Creado por", CREATED_BY)

    groups = {}
    for key, (name, label) in GROUPS.items():
        groups[key] = ensure_group(doc, name, label, root)
    return doc, root, groups
