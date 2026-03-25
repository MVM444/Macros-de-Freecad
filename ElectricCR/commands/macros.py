# -*- coding: utf-8 -*-
"""Registro de macros como comandos para ElectricCR.

Funciones clave:
- icon_path/icon_for_macro: resuelven iconos por nombre base o convención.
- register_macro_command: registra .FCMacro/.py como comandos de FreeCAD.
- register_predefined_macros: agrupa macros por carpetas y raíz.
"""

import os
import sys
import unicodedata
import FreeCAD as App
import FreeCADGui as Gui

from .. import usage_log

PKG_DIR = os.path.dirname(os.path.dirname(__file__))
ICONS_DIR = os.path.join(PKG_DIR, "icons")


def _roots():
    """Return (macros_base, macros_de_freecad)."""
    macros_base = os.path.abspath(os.path.join(PKG_DIR, os.pardir))
    mdf = os.path.join(macros_base, 'Macros-de-Freecad')
    return macros_base, mdf


def icon_path(basename: str) -> str:
    if not basename:
        return ""
    candidates = []
    if os.path.isabs(basename):
        candidates.append(basename)
    else:
        normalized = basename.replace('\\', '/')
        root, ext = os.path.splitext(normalized)
        if ext.lower() in ('.svg', '.png'):
            names = [normalized]
        else:
            names = [f"{normalized}.svg", f"{normalized}.png", normalized]
        for name in names:
            candidates.append(os.path.join(ICONS_DIR, name))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return ""


