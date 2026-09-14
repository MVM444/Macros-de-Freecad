# -*- coding: utf-8 -*-
"""
    electriccr.features.objeto_toma_uno (rev O, 2026-09-05 21:50 America/Costa_Rica)

Important rev I behavior:
- Direct devices change AlturaRel and keep their base Placement.
- App::Link instances relink to immutable height masters; shared masters are not mutated.
- Public height services intentionally defer document recompute to the caller.

Important rev J behavior (A1 opt-in prototype):
- ``PhysicalDocumentationA1`` masters keep only physical 3D geometry in Shape.
- PLAN documentation is an owned, hidden-tree auxiliary representation.
- Legacy compound masters remain the default for existing callers/documents.

Important rev K behavior (A1 PLAN spatial authority):
- Device.Placement is the single XY/orientation authority.
- PLAN.Placement is a native expression through PLAN.Owner.
- DocumentationPlaneZ stays independent and the geometry signature excludes Placement.

Important rev L behavior (A1 PLAN insertion snap):
- PLAN exposes SnapPoints=[Vector(0,0,0)] for native Draft Snap Special.
- The insertion snap is local to PLAN and follows PLAN.Placement/Owner automatically.
- No extra visible geometry is added to PLAN Shape, so DXF geometry is unchanged.

Important rev M behavior (A1 visual mode contract):
- A1 maps ModoVisual Ambos/Solo2D/Solo3D to the real Owner/PLAN visibility pair.
- MostrarModelo3D and MostrarSimboloPlano remain the independent persistent flags.
- Visibility changes never rebuild physical or PLAN geometry.

Important rev N behavior (A1 owned PLAN dependency):
- PLAN.Owner uses App::PropertyLinkHidden so Std_Delete does not treat PLAN as an external
  referencing object that may break when its authoritative device is deleted.
- Existing A1 PLAN objects with legacy App::PropertyLink are migrated transactionally during
  sync_plan_representation(), preserving Owner and PLAN expressions.

Important rev O behavior (A1 PLAN tree ownership):
- PLAN is an auxiliary documentation representation and must not belong to user-facing DocumentObjectGroup containers.
- sync_plan_representation() removes accidental PLAN group membership, including membership restored by Undo/Redo.
- This does not change PLAN.Owner, visibility, Placement expressions, or the authoritative Device identity.

- Un solo Placement (sin BasePlacement).
- 2D en Z=0 (planta). En 'Horizontal' sÃƒÆ’Ã‚Â³lo el 3D recibe pitch +90Ãƒâ€šÃ‚Â° (eje Y local).
- 3D a AlturaRel incluso en modo 'Solo3D'.
- Prototipos desde registry_electric.json (2D: .step/.stp/.dxf; 3D: .step/.stp).
- ViewProvider fija DisplayMode='Flat Lines' y visibilidad.
- DepuraciÃƒÆ’Ã‚Â³n detallada [TOMA1] y cubo testigo si faltan recursos.
"""

import json
import re
from pathlib import Path
import FreeCAD as App
import Part


REPRESENTATION_CONTRACT_LEGACY = "LegacyCompound"
REPRESENTATION_CONTRACT_A1 = "PhysicalDocumentationA1"
REPRESENTATION_ROLE_PLAN = "PLAN"
REPRESENTATION_SCHEMA_VERSION = 2

# -----------------------------------------------------------------------------
# GUI (opcional)
# -----------------------------------------------------------------------------
GUI_UP = False
try:
    import FreeCADGui as Gui
    GUI_UP = True
except Exception:
    GUI_UP = False


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
def _ts():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_i(msg): App.Console.PrintMessage(f"[{_ts()}][TOMA1][INFO] {msg}\n")
def log_w(msg): App.Console.PrintWarning(f"[{_ts()}][TOMA1][WARN] {msg}\n")
def log_e(msg): App.Console.PrintError(f"[{_ts()}][TOMA1][ERROR] {msg}\n")


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


# -----------------------------------------------------------------------------
# ViewProvider
# -----------------------------------------------------------------------------
class VP_TomaUno:
    def __init__(self, vobj):
        self.Object = getattr(vobj, "Object", None)
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = getattr(vobj, "Object", None)
        try:
            vobj.DisplayModes = ("Flat Lines",)
            vobj.DisplayMode = "Flat Lines"
        except Exception:
            pass
        try:
            vobj.Visibility = not bool(getattr(self.Object, "EsPrototipo", False))
            vobj.Transparency = 0
            vobj.LineWidth = 1.0
            vobj.PointSize = 3.0
        except Exception:
            pass

    def getDisplayModes(self, vobj): return ["Flat Lines"]
    def getDefaultDisplayMode(self): return "Flat Lines"
    def setDisplayMode(self, mode): return "Flat Lines"
    def updateData(self, fp, prop): return
    def onChanged(self, vp, prop): return
    def __getstate__(self): return None
    def __setstate__(self, state): return


# -----------------------------------------------------------------------------
# Registro (registry_electric.json)
# -----------------------------------------------------------------------------
def _candidate_registry_files():
    cands = []
    here = Path(__file__).resolve()
    ancestors = [here.parent, *here.parents[:6]]
    for anc in ancestors:
        if anc is None:
            continue
        reg = anc / "Resources" / "registry" / "registry_electric.json"
        if reg.exists():
            try:
                cands.append(reg.resolve())
            except Exception:
                cands.append(reg)
    try:
        user_dir = Path(App.getUserAppDataDir())
    except Exception:
        user_dir = Path.home() / "AppData" / "Roaming" / "FreeCAD"
    user_reg = user_dir / "Macro" / "Resources" / "registry" / "registry_electric.json"
    if user_reg.exists():
        try:
            cands.append(user_reg.resolve())
        except Exception:
            cands.append(user_reg)
    uniq, seen = [], set()
    for p in cands:
        sp = str(p)
        if sp not in seen:
            uniq.append(p)
            seen.add(sp)
    return uniq


def _load_registry():
    reg = {"schema": "1.0.0", "types": {}}
    for f in _candidate_registry_files():
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict) and "types" in data:
                reg["types"].update(data["types"])
                log_i(f"Registro cargado: {f}")
                return reg
        except Exception as ex:
            log_w(f"Registro ilegible en {f}: {ex}")
    log_w("No se encontrÃƒÆ’Ã‚Â³ registry_electric.json; asigna manualmente Tipo/recursos si aplica.")
    return reg


REGISTRY = _load_registry()


# -----------------------------------------------------------------------------
# ResoluciÃƒÆ’Ã‚Â³n de recursos 2D/3D (STEP/DXF)
# -----------------------------------------------------------------------------
def _resource_dirs():
    here = Path(__file__).resolve()
    roots = []
    # search up to 6 parent levels for a Resources/prototypes folder
    for ancestor in [here.parent, *here.parents[:6]]:
        if ancestor is None:
            continue
        candidate = ancestor / "Resources" / "prototypes"
        if candidate.exists():
            roots.append(candidate)
    try:
        user = Path(App.getUserAppDataDir())
    except Exception:
        user = Path.home() / "AppData" / "Roaming" / "FreeCAD"
    roots += [user / "Macro" / "Resources" / "prototypes"]
    expanded = []
    for r in roots:
        expanded += [r, r / "2d", r / "3d"]
    uniq, seen = [], set()
    for r in expanded:
        try:
            resolved = r.resolve()
        except Exception:
            resolved = r
        if resolved.exists() and resolved.is_dir() and str(resolved) not in seen:
            uniq.append(resolved)
            seen.add(str(resolved))
    return uniq


