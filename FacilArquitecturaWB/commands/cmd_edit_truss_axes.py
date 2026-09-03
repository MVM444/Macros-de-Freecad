"""Editor sencillo de ejes de cerchas para Facil Arquitectura.

Nombre: cmd_edit_truss_axes.py
Proposito: editar de forma amigable la distribucion del Arch Axis nativo usado por
las cerchas de FA Techo, sin recurrir al editor BIM de ejes.
Funcion principal: seleccionar Ejes de cerchas o Cerchas BIM, calcular una nueva
lista ``Distances`` con los planificadores del nucleo y aplicarla al mismo Arch Axis.
FreeCAD objetivo: 1.1.3.
Version: 0.1.1
Fecha y hora: 2026-08-31 13:36 America/Costa_Rica

Instrucciones de mantenimiento:
- No sustituir Arch Axis ni crear geometria paralela.
- Mantener este comando como adaptador GUI; reutilizar axis_distribution_core.
- Trabajar dentro de transaccion y conservar el eje/cercha existentes.
- Aceptar tambien la seleccion de la cercha resolviendo su propiedad Axis.
- No modificar clavadores, cubierta, pendiente ni apoyos estructurales.
"""

from __future__ import annotations

import os

import FreeCAD as App
import FreeCADGui

from .. import i18n
from .roof_command_common import finish_transaction, open_transaction
from ..core.axis_distribution_core import (
    plan_fixed_axis_distribution,
    plan_rounded_axis_distribution,
    plan_uniform_axis_distribution,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import msg
from ..core.reloadable_command import ReloadableCommandProxy


COMMAND_NAME = "FA_EditTrussAxes"
LOG = "[FA EJES CERCHAS] "

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "edit_truss_axes.svg")
).replace(os.sep, "/")



def _log(text):
    App.Console.PrintMessage(LOG + str(text) + "\n")


def _is_truss_axis(obj):
    return bool(
        obj is not None
        and hasattr(obj, "Distances")
        and hasattr(obj, "Angles")
        and str(getattr(obj, "FA_Role", "")) == "TRUSS_AXIS"
    )


def _resolve_axis_from_object(obj):
    if _is_truss_axis(obj):
        return obj
    axis = getattr(obj, "Axis", None) if obj is not None else None
    if _is_truss_axis(axis):
        return axis
    return None


def _require_truss_axis():
    doc = App.ActiveDocument
    if doc is None:
        raise UserFacingError("No hay un documento activo.")
    selection = list(FreeCADGui.Selection.getSelection() or [])
    axes = []
    for obj in selection:
        axis = _resolve_axis_from_object(obj)
        if axis is not None and axis not in axes:
            axes.append(axis)
    if not axes and not selection:
        axes = [obj for obj in doc.Objects if _is_truss_axis(obj)]
    if len(axes) != 1:
        raise UserFacingError(
            "Seleccione exactamente 'Ejes de cerchas' o la correspondiente 'Cerchas BIM'."
        )
    return axes[0]


def _float_value(value, default=0.0):
    try:
        return float(value.Value if hasattr(value, "Value") else value)
    except Exception:
        return float(default)


def _positions_from_distances(distances):
    out = []
    acc = 0.0
    for value in list(distances or []):
        acc += float(value)
        out.append(acc)
    return out


def _axis_state(axis):
    distances = [float(v) for v in list(axis.Distances or [])]
    if not distances:
        raise UserFacingError("El eje seleccionado no contiene distancias editables.")
    positions = _positions_from_distances(distances)
    support_start = _float_value(getattr(axis, "FA_SupportStart", 0.0), 0.0)
    support_end = _float_value(getattr(axis, "FA_SupportEnd", 0.0), 0.0)
    support_length = support_end - support_start
    if support_length <= 1e-6:
        support_length = float(positions[-1])
    start_offset = max(0.0, float(positions[0]))
    end_offset = max(0.0, float(support_length - positions[-1]))
    requested = _float_value(getattr(axis, "FA_RequestedSpacing", 0.0), 0.0)
    if requested <= 1e-6:
        intervals = [float(v) for v in distances[1:]]
        requested = max(intervals) if intervals else support_length
    mode = str(getattr(axis, "FA_DistributionMode", "fixed") or "fixed").lower()
    round_step = _float_value(getattr(axis, "FA_RoundStep", 100.0), 100.0)
    return {
        "support_length_mm": float(support_length),
        "support_start_mm": float(support_start),
        "support_end_mm": float(support_end),
        "start_offset_mm": float(start_offset),
        "end_offset_mm": float(end_offset),
        "requested_spacing_mm": float(requested),
        "mode": mode,
        "round_step_mm": float(round_step),
        "positions_mm": positions,
        "distances_mm": distances,
    }


