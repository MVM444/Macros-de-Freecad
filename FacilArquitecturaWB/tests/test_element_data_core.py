import json
import sys
import unittest

from FacilArquitecturaWB.core import element_data_core as core


def geom(index=0, x=500.0, y=0.0, length=1000.0, angle=0.0, sketch="SketchVentanas"):
    return {
        "SourceSketch": sketch,
        "GeometryIndex": index,
        "CenterX": x,
        "CenterY": y,
        "Length": length,
        "AngleDeg": angle,
    }


def record(**changes):
    data = {
        "ElementID": "V-001",
        "SourceSketch": "SketchVentanas",
        "GeometryIndex": 0,
        "CenterX": 500.0,
        "CenterY": 0.0,
        "Length": 1000.0,
        "AngleDeg": 0.0,
        "Height": 1200.0,
        "SillHeight": 900.0,
        "Preset": "Open 1-pane",
        "Opening": 0.0,
        "Frame": 40.0,
        "Offset": 0.0,
    }
    data.update(changes)
    return data


class ElementDataCoreTests(unittest.TestCase):
    def test_serialization_round_trip_is_json_compatible(self):
        payload = core.serialize_records([record()])
        encoded = json.dumps(payload)
        restored = core.deserialize_records(encoded)
        self.assertEqual("V-001", restored[0]["ElementID"])
        self.assertEqual(core.SCHEMA_VERSION, restored[0]["SchemaVersion"])

    def test_empty_template(self):
        payload = core.serialize_records([])
        self.assertEqual([], payload["categories"]["windows"])
        report = core.validate_records("windows", [], [])
        self.assertEqual(0, report["record_count"])

    def test_matches_by_source_and_geometry_index(self):
        report = core.validate_records("windows", [record()], [geom()])
        self.assertEqual("MATCH", report["entries"][0]["status"])

    def test_changed_index_recovers_by_geometric_signature(self):
        report = core.validate_records("windows", [record(GeometryIndex=7)], [geom(index=2)])
        self.assertEqual("CAMBIO", report["entries"][0]["status"])
        self.assertEqual(2, report["entries"][0]["matched_geometry"]["GeometryIndex"])

    def test_changed_width_is_cambio_and_destination_width_is_planned(self):
        plan = core.plan_application("windows", [record()], [geom(length=1200.0)])
        self.assertEqual("CAMBIO", plan["plans"][0]["status"])
        self.assertEqual(1200.0, plan["plans"][0]["geometry"]["Length"])
        self.assertEqual(1200.0, plan["plans"][0]["record"]["Height"])

    def test_outside_tolerance_is_no_match(self):
        report = core.validate_records("windows", [record()], [geom(x=3000.0)])
        self.assertEqual("NO_MATCH", report["entries"][0]["status"])

    def test_equivalent_candidates_are_ambiguous(self):
        row = record(SourceSketch="", GeometryIndex=0)
        geometry = [geom(sketch="A"), geom(sketch="B")]
        report = core.validate_records("windows", [row], geometry)
        self.assertEqual("AMBIGUO", report["entries"][0]["status"])
        self.assertEqual([], core.plan_application("windows", [row], geometry)["plans"])

    def test_transfer_properties_are_preserved(self):
        normalized = core.build_table_data(
            "windows",
            [record(Height=1450, SillHeight=780, Preset="Sliding 2-pane", Frame=55, Offset=12)],
        )[0]
        self.assertEqual(1450.0, normalized["Height"])
        self.assertEqual(780.0, normalized["SillHeight"])
        self.assertEqual("Sliding 2-pane", normalized["Preset"])
        self.assertEqual(55.0, normalized["Frame"])

    def test_invalid_rows_are_not_planned(self):
        plan = core.plan_application("windows", [record(Height=-1)], [geom()])
        self.assertEqual([], plan["plans"])
        self.assertEqual("NO_MATCH", plan["validation"]["entries"][0]["status"])

    def test_duplicate_element_ids_are_ambiguous(self):
        rows = [record(), record(GeometryIndex=1, CenterX=1600.0)]
        report = core.validate_records("windows", rows, [geom(), geom(index=1, x=1600.0)])
        self.assertEqual("AMBIGUO", report["entries"][0]["status"])
        self.assertEqual("AMBIGUO", report["entries"][1]["status"])

    def test_two_rows_cannot_claim_the_same_geometry(self):
        rows = [record(ElementID="V-001"), record(ElementID="V-002")]
        report = core.validate_records("windows", rows, [geom()])
        self.assertEqual(["AMBIGUO", "AMBIGUO"], [item["status"] for item in report["entries"]])
        self.assertEqual([], core.plan_application("windows", rows, [geom()])["plans"])

    def test_module_has_no_gui_dependency(self):
        self.assertNotIn("FreeCADGui", core.__dict__)
        self.assertNotIn("PySide", core.__dict__)


