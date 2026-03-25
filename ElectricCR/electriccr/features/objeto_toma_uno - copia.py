# -*- coding: utf-8 -*-
"""
electriccr.features.objeto_toma_uno
Descripcion (sin acentos):
  Objeto Toma en un solo nodo (Part::FeaturePython) sin hijos link.
  Construye su Shape tomando las Shapes de prototipos por Label dentro de
  electrico/_lib: "ProtoToma2D" y "ProtoToma3D" (configurable).

  Propiedades clave:
    - Categoria: Pared/Cielo/Piso (MVP: Pared)
    - Tipo: Toma (extensible)
    - ModoVisual: Ambos/Solo2D/Solo3D
    - Giro: grados sobre Z local
    - OffsetX / OffsetY: mm en XY local
    - AlturaRel: mm solo aplicado al 3D (Z local)
    - OrientacionPared: Vertical(0), Horizontal(+90), Auto (MVP: 0)
    - LabelProto2D / LabelProto3D: labels de prototipos en _lib

  ViewProvider:
    Define display modes validos ["Shaded","Wireframe","FlatLines"]
    y fija "Shaded" como default para evitar errores de enumeracion
    ('... is not part of the enumeration ...').
    Ref: getDisplayModes / getDefaultDisplayMode / setDisplayMode. 
"""

import math, re
from datetime import datetime
import FreeCAD as App
from pathlib import Path
import importlib.util
from importlib.machinery import SourceFileLoader

GUI_UP = False
try:
    import FreeCADGui as Gui
    GUI_UP = True
except Exception:
    GUI_UP = False

try:
    import Part
except Exception:
    Part = None

SCHEMA_VERSION = "1.0.0"

def _ts():
    try:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "NA"

def log_i(msg): App.Console.PrintMessage(f"[{_ts()}][TOMA1][INFO] {msg}\n")
def log_w(msg): App.Console.PrintWarning(f"[{_ts()}][TOMA1][WARN] {msg}\n")
def log_e(msg): App.Console.PrintError(f"[{_ts()}][TOMA1][ERROR] {msg}\n")

_ELECTRIC_PRINCIPAL_MOD = None
_RESOURCES_DIRS = None
_PROTO_ENSURE_FAILURES = set()



def _scalar(val, default=0.0):
    try:
        if hasattr(val, 'Value'):
            return float(val.Value)
        return float(val)
    except Exception:
        try:
            return float(val)
        except Exception:
            return float(default)




def _candidate_electric_principal_files(max_levels=8):
    candidates = []
    seen = set()
    try:
        base = Path(__file__).resolve().parent
    except Exception:
        base = None
    cur = base
    for _ in range(max_levels):
        if cur is None:
            break
        if cur in seen:
            break
        seen.add(cur)
        cand = cur / "Electric_Principal.FCMacro"
        if cand.exists():
            candidates.append(cand)
        cur = cur.parent
    try:
        macro_dir = Path(App.getUserAppDataDir()) / "Macro"
        cand = macro_dir / "Electric_Principal.FCMacro"
        if cand.exists():
            candidates.append(cand)
    except Exception:
        pass
    out = []
    seen_paths = set()
    for c in candidates:
        try:
            resolved = c.resolve()
        except Exception:
            resolved = c
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        out.append(resolved)
    return out


def _candidate_resources_dirs(max_levels=8):
    dirs = []
    seen = set()
    try:
        base = Path(__file__).resolve().parent
    except Exception:
        base = None
    cur = base
    for _ in range(max_levels):
        if cur is None:
            break
        if cur in seen:
            break
        seen.add(cur)
        res = cur / "Resources"
        if res.is_dir():
            dirs.append(res)
            sub = res / "prototypes"
            if sub.is_dir():
                dirs.append(sub)
        cur = cur.parent
    try:
        base_macro = Path(App.getUserAppDataDir()) / "Macro" / "Resources"
        if base_macro.is_dir():
            dirs.append(base_macro)
            sub = base_macro / "prototypes"
            if sub.is_dir():
                dirs.append(sub)
    except Exception:
        pass
    out = []
    seen_paths = set()
    for d in dirs:
        try:
            resolved = d.resolve()
        except Exception:
            resolved = d
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        out.append(resolved)
    return out


