# Archivo: ARQUITECTURA.md
**Proposito:** Definir la arquitectura conceptual del Workbench y la relacion entre sus componentes HVAC.  
**Fecha y hora de version:** 2026-08-26 11:55 America/Costa_Rica  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Arquitectura Conceptual

## Enfoque general

MEPWorkbenchCR se estructura como un Workbench modular de FreeCAD. El alcance inicial es HVAC, pero la arquitectura se disena para habilitar expansion MEP sin reescritura estructural.

## Filosofia MVP (actual)

- Inspiracion de flujo: Iluminacion de ElectricCR.
- Centro del MVP: Recinto HVAC + Etiqueta HVAC + Evaporadora + Cobertura.
- Segunda capa operativa: Proyecto HVAC, Condensadora, Rutas, Puertos, Validacion.

## Capas principales

- Capa de Workbench: registro de comandos, barras de herramientas y menu.
- Capa de dominio HVAC: reglas de negocio, calculo, cobertura, validaciones y relaciones entre objetos.
- Capa de objetos del documento: entidades parametricas en FreeCAD (proyecto, recinto, equipos, rutas, puertos, etiquetas).
- Capa de recursos: iconos, UI y material de apoyo visual.
- Capa de documentacion: reglas, flujo, convenciones y roadmap.

## Modulos principales HVAC

- Proyecto HVAC: concentra variables climaticas y define factor de referencia.
- Recinto HVAC: unidad base y punto de entrada principal del usuario.
- Etiqueta HVAC: salida protagonista sobre el recinto (carga y cobertura).
- Evaporadora: equipo interior concreto asociado visualmente al recinto.
- HVAC Quick Calculation: hoja resumen de resultados por recinto.
- Condensadora: equipo 3D independiente que consolida evaporadoras.
- Ruta HVAC: conexion tecnica entre puertos segun tipo de servicio.
- Puerto HVAC: punto obligatorio de conexion y validacion de compatibilidad.

## Relacion entre componentes

- Recinto HVAC -> calcula carga requerida.
- Evaporadora -> aporta capacidad instalada del recinto.
- Etiqueta HVAC -> refleja carga y cobertura del recinto en tiempo real.
- Hoja HVAC Quick Calculation -> consolida calculo rapido de todas las areas.
- Proyecto HVAC -> influye en factor climatico (soporte transversal).
- Condensadora/Ruta/Puertos -> fase posterior de sistema completo.

## Modelo Areas y SubAreas por disciplina (proxima base)

- `Area` define el perfil del recinto y puede ser de cualquier forma.
- `SubArea` define zonas internas de calculo/criterio por disciplina.
- Un recinto puede tener varias subareas de una misma disciplina.
- Un recinto puede tener subareas de multiples disciplinas al mismo tiempo (Iluminacion, Incendio, HVAC).
- Regla de evaluacion base: priorizar subareas de la disciplina activa; fallback al Area del recinto.

## Rol del Loader

- El loader permite cargar o recargar el Workbench sin reiniciar FreeCAD.
- Debe facilitar ciclos de desarrollo y validacion rapida.
- Debe minimizar estados inconsistentes al recargar modulos.

## Objeto unico con representacion 2D y 3D

- Cada equipo debe conservar una unica identidad semantica; su simbolo 2D y su geometria 3D son representaciones del mismo objeto y comparten Placement y propiedades.
- La planta 2D debe ser un medio sencillo de trabajo: colocar, seleccionar, mover, rotar y editar equipos mediante simbologia tecnica cuando resulte mas eficiente que manipular el modelo 3D.
- La representacion 3D se utiliza para visualizacion, altura de montaje, coordinacion, interferencias y comprobacion espacial.
- Los cambios realizados desde el flujo 2D deben reflejarse en el 3D sin crear una segunda instancia que deba sincronizarse manualmente.
- La etiqueta HVAC actua como capa informativa de resultados sobre el recinto.
- Todo elemento calculado, dimensionado o disenado por el Workbench debe poder producir una representacion documental 2D comprensible, identificable y exportable.
- Si FreeCAD/BIM requiere perfiles, objetos Base, Hosts u otros auxiliares, estos se consideran dependencias vinculadas y no una segunda identidad del equipo.

## Puertos y conexiones

