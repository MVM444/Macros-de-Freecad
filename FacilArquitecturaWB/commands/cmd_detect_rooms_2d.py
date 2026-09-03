"""Comando para detectar recintos cerrados y producir su Sketch documental 2D.

Nombre: cmd_detect_rooms_2d.py
Proposito: exponer en la barra la misma deteccion de recintos que usa FA Demo edificio.
Funcion principal: recopilar Sketches de planta, detectar caras cerradas y crear un
Sketch trazable con areas y restricciones basicas.
Instrucciones relevantes para futuras modificaciones:
- Reutilizar siempre ``core.room_utils.create_closed_room_sketch``.
- Mantener una sola transaccion para Undo/Redo.
- No crear Espacios BIM aqui; esa conversion pertenece a FA_CreateBIMSpaces.
Version: 0.2.2
Fecha y hora: 2026-09-01 America/Costa_Rica
"""
from __future__ import annotations
import os
import FreeCAD
import FreeCADGui
from PySide import QtWidgets
from .. import i18n
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_structure_utils import adopt_auxiliary_sources, ensure_auxiliary_parent
from ..core.project_structure import active_or_new_document, msg
from ..core.reloadable_command import ReloadableCommandProxy
from ..core.room_utils import DEFAULT_MIN_ROOM_AREA_M2, DEFAULT_SNAP_TOLERANCE_MM, collect_room_source_sketches, create_closed_room_sketch
from ..ui.process_feedback import LongOperationFeedback

ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "detect_rooms.svg")).replace(os.sep, "/")
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/DetectRooms2D"

class DetectRoomsDialog(QtWidgets.QDialog):
    def __init__(self, source_count, parent=None):
        super().__init__(parent); self.params=FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle(i18n.bi("FA Detectar recintos 2D", "FA Detect 2D Rooms")); self.setMinimumWidth(440)
        layout=QtWidgets.QVBoxLayout(self)
        info=QtWidgets.QLabel(i18n.bi("Sketches fuente: %d\nCrea un Sketch documental con los recintos cerrados detectados." % int(source_count), "Source Sketches: %d\nCreates a documentary Sketch with the detected closed rooms." % int(source_count))); info.setWordWrap(True); layout.addWidget(info)
        form=QtWidgets.QFormLayout()
        self.snap=QtWidgets.QDoubleSpinBox(); self.snap.setRange(0.1,500.0); self.snap.setDecimals(1); self.snap.setSuffix(" mm"); self.snap.setValue(self.params.GetFloat("snap_tolerance_mm", DEFAULT_SNAP_TOLERANCE_MM)); form.addRow("Tolerancia de cierre", self.snap)
        self.min_area=QtWidgets.QDoubleSpinBox(); self.min_area.setRange(0.01,10000.0); self.min_area.setDecimals(2); self.min_area.setSuffix(" m2"); self.min_area.setValue(self.params.GetFloat("minimum_room_area_m2", DEFAULT_MIN_ROOM_AREA_M2)); form.addRow(i18n.bi("Area minima", "Minimum area"), self.min_area)
        self.replace=QtWidgets.QCheckBox(i18n.bi("Reemplazar Sketch de recintos generado anteriormente", "Replace previously generated room Sketch")); self.replace.setChecked(self.params.GetBool("replace_previous",True)); form.addRow("",self.replace); layout.addLayout(form)
        buttons=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    def values(self):
        values={"snap_tolerance":float(self.snap.value()),"minimum_room_area_m2":float(self.min_area.value()),"replace_previous":bool(self.replace.isChecked())}
        self.params.SetFloat("snap_tolerance_mm",values["snap_tolerance"]); self.params.SetFloat("minimum_room_area_m2",values["minimum_room_area_m2"]); self.params.SetBool("replace_previous",values["replace_previous"]); return values

class CommandClass:
    CommandName="FA_DetectRooms2D"
    def GetResources(self):
        return {"MenuText":i18n.bi("FA Detectar recintos 2D", "FA Detect 2D Rooms"),"ToolTip":i18n.bi("Experimental: detectar recintos cerrados desde Sketches y crear su representacion documental 2D.", "Experimental: detect closed rooms from Sketches and create their documentary 2D representation."),"Pixmap":ICON_PATH}
    def Activated(self):
        doc=None; transaction_open=False
        try:
            doc=active_or_new_document()
            selection=list(FreeCADGui.Selection.getSelection() or [])
            sources=collect_room_source_sketches(doc,selection=selection or None)
            if not sources and selection:
                # Una seleccion accidental de un objeto BIM/resultado de la demo no debe
                # bloquear la deteccion. La seleccion conserva prioridad cuando realmente
                # contiene Sketches de planta; en caso contrario se reintenta sobre el
                # documento completo.
                sources=collect_room_source_sketches(doc,selection=None)
                if sources:
                    msg("La seleccion actual no contiene fuentes de planta; se usaran los Sketches del documento.")
            if not sources: raise UserFacingError("No se encontraron Sketches de planta utilizables para detectar recintos.")
            dialog=DetectRoomsDialog(len(sources),parent=FreeCADGui.getMainWindow()); accepted=dialog.exec() if hasattr(dialog,"exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted: return
            options=dialog.values()
            support_parent, target_level=ensure_auxiliary_parent(doc,sources,legacy_key="areas")
            with LongOperationFeedback("FA Detectar recintos 2D","Analizando Sketches") as feedback:
                doc.openTransaction("FA Detectar recintos 2D"); transaction_open=True
                feedback.stage("Detectando contornos cerrados")
                sketch, topology=create_closed_room_sketch(doc,support_parent,sources,snap_tolerance=options["snap_tolerance"],minimum_room_area_m2=options["minimum_room_area_m2"],replace_previous=options["replace_previous"])
                if target_level is not None:
                    adopt_auxiliary_sources(doc,target_level,[sketch]+sources)
                feedback.stage("Recomputando documento"); doc.recompute(); doc.commitTransaction(); transaction_open=False
            FreeCADGui.Selection.clearSelection(); FreeCADGui.Selection.addSelection(sketch)
            msg("Recintos 2D detectados: %d | Sketch: %s" % (len(topology.get("faces",[])), sketch.Label))
        except Exception as exc:
            if transaction_open and doc is not None:
                try: doc.abortTransaction()
                except Exception: pass
            handle_command_exception("FA Detectar recintos 2D",exc)
    def IsActive(self): return True

def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
