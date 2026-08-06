"""Native ArchGrid inference helpers for FacilArquitecturaWB.

Descripcion: crea una cuadricula ArchGrid ajustada a alineamientos reales del edificio.
Fecha: 2026-07-25
Version: 0.4.9
"""

from __future__ import annotations

import math

import FreeCAD

from .axis_utils import _axis_angle_difference, _segments_from_sketch, axis_family_specs_from_segments
from .command_errors import UserFacingError
from .project_structure import msg, set_prop

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None

try:
    import Part
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Part = None

try:
    import Sketcher
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Sketcher = None


GENERATED_BY = "FA_CreateBuildingGrid"
DEFAULT_CLUSTER_TOLERANCE_MM = 80.0
DEFAULT_WALL_SUPPORT_MM = 5000.0
DEFAULT_MAX_LINES_PER_DIRECTION = 8
ORIENTATION_TOLERANCE_DEG = 10.0


def collect_building_grid_sources(doc, selection=None):
    """Collect measured wall and opening centerline sketches from the document."""
    all_sources = {"walls": [], "doors": [], "windows": []}
    for obj in list(getattr(doc, "Objects", []) or []):
        kind = _source_kind(obj)
        if kind in all_sources and _is_usable_source(obj):
            all_sources[kind].append(obj)

    closed_walls = [
        obj
        for obj in all_sources["walls"]
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == "FA_CloseWallSketch"
    ]
    measured_walls = [obj for obj in all_sources["walls"] if _wall_has_measured_thickness(obj)]
    if closed_walls:
        all_sources["walls"] = closed_walls
    elif measured_walls:
        all_sources["walls"] = measured_walls

    selected = {"walls": [], "doors": [], "windows": []}
    for obj in _walk_selection(selection):
        kind = _source_kind(obj)
        if kind in selected and obj in all_sources[kind] and obj not in selected[kind]:
            selected[kind].append(obj)

    result = {kind: selected[kind] or all_sources[kind] for kind in all_sources}
    if not result["walls"]:
        raise UserFacingError(
            "No se encontro un Sketch_Centros de paredes con espesor detectado. "
            "Cree primero los centros de los muros."
        )
    return result


def infer_building_grid(
    wall_segments,
    door_segments=None,
    window_segments=None,
    cluster_tolerance=DEFAULT_CLUSTER_TOLERANCE_MM,
    wall_min_support=DEFAULT_WALL_SUPPORT_MM,
    max_lines_per_direction=DEFAULT_MAX_LINES_PER_DIRECTION,
):
    """Infer one orthogonal ArchGrid from supported wall centre alignments."""
    walls = _segments_6d(wall_segments)
    doors = _segments_6d(door_segments)
    windows = _segments_6d(window_segments)
    if len(walls) < 2:
        raise UserFacingError("Se requieren al menos dos lineas de muro para inferir una cuadricula.")

    base_specs, omitted_direction_count = axis_family_specs_from_segments(
        walls,
        position_tolerance=float(cluster_tolerance),
        extension=0.0,
    )
    x_family = max(base_specs, key=lambda spec: abs(float(spec["direction"][0])))
    y_family = base_specs[1] if base_specs[0] is x_family else base_specs[0]
    u = _positive_direction(x_family["direction"])
    v = (-u[1], u[0])
    y_direction = _positive_direction(y_family["direction"])
    perpendicular_error = abs(math.degrees(_axis_angle_difference(_angle(u), _angle(y_direction))) - 90.0)
    if perpendicular_error > ORIENTATION_TOLERANCE_DEG:
        raise UserFacingError(
            "ArchGrid requiere dos direcciones casi perpendiculares; la diferencia medida se aparta %.1f grados."
            % perpendicular_error
        )

    wall_x_records = []
    wall_y_records = []
    for segment in walls:
        family = _segment_family(segment, u, v)
        if family is None:
            continue
        midpoint = _midpoint(segment)
        # A wall parallel to local Y defines a vertical grid line (X position),
        # and a wall parallel to local X defines a horizontal line (Y position).
        if family == "y":
            wall_x_records.append(
                {"position": _dot(midpoint, u), "length": _length(segment), "kind": "walls"}
            )
        else:
            wall_y_records.append(
                {"position": _dot(midpoint, v), "length": _length(segment), "kind": "walls"}
            )

    wall_x = _cluster_records(wall_x_records, float(cluster_tolerance))
    wall_y = _cluster_records(wall_y_records, float(cluster_tolerance))
    selected_x = _select_wall_lines(wall_x, float(wall_min_support), int(max_lines_per_direction))
    selected_y = _select_wall_lines(wall_y, float(wall_min_support), int(max_lines_per_direction))
    if len(selected_x) < 2 or len(selected_y) < 2:
        raise UserFacingError("No se obtuvieron al menos dos limites de pared en cada direccion.")

    # Door and window centerlines inform the earlier wall-reconstruction stage,
    # but they never introduce ArchGrid divisions of their own. Every grid line
    # below is therefore supported by a real wall centre alignment.
    x_positions = [item["position"] for item in selected_x]
    y_positions = [item["position"] for item in selected_y]
    extent_x, extent_y = _local_segment_extents(walls, u, v)
    x_positions, x_boundary_count = _fit_grid_boundaries_to_extents(
        x_positions,
        extent_x,
        float(cluster_tolerance),
    )
    y_positions, y_boundary_count = _fit_grid_boundaries_to_extents(
        y_positions,
        extent_y,
        float(cluster_tolerance),
    )
    if len(x_positions) < 2 or len(y_positions) < 2:
        raise UserFacingError("La informacion disponible no forma una cuadricula rectangular util.")

    x_sizes = [x_positions[index] - x_positions[index - 1] for index in range(1, len(x_positions))]
    y_descending = list(reversed(y_positions))
    y_sizes = [y_descending[index - 1] - y_descending[index] for index in range(1, len(y_descending))]
    origin = (
        u[0] * x_positions[0] + v[0] * y_positions[-1],
        u[1] * x_positions[0] + v[1] * y_positions[-1],
        _average_z(walls),
    )
    return {
        "u": u,
        "v": v,
        "rotation_deg": math.degrees(_angle(u)),
        "origin": origin,
        "x_positions": x_positions,
        "y_positions": y_positions,
        "column_sizes": x_sizes,
        "row_sizes": y_sizes,
        "wall_x_lines": selected_x,
        "wall_y_lines": selected_y,
        "opening_x_lines": [],
        "opening_y_lines": [],
        "extent_boundary_count": x_boundary_count + y_boundary_count,
        "omitted_direction_count": omitted_direction_count,
        "wall_segment_count": len(walls),
        "door_segment_count": len(doors),
        "window_segment_count": len(windows),
    }