- Cada equipo relevante debe exponer puertos tecnicos.
- Las rutas se crean sobre puertos, no sobre geometria suelta.
- La validacion de tipo de puerto es obligatoria para evitar conexiones invalidas.
- Las conexiones deben mantener trazabilidad de origen, destino y tipo de servicio.

## Preparacion para crecimiento futuro

- Estructura modular por disciplina para expandir a Agua, Sanitario y Electrico.
- Reutilizacion de logica de seleccion, rutas y conexion inspirada en ElectricCR.
- Separacion clara entre reglas de negocio y presentacion para facilitar mantenimiento.
- Base compatible con FreeCAD 1.0.2 y preparada para ajustes en 1.1.

## Disciplina Sanitario - base v0.5.0 2026-08-26

Se incorpora una disciplina sanitaria independiente del GUI, ubicada en `MEP/sanitary/`. El caso inicial de referencia es Esparza y el alcance se limita a tanque septico, FAFA post-tanque y campo de infiltracion por zanjas.

Arquitectura vigente:

```text
MEP/sanitary/
|-- models.py            # resultados y mensajes JSON-compatible
|-- septic.py            # tanque septico + referencias comerciales
|-- fafa.py              # TRH + porosidad + COV + referencias comerciales
|-- infiltration.py      # prueba T, Tabla 2 T->Vp, area y zanjas
|-- system.py            # orquestador + geometry_spec neutral
|-- layout.py            # acomodo rectangular neutral de zanjas
|-- freecad_adapter.py   # preview experimental, dry_run por defecto
|-- freecad_objects.py   # Part::FeaturePython experimentales
|-- documentation.py     # planta/seccion neutral + SVG
|-- case.py              # validacion segura de entradas
`-- examples/
    `-- esparza_input_template.json
|-- boundary.py       # contrato geometrico Boundary2D independiente de FreeCAD
|-- spatial.py        # validacion de propiedad, edificio y areas disponibles
```

Reglas:

- El nucleo no depende de `FreeCADGui`, Qt ni del documento FreeCAD.
- `system.py` produce un `geometry_spec` neutral para que el adaptador no duplique formulas.
- `freecad_adapter.py` importa `FreeCAD` y `Part` solo cuando se solicita escritura; `dry_run=True` no modifica documentos.
- El adaptador de preview y los `Part::FeaturePython` de `freecad_objects.py` son experimentales hasta validacion real; no se exponen aun en GUI.
- `documentation.py` genera planta/seccion JSON-compatible y SVG desde el mismo resultado, sin duplicar formulas.
- `case.py` impide calcular plantillas incompletas y devuelve faltantes de forma estructurada.
- La Tabla 2 del Anexo 3 del Decreto 42075-S-MINAE esta codificada para T=2..24 min/cm. Para T no entero se usa por defecto la fila entera superior como seleccion conservadora.
- Se exigen al menos dos pruebas de infiltracion y se adopta como criterio la prueba mas lenta.
- El FAFA mantiene TRH=8 h y porosidad=0.70 como preset tecnico configurable; la DBO post-tanque sigue siendo opcional y, si falta, se marca como preliminar.
- Las referencias comerciales son solo candidatos posteriores al calculo; no son seleccion automatica de compra.
- Toda integracion definitiva debe producir planta y seccion 2D comprensibles y exportables desde las mismas propiedades autoritativas.

Estado: `NUCLEO v0.4.1 IMPLEMENTADO / 22 PRUEBAS PYTHON APROBADAS / VALIDACION FREECAD REAL PENDIENTE`.

### Referencias espaciales sanitarias

La disciplina sanitaria introduce `Boundary2D` como contrato geometrico neutral. El nucleo recibe poligonos cerrados y no conoce Draft, Sketcher, Part ni GUI. El adaptador FreeCAD sera responsable de extraer puntos XY desde Draft Wire, Sketch, Part Wire, Part Face, rectangulos, poligonos o conjuntos de lineas que formen un contorno.

Roles iniciales: `PROPERTY_BOUNDARY`, `BUILDING_FOOTPRINT`, `TANKS_AREA` y `DRAINAGE_AREA`. Las areas dibujadas son restricciones de entrada; tanque, FAFA y zanjas son resultados separados.
