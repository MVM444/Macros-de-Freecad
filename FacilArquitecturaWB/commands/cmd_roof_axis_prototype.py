"""FA Techo desde rectangulo para Facil Arquitectura.


Nombre: cmd_roof_axis_prototype.py
Proposito: crear un techo BIM completo desde un Draft Rectangle seleccionado, sin
Sketches redundantes para cerchas ni clavadores.
Funcion principal: usar el rectangulo como huella/cota de apoyo, crear Arch Axis
parametricos, una cercha maestra repetida por Axis, clavadores Structure/Beam
repetidos por Axis y una cubierta Arch Roof sobre una Base Draft Rectangle interna.
FreeCAD objetivo: 1.1.3.
Version: 0.6.1
Fecha y hora: 2026-09-01 09:08 America/Costa_Rica


Instrucciones de mantenimiento:
- Este archivo conserva su nombre historico para no crear una segunda ruta paralela.
- El comando ya no crea un documento de ejemplo: trabaja en el documento activo.
- Requerir exactamente un Draft Rectangle horizontal como fuente.
- No reparentar ni ocultar el rectangulo fuente del usuario.
- Preferir Draft Line/Rectangle para geometria auxiliar simple.
- Clavadores: una sola Arch Structure/Beam maestra por faldon + Arch Axis.
- Cerchas: una sola Draft Line + Arch Truss + Arch Axis.
- La linea Base de la cercha es su plano inferior de apoyo y debe quedar exactamente en la cota de muros/rectangulo.
- Mantener la Base de Arch Roof separada de la huella: la cubierta necesita una
  elevacion propia para apoyar sobre clavadores sin mover/acoplar la fuente del usuario.
- No crear App::Link ni enlaces personalizados a la fuente; guardar su Name como texto
  para evitar abanicos de dependencias en el arbol.
- Validar toda la entrada antes de abrir transaccion y reemplazar solo objetos creados
  por este comando para la misma fuente.
"""


from __future__ import annotations


import math
import os
import statistics


import FreeCAD as App
import FreeCADGui
import Draft
import Arch


from .. import i18n
from .roof_command_common import (
    current_selection,
    ensure_roof_container,
    ensure_target_level,
    finish_transaction,
    open_transaction,
    select_results,
)
from ..core.axis_distribution_core import (
    plan_fixed_axis_distribution,
    plan_rounded_axis_distribution,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import msg, warn
from ..core.reloadable_command import ReloadableCommandProxy
from ..core.process_feedback import long_process_message
from ..ui.process_feedback import LongOperationFeedback

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "roof_from_rectangle.svg")
).replace(os.sep, "/")

from ..core.roof_support_core import (
    apply_symmetric_support_adjust,
    select_end_support_axes,
)




LOG = "[FA TECHO RECT] "
GENERATOR = "FA_RoofFromRectangle"
PREF_ROOT = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/RoofSystem"




def _log(text):
    App.Console.PrintMessage(LOG + str(text) + "\n")




def _draft_rectangle(length, height, placement, face=False):
    fn = getattr(Draft, "make_rectangle", None) or getattr(Draft, "makeRectangle", None)
    if fn is None:
        raise RuntimeError("Draft.make_rectangle no esta disponible")
    return fn(float(length), float(height), placement=placement, face=bool(face))




def _draft_line(p0, p1):
    fn = getattr(Draft, "make_line", None) or getattr(Draft, "makeLine", None)
    if fn is None:
        raise RuntimeError("Draft.make_line no esta disponible")
    return fn(p0, p1)




def _axis_rotation(x_axis, y_axis):
    x = App.Vector(x_axis)
    y = App.Vector(y_axis)
    x.normalize()
    y.normalize()
    z = x.cross(y)
    if not z.Length:
        raise ValueError("Los ejes X/Y no pueden ser paralelos")
    z.normalize()
    return App.Rotation(x, y, z, "XYZ")




def _is_rectangle(obj):
    if obj is None:
        return False
    try:
        if Draft.getType(obj) == "Rectangle":
            return True
    except Exception:
        pass
    return bool(
        str(getattr(obj, "TypeId", "")) == "Part::Part2DObjectPython"
        and hasattr(obj, "Length")
        and hasattr(obj, "Height")
        and hasattr(obj, "Shape")
    )




def _require_selected_rectangle(selection):
    rectangles = [obj for obj in list(selection or []) if _is_rectangle(obj)]
    if len(rectangles) != 1:
        raise UserFacingError(
            "Seleccione exactamente un Draft Rectangle horizontal colocado sobre la cota de apoyo del techo."
        )
    source = rectangles[0]
    if getattr(source, "Document", None) is None:
        raise UserFacingError("El rectangulo seleccionado no pertenece a un documento.")
    length = float(source.Length.Value if hasattr(source.Length, "Value") else source.Length)
    height = float(source.Height.Value if hasattr(source.Height, "Value") else source.Height)
    if length <= 1e-6 or height <= 1e-6:
        raise UserFacingError("El Draft Rectangle seleccionado tiene dimensiones invalidas.")
    try:
        wires = list(source.Shape.Wires)
        if not wires or not wires[0].isClosed():
            raise UserFacingError("El Draft Rectangle no produce un contorno cerrado valido.")
    except UserFacingError:
        raise
    except Exception as exc:
        raise UserFacingError("No se pudo leer la geometria del Draft Rectangle: %s" % exc)


    rot = source.Placement.Rotation
    u = rot.multVec(App.Vector(1, 0, 0))
    v = rot.multVec(App.Vector(0, 1, 0))
    normal = u.cross(v)
    if not normal.Length:
        raise UserFacingError("No se pudo determinar el plano del rectangulo.")
    normal.normalize()
    if abs(abs(normal.dot(App.Vector(0, 0, 1))) - 1.0) > 1e-5:
        raise UserFacingError(
            "Por ahora FA Techo desde rectangulo requiere un Draft Rectangle horizontal."
        )
    return source




def _prefs():
    return {
        "truss": App.ParamGet(PREF_ROOT + "/Trusses"),
        "purlin": App.ParamGet(PREF_ROOT + "/Purlins"),
        "roof": App.ParamGet(PREF_ROOT + "/Roof"),
        "rect": App.ParamGet(PREF_ROOT + "/RectangleInput"),
    }