def _find_resource(relname: str, prefer_kind: str = None):
    if not relname:
        return None
    name = relname.replace('\\\\', '/').split('/')[-1]
    dirs = list(_resource_dirs())
    prefer = str(prefer_kind or '').lower()
    if prefer in ('2d', '3d'):
        preferred = [d for d in dirs if prefer in d.name.lower()]
        others = [d for d in dirs if d not in preferred]
        dirs = preferred + others
    for d in dirs:
        p = d / name
        if p.exists() and p.is_file():
            return str(p)
    return None



def _read_step(path: str):
    shp = Part.Shape(); shp.read(path)
    if shp.isNull():
        raise ValueError("Shape nula al leer STEP")
    return shp


def _read_dxf(path: str):
    try:
        import Import
        doc = App.ActiveDocument or App.newDocument("TmpDXF")
        before = set(o.Name for o in doc.Objects)
        Import.insert(path, doc.Name)
        created = [o for o in doc.Objects if o.Name not in before]
        shapes = []
        for o in created:
            try:
                if hasattr(o, "Shape") and not o.Shape.isNull():
                    shapes.append(o.Shape.copy())
            except Exception:
                pass
            try:
                doc.removeObject(o.Name)
            except Exception:
                pass
        if not shapes:
            raise ValueError("DXF sin shape usable")
        return Part.makeCompound(shapes)
    except Exception as ex:
        raise RuntimeError(f"Fallo leyendo DXF: {ex}")


def _load_symbol_shape(symbol_filename: str):
    if not symbol_filename: return None
    ext = Path(symbol_filename).suffix.lower()
    full = _find_resource(symbol_filename, "2d")
    if not full:
        log_w(f"Recurso 2D no encontrado: {symbol_filename}"); return None
    if ext in (".step", ".stp"):
        try: return _read_step(full)
        except Exception as ex:
            log_w(f"Error leyendo STEP 2D '{symbol_filename}': {ex}"); return None
    if ext == ".dxf":
        try: return _read_dxf(full)
        except Exception as ex:
            log_w(f"Error leyendo DXF 2D '{symbol_filename}': {ex}"); return None
    log_w(f"Formato 2D no soportado ({ext}) para {symbol_filename}; use .step/.stp o .dxf")
    return None


def _load_model_shape(model_filename: str):
    if not model_filename: return None
    ext = Path(model_filename).suffix.lower()
    full = _find_resource(model_filename, "3d")
    if not full:
        log_w(f"Recurso 3D no encontrado: {model_filename}"); return None
    if ext in (".step", ".stp"):
        try: return _read_step(full)
        except Exception as ex:
            log_w(f"Error leyendo STEP 3D '{model_filename}': {ex}"); return None
    log_w(f"Formato 3D no soportado ({ext}) para {model_filename}; use .step/.stp")
    return None


# -----------------------------------------------------------------------------
# Objeto paramÃƒÆ’Ã‚Â©trico
# -----------------------------------------------------------------------------
class TomaUnoProxy:
    """Part::FeaturePython con Shape compuesta 2D/3D en coordenadas locales."""
    def __init__(self):
        self.initialized = False
        self.Object = None  # referencia segura

    def attach(self, obj):
        # *** CLAVE: asignar el proxy ***
        obj.Proxy = self
        self.Object = obj

        # VisualizaciÃƒÆ’Ã‚Â³n / clasificaciÃƒÆ’Ã‚Â³n
        obj.addProperty("App::PropertyEnumeration", "ModoVisual", "Core", "VisualizaciÃƒÆ’Ã‚Â³n")\
            .ModoVisual = ["Ambos", "Solo2D", "Solo3D"]
        obj.ModoVisual = "Ambos"
        obj.addProperty("App::PropertyEnumeration", "Categoria", "Core", "CategorÃƒÆ’Ã‚Â­a")\
            .Categoria = ["Pared", "Cielo", "Piso"]
        obj.Categoria = "Pared"
        obj.addProperty("App::PropertyEnumeration", "Tipo", "Core", "Tipo lÃƒÆ’Ã‚Â³gico")\
            .Tipo = ["Toma", "Apagador", "Luminaria", "Sensor", "Rociador", "Altavoz", "Camara"]
        obj.Tipo = "Toma"

        # ParÃƒÆ’Ã‚Â¡metros geomÃƒÆ’Ã‚Â©tricos locales
        obj.addProperty("App::PropertyAngle", "Giro", "Core", "Giro sobre Z local").Giro = 0.0
        obj.addProperty("App::PropertyDistance", "OffsetX", "Core", "Desplazamiento local X").OffsetX = 0.0
        obj.addProperty("App::PropertyDistance", "OffsetY", "Core", "Desplazamiento local Y").OffsetY = 0.0
        obj.addProperty("App::PropertyDistance", "AlturaRel", "Core", "Altura 3D sobre Z local").AlturaRel = 300.0
        obj.addProperty("App::PropertyEnumeration", "OrientacionPared", "Core",
                        "Afecta 3D (pitch Y) y 2D (yaw Z)")\
            .OrientacionPared = ["Vertical", "Horizontal", "Auto"]
        obj.OrientacionPared = "Vertical"

        # Trazabilidad
        obj.addProperty("App::PropertyString", "KeyRegistro", "Registro", "Clave del registro").KeyRegistro = ""
        obj.addProperty("App::PropertyString", "RecursoProto2D", "Registro", "Archivo 2D").RecursoProto2D = ""
        obj.addProperty("App::PropertyString", "RecursoProto3D", "Registro", "Archivo 3D").RecursoProto3D = ""
        obj.addProperty(
            "App::PropertyString",
            "RepresentationContract",
            "Representations",
            "Contrato de representacion; legacy combina 2D/3D y A1 conserva solo 3D en Shape",
        ).RepresentationContract = REPRESENTATION_CONTRACT_LEGACY

        self.initialized = True
        log_i(f"attach properties on {obj.Name}")

        # ViewProvider
        if GUI_UP and hasattr(obj, "ViewObject") and (obj.ViewObject is not None):
            try:
                VP_TomaUno(obj.ViewObject)
                obj.ViewObject.DisplayMode = "Flat Lines"
                obj.ViewObject.Visibility = True
                obj.ViewObject.Transparency = 0
            except Exception as ex:
                log_w(f"No se pudo inicializar ViewProvider: {ex}")

    def _shapes_from_registry(self, obj):
        key = obj.KeyRegistro or obj.Tipo
        tinfo = (REGISTRY.get("types") or {}).get(str(key), {}) or {}

        sym_name = tinfo.get("symbol2D", "") or obj.RecursoProto2D
        mdl_name = tinfo.get("model3D", "") or obj.RecursoProto3D

        sym_path = _find_resource(sym_name, "2d") if sym_name else None
        mdl_path = _find_resource(mdl_name, "3d") if mdl_name else None
        log_i(f"KeyRegistro='{key}' | symbol2D='{sym_name}' -> {sym_path} | model3D='{mdl_name}' -> {mdl_path}")

        s2 = _load_symbol_shape(sym_name) if sym_name else None
        s3 = _load_model_shape(mdl_name) if mdl_name else None

        if not s2: log_w("Proto 2D no disponible (s2=None)")
        if not s3: log_w("Proto 3D no disponible (s3=None)")
        return s2, s3

    def _build_shape(self, obj):
        """Construye la Shape en marco local del objeto (no toca obj.Placement)."""
        s2, s3 = self._shapes_from_registry(obj)

        yaw = float(obj.Giro)  # yaw local Z
        off = App.Vector(float(obj.OffsetX), float(obj.OffsetY), 0.0)
        h = float(obj.AlturaRel)

        shapes = []
        physical_only = (
            _safe_text(getattr(obj, "RepresentationContract", REPRESENTATION_CONTRACT_LEGACY))
            == REPRESENTATION_CONTRACT_A1
        )

        # 2D: planta Z=0 (offset + yaw)
        if not physical_only and obj.ModoVisual in ("Ambos", "Solo2D") and s2:
            s2c = s2.copy()
            s2c.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), yaw)
            s2c.translate(off)
            shapes.append(s2c)
        elif not physical_only and obj.ModoVisual in ("Ambos", "Solo2D") and not s2:
            log_w("Proto 2D no disponible")

        # 3D: offset + altura; si Horizontal, +90Ãƒâ€šÃ‚Â° sobre Y solo al 3D
        if (physical_only or obj.ModoVisual in ("Ambos", "Solo3D")) and s3:
            s3c = s3.copy()
            s3c.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), yaw)
            if obj.OrientacionPared == "Horizontal":
                s3c.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
            s3c.translate(App.Vector(off.x, off.y, h))
            shapes.append(s3c)
        elif (physical_only or obj.ModoVisual in ("Ambos", "Solo3D")) and not s3:
            log_w("Proto 3D no disponible")

        if not shapes:
            # Fallback: cubo testigo (100x100x10) elevado a AlturaRel
            try:
                bx = Part.makeBox(100, 100, 10)
                bx.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), yaw)
                if obj.OrientacionPared == "Horizontal":
                    bx.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
                bx.translate(App.Vector(off.x, off.y, h))
                log_w("Usando CUBO TESTIGO (no se cargaron prototipos 2D/3D).")
                return Part.makeCompound([bx])
            except Exception as ex:
                log_e(f"Fallo creando cubo testigo: {ex}")
                return None

        return Part.makeCompound(shapes)

    def execute(self, obj):
        if not hasattr(self, "initialized"):
            # Compatibilidad con documentos antiguos (proxy sin __init__/__setstate__)
            self.initialized = True
        if not self.initialized:
            return
        # Asegurar referencia al objeto tras restaurar documento
        self.Object = obj
        log_i(f"execute() llamado para {obj.Name}")
        try:
            comp = self._build_shape(obj)
            if comp:
                obj.Shape = comp
                if GUI_UP and hasattr(obj, "ViewObject"):
                    try:
                        obj.ViewObject.Visibility = not bool(getattr(obj, "EsPrototipo", False))
                        obj.ViewObject.Transparency = 0
                        obj.ViewObject.DisplayMode = "Flat Lines"
                    except Exception:
                        pass
                contract = _safe_text(
                    getattr(obj, "RepresentationContract", REPRESENTATION_CONTRACT_LEGACY)
                )
                log_i(
                    f"Shape regenerada en {obj.Name} con modo={obj.ModoVisual} "
                    f"contrato={contract}"
                )
            else:
                obj.Shape = Part.Shape()
                log_w("No se pudo construir Shape (sin recursos vÃƒÆ’Ã‚Â¡lidos).")
        except Exception as ex:
            log_e(f"execute fallo: {ex}")


    def __repr__(self):
        # Representación corta y segura
        return f"<TomaUnoProxy at {hex(id(self))}>"

    def __getstate__(self):
        """
        Si alguna herramienta intenta serializar el Proxy, devolvemos un estado
        mínimo 100% JSON-serializable.
        """
        return {"class": "TomaUnoProxy", "version": "revF-min"}

    def __setstate__(self, state):
        # Estado m?nimo tras restaurar documento (evita AttributeError)
        self.initialized = True
        self.Object = None
