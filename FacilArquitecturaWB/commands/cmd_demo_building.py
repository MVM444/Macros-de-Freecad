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
- Mantener el modo completo en una sola transaccion para conservar el comportamiento
  atomico existente; el modo guiado usa una transaccion por paso.
- El modo guiado debe reutilizar exactamente las mismas operaciones de materializacion
  y la misma especificacion JSON que el modo completo.
- Conservar salida 2D mediante los Sketches fuente y el Draft Rectangle de techo.
- Los paneles de Demo guiada usan un objectName estable y deben limpiarse por MainWindow en cada registro/hot restart; nunca confiar solo en globals Python para su ciclo de vida.
FreeCAD objetivo: 1.1.3.
Version: 0.4.1
Fecha y hora: 2026-09-02 15:22 America/Costa_Rica
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
from ..core.demo_building_core import CANONICAL_SEED, build_demo_spec, spec_summary
from ..core.demo_guided_core import guided_progress_text, guided_step, guided_steps, guided_total_steps
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
        previous_mode = self.params.GetString("mode", "fixed")
        self.mode.setCurrentIndex(1 if previous_mode == "random" else 0)
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
        randomized = self.mode.currentData() == "random"
        seed = int(self.seed.value()) if randomized else CANONICAL_SEED
        return randomized, seed

    def _refresh(self):
        randomized, seed = self._values()
        self.seed.setEnabled(randomized)
        try:
            self.preview.setText(spec_summary(build_demo_spec(seed, randomized)))
        except Exception as exc:
            self.preview.setText(i18n.bi("Configuracion invalida: %s" % exc, "Invalid configuration: %s" % exc))

    def values(self):
        randomized, seed = self._values()
        execution = str(self.execution.currentData() or "guided")
        self.params.SetString("mode", "random" if randomized else "fixed")
        self.params.SetString("execution", execution)
        if randomized:
            self.params.SetInt("seed", int(seed))
        return {
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


def _make_sketch(doc, name, label, segments):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    sketch.Label = label
    for segment in segments:
        x1, y1 = map(float, segment["start_mm"])
        x2, y2 = map(float, segment["end_mm"])
        sketch.addGeometry(
            Part.LineSegment(App.Vector(x1, y1, 0.0), App.Vector(x2, y2, 0.0)),
            False,
        )
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



def _make_roof_rectangle(doc, group, spec):
    width = float(spec["footprint"]["width_mm"])
    depth = float(spec["footprint"]["depth_mm"])
    z = float(spec["walls"]["height_mm"])
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

    def __init__(self, spec, execution_mode="immediate"):
        self.spec = spec
        self.execution_mode = str(execution_mode or "immediate")
        self.doc = _new_demo_document(spec)
        self.current_step = 0
        self.parameter_sheet = None
        self.building = None
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
            level_name="Nivel 00",
            elevation_mm=0.0,
            update_existing=True,
        )
        self.building = structure["building"]
        self.level = structure["level"]
        self.sources_group = _make_aux_group(self.doc, self.level)
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
        )
        self.interior_sketch = _make_sketch(
            self.doc,
            "Sketch_Muro_Interior_Demo",
            "Sketch muro interior - Demo",
            self.spec["walls"]["interior_segments"],
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
            "floor_top_z_mm": float(self.spec["floor"]["top_z_mm"]),
            "create_test_terrain": bool(site_spec.get("garden_enabled", True)),
            "cut_terrain_under_building": True,
            "terrain_margin_mm": float(site_spec.get("terrain_margin_mm", 2500.0)),
            "pad_margin_mm": float(site_spec.get("pad_margin_mm", 750.0)),
            "terrain_variation_mm": float(site_spec.get("terrain_variation_mm", 0.0)),
            "terrain_seed": int(self.spec["seed"]),
            "replace_previous": True,
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

    def _step_ceiling(self):
        self.ceiling_result = create_modular_ceilings(
            self.doc,
            self.level,
            self.spaces,
            [],
            dict(_ceiling_options(self.spec), create_documentary_grid=False),
            level=self.level,
            schedule_group=self.sources_group,
        )

    def _step_roof_source(self):
        self.roof_rectangle = _make_roof_rectangle(
            self.doc,
            self.sources_group,
            self.spec,
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
                "Crear desde cero una casa BIM simple. Modo fijo 6x8 m o aleatorio reproducible por semilla; genera Sketches, piso, muros, puertas, ventanas, Espacios BIM, cielo modular 600x600 y techo.",
                "Create a simple BIM house from scratch. Fixed 6x8 m or seed-reproducible random mode; generates Sketches, floor, walls, doors, windows, BIM Spaces, modular ceiling, and roof.",
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
            spec = build_demo_spec(options["seed"], options["randomized"])
            if options.get("execution") == "guided":
                start_guided_demo(spec)
                return
            result = _materialize(spec)
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(),
                i18n.bi("FA Demo edificio", "FA Building Demo"),
                i18n.bi(
                    "Demostracion creada en un documento nuevo.\n\n%s" % spec_summary(result["spec"]),
                    "Demo created in a new document.\n\n%s" % spec_summary(result["spec"]),
                ),
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