def create_inferred_building_grid(doc, bim_group, sources, params=None):
    """Create or replace one native ArchGrid object from building sources."""
    _require_arch_grid()
    params = dict(params or {})
    wall_segments = _segments_from_sources(sources.get("walls"))
    opening_segments = _segments_from_sources(sources.get("doors")) + _segments_from_sources(
        sources.get("windows")
    )
    model = infer_building_grid(
        wall_segments,
        _segments_from_sources(sources.get("doors")),
        _segments_from_sources(sources.get("windows")),
        cluster_tolerance=params.get("grid_cluster_tolerance_mm", DEFAULT_CLUSTER_TOLERANCE_MM),
        wall_min_support=params.get("grid_primary_support_mm", DEFAULT_WALL_SUPPORT_MM),
        max_lines_per_direction=params.get(
            "grid_max_lines_per_direction", DEFAULT_MAX_LINES_PER_DIRECTION
        ),
    )
    removed = remove_previous_inferred_grid(doc)
    if removed:
        msg("Cuadricula ArchGrid anterior reemplazada: %d objetos" % removed)

    uses_closed_centres = any(
        str(getattr(source, "FA_GeneratedBy", "") or "") == "FA_CloseWallSketch"
        for source in sources.get("walls", [])
    )
    grid_label = (
        "Cuadricula arquitectonica - paredes reconstruidas"
        if uses_closed_centres
        else "Cuadricula arquitectonica - centros de paredes"
    )
    grid = Arch.makeGrid(name=grid_label)
    if grid is None:
        raise RuntimeError("Arch.makeGrid no pudo crear la cuadricula.")
    grid.Label = grid_label
    grid.Rows = len(model["row_sizes"])
    grid.Columns = len(model["column_sizes"])
    grid.RowSize = [float(value) for value in model["row_sizes"]]
    grid.ColumnSize = [float(value) for value in model["column_sizes"]]
    grid.Width = float(sum(model["column_sizes"]))
    grid.Height = float(sum(model["row_sizes"]))
    grid.AutoWidth = 0.0
    grid.AutoHeight = 0.0
    grid.PointsOutput = "Vertices"
    grid.Placement = FreeCAD.Placement(
        FreeCAD.Vector(*model["origin"]),
        FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), float(model["rotation_deg"])),
    )
    _tag_grid_object(grid)
    wall_sources = list(sources.get("walls", []))
    opening_sources = list(sources.get("doors", [])) + list(sources.get("windows", []))
    set_prop(
        grid,
        "App::PropertyLinkList",
        "FA_SourceSketches",
        "FacilArquitectura",
        "Sketches de paredes, puertas y ventanas usados por el flujo",
        wall_sources + opening_sources,
    )
    set_prop(
        grid,
        "App::PropertyLinkList",
        "FA_SourceWallSketches",
        "FacilArquitectura",
        "Sketches de centros de paredes reconstruidos",
        wall_sources,
    )
    set_prop(
        grid,
        "App::PropertyLinkList",
        "FA_SourceOpeningSketches",
        "FacilArquitectura",
        "Sketches de puertas y ventanas usados para validar cierres",
        opening_sources,
    )
    set_prop(
        grid,
        "App::PropertyString",
        "FA_InferenceMethod",
        "FacilArquitectura",
        "Metodo de inferencia",
        "native_arch_grid_from_supported_wall_centrelines",
    )
    set_prop(
        grid,
        "App::PropertyBool",
        "FA_UsesClosedWallCenters",
        "FacilArquitectura",
        "La cuadricula usa centros con huecos de puertas y ventanas cerrados",
        uses_closed_centres,
    )
    set_prop(
        grid,
        "App::PropertyInteger",
        "FA_ClosedGapCount",
        "FacilArquitectura",
        "Huecos de puertas y ventanas cerrados en los sketches fuente",
        sum(int(getattr(source, "FA_ClosedGapCount", 0) or 0) for source in wall_sources),
    )
    set_prop(
        grid,
        "App::PropertyInteger",
        "FA_WallGridLineCount",
        "FacilArquitectura",
        "Lineas sostenidas por paredes",
        len(model["wall_x_lines"]) + len(model["wall_y_lines"]),
    )
    set_prop(
        grid,
        "App::PropertyInteger",
        "FA_ExtentBoundaryCount",
        "FacilArquitectura",
        "Bordes exteriores ajustados a la extension completa del sketch",
        int(model["extent_boundary_count"]),
    )
    set_prop(
        grid,
        "App::PropertyFloatList",
        "FA_LocalXPositions",
        "FacilArquitectura",
        "Posiciones locales X usadas por ArchGrid",
        [float(value) for value in model["x_positions"]],
    )
    set_prop(
        grid,
        "App::PropertyFloatList",
        "FA_LocalYPositions",
        "FacilArquitectura",
        "Posiciones locales Y usadas por ArchGrid",
        [float(value) for value in model["y_positions"]],
    )
    try:
        bim_group.addObject(grid)
    except Exception:
        pass
    try:
        grid.ViewObject.ShapeColor = (0.25, 0.65, 0.95)
        grid.ViewObject.LineColor = (0.95, 0.35, 0.05)
        grid.ViewObject.LineWidth = 2.5
        grid.ViewObject.Transparency = 92
    except Exception:
        pass
    doc.recompute()
    display = _create_clipped_grid_display(
        doc,
        bim_group,
        grid,
        wall_sources,
        wall_segments,
        opening_sources,
        opening_segments,
        float(params.get("wall_height_mm", 3000.0)) + 10.0,
        float(params.get("grid_cluster_tolerance_mm", DEFAULT_CLUSTER_TOLERANCE_MM)),
    )
    set_prop(
        grid,
        "App::PropertyLink",
        "FA_ClippedDisplay",
        "FacilArquitectura",
        "Representacion visible recortada a los centros reales de paredes",
        display,
    )
    # Sketch.Shape is populated only after recompute; the reconstructed wall
    # reads those edges immediately below.
    doc.recompute()
    reconstructed_base, reconstructed_wall = _create_reconstructed_wall(
        doc,
        bim_group,
        display,
        wall_sources,
        opening_sources,
        float(params.get("wall_thickness_mm", 120.0)),
        float(params.get("wall_height_mm", 3000.0)),
    )
    try:
        grid.ViewObject.Visibility = False
        display.ViewObject.Visibility = True
        reconstructed_base.ViewObject.Visibility = False
        reconstructed_wall.ViewObject.Visibility = True
    except Exception:
        pass
    _hide_original_bim_walls(doc)
    doc.recompute()
    return {
        "grid": grid,
        "display": display,
        "wall_base": reconstructed_base,
        "wall": reconstructed_wall,
        "model": model,
    }


