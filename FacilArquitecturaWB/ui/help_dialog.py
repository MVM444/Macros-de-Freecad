"""Integrated user Help for Facil Arquitectura.

Name: ui/help_dialog.py
Purpose: keep Getting Started, CAD import guidance, the real DWG/DXF-to-BIM
workflow, toolbar explanations, Demo information and About information in one
canonical read-only dialog.
Main behavior: bilingual Spanish/English UI that follows the FreeCAD language and
launches only existing FA commands; it never creates or modifies documents by itself.
Maintenance notes:
- Keep this as the canonical short user-help source; do not duplicate a divergent
  mini-manual inside command modules.
- Use "buque/buques" in Spanish user-facing text for architectural openings.
- Keep DWG/DXF limitations explicit and conservative.
- Mark Rooms/Spaces generation as experimental while explaining that BIM Space is
  the intended integration object for other engineering and building-services Workbenches.
- Do not present FA as a replacement for architects, drafters, BIM specialists or
  the native architectural tools already available in FreeCAD.
Version: 0.2.0
Date and time: 2026-09-02 15:35 America/Costa_Rica
"""

from __future__ import annotations

import os

import FreeCADGui
from PySide import QtGui, QtWidgets

from .. import i18n
from ..core.constants import BUILD_ID, VERSION

ICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons"))
HELP_ICON_PATH = os.path.join(ICON_DIR, "fa_help.svg").replace(os.sep, "/")


def _icon(name):
    return os.path.join(ICON_DIR, str(name)).replace(os.sep, "/")


def _main_window():
    try:
        return FreeCADGui.getMainWindow()
    except Exception:
        return None


def _label(text, bold=False):
    widget = QtWidgets.QLabel(text)
    widget.setWordWrap(True)
    if bold:
        font = widget.font()
        font.setBold(True)
        widget.setFont(font)
    return widget


def _step(icon_name, title, description):
    row = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(row)
    icon = QtWidgets.QLabel()
    icon.setFixedSize(48, 48)
    icon.setPixmap(QtGui.QIcon(_icon(icon_name)).pixmap(42, 42))
    layout.addWidget(icon)
    texts = QtWidgets.QVBoxLayout()
    texts.addWidget(_label(title, bold=True))
    texts.addWidget(_label(description))
    layout.addLayout(texts, 1)
    return row


def _scroll_tab():
    tab = QtWidgets.QWidget()
    outer = QtWidgets.QVBoxLayout(tab)
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    body = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(body)
    scroll.setWidget(body)
    outer.addWidget(scroll, 1)
    return tab, layout


def _run(command_id):
    try:
        FreeCADGui.runCommand(command_id)
    except Exception:
        pass