def _read_settings():
    p = _prefs()
    return {
        "pitch_deg": p["roof"].GetFloat("slope_deg", p["truss"].GetFloat("pitch_deg", 20.0)),
        "ridge_mode": p["rect"].GetString("ridge_mode", "long_side"),
        "support_mode": p["rect"].GetString("support_mode", "walls_if_consistent"),
        "truss_spacing_mm": p["truss"].GetFloat("spacing_mm", 3000.0),
        "truss_distribution_mode": p["truss"].GetString("distribution_mode", "fixed"),
        "truss_round_step_mm": p["truss"].GetFloat("round_step_mm", 100.0),
        "truss_support_xy_mode": p["rect"].GetString("truss_support_xy_mode", "walls_if_available"),
        "truss_support_adjust_mm": p["truss"].GetFloat("support_adjust_mm", 0.0),
        "truss_support_edge_tolerance_mm": p["truss"].GetFloat("support_edge_tolerance_mm", 1000.0),
        "truss_height_start_mm": p["truss"].GetFloat("height_start_mm", 150.0),
        "purlin_spacing_mm": p["purlin"].GetFloat("spacing_mm", 800.0),
        "purlin_distribution_mode": p["purlin"].GetString("distribution_mode", "fixed"),
        "purlin_round_step_mm": p["purlin"].GetFloat("round_step_mm", 50.0),
        "purlin_start_offset_mm": p["purlin"].GetFloat("start_offset_mm", 200.0),
        "purlin_end_offset_mm": p["purlin"].GetFloat("end_offset_mm", 200.0),
        "purlin_width_mm": p["purlin"].GetFloat("profile_width_mm", 50.0),
        "purlin_height_mm": p["purlin"].GetFloat("profile_height_mm", 100.0),
        "roof_thickness_mm": p["roof"].GetFloat("thickness_mm", 50.0),
        "overhang_mm": p["roof"].GetFloat("overhang_mm", 600.0),
        "strut_height_mm": p["truss"].GetFloat("strut_height_mm", 50.0),
        "strut_width_mm": p["truss"].GetFloat("strut_width_mm", 50.0),
        "rod_size_mm": p["truss"].GetFloat("rod_size_mm", 25.0),
        "rod_sections": p["truss"].GetInt("rod_sections", 6),
        "rod_end": p["truss"].GetBool("rod_end", True),
        "rod_mode": p["truss"].GetString("rod_mode", "/|\\|/|\\"),
        "rod_type": p["truss"].GetString("rod_type", "Square"),
        "rod_direction": p["truss"].GetString("rod_direction", "Forward"),
    }




def _save_settings(s):
    p = _prefs()
    p["roof"].SetFloat("slope_deg", float(s["pitch_deg"]))
    p["truss"].SetFloat("pitch_deg", float(s["pitch_deg"]))
    p["rect"].SetString("ridge_mode", str(s["ridge_mode"]))
    p["rect"].SetString("support_mode", str(s["support_mode"]))
    p["truss"].SetFloat("spacing_mm", float(s["truss_spacing_mm"]))
    p["truss"].SetString("distribution_mode", str(s["truss_distribution_mode"]))
    p["truss"].SetFloat("round_step_mm", float(s["truss_round_step_mm"]))
    p["rect"].SetString("truss_support_xy_mode", str(s["truss_support_xy_mode"]))
    p["truss"].SetFloat("support_adjust_mm", float(s["truss_support_adjust_mm"]))
    p["truss"].SetFloat("support_edge_tolerance_mm", float(s["truss_support_edge_tolerance_mm"]))
    p["truss"].SetFloat("height_start_mm", float(s["truss_height_start_mm"]))
    p["purlin"].SetFloat("spacing_mm", float(s["purlin_spacing_mm"]))
    p["purlin"].SetString("distribution_mode", str(s["purlin_distribution_mode"]))
    p["purlin"].SetFloat("round_step_mm", float(s["purlin_round_step_mm"]))
    p["purlin"].SetFloat("start_offset_mm", float(s["purlin_start_offset_mm"]))
    p["purlin"].SetFloat("end_offset_mm", float(s["purlin_end_offset_mm"]))
    p["purlin"].SetFloat("profile_width_mm", float(s["purlin_width_mm"]))
    p["purlin"].SetFloat("profile_height_mm", float(s["purlin_height_mm"]))
    p["roof"].SetFloat("thickness_mm", float(s["roof_thickness_mm"]))
    p["roof"].SetFloat("overhang_mm", float(s["overhang_mm"]))