# -----------------------------------------------------------------------------
def _safe_name_token(value, fallback="X"):
    txt = _safe_text(value).strip()
    if not txt:
        return fallback
    txt = re.sub(r"[^0-9A-Za-z_]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt or fallback


def _ensure_group(doc, name, parent=None):
    if not doc:
        return None
    grp = doc.getObject(name)
    if grp:
        return grp
    try:
        grp = doc.addObject("App::DocumentObjectGroup", name)
    except Exception:
        return None
    try:
        if parent and hasattr(parent, "addObject"):
            parent.addObject(grp)
    except Exception:
        pass
    return grp


def _ensure_master_group(doc):
    g_elec = _ensure_group(doc, "electrico", parent=None)
    g_lib = _ensure_group(doc, "_lib", parent=g_elec)
    g_dev = _ensure_group(doc, "_lib_devices", parent=g_lib or g_elec)
    return g_dev


def _mark_as_master(master):
    if master is None:
        return
    try:
        if "EsPrototipo" not in (master.PropertiesList or []):
            master.addProperty(
                "App::PropertyBool",
                "EsPrototipo",
                "Link",
                "Objeto maestro compartido; no es una instancia fisica",
            )
        master.EsPrototipo = True
    except Exception:
        pass


def _ensure_link_metadata(
    obj,
    tipo_logico,
    key_registro,
    modo_visual,
    altura_rel,
    orientacion_pared,
    representation_contract=REPRESENTATION_CONTRACT_LEGACY,
):
    if not obj:
        return
    defs = [
        ("App::PropertyString", "Tipo", "Registro", "Tipo logico"),
        ("App::PropertyString", "KeyRegistro", "Registro", "Clave registro"),
        ("App::PropertyString", "ModoVisual", "Core", "Modo visual"),
        ("App::PropertyFloat", "AlturaRel", "Core", "Altura relativa (mm)"),
        ("App::PropertyString", "OrientacionPared", "Core", "Orientacion pared"),
        (
            "App::PropertyString",
            "RepresentationContract",
            "Representations",
            "Contrato activo de representacion",
        ),
    ]
    for ptype, pname, pgroup, pdesc in defs:
        try:
            if pname not in obj.PropertiesList:
                obj.addProperty(ptype, pname, pgroup, pdesc)
        except Exception:
            pass
    try:
        obj.Tipo = _safe_text(tipo_logico)
    except Exception:
        pass
    try:
        obj.KeyRegistro = _safe_text(key_registro)
    except Exception:
        pass
    try:
        obj.ModoVisual = _safe_text(modo_visual)
    except Exception:
        pass
    try:
        obj.AlturaRel = float(altura_rel or 0.0)
    except Exception:
        pass
    try:
        obj.OrientacionPared = _safe_text(orientacion_pared)
    except Exception:
        pass
    try:
        obj.RepresentationContract = (
            _safe_text(representation_contract) or REPRESENTATION_CONTRACT_LEGACY
        )
    except Exception:
        pass


def _master_name_for(
    key_registro,
    tipo_logico,
    modo_visual,
    altura_rel,
    orientacion_pared,
    representation_contract=REPRESENTATION_CONTRACT_LEGACY,
):
    k = _safe_name_token(key_registro, "SinKey")
    t = _safe_name_token(tipo_logico, "Tipo")
    m = _safe_name_token(modo_visual, "Ambos")
    o = _safe_name_token(orientacion_pared, "Vertical")
    h = int(round(float(altura_rel or 0.0)))
    suffix = "_A1Physical" if representation_contract == REPRESENTATION_CONTRACT_A1 else ""
    return f"Master_{k}_{t}_{m}_{o}_{h}{suffix}"


def _get_or_create_master_toma(doc, key_registro=None, tipo_logico=None, modo_visual="Ambos",
                               altura_rel=300.0, orientacion_pared="Vertical", hide_master=True,
                               representation_contract=REPRESENTATION_CONTRACT_LEGACY):
    master_name = _master_name_for(
        key_registro,
        tipo_logico,
        modo_visual,
        altura_rel,
        orientacion_pared,
        representation_contract=representation_contract,
    )
    master = doc.getObject(master_name)
    if master and master.TypeId == "Part::FeaturePython":
        _mark_as_master(master)
        if hide_master and GUI_UP:
            try:
                master.ViewObject.Visibility = False
            except Exception:
                pass
        return master

    master = crear_toma_uno(
        doc=doc,
        name_prefix=master_name,
        key_registro=key_registro,
        tipo_logico=tipo_logico,
        internal_name=master_name,
        recompute=False,
        representation_contract=representation_contract,
    )
    try:
        master.ModoVisual = _safe_text(modo_visual or "Ambos") or "Ambos"
    except Exception:
        pass
    try:
        master.AlturaRel = float(altura_rel or 0.0)
    except Exception:
        pass
    try:
        master.OrientacionPared = _safe_text(orientacion_pared or "Vertical") or "Vertical"
    except Exception:
        pass
    try:
        master.RepresentationContract = (
            _safe_text(representation_contract) or REPRESENTATION_CONTRACT_LEGACY
        )
    except Exception:
        pass
    try:
        master.Giro = 0.0
    except Exception:
        pass
    try:
        master.Placement = App.Placement()
    except Exception:
        pass
    _mark_as_master(master)

    g_dev = _ensure_master_group(doc)
    try:
        if g_dev and hasattr(g_dev, "addObject"):
            if master not in (g_dev.Group or []):
                g_dev.addObject(master)
    except Exception:
        pass

    if hide_master and GUI_UP:
        try:
            master.ViewObject.Visibility = False
        except Exception:
            pass
    return master


def _property_text(obj, names, default=""):
    """Return the first non-empty property as plain text."""
    if obj is None:
        return _safe_text(default)
    props = list(getattr(obj, "PropertiesList", []) or [])
    for name in tuple(names or ()):
        if name not in props:
            continue
        try:
            value = _safe_text(getattr(obj, name, "")).strip()
        except Exception:
            value = ""
        if value:
            return value
    return _safe_text(default)


def _property_float(obj, names, default=0.0):
    """Return the first available numeric property as float."""
    if obj is None:
        return float(default)
    props = list(getattr(obj, "PropertiesList", []) or [])
    for name in tuple(names or ()):
        if name not in props:
            continue
        try:
            value = getattr(obj, name)
            if hasattr(value, "Value"):
                value = value.Value
            return float(value)
        except Exception:
            continue
    return float(default)


def _linked_master(obj):
    if str(getattr(obj, "TypeId", "") or "") != "App::Link":
        return None
    try:
        return getattr(obj, "LinkedObject", None) or getattr(obj, "Link", None)
    except Exception:
        return None


def is_electriccr_device(obj):
    """Return True for a direct TomaUno device or one of its App::Link instances."""
    candidate = _linked_master(obj) or obj
    if candidate is None:
        return False
    props = set(getattr(candidate, "PropertiesList", []) or [])
    if not {"AlturaRel", "ModoVisual"}.issubset(props):
        return False
    proxy = getattr(candidate, "Proxy", None)
    if isinstance(proxy, TomaUnoProxy):
        return True
    # Restored legacy documents can lose the Python proxy but retain the
    # ElectricCR semantic property set.
    return "KeyRegistro" in props and ("Tipo" in props or "LnkMasterKey" in props)


def installation_elevation_mm(obj):
    """Return the semantic 3D installation height for an ElectricCR device."""
    if not is_electriccr_device(obj):
        raise ValueError("El objeto no es un dispositivo ElectricCR compatible")
    master = _linked_master(obj)
    if master is not None:
        props = set(getattr(obj, "PropertiesList", []) or [])
        if "AlturaRel" in props:
            return _property_float(obj, ("AlturaRel",), 0.0)
        return _property_float(master, ("AlturaRel", "LnkMasterAltura"), 0.0)
    return _property_float(obj, ("AlturaRel",), 0.0)


def set_installation_elevation(obj, elevation_mm):
    """Set only the ElectricCR device's relative 3D installation height.

    Direct FeaturePython devices update ``AlturaRel`` and are touched for the
    document's next recompute. App::Link instances are relinked to a matching
    immutable master; instance Placement, Label and group ownership remain.
    This function intentionally does not recompute the document.
    """
    if not is_electriccr_device(obj):
        raise ValueError("El objeto no es un dispositivo ElectricCR compatible")

    target_mm = float(elevation_mm)
    master = _linked_master(obj)
    if master is None:
        old_mm = _property_float(obj, ("AlturaRel",), 0.0)
        obj.AlturaRel = target_mm
        try:
            obj.touch()
        except Exception:
            pass
        return {
            "strategy": "electriccr_direct",
            "old_mm": old_mm,
            "new_mm": target_mm,
            "master_old": "",
            "master_new": "",
        }

    old_mm = installation_elevation_mm(obj)
    key_registro = _property_text(
        obj, ("KeyRegistro",),
        _property_text(master, ("KeyRegistro", "LnkMasterKey"), ""),
    )
    tipo_logico = _property_text(
        obj, ("Tipo",),
        _property_text(master, ("Tipo",), "Toma"),
    )
    modo_visual = _property_text(
        obj, ("ModoVisual",),
        _property_text(master, ("ModoVisual", "LnkMasterMode"), "Ambos"),
    ) or "Ambos"
    orientacion = _property_text(
        obj, ("OrientacionPared",),
        _property_text(master, ("OrientacionPared",), "Vertical"),
    ) or "Vertical"
    representation_contract = _property_text(
        obj,
        ("RepresentationContract",),
        _property_text(
            master,
            ("RepresentationContract",),
            REPRESENTATION_CONTRACT_LEGACY,
        ),
    ) or REPRESENTATION_CONTRACT_LEGACY

    if not key_registro:
        raise ValueError("El App::Link ElectricCR no tiene KeyRegistro recuperable")

    placement = App.Placement(obj.Placement)
    old_master_name = _safe_text(getattr(master, "Name", ""))
    new_master = _get_or_create_master_toma(
        doc=obj.Document,
        key_registro=key_registro,
        tipo_logico=tipo_logico,
        modo_visual=modo_visual,
        altura_rel=target_mm,
        orientacion_pared=orientacion,
        hide_master=True,
        representation_contract=representation_contract,
    )
    if new_master is None:
        raise RuntimeError("No se pudo crear el maestro ElectricCR para la nueva altura")

    obj.LinkedObject = new_master
    obj.Placement = placement
    _ensure_link_metadata(
        obj,
        tipo_logico=tipo_logico,
        key_registro=key_registro,
        modo_visual=modo_visual,
        altura_rel=target_mm,
        orientacion_pared=orientacion,
        representation_contract=representation_contract,
    )
    try:
        obj.touch()
    except Exception:
        pass

    return {
        "strategy": "electriccr_link",
        "old_mm": old_mm,
        "new_mm": target_mm,
        "master_old": old_master_name,
        "master_new": _safe_text(getattr(new_master, "Name", "")),
    }


def _ensure_documentation_owner_properties(obj):
    definitions = (
        (
            "App::PropertyString",
            "DocumentationRepresentationName",
            "Representations",
            "Nombre persistente de la representacion PLAN; el hijo enlaza al propietario",
        ),
        (
            "App::PropertyBool",
            "MostrarModelo3D",
            "Representations",
            "Mostrar la representacion fisica 3D",
        ),
        (
            "App::PropertyBool",
            "MostrarSimboloPlano",
            "Representations",
            "Mostrar la representacion documental PLAN",
        ),
        (
            "App::PropertyFloat",
            "PlanSymbolScale",
            "Representations",
            "Escala grafica del simbolo PLAN; no afecta Shape fisica",
        ),
        (
            "App::PropertyFloat",
            "DocumentationPlaneZ",
            "Representations",
            "Cota documental PLAN independiente de la altura fisica",
        ),
    )
    added = []
    for ptype, pname, group, description in definitions:
        if pname in list(getattr(obj, "PropertiesList", []) or []):
            continue
        obj.addProperty(ptype, pname, group, description)
        added.append(pname)
        if pname in ("MostrarModelo3D", "MostrarSimboloPlano"):
            setattr(obj, pname, True)
        elif pname == "PlanSymbolScale":
            setattr(obj, pname, 1.0)
        elif pname == "DocumentationPlaneZ":
            setattr(obj, pname, 0.0)
    return added


def _documentation_candidates(owner, role=REPRESENTATION_ROLE_PLAN):
    if owner is None or getattr(owner, "Document", None) is None:
        return []
    matches = []
    for candidate in list(owner.Document.Objects or []):
        props = set(getattr(candidate, "PropertiesList", []) or [])
        if "DocumentationOnly" not in props or not bool(getattr(candidate, "DocumentationOnly", False)):
            continue
        if "RepresentationRole" not in props or _safe_text(candidate.RepresentationRole) != role:
            continue
        if "Owner" in props and getattr(candidate, "Owner", None) is owner:
            matches.append(candidate)
    return matches


def get_physical_shape(obj):
    """Return the authoritative physical Shape without adding documentation."""
    if obj is None or not hasattr(obj, "Shape"):
        return None
    return obj.Shape


def get_plan_representation(obj):
    """Return the PLAN documentation object associated with one device."""
    if obj is None:
        return None
    props = set(getattr(obj, "PropertiesList", []) or [])
    if "DocumentationOnly" in props and bool(getattr(obj, "DocumentationOnly", False)):
        return obj if _safe_text(getattr(obj, "RepresentationRole", "")) == REPRESENTATION_ROLE_PLAN else None
    if "DocumentationRepresentationName" in props and getattr(obj, "Document", None) is not None:
        candidate = obj.Document.getObject(_safe_text(obj.DocumentationRepresentationName))
        if candidate is not None and getattr(candidate, "Owner", None) is obj:
            return candidate
    matches = _documentation_candidates(obj)
    return matches[0] if len(matches) == 1 else None


def resolve_representation_owner(candidate):
    """Resolve the single electromechanical owner from either owner or PLAN object."""
    if candidate is None:
        return None
    props = set(getattr(candidate, "PropertiesList", []) or [])
    if "DocumentationOnly" in props and bool(getattr(candidate, "DocumentationOnly", False)):
        return getattr(candidate, "Owner", None) if "Owner" in props else None
    return candidate if is_electriccr_device(candidate) else None


def _plan_source_shape(owner):
    source = _linked_master(owner) or owner
    proxy = getattr(source, "Proxy", None)
    symbol = None
    if proxy is not None and hasattr(proxy, "_shapes_from_registry"):
        symbol, _model = proxy._shapes_from_registry(source)
    if symbol is None:
        key = _property_text(source, ("KeyRegistro",), _property_text(owner, ("KeyRegistro",), ""))
        info = (REGISTRY.get("types") or {}).get(key, {}) or {}
        symbol = _load_symbol_shape(info.get("symbol2D", ""))
    if symbol is None:
        raise RuntimeError("No se pudo resolver la geometria documental PLAN")

    shape = symbol.copy()
    yaw = _property_float(source, ("Giro",), 0.0)
    offset_x = _property_float(source, ("OffsetX",), 0.0)
    offset_y = _property_float(source, ("OffsetY",), 0.0)
    scale = max(0.001, _property_float(owner, ("PlanSymbolScale",), 1.0))
    if abs(scale - 1.0) > 1.0e-12:
        matrix = App.Matrix()
        matrix.A11 = scale
        matrix.A22 = scale
        matrix.A33 = scale
        shape = shape.transformGeometry(matrix)
    if abs(yaw) > 1.0e-12:
        shape.rotate(App.Vector(), App.Vector(0.0, 0.0, 1.0), yaw)
    if abs(offset_x) > 1.0e-12 or abs(offset_y) > 1.0e-12:
        shape.translate(App.Vector(offset_x, offset_y, 0.0))
    return shape


def _plan_placement(owner):
    placement = App.Placement(owner.Placement)
    placement.Base = App.Vector(
        float(placement.Base.x),
        float(placement.Base.y),
        _property_float(owner, ("DocumentationPlaneZ",), 0.0),
    )
    return placement


def _plan_spatial_expression():
    """Return the native document dependency from PLAN to its Owner."""
    return (
        "placement(vector(Owner.Placement.Base.x; Owner.Placement.Base.y; "
        "Owner.DocumentationPlaneZ); Owner.Placement.Rotation)"
    )


def _normalize_expression(expression):
    value = "".join(_safe_text(expression).split())
    return value.replace(".Owner.", "Owner.")


def _plan_placement_expression(plan):
    for path, expression in list(getattr(plan, "ExpressionEngine", []) or []):
        if _safe_text(path).lstrip(".") == "Placement":
            return _safe_text(expression)
    return ""


def _plan_has_spatial_dependency(plan, owner):
    if plan is None or getattr(plan, "Owner", None) is not owner:
        return False
    return _normalize_expression(_plan_placement_expression(plan)) == _normalize_expression(
        _plan_spatial_expression()
    )


def _bind_plan_spatial_dependency(plan):
    """Bind PLAN Placement atomically; remove obsolete component expressions."""
    for path, _expression in list(getattr(plan, "ExpressionEngine", []) or []):
        clean_path = _safe_text(path).lstrip(".")
        if clean_path == "Placement" or clean_path.startswith("Placement."):
            plan.setExpression(clean_path, None)
    plan.setExpression("Placement", _plan_spatial_expression())


def _plan_signature(owner):
    source = _linked_master(owner) or owner
    values = (
        REPRESENTATION_SCHEMA_VERSION,
        _property_text(source, ("KeyRegistro",), _property_text(owner, ("KeyRegistro",), "")),
        round(_property_float(source, ("Giro",), 0.0), 9),
        round(_property_float(source, ("OffsetX",), 0.0), 9),
        round(_property_float(source, ("OffsetY",), 0.0), 9),
        round(_property_float(owner, ("PlanSymbolScale",), 1.0), 9),
    )
    return repr(values)


def _shape_metrics(shape):
    if shape is None or shape.isNull():
        return {
            "volume": 0.0,
            "bound_box": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            "solids": 0,
            "faces": 0,
        }
    box = shape.BoundBox
    return {
        "volume": round(float(shape.Volume), 9),
        "bound_box": tuple(
            round(float(value), 9)
            for value in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)
        ),
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
    }




