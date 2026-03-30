# Archivo: ARQUITECTURA.md
**Proposito:** Definir la arquitectura conceptual del Workbench y la relacion entre sus componentes HVAC.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
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
- Condensadora: equipo 3D independiente que consolida evaporadoras.
- Ruta HVAC: conexion tecnica entre puertos segun tipo de servicio.
- Puerto HVAC: punto obligatorio de conexion y validacion de compatibilidad.

## Relacion entre componentes

- Recinto HVAC -> calcula carga requerida.
- Evaporadora -> aporta capacidad instalada del recinto.
- Etiqueta HVAC -> refleja carga y cobertura del recinto en tiempo real.
- Proyecto HVAC -> influye en factor climatico (soporte transversal).
- Condensadora/Ruta/Puertos -> fase posterior de sistema completo.

## Rol del Loader

- El loader permite cargar o recargar el Workbench sin reiniciar FreeCAD.
- Debe facilitar ciclos de desarrollo y validacion rapida.
- Debe minimizar estados inconsistentes al recargar modulos.

## Modelo 3D con simbologia 2D

- Los equipos se modelan como objetos 3D para coordinacion espacial.
- La representacion 2D se usa para lectura tecnica en planta y documentacion.
- La etiqueta HVAC actua como capa informativa de resultados sobre el recinto.

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
