"""Herramienta de demostracion automatica para Facil Arquitectura.

Nombre: cmd_demo_building.py
Proposito: crear desde cero una casa BIM pequena y completa para demostrar el
flujo del Workbench sin depender de archivos previos.
Funcion principal: materializar una especificacion generada por
``core.demo_building_core`` en un documento nuevo: Sketches -> piso -> muros ->
puertas/ventanas -> recintos/Espacios BIM -> cielorraso 600x600 -> techo BIM por ejes.
Instrucciones relevantes para futuras modificaciones:
- Mantener la generacion geometrica aleatoria en demo_building_core.py, sin Qt.
- Reutilizar las utilidades existentes de muros, aberturas, recintos, cielos, piso y techo; no
  crear implementaciones BIM paralelas.
- Abrir siempre un documento nuevo para no tocar trabajo real del usuario.
- La misma semilla debe producir la misma especificacion.
- Mantener el modo completo de una planta en una sola transaccion; la demo de dos
  pisos usa fases confirmadas para proteger hosts BIM y el modo guiado una transaccion por paso.
- El modo guiado debe reutilizar exactamente las mismas operaciones de materializacion
  y la misma especificacion JSON que el modo completo.
- Conservar salida 2D mediante los Sketches fuente y el Draft Rectangle de techo.
- Los paneles de Demo guiada usan un objectName estable y deben limpiarse por MainWindow en cada registro/hot restart; nunca confiar solo en globals Python para su ciclo de vida.
FreeCAD objetivo: 1.1.3.
Version: 0.9.4
Fecha y hora: 2026-09-14 20:00 America/Costa_Rica
"""

from __future__ import annotations

import json
import os

import Draft
import FreeCAD as App
import FreeCADGui
import Part
from PySide import QtCore, QtGui, QtWidgets

from .. import i18n

from ..core.bim_structure_utils import add_to_container, ensure_bim_structure
from ..core.bim_utils import (
    create_walls_from_centerline_sketches,
    prepare_sketches_as_wall_centerlines,
)
from ..core.command_errors import handle_command_exception
from ..core.demo_building_core import CANONICAL_SEED, build_demo_spec, build_two_storey_demo_spec, spec_summary
from ..core.demo_guided_core import guided_progress_text, guided_step, guided_steps, guided_total_steps
from ..core.fa_stair_core import plan_angled_stair, plan_stair_clearance
from ..core.stair_freecad_adapter import (
    build_stair_context,
    build_ceiling_finish_exclusion_zones,
    create_clearance_previews,
    create_native_slab_opening,
    create_native_stair,
    create_stair_opening_liner,
    mark_clearance_plans_applied,
)
from ..core.opening_utils import create_openings_from_centerlines
from ..core.room_utils import create_closed_room_sketch
from ..core.space_utils import create_bim_spaces
from ..core.process_feedback import long_process_message
from ..ui.process_feedback import LongOperationFeedback
from ..core.ceiling_utils import create_modular_ceilings
from ..core.parameters import ensure_parameter_sheet
from ..core.project_structure import ensure_group, msg, set_prop
from ..core.reloadable_command import ReloadableCommandProxy
from ..core.site_floor_utils import create_site_floor_from_sketches
from .cmd_roof_axis_prototype import create_roof_from_rectangle_programmatic
from .cmd_model_diagnostic import generate_report, show_report_dialog

ICON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons")
)
ICON_PATH = os.path.join(ICON_DIR, "demo_building.svg").replace(os.sep, "/")


def _guided_icon_path(file_name):
    """Resolve one declared guided-step SVG without allowing path traversal."""
    safe_name = os.path.basename(str(file_name or "demo_building.svg"))
    return os.path.join(ICON_DIR, safe_name).replace(os.sep, "/")


def _guided_meta_text(meta, key, default=""):
    """Return one guided-step label in the active FreeCAD language."""
    data = dict(meta or {})
    if i18n.current_language() == "en":
        value = data.get(str(key) + "_en")
        if value:
            return str(value)
    value = data.get(key)
    return str(value if value not in (None, "") else default)
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/DemoBuilding"
GENERATOR = "FA_DemoBuilding"
LOG = "[FA DEMO] "
DEMO_COMMAND_VERSION = "0.9.4"


def _log(text):
    App.Console.PrintMessage(LOG + str(text) + "\n")


def _qt_enum(name, scoped_name=None):
    """Resolve Qt5/Qt6 enum aliases used by FreeCAD 1.1.x builds."""
    direct = getattr(QtCore.Qt, name, None)
    if direct is not None:
        return direct
    scope = getattr(QtCore.Qt, str(scoped_name or ""), None)
    if scope is not None:
        value = getattr(scope, name, None)
        if value is not None:
            return value
    raise AttributeError("Qt enum no disponible: %s" % name)


