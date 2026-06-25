from pathlib import Path
import sys

root = Path(r"c:/Users/marco/OneDrive - Caja Costarricense de Seguro Social/Documentos/FreeCAD/Macros/Macros-de-Freecad")
sys.path.insert(0, str(root))
macro_path = root / "Objetos" / "Insertar_Dispositivo.FCMacro"
code = macro_path.read_text(encoding="utf-8")
ns = {}
exec(compile(code, str(macro_path), "exec"), ns)
print(ns['_candidate_electriccr_dirs']())