def _show_settings_dialog(settings, source, wall_info):
    if not getattr(App, "GuiUp", False):
        return dict(settings)
    from PySide import QtCore, QtWidgets


    dlg = QtWidgets.QDialog(FreeCADGui.getMainWindow())
    dlg.setWindowTitle(i18n.bi("FA Techo desde rectangulo", "FA Roof from rectangle"))
    layout = QtWidgets.QVBoxLayout(dlg)
    wall_text = i18n.bi("Sin muros BIM coincidentes detectados", "No matching BIM walls detected")
    if wall_info.get("count"):
        wall_text = i18n.bi(
            "Muros BIM: %d | coronacion mediana %.1f mm | dispersion %.1f mm",
            "BIM walls: %d | median top %.1f mm | spread %.1f mm",
        ) % (wall_info["count"], wall_info["top_z_mm"], wall_info["spread_mm"])
    intro = QtWidgets.QLabel(
        i18n.bi("Fuente: %s\n%.1f x %.1f mm | Z rectangulo=%.1f mm\n%s", "Source: %s\n%.1f x %.1f mm | rectangle Z=%.1f mm\n%s")
        % (
            source.Label,
            float(source.Length.Value),
            float(source.Height.Value),
            float(source.Placement.Base.z),
            wall_text,
        )
    )
    layout.addWidget(intro)

    duration = QtWidgets.QLabel(long_process_message(i18n.bi("La creacion del sistema de techo", "Roof system creation")))
    duration.setWordWrap(True)
    duration_font = duration.font()
    duration_font.setBold(True)
    duration.setFont(duration_font)
    layout.addWidget(duration)


    form = QtWidgets.QFormLayout()
    layout.addLayout(form)


    def spin(value, minimum, maximum, step, decimals=0):
        w = QtWidgets.QDoubleSpinBox()
        w.setRange(float(minimum), float(maximum))
        w.setDecimals(int(decimals))
        w.setSingleStep(float(step))
        w.setValue(float(value))
        w.setSuffix(" mm")
        return w


    pitch = QtWidgets.QDoubleSpinBox()
    pitch.setRange(1.0, 89.0)
    pitch.setDecimals(1)
    pitch.setSingleStep(1.0)
    pitch.setValue(float(settings["pitch_deg"]))
    pitch.setSuffix(" deg")
    form.addRow(i18n.bi("Pendiente:", "Pitch:"), pitch)


    ridge = QtWidgets.QComboBox()
    ridge.addItem(i18n.bi("Cumbrera sobre el lado largo (automatico)", "Ridge over long side (automatic)"), "long_side")
    ridge.addItem(i18n.bi("Cumbrera paralela a Length", "Ridge parallel to Length"), "length")
    ridge.addItem(i18n.bi("Cumbrera paralela a Height", "Ridge parallel to Height"), "height")
    idx = max(0, ridge.findData(settings["ridge_mode"]))
    ridge.setCurrentIndex(idx)
    form.addRow(i18n.bi("Direccion de cumbrera:", "Ridge direction:"), ridge)


    support = QtWidgets.QComboBox()
    support.addItem(i18n.bi("Usar Z del rectangulo", "Use rectangle Z"), "rectangle")
    support.addItem(i18n.bi("Usar muros BIM si su coronacion es coherente", "Use BIM walls when their top elevation is consistent"), "walls_if_consistent")
    support.setCurrentIndex(max(0, support.findData(settings["support_mode"])))
    if not wall_info.get("count"):
        support.model().item(1).setEnabled(False)
        support.setCurrentIndex(0)
    form.addRow(i18n.bi("Cota de apoyo:", "Support elevation:"), support)


    truss_support_xy = QtWidgets.QComboBox()
    truss_support_xy.addItem(i18n.bi("Centrar cerchas extremas sobre muros BIM (automatico)", "Center end trusses on BIM walls (automatic)"), "walls_if_available")
    truss_support_xy.addItem(i18n.bi("Usar bordes del rectangulo", "Use rectangle edges"), "rectangle")
    truss_support_xy.setCurrentIndex(max(0, truss_support_xy.findData(settings["truss_support_xy_mode"])))
    if not wall_info.get("count"):
        truss_support_xy.model().item(0).setEnabled(False)
        truss_support_xy.setCurrentIndex(max(0, truss_support_xy.findData("rectangle")))
    form.addRow(i18n.bi("Apoyo XY cerchas:", "Truss XY support:"), truss_support_xy)


    truss_support_adjust = spin(settings["truss_support_adjust_mm"], -1000.0, 1000.0, 25.0)
    form.addRow(i18n.bi("Ajuste apoyo (+ hacia interior):", "Support adjustment (+ inward):"), truss_support_adjust)


    truss_spacing = spin(settings["truss_spacing_mm"], 100.0, 20000.0, 100.0)
    form.addRow(i18n.bi("Separacion cerchas:", "Truss spacing:"), truss_spacing)


    truss_mode = QtWidgets.QComboBox()
    truss_mode.addItem(i18n.bi("Mantener valor; extremos simetricos", "Keep value; symmetric ends"), "fixed")
    truss_mode.addItem(i18n.bi("Calculada con nominal redondeado", "Calculated with rounded nominal"), "rounded")
    truss_mode.setCurrentIndex(max(0, truss_mode.findData(settings["truss_distribution_mode"])))
    form.addRow(i18n.bi("Distribucion cerchas:", "Truss distribution:"), truss_mode)


    truss_round_step = QtWidgets.QComboBox()
    truss_round_step.addItem("50 mm (5 cm)", 50.0)
    truss_round_step.addItem("100 mm (10 cm)", 100.0)
    truss_round_step.setCurrentIndex(max(0, truss_round_step.findData(float(settings["truss_round_step_mm"]))))
    form.addRow(i18n.bi("Redondeo cerchas:", "Truss rounding:"), truss_round_step)


    truss_height_start = spin(settings["truss_height_start_mm"], 0.0, 2000.0, 50.0)
    form.addRow(i18n.bi("Altura talon cercha:", "Truss heel height:"), truss_height_start)


    purlin_spacing = spin(settings["purlin_spacing_mm"], 50.0, 5000.0, 50.0)
    form.addRow(i18n.bi("Separacion clavadores:", "Purlin spacing:"), purlin_spacing)


    mode = QtWidgets.QComboBox()
    mode.addItem(i18n.bi("Mantener valor; primer/ultimo intervalo ajustado", "Keep value; adjust first/last interval"), "fixed")
    mode.addItem(i18n.bi("Calculada con nominal redondeado", "Calculated with rounded nominal"), "rounded")
    mode.setCurrentIndex(max(0, mode.findData(settings["purlin_distribution_mode"])))
    form.addRow(i18n.bi("Distribucion clavadores:", "Purlin distribution:"), mode)


    round_step = QtWidgets.QComboBox()
    round_step.addItem("50 mm (5 cm)", 50.0)
    round_step.addItem("100 mm (10 cm)", 100.0)
    round_step.setCurrentIndex(max(0, round_step.findData(float(settings["purlin_round_step_mm"]))))
    form.addRow(i18n.bi("Redondeo calculado:", "Calculated rounding:"), round_step)


    start_offset = spin(settings["purlin_start_offset_mm"], 0.0, 5000.0, 50.0)
    end_offset = spin(settings["purlin_end_offset_mm"], 0.0, 5000.0, 50.0)
    form.addRow(i18n.bi("Retiro desde alero:", "Offset from eave:"), start_offset)
    form.addRow(i18n.bi("Retiro desde cumbrera:", "Offset from ridge:"), end_offset)


    purlin_w = spin(settings["purlin_width_mm"], 10.0, 1000.0, 10.0)
    purlin_h = spin(settings["purlin_height_mm"], 10.0, 1000.0, 10.0)
    form.addRow(i18n.bi("Ancho seccion clavador:", "Purlin section width:"), purlin_w)
    form.addRow(i18n.bi("Alto seccion clavador:", "Purlin section height:"), purlin_h)


    overhang = spin(settings["overhang_mm"], 0.0, 5000.0, 50.0)
    thickness = spin(settings["roof_thickness_mm"], 1.0, 1000.0, 10.0)
    form.addRow(i18n.bi("Alero cubierta:", "Roof overhang:"), overhang)
    form.addRow(i18n.bi("Espesor cubierta:", "Roof thickness:"), thickness)


    note = QtWidgets.QLabel(i18n.bi(
        "Los valores aceptados se guardan como preferencias del Workbench.\n"
        "Huella, apoyo estructural y borde de cubierta se mantienen como referencias separadas.\n"
        "Si no se resuelven dos muros extremos, las cerchas usan el Rectangle como fallback.",
        "Accepted values are saved as Workbench preferences.\n"
        "Footprint, structural support and roof edge remain separate references.\n"
        "If two end walls cannot be resolved, trusses use the Rectangle as fallback.",
    ))
    note.setWordWrap(True)
    layout.addWidget(note)


    def sync_round_enabled():
        round_step.setEnabled(mode.currentData() == "rounded")
        truss_round_step.setEnabled(truss_mode.currentData() == "rounded")


    mode.currentIndexChanged.connect(sync_round_enabled)
    truss_mode.currentIndexChanged.connect(sync_round_enabled)
    sync_round_enabled()


    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout.addWidget(buttons)
    if dlg.exec() != QtWidgets.QDialog.Accepted:
        return None


    result = dict(settings)
    result.update(
        {
            "pitch_deg": pitch.value(),
            "ridge_mode": str(ridge.currentData()),
            "support_mode": str(support.currentData()),
            "truss_support_xy_mode": str(truss_support_xy.currentData()),
            "truss_support_adjust_mm": truss_support_adjust.value(),
            "truss_spacing_mm": truss_spacing.value(),
            "truss_distribution_mode": str(truss_mode.currentData()),
            "truss_round_step_mm": float(truss_round_step.currentData()),
            "truss_height_start_mm": truss_height_start.value(),
            "purlin_spacing_mm": purlin_spacing.value(),
            "purlin_distribution_mode": str(mode.currentData()),
            "purlin_round_step_mm": float(round_step.currentData()),
            "purlin_start_offset_mm": start_offset.value(),
            "purlin_end_offset_mm": end_offset.value(),
            "purlin_width_mm": purlin_w.value(),
            "purlin_height_mm": purlin_h.value(),
            "overhang_mm": overhang.value(),
            "roof_thickness_mm": thickness.value(),
        }
    )
    return result




def _rectangle_geometry(source, settings, support_z_mm=None):
    lx = float(source.Length.Value)
    ly = float(source.Height.Value)
    placement = App.Placement(source.Placement)
    u = placement.Rotation.multVec(App.Vector(1, 0, 0))
    v = placement.Rotation.multVec(App.Vector(0, 1, 0))
    u.normalize()
    v.normalize()
    origin = App.Vector(placement.Base)
    if support_z_mm is not None:
        origin.z = float(support_z_mm)
        placement.Base = App.Vector(origin)


    mode = settings["ridge_mode"]
    if mode == "length":
        ridge_dir, ridge_length = u, lx
        span_dir, span_length = v, ly
        span_is_length = False
    elif mode == "height":
        ridge_dir, ridge_length = v, ly
        span_dir, span_length = u, lx
        span_is_length = True
    else:
        if lx <= ly:
            ridge_dir, ridge_length = v, ly
            span_dir, span_length = u, lx
            span_is_length = True
        else:
            ridge_dir, ridge_length = u, lx
            span_dir, span_length = v, ly
            span_is_length = False


    return {
        "length_x_mm": lx,
        "length_y_mm": ly,
        "origin": origin,
        "u": u,
        "v": v,
        "ridge_dir": App.Vector(ridge_dir),
        "ridge_length_mm": float(ridge_length),
        "span_dir": App.Vector(span_dir),
        "span_length_mm": float(span_length),
        "span_is_length": bool(span_is_length),
        "support_z_mm": float(origin.z),
        "source_placement": placement,
    }




