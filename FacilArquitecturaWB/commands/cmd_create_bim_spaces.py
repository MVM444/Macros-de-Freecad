"""Comando para crear Espacios BIM nativos desde el Sketch documental de recintos.

Nombre: cmd_create_bim_spaces.py
Proposito: exponer como herramienta real la conversion de recintos 2D a Arch Space.
Funcion principal: localizar un Sketch de recintos, resolver el Level destino y
materializar volumenes ``Arch Space`` mediante ``core.space_utils``.
Instrucciones relevantes para futuras modificaciones:
- Reutilizar ``create_bim_spaces``; no duplicar geometria en este comando ni en la demo.
- Mantener el Sketch documental como fuente trazable y exportable 2D.
- No incorporar reglas de GameEngineExport u otros Workbenches.
Version: 0.3.1
Fecha y hora: 2026-09-01 America/Costa_Rica
"""
from __future__ import annotations
import os
import FreeCAD
import FreeCADGui
from PySide import QtWidgets
from .. import i18n
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_structure_utils import (
    adopt_auxiliary_sources,
    ensure_bim_structure,
    is_level,
    migrate_legacy_support_to_level,
    selected_level,
)
from ..core.project_structure import msg
from ..core.reloadable_command import ReloadableCommandProxy
from ..core.space_utils import collect_closed_room_sketches, create_bim_spaces
from ..core.process_feedback import long_process_message
from ..ui.process_feedback import LongOperationFeedback

ICON_PATH=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","resources","icons","bim_spaces.svg")).replace(os.sep,"/")
PREFERENCES_PATH="User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/BIMSpaces"

def _find_level_in_parents(obj):
    pending=list(getattr(obj,"InList",[]) or []); seen=set()
    while pending:
        parent=pending.pop(0)
        if id(parent) in seen: continue
        seen.add(id(parent))
        if is_level(parent): return parent
        pending.extend(list(getattr(parent,"InList",[]) or []))
    return None

class BIMSpacesDialog(QtWidgets.QDialog):
    def __init__(self, room_count, parent=None):
        super().__init__(parent); self.params=FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle(i18n.bi("FA Crear espacios BIM", "FA Create BIM Spaces")); self.setMinimumWidth(450)
        layout=QtWidgets.QVBoxLayout(self)
        info=QtWidgets.QLabel(i18n.bi("Recintos detectados: %d\nCada recinto se convertira en un Arch Space nativo." % int(room_count), "Detected rooms: %d\nEach room will be converted into a native Arch Space." % int(room_count))); info.setWordWrap(True); layout.addWidget(info)
        warning=QtWidgets.QLabel(long_process_message("La creacion de Espacios BIM")); warning.setWordWrap(True); f=warning.font(); f.setBold(True); warning.setFont(f); layout.addWidget(warning)
        form=QtWidgets.QFormLayout(); self.height=QtWidgets.QDoubleSpinBox(); self.height.setRange(100.0,20000.0); self.height.setDecimals(1); self.height.setSuffix(" mm"); self.height.setValue(self.params.GetFloat("height_mm",2700.0)); form.addRow(i18n.bi("Altura del espacio", "Space height"),self.height)
        self.replace=QtWidgets.QCheckBox(i18n.bi("Actualizar Espacios BIM FA existentes de este Sketch sin cambiar su identidad", "Update existing FA BIM Spaces from this Sketch without changing their identity")); self.replace.setChecked(self.params.GetBool("replace_existing",True)); form.addRow("",self.replace); layout.addLayout(form)
        buttons=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    def values(self):
        values={"height_mm":float(self.height.value()),"replace_existing":bool(self.replace.isChecked())}; self.params.SetFloat("height_mm",values["height_mm"]); self.params.SetBool("replace_existing",values["replace_existing"]); return values

class CommandClass:
    CommandName="FA_CreateBIMSpaces"
    def GetResources(self):
        return {"MenuText":i18n.bi("FA Crear espacios BIM", "FA Create BIM Spaces"),"ToolTip":i18n.bi("Experimental: crear Arch Space nativos desde el Sketch de recintos detectados.", "Experimental: create native Arch Spaces from the detected-room Sketch."),"Pixmap":ICON_PATH}
    def Activated(self):
        doc=FreeCAD.ActiveDocument; transaction_open=False
        try:
            if doc is None: raise UserFacingError("Abra o cree un documento antes de crear Espacios BIM.")
            selection=list(FreeCADGui.Selection.getSelection() or [])
            sketches=collect_closed_room_sketches(doc,selection=selection)
            if not sketches: raise UserFacingError("No se encontro un Sketch de recintos. Ejecute primero FA Detectar recintos 2D.")
            if len(sketches)>1 and not any(obj in selection for obj in sketches): raise UserFacingError("Hay varios Sketches de recintos. Seleccione explicitamente el que desea convertir.")
            room_sketch=sketches[0]
            target_level=selected_level(selection) or _find_level_in_parents(room_sketch)
            dialog=BIMSpacesDialog(int(getattr(room_sketch,"FA_RoomCount",0) or 0),parent=FreeCADGui.getMainWindow()); accepted=dialog.exec() if hasattr(dialog,"exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted: return
            options=dialog.values()
            with LongOperationFeedback("FA Crear espacios BIM","Preparando estructura BIM") as feedback:
                doc.openTransaction("FA Crear espacios BIM"); transaction_open=True
                if target_level is None:
                    feedback.stage("Resolviendo Building y Level")
                    target_level=ensure_bim_structure(doc)["level"]
                migrate_legacy_support_to_level(doc,target_level)
                source_objects=[room_sketch]+list(getattr(room_sketch,"FA_SourceSketches",[]) or [])
                adopt_auxiliary_sources(doc,target_level,source_objects)
                feedback.stage("Creando objetos Arch Space")
                result=create_bim_spaces(doc,target_level,room_sketch,default_height_mm=options["height_mm"],replace_existing=options["replace_existing"])
                feedback.stage("Recomputando y validando")
                doc.recompute(); doc.commitTransaction(); transaction_open=False
            FreeCADGui.Selection.clearSelection()
            for obj in result["spaces"]: FreeCADGui.Selection.addSelection(obj)
            msg("Espacios BIM sincronizados: %d | actualizados: %d | nuevos: %d | ambiguos: %d | Level: %s" % (len(result["spaces"]),result.get("updated",0),result.get("created",0),result.get("ambiguous",0),target_level.Label))
        except Exception as exc:
            if transaction_open and doc is not None:
                try: doc.abortTransaction()
                except Exception: pass
            handle_command_exception("FA Crear espacios BIM",exc)
    def IsActive(self): return FreeCAD.ActiveDocument is not None

def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