def _plan_owner_property_type(plan):
    if plan is None or "Owner" not in set(getattr(plan, "PropertiesList", []) or []):
        return ""
    try:
        return _safe_text(plan.getTypeIdOfProperty("Owner"))
    except Exception:
        return ""


def _migrate_plan_owner_to_hidden(plan, owner):
    """Migrate legacy PLAN.Owner PropertyLink to PropertyLinkHidden transactionally."""
    current_type = _plan_owner_property_type(plan)
    if current_type == "App::PropertyLinkHidden":
        plan.Owner = owner
        return False
    if current_type not in ("", "App::PropertyLink"):
        raise RuntimeError(
            "Tipo Owner PLAN no soportado para A1: %s" % (current_type or "<desconocido>")
        )

    saved_expressions = list(getattr(plan, "ExpressionEngine", []) or [])
    if current_type == "App::PropertyLink":
        # Clear expressions that can dereference Owner before removing the dynamic property.
        # The surrounding document transaction makes the migration rollback-safe.
        for path, expression in saved_expressions:
            if "Owner" in _safe_text(expression):
                plan.setExpression(_safe_text(path).lstrip("."), None)
        if not bool(plan.removeProperty("Owner")):
            raise RuntimeError("No se pudo reemplazar PLAN.Owner por PropertyLinkHidden")

    if "Owner" not in set(getattr(plan, "PropertiesList", []) or []):
        plan.addProperty(
            "App::PropertyLinkHidden",
            "Owner",
            "Representations",
            "Propietario electromecanico autoritativo",
        )
    plan.Owner = owner

    # Restore any expressions cleared for migration. The canonical Placement binding is
    # verified/rebuilt immediately afterwards by sync_plan_representation().
    for path, expression in saved_expressions:
        clean_path = _safe_text(path).lstrip(".")
        if expression and "Owner" in _safe_text(expression):
            plan.setExpression(clean_path, _safe_text(expression))
    return current_type == "App::PropertyLink"