def build_first_steps_tab():
    tab, layout = _scroll_tab()
    layout.addWidget(_label(i18n.bi(
        "Facil Arquitectura esta orientado a obtener rapidamente una base arquitectonica BIM utilizable. Puede comenzar con una Demo, con un DWG/DXF existente o dibujando/corrigiendo Sketches directamente en FreeCAD.",
        "Facil Arquitectura is intended to quickly obtain a usable architectural BIM base. You can start with a Demo, an existing DWG/DXF, or by drawing/correcting Sketches directly in FreeCAD.",
    )))
    layout.addWidget(_step(
        "demo_building.svg",
        i18n.bi("1. Quiero conocer Facil Arquitectura", "1. I want to learn Facil Arquitectura"),
        i18n.bi(
            "Use Demo edificio. Genera una casa de prueba en un documento nuevo y permite observar el flujo completo sin preparar un archivo previo.",
            "Use Building Demo. It creates a test house in a new document and lets you observe the complete workflow without preparing a source file.",
        ),
    ))
    layout.addWidget(_step(
        "import_cad_reference.svg",
        i18n.bi("2. Tengo un plano DWG o DXF", "2. I have a DWG or DXF drawing"),
        i18n.bi(
            "Importe el archivo, seleccione la escala/unidad del dibujo original y las capas que contienen la informacion necesaria. Luego prepare centros de paredes, ventanas y puertas antes de crear el BIM.",
            "Import the file, select the original drawing scale/unit and the layers containing the required information. Then prepare wall, window, and door centerlines before creating BIM objects.",
        ),
    ))
    layout.addWidget(_step(
        "walls_from_centerlines.svg",
        i18n.bi("3. Voy a dibujar manualmente", "3. I will draw manually"),
        i18n.bi(
            "Cree o corrija Sketches 2D y continue con paredes, puertas, ventanas, Recintos/Espacios BIM, techo y cielorraso segun lo requiera el modelo.",
            "Create or correct 2D Sketches and continue with walls, doors, windows, Rooms/BIM Spaces, roof, and ceiling as required by the model.",
        ),
    ))

    layout.addWidget(_label(i18n.bi(
        "Importante: el flujo desde CAD ha sido probado con un numero limitado de planos. No se garantiza que cualquier DWG/DXF pueda reconstruirse automaticamente; puede requerir seleccion cuidadosa de capas, limpieza y correccion manual.",
        "Important: the CAD workflow has been tested with a limited number of drawings. Automatic reconstruction is not guaranteed for every DWG/DXF; careful layer selection, cleanup, and manual correction may be required.",
    ), bold=True))
    layout.addWidget(_label(i18n.bi(
        "FA no pretende sustituir a un arquitecto, dibujante especializado ni a las herramientas arquitectonicas/BIM de FreeCAD. Su objetivo es facilitar un modelo rapido, especialmente cuando se necesita una base para otros flujos de ingenieria e instalaciones.",
        "FA is not intended to replace an architect, professional drafter, or FreeCAD's architectural/BIM tools. Its purpose is to facilitate a quick model, especially when a base is needed for other engineering and building-services workflows.",
    )))

    buttons = QtWidgets.QHBoxLayout()
    demo = QtWidgets.QPushButton(i18n.bi("Abrir Demo", "Open Demo"))
    demo.setIcon(QtGui.QIcon(_icon("demo_building.svg")))
    demo.clicked.connect(lambda: _run("FA_DemoBuilding"))
    cad = QtWidgets.QPushButton(i18n.bi("Importar DWG/DXF", "Import DWG/DXF"))
    cad.setIcon(QtGui.QIcon(_icon("import_cad_reference.svg")))
    cad.clicked.connect(lambda: _run("FA_ImportCADReference"))
    buttons.addWidget(demo)
    buttons.addWidget(cad)
    buttons.addStretch(1)
    layout.addLayout(buttons)
    layout.addStretch(1)
    return tab


def build_cad_tab():
    tab, layout = _scroll_tab()
    layout.addWidget(_label(i18n.bi("DWG / DXF - condiciones de uso", "DWG / DXF - usage conditions"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "DXF se importa directamente. Para DWG, FreeCAD necesita un convertidor DWG externo configurado; normalmente se utiliza ODA File Converter. Facil Arquitectura usa el convertidor que FreeCAD tenga configurado.",
        "DXF is imported directly. For DWG, FreeCAD needs a configured external DWG converter; ODA File Converter is commonly used. Facil Arquitectura uses the converter configured in FreeCAD.",
    )))
    layout.addWidget(_label(i18n.bi(
        "Si no dispone de un convertidor DWG, convierta previamente el archivo a DXF y use el mismo comando Importar DWG/DXF.",
        "If no DWG converter is available, convert the file to DXF first and use the same Import DWG/DXF command.",
    )))
    layout.addWidget(_label(i18n.bi("Antes de generar BIM", "Before generating BIM"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "1) Seleccione la escala/unidad que corresponde al dibujo original.  2) Importe solamente las capas que contienen informacion util.  3) Compruebe una distancia conocida.  4) Revise bloques, textos, lineas duplicadas, geometria fuera de lugar y capas que no sean necesarias.",
        "1) Select the scale/unit that matches the original drawing.  2) Import only the layers that contain useful information.  3) Verify a known distance.  4) Review blocks, text, duplicate lines, misplaced geometry, and unnecessary layers.",
    )))
    layout.addWidget(_label(i18n.bi("Capas recomendadas para el flujo FA", "Recommended layers for the FA workflow"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "- Paredes: seleccione la capa y use FA Centros desde seleccion.\n- Ventanas: seleccione la capa y use FA Centros de ventanas.\n- Puertas: seleccione la capa y use FA Centros de puertas.\n- Rotulos de recintos: conserve/importa la capa correspondiente cuando exista y use la herramienta de rotulos de recintos.",
        "- Walls: select the layer and use FA Centerlines from Selection.\n- Windows: select the layer and use FA Window Centerlines.\n- Doors: select the layer and use FA Door Centerlines.\n- Room labels: keep/import the corresponding layer when available and use the room-label tool.",
    )))
    layout.addWidget(_label(i18n.bi("Buques y limpieza", "Openings and cleanup"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Si despues de preparar los Sketches quedan espacios vacios asociados a buques de puertas o ventanas, revise primero que correspondan realmente a una abertura y utilice FA Cerrar buques cuando proceda. No use la herramienta para cerrar interrupciones cuya funcion no haya sido identificada.",
        "If empty spaces associated with door or window openings remain after preparing the Sketches, first verify that they are real openings and use FA Close Openings when appropriate. Do not use the tool to close interruptions whose purpose has not been identified.",
    )))
    layout.addWidget(_label(i18n.bi("Limitaciones conocidas", "Known limitations"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Los planos CAD pueden variar ampliamente en capas, bloques, unidades, polilineas, precision y criterio de dibujo. La importacion no limpia automaticamente el archivo ni lo convierte por si sola en un modelo BIM. El flujo actual se ha validado con pocos ejemplos y debe considerarse asistido, no universal.",
        "CAD drawings can vary widely in layers, blocks, units, polylines, precision, and drafting conventions. Import does not automatically clean the file or convert it by itself into a BIM model. The current workflow has been validated with only a limited number of examples and should be considered assisted, not universal.",
    )))
    layout.addStretch(1)
    return tab