def _plan(mode, support_length, spacing, start_offset, end_offset):
    if mode == "uniform":
        return plan_uniform_axis_distribution(
            support_length, spacing, start_offset, end_offset
        )
    if mode == "rounded50":
        return plan_rounded_axis_distribution(
            support_length, spacing, 50.0, start_offset, end_offset
        )
    if mode == "rounded100":
        return plan_rounded_axis_distribution(
            support_length, spacing, 100.0, start_offset, end_offset
        )
    return plan_fixed_axis_distribution(
        support_length, spacing, start_offset, end_offset
    )


def _preview_text(layout):
    positions = ", ".join("%.1f" % float(v) for v in layout["positions_mm"])
    intervals = ", ".join("%.1f" % float(v) for v in layout["intervals_mm"])
    return (
        "Cerchas: %d\n"
        "Nominal usado: %.1f mm\n"
        "Intervalo min/max: %.1f / %.1f mm\n"
        "Posiciones desde apoyo inicial: %s mm\n"
        "Intervalos: %s mm"
        % (
            int(layout["axis_count"]),
            float(layout["spacing_mm"]),
            float(layout["min_interval_mm"]),
            float(layout["max_interval_mm"]),
            positions or "0.0",
            intervals or "sin intervalos",
        )
    )


def _show_dialog(axis, state):
    from PySide import QtWidgets

    dialog = QtWidgets.QDialog(FreeCADGui.getMainWindow())
    dialog.setWindowTitle(i18n.bi("FA - Editar ejes de cerchas", "FA - Edit truss axes"))
    dialog.setMinimumWidth(560)
    root = QtWidgets.QVBoxLayout(dialog)

    info = QtWidgets.QLabel(
        i18n.bi("Eje: %s\nLongitud entre apoyos: %.1f mm", "Axis: %s\nLength between supports: %.1f mm")
        % (axis.Label, state["support_length_mm"])
    )
    root.addWidget(info)

    form = QtWidgets.QFormLayout()
    root.addLayout(form)

    def spin(value, minimum, maximum, step):
        widget = QtWidgets.QDoubleSpinBox()
        widget.setDecimals(1)
        widget.setRange(float(minimum), float(maximum))
        widget.setSingleStep(float(step))
        widget.setSuffix(" mm")
        widget.setValue(float(value))
        return widget

    mode = QtWidgets.QComboBox()
    mode.addItem(i18n.bi("Mantener separacion; extremos simetricos", "Keep spacing; symmetric ends"), "fixed")
    mode.addItem(i18n.bi("Distribucion uniforme", "Uniform distribution"), "uniform")
    mode.addItem(i18n.bi("Redondear nominal a 50 mm", "Round nominal to 50 mm"), "rounded50")
    mode.addItem(i18n.bi("Redondear nominal a 100 mm", "Round nominal to 100 mm"), "rounded100")
    current_mode = state["mode"]
    if current_mode == "rounded":
        current_mode = "rounded50" if abs(state["round_step_mm"] - 50.0) < 1e-6 else "rounded100"
    index = mode.findData(current_mode)
    mode.setCurrentIndex(index if index >= 0 else 0)
    form.addRow(i18n.bi("Modo:", "Mode:"), mode)

    spacing = spin(state["requested_spacing_mm"], 100.0, 20000.0, 50.0)
    first = spin(state["start_offset_mm"], 0.0, state["support_length_mm"], 25.0)
    last = spin(state["end_offset_mm"], 0.0, state["support_length_mm"], 25.0)
    form.addRow(i18n.bi("Separacion maxima:", "Maximum spacing:"), spacing)
    form.addRow(i18n.bi("Retiro primera cercha:", "First truss offset:"), first)
    form.addRow(i18n.bi("Retiro ultima cercha:", "Last truss offset:"), last)

    preview = QtWidgets.QPlainTextEdit()
    preview.setReadOnly(True)
    preview.setMinimumHeight(135)
    root.addWidget(preview)

    error_label = QtWidgets.QLabel("")
    error_label.setWordWrap(True)
    root.addWidget(error_label)

    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
    )
    buttons.button(QtWidgets.QDialogButtonBox.Ok).setText(i18n.bi("Aplicar", "Apply"))
    root.addWidget(buttons)

    current_layout = {"value": None}

    def refresh():
        try:
            layout = _plan(
                str(mode.currentData()),
                state["support_length_mm"],
                spacing.value(),
                first.value(),
                last.value(),
            )
            if int(layout["axis_count"]) < 2:
                raise ValueError(i18n.bi("La distribucion debe contener al menos dos cerchas.", "The distribution must contain at least two trusses."))
            current_layout["value"] = layout
            preview.setPlainText(_preview_text(layout))
            error_label.setText("")
            buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        except Exception as exc:
            current_layout["value"] = None
            preview.setPlainText("")
            error_label.setText(str(exc))
            buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    mode.currentIndexChanged.connect(refresh)
    spacing.valueChanged.connect(refresh)
    first.valueChanged.connect(refresh)
    last.valueChanged.connect(refresh)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    refresh()

    if dialog.exec() != QtWidgets.QDialog.Accepted:
        return None
    return current_layout["value"], str(mode.currentData()), float(spacing.value())