class DemoBuildingDialog(QtWidgets.QDialog):
    """Minimal options for the canonical/random reproducible demo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.params = App.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle(i18n.bi("FA Demo edificio", "FA Building Demo"))
        self.setMinimumWidth(390)

        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(
            i18n.bi(
                "Crea un documento nuevo con Sketches, piso, muros, puertas, ventanas, Espacios BIM, cielo modular 600x600 y techo BIM. No modifica el documento actual.",
                "Creates a new document with Sketches, floor, walls, doors, windows, BIM Spaces, 600x600 modular ceiling, and BIM roof. It does not modify the current document.",
            )
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        purpose = QtWidgets.QLabel(i18n.bi(
            "La Demo sirve para aprender y comprobar las herramientas. No valida que cualquier DWG pueda procesarse automaticamente.",
            "The Demo is for learning and testing the tools. It does not validate that any DWG can be processed automatically.",
        ))
        purpose.setWordWrap(True)
        layout.addWidget(purpose)

        form = QtWidgets.QFormLayout()
        self.mode = QtWidgets.QComboBox()
        self.mode.addItem(i18n.bi("Casa fija 6 x 8 m", "Fixed 6 x 8 m house"), "fixed")
        self.mode.addItem(i18n.bi("Casa aleatoria reproducible", "Reproducible random house"), "random")
        self.mode.addItem(i18n.bi("Casa fija 2 pisos 6 x 8 m", "Fixed two-storey 6 x 8 m house"), "two_storey")
        previous_mode = self.params.GetString("mode", "fixed")
        self.mode.setCurrentIndex({"fixed": 0, "random": 1, "two_storey": 2}.get(previous_mode, 0))
        form.addRow(i18n.bi("Modo", "Mode"), self.mode)

        self.seed = QtWidgets.QSpinBox()
        self.seed.setRange(0, 2147483647)
        self.seed.setValue(self.params.GetInt("seed", 12345))
        self.seed.setToolTip(i18n.bi("La misma semilla genera exactamente la misma casa aleatoria.", "The same seed generates exactly the same random house."))
        form.addRow(i18n.bi("Semilla", "Seed"), self.seed)

        self.execution = QtWidgets.QComboBox()
        self.execution.addItem(i18n.bi("Generar edificio completo", "Generate complete building"), "immediate")
        self.execution.addItem(i18n.bi("Demostracion guiada paso a paso", "Guided step-by-step demo"), "guided")
        # Build .3 migrates the old complete-generation default exactly once.
        # After migration, the user's explicit choice is persisted normally.
        if self.params.GetInt("execution_default_profile", 0) < 2:
            self.params.SetString("execution", "guided")
            self.params.SetInt("execution_default_profile", 2)
        previous_execution = self.params.GetString("execution", "guided")
        self.execution.setCurrentIndex(0 if previous_execution == "immediate" else 1)
        self.execution.setToolTip(
            i18n.bi("El modo guiado usa la misma casa y las mismas herramientas, pero detiene la construccion entre etapas.", "Guided mode uses the same house and tools, but pauses construction between stages.")
        )
        form.addRow(i18n.bi("Ejecucion", "Execution"), self.execution)
        layout.addLayout(form)

        self.preview = QtWidgets.QLabel("")
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.mode.currentIndexChanged.connect(self._refresh)
        self.seed.valueChanged.connect(self._refresh)
        self._refresh()

    def _values(self):
        mode = str(self.mode.currentData() or "fixed")
        randomized = mode == "random"
        seed = int(self.seed.value()) if randomized else CANONICAL_SEED
        return mode, randomized, seed

    def _refresh(self):
        mode, randomized, seed = self._values()
        self.seed.setEnabled(randomized)
        # The existing guided 14-step player is intentionally preserved for
        # single-storey demos. Multi-level guided playback will be a separate
        # extension after the immediate two-storey case is validated in FreeCAD.
        if mode == "two_storey":
            self.execution.setCurrentIndex(0)
            self.execution.setEnabled(False)
        else:
            self.execution.setEnabled(True)
        try:
            spec = build_two_storey_demo_spec() if mode == "two_storey" else build_demo_spec(seed, randomized)
            self.preview.setText(spec_summary(spec))
        except Exception as exc:
            self.preview.setText(i18n.bi("Configuracion invalida: %s" % exc, "Invalid configuration: %s" % exc))

    def values(self):
        mode, randomized, seed = self._values()
        execution = "immediate" if mode == "two_storey" else str(self.execution.currentData() or "guided")
        self.params.SetString("mode", mode)
        self.params.SetString("execution", execution)
        if randomized:
            self.params.SetInt("seed", int(seed))
        return {
            "mode": mode,
            "randomized": bool(randomized),
            "seed": int(seed),
            "execution": execution,
        }


def _unique_document_name(base):
    clean = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(base))
    clean = clean.strip("_") or "FA_Demo_Casa"
    existing = set((App.listDocuments() or {}).keys())
    if clean not in existing:
        return clean
    index = 2
    while "%s_%d" % (clean, index) in existing:
        index += 1
    return "%s_%d" % (clean, index)


def _new_demo_document(spec):
    base = "FA_Demo_Casa_%s" % (str(spec["seed"]) if spec["randomized"] else "6x8")
    name = _unique_document_name(base)
    doc = App.newDocument(name)
    doc.Label = "%s | seed %d" % (spec["name"], int(spec["seed"]))
    return doc


def _make_sketch(doc, name, label, segments, z_mm=0.0):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    sketch.Label = label
    for segment in segments:
        x1, y1 = map(float, segment["start_mm"])
        x2, y2 = map(float, segment["end_mm"])
        sketch.addGeometry(
            Part.LineSegment(App.Vector(x1, y1, 0.0), App.Vector(x2, y2, 0.0)),
            False,
        )
    # Multinivel: la geometria fuente nace directamente en su cota global.
    # No depende de que un BuildingPart traslade hijos agregados posteriormente.
    placement = sketch.Placement
    placement.Base.z = float(z_mm)
    sketch.Placement = placement
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Generador",
        GENERATOR,
    )
    return sketch


def _tag_opening_source(sketch, kind):
    singular = "door" if kind == "door" else "window"
    plural = "doors" if kind == "door" else "windows"
    set_prop(sketch, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", singular + "_centerlines")
    set_prop(sketch, "App::PropertyString", "FA_CenterlineKind", "FacilArquitectura", "Tipo de eje", plural)
    set_prop(sketch, "App::PropertyString", "FA_ElementType", "FacilArquitectura", "Tipo de elemento", singular)
    return sketch


def _make_aux_group(doc, level):
    group = doc.addObject("App::DocumentObjectGroup", "FA_DemoSources")
    group.Label = "Demo - Fuentes 2D y control"
    add_to_container(level, group)
    set_prop(group, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATOR)
    set_prop(group, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "demo_sources")
    return group


def _make_controller(doc, group, spec, execution_mode="immediate"):
    ctrl = doc.addObject("App::FeaturePython", "FA_DemoBuilding")
    ctrl.Label = "Control demo edificio"
    set_prop(ctrl, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATOR)
    set_prop(ctrl, "App::PropertyInteger", "Seed", "Demo", "Semilla reproducible", int(spec["seed"]))
    set_prop(ctrl, "App::PropertyBool", "Randomized", "Demo", "Usa modo aleatorio", bool(spec["randomized"]))
    set_prop(ctrl, "App::PropertyString", "SpecificationJSON", "Demo", "Especificacion JSON reproducible", json.dumps(spec, sort_keys=True, separators=(",", ":")))
    set_prop(ctrl, "App::PropertyString", "Description", "Demo", "Descripcion", spec_summary(spec))
    set_prop(ctrl, "App::PropertyString", "ExecutionMode", "Demo guiada", "Modo de ejecucion", str(execution_mode))
    set_prop(ctrl, "App::PropertyInteger", "CurrentStep", "Demo guiada", "Paso actual", 0)
    set_prop(ctrl, "App::PropertyInteger", "TotalSteps", "Demo guiada", "Cantidad total de pasos", guided_total_steps())
    set_prop(ctrl, "App::PropertyString", "PlaybackState", "Demo guiada", "Estado del reproductor", "ready")
    set_prop(ctrl, "App::PropertyString", "LastCompletedStep", "Demo guiada", "Ultimo paso completado", "")
    set_prop(ctrl, "App::PropertyString", "LastError", "Demo guiada", "Ultimo error", "")
    set_prop(ctrl, "App::PropertyBool", "AutoCamera", "Demo guiada", "Encuadre automatico", True)
    set_prop(ctrl, "App::PropertyString", "StepPlanJSON", "Demo guiada", "Guion JSON", json.dumps(guided_steps(), sort_keys=True, separators=(",", ":")))
    group.addObject(ctrl)
    return ctrl



def _sync_demo_parameter_sheet(sheet, spec):
    """Make the generic project parameter sheet reflect this demo document.

    The caller must recompute the document after ``ensure_parameter_sheet`` so
    newly written cells/aliases are queryable. Returns ``(updated, total)`` to
    make synchronization observable without turning the Spreadsheet into a
    hidden source of geometry.
    """
    values = {
        "building_width_mm": float(spec["footprint"]["width_mm"]),
        "building_depth_mm": float(spec["footprint"]["depth_mm"]),
        "wall_height_mm": float(spec["walls"]["height_mm"]),
        "ext_wall_thickness_mm": float(spec["walls"]["exterior_thickness_mm"]),
        "int_wall_thickness_mm": float(spec["walls"]["interior_thickness_mm"]),
        "door_height_mm": float(spec["openings"]["door_height_mm"]),
        "window_sill_mm": float(spec["openings"]["window_sill_mm"]),
        "window_height_mm": float(spec["openings"]["window_height_mm"]),
        "slab_thickness_mm": float(spec["floor"]["thickness_mm"]),
        "floor_level_mm": float(spec["floor"]["top_z_mm"]),
    }
    pending = dict(values)
    updated = 0
    for row in range(2, 200):
        try:
            key = str(sheet.get("A%d" % row) or "").strip()
        except Exception:
            key = ""
        if key not in pending:
            continue
        sheet.set("B%d" % row, str(pending.pop(key)))
        updated += 1
        if not pending:
            break
    if pending:
        _log("Parametros demo no encontrados en Spreadsheet despues de recomputar: %s" % ", ".join(sorted(pending)))
    else:
        _log("Parametros demo sincronizados: %d/%d" % (updated, len(values)))
    return updated, len(values)


def _validate_recomputed_footprint(sketch, spec):
    """Validate the exterior Sketch Shape only after document recompute."""
    shape = getattr(sketch, "Shape", None)
    bbox = getattr(shape, "BoundBox", None)
    if bbox is None:
        raise RuntimeError("El Sketch exterior no produjo Shape/BoundBox despues de recomputar.")
    actual_w = float(bbox.XMax) - float(bbox.XMin)
    actual_d = float(bbox.YMax) - float(bbox.YMin)
    expected_w = float(spec["footprint"]["width_mm"])
    expected_d = float(spec["footprint"]["depth_mm"])
    if actual_w < 500.0 or actual_d < 500.0:
        raise RuntimeError(
            "El Sketch exterior no se recomputo correctamente: %.1f x %.1f mm."
            % (actual_w, actual_d)
        )
    if abs(actual_w - expected_w) > 1.0 or abs(actual_d - expected_d) > 1.0:
        raise RuntimeError(
            "Huella 2D inesperada despues de recomputar: %.1f x %.1f mm; esperada %.1f x %.1f mm."
            % (actual_w, actual_d, expected_w, expected_d)
        )
    _log("Fuentes 2D recomputadas | huella exterior=%.1f x %.1f mm" % (actual_w, actual_d))



def _make_roof_rectangle(doc, group, spec, base_z_mm=0.0):
    width = float(spec["footprint"]["width_mm"])
    depth = float(spec["footprint"]["depth_mm"])
    z = float(base_z_mm) + float(spec["walls"]["height_mm"])
    placement = App.Placement(App.Vector(0.0, 0.0, z), App.Rotation())
    maker = getattr(Draft, "make_rectangle", None) or getattr(Draft, "makeRectangle", None)
    if maker is None:
        raise RuntimeError("Draft no expone makeRectangle/make_rectangle.")
    try:
        rect = maker(width, depth, placement=placement, face=False)
    except TypeError:
        rect = maker(width, depth, placement=placement)
        if hasattr(rect, "MakeFace"):
            rect.MakeFace = False
    rect.Label = "Huella techo - Demo"
    set_prop(rect, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATOR)
    set_prop(rect, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "roof_footprint")
    group.addObject(rect)
    doc.recompute()
    return rect


def _roof_settings(spec):
    roof = spec["roof"]
    return {
        "pitch_deg": float(roof["pitch_deg"]),
        "ridge_mode": "long_side",
        "support_mode": "walls_if_consistent",
        "truss_spacing_mm": float(roof["truss_spacing_mm"]),
        "truss_distribution_mode": "fixed",
        "truss_round_step_mm": 100.0,
        "truss_support_xy_mode": "walls_if_available",
        "truss_support_adjust_mm": 0.0,
        "truss_support_edge_tolerance_mm": 1000.0,
        "truss_height_start_mm": float(roof["truss_height_start_mm"]),
        "purlin_spacing_mm": float(roof["purlin_spacing_mm"]),
        "purlin_distribution_mode": "fixed",
        "purlin_round_step_mm": 50.0,
        "purlin_start_offset_mm": 200.0,
        "purlin_end_offset_mm": 200.0,
        "purlin_width_mm": float(roof["purlin_width_mm"]),
        "purlin_height_mm": float(roof["purlin_height_mm"]),
        "roof_thickness_mm": float(roof["thickness_mm"]),
        "overhang_mm": float(roof["overhang_mm"]),
    }



def _ceiling_options(spec):
    ceiling = spec["ceiling"]
    return {
        "module_mm": float(ceiling["module_mm"]),
        "ceiling_elevation_mm": float(ceiling["elevation_mm"]),
        "panel_thickness_mm": float(ceiling["panel_thickness_mm"]),
        "joint_gap_mm": float(ceiling["joint_gap_mm"]),
        "alignment_tolerance_mm": float(ceiling["alignment_tolerance_mm"]),
        "align_to_luminaires": False,
        "replace_previous": True,
    }


class DemoBuildingSession:
    """Stateful FreeCAD adapter shared by immediate and guided execution."""

    def __init__(
        self,
        spec,
        execution_mode="immediate",
        doc=None,
        building=None,
        level_name="Nivel 00",
        level_elevation_mm=0.0,
        geometry_z_offset_mm=0.0,
        create_site=True,
        create_controller=True,
        name_suffix="",
        create_level_if_label_missing=False,
        ceiling_namespace="",
    ):
        self.spec = spec
        self.execution_mode = str(execution_mode or "immediate")
        self.doc = doc if doc is not None else _new_demo_document(spec)
        self.level_name = str(level_name or "Nivel 00")
        self.level_elevation_mm = float(level_elevation_mm)
        self.geometry_z_offset_mm = float(geometry_z_offset_mm)
        self.create_site = bool(create_site)
        self.create_controller = bool(create_controller)
        self.name_suffix = str(name_suffix or "")
        self.create_level_if_label_missing = bool(create_level_if_label_missing)
        self.ceiling_namespace = str(ceiling_namespace or "").strip()
        self.current_step = 0
        self.parameter_sheet = None
        self.building = building
        self.level = None
        self.sources_group = None
        self.controller = None
        self.exterior_sketch = None
        self.interior_sketch = None
        self.door_sketch = None
        self.window_sketch = None
        self.floor_result = None
        self.walls = []
        self.doors = []
        self.windows = []
        self.room_sketch = None
        self.room_topology = None
        self.space_result = None
        self.spaces = []
        self.ceiling_result = None
        self.ceiling_exclusion_zones = []
        self.ceiling_exclusion_owner = None
        self.ceiling_exclusion_reason = ""
        self.roof_rectangle = None
        self.roof_result = None
        # Guided-mode presentation is view-only. Geometry and document properties
        # remain untouched while Sketch sources are being explained.
        self._guided_view_state = {}
        self._guided_presentation_step = ""

    def _update_controller(self, state=None, error=None, auto_camera=None):
        if self.controller is None:
            return
        set_prop(self.controller, "App::PropertyInteger", "CurrentStep", "Demo guiada", "Paso actual", int(self.current_step))
        set_prop(self.controller, "App::PropertyInteger", "TotalSteps", "Demo guiada", "Cantidad total de pasos", guided_total_steps())
        if self.current_step > 0:
            meta = guided_step(self.current_step)
            set_prop(self.controller, "App::PropertyString", "LastCompletedStep", "Demo guiada", "Ultimo paso completado", meta["id"])
        if state is not None:
            set_prop(self.controller, "App::PropertyString", "PlaybackState", "Demo guiada", "Estado del reproductor", str(state))
        if error is not None:
            set_prop(self.controller, "App::PropertyString", "LastError", "Demo guiada", "Ultimo error", str(error))
        if auto_camera is not None:
            set_prop(self.controller, "App::PropertyBool", "AutoCamera", "Demo guiada", "Encuadre automatico", bool(auto_camera))

    def set_playback_state(self, state, error=None, auto_camera=None):
        self._update_controller(state=state, error=error, auto_camera=auto_camera)
        try:
            self.doc.recompute()
        except Exception:
            pass

    def _remember_guided_view_state(self, obj):
        if obj is None:
            return
        key = getattr(obj, "Name", "") or str(id(obj))
        if key in self._guided_view_state:
            return
        try:
            view = obj.ViewObject
        except Exception:
            return
        state = {"object": obj, "visibility": None, "transparency": None}
        try:
            state["visibility"] = bool(view.Visibility)
        except Exception:
            pass
        try:
            state["transparency"] = int(view.Transparency)
        except Exception:
            pass
        self._guided_view_state[key] = state

    def _set_guided_view(self, obj, visibility=None, transparency=None):
        if obj is None:
            return
        self._remember_guided_view_state(obj)
        try:
            view = obj.ViewObject
        except Exception:
            return
        if visibility is not None:
            try:
                view.Visibility = bool(visibility)
            except Exception:
                pass
        if transparency is not None:
            try:
                view.Transparency = max(0, min(100, int(transparency)))
            except Exception:
                pass

    def restore_guided_presentation(self):
        """Restore view properties changed only for the guided explanation."""
        for state in list(self._guided_view_state.values()):
            obj = state.get("object")
            if obj is None:
                continue
            try:
                view = obj.ViewObject
            except Exception:
                continue
            if state.get("visibility") is not None:
                try:
                    view.Visibility = bool(state["visibility"])
                except Exception:
                    pass
            if state.get("transparency") is not None:
                try:
                    view.Transparency = int(state["transparency"])
                except Exception:
                    pass
        self._guided_view_state = {}
        self._guided_presentation_step = ""

    def apply_guided_presentation(self, step_id):
        """Reveal 2D sources by temporarily de-emphasizing obstructing BIM objects."""
        self.restore_guided_presentation()
        if self.execution_mode != "guided":
            return
        step_id = str(step_id or "")
        slab = self.floor_result.get("slab") if self.floor_result else None

        if step_id == "wall_sources":
            self._set_guided_view(self.exterior_sketch, visibility=True)
            self._set_guided_view(self.interior_sketch, visibility=True)
        elif step_id == "door_sources":
            for wall in self.walls:
                self._set_guided_view(wall, visibility=True, transparency=80)
            self._set_guided_view(slab, transparency=85)
            self._set_guided_view(self.door_sketch, visibility=True)
        elif step_id == "window_sources":
            for wall in self.walls:
                self._set_guided_view(wall, visibility=True, transparency=80)
            self._set_guided_view(slab, transparency=85)
            self._set_guided_view(self.window_sketch, visibility=True)
        elif step_id == "rooms":
            for wall in self.walls:
                self._set_guided_view(wall, visibility=False)
            self._set_guided_view(slab, transparency=90)
            self._set_guided_view(self.room_sketch, visibility=True)
        elif step_id == "roof_source":
            for wall in self.walls:
                self._set_guided_view(wall, visibility=True, transparency=65)
            self._set_guided_view(self.roof_rectangle, visibility=True)

        self._guided_presentation_step = step_id

    def _clear_step_state(self, step_id):
        mapping = {
            "project": ("parameter_sheet", "building", "level", "sources_group", "controller"),
            "wall_sources": ("exterior_sketch", "interior_sketch"),
            "floor": ("floor_result",),
            "walls": ("walls",),
            "door_sources": ("door_sketch",),
            "doors": ("doors",),
            "window_sources": ("window_sketch",),
            "windows": ("windows",),
            "rooms": ("room_sketch", "room_topology"),
            "spaces": ("space_result", "spaces"),
            "ceiling": ("ceiling_result",),
            "roof_source": ("roof_rectangle",),
            "roof": ("roof_result",),
        }
        for attr in mapping.get(step_id, ()):
            if attr in ("walls", "doors", "windows", "spaces"):
                setattr(self, attr, [])
            else:
                setattr(self, attr, None)

    def execute_step(self, step_number, manage_transaction=True):
        number = int(step_number)
        if number != self.current_step + 1:
            raise RuntimeError(
                "La demo guiada solo puede avanzar secuencialmente: actual=%d solicitado=%d"
                % (self.current_step, number)
            )
        meta = guided_step(number)
        handler = getattr(self, "_step_" + meta["id"], None)
        if handler is None:
            raise RuntimeError("Paso guiado sin adaptador FreeCAD: %s" % meta["id"])

        transaction_open = False
        try:
            if manage_transaction:
                self.doc.openTransaction("FA Demo %02d - %s" % (number, meta["title"]))
                transaction_open = True
            if self.controller is not None:
                self.set_playback_state("running", error="")
            handler()
            self.doc.recompute()
            if manage_transaction:
                self.doc.commitTransaction()
                transaction_open = False
            self.current_step = number
            final_state = "finished" if number >= guided_total_steps() else "paused"
            self._update_controller(state=final_state, error="")
            self.doc.recompute()
            _log("%d/%d %s" % (number, guided_total_steps(), meta["title"]))
            return meta
        except Exception as exc:
            if transaction_open:
                try:
                    self.doc.abortTransaction()
                except Exception:
                    pass
            self._clear_step_state(meta["id"])
            self._update_controller(state="error", error=str(exc))
            raise

    def _step_project(self):
        _log("Creando %s" % spec_summary(self.spec))
        # The native BIM hierarchy is authoritative from the first step. Demo
        # parameters are support data and therefore live in the Level source group,
        # never in a parallel FA_Project tree.
        structure = ensure_bim_structure(
            self.doc,
            building_name="Casa demo",
            level_name=self.level_name,
            elevation_mm=self.level_elevation_mm,
            building=self.building,
            update_existing=True,
            create_level_if_label_missing=self.create_level_if_label_missing,
        )
        self.building = structure["building"]
        self.level = structure["level"]
        self.sources_group = _make_aux_group(self.doc, self.level)
        if self.name_suffix:
            self.sources_group.Label = "Demo - Fuentes 2D y control%s" % self.name_suffix
        if self.create_controller:
            self.parameter_sheet = ensure_parameter_sheet(self.doc, self.sources_group)
            # Spreadsheet cells and aliases created by ensure_parameter_sheet are not
            # reliably readable until a recompute in FreeCAD 1.1.3.
            self.doc.recompute()
            _sync_demo_parameter_sheet(self.parameter_sheet, self.spec)
            self.doc.recompute()
            self.controller = _make_controller(
                self.doc,
                self.sources_group,
                self.spec,
                execution_mode=self.execution_mode,
            )

    def _step_wall_sources(self):
        self.exterior_sketch = _make_sketch(
            self.doc,
            "Sketch_Muros_Exteriores_Demo",
            "Sketch muros exteriores - Demo",
            self.spec["walls"]["exterior_segments"],
            z_mm=self.geometry_z_offset_mm,
        )
        self.interior_sketch = _make_sketch(
            self.doc,
            "Sketch_Muro_Interior_Demo",
            "Sketch muro interior - Demo",
            self.spec["walls"]["interior_segments"],
            z_mm=self.geometry_z_offset_mm,
        )
        prepare_sketches_as_wall_centerlines(
            [self.exterior_sketch],
            self.spec["walls"]["exterior_thickness_mm"],
            self.spec["walls"]["height_mm"],
            "exterior",
        )
        prepare_sketches_as_wall_centerlines(
            [self.interior_sketch],
            self.spec["walls"]["interior_thickness_mm"],
            self.spec["walls"]["height_mm"],
            "interior",
        )
        self.doc.recompute()
        _validate_recomputed_footprint(self.exterior_sketch, self.spec)

    def _step_floor(self):
        site_spec = dict(self.spec.get("site", {}) or {})
        floor_options = {
            "floor_thickness_mm": float(self.spec["floor"]["thickness_mm"]),
            "floor_overhang_mm": float(self.spec["floor"]["overhang_mm"]),
            "floor_top_z_mm": float(self.spec["floor"]["top_z_mm"]) + self.geometry_z_offset_mm,
            "create_test_terrain": bool(site_spec.get("garden_enabled", True)) and self.create_site,
            "create_site": self.create_site,
            "cut_terrain_under_building": True,
            "terrain_margin_mm": float(site_spec.get("terrain_margin_mm", 2500.0)),
            "pad_margin_mm": float(site_spec.get("pad_margin_mm", 750.0)),
            "terrain_variation_mm": float(site_spec.get("terrain_variation_mm", 0.0)),
            "terrain_seed": int(self.spec["seed"]),
            "replace_previous": bool(self.create_site),
        }
        self.floor_result = create_site_floor_from_sketches(
            self.doc,
            None,
            [self.exterior_sketch],
            floor_options,
            building=self.building,
            level=self.level,
        )
        terrain = self.floor_result.get("terrain") if self.floor_result else None
        if terrain is not None:
            terrain.Label = "Jardin - Demo"
            set_prop(
                terrain,
                "App::PropertyString",
                "FA_LandscapeRole",
                "FacilArquitectura",
                "Rol paisajistico del terreno demo",
                str(site_spec.get("landscape_role", "garden")),
            )
            garden_shape_color = (0.30, 0.62, 0.24)
            garden_line_color = (0.18, 0.38, 0.14)
            try:
                terrain.ViewObject.ShapeColor = garden_shape_color
                terrain.ViewObject.LineColor = garden_line_color
                terrain.ViewObject.Transparency = 0
            except Exception:
                pass

            # Arch.makeSite() puede ocultar la Base/Terrain y mostrar la Shape del
            # propio Site. Colorear ambos evita que el jardin aparezca gris tras
            # recomputar con el ViewProvider nativo de Arch.
            site = self.floor_result.get("site") if self.floor_result else None
            if site is not None:
                try:
                    site.ViewObject.ShapeColor = garden_shape_color
                    site.ViewObject.LineColor = garden_line_color
                    site.ViewObject.Transparency = 0
                except Exception:
                    pass

            # Aplicar el estilo despues del recompute final, porque Arch Site puede
            # actualizar su representacion cuando adopta Terrain como Base.
            self.doc.recompute()
            for garden_obj in (terrain, site):
                if garden_obj is None:
                    continue
                try:
                    garden_obj.ViewObject.ShapeColor = garden_shape_color
                    garden_obj.ViewObject.LineColor = garden_line_color
                    garden_obj.ViewObject.Transparency = 0
                except Exception:
                    pass

    def _step_walls(self):
        wall_params = {
            "wall_height_mm": float(self.spec["walls"]["height_mm"]),
            "ext_wall_thickness_mm": float(self.spec["walls"]["exterior_thickness_mm"]),
            "int_wall_thickness_mm": float(self.spec["walls"]["interior_thickness_mm"]),
        }
        self.walls = create_walls_from_centerline_sketches(
            self.doc,
            self.level,
            [self.exterior_sketch, self.interior_sketch],
            wall_params,
            target_level=self.level,
        )

    def _step_door_sources(self):
        self.door_sketch = _tag_opening_source(
            _make_sketch(
                self.doc,
                "Sketch_Centros_Puertas_Demo",
                "Sketch centros puertas - Demo",
                self.spec["openings"]["doors"],
                z_mm=self.geometry_z_offset_mm,
            ),
            "door",
        )
        self.sources_group.addObject(self.door_sketch)
        try:
            self.door_sketch.ViewObject.Visibility = True
        except Exception:
            pass

    def _step_doors(self):
        self.doors, summary = create_openings_from_centerlines(
            self.doc,
            self.level,
            [self.door_sketch],
            self.walls,
            "door",
            height_mm=float(self.spec["openings"]["door_height_mm"]),
            host_tolerance_mm=float(self.spec["openings"]["host_tolerance_mm"]),
            replace_existing=True,
        )
        if summary["rejected_count"]:
            raise RuntimeError("La demo rechazo %d puertas." % summary["rejected_count"])
        try:
            self.door_sketch.ViewObject.Visibility = False
        except Exception:
            pass

    def _step_window_sources(self):
        self.window_sketch = _tag_opening_source(
            _make_sketch(
                self.doc,
                "Sketch_Centros_Ventanas_Demo",
                "Sketch centros ventanas - Demo",
                self.spec["openings"]["windows"],
                z_mm=self.geometry_z_offset_mm,
            ),
            "window",
        )
        self.sources_group.addObject(self.window_sketch)
        try:
            self.window_sketch.ViewObject.Visibility = True
        except Exception:
            pass

    def _step_windows(self):
        self.windows, summary = create_openings_from_centerlines(
            self.doc,
            self.level,
            [self.window_sketch],
            self.walls,
            "window",
            height_mm=float(self.spec["openings"]["window_height_mm"]),
            sill_mm=float(self.spec["openings"]["window_sill_mm"]),
            host_tolerance_mm=float(self.spec["openings"]["host_tolerance_mm"]),
            replace_existing=True,
        )
        if summary["rejected_count"]:
            raise RuntimeError("La demo rechazo %d ventanas." % summary["rejected_count"])
        try:
            self.window_sketch.ViewObject.Visibility = False
        except Exception:
            pass

    def _step_rooms(self):
        self.room_sketch, self.room_topology = create_closed_room_sketch(
            self.doc,
            self.sources_group,
            [self.exterior_sketch, self.interior_sketch],
            snap_tolerance=float(self.spec["rooms"]["snap_tolerance_mm"]),
            minimum_room_area_m2=float(self.spec["rooms"]["minimum_area_m2"]),
            replace_previous=False,
        )
        # El Sketch documental del recinto tambien pertenece a la cota global del piso.
        room_placement = self.room_sketch.Placement
        room_placement.Base.z = self.geometry_z_offset_mm
        self.room_sketch.Placement = room_placement
        if len(self.room_topology["faces"]) != len(self.spec["rooms"]["items"]):
            raise RuntimeError(
                "La deteccion documental encontro %d recintos y la especificacion esperaba %d."
                % (len(self.room_topology["faces"]), len(self.spec["rooms"]["items"]))
            )

    def _step_spaces(self):
        # Reuse the same Arch Space service exposed by FA_CreateBIMSpaces.
        self.space_result = create_bim_spaces(
            self.doc,
            self.level,
            self.room_sketch,
            room_records=self.spec["rooms"]["items"],
            default_height_mm=float(self.spec["rooms"]["items"][0].get("space_height_mm", 2700.0)),
            replace_existing=True,
            generator=GENERATOR,
            label_suffix=" - Demo",
        )
        self.spaces = list(self.space_result["spaces"])
        # space_utils construye sus bases desde poligonos JSON en Z=0. Para un
        # nivel superior desplazamos la Base geometrica de cada Arch Space a la
        # cota absoluta del piso; el Space conserva esa Base como autoridad.
        for base in list(self.space_result.get("bases", []) or []):
            try:
                placement = base.Placement
                placement.Base.z = self.geometry_z_offset_mm
                base.Placement = placement
            except Exception:
                pass
        self.doc.recompute()

    def _step_ceiling(self):
        self.ceiling_result = create_modular_ceilings(
            self.doc,
            self.level,
            self.spaces,
            [],
            dict(
                _ceiling_options(self.spec),
                ceiling_elevation_mm=float(self.spec["ceiling"]["elevation_mm"]) + self.geometry_z_offset_mm,
                create_documentary_grid=False,
                replace_previous=False if self.ceiling_namespace else True,
                group_name=("FA_Ceilings_%s" % self.ceiling_namespace) if self.ceiling_namespace else "FA_Ceilings",
                group_label=("Cielos suspendidos - %s" % self.level_name) if self.ceiling_namespace else "Cielos suspendidos",
                sheet_name=("Spreadsheet_CielosSuspendidos_%s" % self.ceiling_namespace) if self.ceiling_namespace else "Spreadsheet_CielosSuspendidos",
                exclusion_zones_world_mm=list(self.ceiling_exclusion_zones or []),
                exclusion_owner=self.ceiling_exclusion_owner,
                exclusion_reason=self.ceiling_exclusion_reason,
            ),
            level=self.level,
            schedule_group=self.sources_group,
        )

    def _step_roof_source(self):
        self.roof_rectangle = _make_roof_rectangle(
            self.doc,
            self.sources_group,
            self.spec,
            base_z_mm=self.geometry_z_offset_mm,
        )

    def _step_roof(self):
        self.roof_result = create_roof_from_rectangle_programmatic(
            self.roof_rectangle,
            settings_override=_roof_settings(self.spec),
            level=self.level,
            manage_transaction=False,
            save_preferences=False,
            select_output=False,
            fit_view=False,
        )

    def _generated_objects(self):
        items = []
        if self.floor_result:
            # Never link the controller back to Site/Building/Level ancestors.
            # Site -> Building -> Level -> FA_DemoSources -> controller already
            # exists, so controller -> Site would close a dependency cycle and
            # FreeCAD reports "The graph must be a DAG". Keep only leaf output.
            items.append(self.floor_result.get("slab"))
            items.append(self.floor_result.get("terrain"))
        items.extend(self.walls)
        items.extend(self.doors)
        items.extend(self.windows)
        items.extend(self.spaces)
        if self.ceiling_result:
            items.extend(list(self.ceiling_result.get("objects", [])))
        if self.roof_result:
            items.extend(
                self.roof_result.get(key)
                for key in (
                    "truss_axis",
                    "truss",
                    "left_axis",
                    "left_beam",
                    "right_axis",
                    "right_beam",
                    "roof",
                )
            )
        return [obj for obj in items if obj is not None]

    def _step_finalize(self):
        sources = [
            self.exterior_sketch,
            self.interior_sketch,
            self.door_sketch,
            self.window_sketch,
            self.room_sketch,
            self.roof_rectangle,
        ]
        set_prop(self.controller, "App::PropertyLinkList", "Sources", "Demo", "Fuentes 2D", [obj for obj in sources if obj is not None])
        set_prop(self.controller, "App::PropertyLink", "RoomSketch", "Demo", "Sketch documental de recintos", self.room_sketch)
        set_prop(self.controller, "App::PropertyLinkList", "Spaces", "Demo", "Espacios BIM", self.spaces)
        ceiling_objects = list(self.ceiling_result.get("objects", [])) if self.ceiling_result else []
        set_prop(self.controller, "App::PropertyLinkList", "CeilingObjects", "Demo", "Objetos de cielorraso", ceiling_objects)
        generated = self._generated_objects()
        set_prop(self.controller, "App::PropertyLinkList", "GeneratedObjects", "Demo", "Objetos generados", generated)
        set_prop(self.controller, "App::PropertyInteger", "GeneratedCount", "Demo", "Cantidad de objetos principales", len(generated))
        context_names = {
            "site": getattr(self.floor_result.get("site") if self.floor_result else None, "Name", ""),
            "terrain": getattr(self.floor_result.get("terrain") if self.floor_result else None, "Name", ""),
            "building": getattr(self.building, "Name", ""),
            "level": getattr(self.level, "Name", ""),
            "sources_group": getattr(self.sources_group, "Name", ""),
        }
        set_prop(
            self.controller,
            "App::PropertyString",
            "ContextContainersJSON",
            "Demo",
            "Contenedores de contexto sin enlaces ciclicos",
            json.dumps(context_names, sort_keys=True, separators=(",", ":")),
        )
        for source in (self.door_sketch, self.window_sketch):
            if source is None:
                continue
            try:
                source.ViewObject.Visibility = False
            except Exception:
                pass
        msg(
            "FA Demo edificio completado | seed=%d | muros=%d | puertas=%d | ventanas=%d | espacios=%d | cielos=%d | cerchas=%d"
            % (
                int(self.spec["seed"]),
                len(self.walls),
                len(self.doors),
                len(self.windows),
                len(self.spaces),
                len(self.ceiling_result["plans"]) if self.ceiling_result else 0,
                int(self.roof_result["plan"]["truss"]["axis_count"]) if self.roof_result else 0,
            )
        )

    def result(self):
        return {
            "document": self.doc,
            "controller": self.controller,
            "spec": self.spec,
            "walls": self.walls,
            "doors": self.doors,
            "windows": self.windows,
            "room_sketch": self.room_sketch,
            "spaces": self.spaces,
            "ceilings": self.ceiling_result,
            "floor": self.floor_result,
            "roof": self.roof_result,
        }

    def close_document(self):
        self.restore_guided_presentation()
        name = getattr(self.doc, "Name", "")
        if not name:
            return
        try:
            App.closeDocument(name)
        except Exception:
            pass

    def rebuild_to_step(self, target_step):
        target = max(0, min(int(target_step), guided_total_steps()))
        spec = self.spec
        mode = self.execution_mode
        auto_camera = True
        if self.controller is not None:
            try:
                auto_camera = bool(self.controller.AutoCamera)
            except Exception:
                pass
        self.close_document()
        self.__init__(spec, execution_mode=mode)
        for number in range(1, target + 1):
            self.execute_step(number, manage_transaction=True)
        self.set_playback_state("finished" if target == guided_total_steps() else "paused", auto_camera=auto_camera)
        return self


def _apply_guided_camera(camera_mode):
    try:
        gui_doc = FreeCADGui.activeDocument()
        if gui_doc is None:
            return
        view = gui_doc.activeView()
        if str(camera_mode) == "top":
            view.viewTop()
        else:
            view.viewAxonometric()
        view.fitAll()
    except Exception:
        pass


def _materialize(spec):
    """Preserve atomic complete generation while showing visible activity."""
    session = DemoBuildingSession(spec, execution_mode="immediate")
    transaction_open = False
    feedback = LongOperationFeedback("FA Demo edificio", "Preparando demostracion").start()
    try:
        session.doc.openTransaction("FA Demo edificio")
        transaction_open = True
        if session.controller is not None:
            session.set_playback_state("running")
        for number in range(1, guided_total_steps() + 1):
            meta = guided_step(number)
            if meta.get("long_process"):
                feedback.stage(_guided_meta_text(meta, "title", i18n.bi("Paso %d" % number, "Step %d" % number)))
            session.execute_step(number, manage_transaction=False)
        feedback.stage("Recomputando y finalizando")
        session.doc.commitTransaction()
        transaction_open = False
        session.set_playback_state("finished", error="", auto_camera=True)
        _apply_guided_camera("axon")
        try:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(session.controller)
        except Exception:
            pass
        feedback.finish(success=True)
        return session.result()
    except Exception as exc:
        feedback.finish(success=False, error=str(exc))
        if transaction_open:
            try:
                session.doc.abortTransaction()
            except Exception:
                pass
        session.close_document()
        raise


def _run_demo_diagnostic(doc, intro="", parent=None):
    """Generate a full-document diagnostic after a successful Demo build.

    The Demo must never inherit a residual Tree selection: selection=[] forces
    document scope. Diagnostic failure does not invalidate the already-created
    model; it is reported separately and leaves the document untouched.
    """
    try:
        result = generate_report(
            doc=doc,
            selection=[],
            objective="Validacion automatica de FA Demo edificio",
            copy_prompt=False,
        )
        counts = result["diagnostic"]["counts"]
        _log(
            "Diagnostico automatico Demo | alcance=%s | objetos=%d | errores=%d | advertencias=%d | MD=%s"
            % (
                result["snapshot"].get("meta", {}).get("scope", ""),
                result["diagnostic"]["object_count"],
                counts.get("ERROR", 0),
                counts.get("WARN", 0),
                result["md_path"],
            )
        )
        show_report_dialog(
            result,
            parent=parent or FreeCADGui.getMainWindow(),
            title=i18n.bi("FA Demo edificio - diagnostico", "FA Building Demo - diagnostic"),
            intro=str(intro or ""),
        )
        return result
    except Exception as exc:
        _log("Diagnostico automatico no disponible: %s" % exc)
        QtWidgets.QMessageBox.warning(
            parent or FreeCADGui.getMainWindow(),
            i18n.bi("FA Demo edificio", "FA Building Demo"),
            i18n.bi(
                "La demostracion fue creada, pero no se pudo generar el informe diagnostico automatico.\n\n%s" % exc,
                "The demo was created, but the automatic diagnostic report could not be generated.\n\n%s" % exc,
            ),
        )
        return None


def _confirm_long_process_notice(mode="fixed"):
    """Ask for explicit Generate/Cancel before any immediate demo object exists."""
    two_storey = str(mode or "") == "two_storey"
    if two_storey:
        body_es = (
            "La generacion de la casa demo de dos pisos puede tardar varios segundos "
            "o algunos minutos.\n\n"
            "FreeCAD puede permanecer ocupado mientras crea y recomputa los objetos BIM.\n\n"
            "Version de prueba: %s" % DEMO_COMMAND_VERSION
        )
        body_en = (
            "Generating the two-storey demo house can take several seconds or a few minutes.\n\n"
            "FreeCAD may remain busy while BIM objects are created and recomputed.\n\n"
            "Test version: %s" % DEMO_COMMAND_VERSION
        )
    else:
        body_es = (
            "La generacion de la demostracion puede tardar varios segundos o algunos minutos.\n\n"
            "FreeCAD puede permanecer ocupado durante el proceso.\n\n"
            "Version de prueba: %s" % DEMO_COMMAND_VERSION
        )
        body_en = (
            "Generating the demo can take several seconds or a few minutes.\n\n"
            "FreeCAD may remain busy during the process.\n\n"
            "Test version: %s" % DEMO_COMMAND_VERSION
        )

    box = QtWidgets.QMessageBox(FreeCADGui.getMainWindow())
    box.setWindowTitle(i18n.bi("FA Demo edificio - proceso largo", "FA Building Demo - long process"))
    box.setIcon(QtWidgets.QMessageBox.Information)
    box.setText(i18n.bi(body_es, body_en))
    generate_button = box.addButton(i18n.bi("Generar", "Generate"), QtWidgets.QMessageBox.AcceptRole)
    cancel_button = box.addButton(i18n.bi("Cancelar", "Cancel"), QtWidgets.QMessageBox.RejectRole)
    box.setDefaultButton(generate_button)
    box.setEscapeButton(cancel_button)
    if hasattr(box, "exec"):
        box.exec()
    else:
        box.exec_()
    return box.clickedButton() is generate_button


def _validate_storey_wall_z(session, expected_z_mm):
    """Fail before hosted openings exist if a storey's walls are at the wrong Z."""
    target = float(expected_z_mm)
    wall_z = []
    for wall in list(session.walls or []):
        try:
            shape = wall.Shape
            if shape and not shape.isNull():
                wall_z.append(float(shape.BoundBox.ZMin))
        except Exception:
            continue
    if not wall_z:
        raise RuntimeError("No se pudo verificar la cota Z de los muros de %s." % session.level_name)
    actual = min(wall_z)
    if abs(actual - target) > 1.0:
        raise RuntimeError(
            "Nivel %s creo muros en Z=%.1f mm; se esperaba %.1f mm. "
            "La generacion se detuvo antes de crear puertas y ventanas."
            % (session.level_name, actual, target)
        )
    _log(
        "%s verificado en cota absoluta Z=%.1f mm | muros=%d"
        % (session.level_name, target, len(wall_z))
    )

