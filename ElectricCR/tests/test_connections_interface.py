"""Verifica la interfaz reducida de Conectar sin iniciar FreeCAD."""

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
CONNECT = REPO / "Conectar"


def _header(name, key):
    prefix = "# {}:".format(key).lower()
    for line in (CONNECT / name).read_text(encoding="utf-8-sig").splitlines()[:16]:
        if line.strip().lower().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def main():
    visible = {
        "Conectar_Alimentadores_a_Tablero_Auto.FCMacro",
        "Conectar_Octogonales_por_Circuito.FCMacro",
        "Ajustar_Alimentador_o_Ramal_Manual.FCMacro",
    }
    legacy = {
        "Conectar_Cajas_a_Tablero_Auto.FCMacro",
        "Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro",
        "Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro",
        "Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro",
        "Conectar_Octogonales_Ortogonal_por_Circuito_TCOM.FCMacro",
        "Conectar_Tableros_Cara_Superior.FCMacro",
        "Conectar_Desconectores_HVAC_a_TP.FCMacro",
        "Preparar_Red_TCOM_Completa.FCMacro",
    }
    for name in visible:
        if _header(name, "Toolbar") != "Conectar":
            raise RuntimeError("Herramienta general fuera de Conectar: " + name)
        icon = _header(name, "Icon")
        if not icon:
            raise RuntimeError("Herramienta sin icono: " + name)
    for name in legacy:
        if _header(name, "Toolbar") != "Conectar Legacy":
            raise RuntimeError("Wrapper aun visible en barra normal: " + name)

    config = json.loads((REPO / "ElectricCR" / "config.json").read_text(encoding="utf-8-sig"))
    visible_groups = set(config.get("macro_toolbar_groups", []))
    if "Conectar" not in visible_groups or "Conectar Legacy" in visible_groups:
        raise RuntimeError("Configuracion de barras no oculta Legacy")

    registry = (REPO / "ElectricCR" / "commands" / "macros.py").read_text(encoding="utf-8-sig")
    start = registry.index("def _cmd_id")
    end = registry.index("def _register_dir_group", start)
    body = registry[start:end]
    if "getmtime" in body or "mtime" in body:
        raise RuntimeError("Los IDs de comandos siguen dependiendo de fecha")
    print("CONNECTION INTERFACE OK visible=3 legacy=8 stable_ids=SI")


if __name__ == "__main__":
    main()