def _plan(settings, geom, truss_support):
    pitch = math.radians(float(settings["pitch_deg"]))
    if abs(math.cos(pitch)) < 1e-9:
        raise UserFacingError(i18n.bi("La pendiente indicada no es valida para este techo.", "The specified pitch is not valid for this roof."))
    span = geom["span_length_mm"]
    slope_len = (span * 0.5) / math.cos(pitch)
    truss_len = float(truss_support["support_length_mm"])
    if settings["truss_distribution_mode"] == "rounded":
        truss = plan_rounded_axis_distribution(
            truss_len,
            settings["truss_spacing_mm"],
            settings["truss_round_step_mm"],
            0.0,
            0.0,
        )
    else:
        truss = plan_fixed_axis_distribution(
            truss_len, settings["truss_spacing_mm"], 0.0, 0.0
        )
    truss["support_start_mm"] = float(truss_support["start_axis_mm"])
    truss["support_end_mm"] = float(truss_support["end_axis_mm"])
    truss["support_source"] = str(truss_support["source"])
    truss["support_adjust_mm"] = float(truss_support["adjust_mm"])

    if settings["purlin_start_offset_mm"] + settings["purlin_end_offset_mm"] >= slope_len:
        raise UserFacingError(
            "Los retiros de clavadores dejan sin longitud util el faldon (longitud %.1f mm)." % slope_len
        )
    if settings["purlin_distribution_mode"] == "rounded":
        purlin = plan_rounded_axis_distribution(
            slope_len,
            settings["purlin_spacing_mm"],
            settings["purlin_round_step_mm"],
            settings["purlin_start_offset_mm"],
            settings["purlin_end_offset_mm"],
        )
    else:
        purlin = plan_fixed_axis_distribution(
            slope_len,
            settings["purlin_spacing_mm"],
            settings["purlin_start_offset_mm"],
            settings["purlin_end_offset_mm"],
        )
    return {
        "pitch_rad": pitch,
        "slope_length_mm": slope_len,
        "truss": truss,
        "purlin": purlin,
        "truss_support": dict(truss_support),
    }



def _make_axis(label, layout, length, placement, role, source_name, side=""):
    axis = Arch.makeAxis(num=int(layout["axis_count"]), size=float(length), name=label)
    if axis is None:
        raise RuntimeError("Arch.makeAxis no pudo crear %s" % label)
    axis.Label = label
    axis.Distances = [float(v) for v in layout["distances_mm"]]
    axis.Angles = [0.0] * int(layout["axis_count"])
    axis.Length = float(length)
    axis.Placement = placement
    _tag(axis, role, source_name)
    props = [
        ("App::PropertyLength", "FA_RequestedSpacing", "Separacion solicitada"),
        ("App::PropertyLength", "FA_NominalSpacing", "Separacion nominal usada"),
        ("App::PropertyLength", "FA_MinInterval", "Intervalo minimo entre ejes"),
        ("App::PropertyLength", "FA_MaxInterval", "Intervalo maximo entre ejes"),
        ("App::PropertyLength", "FA_StartOffset", "Retiro inicial"),
        ("App::PropertyLength", "FA_EndOffset", "Retiro final"),
        ("App::PropertyString", "FA_DistributionMode", "Modo de distribucion"),
        ("App::PropertyString", "FA_RoofSide", "Faldon"),
    ]
    for ptype, name, desc in props:
        if name not in axis.PropertiesList:
            axis.addProperty(ptype, name, "FA Techo", desc)
    axis.FA_RequestedSpacing = float(layout["max_spacing_mm"])
    axis.FA_NominalSpacing = float(layout["spacing_mm"])
    axis.FA_MinInterval = float(layout["min_interval_mm"])
    axis.FA_MaxInterval = float(layout["max_interval_mm"])
    axis.FA_StartOffset = float(layout["start_offset_mm"])
    axis.FA_EndOffset = float(layout["end_offset_mm"])
    axis.FA_DistributionMode = str(layout.get("mode", ""))
    axis.FA_RoofSide = str(side)
    if "round_step_mm" in layout:
        if "FA_RoundStep" not in axis.PropertiesList:
            axis.addProperty("App::PropertyLength", "FA_RoundStep", "FA Techo", "Paso de redondeo")
        axis.FA_RoundStep = float(layout["round_step_mm"])
    try:
        axis.ViewObject.NumberingStyle = "01,02,03"
        axis.ViewObject.BubblePosition = "Start"
        axis.ViewObject.DrawStyle = "Dashdot"
        axis.ViewObject.Visibility = True
    except Exception:
        pass
    return axis




def _tag(obj, role, source_name):
    if "FA_Generator" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "FA_Generator", "FA Techo", "Generador")
    if "FA_SourceName" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "FA_SourceName", "FA Techo", "Name de la fuente")
    if "FA_Role" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "FA_Role", "FA Techo", "Rol")
    obj.FA_Generator = GENERATOR
    obj.FA_SourceName = str(source_name)
    obj.FA_Role = str(role)




def _remove_previous(doc, source_name):
    matches = [
        obj
        for obj in list(doc.Objects)
        if str(getattr(obj, "FA_Generator", "")) == GENERATOR
        and str(getattr(obj, "FA_SourceName", "")) == str(source_name)
    ]
    matches.sort(key=lambda obj: len(list(getattr(obj, "OutListRecursive", []) or [])))
    removed = 0
    for obj in matches:
        if doc.getObject(obj.Name) is not None:
            doc.removeObject(obj.Name)
            removed += 1
    if removed:
        doc.recompute()
    return removed




def _make_trusses(doc, group, geom, plan, settings, source_name):
    support = plan["truss_support"]
    axis_origin = App.Vector(geom["origin"]).add(
        App.Vector(geom["ridge_dir"]).multiply(float(support["start_axis_mm"]))
    )
    axis = _make_axis(
        "Ejes de cerchas",
        plan["truss"],
        geom["span_length_mm"],
        App.Placement(axis_origin, _axis_rotation(geom["ridge_dir"], geom["span_dir"])),
        "TRUSS_AXIS",
        source_name,
    )
    for ptype, name, desc, value in [
        ("App::PropertyString", "FA_SupportSource", "Referencia de apoyo XY", str(support["source"])),
        ("App::PropertyLength", "FA_SupportStart", "Eje extremo inicial", float(support["start_axis_mm"])),
        ("App::PropertyLength", "FA_SupportEnd", "Eje extremo final", float(support["end_axis_mm"])),
        ("App::PropertyLength", "FA_SupportAdjust", "Ajuste simetrico de apoyo", float(support["adjust_mm"])),
    ]:
        if name not in axis.PropertiesList:
            axis.addProperty(ptype, name, "FA Techo", desc)
        setattr(axis, name, value)
    group.addObject(axis)


    # ArchTruss construye el cordon inferior hacia arriba desde su Base; esa linea
    # es el plano de apoyo y debe quedar exactamente en support_z.
    p0 = App.Vector(0, 0, 0)
    p1 = App.Vector(geom["span_dir"]).multiply(geom["span_length_mm"]).add(p0)
    base = _draft_line(p0, p1)
    if base is None:
        raise RuntimeError("No se pudo crear Base cercha")
    base.Label = "Base cercha"
    _tag(base, "TRUSS_BASE", source_name)


    truss = Arch.makeTruss(base)
    if truss is None:
        raise RuntimeError("Arch.makeTruss no pudo crear la cercha")
    truss.Label = "Cerchas BIM"
    truss.SlantType = "Double"
    truss.Normal = App.Vector(0, 0, 1)
    truss.HeightStart = float(settings["truss_height_start_mm"])
    truss.HeightEnd = float(settings["truss_height_start_mm"]) + (
        geom["span_length_mm"] * 0.5 * math.tan(plan["pitch_rad"])
    )
    truss.StrutHeight = float(settings["strut_height_mm"])
    truss.StrutWidth = float(settings["strut_width_mm"])
    truss.RodType = str(settings["rod_type"])
    truss.RodDirection = str(settings["rod_direction"])
    truss.RodSize = float(settings["rod_size_mm"])
    truss.RodSections = int(settings["rod_sections"])
    truss.RodEnd = bool(settings["rod_end"])
    truss.RodMode = str(settings["rod_mode"])
    truss.Axis = axis
    _tag(truss, "TRUSSES", source_name)
    group.addObject(truss)
    return axis, base, truss