def _create_demo_stair_source(session, stair_spec):
    """Create the deterministic two-segment construction path for the canonical stair."""
    points_xy = list(stair_spec.get("path_points_mm", []) or [])
    if len(points_xy) != 3:
        raise RuntimeError("La especificacion de escalera Demo requiere exactamente tres puntos XY.")
    z = float(session.geometry_z_offset_mm)
    points = [App.Vector(float(x), float(y), z) for x, y in points_xy]
    source = session.doc.addObject("Part::Feature", "FA_DemoStairPath")
    source.Label = "FA Escalera - Recorrido demo"
    source.Shape = Part.makePolygon(points)
    set_prop(source, "App::PropertyString", "FA_GeneratedBy", "Demo", "Generador", GENERATOR)
    set_prop(source, "App::PropertyString", "FA_Role", "Demo", "Rol", "stair_source_path")
    add_to_container(session.sources_group, source)
    try:
        source.ViewObject.Visibility = False
    except Exception:
        pass
    return source


def _materialize_demo_stair(ground, upper, stair_spec):
    """Materialize the canonical demo stair through the shared native adapter."""
    lower_slab = ground.floor_result.get("slab") if ground.floor_result else None
    upper_slab = upper.floor_result.get("slab") if upper.floor_result else None
    if lower_slab is None or upper_slab is None:
        raise RuntimeError("No se encontraron ambas losas para crear la escalera Demo.")

    source = _create_demo_stair_source(ground, stair_spec)
    context = build_stair_context(ground.doc, lower_slab, upper_slab, source)
    plan = plan_angled_stair(
        context["points"],
        context["lower_info"]["top_z"],
        context["upper_info"]["top_z"],
        width_mm=float(stair_spec.get("width_mm", 1000.0)),
        target_riser_mm=float(stair_spec.get("target_riser_mm", 175.0)),
    )
    result = create_native_stair(
        ground.doc,
        context,
        plan,
        structure_thickness_mm=float(stair_spec.get("structure_thickness_mm", 150.0)),
        create_plan=bool(stair_spec.get("create_plan", True)),
        railings_mode=str(stair_spec.get("railings_mode", "native")),
        prevent_duplicate=True,
    )
    result["plan"] = plan
    result["source"] = source

    # Headroom is planned independently from materialization. The upper-slab
    # plane feeds an Arch-native Subtraction; the lower-ceiling plane is passed
    # to the modular ceiling generator before its panels are created.
    ceiling_elevation = (
        float(ground.spec.get("ceiling", {}).get("elevation_mm", 2700.0))
        + float(ground.geometry_z_offset_mm)
    )
    ceiling_thickness = float(ground.spec.get("ceiling", {}).get("panel_thickness_mm", 15.0))
    clearance_plan = plan_stair_clearance(
        plan,
        [
            {
                "id": "upper_slab",
                "role": "upper_slab",
                "plane_z_mm": float(context["upper_info"]["bottom_z"]),
            },
            {
                "id": "lower_ceiling",
                "role": "lower_ceiling",
                "plane_z_mm": ceiling_elevation - ceiling_thickness,
            },
        ],
        headroom_mm=float(stair_spec.get("headroom_mm", 2100.0)),
        side_margin_mm=float(stair_spec.get("clearance_side_margin_mm", 50.0)),
        approach_margin_mm=float(stair_spec.get("clearance_approach_margin_mm", 100.0)),
    )
    previews = {}
    if bool(stair_spec.get("clearance_preview", True)):
        previews = create_clearance_previews(
            ground.doc,
            result.get("master"),
            clearance_plan,
            plane_containers={
                "upper_slab": upper.level,
                "lower_ceiling": ground.level,
            },
            visible=True,
        )
    result["clearance_plan"] = clearance_plan
    result["clearance_previews"] = previews

    slab_plane = next((item for item in clearance_plan["planes"] if item["id"] == "upper_slab"), {})
    ceiling_plane = next((item for item in clearance_plan["planes"] if item["id"] == "lower_ceiling"), {})
    expected_geometry = str(stair_spec.get("clearance_geometry_revision") or "").strip()
    if expected_geometry:
        for plane in (slab_plane, ceiling_plane):
            if str(plane.get("opening_shape") or "") != expected_geometry:
                raise RuntimeError(
                    "La geometria del buque no coincide con la revision esperada %s: %s."
                    % (expected_geometry, plane.get("opening_shape"))
                )

    slab_opening = None
    if bool(stair_spec.get("cut_upper_slab", False)):
        slab_opening = create_native_slab_opening(
            ground.doc,
            result.get("master"),
            upper_slab,
            clearance_plan,
            plane_id="upper_slab",
            vertical_margin_mm=float(stair_spec.get("slab_opening_vertical_margin_mm", 20.0)),
            dry_run=False,
        )
    result["slab_opening"] = slab_opening
    result["ceiling_clearance_zones"] = list(ceiling_plane.get("zones", []) or [])
    if bool(stair_spec.get("apply_ceiling_exclusion", False)):
        finish_exclusion = build_ceiling_finish_exclusion_zones(
            clearance_plan,
            plane_id="lower_ceiling",
            liner_thickness_mm=float(stair_spec.get("opening_liner_thickness_mm", 100.0)) if bool(stair_spec.get("create_opening_liner", False)) else 0.0,
            edge_gap_mm=float(stair_spec.get("ceiling_exclusion_edge_gap_mm", 3.0)),
        )
        result["ceiling_exclusion_zones"] = list(finish_exclusion.get("zones", []) or [])
        result["ceiling_finish_exclusion"] = finish_exclusion
    else:
        result["ceiling_exclusion_zones"] = []
        result["ceiling_finish_exclusion"] = {}
    _log(
        "Escalera Demo nativa creada | %d contrahuellas | %.1f mm | Levels=%s -> %s | barandillas=%s | hueco losa=%s (%s/%d zonas) | exclusion cielo=%s/%d zonas"
        % (
            int(plan["steps"]["total_risers"]),
            float(plan["steps"]["riser_mm"]),
            getattr(context.get("lower_level"), "Label", "?"),
            getattr(context.get("upper_level"), "Label", "?"),
            result.get("railing_status", "?"),
            str((slab_opening or {}).get("status", "no_aplicado")),
            str(slab_plane.get("opening_shape", "?")),
            int(slab_plane.get("zone_count", 0)),
            str(ceiling_plane.get("opening_shape", "?")),
            int(ceiling_plane.get("zone_count", 0)),
        )
    )
    return result