def remove_previous_inferred_grid(doc):
    """Remove only objects generated by this command, including the superseded axis version."""
    candidates = [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY
    ]
    role_priority = {
        "axis_system": 0,
        "axis_family": 1,
        "reconstructed_wall": 0,
        "arch_grid": 0,
        "reconstructed_wall_base": 1,
        "grid_clipped_lines": 1,
        "grid_container": 2,
    }
    candidates.sort(key=lambda obj: role_priority.get(str(getattr(obj, "FA_Role", "") or ""), 2))
    removed = 0
    for obj in candidates:
        name = str(getattr(obj, "Name", "") or "")
        try:
            if name and doc.getObject(name) is not None:
                doc.removeObject(name)
                removed += 1
        except Exception:
            pass
    return removed


def _segments_from_sources(sketches):
    result = []
    for sketch in list(sketches or []):
        result.extend(_segments_from_sketch(sketch))
    return result


def _create_clipped_grid_display(
    doc,
    bim_group,
    grid,
    wall_sources,
    wall_segments,
    opening_sources,
    opening_segments,
    display_elevation,
    alignment_tolerance,
):
    """Show only real reconstructed wall segments while retaining the native ArchGrid."""
    if Part is None or not hasattr(Part, "makeLine") or not hasattr(Part, "makeCompound"):
        raise RuntimeError("Part no esta disponible para crear el trazado recortado de la cuadricula.")
    wall_lines = _segments_6d(wall_segments)
    closure_lines = infer_opening_closure_segments(
        wall_lines,
        opening_segments,
        max_connection_gap=3000.0,
        line_tolerance=max(150.0, float(alignment_tolerance) * 2.0),
    )
    input_segments = wall_lines + closure_lines
    segments = build_connected_orthogonal_network(
        input_segments,
        corner_tolerance=max(150.0, float(alignment_tolerance) * 2.0),
    )
    display = doc.addObject("Sketcher::SketchObject", "FA_GridWallTrace")
    display.Label = "Cuadricula visible - paredes sin puertas ni ventanas"
    geometry = [
        Part.LineSegment(
            FreeCAD.Vector(segment[0], segment[1], 0.0),
            FreeCAD.Vector(segment[3], segment[4], 0.0),
        )
        for segment in segments
    ]
    if geometry:
        display.addGeometry(geometry, False)
    constraint_summary = _add_trace_constraints(display, segments)
    display.Placement = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Rotation(),
    )
    set_prop(
        display,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Generado por",
        GENERATED_BY,
    )
    set_prop(
        display,
        "App::PropertyString",
        "FA_Role",
        "FacilArquitectura",
        "Rol",
        "grid_clipped_lines",
    )
    source_wall = next(iter(list(wall_sources or [])), None)
    source_thickness = _quantity_value(getattr(source_wall, "FA_WallThickness", 0.0))
    source_height = _quantity_value(getattr(source_wall, "FA_WallHeight", 0.0))
    set_prop(
        display,
        "App::PropertyString",
        "FA_CenterlineKind",
        "FacilArquitectura",
        "Tipo de eje compatible con los comandos BIM",
        "walls",
    )
    set_prop(
        display,
        "App::PropertyBool",
        "FA_ThicknessDetected",
        "FacilArquitectura",
        "El espesor procede del sketch de paredes fuente",
        source_thickness > 0.0,
    )
    set_prop(
        display,
        "App::PropertyLength",
        "FA_WallThickness",
        "FacilArquitectura",
        "Espesor parametrico para FA Muros BIM desde centros",
        source_thickness,
    )
    set_prop(
        display,
        "App::PropertyLength",
        "FA_WallHeight",
        "FacilArquitectura",
        "Altura parametrica para FA Muros BIM desde centros",
        source_height if source_height > 0.0 else max(0.0, float(display_elevation) - 10.0),
    )
    set_prop(
        display,
        "App::PropertyString",
        "FA_ArchGridName",
        "FacilArquitectura",
        "Nombre interno de la cuadricula BIM nativa asociada",
        str(getattr(grid, "Name", "") or ""),
    )
    set_prop(
        display,
        "App::PropertyLinkList",
        "FA_SourceWallSketches",
        "FacilArquitectura",
        "Sketches reconstruidos que limitan el trazado visible",
        list(wall_sources or []),
    )
    set_prop(
        display,
        "App::PropertyLinkList",
        "FA_SourceOpeningSketches",
        "FacilArquitectura",
        "Sketches de puertas y ventanas usados para completar los huecos",
        list(opening_sources or []),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_WallSegmentCount",
        "FacilArquitectura",
        "Segmentos procedentes del sketch de paredes reconstruidas",
        len(wall_lines),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_OpeningClosureSegmentCount",
        "FacilArquitectura",
        "Segmentos ajustados desde puertas y ventanas para completar muros",
        len(closure_lines),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_InputSegmentCount",
        "FacilArquitectura",
        "Segmentos de entrada antes de unir y dividir la red",
        len(input_segments),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_ClippedSegmentCount",
        "FacilArquitectura",
        "Segmentos visibles respaldados por paredes",
        len(geometry),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_ConstraintCount",
        "FacilArquitectura",
        "Restricciones geometricas agregadas al sketch",
        int(constraint_summary["constraint_count"]),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_CoincidentConstraintCount",
        "FacilArquitectura",
        "Restricciones coincidentes en esquinas y encuentros",
        int(constraint_summary["coincident_count"]),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_OrthogonalConstraintCount",
        "FacilArquitectura",
        "Restricciones horizontales y verticales",
        int(constraint_summary["orthogonal_count"]),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_NetworkNodeCount",
        "FacilArquitectura",
        "Nodos de la red conectada",
        int(constraint_summary["node_count"]),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_ClosedCornerNodeCount",
        "FacilArquitectura",
        "Nodos con dos o mas tramos unidos",
        int(constraint_summary["closed_corner_count"]),
    )
    set_prop(
        display,
        "App::PropertyInteger",
        "FA_OpenEndpointCount",
        "FacilArquitectura",
        "Extremos que no enlazan con otro tramo",
        int(constraint_summary["open_endpoint_count"]),
    )
    set_prop(
        display,
        "App::PropertyLength",
        "FA_DisplayElevation",
        "FacilArquitectura",
        "Elevacion real del sketch base de muros",
        0.0,
    )
    try:
        bim_group.addObject(display)
    except Exception:
        pass
    try:
        display.ViewObject.LineColor = (0.95, 0.35, 0.05)
        display.ViewObject.PointColor = (0.95, 0.35, 0.05)
        display.ViewObject.LineWidth = 3.5
    except Exception:
        pass
    return display