def _make_purlin_side(doc, group, geom, plan, settings, source_name, side):
    pitch = plan["pitch_rad"]
    span_dir = App.Vector(geom["span_dir"])
    ridge_dir = App.Vector(geom["ridge_dir"])
    origin = App.Vector(geom["origin"]).add(
        App.Vector(0, 0, float(settings["truss_height_start_mm"]))
    )
    if side == "LEFT":
        slope_dir = App.Vector(span_dir).multiply(math.cos(pitch)).add(
            App.Vector(0, 0, math.sin(pitch))
        )
        normal = App.Vector(span_dir).multiply(-math.sin(pitch)).add(
            App.Vector(0, 0, math.cos(pitch))
        )
        axis_origin = origin
        label_side = "izquierdo"
    else:
        slope_dir = App.Vector(span_dir).multiply(-math.cos(pitch)).add(
            App.Vector(0, 0, math.sin(pitch))
        )
        normal = App.Vector(span_dir).multiply(math.sin(pitch)).add(
            App.Vector(0, 0, math.cos(pitch))
        )
        axis_origin = origin.add(App.Vector(span_dir).multiply(geom["span_length_mm"]))
        label_side = "derecho"
    slope_dir.normalize()
    normal.normalize()


    axis = _make_axis(
        "Ejes clavadores - faldon %s" % label_side,
        plan["purlin"],
        geom["ridge_length_mm"],
        App.Placement(axis_origin, _axis_rotation(slope_dir, ridge_dir)),
        "PURLIN_AXIS",
        source_name,
        side=side,
    )
    group.addObject(axis)
    doc.recompute()


    section_x = normal.cross(ridge_dir)
    section_x.normalize()
    section_origin = App.Vector(section_x).multiply(-float(settings["purlin_width_mm"]) * 0.5)
    section = _draft_rectangle(
        settings["purlin_width_mm"],
        settings["purlin_height_mm"],
        App.Placement(section_origin, _axis_rotation(section_x, normal)),
        face=True,
    )
    if section is None:
        raise RuntimeError("No se pudo crear la seccion del clavador %s" % side)
    section.Label = "Seccion clavador - faldon %s" % label_side
    _tag(section, "PURLIN_SECTION", source_name)


    beam = Arch.makeStructure(
        section,
        length=float(geom["ridge_length_mm"]),
        name="FA_Purlins_%s" % side,
    )
    if beam is None:
        raise RuntimeError("Arch.makeStructure no pudo crear clavadores %s" % side)
    beam.Label = "Clavadores BIM - faldon %s" % label_side
    beam.Placement = App.Placement()
    beam.Axis = axis
    try:
        beam.IfcType = "Beam"
    except Exception:
        pass
    _tag(beam, "PURLINS", source_name)
    if "FA_RoofSide" not in beam.PropertiesList:
        beam.addProperty("App::PropertyString", "FA_RoofSide", "FA Techo", "Faldon")
    if "FA_ExpectedCount" not in beam.PropertiesList:
        beam.addProperty("App::PropertyInteger", "FA_ExpectedCount", "FA Techo", "Cantidad esperada")
    beam.FA_RoofSide = side
    beam.FA_ExpectedCount = int(plan["purlin"]["axis_count"])
    group.addObject(beam)
    doc.recompute()
    try:
        section.ViewObject.Visibility = False
        axis.ViewObject.Visibility = True
    except Exception:
        pass
    return axis, section, beam




def _make_roof(doc, group, source, geom, plan, settings, source_name):
    vertical_offset = (
        float(settings["truss_height_start_mm"])
        + float(settings["purlin_height_mm"]) / math.cos(plan["pitch_rad"])
    )
    placement = App.Placement(geom["source_placement"])
    placement.Base = placement.Base.add(App.Vector(0, 0, vertical_offset))
    base = _draft_rectangle(
        geom["length_x_mm"],
        geom["length_y_mm"],
        placement,
        face=False,
    )
    if base is None:
        raise RuntimeError("No se pudo crear Base cubierta")
    base.Label = "Base cubierta"
    _tag(base, "ROOF_BASE", source_name)


    # Arch.makeRoof only initializes its per-edge lists when the Base already
    # exposes a closed wire. A freshly created Draft Rectangle needs an
    # explicit recompute before it can safely be used as Roof.Base.
    base.recompute()
    base_shape = getattr(base, "Shape", None)
    base_wires = list(getattr(base_shape, "Wires", []) or []) if base_shape is not None else []
    if (
        base_shape is None
        or base_shape.isNull()
        or not base_wires
        or not base_wires[0].isClosed()
    ):
        raise RuntimeError("Base cubierta no produjo un Wire cerrado antes de Arch.makeRoof")


    pitch = float(settings["pitch_deg"])
    run = geom["span_length_mm"] * 0.5
    if geom["span_is_length"]:
        angles = [90.0, pitch, 90.0, pitch]
        runs = [0.0, run, 0.0, run]
    else:
        angles = [pitch, 90.0, pitch, 90.0]
        runs = [run, 0.0, run, 0.0]


    roof = Arch.makeRoof(
        base,
        angles=angles,
        run=runs,
        thickness=[float(settings["roof_thickness_mm"])] * 4,
        overhang=[float(settings["overhang_mm"])] * 4,
        name="FA_RoofFromRectangle",
    )
    if roof is None:
        raise RuntimeError("Arch.makeRoof no pudo crear la cubierta")
    roof.Label = "Cubierta BIM"
    _tag(roof, "ROOF", source_name)
    for ptype, name, desc, value in [
        ("App::PropertyAngle", "FA_Pitch", "Pendiente nominal", float(settings["pitch_deg"])),
        ("App::PropertyLength", "FA_Overhang", "Alero nominal", float(settings["overhang_mm"])),
        ("App::PropertyLength", "FA_RoofThickness", "Espesor nominal", float(settings["roof_thickness_mm"])),
        ("App::PropertyLength", "FA_SupportElevation", "Cota de apoyo", float(geom["support_z_mm"])),
    ]:
        if name not in roof.PropertiesList:
            roof.addProperty(ptype, name, "FA Techo", desc)
        setattr(roof, name, value)
    group.addObject(roof)
    try:
        base.ViewObject.Visibility = False
        roof.ViewObject.Transparency = 65
    except Exception:
        pass
    return base, roof




def _shape_ok(obj):
    try:
        return (not obj.Shape.isNull()) and obj.Shape.isValid()
    except Exception:
        return False




