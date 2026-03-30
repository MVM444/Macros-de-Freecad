# Archivo: README.md
**Proposito:** Presentar el proyecto MEPWorkbenchCR, su alcance inicial HVAC y su direccion de crecimiento MEP.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# MEPWorkbenchCR

MEPWorkbenchCR es un Workbench de FreeCAD enfocado inicialmente en HVAC para oficinas, con vision de evolucion a plataforma MEP. El proyecto se define como modular, expandible, publico y open source.

## Alcance actual

- Implementacion inicial centrada en HVAC.
- Recintos HVAC generados desde poligonos y grupos de Areas/Recintos.
- Calculo de cargas termicas por recinto (modo rapido y modo preciso).
- Gestion de evaporadoras y condensadoras como objetos tecnicos del sistema.
- Rutas HVAC por tipo de servicio (refrigerante, electrica, condensados).
- Puntos de conexion obligatorios para asegurar consistencia de red.
- Etiquetado tecnico por recinto con carga y cobertura.

## Enfoque HVAC

- El recinto es la unidad base de calculo.
- El equipo responde al calculo del recinto, no al reves.
- La condensadora valida cobertura total del conjunto de evaporadoras.
- Las rutas representan conexiones funcionales entre puertos.
- El factor climatico se expresa principalmente en BTU/h por m2 y secundariamente en W/m2.

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
