# Area por click - pseudocodigo

## Contexto del proyecto aplicado

- ElectricCR registra macros por carpeta. Esta herramienta debe vivir en `Areas`.
- La macro debe usar cabecera con `MenuText`, `ToolTip`, `Icon` y `Transaction: self`.
- El flujo requiere interaccion continua con la vista 3D, por lo que debe usar panel no modal.
- Segun las notas recurrentes, preferir `QDockWidget` movible y flotante sobre `QDialog.exec_()`.
- Las Areas no deben limitarse a rectangulos. El contorno puede ser cualquier geometria plana cerrada.
- La deteccion de recintos debe soportar alias: `Areas`, `Recintos`, `Espacios`, `Zonas`.
- Evitar que objetos ya generados de Areas entren otra vez como geometria fuente.

## Objetivo

Crear un panel de FreeCAD para generar poligonos de recintos por clicks sucesivos:

1. El usuario abre el panel.
2. El panel analiza una vez la geometria del plano y construye una red 2D de limites.
3. El usuario activa captura.
4. El usuario hace click dentro de cada recinto.
5. Por cada click, la macro crea el poligono cerrado del recinto que contiene ese punto.
6. El usuario puede seguir clickando recintos hasta cerrar el panel o detener captura.

## Decision principal

No calcular el poligono desde cero para cada click.

La macro debe separar el proceso en dos niveles:

- Preparacion global: leer lineas, limpiar detalles, cerrar huecos razonables y generar caras candidatas.
- Resolucion por click: buscar la cara cerrada mas pequena que contiene el punto clicado.

Esto permite que funcione para todos los recintos en una misma sesion y evita recalcular intersecciones pesadas en cada click.

## Panel propuesto

Nombre:

```text
Areas por click
```
Controles:

```text
Alcance:
    combo: Auto / Seleccion actual / Objetos visibles / Grupo elegido
    combo grupo fuente: listado de grupos candidatos
    boton: Actualizar alcance

Destino:
    combo grupo destino: Areas / Recintos / Espacios / Zonas / crear Areas
    texto prefijo: Area
    contador inicial
    checkbox: Omitir si el click cae dentro de un area existente

Captura:
    boton: Reconstruir red
    boton toggle: Iniciar clicks / Detener clicks
    boton: Deshacer ultimo
    boton: Borrar generados de esta sesion

Tolerancias:
    snap endpoints
    cerrar buque puerta
    extender union T
    longitud minima muro
    tamano maximo columna/detalle
    area minima recinto

Debug:
    checkbox: crear grupo debug
    checkbox: mostrar cierres virtuales
    checkbox: mostrar segmentos ignorados
    tabla resumen: label, area m2, lados, cierres virtuales, confianza
```

Reglas UI:

```text
crear QDockWidget con objectName estable
permitir Left/Right/Top/Bottom DockWidgetArea
permitir DockWidgetClosable, DockWidgetMovable, DockWidgetFloatable
persistir floating/acoplado y tolerancias en preferencias
fallback a QDialog no modal si QDockWidget falla
no usar exec_()
```

## Estados internos

```text
SessionState:
    doc
    dock
    panel_widget
    capture_active
    snapper_active
    source_scope
    destination_group
    generated_objects
    wall_model
    face_index
    preferences

WallModel:
    raw_segments
    wall_segments
    ignored_segments
    virtual_segments
    nodes
    graph_edges
    faces

Segment2D:
    p1
    p2
    source_object_name
    source_object_label
    source_edge_index
    kind: real_wall / virtual_gap / ignored_detail
    confidence

FaceCandidate:
    points
    bbox
    area_mm2
    real_edge_count
    virtual_edge_count
    confidence
```

## Flujo principal del macro

```text
function main():
    validar FreeCADGui, ActiveDocument, PySide
    cerrar panel anterior con el mismo objectName si existe
    crear SessionState global para evitar garbage collection
    construir QDockWidget
    cargar preferencias
    poblar combos de grupos
    conectar botones
    mostrar panel
```