def build_workflow_tab():
    tab, layout = _scroll_tab()
    layout.addWidget(_label(i18n.bi("Flujo recomendado para un modelo rapido", "Recommended quick-model workflow"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Este flujo resume la forma de trabajo que se ha probado hasta ahora. Puede adaptarse al dibujo disponible y no obliga a utilizar todas las herramientas en todos los proyectos.",
        "This workflow summarizes the approach tested so far. It can be adapted to the available drawing and does not require every tool to be used on every project.",
    )))

    steps = [
        ("import_cad_reference.svg", i18n.bi("1. Importar y seleccionar informacion", "1. Import and select information"), i18n.bi(
            "Importe DWG/DXF, seleccione la escala/unidad del dibujo original y las capas que realmente necesita.",
            "Import DWG/DXF, select the original drawing scale/unit, and the layers you actually need.",
        )),
        ("centerlines_from_selection.svg", i18n.bi("2. Preparar centros de paredes", "2. Prepare wall centerlines"), i18n.bi(
            "Seleccione la capa de paredes y ejecute FA Centros desde seleccion para obtener la geometria base que utilizara el muro BIM.",
            "Select the wall layer and run FA Centerlines from Selection to obtain the base geometry used by the BIM wall.",
        )),
        ("create_windows_bim.svg", i18n.bi("3. Preparar centros de ventanas", "3. Prepare window centerlines"), i18n.bi(
            "Seleccione la capa de ventanas y ejecute FA Centros de ventanas. Revise que cada eje represente la ventana esperada.",
            "Select the window layer and run FA Window Centerlines. Verify that each centerline represents the expected window.",
        )),
        ("create_doors_bim.svg", i18n.bi("4. Preparar centros de puertas", "4. Prepare door centerlines"), i18n.bi(
            "Seleccione la capa de puertas y ejecute FA Centros de puertas. Revise especialmente puertas cercanas a esquinas o encuentros de muros.",
            "Select the door layer and run FA Door Centerlines. Pay special attention to doors near corners or wall junctions.",
        )),
        ("opening_only.svg", i18n.bi("5. Cerrar buques cuando sea necesario", "5. Close openings when needed"), i18n.bi(
            "Si el Sketch de pared conserva vacios de los simbolos CAD, use FA Cerrar buques para completar los tramos validados sin alterar el resto de la pared.",
            "If the wall Sketch still contains gaps from CAD symbols, use FA Close Openings to complete validated wall segments without altering the rest of the wall.",
        )),
        ("walls_from_centerlines.svg", i18n.bi("6. Crear paredes BIM", "6. Create BIM walls"), i18n.bi(
            "Genere las paredes BIM desde los Sketches preparados y revise espesor, altura, nivel y continuidad.",
            "Generate BIM walls from the prepared Sketches and review thickness, height, level, and continuity.",
        )),
        ("create_doors_bim.svg", i18n.bi("7. Crear puertas y ventanas BIM", "7. Create BIM doors and windows"), i18n.bi(
            "Use las herramientas BIM de puertas y ventanas para alojarlas en los muros y comprobar visualmente los buques resultantes.",
            "Use the BIM door and window tools to host them in walls and visually verify the resulting openings.",
        )),
        ("detect_rooms.svg", i18n.bi("8. Crear/identificar Recintos y Espacios BIM", "8. Create/identify Rooms and BIM Spaces"), i18n.bi(
            "Las herramientas de Recintos/Espacios siguen siendo experimentales, pero BIM Space es el objeto previsto para compartir nombre, area, nivel y geometria del recinto con otros Workbenches de ingenieria e instalaciones.",
            "Rooms/Spaces tools are still experimental, but BIM Space is the intended object for sharing room name, area, level, and geometry with other engineering and building-services Workbenches.",
        )),
        ("roof_from_rectangle.svg", i18n.bi("9. Crear techo", "9. Create the roof"), i18n.bi(
            "Dibuje un rectangulo que cubra el perimetro de las paredes y use FA Techo desde rectangulo. A partir de esa huella se generan ejes, cerchas, clavadores y cubierta segun las opciones de la herramienta.",
            "Draw a rectangle covering the wall perimeter and use FA Roof from Rectangle. From that footprint, axes, trusses, purlins, and roof covering are generated according to the tool options.",
        )),
        ("modular_ceiling.svg", i18n.bi("10. Crear cielorraso", "10. Create the ceiling"), i18n.bi(
            "Preferiblemente seleccione uno o varios BIM Spaces y ejecute FA Cielo 600x600. Tambien se aceptan recintos poligonales o rectangulares validos. Defina modulo, cota inferior, espesor, junta y alineacion con luminarias. Si existen luminarias compatibles, la herramienta puede reservar sus celdas sin moverlas.",
            "Preferably select one or more BIM Spaces and run FA 600x600 Ceiling. Valid polygonal or rectangular rooms are also accepted. Set module, underside elevation, thickness, joint, and luminaire alignment. If compatible luminaires exist, the tool can reserve their cells without moving them.",
        )),
    ]
    for icon_name, title, description in steps:
        layout.addWidget(_step(icon_name, title, description))

    layout.addWidget(_label(i18n.bi("Nota sobre el cielorraso", "Ceiling note"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Si no hay una seleccion activa, FA Cielo 600x600 intenta localizar recintos disponibles en el documento y da prioridad a los BIM Spaces. La reticula modular siempre se calcula internamente; su objeto 2D documental permanente es opcional.",
        "If there is no active selection, FA 600x600 Ceiling attempts to find available rooms in the document and gives priority to BIM Spaces. The modular grid is always calculated internally; its permanent documentary 2D object is optional.",
    )))
    layout.addStretch(1)
    return tab