def _linked_trusses(axis):
    linked = []
    for obj in list(getattr(axis.Document, "Objects", []) or []):
        try:
            if getattr(obj, "Axis", None) is axis:
                linked.append(obj)
        except Exception:
            pass
    return linked


def _shape_valid(obj):
    try:
        return not obj.Shape.isNull() and obj.Shape.isValid()
    except Exception:
        return False


def _set_property(axis, name, value):
    if name not in getattr(axis, "PropertiesList", []):
        return
    setattr(axis, name, value)


def _apply_layout(axis, layout, ui_mode, requested_spacing):
    doc = axis.Document
    opened = False
    try:
        opened = open_transaction(doc, "FA Editar ejes de cerchas")
        axis.Distances = [float(v) for v in layout["distances_mm"]]
        axis.Angles = [0.0] * int(layout["axis_count"])
        _set_property(axis, "FA_RequestedSpacing", float(requested_spacing))
        _set_property(axis, "FA_NominalSpacing", float(layout["spacing_mm"]))
        _set_property(axis, "FA_MinInterval", float(layout["min_interval_mm"]))
        _set_property(axis, "FA_MaxInterval", float(layout["max_interval_mm"]))
        _set_property(axis, "FA_StartOffset", float(layout["start_offset_mm"]))
        _set_property(axis, "FA_EndOffset", float(layout["end_offset_mm"]))
        persisted_mode = "rounded" if ui_mode.startswith("rounded") else ui_mode
        _set_property(axis, "FA_DistributionMode", persisted_mode)
        if ui_mode.startswith("rounded"):
            if "FA_RoundStep" not in getattr(axis, "PropertiesList", []):
                axis.addProperty(
                    "App::PropertyLength",
                    "FA_RoundStep",
                    "FA Techo",
                    "Paso de redondeo del editor de ejes",
                )
            axis.FA_RoundStep = 50.0 if ui_mode == "rounded50" else 100.0
        doc.recompute()

        linked = _linked_trusses(axis)
        invalid = [obj.Label for obj in linked if hasattr(obj, "Shape") and not _shape_valid(obj)]
        if invalid:
            raise RuntimeError(
                "La nueva distribucion produjo geometria invalida en: %s"
                % ", ".join(invalid)
            )
        finish_transaction(doc, opened, commit=True)
        opened = False
    except Exception:
        finish_transaction(doc, opened, commit=False)
        raise

    _log(
        "Axis=%s | modo=%s | cerchas=%d | nominal=%.1f | min/max=%.1f/%.1f | retiros=%.1f/%.1f mm"
        % (
            axis.Name,
            ui_mode,
            layout["axis_count"],
            layout["spacing_mm"],
            layout["min_interval_mm"],
            layout["max_interval_mm"],
            layout["start_offset_mm"],
            layout["end_offset_mm"],
        )
    )
    msg("FA Editar ejes de cerchas: %d cerchas actualizadas." % int(layout["axis_count"]))


class CommandClass:
    CommandName = COMMAND_NAME

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Editar ejes de cerchas", "FA Edit truss axes"),
            "ToolTip": i18n.bi(
                "Seleccione Ejes de cerchas o Cerchas BIM. Ajusta separacion y retiros "
                "sobre el Arch Axis nativo sin usar el editor BIM de ejes.",
                "Select Truss axes or BIM Trusses. Adjust spacing and offsets on the native "
                "Arch Axis without using the BIM axis editor.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            axis = _require_truss_axis()
            state = _axis_state(axis)
            result = _show_dialog(axis, state)
            if result is None:
                return
            layout, mode, requested_spacing = result
            _apply_layout(axis, layout, mode, requested_spacing)
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(axis)
        except Exception as exc:
            handle_command_exception(i18n.bi("FA Editar ejes de cerchas", "FA Edit truss axes"), exc)

    def IsActive(self):  # noqa: N802
        return App.ActiveDocument is not None


def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