## Al pulsar "Reconstruir red"

```text
function rebuild_wall_model():
    doc = FreeCAD.ActiveDocument

    scope_objects = resolve_scope_from_panel()

    raw_segments = collect_segments(scope_objects)
    classified = classify_segments(raw_segments)
    cleaned = normalize_wall_network(classified.wall_segments)
    graph = build_planar_graph(cleaned)
    faces = extract_faces(graph)
    faces = filter_room_faces(faces)

    state.wall_model = graph
    state.face_index = build_face_index(faces)

    update_panel_summary()
    if debug enabled:
        draw_debug_geometry()
```

## Recoleccion de segmentos

```text
function collect_segments(objects):
    segments = []

    for obj in objects:
        if obj is generated area:
            continue

        if obj is inside destination Areas group:
            continue

        if object label/name suggests sensors, humo, luminarias, tomas, cajas:
            continue unless user selected it explicitly

        if obj has no Shape:
            continue

        for edge in obj.Shape.Edges:
            if edge is straight line:
                p1, p2 = endpoints projected to XY
                if distance(p1, p2) >= tiny_length:
                    add Segment2D(p1, p2, source=obj)

            else if edge is arc/circle:
                if arc looks like door swing:
                    add to ignored_segments
                else:
                    discretize only if user enabled curve support

    return segments
```

## Clasificacion de geometria

La clasificacion no debe depender de una sola regla. Debe sumar evidencia.

```text
function classify_segments(raw_segments):
    detect dominant directions from long segments

    for segment in raw_segments:
        score_wall = 0
        score_detail = 0

        if length >= min_wall_length:
            score_wall += 2
        else:
            score_detail += 2

        if angle matches dominant direction:
            score_wall += 1

        if segment connects to other long segments:
            score_wall += 2

        if segment belongs to small closed rectangle:
            score_detail += 4

        if segment is near/inside wall thickness and short:
            score_detail += 2

        if source label suggests column/window/door/symbol:
            score_detail += 2

        if source label suggests wall/muro/pared/arquitectura:
            score_wall += 2

        if score_detail > score_wall:
            ignored_segments.add(segment)
        else:
            wall_segments.add(segment)

    remove probable columns:
        find small closed loops
        if bbox width and height <= max_column_size:
            move those segments to ignored_segments

    remove door swing arcs:
        arcs are ignored for boundary
        jamb/short door lines are ignored unless they are required to close a wall face

    return wall_segments, ignored_segments
```

## Normalizacion de red de muros

```text
function normalize_wall_network(wall_segments):
    segments = copy(wall_segments)

    snap endpoints:
        group points closer than tol_snap
        replace each point by group centroid

    merge collinear overlaps:
        for each direction cluster:
            group segments on same support line
            merge segments that overlap or almost touch

    close collinear door gaps:
        for two collinear segments on same support:
            gap = distance between nearest endpoints along support
            if 0 < gap <= tol_door_gap:
                add virtual segment between endpoints

    extend T junctions:
        for each free endpoint:
            find nearest segment whose support is perpendicular or compatible
            if projection falls inside target segment
            and distance <= tol_t_gap:
                extend endpoint to projection
                mark added part as virtual

    split at intersections:
        compute every intersection between non-parallel segments
        add intersection as node if it lies inside both segment extents
        split long segments at all internal nodes

    remove dangling detail stubs:
        delete segments with one free end if length < min_wall_length
        keep long perimeter segments even if one end remains open

    deduplicate:
        remove repeated segments with same snapped endpoints

    return real segments + virtual segments
```

## Construccion de grafo planar

```text
function build_planar_graph(segments):
    nodes = unique segment endpoints

    for each segment:
        create undirected edge between nodes
        store kind real/virtual and source metadata

    for each node:
        collect connected edges
        sort outgoing half-edges by atan2 angle

    return graph
```

