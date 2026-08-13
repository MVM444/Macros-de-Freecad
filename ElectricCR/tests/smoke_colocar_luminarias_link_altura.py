# -*- coding: utf-8 -*-
"""Geometric smoke test for ColocarLuminarias_Link height selection."""

from pathlib import Path
import os
import runpy
import sys
import tempfile

import FreeCAD as App


REPO_ROOT = Path(__file__).resolve().parents[2]
MACRO_PATH = REPO_ROOT / "Iluminacion" / "ColocarLuminarias_Link.FCMacro"
if not MACRO_PATH.is_file():
    # Keep the source path with its real accented directory on Windows.
    candidates = list(REPO_ROOT.glob("Iluminaci*n/ColocarLuminarias_Link.FCMacro"))
    if not candidates:
        raise RuntimeError("No se encontro ColocarLuminarias_Link.FCMacro")
    MACRO_PATH = candidates[0]

for candidate in (REPO_ROOT, REPO_ROOT / "ElectricCR"):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)


def _assert_close(actual, expected, tolerance, message):
    if abs(float(actual) - float(expected)) > float(tolerance):
        raise AssertionError(
            "{}: actual={} esperado={} tolerancia={}".format(
                message, actual, expected, tolerance
            )
        )


def _linked_master(link):
    return getattr(link, "LinkedObject", None) or getattr(link, "Link", None)


namespace = runpy.run_path(str(MACRO_PATH), run_name="electriccr_luminaria_link_height_test")
load_registry = namespace["load_registry"]
get_crear_toma_uno = namespace["get_crear_toma_uno"]
ensure_link_master = namespace["ensure_link_master"]
insert_link_in_cell = namespace["insert_link_in_cell"]
resolve_settings = namespace["resolve_rectangle_luminaire_settings"]
run_macro = namespace["run"]
QtWidgets = namespace["QtWidgets"]

registry = load_registry()
key = "Luminaria 60x60"
if key not in (registry.get("types") or {}):
    raise AssertionError("El registro de prueba no contiene '{}'".format(key))

doc = App.newDocument("SmokeLuminariaLinkAltura")
rect = doc.addObject("Part::FeaturePython", "AreaPrueba")
rect.Label = "Area prueba"
rect.addProperty("App::PropertyString", "LightingTypeKey")
rect.LightingTypeKey = key
rect.addProperty("App::PropertyLength", "LightingMountHeight")
rect.LightingMountHeight = 3000.0
rect.addProperty("App::PropertyLength", "Length")
rect.Length = 1200.0
rect.addProperty("App::PropertyLength", "Height")
rect.Height = 1200.0
rect.addProperty("App::PropertyInteger", "Columns")
rect.Columns = 1
rect.addProperty("App::PropertyInteger", "Rows")
rect.Rows = 1

rect_key, active_key, active_height, active_mode = resolve_settings(
    rect,
    registry,
    selected_key="Luminaria LED Redonda 1000lm",
    selected_height=5000.0,
    selected_mode="Ambos",
    use_assigned_area_type=True,
)
if rect_key != key or active_key != key:
    raise AssertionError("No se conservo el tipo asignado al area")
_assert_close(active_height, 5000.0, 0.01, "La altura del dialogo fue reemplazada")


class _Dialog5000(object):
    def __init__(self, _registry, _parent=None):
        pass

    def exec_(self):
        return QtWidgets.QDialog.Accepted

    def selected_key(self):
        return "Luminaria LED Redonda 1000lm"

    def selected_prefix(self):
        return "LuminariaPrueba_"

    def selected_altura(self):
        return 5000.0

    def selected_mode(self):
        return "Ambos"

    def reuse_master(self):
        return True

    def use_assigned_area_type(self):
        return True

    def use_ceiling_module(self):
        return False

    def ceiling_module(self):
        return 600.0


run_globals = run_macro.__globals__
run_globals["PickTypeDialog"] = _Dialog5000
run_globals["collect_rectangles_from_selection"] = lambda: [rect]


class _HeadlessGui(object):
    @staticmethod
    def getMainWindow():
        return None


run_globals["Gui"] = _HeadlessGui
run_macro()
macro_links = [obj for obj in doc.Objects if obj.TypeId == "App::Link"]
if len(macro_links) != 1:
    raise AssertionError("La ejecucion real no creo exactamente una luminaria Link")