def _solid_count(obj):
    try:
        return len(obj.Shape.Solids)
    except Exception:
        return 0




def _distance(a, b):
    try:
        return float(a.Shape.distToShape(b.Shape)[0])
    except Exception:
        return float("inf")




def _bbox_xy_overlap(a, b, tol=1.0):
    return not (
        a.XMax < b.XMin - tol
        or a.XMin > b.XMax + tol
        or a.YMax < b.YMin - tol
        or a.YMin > b.YMax + tol
    )




def _global_placement(obj):
    try:
        return App.Placement(obj.getGlobalPlacement())
    except Exception:
        try:
            return App.Placement(obj.Placement)
        except Exception:
            return App.Placement()


def _edge_world_endpoints(owner, edge):
    vertices = list(getattr(edge, "Vertexes", []) or [])
    if len(vertices) < 2:
        return None
    placement = _global_placement(owner)
    return (
        placement.multVec(App.Vector(vertices[0].Point)),
        placement.multVec(App.Vector(vertices[-1].Point)),
    )


def _local_roof_coordinates(point, geom):
    rel = App.Vector(point).sub(App.Vector(geom["origin"]))
    return (
        float(rel.dot(App.Vector(geom["ridge_dir"]))),
        float(rel.dot(App.Vector(geom["span_dir"]))),
    )


def _wall_axis_candidates(wall_info, geom):
    """Extract transverse wall centerline positions from native Wall.Base geometry.

    FA walls use the source Sketch directly as Wall.Base. Reading those edges gives
    a better structural reference than the wall bounding box and also works when a
    single Wall object contains the whole perimeter.
    """
    ridge_dir = App.Vector(geom["ridge_dir"])
    span_dir = App.Vector(geom["span_dir"])
    ridge_len = float(geom["ridge_length_mm"])
    span_len = float(geom["span_length_mm"])
    raw = []

    for wall in list(wall_info.get("walls") or []):
        base = getattr(wall, "Base", None)
        if isinstance(base, (tuple, list)) and base:
            base = base[0]
        owner = base if base is not None and hasattr(base, "Shape") else wall
        shape = getattr(owner, "Shape", None)
        edges = list(getattr(shape, "Edges", []) or []) if shape is not None else []
        for edge in edges:
            endpoints = _edge_world_endpoints(owner, edge)
            if endpoints is None:
                continue
            p0, p1 = endpoints
            chord = p1.sub(p0)
            horizontal = App.Vector(chord.x, chord.y, 0.0)
            if horizontal.Length <= 1e-6:
                continue
            direction = App.Vector(horizontal)
            direction.normalize()
            # End support walls run essentially across the roof span, therefore
            # they are perpendicular to the ridge direction.
            span_alignment = abs(float(direction.dot(span_dir)))
            ridge_alignment = abs(float(direction.dot(ridge_dir)))
            if span_alignment < 0.90 or ridge_alignment > 0.45:
                continue
            r0, s0 = _local_roof_coordinates(p0, geom)
            r1, s1 = _local_roof_coordinates(p1, geom)
            span_min, span_max = sorted((s0, s1))
            if span_max < -25.0 or span_min > span_len + 25.0:
                continue
            r = 0.5 * (r0 + r1)
            if -1500.0 <= r <= ridge_len + 1500.0:
                raw.append(float(r))

    # Collapse duplicate/coincident Sketch edges without losing millimetric intent.
    unique = []
    for value in sorted(raw):
        if not unique or abs(value - unique[-1]) > 1.0:
            unique.append(value)
    return unique


def _resolve_truss_support(settings, geom, wall_info):
    ridge_len = float(geom["ridge_length_mm"])
    source = "rectangle"
    start = 0.0
    end = ridge_len
    candidates = _wall_axis_candidates(wall_info, geom)
    selected = None
    if settings.get("truss_support_xy_mode") == "walls_if_available" and candidates:
        selected = select_end_support_axes(
            candidates,
            ridge_len,
            settings.get("truss_support_edge_tolerance_mm", 1000.0),
        )
        if selected is not None:
            source = "walls"
            start = float(selected["start_axis_mm"])
            end = float(selected["end_axis_mm"])

    adjusted = apply_symmetric_support_adjust(
        start, end, settings.get("truss_support_adjust_mm", 0.0)
    )
    return {
        "source": source,
        "start_axis_mm": float(adjusted["start_axis_mm"]),
        "end_axis_mm": float(adjusted["end_axis_mm"]),
        "support_length_mm": float(adjusted["support_length_mm"]),
        "adjust_mm": float(adjusted["adjust_mm"]),
        "wall_candidates_mm": [float(v) for v in candidates],
        "wall_selection": selected,
    }


def _wall_support_info(doc, source, tolerance_mm=25.0):
    """Read-only diagnostic of BIM wall crowns below the selected footprint."""
    try:
        src_bb = source.Shape.BoundBox
    except Exception:
        return {
            "count": 0, "top_z_mm": None, "delta_mm": None, "spread_mm": None,
            "consistent": False, "walls": [],
        }
    tops = []
    walls = []
    for obj in list(doc.Objects):
        if obj is source:
            continue
        try:
            dtype = Draft.getType(obj)
        except Exception:
            dtype = ""
        if dtype != "Wall" and "wall" not in str(getattr(obj, "IfcType", "")).lower():
            continue
        try:
            if obj.Shape.isNull():
                continue
            bb = obj.Shape.BoundBox
            if _bbox_xy_overlap(src_bb, bb, tol=10.0):
                tops.append(float(bb.ZMax))
                walls.append(obj)
        except Exception:
            continue
    if not tops:
        return {
            "count": 0, "top_z_mm": None, "delta_mm": None, "spread_mm": None,
            "consistent": False, "walls": [],
        }
    top = float(statistics.median(tops))
    spread = float(max(tops) - min(tops))
    return {
        "count": len(tops),
        "top_z_mm": top,
        "delta_mm": float(source.Placement.Base.z) - top,
        "spread_mm": spread,
        "consistent": spread <= float(tolerance_mm),
        "walls": walls,
    }




def _support_elevation(settings, source, wall_info):
    source_z = float(source.Placement.Base.z)
    if settings.get("support_mode") == "walls_if_consistent":
        if wall_info.get("count") and wall_info.get("consistent"):
            return float(wall_info["top_z_mm"]), "walls"
        if wall_info.get("count") and not wall_info.get("consistent"):
            warn(
                "FA Techo: los muros BIM detectados tienen coronaciones dispersas (%.1f mm); "
                "se conserva la Z del rectangulo." % float(wall_info.get("spread_mm") or 0.0)
            )
    return source_z, "rectangle"




def _validate_created(truss, left_beam, right_beam, roof, expected_purlins):
    checks = {
        "truss": _shape_ok(truss),
        "left_beam": _shape_ok(left_beam),
        "right_beam": _shape_ok(right_beam),
        "roof": _shape_ok(roof),
    }
    if not all(checks.values()):
        raise RuntimeError("La geometria creada no es valida: %s" % checks)
    left_solids = _solid_count(left_beam)
    right_solids = _solid_count(right_beam)
    if left_solids < int(expected_purlins) or right_solids < int(expected_purlins):
        raise RuntimeError(
            "Los clavadores no se materializaron completos: LEFT=%d RIGHT=%d esperados=%d"
            % (left_solids, right_solids, int(expected_purlins))
        )
    return checks, left_solids, right_solids