def _materialize_two_storey(spec):
    """Materialize two BIM Levels directly at their absolute geometric elevations.

    The upper storey no longer relies on moving a completed BuildingPart. Its
    Sketches, slab, walls, openings, Spaces, ceiling and roof are created using
    an explicit Z offset. Transactions are staged so a Z failure is detected
    before hosted ArchWindow objects exist.
    """
    storeys = list(spec.get("storeys", []) or [])
    if len(storeys) != 2:
        raise RuntimeError("La demo de dos pisos requiere exactamente dos niveles.")

    ground_info, upper_info = storeys
    ground = DemoBuildingSession(
        ground_info["spec"],
        execution_mode="immediate",
        level_name=ground_info["level_name"],
        level_elevation_mm=ground_info["elevation_mm"],
        geometry_z_offset_mm=ground_info["elevation_mm"],
        create_site=True,
        create_controller=True,
        name_suffix=" - Nivel 00",
        create_level_if_label_missing=True,
        ceiling_namespace="Nivel00",
    )
    feedback = LongOperationFeedback("FA Demo edificio 2 pisos", "Preparando demostracion multinivel").start()
    transaction_open = False
    upper = None
    try:
        _log("Version comando demo %s | multinivel Z absoluta" % DEMO_COMMAND_VERSION)
        ground.doc.Label = "%s | 2 niveles" % spec.get("name", "Casa demo 2 pisos")

        # Fase 1: planta baja hasta Espacios BIM. El cielo se difiere hasta
        # conocer la envolvente de la escalera y asi nace ya con su exclusion.
        ground.doc.openTransaction("FA Demo 2 pisos - Nivel 00")
        transaction_open = True
        for number in range(1, 11):
            ground.execute_step(number, manage_transaction=False)
        ground.doc.commitTransaction()
        transaction_open = False

        # Fase 2: Nivel 01 hasta muros, directamente en Z=3000. La validacion
        # ocurre aqui, antes de crear objetos ArchWindow hospedados.
        upper_z = float(upper_info["elevation_mm"])
        upper = DemoBuildingSession(
            upper_info["spec"],
            execution_mode="immediate",
            doc=ground.doc,
            building=ground.building,
            level_name=upper_info["level_name"],
            level_elevation_mm=upper_z,
            geometry_z_offset_mm=upper_z,
            create_site=False,
            create_controller=False,
            name_suffix=" - Nivel 01",
            create_level_if_label_missing=True,
            ceiling_namespace="Nivel01",
        )
        ground.doc.openTransaction("FA Demo 2 pisos - Nivel 01 estructura")
        transaction_open = True
        for number in range(1, 5):
            upper.execute_step(number, manage_transaction=False)
        if upper.level is ground.level:
            raise RuntimeError("Nivel 01 reutilizo indebidamente el objeto de Nivel 00.")
        levels_in_building = [obj for obj in list(getattr(ground.building, "Group", []) or []) if str(getattr(obj, "IfcType", "") or "") == "Building Storey"]
        if len(levels_in_building) != 2:
            raise RuntimeError("El Building demo no contiene dos Levels BIM nativos distintos.")
        _log("Jerarquia BIM verificada | Levels nativos=2 | Nivel 00=%s | Nivel 01=%s" % (ground.level.Name, upper.level.Name))
        _validate_storey_wall_z(upper, upper_z)
        ground.doc.commitTransaction()
        transaction_open = False

        # Fase 3: aberturas y acabados. Los muros anfitriones ya pertenecen a
        # una transaccion confirmada, por lo que un rollback no borra primero
        # los hosts de ArchWindow.
        ground.doc.openTransaction("FA Demo 2 pisos - Nivel 01 aberturas y techo")
        transaction_open = True

        stair_spec = dict(spec.get("stair", {}) or {})
        stair_result = _materialize_demo_stair(ground, upper, stair_spec) if bool(stair_spec.get("requested", False)) else None
        if stair_result and bool(stair_spec.get("apply_ceiling_exclusion", False)):
            ground.ceiling_exclusion_zones = list(stair_result.get("ceiling_exclusion_zones", []) or [])
            ground.ceiling_exclusion_owner = stair_result.get("master")
            ground.ceiling_exclusion_reason = "stair_clearance_plus_liner_finish"
        ground.execute_step(11, manage_transaction=False)

        # Architectural finish of the stair opening. The tapichel follows the
        # ceiling-side exclusion perimeter and rises only through the plenum,
        # hiding the interior of the suspended ceiling without consuming the
        # calculated stair clearance.
        if stair_result and bool(stair_spec.get("create_opening_liner", False)):
            upper_slab = upper.floor_result.get("slab") if upper.floor_result else None
            liner_result = create_stair_opening_liner(
                ground.doc,
                stair_result.get("master"),
                upper_slab,
                stair_result.get("clearance_plan"),
                plane_id="lower_ceiling",
                thickness_mm=float(stair_spec.get("opening_liner_thickness_mm", 100.0)),
                level=ground.level,
                dry_run=False,
            )
            stair_result["opening_liner"] = liner_result
            _log(
                "Tapichel buque escalera | status=%s | espesor=%.1f mm | altura=%.1f mm | segmentos=%d | extremos abiertos=%d"
                % (
                    str(liner_result.get("status", "?")),
                    float(liner_result.get("thickness_mm", 0.0)),
                    float(liner_result.get("height_mm", 0.0)),
                    int(liner_result.get("solid_count", 0)),
                    int(liner_result.get("skipped_edge_count", 0)),
                )
            )

        for number in range(5, 14):
            upper.execute_step(number, manage_transaction=False)

        if stair_result:
            ceiling_objects = list((ground.ceiling_result or {}).get("exclusion_objects", []) or [])
            master = stair_result.get("master")
            if bool(stair_spec.get("apply_ceiling_exclusion", False)) and not ceiling_objects:
                raise RuntimeError("El cielorraso de Nivel 00 no registro ninguna zona de exclusion para la escalera.")
            if master is not None:
                set_prop(master, "App::PropertyLinkList", "FA_CeilingObjects", "FacilArquitectura", "Cielorrasos recortados por la escalera", ceiling_objects)
                set_prop(master, "App::PropertyString", "FA_CeilingExclusionStatus", "FacilArquitectura", "Estado exclusion de cielorraso", "generator_exclusion_applied" if ceiling_objects else "not_requested")
                previews = dict(stair_result.get("clearance_previews") or {})
                if previews.get("upper_slab") is not None:
                    set_prop(master, "App::PropertyLink", "FA_SlabOpeningPlan", "FacilArquitectura", "PLAN del hueco de losa", previews.get("upper_slab"))
                if previews.get("lower_ceiling") is not None:
                    set_prop(master, "App::PropertyLink", "FA_CeilingExclusionPlan", "FacilArquitectura", "PLAN de exclusion de cielorraso", previews.get("lower_ceiling"))
                if (stair_result.get("slab_opening") or {}).get("status") == "native_subtraction_applied" and ceiling_objects:
                    mark_clearance_plans_applied(previews)

        all_generated = ground._generated_objects() + upper._generated_objects()
        if stair_result:
            all_generated.extend([stair_result.get("master"), stair_result.get("plan2d")])
            all_generated.extend(list((stair_result.get("clearance_previews") or {}).values()))
            slab_opening = stair_result.get("slab_opening") or {}
            all_generated.append(slab_opening.get("cutter"))
            opening_liner = stair_result.get("opening_liner") or {}
            all_generated.append(opening_liner.get("liner"))
        all_generated = [
            obj for obj in all_generated
            if obj is not None
            and getattr(obj, "Document", None) is ground.doc
            and ground.doc.getObject(getattr(obj, "Name", "")) is obj
        ]
        if ground.controller is not None:
            set_prop(ground.controller, "App::PropertyString", "SpecificationJSON", "Demo", "Especificacion JSON reproducible", json.dumps(spec, sort_keys=True, separators=(",", ":")))
            set_prop(ground.controller, "App::PropertyString", "Description", "Demo", "Descripcion", spec_summary(spec))
            set_prop(ground.controller, "App::PropertyString", "BuildingMode", "Demo", "Tipo de edificio demo", "two_storey")
            set_prop(ground.controller, "App::PropertyString", "DemoCommandVersion", "Demo", "Version comando demo", DEMO_COMMAND_VERSION)
            set_prop(ground.controller, "App::PropertyLinkList", "Levels", "Demo", "Niveles BIM", [ground.level, upper.level])
            set_prop(ground.controller, "App::PropertyLinkList", "GeneratedObjects", "Demo", "Objetos generados", all_generated)
            set_prop(ground.controller, "App::PropertyInteger", "GeneratedCount", "Demo", "Cantidad de objetos principales", len(all_generated))
            if stair_result:
                set_prop(ground.controller, "App::PropertyLink", "Stair", "Demo", "Escalera nativa", stair_result.get("master"))
                set_prop(ground.controller, "App::PropertyLink", "StairPlan2D", "Demo", "Representacion PLAN de escalera", stair_result.get("plan2d"))
                set_prop(ground.controller, "App::PropertyLink", "StairSource", "Demo", "Recorrido fuente de escalera", stair_result.get("source"))
                sources = list(getattr(ground.controller, "Sources", []) or [])
                if stair_result.get("source") is not None and stair_result.get("source") not in sources:
                    sources.append(stair_result.get("source"))
                    set_prop(ground.controller, "App::PropertyLinkList", "Sources", "Demo", "Fuentes 2D", sources)
                set_prop(ground.controller, "App::PropertyString", "StairStatus", "Demo", "Estado de escalera nativa", "created_native")
                set_prop(ground.controller, "App::PropertyString", "StairRailingStatus", "Demo", "Estado de barandillas", str(stair_result.get("railing_status", "")))
                previews = dict(stair_result.get("clearance_previews") or {})
                slab_opening = dict(stair_result.get("slab_opening") or {})
                set_prop(ground.controller, "App::PropertyLink", "StairSlabOpening", "Demo", "Buque nativo de losa", slab_opening.get("cutter"))
                opening_liner = dict(stair_result.get("opening_liner") or {})
                set_prop(ground.controller, "App::PropertyLink", "StairOpeningLiner", "Demo", "Tapichel perimetral del buque", opening_liner.get("liner"))
                set_prop(ground.controller, "App::PropertyString", "StairOpeningLinerStatus", "Demo", "Estado tapichel del buque", str(opening_liner.get("status", "not_requested")))
                set_prop(ground.controller, "App::PropertyLink", "StairSlabOpeningPreview", "Demo", "PLAN hueco de losa", previews.get("upper_slab"))
                set_prop(ground.controller, "App::PropertyLink", "StairCeilingExclusionPreview", "Demo", "PLAN exclusion de cielorraso", previews.get("lower_ceiling"))
                set_prop(ground.controller, "App::PropertyLinkList", "StairCeilingObjects", "Demo", "Cielorrasos recortados", list((ground.ceiling_result or {}).get("exclusion_objects", []) or []))
                clearance_ok = slab_opening.get("status") == "native_subtraction_applied" and bool((ground.ceiling_result or {}).get("exclusion_objects", []))
                set_prop(ground.controller, "App::PropertyString", "StairClearanceStatus", "Demo", "Estado de holgura", "applied" if clearance_ok else "incomplete")
            else:
                set_prop(ground.controller, "App::PropertyString", "StairStatus", "Demo", "Estado de escalera nativa", "not_requested")

        ground.doc.recompute()
        ground.doc.commitTransaction()
        transaction_open = False
        _apply_guided_camera("axon")
        feedback.finish(success=True)
        msg(
            "FA Demo 2 pisos completado | version=%s | niveles=2 | muros=%d | puertas=%d | ventanas=%d | espacios=%d | escalera=%s"
            % (
                DEMO_COMMAND_VERSION,
                len(ground.walls) + len(upper.walls),
                len(ground.doors) + len(upper.doors),
                len(ground.windows) + len(upper.windows),
                len(ground.spaces) + len(upper.spaces),
                "si" if stair_result else "no",
            )
        )
        return {
            "document": ground.doc,
            "controller": ground.controller,
            "spec": spec,
            "levels": [ground.level, upper.level],
            "ground": ground.result(),
            "upper": upper.result(),
            "stair": stair_result,
        }
    except Exception as exc:
        feedback.finish(success=False, error=str(exc))
        if transaction_open:
            try:
                ground.doc.abortTransaction()
            except Exception:
                pass
        ground.close_document()
        raise


