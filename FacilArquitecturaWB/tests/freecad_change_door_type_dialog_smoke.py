"""FreeCAD GUI smoke test for the Change Door Type dialog buttons.

Run inside FreeCAD, for example through MCP ``execute_code``.  This test
guards the Qt detail that an ApplyRole button does not emit the button box's
``accepted`` signal.
"""

from PySide import QtWidgets

from FacilArquitecturaWB.ui.dialog_change_door_type import ChangeDoorTypeDialog


def run():
    dialog = ChangeDoorTypeDialog(
        door_count=1,
        current_type="Simple door",
        presets=["Simple door", "Glass door"],
    )
    button_box = dialog.findChild(QtWidgets.QDialogButtonBox)
    assert button_box is not None, "No se encontro QDialogButtonBox"

    apply_button = button_box.button(QtWidgets.QDialogButtonBox.Apply)
    assert apply_button is not None, "No se encontro el boton Aplicar"
    apply_button.click()
    assert dialog.result() == QtWidgets.QDialog.Accepted, (
        "El clic en Aplicar no acepto el dialogo"
    )
    dialog.deleteLater()
    print("[FACILARQ][TEST] Dialogo Cambiar tipo: Aplicar acepta correctamente")
    return True


if __name__ == "__main__":
    run()
