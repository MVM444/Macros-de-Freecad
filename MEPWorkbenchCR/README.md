# Archivo: README.md
**Proposito:** Presentar el proyecto MEPWorkbenchCR, su alcance inicial HVAC y su direccion de crecimiento MEP.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# MEPWorkbenchCR

MEPWorkbenchCR es un Workbench de FreeCAD enfocado inicialmente en HVAC para oficinas, con vision de evolucion a plataforma MEP. El proyecto se define como modular, expandible, publico y open source.

## Alcance actual

- MVP centrado en flujo de recintos, inspirado en Iluminacion de ElectricCR.
- Recintos HVAC generados/actualizados desde poligonos o grupo Areas.
- Calculo de carga por recinto con actualizacion automatica de etiquetas.
- Insercion de evaporadoras concretas con asignacion rapida a recinto.
- Cobertura por recinto visible en etiqueta (capacidad instalada / carga).
- Condensadoras, rutas y puertos mantenidos como segunda capa operativa.

## Enfoque HVAC

- El recinto es la unidad base de calculo.
- La etiqueta del recinto es el resultado principal para lectura tecnica.
- La evaporadora se coloca visualmente y responde al calculo del recinto.
- El factor climatico se expresa principalmente en BTU/h por m2 y secundariamente en W/m2.
- Condensadora y rutas no son paso inicial del MVP, sino fase posterior.

## Flujo MVP recomendado

1. Seleccionar poligonos o grupo `Areas`.
2. Crear/actualizar recintos HVAC.
3. Calcular HVAC en modo rapido (si viene de seleccion de Areas).
4. Ver etiquetas actualizadas de inmediato sobre recintos.
5. Revisar hoja `HVAC Quick Calculation` creada dentro del grupo del proyecto.
6. Insertar evaporadora concreta.
7. Revisar cobertura por recinto.

## Estructura de proyecto al iniciar

- `Crear Proyecto HVAC` crea un grupo raiz en ingles: `HVAC Air and Ventilation`.
- Todos los objetos HVAC relevantes (proyecto, recintos, etiquetas, equipos, rutas y hoja de calculo) se organizan dentro de ese grupo.

## Filosofia del Workbench

- Priorizar decisiones tecnicas trazables y reglas claras de modelado.
- Mantener compatibilidad con FreeCAD 1.0.2 y preparacion para FreeCAD 1.1.
- Evitar deuda tecnica temprana mediante documentacion y convenciones estrictas.
- Separar claramente logica de dominio HVAC, interfaz y recursos.
- Preparar base reutilizable para disciplinas futuras MEP.

## Estado actual

- Estado de planificacion y definicion de base documental.
- Reglas HVAC iniciales definidas para orientar desarrollo incremental.
- Arquitectura propuesta orientada a objetos parametricos y flujo de trabajo reproducible.
- Enfoque de integracion futura con logica tipo ElectricCR para rutas, seleccion y conexion.

## Documentacion del proyecto

- Punto de entrada documental: [docs/README_DOCS.md](docs/README_DOCS.md)
- Carpeta de documentacion: `docs/`

## Vision futura MEP

- Extender HVAC hacia Agua, Sanitario y Electrico bajo una base comun.
- Compartir criterios de rutas, puertos y validaciones entre disciplinas.
- Consolidar una libreria tecnica de objetos 3D con simbologia 2D sincronizada.
- Mantener el proyecto abierto a colaboracion y contribuciones externas.