def _ensure_plan_properties(plan, owner):
    definitions = (
        ("App::PropertyBool", "DocumentationOnly", "Representations", "No es geometria fisica ni otra identidad"),
        ("App::PropertyString", "RepresentationRole", "Representations", "PLAN, ELEVATION o SCHEMATIC"),
        ("App::PropertyInteger", "RepresentationSchemaVersion", "Representations", "Version del contrato documental"),
        ("App::PropertyString", "RepresentationSignature", "Representations", "Firma para sincronizacion idempotente"),
        ("App::PropertyVectorList", "SnapPoints", "Representations", "Puntos locales para Draft Snap Special"),
    )
    for ptype, pname, group, description in definitions:
        if pname not in list(getattr(plan, "PropertiesList", []) or []):
            plan.addProperty(ptype, pname, group, description)
    _migrate_plan_owner_to_hidden(plan, owner)
    plan.DocumentationOnly = True
    plan.RepresentationRole = REPRESENTATION_ROLE_PLAN
    plan.RepresentationSchemaVersion = REPRESENTATION_SCHEMA_VERSION
    # Native Draft Snap Special consumes local SnapPoints and transforms them
    # through the object's Placement. Keep exactly one insertion point at the
    # PLAN local origin so the CAD base point and Device.Placement coincide.
    plan.SnapPoints = [App.Vector(0.0, 0.0, 0.0)]


