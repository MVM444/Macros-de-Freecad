"""Tests for X3D walk-navigation defaults."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
import math
import types

from GameEngineExportWB.core import exporter_x3d
from GameEngineExportWB.core import gamestart


class NavigationTests(unittest.TestCase):
    def test_walk_navigation_is_locked_and_uses_human_step_height(self):
        cfg = exporter_x3d._normalize_navigation_cfg(
            {"navigation": {"speed": 2.0, "eye_height_mm": 1600.0}}
        )
        scene = ET.Element("Scene")
        exporter_x3d._ensure_navigation(scene, lambda tag: tag, cfg)

        navigation = scene.find("NavigationInfo")
        self.assertIsNotNone(navigation)
        self.assertEqual('"WALK"', navigation.attrib["type"])
        self.assertEqual("0.25 1.600 0.350", navigation.attrib["avatarSize"])

    def test_walk_lock_can_be_disabled_explicitly(self):
        cfg = exporter_x3d._normalize_navigation_cfg(
            {"navigation": {"walk_only": False, "step_height_mm": 200.0}}
        )
        scene = ET.Element("Scene")
        exporter_x3d._ensure_navigation(scene, lambda tag: tag, cfg)

        navigation = scene.find("NavigationInfo")
        self.assertEqual('"WALK" "ANY"', navigation.attrib["type"])
        self.assertEqual("0.25 1.600 0.200", navigation.attrib["avatarSize"])

    def test_gamestart_keeps_freecad_rotation_angle_in_radians(self):
        axis = types.SimpleNamespace(Length=1.0, x=1.0, y=0.0, z=0.0)
        placement = types.SimpleNamespace(
            Rotation=types.SimpleNamespace(Axis=axis, Angle=math.pi / 2.0)
        )

        orientation = gamestart._placement_orientation(placement)

        self.assertAlmostEqual(math.pi / 2.0, orientation[3])

    def test_walk_ground_proxy_is_invisible_and_matches_model_bounds(self):
        scene = ET.Element("Scene")
        transform = ET.SubElement(
            scene,
            "Transform",
            {"DEF": exporter_x3d.TRANSFORM_DEF},
        )
        ET.SubElement(
            transform,
            "Coordinate",
            {"point": "1000 2000 -150, 5000 8000 3000"},
        )
        cfg = exporter_x3d._normalize_navigation_cfg(
            {"navigation": {"ground_margin_mm": 0.0}}
        )

        exporter_x3d._ensure_walk_ground_collision(scene, lambda tag: tag, cfg)

        collision = scene.find("Collision")
        self.assertIsNotNone(collision)
        self.assertEqual(exporter_x3d.GROUND_COLLISION_DEF, collision.attrib["DEF"])
        proxy = collision.find("Transform")
        self.assertEqual("proxy", proxy.attrib["containerField"])
        self.assertEqual("3.000000 -0.100000 -5.000000", proxy.attrib["translation"])
        self.assertEqual("4.000000 0.200000 6.000000", proxy.find("Shape/Box").attrib["size"])

    def test_walk_ground_proxy_is_idempotent(self):
        scene = ET.Element("Scene")
        transform = ET.SubElement(
            scene,
            "Transform",
            {"DEF": exporter_x3d.TRANSFORM_DEF},
        )
        ET.SubElement(transform, "Coordinate", {"point": "0 0 0, 1000 1000 0"})
        cfg = exporter_x3d._normalize_navigation_cfg(None)

        exporter_x3d._ensure_walk_ground_collision(scene, lambda tag: tag, cfg)
        exporter_x3d._ensure_walk_ground_collision(scene, lambda tag: tag, cfg)

        proxies = [
            node
            for node in scene.findall("Collision")
            if node.attrib.get("DEF") == exporter_x3d.GROUND_COLLISION_DEF
        ]
        self.assertEqual(1, len(proxies))


if __name__ == "__main__":
    unittest.main()