macro_master = _linked_master(macro_links[0])
if macro_master is None:
    raise AssertionError("La luminaria creada por run() no tiene maestro")
if str(macro_master.KeyRegistro) != key:
    raise AssertionError("run() no respeto el tipo asignado al area")
_assert_close(macro_master.AlturaRel, 5000.0, 0.01, "run() no respeto la altura")
_assert_close(macro_master.Shape.BoundBox.ZMin, 0.0, 2.0, "run() elevo el simbolo 2D")
_assert_close(macro_master.Shape.BoundBox.ZMax, 5100.0, 5.0, "run() dejo el 3D a 3000 mm")

crear_toma_uno = get_crear_toma_uno()
if crear_toma_uno is None:
    raise AssertionError("No se pudo cargar crear_toma_uno desde ElectricCR")

master_2500 = ensure_link_master(
    doc, crear_toma_uno, key, 2500.0, "Ambos", reuse=True
)
doc.recompute()
if master_2500 is None or master_2500.Shape.isNull():
    raise AssertionError("El maestro a 2500 mm no genero Shape")
_assert_close(master_2500.AlturaRel, 2500.0, 0.01, "AlturaRel maestro 2500")
zmin_2500 = float(master_2500.Shape.BoundBox.ZMin)
zmax_2500 = float(master_2500.Shape.BoundBox.ZMax)
_assert_close(zmin_2500, 0.0, 2.0, "El simbolo 2D no quedo en Z=0")

master_5000 = ensure_link_master(
    doc, crear_toma_uno, key, 5000.0, "Ambos", reuse=True
)
doc.recompute()
if master_5000 is None or master_5000.Shape.isNull():
    raise AssertionError("El maestro a 5000 mm no genero Shape")
_assert_close(master_5000.AlturaRel, 5000.0, 0.01, "AlturaRel maestro 5000")
zmin_5000 = float(master_5000.Shape.BoundBox.ZMin)
zmax_5000 = float(master_5000.Shape.BoundBox.ZMax)
_assert_close(zmin_5000, 0.0, 2.0, "El simbolo 2D elevado no quedo en Z=0")
_assert_close(
    zmax_5000 - zmax_2500,
    2500.0,
    5.0,
    "El modelo 3D no subio con la altura seleccionada",
)

link = insert_link_in_cell(
    doc,
    master=master_5000,
    prefix="LuminariaPrueba_",
    rect=rect,
    rect_pos=App.Vector(1000.0, 2000.0, 0.0),
    rect_rot=App.Rotation(),
    x_local=500.0,
    y_local=600.0,
    idx_global=1,
)
doc.recompute()
if _linked_master(link) is not master_5000:
    raise AssertionError("El App::Link no apunta al maestro de 5000 mm")
_assert_close(link.Placement.Base.z, 0.0, 0.01, "El Link elevo su Placement base")

temp_dir = tempfile.mkdtemp(prefix="electriccr_luminaria_altura_")
save_path = os.path.join(temp_dir, "smoke_luminaria_link_altura.FCStd")
master_name = master_5000.Name
link_name = link.Name
doc.recompute()
doc.saveAs(save_path)
App.closeDocument(doc.Name)

reopened = App.openDocument(save_path)
reopened.recompute()
restored_master = reopened.getObject(master_name)
restored_link = reopened.getObject(link_name)
if restored_master is None or restored_link is None:
    raise AssertionError("Faltan maestro o Link despues de reabrir")
_assert_close(restored_master.AlturaRel, 5000.0, 0.01, "Altura restaurada")
_assert_close(
    restored_master.Shape.BoundBox.ZMax,
    zmax_5000,
    5.0,
    "ZMax cambio despues de guardar y reabrir",
)
if _linked_master(restored_link) is not restored_master:
    raise AssertionError("El Link restaurado no apunta al maestro correcto")

print(
    "PASS ColocarLuminarias_Link altura: "
    "ZMin2500={:.3f} ZMax2500={:.3f} ZMin5000={:.3f} ZMax5000={:.3f}".format(
        zmin_2500, zmax_2500, zmin_5000, zmax_5000
    )
)

App.closeDocument(reopened.Name)
os.remove(save_path)
os.rmdir(temp_dir)