def icon_for_macro(dirname: str, filename: str) -> str:
    """Icon for a macro by convention or header hint.

    Priority:
    1) icons/<dirname>/<base>.svg|png
    2) icons/<base>.svg|png
    3) icon next to the macro file (same folder)
    4) '# Icon: ...' header, resolved via icons/ and macro folder
    5) ""
    """
    base = os.path.splitext(filename)[0]

    root_base = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), os.pardir))
    mdf_base = os.path.join(root_base, 'Macros-de-Freecad')
    macro_candidates = []
    if dirname:
        macro_candidates.append(os.path.join(mdf_base, dirname, filename))
        macro_candidates.append(os.path.join(root_base, dirname, filename))
    else:
        macro_candidates.append(os.path.join(mdf_base, filename))
        macro_candidates.append(os.path.join(root_base, filename))
    macro_path = next((p for p in macro_candidates if os.path.exists(p)), "")

    for candidate in (f"{base}.svg", f"{base}.png"):
        p = os.path.join(ICONS_DIR, dirname, candidate)
        if os.path.isfile(p):
            return p

    root = icon_path(base)
    if root:
        return root

    if macro_path:
        macro_dir = os.path.dirname(macro_path)
        for candidate in (f"{base}.svg", f"{base}.png"):
            p = os.path.join(macro_dir, candidate)
            if os.path.isfile(p):
                return p

    try:
        if not macro_path:
            raise FileNotFoundError
        with open(macro_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for _ in range(12):
                line = f.readline()
                if not line:
                    break
                if line.strip().lower().startswith('# icon:'):
                    name = line.split(':', 1)[1].strip()
                    p = icon_path(name)
                    if p:
                        return p
                    p2 = os.path.join(ICONS_DIR, dirname, name)
                    if os.path.isfile(p2):
                        return p2
                    p3 = os.path.join(os.path.dirname(macro_path), name)
                    if os.path.isfile(p3):
                        return p3
                    break
    except Exception:
        pass
    return ""


def macro_header_value(dirname: str, filename: str, key: str) -> str:
    """Read a simple header value like '# MenuText: ...' from a macro."""
    try:
        key_l = str(key or "").strip().lower()
        if not key_l:
            return ""
        # Buscar en ambos: raiz de Macros y Macros-de-Freecad
        root_base = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), os.pardir))
        mdf_base = os.path.join(root_base, 'Macros-de-Freecad')
        candidates = []
        if dirname:
            candidates.append(os.path.join(mdf_base, dirname, filename))
            candidates.append(os.path.join(root_base, dirname, filename))
        else:
            candidates.append(os.path.join(mdf_base, filename))
            candidates.append(os.path.join(root_base, filename))
        macro_path = next((p for p in candidates if os.path.exists(p)), None)
        if not macro_path:
            return ""
        with open(macro_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                s = line.strip()
                if not s or not s.startswith('#'):
                    continue
                low = s.lower()
                prefix = f"# {key_l}:"
                if low.startswith(prefix):
                    return s.split(':', 1)[1].strip()
    except Exception:
        pass
    return ""


def _resolve_moved_path(original_path: str) -> str:
    """Try to resolve a macro path that may have been moved to Macros-de-Freecad.

    Strategy:
    - If original exists, return it.
    - Try same relative path under Macros-de-Freecad.
    - Search by exact filename under Macros-de-Freecad (recursive).
    - Fallback: search by exact filename under Macros base.
    """
    try:
        if os.path.exists(original_path):
            return original_path
        base, mdf = _roots()
        # Try same relative path swapped to Macros-de-Freecad
        try:
            rel = os.path.relpath(original_path, base)
            candidate = os.path.join(mdf, rel)
            if os.path.exists(candidate):
                return candidate
        except Exception:
            pass
        # Search by filename in Macros-de-Freecad
        filename = os.path.basename(original_path)
        for root, _dirs, files in os.walk(mdf):
            if filename in files:
                return os.path.join(root, filename)
        # Fallback search in Macros base
        for root, _dirs, files in os.walk(base):
            if filename in files:
                return os.path.join(root, filename)
    except Exception:
        pass
    return original_path


def _macro_self_manages_transaction(src: str) -> bool:
    """Heuristic: macro already uses FreeCAD document transactions."""
    try:
        text = str(src or "").lower()
    except Exception:
        return False
    if not text:
        return False
    # Explicit opt-in header (recommended for old macros).
    if "# transaction: self" in text or "# transaction:self" in text:
        return True
    has_open = "opentransaction(" in text
    has_close = ("committransaction(" in text) or ("aborttransaction(" in text)
    return bool(has_open and has_close)


def _run_macro_file(macro_abspath: str):
    """Ejecuta un archivo .FCMacro/.py en la sesi??n actual."""
    try:
        macro_abspath = _resolve_moved_path(macro_abspath)
        if not os.path.exists(macro_abspath):
            raise FileNotFoundError(f"No se encontr?? la macro: {macro_abspath}")
        with open(macro_abspath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            src = f.read()
        code = compile(src, macro_abspath, 'exec')
        g = {
            '__name__': '__main__',
            '__file__': macro_abspath,
            'FreeCAD': App,
            'App': App,
            'FreeCADGui': Gui,
            'Gui': Gui,
            'os': os,
            'sys': sys,
        }
        cwd_prev = os.getcwd()
        doc = getattr(App, "ActiveDocument", None)
        trans_opened = False
        use_wrapper_transaction = bool(doc) and (not _macro_self_manages_transaction(src))
        if use_wrapper_transaction:
            try:
                name = os.path.splitext(os.path.basename(macro_abspath))[0]
                doc.openTransaction(f"ElectricCR: {name}")
                trans_opened = True
            except Exception:
                trans_opened = False
        elif doc:
            try:
                App.Console.PrintMessage(
                    f"ElectricCR: transaccion externa omitida (macro autogestiona transaccion): {os.path.basename(macro_abspath)}\n"
                )
            except Exception:
                pass
        try:
            os.chdir(os.path.dirname(macro_abspath))
            exec(code, g, g)
            if trans_opened:
                try:
                    doc.commitTransaction()
                except Exception:
                    pass
        except SystemExit as sx:
            if trans_opened:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            try:
                code_txt = getattr(sx, "code", None)
                App.Console.PrintWarning(
                    f"ElectricCR: macro finalizada por SystemExit ({code_txt}) sin traceback: {os.path.basename(macro_abspath)}\n"
                )
            except Exception:
                pass
            return
        except Exception:
            if trans_opened:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            raise
        finally:
            os.chdir(cwd_prev)
    except Exception as e:
        App.Console.PrintError(f"Error ejecutando macro: {macro_abspath}: {e}\n")


def register_macro_command(cmd_name: str, macro_path: str, menu_text: str, tooltip: str = "", icon: str = "") -> str:
    macro_abspath = os.path.abspath(macro_path)
    if not os.path.exists(macro_abspath):
        return ""

    if not icon:
        icon = icon_path('Rayo')

    class _MacroCmd:
        def GetResources(self):
            return {
                'Pixmap': icon or "",
                'MenuText': menu_text,
                'ToolTip': tooltip or menu_text,
            }

        def Activated(self):
            try:
                tool_id = f"macro:{macro_abspath}"
                meta = {"cmd": cmd_name, "macro": macro_abspath, "label": menu_text}
                usage_log.log_tool(tool_id, meta)
            except Exception:
                pass
            _run_macro_file(macro_abspath)

        def IsActive(self):
            return True

    Gui.addCommand(cmd_name, _MacroCmd())
    return cmd_name


def register_predefined_macros(base_dir: str):
    """Registrar macros ubicadas en 'Macros-de-Freecad' y devolver grupos.

    Estructura esperada:
    <Carpeta de Macros>/Macros-de-Freecad/
      ├─ <Grupo1>/ *.FCMacro | *.py
      ├─ <Grupo2>/ *.FCMacro | *.py
      └─ *.FCMacro | *.py (macros sueltas en la raíz)
    """
    # Directorio raiz donde residen las macros del usuario para ElectricCR
    base_dir = os.path.abspath(base_dir)

    def _find_repo_root():
        seen = set()
        cur = base_dir
        for _ in range(6):
            if not cur or cur in seen:
                break
            seen.add(cur)
            if os.path.basename(cur) == 'Macros-de-Freecad' and os.path.isdir(cur):
                return cur
            candidate = os.path.join(cur, 'Macros-de-Freecad')
            if os.path.isdir(candidate):
                return os.path.abspath(candidate)
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        return None

    repo_root = _find_repo_root()

    groups = []
    import_export_group = "Importar y Exportar"

    def _normalize_group_key(text: str) -> str:
        s = str(text or "").strip().lower()
        if not s:
            return ""
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = " ".join(s.split())
        return s

    def _append_to_group(title: str, cmd: str) -> None:
        if not title or not cmd:
            return
        wanted = _normalize_group_key(title)
        for idx, (group_title, cmds) in enumerate(groups):
            if _normalize_group_key(group_title) == wanted:
                cmds.append(cmd)
                groups[idx] = (group_title, cmds)
                return
        groups.append((title, [cmd]))

    def _normalize_text(text: str) -> str:
        s = str(text or "").strip().lower()
        if not s:
            return ""
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s

    def _is_import_export_macro(filename: str, label: str = "") -> bool:
        stem = os.path.splitext(filename or "")[0]
        probe = _normalize_text(f"{stem} {label}")
        return ("importar" in probe) or ("exportar" in probe)

    def _toolbar_for_macro(dirname: str, filename: str, label: str = "") -> str:
        explicit = (macro_header_value(dirname, filename, "Toolbar") or "").strip()
        if explicit:
            return explicit
        if _is_import_export_macro(filename, label):
            return import_export_group
        return ""

    def _sanitize_id(text: str) -> str:
        import re
        base = os.path.splitext(text)[0]
        base = re.sub(r"[^0-9A-Za-z_]+", "_", base)
        base = re.sub(r"_+", "_", base).strip("_")
        return base or "Macro"

    def _cmd_id(prefix: str, name: str, macro_path: str, icon_path_str: str) -> str:
        try:
            mt = os.path.getmtime(macro_path) if os.path.exists(macro_path) else 0
            it = os.path.getmtime(icon_path_str) if icon_path_str and os.path.exists(icon_path_str) else 0
            ver = int(max(mt, it))
        except Exception:
            ver = 0
        return f"ElectricCR_{prefix}_{_sanitize_id(name)}_{ver}"

    def _register_dir_group(title: str, dirname: str, prefix: str, icon_name: str = ""):
        dir_path = os.path.join(repo_root, dirname)
        if not os.path.isdir(dir_path):
            return
        group_icon = icon_path(icon_name) if icon_name else ""
        cmd_ids = []
        for name in sorted(os.listdir(dir_path)):
            if name.lower().endswith(".fcmacro"):
                if name.lower() == 'desktop.ini':
                    continue
                macro_path = os.path.join(dir_path, name)
                label = os.path.splitext(name)[0]
                header_label = macro_header_value(dirname, name, "MenuText") or macro_header_value(dirname, name, "Label")
                if header_label:
                    label = header_label
                per_icon = icon_for_macro(dirname, name) or group_icon
                cmd_id = _cmd_id(prefix, name, macro_path, per_icon)
                cmd = register_macro_command(cmd_id, macro_path, label, icon=per_icon)
                if cmd:
                    toolbar_override = _toolbar_for_macro(dirname, name, label)
                    if toolbar_override:
                        _append_to_group(toolbar_override, cmd)
                    else:
                        cmd_ids.append(cmd)
        if cmd_ids:
            groups.append((title, cmd_ids))

        # También registrar subcarpetas de primer nivel como grupos separados
        for sub in sorted(os.listdir(dir_path)):
            sub_path = os.path.join(dir_path, sub)
            if os.path.isdir(sub_path) and sub not in {'.git', '__pycache__'}:
                sub_cmds = []
                for fname in sorted(os.listdir(sub_path)):
                    if fname.lower().endswith(".fcmacro") and fname.lower() != 'desktop.ini':
                        macro_path = os.path.join(sub_path, fname)
                        label = os.path.splitext(fname)[0]
                        # dirname puede ser jerárquico (p.ej. 'Electric/Insertar')
                        dir_key = os.path.join(dirname, sub)
                        header_label = macro_header_value(dir_key, fname, "MenuText") or macro_header_value(dir_key, fname, "Label")
                        if header_label:
                            label = header_label
                        per_icon = icon_for_macro(dir_key, fname) or group_icon
                        cmd_id = _cmd_id(f"{prefix}_{sub}", fname, macro_path, per_icon)
                        cmd = register_macro_command(cmd_id, macro_path, label, icon=per_icon)
                        if cmd:
                            toolbar_override = _toolbar_for_macro(dir_key, fname, label)
                            if toolbar_override:
                                _append_to_group(toolbar_override, cmd)
                            else:
                                sub_cmds.append(cmd)
                if sub_cmds:
                    groups.append((f"{title} - {sub}", sub_cmds))

    # Si no existe la carpeta declarada, no registramos nada
    if not repo_root or not os.path.isdir(repo_root):
        App.Console.PrintWarning(f"ElectricCR: no se encontro 'Macros-de-Freecad' cerca de {base_dir}\n")
        return groups

    # Crear grupos por cada subcarpeta encontrada
    ignore_dirs = {
        '.git', '.vscode', '__pycache__', 'Respaldos', 'Xcluidos',
        'ElectricCR', 'Resources', '.qodo'
    }
    for entry in sorted(os.listdir(repo_root)):
        full = os.path.join(repo_root, entry)
        if os.path.isdir(full) and entry not in ignore_dirs and not entry.startswith('.'):
            # Icono de grupo: intenta por nombre de carpeta
            _register_dir_group(entry, entry, prefix=entry, icon_name=entry)

    # Raíz: macros sueltas dentro de Macros-de-Freecad
    ignore_files = {
        'ElectricCRLoader.FCMacro', 'README.md', 'NOTAS.md', 'pyproject.toml', 'pyflow.lock', '.gitignore', 'LICENSE'
    }
    root_cmds = []
    for name in sorted(os.listdir(repo_root)):
        if name in ignore_files:
            continue
        if name.lower().endswith(".fcmacro"):
            macro_path = os.path.join(repo_root, name)
            if os.path.isfile(macro_path):
                per_icon = icon_for_macro('', name) or icon_path('Rayo')
                label = os.path.splitext(name)[0]
                header_label = macro_header_value('', name, "MenuText") or macro_header_value('', name, "Label")
                if header_label:
                    label = header_label
                cmd_id = _cmd_id("Root", name, macro_path, per_icon)
                cmd = register_macro_command(cmd_id, macro_path, label, icon=per_icon)
                if cmd:
                    toolbar_override = _toolbar_for_macro('', name, label)
                    if toolbar_override:
                        _append_to_group(toolbar_override, cmd)
                    else:
                        root_cmds.append(cmd)
    if root_cmds:
        groups.append(("Macros", root_cmds))

    return groups