GUIDED_DOCK_OBJECT_NAME = "FA_DemoGuidedDock"
_ACTIVE_GUIDED_DOCK = None


def _guided_demo_docks(main_window=None):
    """Return every live FA guided-demo dock parented to FreeCAD MainWindow."""
    main_window = main_window or FreeCADGui.getMainWindow()
    if main_window is None:
        return []
    try:
        candidates = list(main_window.findChildren(QtWidgets.QDockWidget))
    except Exception:
        return []
    docks = []
    for dock in candidates:
        try:
            if str(dock.objectName()) == GUIDED_DOCK_OBJECT_NAME:
                docks.append(dock)
        except Exception:
            continue
    return docks


def _clear_active_guided_dock(expected=None):
    """Clear the Python cache only when it still points to the closing dock."""
    global _ACTIVE_GUIDED_DOCK
    if expected is None or _ACTIVE_GUIDED_DOCK is expected:
        _ACTIVE_GUIDED_DOCK = None


def _retire_guided_demo_dock(dock, main_window=None):
    """Remove one obsolete dock from layout immediately and defer Qt deletion safely."""
    if dock is None:
        return False
    main_window = main_window or FreeCADGui.getMainWindow()
    try:
        timer = getattr(dock, "timer", None)
        if timer is not None:
            timer.stop()
    except Exception:
        pass
    # Rename before deferred deletion so a hot-reload callback cannot expose two
    # live docks with the authoritative objectName in the same Qt event loop.
    try:
        dock.setObjectName("%s_Retired_%x" % (GUIDED_DOCK_OBJECT_NAME, id(dock)))
    except Exception:
        pass
    if main_window is not None:
        try:
            main_window.removeDockWidget(dock)
        except Exception:
            pass
    try:
        dock.close()
    except Exception:
        pass
    try:
        dock.deleteLater()
    except Exception:
        pass
    return True


