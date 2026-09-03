"""Nucleo independiente del modo demostracion guiada de Facil Arquitectura.

Nombre: demo_guided_core.py
Proposito: definir el guion reproducible de pasos de FA Demo edificio sin depender
de FreeCAD, FreeCADGui, Qt ni de objetos del documento.
Funcion principal: exponer una secuencia estable y JSON-compatible que el adaptador
de FreeCAD puede ejecutar paso a paso o de forma continua.
Instrucciones relevantes para futuras modificaciones:
- No importar FreeCAD, FreeCADGui, Qt, Draft, Arch ni Part.
- Mantener IDs de pasos estables; MCP y pruebas pueden depender de ellos.
- Cada capacidad FA mostrada debe corresponder a una herramienta real del Workbench;
  los pasos nativos deben identificarse expresamente como Sketcher/Draft.
- No inventar porcentajes de avance en pasos largos.
Version: 0.4.0
Fecha y hora: 2026-09-02 12:15 America/Costa_Rica
"""

from __future__ import annotations

import copy

from .process_feedback import LONG_PROCESS_MESSAGE


_GUIDED_STEPS = (
    {"id":"project","title":"Crear proyecto y Nivel","description":"Crea el documento de demostracion, parametros, Building, Nivel 00 y el controlador reproducible.","camera":"axon","icon":"demo_building.svg","tool":"FA Crear proyecto","title_en":'Create project and Level',"description_en":'Creates the demo document, parameters, Building, Level 00, and the reproducible controller.',"tool_en":'FA Create project'},
    {"id":"wall_sources","title":"Dibujar Sketches de muros","description":"Genera las fuentes 2D de muros exteriores e interiores y las prepara como ejes de muro.","camera":"top","icon":"centerlines_from_selection.svg","tool":"Sketcher / FA Centros de ejes","title_en":'Draw wall Sketches',"description_en":'Generates the 2D sources for exterior and interior walls and prepares them as wall centerlines.',"tool_en":'Sketcher / FA Centerlines'},
    {"id":"floor","title":"Crear losa BIM y jardin","description":"Reutiliza FA Piso BIM y el Site/Terrain nativo: crea la losa y un terreno plano verde alrededor de la casa a manera de jardin.","camera":"axon","icon":"site_floor_bim.svg","tool":"FA Piso BIM","title_en":'Create BIM slab and garden',"description_en":'Reuses FA BIM Floor and native Site/Terrain: creates the slab and a flat green terrain around the house as a garden.',"tool_en":'FA BIM Floor'},
    {"id":"walls","title":"Crear muros BIM","description":"Convierte los Sketches de centros en muros Arch/BIM con espesor y altura de la especificacion.","camera":"axon","icon":"walls_from_centerlines.svg","tool":"FA Muros BIM","title_en":'Create BIM walls',"description_en":'Converts centerline Sketches into Arch/BIM walls using the specification thickness and height.',"tool_en":'FA BIM Walls'},
    {"id":"door_sources","title":"Dibujar centros de puertas","description":"Muestra el Sketch 2D que define posicion, orientacion y ancho de cada puerta.","camera":"top","icon":"door_centerlines.svg","tool":"FA Centros de puertas","title_en":'Draw door centerlines',"description_en":'Shows the 2D Sketch defining position, orientation, and width for each door.',"tool_en":'FA Door Centerlines'},
    {"id":"doors","title":"Crear puertas BIM","description":"Crea puertas Arch nativas, resuelve sus muros anfitriones y valida los cortes.","camera":"axon","icon":"door_centerlines.svg","tool":"FA Puertas BIM","long_process":True,"duration_note":LONG_PROCESS_MESSAGE,"title_en":'Create BIM doors',"description_en":'Creates native Arch doors, resolves their host walls, and validates the cuts.',"tool_en":'FA BIM Doors',"duration_note_en":'This operation may take a while. FreeCAD can remain busy while the calculation finishes.'},
    {"id":"window_sources","title":"Dibujar centros de ventanas","description":"Muestra el Sketch 2D que define posicion, orientacion y ancho de las ventanas.","camera":"top","icon":"window_centerlines.svg","tool":"FA Centros de ventanas","title_en":'Draw window centerlines',"description_en":'Shows the 2D Sketch defining position, orientation, and width for the windows.',"tool_en":'FA Window Centerlines'},
    {"id":"windows","title":"Crear ventanas BIM","description":"Crea ventanas Arch nativas con antepecho y altura, resuelve hosts y valida cortes.","camera":"axon","icon":"window_centerlines.svg","tool":"FA Ventanas BIM","long_process":True,"duration_note":LONG_PROCESS_MESSAGE,"title_en":'Create BIM windows',"description_en":'Creates native Arch windows with sill and height, resolves hosts, and validates cuts.',"tool_en":'FA BIM Windows',"duration_note_en":'This operation may take a while. FreeCAD can remain busy while the calculation finishes.'},
    {"id":"rooms","title":"Detectar recintos 2D","description":"Reutiliza la deteccion de recintos de Facil Arquitectura y conserva el Sketch documental resultante.","camera":"top","icon":"detect_rooms.svg","tool":"FA Detectar recintos 2D","title_en":'Detect 2D rooms',"description_en":'Reuses Facil Arquitectura room detection and preserves the resulting documentary Sketch.',"tool_en":'FA Detect 2D Rooms'},
    {"id":"spaces","title":"Crear Espacios BIM","description":"Materializa cada recinto como Arch Space nativo con volumen y trazabilidad del poligono de piso.","camera":"axon","icon":"bim_spaces.svg","tool":"FA Crear espacios BIM","title_en":'Create BIM Spaces',"description_en":'Materializes each room as a native Arch Space with volume and floor-polygon traceability.',"tool_en":'FA Create BIM Spaces'},
    {"id":"ceiling","title":"Crear cielorraso modular","description":"Genera la reticula y paneles 600 x 600 mediante la herramienta vigente de cielorrasos.","camera":"axon","icon":"modular_ceiling.svg","tool":"FA Cielorraso modular","title_en":'Create modular ceiling',"description_en":'Generates 600 x 600 panels using the current modular-ceiling tool.',"tool_en":'FA Modular Ceiling'},
    {"id":"roof_source","title":"Dibujar huella de techo","description":"Crea el Draft Rectangle que sirve como fuente 2D del sistema de cubierta.","camera":"top","icon":"roof_from_rectangle.svg","tool":"Draft Rectangle","title_en":'Draw roof footprint',"description_en":'Creates the Draft Rectangle used as the 2D source for the roof system.',"tool_en":'Draft Rectangle'},
    {"id":"roof","title":"Crear techo BIM","description":"Reutiliza FA Techo desde rectangulo para crear ejes, cerchas, clavadores y cubierta a dos aguas.","camera":"axon","icon":"roof_from_rectangle.svg","tool":"FA Techo desde rectangulo","long_process":True,"duration_note":LONG_PROCESS_MESSAGE,"title_en":'Create BIM roof',"description_en":'Reuses FA Roof from Rectangle to create axes, trusses, purlins, and a gable roof covering.',"tool_en":'FA Roof from Rectangle',"duration_note_en":'This operation may take a while. FreeCAD can remain busy while the calculation finishes.'},
    {"id":"finalize","title":"Finalizar demostracion","description":"Actualiza trazabilidad, enlaces del controlador, vista final y resumen del edificio generado.","camera":"axon","icon":"demo_building.svg","tool":"FA Demo edificio","title_en":'Finish demonstration',"description_en":'Updates traceability, controller links, final view, and the generated-building summary.',"tool_en":'FA Building Demo'},
)


def guided_steps():
    return [copy.deepcopy(item) for item in _GUIDED_STEPS]


def guided_total_steps():
    return len(_GUIDED_STEPS)


def guided_step(step_number):
    number = int(step_number)
    if number < 1 or number > len(_GUIDED_STEPS):
        raise ValueError("Paso guiado fuera de rango: %s" % step_number)
    return copy.deepcopy(_GUIDED_STEPS[number - 1])


def guided_progress_text(current_step, language="es"):
    current = int(current_step)
    total = len(_GUIDED_STEPS)
    english = str(language or "es").lower().startswith("en")
    if current <= 0:
        return ("Ready to start | 0/%d" if english else "Listo para iniciar | 0/%d") % total
    if current >= total:
        return ("Demo completed | %d/%d" if english else "Demostracion completada | %d/%d") % (total, total)
    step = _GUIDED_STEPS[current - 1]
    title = step.get("title_en") if english else step.get("title")
    if english:
        return "Step %d of %d | %s" % (current, total, title)
    return "Paso %d de %d | %s" % (current, total, title)