def _resource_dirs_with_protos():
    global _RESOURCES_DIRS
    if _RESOURCES_DIRS is None:
        bases = list(_candidate_resources_dirs())
        extra = []
        for base in bases:
            for cand in (base / "Toma_2d.step", base / "Toma_3d.step", base / "switch_simple.step", base / "switch_simple.svg"):
                if cand.is_file():
                    extra.append(cand.parent)
        merged = []
        seen = set()
        for entry in bases + extra:
            try:
                resolved = entry.resolve()
            except Exception:
                resolved = entry
            if resolved in seen:
                continue
            seen.add(resolved)
            merged.append(resolved)
        _RESOURCES_DIRS = merged
    return _RESOURCES_DIRS


def _load_electric_principal_module():
    global _ELECTRIC_PRINCIPAL_MOD
    if _ELECTRIC_PRINCIPAL_MOD is not None:
        return _ELECTRIC_PRINCIPAL_MOD
    for cand in _candidate_electric_principal_files():
        try:
            loader = SourceFileLoader("electric_principal_boot", str(cand))
            spec = importlib.util.spec_from_loader(loader.name, loader)
            if spec is None:
                continue
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
            _ELECTRIC_PRINCIPAL_MOD = module
            log_i(f"Electric_Principal cargado desde: {cand}")
            break
        except Exception as ex:
            log_w(f"No se pudo cargar Electric_Principal en {cand}: {ex}")
    return _ELECTRIC_PRINCIPAL_MOD