if __name__ == "__main__":
    unittest.main()


class ElementDataDoorCoreTests(unittest.TestCase):
    def door_record(self, **changes):
        data = {
            "ElementID": "P-001",
            "SourceSketch": "SketchPuertas",
            "GeometryIndex": 0,
            "CenterX": 500.0,
            "CenterY": 0.0,
            "Length": 900.0,
            "AngleDeg": 0.0,
            "Height": 2100.0,
            "DoorType": "Simple door",
            "TypeSource": "native_preset",
            "TypeRef": "Simple door",
            "Preset": "Simple door",
            "LeafCount": 1,
            "HingeEndpoint": "START",
            "HingePointX": 50.0,
            "HingePointY": 0.0,
            "OpeningSide": "LEFT",
            "OpensInward": True,
            "Opening": 100.0,
            "IfcType": "Door",
        }
        data.update(changes)
        return data

    def door_geom(self, **changes):
        data = {
            "SourceSketch": "SketchPuertas",
            "GeometryIndex": 0,
            "CenterX": 500.0,
            "CenterY": 0.0,
            "Length": 900.0,
            "AngleDeg": 0.0,
        }
        data.update(changes)
        return data

    def test_door_serialization_preserves_hinge_and_swing(self):
        payload = core.serialize_records([self.door_record()], category="doors")
        restored = core.deserialize_records(json.dumps(payload), category="doors")[0]
        self.assertEqual("P-001", restored["ElementID"])
        self.assertEqual("START", restored["HingeEndpoint"])
        self.assertEqual("LEFT", restored["OpeningSide"])
        self.assertIs(restored["OpensInward"], True)
        self.assertEqual(2100.0, restored["Height"])

    def test_double_door_type_is_json_compatible(self):
        row = core.normalize_record(
            "doors",
            self.door_record(
                DoorType="DoubleDoor",
                TypeSource="fa_double",
                TypeRef="architecture.door.double_leaf.glazed.europa",
                Preset="",
                LeafCount=2,
                HingeEndpoint="BOTH",
            ),
        )
        self.assertEqual(2, row["LeafCount"])
        self.assertEqual("BOTH", row["HingeEndpoint"])
        self.assertEqual("fa_double", row["TypeSource"])

    def test_door_width_change_is_cambio(self):
        plan = core.plan_application(
            "doors",
            [self.door_record()],
            [self.door_geom(Length=1000.0)],
        )
        self.assertEqual("CAMBIO", plan["plans"][0]["status"])
        self.assertEqual(1000.0, plan["plans"][0]["geometry"]["Length"])

    def test_door_duplicate_geometry_is_ambiguous(self):
        rows = [
            self.door_record(ElementID="P-001"),
            self.door_record(ElementID="P-002"),
        ]
        report = core.validate_records("doors", rows, [self.door_geom()])
        self.assertEqual(["AMBIGUO", "AMBIGUO"], [x["status"] for x in report["entries"]])

    def test_invalid_door_type_is_not_planned(self):
        plan = core.plan_application(
            "doors",
            [self.door_record(DoorType="", Preset="", TypeRef="")],
            [self.door_geom()],
        )
        self.assertEqual([], plan["plans"])
        self.assertEqual("NO_MATCH", plan["validation"]["entries"][0]["status"])

    def test_door_aliases_normalize(self):
        row = core.normalize_record(
            "puertas",
            self.door_record(HingeEndpoint="fin", OpeningSide="derecha", OpensInward="si"),
        )
        self.assertEqual("doors", row["Category"])
        self.assertEqual("END", row["HingeEndpoint"])
        self.assertEqual("RIGHT", row["OpeningSide"])
        self.assertIs(row["OpensInward"], True)
