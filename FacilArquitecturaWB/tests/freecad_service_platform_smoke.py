"""FreeCADCmd smoke test for creation, update and document restore.

Run with FreeCADCmd.exe and this file as its first argument.
"""

from __future__ import annotations

import os
import sys

import FreeCAD


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.modules.service_platform.builder import (  # noqa: E402
    create_service_platform_front,
    update_service_platform_front,
)
from FacilArquitecturaWB.modules.service_platform.model import PlatformOptions  # noqa: E402
from FacilArquitecturaWB.modules.service_platform.properties import GENERATED_BY  # noqa: E402
from FacilArquitecturaWB.modules.service_platform.validation import PlatformValidationError  # noqa: E402


def _generated_count(doc):
    return sum(1 for obj in doc.Objects if str(getattr(obj, "FA_GeneratedBy", "")) == GENERATED_BY)


def main():
    output = os.path.join(REPO_DIR, ".codex_tmp", "service_platform_smoke.FCStd")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc = FreeCAD.newDocument("ServicePlatformSmoke")
    result = create_service_platform_front(doc, PlatformOptions())
    doc.recompute()
    root = result["root"]
    root_name = root.Name
    assert len(result["sketches"]) == 6
    assert all(len(sketch.Geometry) > 0 for sketch in result["sketches"].values())
    assert all(len(sketch.Constraints) > 0 for sketch in result["sketches"].values())
    assert all(sketch.Owner is root for sketch in result["sketches"].values())
    assert len(result["geometry"]["desks"]) == 2
    assert len(result["geometry"]["dividers"]) == 1
    assert len(result["geometry"]["staff_zones"]) == 2
    assert len(result["geometry"]["public_zones"]) == 2
    first_count = _generated_count(doc)
    assert first_count == 14, first_count  # root + six sketches + seven shapes
    manual = doc.addObject("App::FeaturePython", "PA_ManualNote")
    result["root"].FA_GeometryGroup.addObject(manual)
    root.FA_Reviewed = True
    update_service_platform_front(doc, root)
    doc.recompute()
    assert _generated_count(doc) == first_count
    assert doc.getObject("PA_ManualNote") is manual
    assert root.FA_Reviewed is True

    # Four-position case: 4 desks, 3 dividers and 8 functional zones.
    result["sheet"].set("B2", "7200")
    result["sheet"].set("B3", "4")
    doc.recompute()
    four = update_service_platform_front(doc, root)
    doc.recompute()
    assert len(four["geometry"]["desks"]) == 4
    assert len(four["geometry"]["dividers"]) == 3
    assert len(four["geometry"]["staff_zones"]) == 4
    assert len(four["geometry"]["public_zones"]) == 4

    # Invalid input is rejected before any representation is removed.
    result["sheet"].set("B2", "2400")
    result["sheet"].set("B3", "2")
    doc.recompute()
    objects_before_rejection = len(doc.Objects)
    try:
        update_service_platform_front(doc, root)
        raise AssertionError("Insufficient width was not rejected")
    except PlatformValidationError:
        pass
    assert len(doc.Objects) == objects_before_rejection

    result["sheet"].set("B2", "3840")
    result["sheet"].set("B3", "2")
    doc.recompute()
    update_service_platform_front(doc, root)
    doc.recompute()
    doc.saveAs(output)
    document_name = doc.Name
    FreeCAD.closeDocument(document_name)

    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    restored_root = reopened.getObject(root_name)
    assert restored_root is not None
    before_restore_update = len(reopened.Objects)
    update_service_platform_front(reopened, restored_root)
    reopened.recompute()
    assert len(reopened.Objects) == before_restore_update
    assert _generated_count(reopened) == first_count
    assert reopened.getObject("PA_ManualNote") is not None
    assert restored_root.FA_Reviewed is True
    reopened.save()
    FreeCAD.closeDocument(reopened.Name)

    undo_doc = FreeCAD.newDocument("ServicePlatformUndo")
    undo_doc.UndoMode = 1
    undo_doc.openTransaction("Create service platform")
    undo_result = create_service_platform_front(undo_doc, PlatformOptions())
    undo_doc.recompute()
    undo_doc.commitTransaction()
    undo_root_name = undo_result["root"].Name
    assert undo_doc.getObject(undo_root_name) is not None
    undo_doc.undo()
    undo_doc.recompute()
    assert undo_doc.getObject(undo_root_name) is None
    undo_doc.redo()
    undo_doc.recompute()
    assert undo_doc.getObject(undo_root_name) is not None
    FreeCAD.closeDocument(undo_doc.Name)
    print("SERVICE_PLATFORM_SMOKE_OK", output, first_count)


if __name__ == "__main__":
    main()