## Extraccion de poligonos cerrados

Usar recorrido de semiaristas. Cada segmento se visita en ambos sentidos.

```text
function extract_faces(graph):
    faces = []
    visited_half_edges = set()

    for each directed edge (u -> v):
        if directed edge visited:
            continue

        ring = []
        current = (u -> v)

        while current not visited:
            mark current visited
            append current.start point to ring

            at node current.end:
                find reverse direction (current.end -> current.start)
                choose next outgoing edge by left-hand rule
                current = next edge

            if current returns to starting directed edge:
                close ring
                break

        if ring is closed and valid:
            area = signed_area(ring)
            add face with points, area, edge metadata

    remove exterior face:
        exterior is usually largest absolute area or wrong winding

    simplify:
        remove duplicate consecutive points
        remove collinear intermediate points

    return faces
```

## Filtrado de caras candidatas

```text
function filter_room_faces(faces):
    candidates = []

    for face in faces:
        if abs(face.area) < min_room_area:
            continue

        if face is wall-thickness strip:
            continue if narrow ratio and no user click inside it

        if face has too many virtual edges:
            keep but lower confidence

        if face bbox is absurdly large compared with drawing:
            lower confidence or mark as exterior

        candidates.add(face)

    return candidates
```

## Al pulsar "Iniciar clicks"

```text
function start_capture():
    if state.face_index is empty:
        rebuild_wall_model()

    state.capture_active = True
    arm_next_point_capture()
```

Captura recomendada:

```text
function arm_next_point_capture():
    if not state.capture_active:
        return

    state.snapper_active = True
    Gui.Snapper.getPoint(
        callback = on_point_clicked,
        title = "Click dentro de un recinto"
    )
```

Despues de cada click:

```text
function on_point_clicked(point, snapinfo=None):
    state.snapper_active = False

    if point is None:
        state.capture_active = False
        update_button_state()
        return

    seed = project point to XY
    result = create_area_from_seed(seed)
    update_table(result)

    if state.capture_active:
        QTimer.singleShot(0, arm_next_point_capture)
```

Al detener o cerrar:

```text
function stop_capture():
    state.capture_active = False
    if Gui.Snapper can be cancelled:
        cancel active Snapper
    persist preferences
```

## Resolver area por click

```text
function create_area_from_seed(seed):
    existing = find_existing_area_containing(seed)
    if existing and panel.skip_existing:
        return status "omitida"

    candidates = query face_index by seed bbox
    candidates = [face for face in candidates if point_in_polygon(seed, face.points)]

    if candidates is empty:
        fallback = raster_flood_fill(seed)
        if fallback succeeds:
            face = fallback.face
        else:
            warn user and optionally draw debug marker
            return status "sin recinto"
    else:
        face = choose_best_face(seed, candidates)

    if face.confidence < warning_threshold:
        show warning in table but still create area

    obj = make_area_object(face, seed)
    state.generated_objects.append(obj)
    doc.recompute()

    return status "creada", obj, face
```

## Seleccion de mejor cara

```text
function choose_best_face(seed, candidates):
    sort candidates by:
        1. smaller area
        2. higher confidence
        3. fewer virtual closures
        4. lower perimeter complexity

    return first candidate
```

La cara mas pequena que contiene el punto evita escoger el contorno exterior del edificio cuando tambien contiene el click.

## Fallback raster opcional

Usar solo cuando la red vectorial no cierra un recinto o la confianza sea muy baja.

```text
function raster_flood_fill(seed):
    define local bbox around seed or full drawing bbox
    choose grid size from tolerance, for example 50 mm to 100 mm

    burn wall segments into obstacle grid:
        real wall segments
        virtual closure segments
        inflated by wall/line tolerance

    ignore detail segments:
        columns
        door arcs
        window symbols
        generated areas

    flood fill from seed cell
    trace boundary of filled region
    simplify contour with Douglas-Peucker
    snap contour vertices to nearby wall support lines

    if resulting polygon valid:
        return FaceCandidate with low/medium confidence
    else:
        fail
```