def _ensure_prototypes_for_labels(doc, label2, label3, file2=None, file3=None):
    if doc is None:
        return
    proto2d = find_by_label_in_lib(doc, label2) if label2 else None
    proto3d = find_by_label_in_lib(doc, label3) if label3 else None
    if proto2d and proto3d:
        return

    def _resolve_resource(name, prefer_kind=None):
        if not name:
            return None
        try:
            candidate = Path(name)
            if candidate.is_file():
                return candidate
        except Exception:
            pass
        prefer = str(prefer_kind or "").lower()
        prefer_dirs = []
        if prefer == '3d':
            prefer_dirs.extend([
                Path('prototypes/3d'),
                Path('Resources/prototypes/3d'),
                Path('3d'),
                Path('Resources/3d'),
            ])
        elif prefer == '2d':
            prefer_dirs.extend([
                Path('prototypes/2d'),
                Path('Resources/prototypes/2d'),
                Path('2d'),
                Path('Resources/2d'),
            ])
        common_dirs = [
            Path('.'),
            Path('prototypes'),
            Path('prototypes/2d'),
            Path('prototypes/3d'),
            Path('Resources'),
            Path('Resources/prototypes'),
            Path('Resources/prototypes/2d'),
            Path('Resources/prototypes/3d'),
        ]
        subdirs = []
        for entry in prefer_dirs + common_dirs:
            if entry not in subdirs:
                subdirs.append(entry)
        for base in _resource_dirs_with_protos():
            for sub in subdirs:
                cand = base / sub / name
                if cand.is_file():
                    return cand
            try:
                stem = Path(name).name
            except Exception:
                stem = None
            if stem:
                for sub in subdirs:
                    cand2 = base / sub / stem
                    if cand2.is_file():
                        return cand2
        return None
        try:
            candidate = Path(name)
            if candidate.is_file():
                return candidate
        except Exception:
            pass
        subdirs = [
            Path('.'), Path('prototypes'), Path('prototypes/2d'), Path('prototypes/3d'),
            Path('Resources'), Path('Resources/prototypes'), Path('Resources/prototypes/2d'), Path('Resources/prototypes/3d')
        ]
        for base in _resource_dirs_with_protos():
            for sub in subdirs:
                cand = base / sub / name
                if cand.is_file():
                    return cand
            try:
                stem = Path(name).name
            except Exception:
                stem = None
            if stem:
                for sub in subdirs:
                    cand2 = base / sub / stem
                    if cand2.is_file():
                        return cand2
        return None

    def _build_proto(label, filepath, expect_2d):
        import Part
        path_obj = _resolve_resource(filepath, '2d' if expect_2d else '3d')
        if not path_obj:
            log_w(f"Recurso no encontrado: {filepath}")
            return None
        created = []
        shapes = []
        suffix = path_obj.suffix.lower()
        if suffix in {'.step', '.stp', '.iges', '.igs'}:
            shape = _read_step_shape(str(path_obj))
            if shape is not None:
                shapes = (_collect_shapes_for_2d_from_shape(shape) if expect_2d else _collect_shapes_for_3d_from_shape(shape))
        if not shapes:
            created = _insert_file_return_created(str(path_obj), doc)
            shapes = (_collect_shapes_for_2d(created) if expect_2d else _collect_shapes_for_3d(created))
        if not shapes:
            log_w(f"No se pudo generar shape desde {path_obj}")
            if created:
                _delete_created(doc, created)
            return None
        existing = find_by_label_in_lib(doc, label) if label else None
        if existing:
            try:
                doc.removeObject(existing.Name)
            except Exception:
                pass
        feature = _make_feature_from_shapes(doc, shapes, label or path_obj.stem)
        _, g_lib, _ = ensure_groups(doc)
        g_lib.addObject(feature)
        if GUI_UP and hasattr(feature, 'ViewObject'):
            try:
                feature.ViewObject.ShowInTree = False
                feature.Visibility = False
            except Exception:
                pass
        if created:
            _delete_created(doc, created)
        return feature

    custom = bool(file2 or file3)
    if custom:
        if file2 and not proto2d:
            proto2d = _build_proto(label2, file2, True)
        if file3 and not proto3d:
            proto3d = _build_proto(label3, file3, False)
        if proto2d and proto3d:
            return

    proto2d = find_by_label_in_lib(doc, label2) if label2 else proto2d
    proto3d = find_by_label_in_lib(doc, label3) if label3 else proto3d
    if proto2d and proto3d:
        return

    key = (getattr(doc, 'Name', None), label2, label3, file2, file3)
    if key in _PROTO_ENSURE_FAILURES:
        return

    module = _load_electric_principal_module()
    if module is None:
        log_w("No se localizo Electric_Principal.FCMacro para generar prototipos")
        _PROTO_ENSURE_FAILURES.add(key)
        return
    ensure_fn = getattr(module, 'ensure_prototypes_from_resources', None)
    if ensure_fn is None:
        log_w("Electric_Principal no expone ensure_prototypes_from_resources")
        _PROTO_ENSURE_FAILURES.add(key)
        return
    dirs = _resource_dirs_with_protos()
    if not dirs:
        log_w("No se encontraron carpetas Resources candidatas")
        _PROTO_ENSURE_FAILURES.add(key)
        return
    for rdir in dirs:
        try:
            ensure_fn(doc, str(rdir))
            proto2d = find_by_label_in_lib(doc, label2) if label2 else find_by_label_in_lib(doc, 'ProtoToma2D')
            proto3d = find_by_label_in_lib(doc, label3) if label3 else find_by_label_in_lib(doc, 'ProtoToma3D')
            if proto2d and proto3d:
                return
        except Exception as ex:
            log_w(f"ensure_prototypes_from_resources fallo con {rdir}: {ex}")
    _PROTO_ENSURE_FAILURES.add(key)


# -------------------------------------------------------------------
# ViewProvider: fija modos validos y default para evitar ValueError
# Docs/ejemplos sobre getDisplayModes/setDisplayMode en FreeCAD: 
# - FeaturePython.ViewProviderBox setDisplayMode + getDisplayModes
# - Ejemplos de scripted objects con VP
# -------------------------------------------------------------------
class VP_TomaUno(object):
    def __init__(self, vobj):
        vobj.Proxy = self
        # valores de estetica por defecto (opcionales)
        try:
            vobj.LineWidth = 1.0
            vobj.PointSize = 3.0
        except Exception:
            pass

    # lista de modos admitidos por este VP
    def getDisplayModes(self, vobj):
        # solo exponemos el modo relevante para evitar duplicados
        return ["Flat Lines"]

    # modo default cuando se crea el objeto
    def getDefaultDisplayMode(self):
        return "Flat Lines"

    # normalizamos a la etiqueta esperada
    def setDisplayMode(self, mode):
        if mode in ("FlatLines", "Flat Lines"):
            return "Flat Lines"
        return "Flat Lines"

    def attach(self, vobj):
        try:
            vobj.DisplayModes = ("Flat Lines",)
        except Exception:
            pass
        return

    # metodos opcionales de VP no requeridos para este MVP:
    def updateData(self, fp, prop):
        return
    def onChanged(self, vp, prop):
        return
    def __getstate__(self):
        return None
    def __setstate__(self, s):
        return

