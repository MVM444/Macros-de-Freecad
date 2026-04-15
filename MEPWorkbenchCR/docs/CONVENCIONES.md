# Archivo: CONVENCIONES.md
**Proposito:** Definir convenciones de nombres, modularidad y criterio tecnico para desarrollo sostenible.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Convenciones del Proyecto

## Convenciones de nombres

- Usar nombres tecnicos internos sin tildes ni caracteres especiales.
- Mantener nombres estables y descriptivos para objetos del dominio.
- Usar prefijos consistentes por modulo cuando aplique.
- Evitar abreviaturas ambiguas en nombres de propiedades.

## Convenciones de archivos y rutas

- Nombres de archivo en minuscula con guion bajo cuando sea necesario.
- Estructura modular por disciplina y utilidades compartidas.
- Evitar espacios y caracteres no ASCII en rutas tecnicas internas.
- Mantener separacion clara entre codigo, recursos y documentacion.

## Convenciones de objetos del modelo

- Recinto como entidad principal de calculo.
- Equipos interiores y exteriores como entidades diferenciadas.
- Rutas definidas por tipo de servicio.
- Puertos como entidad obligatoria para conexion.
- Etiquetas como capa de reporte visible del estado del recinto.

## Convencion transversal de Areas y SubAreas

- Esta convencion aplica a HVAC, Electrico, Incendio y futuras disciplinas del ecosistema.
- Area base: puede ser cualquier geometria plana cerrada (no solo rectangulos).
- Area base representa el perfil del recinto.
- SubArea: puede ser cualquier geometria plana cerrada, con preferencia de uso por rectangulos para flujo operativo.
- Un recinto puede contener multiples SubAreas por disciplina (Iluminacion, Incendio, HVAC).
- Debe soportarse mas de una SubArea de la misma disciplina dentro del mismo recinto.
- Regla de prioridad de calculo: `SubAreas > Areas`.
- Fallback: si no hay SubAreas, usar Areas; si no hay Areas pero si hay SubAreas validas, usar SubAreas.

## Convenciones de comentarios futuros

- Comentarios breves y tecnicos.
- Documentar por que se toma una decision, no solo que hace una linea.
- Evitar comentarios redundantes.
- Actualizar comentarios cuando cambie la logica.

## Convenciones de depuracion

- Incluir mensajes de depuracion cuando se programe.
- Usar prefijos de modulo para lectura de consola.
- Evitar ruido excesivo de log en operaciones repetitivas.
- Priorizar mensajes de errores accionables.

## Convenciones de modularidad

- Un modulo debe tener una responsabilidad principal.
- Evitar dependencias circulares entre modulos.
- Reutilizar utilidades comunes para seleccion y conexion.
- Preparar interfaces para integracion futura con logica tipo ElectricCR.

## Reglas de compatibilidad

- Mantener compatibilidad funcional con FreeCAD 1.0.2.
- Preparar validaciones para comportamiento esperado en FreeCAD 1.1.
- Evitar decisiones acopladas a una sola version del entorno.
