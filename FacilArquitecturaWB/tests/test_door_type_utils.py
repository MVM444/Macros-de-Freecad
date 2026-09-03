"""Pure tests for native BIM door preset selection and override metadata."""

from __future__ import annotations

import sys
import types
import unittest


def _install_freecad_stub():
    if "FreeCAD" in sys.modules:
        return
    module = types.ModuleType("FreeCAD")
    module.Console = types.SimpleNamespace(
        PrintMessage=lambda _message: None,
        PrintWarning=lambda _message: None,
    )
    sys.modules["FreeCAD"] = module


_install_freecad_stub()

from FacilArquitecturaWB.core import door_type_utils as doors  # noqa: E402


class FakeObject:
    def __init__(self, ifc_type="Door", proxy_type="Window"):
        self.Name = "Door"
        self.Label = "Door"
        self.IfcType = ifc_type
        self.Proxy = types.SimpleNamespace(Type=proxy_type)
        self.Base = object()
        self.WindowParts = []
        self.Preset = 6
        self.Width = 900.0
        self.Height = 2100.0
        self.Hosts = []
        self.PropertiesList = []

    def addProperty(self, _prop_type, name, _group, _description):
        self.PropertiesList.append(name)


class PresetModule:
    WindowPresets = [
        "Fixed",
        "Simple door",
        "Glass door",
        "Opening only",
    ]


class DoorTypePureTests(unittest.TestCase):
    def test_runtime_preset_filter_accepts_installed_strings(self):
        self.assertEqual(
            ["Simple door", "Glass door"],
            doors.native_door_presets(PresetModule),
        )

    def test_runtime_preset_filter_tolerates_legacy_tuple_entries(self):
        module = types.SimpleNamespace(
            WindowPresets=[("Simple door", object()), ("Fixed", object())]
        )
        self.assertEqual(["Simple door"], doors.native_door_presets(module))

    def test_native_arch_door_is_accepted(self):
        accepted, reason = doors.door_compatibility(FakeObject())
        self.assertTrue(accepted, reason)

    def test_window_and_opening_element_are_rejected(self):
        self.assertFalse(doors.door_compatibility(FakeObject("Window"))[0])
        self.assertFalse(doors.door_compatibility(FakeObject("Opening Element"))[0])

    def test_generic_part_with_ifc_door_is_rejected(self):
        self.assertFalse(doors.door_compatibility(FakeObject("Door", "Feature"))[0])

    def test_special_fa_double_door_is_rejected_without_damage(self):
        obj = FakeObject()
        obj.FA_GeneratedBy = doors.DOUBLE_DOOR_GENERATOR
        accepted, reason = doors.door_compatibility(obj)
        self.assertFalse(accepted)
        self.assertIn("puerta doble", reason)

    def test_source_override_round_trip_is_per_geometry_index(self):
        source = FakeObject(ifc_type="", proxy_type="")
        door = FakeObject()
        door.FA_SourceSketch = source
        door.FA_SourceGeometryIndex = 4

        self.assertTrue(doors.record_source_door_override(door, "Glass door"))
        self.assertEqual({"4": "Glass door"}, doors.source_door_type_overrides(source))
        self.assertEqual(
            "Glass door",
            doors.door_preset_override(
                source, 4, presets=["Simple door", "Glass door"]
            ),
        )
        self.assertEqual(
            "",
            doors.door_preset_override(source, 3, presets=["Simple door", "Glass door"]),
        )


if __name__ == "__main__":
    unittest.main()


class DoorTypeTableResolutionTests(unittest.TestCase):
    def test_catalog_includes_double_and_installed_presets(self):
        catalog = doors.door_type_catalog(PresetModule)
        self.assertEqual("DoubleDoor", catalog[0]["DoorType"])
        names = [item["DoorType"] for item in catalog]
        self.assertIn("Simple door", names)
        self.assertIn("Glass door", names)

    def test_arbitrary_user_label_can_reference_installed_preset(self):
        resolved = doors.resolve_door_type(
            door_type="Puerta Oficina",
            type_source="native_preset",
            type_ref="Glass door",
            preset_module=PresetModule,
        )
        self.assertEqual("Puerta Oficina", resolved["DoorType"])
        self.assertEqual("Glass door", resolved["Preset"])
        self.assertEqual(1, resolved["LeafCount"])

    def test_double_type_uses_explicit_factory(self):
        resolved = doors.resolve_door_type(
            door_type="Puerta doble acceso",
            type_source="fa_double",
            type_ref=doors.DOUBLE_DOOR_SPEC_ID,
            leaf_count=2,
            preset_module=PresetModule,
        )
        self.assertEqual("fa_double", resolved["TypeSource"])
        self.assertEqual(doors.DOUBLE_DOOR_SPEC_ID, resolved["TypeRef"])
        self.assertGreaterEqual(resolved["LeafCount"], 2)

    def test_unknown_type_is_rejected_instead_of_substitution(self):
        with self.assertRaises(Exception):
            doors.resolve_door_type(
                door_type="Tipo inexistente",
                type_source="native_preset",
                preset_module=PresetModule,
            )
