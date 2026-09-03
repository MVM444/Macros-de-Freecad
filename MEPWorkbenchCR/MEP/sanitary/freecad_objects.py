"""
Nombre: freecad_objects.py
Proposito: Objetos parametricos sanitarios experimentales para MEPWorkbenchCR.
Funcionamiento: Define proxies y creadores para tanque septico, FAFA y zanja,
  siguiendo el patron Part::FeaturePython ya usado por HVAC. El modo dry_run
  devuelve especificaciones sin importar ni modificar FreeCAD.
Modificaciones futuras: Agregar puertos tecnicos, helpers documentales 2D,
  cajas de distribucion y validacion real en FreeCAD 1.1.3 antes de exponer GUI.
Version: 0.1.0
Fecha: 2026-08-26

IMPORTANTE:
- No importa FreeCADGui ni Qt.
- No selecciona fabricantes ni dimensiones comerciales automaticamente.
- Los objetos no se consideran integrados hasta validacion en FreeCAD real.
"""


def _spec(component_type, name, properties):
    return {
        "component_type": component_type,
        "name": name,
        "object_type": "Part::FeaturePython",
        "properties": dict(properties),
        "status": "EXPERIMENTAL_NOT_VALIDATED_IN_FREECAD",
    }


def septic_creation_spec(name="MEP_SepticTank", **properties):
    return _spec("SANITARY_SEPTIC_TANK", name, properties)


def fafa_creation_spec(name="MEP_FAFA", **properties):
    return _spec("SANITARY_FAFA", name, properties)


def trench_creation_spec(name="MEP_InfiltrationTrench", **properties):
    return _spec("SANITARY_INFILTRATION_TRENCH", name, properties)


def _add(obj, prop_type, name, group, description):
    if name not in obj.PropertiesList:
        obj.addProperty(prop_type, name, group, description)


def _length_mm(obj, name, default=0.0):
    value = getattr(obj, name, default)
    try:
        return float(value.Value)
    except Exception:
        return float(value)


def _float(obj, name, default=0.0):
    try:
        return float(getattr(obj, name, default))
    except Exception:
        return float(default)


def _set_length(obj, name, value_m):
    if value_m is not None:
        setattr(obj, name, float(value_m) * 1000.0)


def _set_float(obj, name, value):
    if value is not None:
        setattr(obj, name, float(value))


def _set_enum(obj, name, options, selected):
    try:
        setattr(obj, name, list(options))
        if selected in options:
            setattr(obj, name, selected)
    except Exception:
        pass