def _toolbar_entries():
    return [
        ("demo_building.svg", i18n.bi("FA Proyecto BIM", "FA BIM Project"), i18n.bi("Demo, FA JSON y Ayuda: crear un modelo de prueba, inspeccionarlo en JSON y recibir comandos JSON controlados desde ChatGPT/MCP.", "Demo, FA JSON, and Help: create a test model, inspect it as JSON, and receive controlled JSON commands from ChatGPT/MCP.")),
        ("import_cad_reference.svg", i18n.bi("FA DWG/DXF y preparacion 2D", "FA DWG/DXF & 2D Prep"), i18n.bi("Importacion CAD, cierre de buques y recuperacion de rotulos de recintos.", "CAD import, opening closure, and room-label collection.")),
        ("centerlines_from_selection.svg", i18n.bi("FA Dibujo 2D", "FA 2D Drawing"), i18n.bi("Herramientas nativas de Sketcher/Draft para crear o corregir la geometria base.", "Native Sketcher/Draft tools for creating or correcting base geometry.")),
        ("building_grid.svg", i18n.bi("FA Estructura BIM", "FA BIM Structure"), i18n.bi("Reticulas/ejes, lineas de centro, paredes, columnas y losa/sitio.", "Grids/axes, centerlines, walls, columns, and slab/site.")),
        ("create_doors_bim.svg", i18n.bi("FA Aberturas BIM", "FA BIM Openings"), i18n.bi("Puertas, ventanas, tipos, tablas y buques asociados a sus muros.", "Doors, windows, types, schedules, and openings associated with their walls.")),
        ("detect_rooms.svg", i18n.bi("FA Recintos (Experimental)", "FA Rooms (Experimental)"), i18n.bi("Deteccion, consulta, nombre y creacion de BIM Spaces. Su generacion sigue en desarrollo, pero los Spaces son esenciales para futuras integraciones con otros Workbenches de ingenieria e instalaciones.", "Detection, inspection, naming, and BIM Space creation. Their generation is still under development, but Spaces are essential for future integration with other engineering and building-services Workbenches.")),
        ("roof_from_rectangle.svg", i18n.bi("FA Techos y cielorrasos", "FA Roofs & Ceilings"), i18n.bi("Techo BIM por ejes, edicion de cerchas y cielorraso modular por recinto/Space.", "Axis-based BIM roof, truss editing, and modular ceiling by room/Space.")),
        ("facilarq.svg", i18n.bi("FA Auxiliares BIM", "FA BIM Utilities"), i18n.bi("Comandos nativos complementarios que no pertenecen al flujo principal.", "Complementary native commands outside the main workflow.")),
    ]


