#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import FreeCAD as App
import FreeCADGui as Gui

from .. import chatlog
from .. import usage_log


def _qmods():
    try:
        from PySide2 import QtWidgets
        return QtWidgets
    except Exception:
        try:
            from PySide import QtGui as QtWidgets
            return QtWidgets
        except Exception:
            return None


class ChatSaveEntryCmd:
    def GetResources(self):
        return {
            'MenuText': 'Guardar chat…',
            'ToolTip': 'Guardar una entrada (rol + texto) en el registro de chat.',
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            usage_log.log_tool(SAVE_CMD, {"source": "chat"})
        except Exception:
            pass
        QtWidgets = _qmods()
        if QtWidgets is None:
            App.Console.PrintError('ElectricCR: Qt no disponible para el diálogo.\n')
            return
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle('Guardar chat')
        layout = QtWidgets.QVBoxLayout(dlg)

        role_box = QtWidgets.QComboBox(dlg)
        role_box.addItems(['user', 'assistant', 'system'])
        layout.addWidget(role_box)

        text_edit = QtWidgets.QPlainTextEdit(dlg)
        text_edit.setPlaceholderText('Pega aquí el texto del chat…')
        text_edit.setMinimumSize(500, 250)
        layout.addWidget(text_edit)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            role = role_box.currentText()
            text = text_edit.toPlainText()
            path = chatlog.append_entry(role, text)
            App.Console.PrintMessage(f"ElectricCR: entrada guardada en {path}\n")


class ChatOpenFolderCmd:
    def GetResources(self):
        return {
            'MenuText': 'Abrir carpeta de logs',
            'ToolTip': 'Abrir la carpeta donde se guardan los registros de chat.',
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            usage_log.log_tool(OPEN_CMD, {"source": "chat"})
        except Exception:
            pass
        folder = chatlog._ensure_logs_dir()
        try:
            if os.name == 'nt':
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception as e:
            App.Console.PrintError(f"ElectricCR: no se pudo abrir la carpeta: {e}\n")


class ChatPrintSessionCmd:
    def GetResources(self):
        return {
            'MenuText': 'Imprimir sesión actual',
            'ToolTip': 'Imprime en la consola la sesión de hoy para poder restaurarla/copiarla.',
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            usage_log.log_tool(PRINT_CMD, {"source": "chat"})
        except Exception:
            pass
        path = chatlog.current_session_path()
        data = chatlog.load_session(path)
        if not data:
            App.Console.PrintWarning('ElectricCR: no hay entradas en la sesión actual.\n')
            return
        App.Console.PrintMessage(f"ElectricCR: sesión: {path}\n")
        for item in data:
            role = item.get('role', '?')
            txt = item.get('text', '')
            ts = item.get('ts', '')
            App.Console.PrintMessage(f"[{ts}] {role}> {txt}\n")


SAVE_CMD = 'ElectricCR_Chat_Save'
OPEN_CMD = 'ElectricCR_Chat_OpenFolder'
PRINT_CMD = 'ElectricCR_Chat_Print'

Gui.addCommand(SAVE_CMD, ChatSaveEntryCmd())
Gui.addCommand(OPEN_CMD, ChatOpenFolderCmd())
Gui.addCommand(PRINT_CMD, ChatPrintSessionCmd())
