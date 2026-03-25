# -*- coding: utf-8 -*-
"""
electriccr.features.objeto_toma_uno (rev H)

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
            vobj.Visibility = True
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

        sym_path = _find_resource(sym_name) if sym_name else None
        mdl_path = _find_resource(mdl_name) if mdl_name else None
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

        # 2D: planta Z=0 (offset + yaw)
        if obj.ModoVisual in ("Ambos", "Solo2D") and s2:
            s2c = s2.copy()
            s2c.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), yaw)
            s2c.translate(off)
            shapes.append(s2c)
        elif obj.ModoVisual in ("Ambos", "Solo2D") and not s2:
            log_w("Proto 2D no disponible")

        # 3D: offset + altura; si Horizontal, +90Ãƒâ€šÃ‚Â° sobre Y solo al 3D
        if obj.ModoVisual in ("Ambos", "Solo3D") and s3:
            s3c = s3.copy()
            s3c.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), yaw)
            if obj.OrientacionPared == "Horizontal":
                s3c.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
            s3c.translate(App.Vector(off.x, off.y, h))
            shapes.append(s3c)
        elif obj.ModoVisual in ("Ambos", "Solo3D") and not s3:
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
                        obj.ViewObject.Visibility = True
                        obj.ViewObject.Transparency = 0
                        obj.ViewObject.DisplayMode = "Flat Lines"
                    except Exception:
                        pass
                log_i(f"Shape regenerada en {obj.Name} con modo={obj.ModoVisual}")
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


def _ensure_link_metadata(obj, tipo_logico, key_registro, modo_visual, altura_rel, orientacion_pared):
    if not obj:
        return
    defs = [
        ("App::PropertyString", "Tipo", "Registro", "Tipo logico"),
        ("App::PropertyString", "KeyRegistro", "Registro", "Clave registro"),
        ("App::PropertyString", "ModoVisual", "Core", "Modo visual"),
        ("App::PropertyFloat", "AlturaRel", "Core", "Altura relativa (mm)"),
        ("App::PropertyString", "OrientacionPared", "Core", "Orientacion pared"),
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


def _master_name_for(key_registro, tipo_logico, modo_visual, altura_rel, orientacion_pared):
    k = _safe_name_token(key_registro, "SinKey")
    t = _safe_name_token(tipo_logico, "Tipo")
    m = _safe_name_token(modo_visual, "Ambos")
    o = _safe_name_token(orientacion_pared, "Vertical")
    h = int(round(float(altura_rel or 0.0)))
    return f"Master_{k}_{t}_{m}_{o}_{h}"


def _get_or_create_master_toma(doc, key_registro=None, tipo_logico=None, modo_visual="Ambos",
                               altura_rel=300.0, orientacion_pared="Vertical", hide_master=True):
    master_name = _master_name_for(key_registro, tipo_logico, modo_visual, altura_rel, orientacion_pared)
    master = doc.getObject(master_name)
    if master and master.TypeId == "Part::FeaturePython":
        return master

    master = crear_toma_uno(
        doc=doc,
        name_prefix=master_name,
        key_registro=key_registro,
        tipo_logico=tipo_logico,
        internal_name=master_name,
        recompute=False,
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
        master.Giro = 0.0
    except Exception:
        pass
    try:
        master.Placement = App.Placement()
    except Exception:
        pass

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


def crear_toma_link(doc=None, name_prefix=None, key_registro=None, tipo_logico=None, placement=None,
                    modo_visual="Ambos", altura_rel=300.0, orientacion_pared="Vertical",
                    internal_name=None, recompute=True, target_group=None, hide_master=True):
    """
    Crea una instancia App::Link hacia un objeto maestro de dispositivo.
    Reduce peso porque la geometria se almacena una sola vez.
    """
    doc = doc or App.ActiveDocument or App.newDocument("Electrico")

    master = _get_or_create_master_toma(
        doc=doc,
        key_registro=key_registro,
        tipo_logico=tipo_logico,
        modo_visual=modo_visual,
        altura_rel=altura_rel,
        orientacion_pared=orientacion_pared,
        hide_master=hide_master,
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

    _ensure_link_metadata(link, tipo_logico, key_registro, modo_visual, altura_rel, orientacion_pared)

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
    log_i(f"created link device '{link.Name}' -> '{master.Name}' (Tipo={tipo_logico}, Key={key_registro})")
    return link


def crear_toma_uno(doc=None, name_prefix=None, key_registro=None, tipo_logico=None, internal_name=None, recompute=True):
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

    # Disparar compute inicial
    obj.touch()
    if recompute:
        try:
            doc.recompute()
        except Exception:
            pass
    log_i(f"created single-node device '{obj.Name}' (Tipo={obj.Tipo}, Key={obj.KeyRegistro})")
    return obj