# -------------------------------------------------------------------
# utilidades de grupos y busqueda por Label en _lib
# -------------------------------------------------------------------
def ensure_groups(doc, instances_group_label="Tomacorrientes"):
    g_elec = doc.getObject("electrico")
    if not g_elec:
        g_elec = doc.addObject("App::DocumentObjectGroup", "electrico")
        log_i("created group electrico")
    g_lib = doc.getObject("_lib")
    if not g_lib:
        g_lib = doc.addObject("App::DocumentObjectGroup", "_lib")
        g_elec.addObject(g_lib)
        log_i("created subgroup _lib")
    g_inst = doc.getObject(instances_group_label)
    if not g_inst:
        g_inst = doc.addObject("App::DocumentObjectGroup", instances_group_label)
        g_elec.addObject(g_inst)
        log_i(f"created subgroup {instances_group_label}")
    return g_elec, g_lib, g_inst

def _iter_group_recursive(root):
    if not root: 
        return
    yield root
    ch = []
    try:
        ch = list(getattr(root, "Group", []) or [])
    except Exception:
        ch = []
    for c in ch:
        for it in _iter_group_recursive(c):
            yield it

def find_by_label_in_lib(doc, want_label):
    _, g_lib, _ = ensure_groups(doc)
    # match exacto
    for o in _iter_group_recursive(g_lib):
        try:
            if getattr(o, "Label", "") == want_label:
                return o
        except Exception:
            pass
    # fallback: contiene
    for o in _iter_group_recursive(g_lib):
        try:
            if want_label in getattr(o, "Label", ""):
                return o
        except Exception:
            pass
    return None

# -------------------------------------------------------------------
# helpers de insercion
# -------------------------------------------------------------------
def _selection_info():
    if not GUI_UP:
        return (None, None, None, None, None, None)
    sel = Gui.Selection.getSelectionEx()
    if not sel:
        return (None, None, None, None, None, None)
    s0 = sel[0]
    sub = s0.SubObjects
    if not sub:
        return (s0.Object, None, None, None, None, None)
    so = sub[0]
    try:
        import Part as _P
    except Exception:
        return (s0.Object, so, "Other", None, None, None)
    if isinstance(so, _P.Face):
        u0, v0, u1, v1 = so.ParameterRange
        u = u0 + (u1 - u0) * 0.5
        v = v0 + (v1 - v0) * 0.5
        pnt = so.valueAt(u, v)
        nrm = so.normalAt(u, v)
        return (s0.Object, so, "Face", pnt, None, nrm)
    if isinstance(so, _P.Edge):
        umin, umax = so.ParameterRange
        umid = (umin + umax) * 0.5
        pnt = so.valueAt(umid)
        try:
            tng = so.tangentAt(umid)
        except Exception:
            tng = None
        return (s0.Object, so, "Edge", pnt, tng, None)
    return (s0.Object, so, "Other", None, None, None)

def _yaw_from_tangent(tng):
    if not tng:
        return 0.0
    v = App.Vector(tng.x, tng.y, 0)
    if v.Length == 0:
        return 0.0
    return math.degrees(math.atan2(v.y, v.x))