def create_roof_from_rectangle_programmatic(
    source,
    settings_override=None,
    level=None,
    manage_transaction=True,
    save_preferences=False,
    select_output=False,
    fit_view=False,
    feedback=None,
):
    """Create the current FA roof system from a Draft Rectangle without dialogs.

    This adapter exists for demos, MCP and other internal workflows that already
    validated their inputs.  It reuses the same native Axis/Truss/Structure/Roof
    implementation as the toolbar command and deliberately does not alter user
    preferences unless ``save_preferences`` is true.
    """
    source = _require_selected_rectangle([source])
    wall_info = _wall_support_info(source.Document, source)
    settings = _read_settings()
    for key, value in dict(settings_override or {}).items():
        if key in settings:
            settings[key] = value
    support_z, support_source = _support_elevation(settings, source, wall_info)
    geom = _rectangle_geometry(source, settings, support_z_mm=support_z)
    truss_support = _resolve_truss_support(settings, geom, wall_info)
    plan = _plan(settings, geom, truss_support)
    if save_preferences:
        _save_settings(settings)

    doc = source.Document
    opened = False
    try:
        if manage_transaction:
            opened = open_transaction(doc, "FA Techo desde rectangulo")
        if level is None:
            level = ensure_target_level(doc, list(wall_info.get("walls") or []))
        group = ensure_roof_container(level)
        removed = _remove_previous(doc, source.Name)

        truss_axis, truss_base, truss = _make_trusses(
            doc, group, geom, plan, settings, source.Name
        )
        if feedback is not None:
            feedback.stage("Creando clavadores")
        left_axis, left_section, left_beam = _make_purlin_side(
            doc, group, geom, plan, settings, source.Name, "LEFT"
        )
        right_axis, right_section, right_beam = _make_purlin_side(
            doc, group, geom, plan, settings, source.Name, "RIGHT"
        )
        if feedback is not None:
            feedback.stage("Creando cubierta BIM")
        roof_base, roof = _make_roof(
            doc, group, source, geom, plan, settings, source.Name
        )
        if feedback is not None:
            feedback.stage("Recomputando y validando geometria")
        doc.recompute()

        checks, left_solids, right_solids = _validate_created(
            truss, left_beam, right_beam, roof, plan["purlin"]["axis_count"]
        )
        truss_support_z = float(truss.Shape.BoundBox.ZMin)
        truss_support_delta = truss_support_z - float(geom["support_z_mm"])
        if abs(truss_support_delta) > 1e-5:
            raise RuntimeError(
                "La Base inferior de las cerchas no coincide con la cota de apoyo: "
                "base=%.6f apoyo=%.6f delta=%.6f mm"
                % (truss_support_z, geom["support_z_mm"], truss_support_delta)
            )

        first_axis_mm = float(plan["truss_support"]["start_axis_mm"]) + float(
            plan["truss"]["positions_mm"][0]
        )
        last_axis_mm = float(plan["truss_support"]["start_axis_mm"]) + float(
            plan["truss"]["positions_mm"][-1]
        )
        first_axis_delta = first_axis_mm - float(plan["truss_support"]["start_axis_mm"])
        last_axis_delta = last_axis_mm - float(plan["truss_support"]["end_axis_mm"])
        if abs(first_axis_delta) > 1e-5 or abs(last_axis_delta) > 1e-5:
            raise RuntimeError(
                "Los ejes extremos de cerchas no coinciden con sus apoyos: "
                "inicio delta=%.6f fin delta=%.6f mm"
                % (first_axis_delta, last_axis_delta)
            )

        left_roof_distance = _distance(left_beam, roof)
        left_truss_distance = _distance(left_beam, truss)
        right_roof_distance = _distance(right_beam, roof)
        right_truss_distance = _distance(right_beam, truss)
        if max(
            left_roof_distance,
            left_truss_distance,
            right_roof_distance,
            right_truss_distance,
        ) > 0.1:
            raise RuntimeError(
                "Se perdio continuidad geometrica techo/clavadores/cerchas: "
                "LEFT techo=%.6f cerchas=%.6f RIGHT techo=%.6f cerchas=%.6f mm"
                % (
                    left_roof_distance,
                    left_truss_distance,
                    right_roof_distance,
                    right_truss_distance,
                )
            )

        if manage_transaction:
            finish_transaction(doc, opened, commit=True)
            opened = False

        _log(
            "Creacion programatica fuente=%s | %.1fx%.1f mm | cerchas=%d | clavadores=%d/faldon | roof=%s"
            % (
                source.Name,
                geom["length_x_mm"],
                geom["length_y_mm"],
                plan["truss"]["axis_count"],
                plan["purlin"]["axis_count"],
                checks["roof"],
            )
        )
        if removed:
            _log("Creacion programatica reemplazo %d objetos previos" % removed)
        if select_output:
            select_results([truss_axis, truss, left_axis, left_beam, right_axis, right_beam, roof])
        if fit_view:
            try:
                FreeCADGui.activeDocument().activeView().viewAxonometric()
                FreeCADGui.activeDocument().activeView().fitAll()
            except Exception:
                pass
        return {
            "source": source,
            "group": group,
            "truss_axis": truss_axis,
            "truss_base": truss_base,
            "truss": truss,
            "left_axis": left_axis,
            "left_section": left_section,
            "left_beam": left_beam,
            "right_axis": right_axis,
            "right_section": right_section,
            "right_beam": right_beam,
            "roof_base": roof_base,
            "roof": roof,
            "plan": plan,
            "wall_info": wall_info,
            "settings": dict(settings),
            "support_source": support_source,
        }
    except Exception:
        if manage_transaction:
            finish_transaction(doc, opened, commit=False)
        raise