def cleanup_guided_demo_docks(main_window=None, keep=None):
    """Retire stale guided-demo docks without touching native FreeCAD docks/layout."""
    main_window = main_window or FreeCADGui.getMainWindow()
    removed = 0
    for dock in _guided_demo_docks(main_window):
        if keep is not None and dock is keep:
            continue
        if _retire_guided_demo_dock(dock, main_window=main_window):
            removed += 1
    return removed


class GuidedDemoDock(QtWidgets.QDockWidget):
    """Non-modal player for the same demo specification used by immediate mode."""

    def __init__(self, spec, parent=None):
        super().__init__("FA Demo guiada", parent)
        self.setObjectName(GUIDED_DOCK_OBJECT_NAME)
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
        self.setAttribute(_qt_enum("WA_DeleteOnClose", "WidgetAttribute"), True)
        try:
            self.setAllowedAreas(
                _qt_enum("LeftDockWidgetArea", "DockWidgetArea")
                | _qt_enum("RightDockWidgetArea", "DockWidgetArea")
            )
        except Exception:
            pass
        self.session = DemoBuildingSession(spec, execution_mode="guided")
        self.busy = False
        self._diagnostic_generated = False
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._on_timer)

        body = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(body)
        self.summary = QtWidgets.QLabel(spec_summary(spec))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        step_header = QtWidgets.QHBoxLayout()
        self.step_icon = QtWidgets.QLabel()
        self.step_icon.setFixedSize(48, 48)
        try:
            self.step_icon.setAlignment(_qt_enum("AlignCenter", "AlignmentFlag"))
        except Exception:
            pass
        step_header.addWidget(self.step_icon)

        self.step_label = QtWidgets.QLabel(guided_progress_text(0, i18n.current_language()))
        font = self.step_label.font()
        font.setBold(True)
        self.step_label.setFont(font)
        self.step_label.setWordWrap(True)
        step_header.addWidget(self.step_label, 1)
        layout.addLayout(step_header)

        self.tool_label = QtWidgets.QLabel(i18n.bi("Herramienta: FA Demo edificio", "Tool: FA Building Demo"))
        tool_font = self.tool_label.font()
        tool_font.setBold(True)
        self.tool_label.setFont(tool_font)
        self.tool_label.setWordWrap(True)
        layout.addWidget(self.tool_label)

        self.description = QtWidgets.QLabel(i18n.bi("Presione Siguiente o Reproducir para iniciar.", "Press Next or Play to start."))
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        self.status_frame = QtWidgets.QFrame()
        try:
            self.status_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        except Exception:
            pass
        self.status_frame.setFixedHeight(86)
        status_layout = QtWidgets.QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(8, 6, 8, 6)
        self.activity_indicator = QtWidgets.QLabel("\u23f3")
        activity_font = self.activity_indicator.font()
        activity_font.setPointSize(max(16, activity_font.pointSize() + 5))
        self.activity_indicator.setFont(activity_font)
        self.activity_indicator.setFixedWidth(34)
        try:
            self.activity_indicator.setAlignment(_qt_enum("AlignCenter", "AlignmentFlag"))
        except Exception:
            pass
        status_layout.addWidget(self.activity_indicator)
        self.duration_note = QtWidgets.QLabel(i18n.bi("Estado: listo para continuar.", "Status: ready to continue."))
        self.duration_note.setWordWrap(True)
        duration_font = self.duration_note.font()
        duration_font.setBold(True)
        self.duration_note.setFont(duration_font)
        self.duration_note.setMinimumHeight(64)
        self.duration_note.setMaximumHeight(64)
        status_layout.addWidget(self.duration_note, 1)
        layout.addWidget(self.status_frame)
        self._active_operation_meta = None

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, guided_total_steps())
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        controls = QtWidgets.QHBoxLayout()
        self.restart_button = QtWidgets.QPushButton(i18n.bi("|< Reiniciar", "|< Restart"))
        self.previous_button = QtWidgets.QPushButton(i18n.bi("< Anterior", "< Previous"))
        self.play_button = QtWidgets.QPushButton(i18n.bi("Reproducir", "Play"))
        self.next_button = QtWidgets.QPushButton(i18n.bi("Siguiente >", "Next >"))
        for button in (
            self.restart_button,
            self.previous_button,
            self.play_button,
            self.next_button,
        ):
            try:
                button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            except Exception:
                pass
            button.setMinimumHeight(30)
            controls.addWidget(button, 1)
        layout.addLayout(controls)

        options = QtWidgets.QFormLayout()
        self.speed = QtWidgets.QComboBox()
        self.speed.addItem(i18n.bi("Lenta - 3 s", "Slow - 3 s"), 3000)
        self.speed.addItem(i18n.bi("Normal - 1.5 s", "Normal - 1.5 s"), 1500)
        self.speed.addItem(i18n.bi("Rapida - 0.5 s", "Fast - 0.5 s"), 500)
        self.speed.setCurrentIndex(1)
        options.addRow(i18n.bi("Velocidad", "Speed"), self.speed)
        self.auto_camera = QtWidgets.QCheckBox(i18n.bi("Encuadre automatico", "Automatic framing"))
        self.auto_camera.setChecked(True)
        options.addRow(i18n.bi("Vista", "View"), self.auto_camera)
        layout.addLayout(options)

        note = QtWidgets.QLabel(
            i18n.bi("Anterior reconstruye deterministicamente la misma especificacion hasta el paso previo; no elimina objetos manualmente.", "Previous deterministically rebuilds the same specification up to the prior step; it does not manually delete objects.")
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch(1)
        self.close_button = QtWidgets.QPushButton(i18n.bi("Cerrar demostracion", "Close demo"))
        self.close_button.setToolTip(i18n.bi("Cierra solo el reproductor. El documento generado permanece abierto.", "Closes only the player. The generated document remains open."))
        close_row.addWidget(self.close_button)
        layout.addLayout(close_row)
        self.setWidget(body)

        self.restart_button.clicked.connect(self._restart)
        self.previous_button.clicked.connect(self._previous)
        self.play_button.clicked.connect(self._toggle_play)
        self.next_button.clicked.connect(self._next)
        self.close_button.clicked.connect(self.close)
        self.speed.currentIndexChanged.connect(self._update_timer_interval)
        self.auto_camera.toggled.connect(self._auto_camera_changed)
        self._update_timer_interval()
        self._refresh_ui()

    def _set_step_icon(self, meta=None):
        file_name = "demo_building.svg"
        title = "FA Demo edificio"
        if meta:
            file_name = str(meta.get("icon") or file_name)
            title = _guided_meta_text(meta, "tool", _guided_meta_text(meta, "title", title))
        path = _guided_icon_path(file_name)
        icon = QtGui.QIcon(path)
        self.step_icon.setPixmap(icon.pixmap(44, 44))
        self.step_icon.setToolTip(i18n.bi("Herramienta de este paso: %s" % title, "Tool for this step: %s" % title))

    def _update_timer_interval(self, *_args):
        self.timer.setInterval(int(self.speed.currentData() or 1500))

    def _auto_camera_changed(self, checked):
        self.session.set_playback_state(
            "playing" if self.timer.isActive() else "paused",
            auto_camera=bool(checked),
        )
        if checked and self.session.current_step > 0:
            _apply_guided_camera(guided_step(self.session.current_step)["camera"])

    def _flush_panel(self):
        """Paint warnings/status before entering a synchronous FreeCAD calculation."""
        for widget in (self.status_frame, self.duration_note, self):
            try:
                widget.repaint()
            except Exception:
                pass
        try:
            FreeCADGui.updateGui()
        except Exception:
            pass
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

    def _set_operation_notice(self, meta=None, active=False):
        if meta and meta.get("long_process"):
            title = _guided_meta_text(meta, "title", _guided_meta_text(meta, "tool", i18n.bi("Proceso", "Process")))
            note = _guided_meta_text(meta, "duration_note")
            prefix = i18n.bi("En curso", "In progress") if active else i18n.bi("Siguiente paso", "Next step")
            self.activity_indicator.setText("\u23f3")
            self.duration_note.setText("%s: %s. %s" % (prefix, title, note))
        elif active and meta:
            self.activity_indicator.setText("\u23f3")
            self.duration_note.setText(i18n.bi("En curso: %s." % _guided_meta_text(meta, "title", "Proceso"), "In progress: %s." % _guided_meta_text(meta, "title", "Process")))
        else:
            self.activity_indicator.setText("\u2713")
            self.duration_note.setText(i18n.bi("Estado: listo para continuar.", "Status: ready to continue."))

    def _set_busy(self, busy):
        self.busy = bool(busy)
        self.restart_button.setEnabled(not self.busy)
        self.previous_button.setEnabled((not self.busy) and self.session.current_step > 0)
        self.next_button.setEnabled((not self.busy) and self.session.current_step < guided_total_steps())
        self.play_button.setEnabled((not self.busy) and self.session.current_step < guided_total_steps())
        self.speed.setEnabled(not self.busy)
        self.auto_camera.setEnabled(not self.busy)
        self.close_button.setEnabled(not self.busy)
        QtWidgets.QApplication.processEvents()

    def _refresh_ui(self):
        current = self.session.current_step
        total = guided_total_steps()
        self.progress.setValue(current)
        self.step_label.setText(guided_progress_text(current, i18n.current_language()))
        if current <= 0:
            self._set_step_icon(None)
            self.tool_label.setText(i18n.bi("Herramienta: FA Demo edificio", "Tool: FA Building Demo"))
            self.description.setText(i18n.bi("Presione Siguiente o Reproducir para iniciar.", "Press Next or Play to start."))
        else:
            meta = guided_step(current)
            self._set_step_icon(meta)
            self.tool_label.setText(i18n.bi("Herramienta: %s" % _guided_meta_text(meta, "tool", _guided_meta_text(meta, "title")), "Tool: %s" % _guided_meta_text(meta, "tool", _guided_meta_text(meta, "title"))))
            self.description.setText(_guided_meta_text(meta, "description"))
        if self.busy and self._active_operation_meta is not None:
            self._set_operation_notice(self._active_operation_meta, active=True)
        elif current < total:
            upcoming = guided_step(current + 1)
            if upcoming.get("long_process"):
                self._set_operation_notice(upcoming, active=False)
            else:
                self._set_operation_notice(None, active=False)
        else:
            self.activity_indicator.setText("\u2713")
            self.duration_note.setText(i18n.bi("Demostracion completada.", "Demo completed."))
        self.previous_button.setEnabled((not self.busy) and current > 0)
        self.next_button.setEnabled((not self.busy) and current < total)
        self.play_button.setEnabled((not self.busy) and current < total)
        self.play_button.setText(i18n.bi("Pausa", "Pause") if self.timer.isActive() else i18n.bi("Reproducir", "Play"))
        if current >= total:
            self.timer.stop()
            self.play_button.setText(i18n.bi("Reproducir", "Play"))
            self.session.set_playback_state("finished", error="", auto_camera=self.auto_camera.isChecked())

    def _run_step(self, number):
        if self.busy:
            return False
        meta = guided_step(number)
        self._active_operation_meta = meta
        if meta.get("long_process"):
            self._set_operation_notice(meta, active=False)
        self._set_busy(True)
        if meta.get("long_process"):
            # Busy is already true, so flushing the Qt queue cannot start another demo step.
            self._flush_panel()
            self._set_operation_notice(meta, active=True)
            self._flush_panel()
        feedback = None
        if meta.get("long_process"):
            feedback = LongOperationFeedback(_guided_meta_text(meta, "tool", _guided_meta_text(meta, "title")), i18n.bi("Iniciando paso guiado", "Starting guided step")).start()
        try:
            if feedback is not None:
                feedback.stage("Creando y recomputando objetos BIM")
            meta = self.session.execute_step(number, manage_transaction=True)
            self.session.set_playback_state(
                "playing" if self.timer.isActive() else ("finished" if number == guided_total_steps() else "paused"),
                error="",
                auto_camera=self.auto_camera.isChecked(),
            )
            self.session.apply_guided_presentation(meta["id"])
            if self.auto_camera.isChecked():
                _apply_guided_camera(meta["camera"])
            try:
                FreeCADGui.Selection.clearSelection()
                if self.session.controller is not None:
                    FreeCADGui.Selection.addSelection(self.session.controller)
            except Exception:
                pass
            if feedback is not None:
                feedback.finish(success=True)
            if number == guided_total_steps() and not self._diagnostic_generated:
                self.timer.stop()
                self._diagnostic_generated = True
                _run_demo_diagnostic(
                    self.session.doc,
                    intro=i18n.bi(
                        "Demostracion guiada completada.",
                        "Guided demo completed.",
                    ),
                    parent=FreeCADGui.getMainWindow(),
                )
            return True
        except Exception as exc:
            if feedback is not None:
                feedback.finish(success=False, error=str(exc))
            self.timer.stop()
            self.session.set_playback_state("error", error=str(exc), auto_camera=self.auto_camera.isChecked())
            QtWidgets.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                "FA Demo guiada",
                "Fallo en el paso %d. El documento se conserva hasta el ultimo paso correcto.\n\n%s"
                % (number, exc),
            )
            return False
        finally:
            self._active_operation_meta = None
            self._set_busy(False)
            self._refresh_ui()

    def _next(self):
        if self.session.current_step < guided_total_steps():
            self._run_step(self.session.current_step + 1)

    def _on_timer(self):
        if self.session.current_step >= guided_total_steps():
            self.timer.stop()
            self._refresh_ui()
            return
        self._run_step(self.session.current_step + 1)

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.session.set_playback_state("paused", auto_camera=self.auto_camera.isChecked())
        elif self.session.current_step < guided_total_steps():
            self._update_timer_interval()
            self.timer.start()
            self.session.set_playback_state("playing", error="", auto_camera=self.auto_camera.isChecked())
            self._next()
        self._refresh_ui()

    def _rebuild(self, target):
        if self.busy:
            return
        self.timer.stop()
        if int(target) < guided_total_steps():
            self._diagnostic_generated = False
        self._set_busy(True)
        try:
            self.session.rebuild_to_step(target)
            self.session.set_playback_state("paused", error="", auto_camera=self.auto_camera.isChecked())
            if self.session.current_step > 0:
                current_meta = guided_step(self.session.current_step)
                self.session.apply_guided_presentation(current_meta["id"])
                if self.auto_camera.isChecked():
                    _apply_guided_camera(current_meta["camera"])
            else:
                self.session.restore_guided_presentation()
                if self.auto_camera.isChecked():
                    _apply_guided_camera("axon")
        except Exception as exc:
            self.session.set_playback_state("error", error=str(exc), auto_camera=self.auto_camera.isChecked())
            QtWidgets.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                "FA Demo guiada",
                "No se pudo reconstruir la demostracion.\n\n%s" % exc,
            )
        finally:
            self._set_busy(False)
            self._refresh_ui()

    def _previous(self):
        self._rebuild(max(0, self.session.current_step - 1))

    def _restart(self):
        self._rebuild(0)

    def closeEvent(self, event):
        self.timer.stop()
        self.session.restore_guided_presentation()
        self.session.set_playback_state("paused", auto_camera=self.auto_camera.isChecked())
        _clear_active_guided_dock(self)
        # Closing the dock never closes or deletes the generated FreeCAD document.
        super().closeEvent(event)


