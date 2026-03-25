from pathlib import Path

path = Path("Insertar_Dispositivo.FCMacro")
text = path.read_text(encoding="utf-8")
start = text.index("def _candidate_electriccr_dirs()")
end = text.index("class InsertarDispositivoDialog", start)
new_block = """def _candidate_electriccr_dirs() -> list[Path]:
    \"\"\"Buscar posibles directorios que contienen el paquete ElectricCR.\"\"\"
    found: list[Path] = []
    seen: set[Path] = set()

    def push(path: Path) -> None:
        if not path:
            return
        try:
            real = path.resolve()
        except Exception:
            real = path
        if real in seen:
            return
        seen.add(real)
        found.append(real)

    def check_base(base: Path | None) -> None:
        if not base:
            return
        try:
            base_resolved = base.resolve()
        except Exception:
            base_resolved = base
        direct = base_resolved / 'electriccr' / 'features' / 'objeto_toma_uno.py'
        if direct.is_file():
            push(base_resolved)
        pkg = base_resolved / 'ElectricCR'
        if (pkg / 'electriccr' / 'features' / 'objeto_toma_uno.py').is_file():
            push(pkg)

    try:
        here = Path(__file__).resolve()
        lineage = [here.parent, *here.parents]
    except Exception:
        lineage = []
    for parent in lineage:
        check_base(parent)
    user_root = _user_macro_root()
    check_base(user_root)
    try:
        check_base(user_root.parent)
    except Exception:
        pass
    return found


def _ensure_electriccr_on_path() -> bool:
    import importlib

    def _try_import() -> bool:
        for name in (\"ElectricCR\", \"electriccr\"):
            try:
                importlib.import_module(name)
                return True
            except ImportError:
                continue
        return False

    if _try_import():
        return True

    candidates = _candidate_electriccr_dirs()
    try:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            cand = parent / 'ElectricCR'
            if cand.is_dir():
                candidates.append(cand)
    except Exception:
        pass

    normalized: list[Path] = []
    seen: set[Path] = set()
    for entry in candidates:
        try:
            real = entry.resolve()
        except Exception:
            real = entry
        if real in seen:
            continue
        seen.add(real)
        normalized.append(real)

    for directory in normalized:
        for path_candidate in (directory.parent, directory):
            if not path_candidate:
                continue
            sp = str(path_candidate)
            if sp and sp not in sys.path:
                sys.path.insert(0, sp)
        importlib.invalidate_caches()
        if _try_import():
            return True

    try:
        App.Console.PrintWarning(
            \"[INSER][WARN] ElectricCR no encontrado. Revise la ubicacion de la carpeta ElectricCR.\\n\"
        )
    except Exception:
        pass
    return False


"""
text = text[:start] + new_block + text[end:]
path.write_text(text, encoding="utf-8")