def _create_reconstructed_wall(
    doc, bim_group, display, wall_sources, opening_sources, width, height
):
    """Build a BIM wall from the completed centreline trace at model elevation zero."""
    edges = []
    for edge in list(getattr(getattr(display, "Shape", None), "Edges", []) or []):
        vertices = list(getattr(edge, "Vertexes", []) or [])
        if len(vertices) < 2:
            continue
        first = vertices[0].Point
        last = vertices[-1].Point
        edges.append(
            Part.makeLine(
                FreeCAD.Vector(first.x, first.y, 0.0),
                FreeCAD.Vector(last.x, last.y, 0.0),
            )
        )
    if not edges:
        raise RuntimeError("El trazado recortado no contiene segmentos para reconstruir paredes.")
    base = doc.addObject("Part::Feature", "FA_ReconstructedWallBase")
    base.Label = "Base de paredes reconstruidas sin aberturas"
    base.Shape = Part.makeCompound(edges)
    set_prop(base, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generado por", GENERATED_BY)
    set_prop(
        base,
        "App::PropertyString",
        "FA_Role",
        "FacilArquitectura",
        "Rol",
        "reconstructed_wall_base",
    )
    wall = Arch.makeWall(
        base,
        width=float(width),
        height=float(height),
        align="Center",
        name="Paredes reconstruidas sin puertas ni ventanas",
    )
    if wall is None:
        raise RuntimeError("Arch.makeWall no pudo reconstruir las paredes completas.")
    wall.Label = "Paredes BIM reconstruidas sin puertas ni ventanas"
    set_prop(wall, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generado por", GENERATED_BY)
    set_prop(
        wall,
        "App::PropertyString",
        "FA_Role",
        "FacilArquitectura",
        "Rol",
        "reconstructed_wall",
    )
    set_prop(
        wall,
        "App::PropertyLink",
        "FA_SourceGridTrace",
        "FacilArquitectura",
        "Trazado completo usado para reconstruir los muros",
        display,
    )
    set_prop(
        wall,
        "App::PropertyLinkList",
        "FA_SourceWallSketches",
        "FacilArquitectura",
        "Sketches de paredes usados",
        list(wall_sources or []),
    )
    set_prop(
        wall,
        "App::PropertyLinkList",
        "FA_SourceOpeningSketches",
        "FacilArquitectura",
        "Sketches de puertas y ventanas cerrados",
        list(opening_sources or []),
    )
    set_prop(
        wall,
        "App::PropertyLength",
        "FA_WallThickness",
        "FacilArquitectura",
        "Espesor reconstruido",
        float(width),
    )
    set_prop(
        wall,
        "App::PropertyLength",
        "FA_WallHeight",
        "FacilArquitectura",
        "Altura reconstruida",
        float(height),
    )
    try:
        bim_group.addObject(base)
        bim_group.addObject(wall)
    except Exception:
        pass
    try:
        base.ViewObject.Visibility = False
        wall.ViewObject.ShapeColor = (0.72, 0.76, 0.78)
        wall.ViewObject.LineColor = (0.15, 0.15, 0.15)
    except Exception:
        pass
    doc.recompute()
    return base, wall


def _hide_original_bim_walls(doc):
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") != "FA_CreateWallsBIM":
            continue
        if str(getattr(obj, "FA_Role", "") or "") != "wall":
            continue
        try:
            obj.ViewObject.Visibility = False
        except Exception:
            pass


def infer_opening_closure_segments(
    wall_segments,
    opening_segments,
    max_connection_gap=3000.0,
    line_tolerance=150.0,
    angle_tolerance_deg=10.0,
):
    """Snap usable door/window axes to nearby collinear walls and complete their gaps."""
    walls = _segments_6d(wall_segments)
    openings = _segments_6d(opening_segments)
    result = []
    angle_limit = math.sin(math.radians(float(angle_tolerance_deg)))
    for opening in openings:
        dx = opening[3] - opening[0]
        dy = opening[4] - opening[1]
        length = math.hypot(dx, dy)
        if length <= 1e-6:
            continue
        u = (dx / length, dy / length)
        n = (-u[1], u[0])
        origin = (opening[0], opening[1])
        candidates = []
        for wall in walls:
            wall_dx = wall[3] - wall[0]
            wall_dy = wall[4] - wall[1]
            wall_length = math.hypot(wall_dx, wall_dy)
            if wall_length <= 1e-6:
                continue
            wall_u = (wall_dx / wall_length, wall_dy / wall_length)
            if abs(_cross2(u, wall_u)) > angle_limit:
                continue
            signed_offset = _dot2(_subtract((wall[0], wall[1]), origin), n)
            if abs(signed_offset) > float(line_tolerance):
                continue
            projections = [
                _dot2(_subtract(point, origin), u)
                for point in ((wall[0], wall[1]), (wall[3], wall[4]))
            ]
            start, end = min(projections), max(projections)
            if end < 0.0:
                gap = -end
            elif start > length:
                gap = start - length
            else:
                gap = 0.0
            candidates.append(
                {
                    "gap": gap,
                    "offset": signed_offset,
                    "start": start,
                    "end": end,
                    "z": (wall[2] + wall[5]) * 0.5,
                }
            )
        usable = [item for item in candidates if item["gap"] <= float(max_connection_gap)]
        if not usable:
            continue
        support = min(usable, key=lambda item: (item["gap"], abs(item["offset"])))
        same_line = [
            item
            for item in usable
            if abs(item["offset"] - support["offset"]) <= max(25.0, float(line_tolerance) * 0.25)
        ]
        start = 0.0
        end = length
        before = [item["end"] for item in same_line if item["end"] < 0.0]
        after = [item["start"] for item in same_line if item["start"] > length]
        if before:
            start = max(before)
        if after:
            end = min(after)
        snapped_origin = (
            origin[0] + n[0] * support["offset"],
            origin[1] + n[1] * support["offset"],
        )
        z = float(support["z"])
        result.append(
            (
                snapped_origin[0] + u[0] * start,
                snapped_origin[1] + u[1] * start,
                z,
                snapped_origin[0] + u[0] * end,
                snapped_origin[1] + u[1] * end,
                z,
            )
        )
    return result


def build_connected_orthogonal_network(
    segments,
    corner_tolerance=100.0,
    coordinate_tolerance=1.0,
):
    """Merge, snap and split an orthogonal centreline network at every junction."""
    tolerance = max(1e-6, float(coordinate_tolerance))
    corner_tolerance = max(tolerance, float(corner_tolerance))
    records = []
    for segment in _segments_6d(segments):
        dx = abs(segment[3] - segment[0])
        dy = abs(segment[4] - segment[1])
        z = (segment[2] + segment[5]) * 0.5
        if dx >= dy:
            start, end = sorted((segment[0], segment[3]))
            records.append(
                {
                    "kind": "h",
                    "station": (segment[1] + segment[4]) * 0.5,
                    "start": start,
                    "end": end,
                    "z": z,
                }
            )
        else:
            start, end = sorted((segment[1], segment[4]))
            records.append(
                {
                    "kind": "v",
                    "station": (segment[0] + segment[3]) * 0.5,
                    "start": start,
                    "end": end,
                    "z": z,
                }
            )
    records = _merge_axis_records(records, tolerance)

    horizontal = [item for item in records if item["kind"] == "h"]
    vertical = [item for item in records if item["kind"] == "v"]
    for item in horizontal:
        _snap_record_endpoints(item, vertical, corner_tolerance)
    for item in vertical:
        _snap_record_endpoints(item, horizontal, corner_tolerance)

    records = _merge_axis_records(records, tolerance)
    horizontal = [item for item in records if item["kind"] == "h"]
    vertical = [item for item in records if item["kind"] == "v"]
    split_values = {id(item): [item["start"], item["end"]] for item in records}
    for h_item in horizontal:
        for v_item in vertical:
            x = v_item["station"]
            y = h_item["station"]
            if (
                h_item["start"] - tolerance <= x <= h_item["end"] + tolerance
                and v_item["start"] - tolerance <= y <= v_item["end"] + tolerance
            ):
                split_values[id(h_item)].append(_clamp(x, h_item["start"], h_item["end"]))
                split_values[id(v_item)].append(_clamp(y, v_item["start"], v_item["end"]))

    result = []
    seen = set()
    for item in records:
        values = _unique_sorted(split_values[id(item)], tolerance)
        for start, end in zip(values, values[1:]):
            if end - start <= tolerance:
                continue
            if item["kind"] == "h":
                segment = (start, item["station"], item["z"], end, item["station"], item["z"])
            else:
                segment = (item["station"], start, item["z"], item["station"], end, item["z"])
            key = tuple(round(value, 6) for value in segment[:2] + segment[3:5])
            if key not in seen:
                seen.add(key)
                result.append(segment)
    return result


def _snap_record_endpoints(record, perpendicular, tolerance):
    for endpoint in ("start", "end"):
        value = record[endpoint]
        candidates = [
            other
            for other in perpendicular
            if abs(other["station"] - value) <= tolerance
            and other["start"] - tolerance <= record["station"] <= other["end"] + tolerance
        ]
        if not candidates:
            continue
        record[endpoint] = min(
            candidates,
            key=lambda other: (
                abs(other["station"] - value),
                abs(_clamp(record["station"], other["start"], other["end"]) - record["station"]),
            ),
        )["station"]


def _merge_axis_records(records, tolerance):
    merged = []
    for kind in ("h", "v"):
        source = sorted(
            (dict(item) for item in records if item["kind"] == kind),
            key=lambda item: (item["station"], item["start"], item["end"]),
        )
        station_groups = []
        for item in source:
            if station_groups and abs(item["station"] - station_groups[-1][0]["station"]) <= tolerance:
                station_groups[-1].append(item)
            else:
                station_groups.append([item])
        for group in station_groups:
            station = sum(item["station"] for item in group) / len(group)
            z = sum(item["z"] for item in group) / len(group)
            intervals = sorted((item["start"], item["end"]) for item in group)
            start, end = intervals[0]
            for next_start, next_end in intervals[1:]:
                if next_start <= end + tolerance:
                    end = max(end, next_end)
                else:
                    merged.append(
                        {"kind": kind, "station": station, "start": start, "end": end, "z": z}
                    )
                    start, end = next_start, next_end
            merged.append({"kind": kind, "station": station, "start": start, "end": end, "z": z})
    return merged


def _unique_sorted(values, tolerance):
    result = []
    for value in sorted(float(item) for item in values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return result


def _clamp(value, minimum, maximum):
    return max(float(minimum), min(float(maximum), float(value)))


def _quantity_value(value):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return 0.0


def _add_trace_constraints(sketch, segments):
    """Constrain segment direction and make shared endpoints coincident."""
    summary = {
        "constraint_count": 0,
        "coincident_count": 0,
        "orthogonal_count": 0,
        "node_count": 0,
        "closed_corner_count": 0,
        "open_endpoint_count": 0,
    }
    nodes = {}
    orthogonal = []
    for index, segment in enumerate(list(segments or [])):
        kind = "Horizontal" if abs(segment[3] - segment[0]) >= abs(segment[4] - segment[1]) else "Vertical"
        if Sketcher is not None:
            orthogonal.append(Sketcher.Constraint(kind, index))
        for position, point in ((1, segment[:2]), (2, segment[3:5])):
            key = (round(float(point[0]), 4), round(float(point[1]), 4))
            nodes.setdefault(key, []).append((index, position))
    summary["node_count"] = len(nodes)
    summary["closed_corner_count"] = sum(1 for endpoints in nodes.values() if len(endpoints) >= 2)
    summary["open_endpoint_count"] = sum(1 for endpoints in nodes.values() if len(endpoints) == 1)
    coincident = []
    if Sketcher is not None:
        for endpoints in nodes.values():
            if len(endpoints) < 2:
                continue
            anchor = endpoints[0]
            for endpoint in endpoints[1:]:
                if endpoint[0] == anchor[0]:
                    continue
                coincident.append(
                    Sketcher.Constraint(
                        "Coincident", anchor[0], anchor[1], endpoint[0], endpoint[1]
                    )
                )
        try:
            if orthogonal or coincident:
                sketch.addConstraint(orthogonal + coincident)
            summary["orthogonal_count"] = len(orthogonal)
            summary["coincident_count"] = len(coincident)
        except Exception:
            # Compatibility fallback for older Sketcher builds without list insertion.
            for constraint in orthogonal + coincident:
                try:
                    sketch.addConstraint(constraint)
                    if constraint.Type in ("Horizontal", "Vertical"):
                        summary["orthogonal_count"] += 1
                    else:
                        summary["coincident_count"] += 1
                except Exception:
                    pass
    summary["constraint_count"] = summary["orthogonal_count"] + summary["coincident_count"]
    return summary


def _source_kind(obj):
    kind = str(getattr(obj, "FA_CenterlineKind", "") or "").strip().lower()
    if kind in ("wall", "walls", "muros", "paredes"):
        return "walls"
    if kind in ("door", "doors", "puerta", "puertas"):
        return "doors"
    if kind in ("window", "windows", "ventana", "ventanas"):
        return "windows"
    return ""


def _is_usable_source(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    return type_id.startswith("Sketcher::") or hasattr(obj, "Geometry")


def _wall_has_measured_thickness(obj):
    try:
        value = getattr(obj, "FA_WallThickness", 0.0)
        thickness = float(getattr(value, "Value", value))
    except Exception:
        thickness = 0.0
    return bool(getattr(obj, "FA_ThicknessDetected", False)) and thickness > 0.0


def _walk_selection(objects):
    pending = list(objects or [])
    result = []
    seen = set()
    while pending:
        obj = pending.pop(0)
        identity = str(getattr(obj, "Name", "") or id(obj))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(obj)
        for attr in ("Group", "Objects"):
            try:
                pending.extend(list(getattr(obj, attr, []) or []))
            except Exception:
                pass
    return result


def _segments_6d(segments):
    result = []
    for segment in list(segments or []):
        values = [float(value) for value in segment]
        if len(values) >= 6:
            clean = tuple(values[:6])
        elif len(values) == 4:
            clean = (values[0], values[1], 0.0, values[2], values[3], 0.0)
        else:
            continue
        if _length(clean) > 1e-6:
            result.append(clean)
    return result


def _segment_family(segment, u, v):
    angle = math.atan2(segment[4] - segment[1], segment[3] - segment[0]) % math.pi
    differences = (
        _axis_angle_difference(angle, _angle(u)),
        _axis_angle_difference(angle, _angle(v)),
    )
    index = 0 if differences[0] <= differences[1] else 1
    if differences[index] > math.radians(ORIENTATION_TOLERANCE_DEG):
        return None
    return "x" if index == 0 else "y"


def _cluster_records(records, tolerance):
    groups = []
    for record in sorted(records, key=lambda item: item["position"]):
        if groups:
            center = sum(item["position"] * item["length"] for item in groups[-1]) / sum(
                item["length"] for item in groups[-1]
            )
        else:
            center = 0.0
        if groups and abs(record["position"] - center) <= tolerance:
            groups[-1].append(record)
        else:
            groups.append([record])
    result = []
    for group in groups:
        total_length = sum(item["length"] for item in group)
        result.append(
            {
                "position": sum(item["position"] * item["length"] for item in group) / total_length,
                "support": total_length,
                "max_length": max(item["length"] for item in group),
                "segment_count": len(group),
                "kinds": sorted(set(item["kind"] for item in group)),
            }
        )
    return result


def _select_wall_lines(clusters, minimum_support, maximum_count):
    if len(clusters) < 2:
        return list(clusters)
    boundaries = {clusters[0]["position"], clusters[-1]["position"]}
    selected = [
        item for item in clusters if item["support"] >= minimum_support or item["position"] in boundaries
    ]
    if len(selected) < 2:
        selected = sorted(clusters, key=lambda item: (-item["support"], item["position"]))[:2]
    maximum_count = max(2, int(maximum_count))
    if len(selected) > maximum_count:
        outer = [item for item in selected if item["position"] in boundaries]
        inner = [item for item in selected if item["position"] not in boundaries]
        inner.sort(key=lambda item: (-item["support"], item["position"]))
        selected = outer + inner[: max(0, maximum_count - len(outer))]
    return sorted(selected, key=lambda item: item["position"])


def _local_segment_extents(segments, u, v):
    points = [
        point
        for segment in segments
        for point in ((segment[0], segment[1]), (segment[3], segment[4]))
    ]
    return (
        (min(_dot(point, u) for point in points), max(_dot(point, u) for point in points)),
        (min(_dot(point, v) for point in points), max(_dot(point, v) for point in points)),
    )


def _fit_grid_boundaries_to_extents(positions, extents, tolerance):
    """Use exact source extents as outer ArchGrid limits without moving inner centres."""
    values = sorted(float(value) for value in positions)
    changed = 0
    for extent in (float(extents[0]), float(extents[1])):
        if values:
            nearest_index = min(range(len(values)), key=lambda index: abs(values[index] - extent))
            if abs(values[nearest_index] - extent) <= tolerance:
                if abs(values[nearest_index] - extent) > 1e-7:
                    values[nearest_index] = extent
                    changed += 1
                continue
        values.append(extent)
        changed += 1
    return sorted(set(values)), changed


def _positive_direction(direction):
    x, y = float(direction[0]), float(direction[1])
    length = math.hypot(x, y)
    x, y = x / length, y / length
    if x < -1e-9 or (abs(x) <= 1e-9 and y < 0.0):
        x, y = -x, -y
    return (x, y)


def _midpoint(segment):
    return ((segment[0] + segment[3]) / 2.0, (segment[1] + segment[4]) / 2.0)


def _length(segment):
    return math.hypot(segment[3] - segment[0], segment[4] - segment[1])


def _dot(first, second):
    return float(first[0]) * float(second[0]) + float(first[1]) * float(second[1])


def _dot2(first, second):
    return _dot(first, second)


def _cross2(first, second):
    return float(first[0]) * float(second[1]) - float(first[1]) * float(second[0])


def _subtract(first, second):
    return (float(first[0]) - float(second[0]), float(first[1]) - float(second[1]))


def _angle(direction):
    return math.atan2(float(direction[1]), float(direction[0])) % math.pi


def _average_z(segments):
    values = [value for segment in segments for value in (segment[2], segment[5])]
    return sum(values) / len(values) if values else 0.0


def _tag_grid_object(grid):
    set_prop(grid, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generado por", GENERATED_BY)
    set_prop(grid, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "arch_grid")


def _require_arch_grid():
    if Arch is None or not hasattr(Arch, "makeGrid"):
        raise UserFacingError("Esta instalacion no ofrece Arch.makeGrid (ArchGrid).")