def start_guided_demo(spec):
    global _ACTIVE_GUIDED_DOCK
    main_window = FreeCADGui.getMainWindow()
    docks = _guided_demo_docks(main_window)

    current = _ACTIVE_GUIDED_DOCK
    current_is_live = current is not None and any(dock is current for dock in docks)
    if current_is_live:
        try:
            if current.isVisible():
                # Remove any historical duplicate without disturbing the current panel.
                cleanup_guided_demo_docks(main_window=main_window, keep=current)
                current.raise_()
                current.activateWindow()
                raise RuntimeError(
                    i18n.bi(
                        "Ya existe una demostracion guiada activa. Cierre su panel antes de iniciar otra.",
                        "A guided demo is already active. Close its panel before starting another one.",
                    )
                )
        except RuntimeError:
            raise
        except Exception:
            pass

    # After hot reload the Python global may be None while the old Qt dock is
    # still parented to MainWindow. Retire every such stale dock synchronously
    # from the layout before creating the replacement.
    cleanup_guided_demo_docks(main_window=main_window)
    _ACTIVE_GUIDED_DOCK = None

    dock = GuidedDemoDock(spec, parent=main_window)
    main_window.addDockWidget(_qt_enum("RightDockWidgetArea", "DockWidgetArea"), dock)
    dock.show()
    dock.raise_()
    _ACTIVE_GUIDED_DOCK = dock
    return dock