def _plan_has_insertion_snap(plan):
    """Return True when PLAN exposes exactly the canonical local origin snap."""
    if plan is None or "SnapPoints" not in set(getattr(plan, "PropertiesList", []) or []):
        return False
    try:
        points = list(plan.SnapPoints or [])
    except Exception:
        return False
    if len(points) != 1:
        return False
    try:
        point = points[0]
        return (
            abs(float(point.x)) <= 1.0e-9
            and abs(float(point.y)) <= 1.0e-9
            and abs(float(point.z)) <= 1.0e-9
        )
    except Exception:
        return False


def _plan_group_parents(plan):
    """Return DocumentObjectGroup-like parents that explicitly contain PLAN."""
    if plan is None:
        return []
    result = []
    try:
        parents = list(getattr(plan, "InList", []) or [])
    except Exception:
        parents = []
    for parent in parents:
        try:
            group = list(getattr(parent, "Group", []) or [])
        except Exception:
            continue
        if plan in group and hasattr(parent, "removeObject"):
            result.append(parent)
    return result


def _detach_plan_from_groups(plan):
    """Keep PLAN as an owned auxiliary representation, never as a sibling device in user groups."""
    removed = []
    for parent in _plan_group_parents(plan):
        try:
            parent.removeObject(plan)
            removed.append(_safe_text(getattr(parent, "Name", "")))
        except Exception:
            pass
    return removed

