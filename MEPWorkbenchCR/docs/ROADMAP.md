# Archivo: ROADMAP.md
**Proposito:** Definir el plan evolutivo del proyecto desde MVP HVAC hacia una plataforma MEP.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Roadmap del Proyecto

## Fase 1: MVP HVAC

- Recintos como base del calculo y del flujo UX.
- Comando principal para crear/actualizar recintos desde poligonos y grupo Areas.
- Etiquetas HVAC como salida protagonista del recinto.
- Evaporadoras concretas para insercion visual rapida.
- Cobertura por recinto visible en etiqueta.
- Calculo HVAC con actualizacion automatica de etiquetas.
- Proyecto/condensadora/rutas como segunda capa operativa.

## Fase 2: Rutas mejoradas

- Consolidar toolbar secundaria de sistema (proyecto, condensadora, rutas, validacion).
- Reglas de trazado mas robustas por tipo de ruta.
- Validaciones avanzadas de continuidad y compatibilidad.
- Mejora de control de niveles y coordinacion espacial.
- Integracion de patrones de seleccion y conexion tipo ElectricCR.

## Fase 3: Biblioteca de equipos y simbolos

- Catalogo inicial de evaporadoras y condensadoras.
- Parametros tecnicos por familia de equipo.
- Simbologia 2D normalizada por tipo de equipo.
- Reglas de representacion coordinada 3D/2D.

## Fase 4: Condensados extendido

- Modelado detallado de rutas de drenaje.
- Verificacion de pendiente minima y continuidad.
- Reglas de descarga por sistema y por zona.

## Fase 5: Agua y sanitario

- Base de objetos y rutas para redes hidraulicas.
- Definicion de puertos y reglas propias de la disciplina.
- Convivencia de HVAC con agua y sanitario en el mismo entorno.

## Fase 6: Expansion MEP

- Integracion progresiva de Electrico, HVAC, Agua y Sanitario.
- Convenciones unificadas de rutas, puertos y validaciones.
- Estandarizacion de reportes tecnicos por disciplina y por sistema.
- Consolidacion como proyecto open source publico de referencia.

## Criterios de avance entre fases

- Reglas funcionales documentadas.
- Flujo de trabajo estable en FreeCAD.
- Riesgos recurrentes mitigados y registrados.
- Compatibilidad mantenida con FreeCAD 1.0.2 y preparada para 1.1.