# -------------------------------------------------------------------
# Proxy principal del objeto
# -------------------------------------------------------------------
class TomaUnoProxy(object):
    def __init__(self):
        self.initialized = False
        self._executing = False

    def __getstate__(self):
        return {"cls": "electriccr.features.objeto_toma_uno.TomaUnoProxy"}

    def __setstate__(self, state):
        self.initialized = False
        self._executing = False

    def onDocumentRestored(self, obj):
        # tras reabrir archivo, reactivar
        self.initialized = True
        try:
            obj.touch()
        except Exception:
            pass

    def attach(self, obj):
        # core
        obj.addProperty("App::PropertyEnumeration", "Categoria", "Core", "").Categoria = ["Pared", "Cielo", "Piso"]
        obj.addProperty("App::PropertyEnumeration", "Tipo", "Core", "").Tipo = ["Toma", "Apagador", "Luminaria", "Sensor", "Rociador", "Altavoz", "Camara"]
        obj.addProperty("App::PropertyEnumeration", "ModoVisual", "Core", "").ModoVisual = ["Ambos", "Solo2D", "Solo3D"]
        obj.addProperty("App::PropertyAngle", "Giro", "Core", "").Giro = 0.0
        obj.addProperty("App::PropertyDistance", "OffsetX", "Core", "").OffsetX = 0.0
        obj.addProperty("App::PropertyDistance", "OffsetY", "Core", "").OffsetY = 0.0
        obj.addProperty("App::PropertyDistance", "AlturaRel", "Core", "").AlturaRel = 0.0

        # pared
        obj.addProperty("App::PropertyEnumeration", "OrientacionPared", "Pared", "").OrientacionPared = ["Vertical", "Horizontal", "Auto"]
        obj.addProperty("App::PropertyBool", "Flip", "Pared", "").Flip = False

        # meta
        obj.addProperty("App::PropertyString", "EtiquetaPlano", "Meta", "")
        obj.addProperty("App::PropertyString", "CircuitoID", "Meta", "")
        obj.addProperty("App::PropertyString", "UUID", "Meta", "")
        obj.addProperty("App::PropertyString", "SchemaVersion", "Meta", "").SchemaVersion = SCHEMA_VERSION

        # internos
        obj.addProperty("App::PropertyString", "LabelProto2D", "Internal", "").LabelProto2D = "ProtoToma2D"
        obj.addProperty("App::PropertyString", "LabelProto3D", "Internal", "").LabelProto3D = "ProtoToma3D"
        obj.addProperty("App::PropertyString", "RecursoProto2D", "Internal", "")
        obj.addProperty("App::PropertyString", "RecursoProto3D", "Internal", "")
        obj.addProperty("App::PropertyString", "KeyRegistro", "Internal", "")
        obj.addProperty("App::PropertyString", "IfcType", "Internal", "")

        self.initialized = True
        log_i(f"attach properties on {obj.Name}")

        # registrar view provider y mode default solo si GUI esta arriba
        if GUI_UP:
            try:
                vp = VP_TomaUno(obj.ViewObject)
                # asegurar un modo valido (de la lista del VP)
                obj.ViewObject.DisplayMode = vp.getDefaultDisplayMode()
                if "Flat Lines" in getattr(obj.ViewObject, "DisplayModes", []):
                    obj.ViewObject.DisplayMode = "Flat Lines"
            except Exception as ex:
                log_w(f"no se pudo fijar VP/mode: {ex}")

    # construir Shape compuesta segun ModoVisual
    def _build_shape(self, obj):
        if Part is None:
            log_e("Part module not available")
            return None

        doc = obj.Document
        _ensure_prototypes_for_labels(doc, obj.LabelProto2D, obj.LabelProto3D, getattr(obj, 'RecursoProto2D', ''), getattr(obj, 'RecursoProto3D', ''))
        proto2d = find_by_label_in_lib(doc, obj.LabelProto2D)
        proto3d = find_by_label_in_lib(doc, obj.LabelProto3D)

        s2 = proto2d.Shape.copy() if (proto2d and hasattr(proto2d, "Shape")) else None
        s3 = proto3d.Shape.copy() if (proto3d and hasattr(proto3d, "Shape")) else None

        if s2 is None:
            log_w("Proto 2D not found or has no Shape")
        if s3 is None:
            log_w("Proto 3D not found or has no Shape")

        offset_local = App.Vector(_scalar(getattr(obj, 'OffsetX', 0.0)), _scalar(getattr(obj, 'OffsetY', 0.0)), 0.0)

        orient = 'Vertical'
        try:
            orient = getattr(obj, 'OrientacionPared', 'Vertical') or 'Vertical'
        except Exception:
            orient = 'Vertical'

        delta_z = 90.0 if orient == 'Horizontal' else 0.0
        yaw_local = _scalar(getattr(obj, 'Giro', 0.0)) + delta_z
        rot_z = App.Rotation(App.Vector(0, 0, 1), yaw_local)

        if s2:
            try:
                s2.Placement = App.Placement(offset_local, rot_z)
            except Exception:
                pass

        altitude_local = rot_z.multVec(App.Vector(0, 0, _scalar(getattr(obj, 'AlturaRel', 0.0))))
        rot_pitch = App.Rotation(App.Vector(0, 1, 0), 90.0) if orient == 'Horizontal' else App.Rotation()
        rot_3d = rot_z.multiply(rot_pitch) if orient == 'Horizontal' else rot_z
        if s3:
            try:
                s3.Placement = App.Placement(offset_local + altitude_local, rot_3d)
            except Exception:
                pass

        pl2_local = App.Placement(offset_local, rot_z)
        pl3_local = App.Placement(offset_local + altitude_local, rot_3d)

        shapes = []
        if obj.ModoVisual in ("Ambos", "Solo2D") and s2:
            try:
                s2.Placement = pl2_local
                shapes.append(s2)
            except Exception as ex:
                log_w(f"s2 placement failed: {ex}")
        if obj.ModoVisual in ("Ambos", "Solo3D") and s3:
            try:
                s3.Placement = pl3_local
                shapes.append(s3)
            except Exception as ex:
                log_w(f"s3 placement failed: {ex}")

        if not shapes:
            return None
        if len(shapes) == 1:
            return shapes[0]
        try:
            return Part.Compound(shapes)
        except Exception as ex:
            log_w(f"compound failed: {ex}")
            return shapes[0]

    def onChanged(self, obj, prop):
        if not self.initialized:
            return
        if prop in ("ModoVisual", "OffsetX", "OffsetY", "AlturaRel", "Giro", "Placement", "OrientacionPared", "LabelProto2D", "LabelProto3D"):
            try:
                obj.touch()
            except Exception:
                pass

    def execute(self, obj):
        if self._executing:
            return
        self._executing = True
        try:
            shp = self._build_shape(obj)
            if shp is None:
                try:
                    obj.Shape = Part.Shape()
                except Exception:
                    pass
            else:
                obj.Shape = shp
        finally:
            self._executing = False