def sync_plan_representation(owner, dry_run=True, manage_transaction=True):
    """Plan or synchronize one hidden-tree PLAN object without changing owner.Shape."""
    if owner is None or not is_electriccr_device(owner):
        raise ValueError("Se requiere un dispositivo ElectricCR compatible")
    contract = _property_text(owner, ("RepresentationContract",), REPRESENTATION_CONTRACT_LEGACY)
    if contract != REPRESENTATION_CONTRACT_A1:
        raise ValueError("El dispositivo no utiliza el contrato PhysicalDocumentationA1")
    doc = owner.Document
    physical = get_physical_shape(owner)
    physical_metrics = _shape_metrics(physical)
    owner_props = set(getattr(owner, "PropertiesList", []) or [])
    current = None
    if "DocumentationRepresentationName" in owner_props:
        current = doc.getObject(_safe_text(owner.DocumentationRepresentationName))
        if current is not None and getattr(current, "Owner", None) is not owner:
            current = None
    matches = _documentation_candidates(owner)
    if current is None and len(matches) == 1:
        current = matches[0]
    if len(matches) > 1:
        raise RuntimeError("Existen multiples representaciones PLAN para el mismo propietario")
    expected_signature = _plan_signature(owner)
    current_signature = _property_text(current, ("RepresentationSignature",), "")
    actions = []
    missing_owner_props = {
        "DocumentationRepresentationName",
        "MostrarModelo3D",
        "MostrarSimboloPlano",
        "PlanSymbolScale",
        "DocumentationPlaneZ",
    } - owner_props
    if missing_owner_props:
        actions.append("ADD_OWNER_PROPERTIES")
    if current is None:
        actions.append("CREATE_PLAN_REPRESENTATION")
    elif current_signature != expected_signature:
        actions.append("UPDATE_PLAN_REPRESENTATION")
    if current is not None and _plan_owner_property_type(current) != "App::PropertyLinkHidden":
        actions.append("MIGRATE_PLAN_OWNER_LINK_HIDDEN")
    if current is not None and not _plan_has_spatial_dependency(current, owner):
        actions.append("BIND_PLAN_TO_OWNER_PLACEMENT")
    if current is not None and not _plan_has_insertion_snap(current):
        actions.append("SET_PLAN_INSERTION_SNAP")
    if current is not None and _plan_group_parents(current):
        actions.append("DETACH_PLAN_FROM_GROUPS")
    if current is not None and (
        "DocumentationRepresentationName" not in owner_props
        or _safe_text(getattr(owner, "DocumentationRepresentationName", "")) != current.Name
    ):
        actions.append("LINK_PLAN_REPRESENTATION")
    if dry_run:
        return {
            "dry_run": True,
            "material_changes": len(actions),
            "actions": actions,
            "physical_metrics": physical_metrics,
            "representation": _safe_text(getattr(current, "Name", "")),
        }

    if manage_transaction:
        doc.openTransaction("ElectricCR synchronize PLAN representation")
    try:
        _ensure_documentation_owner_properties(owner)
        current = get_plan_representation(owner)
        if current is None:
            token = _safe_name_token(
                _property_text(owner, ("ElementUID",), _safe_text(owner.Name)),
                "Device",
            )
            current = doc.addObject("Part::Feature", "ECR_DocPlan_%s" % token)
            current.Label = "%s [PLAN]" % (_safe_text(getattr(owner, "Label", "")) or owner.Name)
        _ensure_plan_properties(current, owner)
        _detach_plan_from_groups(current)
        expected_signature = _plan_signature(owner)
        if _property_text(current, ("RepresentationSignature",), "") != expected_signature:
            current.Shape = _plan_source_shape(owner)
            current.RepresentationSignature = expected_signature
        if not _plan_has_spatial_dependency(current, owner):
            _bind_plan_spatial_dependency(current)
        owner.DocumentationRepresentationName = current.Name
        # Keep historical ModoVisual and separated A1 visibility coherent.
        apply_visual_mode(
            owner,
            _property_text(owner, ("ModoVisual",), "Ambos"),
            update_mode_property=False,
        )
        if get_physical_shape(owner) is None or _shape_metrics(owner.Shape) != physical_metrics:
            raise RuntimeError("La sincronizacion PLAN altero Shape fisica")
        if manage_transaction:
            doc.commitTransaction()
    except Exception:
        if manage_transaction:
            doc.abortTransaction()
        raise
    doc.recompute()
    if GUI_UP:
        _apply_representation_visibility_views(owner)
        try:
            current.ViewObject.ShowInTree = False
            current.ViewObject.Selectable = True
        except Exception:
            pass
    log_i(
        "PLAN synchronized owner=%s representation=%s actions=%s"
        % (owner.Name, current.Name, ",".join(actions) or "NONE")
    )
    return {
        "dry_run": False,
        "material_changes": len(actions),
        "actions": actions,
        "physical_metrics": physical_metrics,
        "representation": current.Name,
    }


def _canonical_visual_mode(value):
    """Return canonical Ambos/Solo2D/Solo3D or an empty string."""
    key = _safe_text(value).strip().lower().replace(" ", "")
    return {
        "ambos": "Ambos",
        "both": "Ambos",
        "solo2d": "Solo2D",
        "2d": "Solo2D",
        "solo3d": "Solo3D",
        "3d": "Solo3D",
    }.get(key, "")


def _visual_mode_flags(mode):
    canonical = _canonical_visual_mode(mode)
    if canonical == "Solo2D":
        return False, True
    if canonical == "Solo3D":
        return True, False
    return True, True


def _mode_from_visibility_flags(show_model_3d, show_plan):
    pair = (bool(show_model_3d), bool(show_plan))
    if pair == (True, True):
        return "Ambos"
    if pair == (False, True):
        return "Solo2D"
    if pair == (True, False):
        return "Solo3D"
    return ""


def _apply_representation_visibility_views(owner):
    """Apply stored A1 visibility flags to the two ViewObjects only."""
    plan = get_plan_representation(owner)
    if GUI_UP:
        try:
            owner.ViewObject.Visibility = bool(owner.MostrarModelo3D)
        except Exception:
            pass
        if plan is not None:
            try:
                plan.ViewObject.Visibility = bool(owner.MostrarSimboloPlano)
            except Exception:
                pass
    return plan


def apply_visual_mode(owner, mode=None, update_mode_property=True):
    """Apply ModoVisual to separated A1 physical/PLAN representations."""
    if owner is None:
        raise ValueError("Se requiere un dispositivo ElectricCR")

    contract = _property_text(
        owner, ("RepresentationContract",), REPRESENTATION_CONTRACT_LEGACY
    )
    canonical = _canonical_visual_mode(
        mode if mode is not None else getattr(owner, "ModoVisual", "Ambos")
    ) or "Ambos"

    if contract != REPRESENTATION_CONTRACT_A1:
        # Legacy keeps its historical geometry-based ModoVisual behavior.
        if update_mode_property and hasattr(owner, "ModoVisual"):
            try:
                owner.ModoVisual = canonical
                owner.touch()
            except Exception:
                pass
        return {
            "mode": canonical,
            "show_model_3d": canonical in ("Ambos", "Solo3D"),
            "show_plan": canonical in ("Ambos", "Solo2D"),
            "a1": False,
        }

    _ensure_documentation_owner_properties(owner)
    show_model_3d, show_plan = _visual_mode_flags(canonical)

    if update_mode_property and hasattr(owner, "ModoVisual"):
        try:
            if _canonical_visual_mode(getattr(owner, "ModoVisual", "")) != canonical:
                owner.ModoVisual = canonical
        except Exception:
            pass

    try:
        if bool(owner.MostrarModelo3D) != bool(show_model_3d):
            owner.MostrarModelo3D = bool(show_model_3d)
    except Exception:
        pass
    try:
        if bool(owner.MostrarSimboloPlano) != bool(show_plan):
            owner.MostrarSimboloPlano = bool(show_plan)
    except Exception:
        pass

    _apply_representation_visibility_views(owner)
    return {
        "mode": canonical,
        "show_model_3d": bool(show_model_3d),
        "show_plan": bool(show_plan),
        "a1": True,
    }


def set_representation_visibility(owner, show_model_3d=None, show_plan=None):
    """Set independent A1 visibility flags without rebuilding either Shape.

    If the pair corresponds to Ambos/Solo2D/Solo3D, mirror ModoVisual so the
    historical visibility manager and A1 stay coherent.
    """
    _ensure_documentation_owner_properties(owner)
    if show_model_3d is not None:
        owner.MostrarModelo3D = bool(show_model_3d)
    if show_plan is not None:
        owner.MostrarSimboloPlano = bool(show_plan)

    mode = _mode_from_visibility_flags(
        bool(owner.MostrarModelo3D),
        bool(owner.MostrarSimboloPlano),
    )
    if mode and hasattr(owner, "ModoVisual"):
        try:
            if _canonical_visual_mode(getattr(owner, "ModoVisual", "")) != mode:
                owner.ModoVisual = mode
        except Exception:
            pass

    _apply_representation_visibility_views(owner)
    return {
        "mode": mode or _safe_text(getattr(owner, "ModoVisual", "")),
        "show_model_3d": bool(owner.MostrarModelo3D),
        "show_plan": bool(owner.MostrarSimboloPlano),
    }


def export_plan_dxf(owners, filepath):
    """Export only PLAN representation objects through FreeCAD's DXF exporter."""
    representations = []
    seen = set()
    for owner in list(owners or []):
        plan = get_plan_representation(owner)
        name = _safe_text(getattr(plan, "Name", ""))
        if plan is not None and name and name not in seen:
            representations.append(plan)
            seen.add(name)
    if not representations:
        raise ValueError("No hay representaciones PLAN exportables")
    import importDXF

    importDXF.export(representations, str(filepath))
    return representations


