"""FreeCAD GUI regression test for HVAC space copy/convert behavior.

Run from FreeCAD's Python console or MCP with::

    from MEPWorkbenchCR.tests.test_hvac_space_copy_convert import run
    run()
"""

import os
import tempfile

import FreeCAD as App
import Part

from MEPWorkbenchCR.MEP.hvac import hvac_equipment
from MEPWorkbenchCR.MEP.hvac import hvac_label
from MEPWorkbenchCR.MEP.hvac import hvac_space


DOC_NAME = "Test_HVACSpace_CopyConvert"


def _closed_wire(points):
    vectors = [App.Vector(*point) for point in points]
    if vectors[0] != vectors[-1]:
        vectors.append(vectors[0])
    return Part.makePolygon(vectors)


def run():
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)

    temp_path = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    doc = App.newDocument(DOC_NAME)
    try:
        outer = doc.addObject("Part::Part2DObject", "AreaSalonCompleto")
        outer.Label = "Salon irregular completo"
        outer.Shape = _closed_wire(
            [(0, 0, 0), (6000, 0, 0), (6000, 4000, 0), (3500, 4000, 0), (3500, 6000, 0), (0, 6000, 0)]
        )

        inner = doc.addObject("Part::Part2DObject", "AreaInterna")
        inner.Label = "Area interna"
        inner.Shape = _closed_wire(
            [(1000, 1000, 0), (3000, 1000, 0), (3000, 3000, 0), (1000, 3000, 0)]
        )

        copied = hvac_space.create_spaces_from_objects(
            [outer, inner], doc=doc, source_mode=hvac_space.SOURCE_MODE_COPY
        )
        doc.recompute()
        assert len(copied) == 2
        assert doc.getObject(outer.Name) is outer
        assert doc.getObject(inner.Name) is inner
        assert all(str(space.SourceMode) == hvac_space.SOURCE_MODE_COPY for space in copied)
        assert all(bool(space.AllowOverlap) for space in copied)

        overlap_point = App.Vector(2000, 2000, 0)
        assert all(hvac_space.space_contains_point(space, overlap_point) for space in copied)
        assert hvac_equipment._space_from_position(doc, overlap_point) == copied[1]

        copied_again = hvac_space.create_spaces_from_objects(
            [outer, inner], doc=doc, source_mode=hvac_space.SOURCE_MODE_COPY
        )
        assert [space.Name for space in copied_again] == [space.Name for space in copied]
        assert len(hvac_space.find_spaces(doc)) == 2

        # A linked copy can later be promoted to an autonomous converted space
        # without replacing the HVAC semantic object or its downstream links.
        promoted_name = copied[1].Name
        promoted = hvac_space.create_spaces_from_objects(
            [inner], doc=doc, source_mode=hvac_space.SOURCE_MODE_CONVERT
        )[0]
        assert promoted.Name == promoted_name
        assert doc.getObject("AreaInterna") is None
        assert promoted.BaseSpace is None
        assert hvac_space.space_contains_point(promoted, overlap_point)

        source_to_convert = doc.addObject("Part::Part2DObject", "AreaConvertir")
        source_to_convert.Label = "Servidor convertido"
        source_to_convert.Shape = Part.makePlane(4000, 3000, App.Vector(8000, 0, 0))
        converted = hvac_space.create_spaces_from_objects(
            [source_to_convert], doc=doc, source_mode=hvac_space.SOURCE_MODE_CONVERT
        )[0]
        converted_name = converted.Name
        doc.recompute()

        assert doc.getObject("AreaConvertir") is None
        assert converted.BaseSpace is None
        assert str(converted.SourceMode) == hvac_space.SOURCE_MODE_CONVERT
        assert converted.SourceObjectName == "AreaConvertir"
        assert abs(float(converted.Area) - 12.0) < 0.001
        assert hvac_space.space_contains_point(converted, App.Vector(9000, 1000, 0))
        assert hvac_label._label_position(converted) is not None
        assert hvac_equipment._space_center_point(converted) is not None
        assert hvac_space.cleanup_non_area_spaces(doc) == 0

        blocked_source = doc.addObject("Part::Part2DObject", "AreaConDependencia")
        blocked_source.Shape = Part.makePlane(1000, 1000, App.Vector(14000, 0, 0))
        dependent = doc.addObject("App::FeaturePython", "DependenciaExterna")
        dependent.addProperty("App::PropertyLink", "AreaSource")
        dependent.AreaSource = blocked_source
        blocked = hvac_space.conversion_blockers([blocked_source])
        assert blocked_source in blocked
        try:
            hvac_space.create_spaces_from_objects(
                [blocked_source], doc=doc, source_mode=hvac_space.SOURCE_MODE_CONVERT
            )
            raise AssertionError("Conversion with an external dependency should fail")
        except RuntimeError:
            pass
        assert doc.getObject(blocked_source.Name) is blocked_source

        doc.recompute()
        doc.saveAs(temp_path)
        App.closeDocument(DOC_NAME)

        reopened = App.openDocument(temp_path)
        reopened.recompute()
        persisted = reopened.getObject(converted_name)
        assert persisted is not None
        assert persisted.BaseSpace is None
        assert str(persisted.SourceMode) == hvac_space.SOURCE_MODE_CONVERT
        assert abs(float(persisted.Area) - 12.0) < 0.001
        assert hvac_space.space_contains_point(persisted, App.Vector(9000, 1000, 0))
        assert hvac_space.cleanup_non_area_spaces(reopened) == 0
        App.closeDocument(reopened.Name)
    finally:
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "copied": 2,
        "converted": 2,
        "overlap": True,
        "dependency_guard": True,
        "persisted": True,
    }


if __name__ == "__main__":
    print(run())