## Creacion del objeto Area

```text
function make_area_object(face, seed):
    label = next label from panel prefix and counter
    points = face.points + first point

    doc.openTransaction("ElectricCR: crear area por click")

    try:
        wire = Draft.makeWire(points, closed=True, face=True)
        wire.Label = label

        ensure properties:
            ElectricCRTipo = "Area"
            AreaM2
            SeedX
            SeedY
            Source = "AreaPorClick"
            VirtualClosures
            Confidence
            GeneratedBy = macro name

        add wire to destination group
        doc.commitTransaction()
        return wire

    except:
        doc.abortTransaction()
        raise
```

Si `Draft.makeWire(..., face=True)` no existe en la version de FreeCAD:

```text
wire = Draft.makeWire(points, closed=True)
set wire.MakeFace = True if property exists
or create Part.Face(Part.makePolygon(points)) as fallback
```

## Debug visual

```text
function draw_debug_geometry():
    group = ensure group "_AreaPorClick_Debug"

    draw real wall network in green or default
    draw virtual closures in magenta/red
    draw ignored details in yellow/gray
    draw failed seed clicks as small circles/crosses
    draw candidate face id text only if debug labels enabled
```

## Casos que debe soportar

```text
Caso 1: recinto rectangular simple
    click dentro
    crea poligono cerrado con 4 lados

Caso 2: recinto irregular en L
    click dentro
    crea poligono no rectangular

Caso 3: puerta con arco y buque
    ignora arco de puerta
    cierra el hueco si gap <= tolerancia
    crea recinto separado

Caso 4: ventana sobre pared
    ignora lineas de simbolo de ventana
    conserva la cara interior de muro como limite

Caso 5: columna dentro del recinto
    detecta pequeno rectangulo cerrado
    lo ignora como limite de recinto
    no parte el recinto en caras falsas

Caso 6: linea larga que atraviesa varios recintos
    divide la linea en intersecciones
    no impide generar cada recinto por separado

Caso 7: muro que casi llega a otro
    extiende union T si distancia <= tolerancia
    marca el tramo como virtual

Caso 8: abertura grande real
    si gap > tolerancia, no cerrar automaticamente
    reportar que el recinto no esta cerrado o requiere tolerancia mayor

Caso 9: click repetido en recinto ya generado
    omitir o advertir segun checkbox del panel

Caso 10: todos los recintos
    reconstruir red una vez
    clickar varios recintos
    crear un area por click sin cerrar el panel
```

## Riesgos tecnicos

- Si el plano mezcla muchas capas sin nombres claros, la clasificacion debe depender mas de conectividad y longitud que de labels.
- Si un buque de puerta es mas ancho que la tolerancia, el recinto no se cerrara automaticamente.
- Si una columna es grande o esta pegada a muros, puede parecer parte del limite real.
- Si la geometria fuente incluye curvas como limites reales, la primera version puede requerir discretizacion controlada.
- Si hay dos pisos o niveles superpuestos en XY, el alcance debe filtrarse por grupo o seleccion para no mezclar plantas.

## Implementacion por etapas

```text
Etapa 1:
    panel QDockWidget
    recolectar segmentos rectos
    snap endpoints
    cerrar gaps colineales
    split por intersecciones
    extraer caras
    crear Draft Wire por click

Etapa 2:
    clasificador robusto de columnas/ventanas/puertas
    debug visual
    tabla de resultados
    deduplicacion contra areas existentes

Etapa 3:
    extender uniones T
    fallback raster
    propiedades ElectricCR completas
    soporte SubAreas

Etapa 4:
    optimizacion con indice espacial
    presets de tolerancias por escala/planta
    pruebas con planos reales
```