def cleanup_orphan_documentation(doc, dry_run=True):
    """Report or remove DocumentationOnly objects whose Owner no longer exists."""
    orphans = []
    for candidate in list(getattr(doc, "Objects", []) or []):
        props = set(getattr(candidate, "PropertiesList", []) or [])
        if "DocumentationOnly" not in props or not bool(getattr(candidate, "DocumentationOnly", False)):
            continue
        owner = getattr(candidate, "Owner", None) if "Owner" in props else None
        if owner is None or doc.getObject(_safe_text(getattr(owner, "Name", ""))) is None:
            orphans.append(candidate)
    if dry_run or not orphans:
        return [obj.Name for obj in orphans]
    doc.openTransaction("ElectricCR clean orphan documentation")
    try:
        names = [obj.Name for obj in orphans]
        for name in names:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return names


def remove_device_with_documentation(owner):
    """Delete one owner and its documentation together inside one transaction."""
    if owner is None or getattr(owner, "Document", None) is None:
        return []
    doc = owner.Document
    targets = [obj.Name for obj in _documentation_candidates(owner)]
    owner_name = owner.Name
    doc.openTransaction("ElectricCR remove device and documentation")
    try:
        for name in targets:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
        if doc.getObject(owner_name) is not None:
            doc.removeObject(owner_name)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return targets + [owner_name]


def crear_toma_link(doc=None, name_prefix=None, key_registro=None, tipo_logico=None, placement=None,
                    modo_visual="Ambos", altura_rel=300.0, orientacion_pared="Vertical",
                    internal_name=None, recompute=True, target_group=None, hide_master=True,
                    separate_documentation=False):
    """
    Crea una instancia App::Link hacia un objeto maestro de dispositivo.
    Reduce peso porque la geometria se almacena una sola vez.
    """
    doc = doc or App.ActiveDocument or App.newDocument("Electrico")
    representation_contract = (
        REPRESENTATION_CONTRACT_A1
        if separate_documentation
        else REPRESENTATION_CONTRACT_LEGACY
    )

    master = _get_or_create_master_toma(
        doc=doc,
        key_registro=key_registro,
        tipo_logico=tipo_logico,
        modo_visual=modo_visual,
        altura_rel=altura_rel,
        orientacion_pared=orientacion_pared,
        hide_master=hide_master,
        representation_contract=representation_contract,
    )
    if master is None:
        raise RuntimeError("No se pudo crear/obtener master para App::Link.")

    if not internal_name:
        base = _safe_name_token(name_prefix or "TomaLink", "TomaLink")
        internal_name = f"Link_{base}"
    try:
        link = doc.addObject("App::Link", internal_name)
    except Exception:
        link = doc.addObject("App::Link")

    link.LinkedObject = master
    try:
        # Permite mover/rotar manualmente con herramientas de transformacion.
        link.LinkTransform = True
    except Exception:
        pass
    try:
        # Asegura que Placement/LinkPlacement no queden bloqueados para edicion.
        link.setEditorMode("Placement", 0)
    except Exception:
        pass
    try:
        link.setEditorMode("LinkPlacement", 0)
    except Exception:
        pass
    try:
        link.setPropertyStatus("Placement", [])
    except Exception:
        pass
    try:
        link.setPropertyStatus("LinkPlacement", [])
    except Exception:
        pass
    try:
        if hasattr(link, "LinkPlacement"):
            link.LinkPlacement = App.Placement()
    except Exception:
        pass
    if GUI_UP:
        try:
            if hasattr(link, "ViewObject") and link.ViewObject is not None:
                link.ViewObject.Selectable = True
        except Exception:
            pass
    if placement is not None:
        try:
            link.Placement = placement
        except Exception:
            pass
    if name_prefix:
        try:
            link.Label = _safe_text(name_prefix)
        except Exception:
            pass

    _ensure_link_metadata(
        link,
        tipo_logico,
        key_registro,
        modo_visual,
        altura_rel,
        orientacion_pared,
        representation_contract=representation_contract,
    )
    if separate_documentation:
        _ensure_documentation_owner_properties(link)

    grp = None
    if target_group is not None:
        if hasattr(target_group, "addObject"):
            grp = target_group
        elif isinstance(target_group, str) and target_group.strip():
            grp = _ensure_group(doc, target_group.strip(), parent=doc.getObject("electrico"))
    if grp is not None:
        try:
            if link not in (grp.Group or []):
                grp.addObject(link)
        except Exception:
            pass

    if recompute:
        try:
            doc.recompute()
        except Exception:
            pass
    # TomaUnoProxy.execute() makes its ViewProvider visible while rebuilding
    # geometry.  Masters are library objects, so enforce their requested hidden
    # state after the recompute too.
    if hide_master and GUI_UP:
        try:
            master.ViewObject.Visibility = False
        except Exception:
            pass
    if separate_documentation and recompute:
        sync_plan_representation(link, dry_run=False)
    log_i(f"created link device '{link.Name}' -> '{master.Name}' (Tipo={tipo_logico}, Key={key_registro})")
    return link


def crear_toma_uno(
    doc=None,
    name_prefix=None,
    key_registro=None,
    tipo_logico=None,
    internal_name=None,
    recompute=True,
    representation_contract=REPRESENTATION_CONTRACT_LEGACY,
):
    """
    Crea y retorna Part::FeaturePython con TomaUnoProxy.
    - name_prefix: prefijo opcional para Label inicial.
    - key_registro: clave (p.ej. 'Apagador_Simple'), para resolver prototipos del registro.
    - tipo_logico: 'Toma','Apagador','Luminaria','Sensor','Rociador','Altavoz','Camara'.
    """
    doc = doc or App.ActiveDocument or App.newDocument("Electrico")
    if internal_name:
        try:
            obj = doc.addObject("Part::FeaturePython", internal_name)
        except Exception:
            obj = doc.addObject("Part::FeaturePython")
    else:
        obj = doc.addObject("Part::FeaturePython")
    if name_prefix:
        try:
            obj.Label = f"{name_prefix}"
        except Exception:
            pass

    # Proxy + ViewProvider
    proxy = TomaUnoProxy()
    proxy.attach(obj)

    if GUI_UP and hasattr(obj, "ViewObject") and (obj.ViewObject is not None):
        try:
            VP_TomaUno(obj.ViewObject)
            obj.ViewObject.DisplayMode = "Flat Lines"
            obj.ViewObject.Visibility = True
            obj.ViewObject.Transparency = 0
        except Exception:
            pass

    # Propiedades clave
    if key_registro:
        obj.KeyRegistro = str(key_registro)
    if tipo_logico in ["Toma", "Apagador", "Luminaria", "Sensor", "Rociador", "Altavoz", "Camara"]:
        obj.Tipo = tipo_logico
    obj.RepresentationContract = (
        _safe_text(representation_contract) or REPRESENTATION_CONTRACT_LEGACY
    )

    # Disparar compute inicial
    obj.touch()
    if recompute:
        try:
            doc.recompute()
        except Exception:
            pass
    log_i(f"created single-node device '{obj.Name}' (Tipo={obj.Tipo}, Key={obj.KeyRegistro})")
    return obj