class CommandClass:
    """Create a complete canonical/random house demo in a new document."""

    CommandName = "FA_DemoBuilding"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Demo edificio", "FA Building Demo"),
            "ToolTip": i18n.bi(
                "Crear desde cero una casa BIM simple. Modo fijo 6x8 m, casa fija de dos pisos o aleatorio reproducible por semilla; genera Sketches, niveles BIM, piso, muros, puertas, ventanas, Espacios BIM, cielo modular 600x600 y techo.",
                "Create a simple BIM house from scratch. Fixed 6x8 m, fixed two-storey, or seed-reproducible random mode; generates Sketches, BIM levels, floor, walls, doors, windows, BIM Spaces, modular ceiling, and roof.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            dialog = DemoBuildingDialog(parent=FreeCADGui.getMainWindow())
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.values()
            spec = build_two_storey_demo_spec() if options.get("mode") == "two_storey" else build_demo_spec(options["seed"], options["randomized"])
            if options.get("execution") == "guided":
                start_guided_demo(spec)
                return
            if not _confirm_long_process_notice(options.get("mode", "fixed")):
                _log("Generacion cancelada por el usuario antes de iniciar | version=%s" % DEMO_COMMAND_VERSION)
                return
            result = _materialize_two_storey(spec) if options.get("mode") == "two_storey" else _materialize(spec)
            _run_demo_diagnostic(
                result["document"],
                intro=i18n.bi(
                    "Demostracion creada en un documento nuevo.\n\n%s" % spec_summary(result["spec"]),
                    "Demo created in a new document.\n\n%s" % spec_summary(result["spec"]),
                ),
                parent=FreeCADGui.getMainWindow(),
            )
        except Exception as exc:
            handle_command_exception(i18n.bi("FA Demo edificio", "FA Building Demo"), exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    # Hot restart invalidates module globals but not Qt children already owned by
    # FreeCAD MainWindow. Remove only FA's guided-demo docks before re-registering.
    cleanup_guided_demo_docks()
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