def _run_from_rectangle():
    selection = current_selection()
    source = _require_selected_rectangle(selection)
    wall_info = _wall_support_info(source.Document, source)
    settings = _show_settings_dialog(_read_settings(), source, wall_info)
    if settings is None:
        return None
    support_z, support_source = _support_elevation(settings, source, wall_info)
    geom = _rectangle_geometry(source, settings, support_z_mm=support_z)
    truss_support = _resolve_truss_support(settings, geom, wall_info)
    plan = _plan(settings, geom, truss_support)
    # Guardar preferencias solo cuando la entrada completa ya es valida.
    _save_settings(settings)


    doc = source.Document
    opened = False
    feedback = LongOperationFeedback("FA Techo desde rectangulo", "Preparando estructura de techo").start()
    try:
        opened = open_transaction(doc, "FA Techo desde rectangulo")
        level_selection = list(selection) + list(wall_info.get("walls") or [])
        level = ensure_target_level(doc, level_selection)
        group = ensure_roof_container(level)
        removed = _remove_previous(doc, source.Name)

        feedback.stage("Creando ejes y cerchas")
        truss_axis, truss_base, truss = _make_trusses(
            doc, group, geom, plan, settings, source.Name
        )
        left_axis, left_section, left_beam = _make_purlin_side(
            doc, group, geom, plan, settings, source.Name, "LEFT"
        )
        right_axis, right_section, right_beam = _make_purlin_side(
            doc, group, geom, plan, settings, source.Name, "RIGHT"
        )
        roof_base, roof = _make_roof(
            doc, group, source, geom, plan, settings, source.Name
        )
        doc.recompute()


        checks, left_solids, right_solids = _validate_created(
            truss, left_beam, right_beam, roof, plan["purlin"]["axis_count"]
        )
        truss_support_z = float(truss.Shape.BoundBox.ZMin)
        truss_support_delta = truss_support_z - float(geom["support_z_mm"])
        if abs(truss_support_delta) > 1e-5:
            raise RuntimeError(
                "La Base inferior de las cerchas no coincide con la cota de apoyo: "
                "base=%.6f apoyo=%.6f delta=%.6f mm"
                % (truss_support_z, geom["support_z_mm"], truss_support_delta)
            )

        first_axis_mm = float(plan["truss_support"]["start_axis_mm"]) + float(plan["truss"]["positions_mm"][0])
        last_axis_mm = float(plan["truss_support"]["start_axis_mm"]) + float(plan["truss"]["positions_mm"][-1])
        first_axis_delta = first_axis_mm - float(plan["truss_support"]["start_axis_mm"])
        last_axis_delta = last_axis_mm - float(plan["truss_support"]["end_axis_mm"])
        if abs(first_axis_delta) > 1e-5 or abs(last_axis_delta) > 1e-5:
            raise RuntimeError(
                "Los ejes extremos de cerchas no coinciden con sus apoyos: "
                "inicio delta=%.6f fin delta=%.6f mm" % (first_axis_delta, last_axis_delta)
            )

        left_roof_distance = _distance(left_beam, roof)
        left_truss_distance = _distance(left_beam, truss)
        right_roof_distance = _distance(right_beam, roof)
        right_truss_distance = _distance(right_beam, truss)
        if max(left_roof_distance, left_truss_distance, right_roof_distance, right_truss_distance) > 0.1:
            raise RuntimeError(
                "Se perdio continuidad geometrica techo/clavadores/cerchas: "
                "LEFT techo=%.6f cerchas=%.6f RIGHT techo=%.6f cerchas=%.6f mm"
                % (left_roof_distance, left_truss_distance, right_roof_distance, right_truss_distance)
            )

        wall_contact_distance = float("inf")
        if wall_info.get("walls"):
            wall_contact_distance = min(_distance(truss, wall) for wall in wall_info["walls"])

        finish_transaction(doc, opened, commit=True)
        opened = False


        _log(
            "Fuente=%s | %.1f x %.1f mm | Z apoyo=%.1f (%s) | span=%.1f | ridge=%.1f"
            % (
                source.Name,
                geom["length_x_mm"],
                geom["length_y_mm"],
                geom["support_z_mm"],
                support_source,
                geom["span_length_mm"],
                geom["ridge_length_mm"],
            )
        )
        _log(
            "Cerchas: modo=%s | %d ejes | solicitado %.1f | nominal %.1f | min/max %.1f/%.1f mm"
            % (
                plan["truss"]["mode"],
                plan["truss"]["axis_count"],
                settings["truss_spacing_mm"],
                plan["truss"]["spacing_mm"],
                plan["truss"]["min_interval_mm"],
                plan["truss"]["max_interval_mm"],
            )
        )
        _log(
            "Apoyo XY cerchas: fuente=%s | inicio=%.1f | fin=%.1f | longitud=%.1f | ajuste=%.1f mm | candidatos muro=%s"
            % (
                plan["truss_support"]["source"],
                plan["truss_support"]["start_axis_mm"],
                plan["truss_support"]["end_axis_mm"],
                plan["truss_support"]["support_length_mm"],
                plan["truss_support"]["adjust_mm"],
                ",".join("%.1f" % v for v in plan["truss_support"].get("wall_candidates_mm", [])) or "ninguno",
            )
        )
        _log(
            "Clavadores: modo=%s | %d ejes/faldon | solicitado %.1f | nominal %.1f | min/max %.1f/%.1f mm"
            % (
                plan["purlin"]["mode"],
                plan["purlin"]["axis_count"],
                settings["purlin_spacing_mm"],
                plan["purlin"]["spacing_mm"],
                plan["purlin"]["min_interval_mm"],
                plan["purlin"]["max_interval_mm"],
            )
        )
        _log("Formas validas=%s | solidos clavadores LEFT=%d RIGHT=%d" % (checks, left_solids, right_solids))
        _log(
            "Apoyo cerchas: base=%.6f | objetivo=%.6f | delta=%.6f mm"
            % (truss_support_z, geom["support_z_mm"], truss_support_delta)
        )
        _log(
            "Distancias: LEFT techo=%.6f cerchas=%.6f | RIGHT techo=%.6f cerchas=%.6f mm"
            % (left_roof_distance, left_truss_distance, right_roof_distance, right_truss_distance)
        )
        if wall_info.get("walls"):
            _log("Distancia cerchas-muros BIM=%.6f mm" % wall_contact_distance)
        if settings.get("truss_support_xy_mode") == "walls_if_available" and plan["truss_support"]["source"] != "walls":
            warn(
                "FA Techo: no se resolvieron dos ejes de muro cercanos a los extremos; "
                "las cerchas extremas usan el Rectangle como fallback."
            )
        if removed:
            _log("Reemplazados %d objetos previos de la misma huella" % removed)
        if wall_info["count"]:
            _log(
                "Muros BIM bajo la huella: %d | coronacion mediana=%.1f | dispersion=%.1f | diferencia rectangulo-muros=%.1f mm"
                % (
                    wall_info["count"], wall_info["top_z_mm"], wall_info["spread_mm"],
                    wall_info["delta_mm"],
                )
            )
            if abs(wall_info["delta_mm"]) > 25.0 and support_source == "rectangle":
                warn(
                    "FA Techo: la huella esta %.1f mm respecto a la cota superior mediana de los muros BIM detectados."
                    % wall_info["delta_mm"]
                )


        select_results([truss_axis, truss, left_axis, left_beam, right_axis, right_beam, roof])
        msg(
            "FA Techo desde rectangulo: %d cerchas | %d clavadores por faldon | Level: %s"
            % (plan["truss"]["axis_count"], plan["purlin"]["axis_count"], level.Label)
        )
        try:
            FreeCADGui.activeDocument().activeView().viewAxonometric()
            FreeCADGui.activeDocument().activeView().fitAll()
        except Exception:
            pass
        feedback.finish(success=True)
        return {
            "source": source,
            "group": group,
            "truss_axis": truss_axis,
            "truss": truss,
            "left_axis": left_axis,
            "left_beam": left_beam,
            "right_axis": right_axis,
            "right_beam": right_beam,
            "roof": roof,
            "plan": plan,
            "wall_info": wall_info,
        }
    except Exception as exc:
        feedback.finish(success=False, error=str(exc))
        finish_transaction(doc, opened, commit=False)
        raise




class CommandClass:
    # Se conserva el ID historico durante esta transicion para que el hot-reload
    # reemplace el boton existente sin dejar dos comandos visibles.
    CommandName = "FA_RoofAxisPrototype"


    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Techo desde rectangulo", "FA Roof from rectangle"),
            "ToolTip": i18n.bi(
                "Seleccione un Draft Rectangle horizontal colocado sobre los muros. "
                "Crea ejes, cerchas, clavadores BIM y cubierta usando preferencias editables.",
                "Select a horizontal Draft Rectangle placed over the walls. "
                "Creates axes, trusses, BIM purlins and roof covering using editable preferences.",
            ),
            "Pixmap": ICON_PATH,
        }


    def Activated(self):  # noqa: N802
        try:
            _run_from_rectangle()
        except Exception as exc:
            handle_command_exception(i18n.bi("FA Techo desde rectangulo", "FA Roof from rectangle"), exc)


    def IsActive(self):  # noqa: N802
        return App.ActiveDocument is not None




def register():
    # FreeCAD 1.1.3 no expone removeCommand(). El proxy estable resuelve
    # CommandClass desde el modulo vigente en cada uso y evita ejecutar
    # implementaciones obsoletas despues del hot-reload.
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command