def build_toolbars_tab():
    tab, layout = _scroll_tab()
    layout.addWidget(_label(i18n.bi(
        "Las barras se ordenan por el flujo normal de trabajo, no por el orden historico en que se desarrollaron las herramientas.",
        "Toolbars are ordered by the normal workflow, not by the historical order in which tools were developed.",
    )))
    for icon_name, title, description in _toolbar_entries():
        layout.addWidget(_step(icon_name, title, description))
    layout.addStretch(1)
    return tab


def build_demo_tab():
    tab, layout = _scroll_tab()
    layout.addWidget(_label(i18n.bi("Demo edificio", "Building Demo"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "La Demo crea un documento nuevo y sirve para aprender y comprobar el flujo de Facil Arquitectura sin preparar un archivo previo.",
        "The Demo creates a new document and is intended to learn and test the Facil Arquitectura workflow without preparing a source file.",
    )))
    layout.addWidget(_label(i18n.bi(
        "Demo fija: siempre genera la misma casa canonica de 6 x 8 m. Demo aleatoria: cambia dimensiones/distribucion dentro de reglas controladas. La misma semilla reproduce exactamente la misma variante.",
        "Fixed Demo: always generates the same canonical 6 x 8 m house. Random Demo: changes dimensions/layout within controlled rules. The same seed reproduces exactly the same variant.",
    )))
    layout.addWidget(_label(i18n.bi(
        "Puede ejecutarse completa o guiada paso a paso. Ambos modos usan la misma especificacion y las mismas herramientas del Workbench.",
        "It can run as a complete build or as a guided step-by-step demonstration. Both modes use the same specification and the same Workbench tools.",
    )))
    layout.addWidget(_label(i18n.bi(
        "La Demo demuestra el tipo de modelo que FA puede producir y sirve como prueba reproducible del Workbench. No demuestra que cualquier DWG arbitrario pueda procesarse automaticamente.",
        "The Demo demonstrates the type of model FA can produce and serves as a reproducible Workbench test. It does not prove that any arbitrary DWG can be processed automatically.",
    ), bold=True))
    layout.addWidget(_label(i18n.bi(
        "FA JSON tiene Salida, Entrada y Resultado. Salida permite ver/copiar/guardar el snapshot. Entrada permite pegar comandos desde ChatGPT/MCP, validarlos, ejecutar Dry-run y aplicarlos tras confirmacion. El Ejemplo crea tres arboles junto a la Demo mediante create_site_object. Resultado incluye Copiar resultado/error para devolver a ChatGPT tanto exitos como fallos estructurados.",
        "FA JSON has Output, Input, and Result. Output lets you view/copy/save the snapshot. Input lets you paste commands from ChatGPT/MCP, validate them, run Dry-run, and apply them after confirmation. Example creates three trees beside the Demo through create_site_object. Result includes Copy result/error so both successes and structured failures can be pasted back into ChatGPT.",
    )))
    layout.addStretch(1)
    return tab


