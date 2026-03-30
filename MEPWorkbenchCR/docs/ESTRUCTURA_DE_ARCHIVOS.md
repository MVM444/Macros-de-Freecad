# Archivo: ESTRUCTURA_DE_ARCHIVOS.md
**Proposito:** Definir la estructura propuesta de carpetas y la relacion entre codigo, recursos y documentacion.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Estructura de Archivos Propuesta

## Arbol de referencia

```text
MEPWorkbenchCR/
|- Init.py
|- InitGui.py
|- README.md
|- docs/
|  |- README_DOCS.md
|  |- ARQUITECTURA.md
|  |- REGLAS_HVAC.md
|  |- FLUJO_DE_TRABAJO.md
|  |- CONVENCIONES.md
|  |- PROBLEMAS_RECURRENTES.md
|  |- ROADMAP.md
|  |- ESTRUCTURA_DE_ARCHIVOS.md
|  `- GLOSARIO.md
|- MEP/
|  |- __init__.py
|  |- hvac/
|  |  |- __init__.py
|  |  |- hvac_project.py
|  |  |- hvac_space.py
|  |  |- hvac_equipment.py
|  |  |- hvac_condensing.py
|  |  |- hvac_route.py
|  |  |- hvac_ports.py
|  |  `- hvac_label.py
|  `- utils/
|     |- __init__.py
|     `- selection.py
`- resources/
   |- icons/
   `- ui/
```

## Ubicacion de Init.py e InitGui.py

- `Init.py`: punto de entrada basico para descubrimiento del Workbench.
- `InitGui.py`: registro de comandos, barras y menu del Workbench.

## Modulos HVAC

- `hvac_project.py`: datos climaticos y factor de proyecto.
- `hvac_space.py`: recintos y calculo de carga termica.
- `hvac_equipment.py`: evaporadoras y capacidad instalada.
- `hvac_condensing.py`: condensadoras y validacion global.
- `hvac_route.py`: rutas por tipo de servicio HVAC.
- `hvac_ports.py`: puntos de conexion y validaciones de puertos.
- `hvac_label.py`: etiquetas informativas de carga y cobertura.

## Recursos

- `resources/icons/`: iconografia de Workbench y comandos.
- `resources/ui/`: archivos de interfaz y activos visuales de apoyo.

## Relacion codigo vs documentacion

- `MEP/` define implementacion tecnica.
- `docs/` define reglas y decisiones funcionales.
- Toda regla establecida en `docs/` debe reflejarse en `MEP/`.
- Todo cambio relevante en `MEP/` debe dejar trazabilidad en `docs/`.