class _BaseSanitaryProxy:
    component_type = "SANITARY_COMPONENT"

    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        self.ensure_properties(obj)

    def ensure_common(self, obj):
        _add(obj, "App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        _add(obj, "App::PropertyString", "ComponentType", "MEP Sanitary", "Sanitary component class")
        _add(obj, "App::PropertyEnumeration", "DesignStatus", "MEP Sanitary", "Engineering status")
        _add(obj, "App::PropertyString", "SourceMethod", "MEP Sanitary", "Calculation/design source")
        _add(obj, "App::PropertyString", "SourceProject", "MEP Sanitary", "Project traceability")
        _add(obj, "App::PropertyBool", "ShowPlan2D", "MEP Sanitary", "Enable linked/documentary plan representation")
        _add(obj, "App::PropertyLink", "Plan2D", "MEP Sanitary", "Linked helper for plan documentation")
        obj.MEPType = "MEP_SANITARY"
        obj.ComponentType = self.component_type
        _set_enum(obj, "DesignStatus", ["PRELIMINARY", "CALCULATED", "VALIDATED"], "PRELIMINARY")

    def ensure_properties(self, obj):
        self.ensure_common(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy or prop in {"Label", "Label2"}:
            return
        if prop in self.geometry_properties():
            self._busy = True
            try:
                self.build_shape(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            self.ensure_properties(obj)
            self.build_shape(obj)
        finally:
            self._busy = False

    def geometry_properties(self):
        return set()

    def build_shape(self, obj):
        raise NotImplementedError

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        self._busy = False


class SepticTankProxy(_BaseSanitaryProxy):
    component_type = "SANITARY_SEPTIC_TANK"

    def ensure_properties(self, obj):
        self.ensure_common(obj)
        g = "MEP Sanitary - Septic"
        for name, desc in [
            ("Length", "Internal length"),
            ("Width", "Internal width"),
            ("LiquidDepth", "Useful liquid depth"),
            ("Freeboard", "Freeboard"),
            ("WallThickness", "Wall thickness"),
            ("BottomThickness", "Bottom slab thickness"),
            ("CoverThickness", "Top cover thickness"),
            ("InletDiameter", "Inlet pipe diameter"),
            ("OutletDiameter", "Outlet pipe diameter"),
            ("VentDiameter", "Vent diameter"),
        ]:
            _add(obj, "App::PropertyLength", name, g, desc)
        _add(obj, "App::PropertyFloat", "DesignFlowM3Day", g, "Design flow in m3/day")
        _add(obj, "App::PropertyFloat", "TRHDays", g, "Hydraulic retention time in days")
        _add(obj, "App::PropertyInteger", "NumberOfChambers", g, "Number of chambers")
        _add(obj, "App::PropertyFloat", "FirstChamberRatio", g, "First chamber fraction")
        _add(obj, "App::PropertyFloat", "UsefulVolumeM3", g, "Calculated useful volume")
        if _length_mm(obj, "WallThickness") <= 0:
            obj.WallThickness = 100.0
        if _length_mm(obj, "BottomThickness") <= 0:
            obj.BottomThickness = 100.0
        if _length_mm(obj, "CoverThickness") <= 0:
            obj.CoverThickness = 100.0
        if _length_mm(obj, "VentDiameter") <= 0:
            obj.VentDiameter = 38.0
        if int(getattr(obj, "NumberOfChambers", 0) or 0) <= 0:
            obj.NumberOfChambers = 1
        if _float(obj, "FirstChamberRatio", 0.0) <= 0:
            obj.FirstChamberRatio = 0.67

    def geometry_properties(self):
        return {"Length", "Width", "LiquidDepth", "Freeboard", "WallThickness", "BottomThickness", "CoverThickness", "NumberOfChambers", "FirstChamberRatio"}

    def build_shape(self, obj):
        import FreeCAD as App
        import Part
        L = _length_mm(obj, "Length")
        W = _length_mm(obj, "Width")
        Hliq = _length_mm(obj, "LiquidDepth")
        free = _length_mm(obj, "Freeboard")
        wall = _length_mm(obj, "WallThickness")
        bottom = _length_mm(obj, "BottomThickness")
        cover = _length_mm(obj, "CoverThickness")
        if min(L, W, Hliq, wall, bottom, cover) <= 0 or free < 0:
            obj.Shape = Part.Shape()
            return
        H = Hliq + free
        outer_L = L + 2.0 * wall
        outer_W = W + 2.0 * wall
        parts = [Part.makeBox(outer_L, outer_W, bottom, App.Vector(-wall, -wall, 0))]
        z = bottom
        parts.extend([
            Part.makeBox(wall, outer_W, H, App.Vector(-wall, -wall, z)),
            Part.makeBox(wall, outer_W, H, App.Vector(L, -wall, z)),
            Part.makeBox(L, wall, H, App.Vector(0, -wall, z)),
            Part.makeBox(L, wall, H, App.Vector(0, W, z)),
            Part.makeBox(outer_L, outer_W, cover, App.Vector(-wall, -wall, z + H)),
        ])
        chambers = int(getattr(obj, "NumberOfChambers", 1) or 1)
        if chambers > 1:
            ratio = max(0.05, min(0.95, _float(obj, "FirstChamberRatio", 0.67)))
            x = L * ratio
            parts.append(Part.makeBox(wall, W, H, App.Vector(x - wall / 2.0, 0, z)))
        obj.Shape = Part.makeCompound(parts)
        obj.UsefulVolumeM3 = (L * W * Hliq) / 1.0e9

    @staticmethod
    def make_plan_shape(obj):
        import FreeCAD as App
        import Part
        L = _length_mm(obj, "Length")
        W = _length_mm(obj, "Width")
        pts = [App.Vector(0,0,0), App.Vector(L,0,0), App.Vector(L,W,0), App.Vector(0,W,0), App.Vector(0,0,0)]
        shapes = [Part.makePolygon(pts)]
        chambers = int(getattr(obj, "NumberOfChambers", 1) or 1)
        if chambers > 1:
            x = L * max(0.05, min(0.95, _float(obj, "FirstChamberRatio", 0.67)))
            shapes.append(Part.makeLine(App.Vector(x,0,0), App.Vector(x,W,0)))
        return Part.makeCompound(shapes)


class FAFAProxy(_BaseSanitaryProxy):
    component_type = "SANITARY_FAFA"

    def ensure_properties(self, obj):
        self.ensure_common(obj)
        g = "MEP Sanitary - FAFA"
        for name, desc in [
            ("Length", "Internal length"),
            ("Width", "Internal width"),
            ("MediaHeight", "Filter media height"),
            ("BottomDistributionHeight", "Bottom distribution zone"),
            ("Freeboard", "Freeboard/headloss reserve"),
            ("WallThickness", "Wall thickness"),
            ("BottomThickness", "Bottom slab thickness"),
            ("CoverThickness", "Top cover thickness"),
            ("InletDiameter", "Inlet diameter"),
            ("OutletDiameter", "Outlet diameter"),
            ("VentDiameter", "Vent diameter"),
        ]:
            _add(obj, "App::PropertyLength", name, g, desc)
        _add(obj, "App::PropertyFloat", "DesignFlowM3Day", g, "Design flow in m3/day")
        _add(obj, "App::PropertyFloat", "TRHHours", g, "Hydraulic retention time in hours")
        _add(obj, "App::PropertyFloat", "MediaVoidRatio", g, "Filter media void ratio")
        _add(obj, "App::PropertyFloat", "InfluentBODmgL", g, "Post-septic influent BOD")
        _add(obj, "App::PropertyString", "MediaType", g, "Filter media description")
        _add(obj, "App::PropertyFloat", "MediaBedVolumeM3", g, "Geometric media bed volume")
        if _length_mm(obj, "WallThickness") <= 0:
            obj.WallThickness = 100.0
        if _length_mm(obj, "BottomThickness") <= 0:
            obj.BottomThickness = 100.0
        if _length_mm(obj, "CoverThickness") <= 0:
            obj.CoverThickness = 100.0
        if _length_mm(obj, "BottomDistributionHeight") <= 0:
            obj.BottomDistributionHeight = 300.0
        if _length_mm(obj, "Freeboard") <= 0:
            obj.Freeboard = 300.0
        if _float(obj, "TRHHours") <= 0:
            obj.TRHHours = 8.0
        if _float(obj, "MediaVoidRatio") <= 0:
            obj.MediaVoidRatio = 0.70
        if not str(getattr(obj, "MediaType", "") or ""):
            obj.MediaType = "piedra_cuarta_reference"

    def geometry_properties(self):
        return {"Length", "Width", "MediaHeight", "BottomDistributionHeight", "Freeboard", "WallThickness", "BottomThickness", "CoverThickness"}

    def build_shape(self, obj):
        import FreeCAD as App
        import Part
        L = _length_mm(obj, "Length")
        W = _length_mm(obj, "Width")
        media_h = _length_mm(obj, "MediaHeight")
        bottom_zone = _length_mm(obj, "BottomDistributionHeight")
        free = _length_mm(obj, "Freeboard")
        wall = _length_mm(obj, "WallThickness")
        bottom = _length_mm(obj, "BottomThickness")
        cover = _length_mm(obj, "CoverThickness")
        if min(L, W, media_h, wall, bottom, cover) <= 0 or min(bottom_zone, free) < 0:
            obj.Shape = Part.Shape()
            return
        H = bottom_zone + media_h + free
        outer_L = L + 2.0 * wall
        outer_W = W + 2.0 * wall
        z = bottom
        parts = [
            Part.makeBox(outer_L, outer_W, bottom, App.Vector(-wall,-wall,0)),
            Part.makeBox(wall, outer_W, H, App.Vector(-wall,-wall,z)),
            Part.makeBox(wall, outer_W, H, App.Vector(L,-wall,z)),
            Part.makeBox(L, wall, H, App.Vector(0,-wall,z)),
            Part.makeBox(L, wall, H, App.Vector(0,W,z)),
            Part.makeBox(outer_L, outer_W, cover, App.Vector(-wall,-wall,z+H)),
            Part.makeBox(L, W, media_h, App.Vector(0,0,z+bottom_zone)),
        ]
        obj.Shape = Part.makeCompound(parts)
        obj.MediaBedVolumeM3 = (L * W * media_h) / 1.0e9

    @staticmethod
    def make_plan_shape(obj):
        import FreeCAD as App
        import Part
        L = _length_mm(obj, "Length")
        W = _length_mm(obj, "Width")
        return Part.makePolygon([App.Vector(0,0,0), App.Vector(L,0,0), App.Vector(L,W,0), App.Vector(0,W,0), App.Vector(0,0,0)])


class InfiltrationTrenchProxy(_BaseSanitaryProxy):
    component_type = "SANITARY_INFILTRATION_TRENCH"

    def ensure_properties(self, obj):
        self.ensure_common(obj)
        g = "MEP Sanitary - Infiltration"
        for name, desc in [
            ("Length", "Trench length"),
            ("Width", "Trench width"),
            ("GravelDepth", "Gravel layer depth"),
            ("PipeDiameter", "Perforated pipe diameter"),
            ("CenterSpacing", "Center to center spacing"),
        ]:
            _add(obj, "App::PropertyLength", name, g, desc)
        _add(obj, "App::PropertyFloat", "TrenchSlopePercent", g, "Required trench and pipe slope")
        _add(obj, "App::PropertyInteger", "TrenchIndex", g, "Index within infiltration field")
        if _length_mm(obj, "PipeDiameter") <= 0:
            obj.PipeDiameter = 100.0
        obj.TrenchSlopePercent = 0.0

    def geometry_properties(self):
        return {"Length", "Width", "GravelDepth", "PipeDiameter", "Placement"}

    def build_shape(self, obj):
        import FreeCAD as App
        import Part
        L = _length_mm(obj, "Length")
        W = _length_mm(obj, "Width")
        D = _length_mm(obj, "GravelDepth")
        pipe_d = _length_mm(obj, "PipeDiameter")
        if min(L, W, D, pipe_d) <= 0:
            obj.Shape = Part.Shape()
            return
        gravel = Part.makeBox(L, W, D, App.Vector(0, 0, -D))
        pipe_z = -min(D * 0.30, max(pipe_d, 50.0))
        pipe = Part.makeCylinder(pipe_d / 2.0, L, App.Vector(0, W/2.0, pipe_z), App.Vector(1,0,0))
        obj.Shape = Part.makeCompound([gravel, pipe])
        obj.TrenchSlopePercent = 0.0

    @staticmethod
    def make_plan_shape(obj):
        import FreeCAD as App
        import Part
        L = _length_mm(obj, "Length")
        W = _length_mm(obj, "Width")
        return Part.makePolygon([App.Vector(0,0,0), App.Vector(L,0,0), App.Vector(L,W,0), App.Vector(0,W,0), App.Vector(0,0,0)])


def create_septic_tank(doc, name="MEP_SepticTank", dry_run=True, **properties):
    spec = septic_creation_spec(name=name, **properties)
    if dry_run:
        return spec
    if doc is None:
        raise ValueError("Se requiere documento FreeCAD")
    obj = doc.getObject(name) or doc.addObject("Part::FeaturePython", name)
    SepticTankProxy(obj)
    for key, value in properties.items():
        if key in {"Length", "Width", "LiquidDepth", "Freeboard", "WallThickness", "BottomThickness", "CoverThickness", "InletDiameter", "OutletDiameter", "VentDiameter"}:
            _set_length(obj, key, value)
        elif key in {"DesignFlowM3Day", "TRHDays", "FirstChamberRatio"}:
            _set_float(obj, key, value)
        elif key == "NumberOfChambers" and value is not None:
            obj.NumberOfChambers = int(value)
        elif key in obj.PropertiesList and value is not None:
            setattr(obj, key, value)
    obj.Proxy.execute(obj)
    return obj


def create_fafa(doc, name="MEP_FAFA", dry_run=True, **properties):
    spec = fafa_creation_spec(name=name, **properties)
    if dry_run:
        return spec
    if doc is None:
        raise ValueError("Se requiere documento FreeCAD")
    obj = doc.getObject(name) or doc.addObject("Part::FeaturePython", name)
    FAFAProxy(obj)
    for key, value in properties.items():
        if key in {"Length", "Width", "MediaHeight", "BottomDistributionHeight", "Freeboard", "WallThickness", "BottomThickness", "CoverThickness", "InletDiameter", "OutletDiameter", "VentDiameter"}:
            _set_length(obj, key, value)
        elif key in {"DesignFlowM3Day", "TRHHours", "MediaVoidRatio", "InfluentBODmgL"}:
            _set_float(obj, key, value)
        elif key in obj.PropertiesList and value is not None:
            setattr(obj, key, value)
    obj.Proxy.execute(obj)
    return obj


def create_infiltration_trench(doc, name="MEP_InfiltrationTrench", dry_run=True, **properties):
    spec = trench_creation_spec(name=name, **properties)
    if dry_run:
        return spec
    if doc is None:
        raise ValueError("Se requiere documento FreeCAD")
    obj = doc.getObject(name) or doc.addObject("Part::FeaturePython", name)
    InfiltrationTrenchProxy(obj)
    for key, value in properties.items():
        if key in {"Length", "Width", "GravelDepth", "PipeDiameter", "CenterSpacing"}:
            _set_length(obj, key, value)
        elif key == "TrenchIndex" and value is not None:
            obj.TrenchIndex = int(value)
        elif key in obj.PropertiesList and value is not None:
            setattr(obj, key, value)
    obj.Proxy.execute(obj)
    return obj
