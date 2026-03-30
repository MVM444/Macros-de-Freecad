"""HVAC package for MEPWorkbenchCR."""

import FreeCAD as App

from . import hvac_condensing
from . import hvac_equipment
from . import hvac_label
from . import hvac_ports
from . import hvac_project
from . import hvac_route
from . import hvac_sheet
from . import hvac_space
from . import hvac_validate

LOG_PREFIX = "[MEP-HVAC] "


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def recalculate_document(doc=None):
    """Recalculate full HVAC model in active document."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo para recalculo HVAC")
        return

    log("Recalculando documento HVAC completo")
    project = hvac_project.get_or_create_project(doc)
    hvac_project.ensure_hvac_root_group(doc)
    hvac_project.recalculate_project(project)
    hvac_ports.sanitize_all_ports(doc)
    hvac_ports.prune_unused_ports(doc)
    hvac_space.cleanup_nested_spaces(doc)

    for space in hvac_space.find_spaces(doc):
        if "Project" in space.PropertiesList and getattr(space, "Project", None) is None:
            space.Project = project
        hvac_space.calculate_space_load(space, project=project)

    for equipment in hvac_equipment.find_equipments(doc):
        hvac_equipment.update_equipment_coverage(equipment)
        if bool(getattr(equipment, "UsePorts", False)):
            hvac_equipment.update_equipment_ports(equipment)

    for condenser in hvac_condensing.find_condensers(doc):
        hvac_condensing.recalculate_condenser(condenser)

    hvac_route.update_all_routes(doc)
    hvac_label.update_all_labels(doc, ensure_visible=True)
    hvac_sheet.update_quickcalc_sheet(doc)
    hvac_project.organize_hvac_objects(doc)
    doc.recompute()
    log("Recalculo HVAC finalizado")


def validate_document(doc=None, recalc_first=True):
    """Validate HVAC model and return report dict."""

    return hvac_validate.validate_document(doc=doc, recalc_first=recalc_first)