# -------------------------------------------------------------------
# helpers de nombre y creacion
# -------------------------------------------------------------------
def _next_name(doc, prefix="Toma_", width=3):
    pat = re.compile(r"^" + re.escape(prefix) + r"(\d{" + str(width) + r"})$")
    maxn = 0
    for o in doc.Objects:
        m = pat.match(o.Name)
        if m:
            try:
                n = int(m.group(1))
                if n > maxn:
                    maxn = n
            except Exception:
                pass
    return f"{prefix}{maxn + 1:0{width}d}"

def crear_toma_uno(
    doc=None,
    name_hint=None,
    instances_group_label="Tomacorrientes",
    label_2d="ProtoToma2D",
    label_3d="ProtoToma3D",
    proto2d_source=None,
    proto3d_source=None,
    name_prefix=None,
    tipo=None,
    categoria=None,
    key_registro=None,
    ifc_type=None,
):
    doc = doc or App.ActiveDocument or App.newDocument("Electrico_Demo")
    _, _, g_inst = ensure_groups(doc, instances_group_label=instances_group_label)
    _ensure_prototypes_for_labels(doc, label_2d, label_3d, proto2d_source, proto3d_source)

    prefix = name_prefix or "Toma_"
    if name_hint:
        name = name_hint
    else:
        name = _next_name(doc, prefix=prefix)
    obj = doc.addObject("Part::FeaturePython", name)
    proxy = TomaUnoProxy()
    proxy.attach(obj)
    obj.Proxy = proxy

    # defaults
    obj.Categoria = categoria or "Pared"
    obj.Tipo = tipo or "Toma"
    obj.ModoVisual = "Ambos"
    obj.LabelProto2D = label_2d
    obj.LabelProto3D = label_3d
    obj.RecursoProto2D = proto2d_source or ""
    obj.RecursoProto3D = proto3d_source or ""
    obj.KeyRegistro = key_registro or ""
    obj.IfcType = ifc_type or ""
    try:
        import uuid
        obj.UUID = str(uuid.uuid4())
    except Exception:
        obj.UUID = ""

    # seleccion opcional
    sel_obj, sub, kind, pnt, tng, nrm = _selection_info()
    base = App.Vector(0, 0, 0)
    yaw = 0.0
    if kind == "Face" and pnt is not None:
        base = pnt
        yaw = 0.0
        log_i("placement from face center")
    elif kind == "Edge" and pnt is not None:
        base = pnt
        yaw = _yaw_from_tangent(tng)
        log_i(f"placement from edge midpoint yaw={yaw:.2f}")
    else:
        log_w("no valid selection; using origin")

    # auto: si es borde podria sumarse 90, MVP conservador 0
    delta_auto = 0.0
    rot = App.Rotation(App.Vector(0, 0, 1), yaw + delta_auto)
    obj.Placement = App.Placement(base, rot)

    # ubicar en grupo
    g_inst.addObject(obj)

    # recompute
    obj.touch()
    doc.recompute()
    log_i(f"created single-node Toma '{obj.Name}'")
    return obj