def build_info_tab():
    tab, layout = _scroll_tab()
    layout.addWidget(_label("Facil Arquitectura", bold=True))
    layout.addWidget(_label(i18n.bi(
        "Facil Arquitectura es un Workbench complementario para FreeCAD orientado a obtener con rapidez un modelo arquitectonico BIM sencillo a partir de dibujos 2D existentes o de geometria creada directamente en FreeCAD.",
        "Facil Arquitectura is a complementary FreeCAD Workbench intended to quickly obtain a simple architectural BIM model from existing 2D drawings or geometry created directly in FreeCAD.",
    )))
    layout.addWidget(_label(i18n.bi("Que no pretende hacer", "What it is not intended to do"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "No pretende sustituir el trabajo de un arquitecto, dibujante especializado, modelador BIM ni las herramientas arquitectonicas existentes en FreeCAD. Tampoco pretende convertir cualquier DWG automaticamente en un modelo terminado.",
        "It is not intended to replace the work of an architect, professional drafter, BIM modeler, or the architectural tools already available in FreeCAD. It is also not intended to automatically convert any DWG into a finished model.",
    )))
    layout.addWidget(_label(i18n.bi("Para que resulta especialmente util", "Where it is especially useful"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Su objetivo es simplificar tareas repetitivas para personas que necesitan un modelo rapido y suficientemente organizado para continuar el trabajo de ingenieria. En particular, los BIM Spaces permiten que otros Workbenches de ingenieria e instalaciones reutilicen la misma identidad del recinto, su nombre, area, nivel y geometria sin crear recintos paralelos.",
        "Its purpose is to simplify repetitive tasks for people who need a quick, sufficiently organized model to continue engineering work. In particular, BIM Spaces allow other engineering and building-services Workbenches to reuse the same room identity, name, area, level, and geometry without creating parallel rooms.",
    )))
    layout.addWidget(_label(i18n.bi("Estado de Recintos/Espacios BIM", "Rooms/BIM Spaces status"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Las herramientas para detectar y generar Recintos/Espacios BIM se consideran experimentales y pueden requerir revision manual. Sin embargo, BIM Space es una pieza esencial de la arquitectura prevista para comunicar Facil Arquitectura con otros Workbenches de ingenieria e instalaciones.",
        "Room/BIM Space detection and generation tools are considered experimental and may require manual review. However, BIM Space is an essential part of the intended architecture for connecting Facil Arquitectura with other engineering and building-services Workbenches.",
    )))
    layout.addWidget(_label(i18n.bi("Desarrollo asistido por inteligencia artificial", "AI-assisted development"), bold=True))
    layout.addWidget(_label(i18n.bi(
        "Facil Arquitectura ha sido desarrollada en gran parte mediante herramientas de inteligencia artificial, bajo direccion humana. Su codigo, arquitectura y comportamiento requieren revision y validacion por programadores profesionales antes de considerarla apta para entornos de produccion, uso critico o distribucion amplia.",
        "Facil Arquitectura has been developed largely using artificial intelligence tools under human direction. Its source code, architecture, and behavior require review and validation by professional software developers before it should be considered suitable for production environments, critical use, or broad distribution.",
    )))
    layout.addWidget(_label(i18n.bi("Version: %s" % VERSION, "Version: %s" % VERSION)))
    layout.addWidget(_label(i18n.bi("Build: %s" % BUILD_ID, "Build: %s" % BUILD_ID)))
    layout.addWidget(_label(i18n.bi("FreeCAD objetivo: 1.1.3", "Target FreeCAD: 1.1.3")))
    layout.addWidget(_label(i18n.bi("Autor: Marco Vinicio Mora Fallas", "Author: Marco Vinicio Mora Fallas")))
    layout.addStretch(1)
    return tab


def build_help_dialog(parent=None):
    dialog = QtWidgets.QDialog(parent or _main_window())
    dialog.setWindowTitle(i18n.bi("Facil Arquitectura - Ayuda", "Facil Arquitectura - Help"))
    dialog.setWindowIcon(QtGui.QIcon(HELP_ICON_PATH))
    dialog.resize(940, 700)
    layout = QtWidgets.QVBoxLayout(dialog)
    tabs = QtWidgets.QTabWidget()
    tabs.addTab(build_first_steps_tab(), QtGui.QIcon(_icon("demo_building.svg")), i18n.bi("Primeros pasos", "Getting Started"))
    tabs.addTab(build_cad_tab(), QtGui.QIcon(_icon("import_cad_reference.svg")), "DWG / DXF")
    tabs.addTab(build_workflow_tab(), QtGui.QIcon(_icon("walls_from_centerlines.svg")), i18n.bi("Flujo de trabajo", "Workflow"))
    tabs.addTab(build_toolbars_tab(), QtGui.QIcon(HELP_ICON_PATH), i18n.bi("Barras", "Toolbars"))
    tabs.addTab(build_demo_tab(), QtGui.QIcon(_icon("demo_building.svg")), i18n.bi("Demo", "Demo"))
    tabs.addTab(build_info_tab(), QtGui.QIcon(_icon("facilarq.svg")), i18n.bi("Informacion", "Information"))
    layout.addWidget(tabs, 1)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return dialog


def show_help_dialog(parent=None):
    dialog = build_help_dialog(parent)
    if hasattr(dialog, "exec"):
        dialog.exec()
    else:
        dialog.exec_()
    return dialog


__all__ = ["HELP_ICON_PATH", "build_help_dialog", "show_help_dialog"]