def _insert_file_return_created(path, doc):
    try:
        import ImportGui
    except Exception as ex:
        log_e(f"ImportGui not available: {ex}")
        return []
    before = {o.Name for o in doc.Objects}
    try:
        ImportGui.insert(path, doc.Name)
    except Exception as ex:
        log_e(f"failed to insert resource: {path} -> {ex}")
        return []
    after = {o.Name for o in doc.Objects}
    created_names = list(after - before)
    return [doc.getObject(name) for name in created_names if doc.getObject(name)]


def _collect_shapes_for_2d(objs):
    shapes = []
    for obj in objs or []:
        try:
            sh = getattr(obj, 'Shape', None)
            if not sh:
                continue
            faces = list(getattr(sh, 'Faces', []) or [])
            edges = list(getattr(sh, 'Edges', []) or [])
            if faces:
                shapes.extend(faces)
            elif edges:
                shapes.extend(edges)
        except Exception:
            continue
    return shapes


def _collect_shapes_for_3d(objs):
    solids = []
    faces = []
    for obj in objs or []:
        try:
            sh = getattr(obj, 'Shape', None)
            if not sh:
                continue
            sols = list(getattr(sh, 'Solids', []) or [])
            fcs = list(getattr(sh, 'Faces', []) or [])
            if sols:
                solids.extend(sols)
            elif fcs:
                faces.extend(fcs)
        except Exception:
            continue
    return solids or faces


def _collect_shapes_for_2d_from_shape(shape):
    if shape is None:
        return []
    try:
        faces = list(getattr(shape, 'Faces', []) or [])
    except Exception:
        faces = []
    if faces:
        return faces
    try:
        edges = list(getattr(shape, 'Edges', []) or [])
    except Exception:
        edges = []
    if edges:
        return edges
    return [shape]


def _collect_shapes_for_3d_from_shape(shape):
    if shape is None:
        return []
    try:
        solids = list(getattr(shape, 'Solids', []) or [])
    except Exception:
        solids = []
    if solids:
        return solids
    try:
        faces = list(getattr(shape, 'Faces', []) or [])
    except Exception:
        faces = []
    if faces:
        return faces
    return []


def _read_step_shape(path):
    if Part is None:
        return None
    try:
        return Part.read(path)
    except Exception:
        return None


def _make_feature_from_shapes(doc, shapes, name_label):
    if Part is None or not shapes:
        return None
    try:
        compound = Part.makeCompound(shapes)
    except Exception:
        compound = shapes[0]
    feat = doc.addObject('Part::Feature', name_label)
    feat.Shape = compound
    feat.Label = name_label
    return feat


def _delete_created(doc, created):
    for obj in created or []:
        try:
            doc.removeObject(obj.Name)
        except Exception:
            pass



