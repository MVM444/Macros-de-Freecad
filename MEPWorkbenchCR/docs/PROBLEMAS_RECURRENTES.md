# Archivo: PROBLEMAS_RECURRENTES.md
**Proposito:** Registrar riesgos tecnicos frecuentes en FreeCAD y definir acciones de mitigacion para HVAC.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Problemas Recurrentes y Mitigacion

## Seleccion de subelementos en lugar de objetos completos

- Problema: el usuario selecciona caras, aristas o vertices en vez de objeto base.
- Riesgo: asociaciones incompletas de recinto, equipo o ruta.
- Mitigacion: normalizar seleccion al objeto contenedor y validar tipo antes de operar.

## App::Link y comportamiento heredado

- Problema: objetos vinculados no se comportan igual que objetos directos.
- Riesgo: perdida de referencias y lecturas inconsistentes de propiedades.
- Mitigacion: desreferenciar enlaces de forma controlada y validar objeto origen.

## Desfase entre 3D y 2D

- Problema: posicion de simbolos o etiquetas no coincide con objeto 3D.
- Riesgo: interpretacion incorrecta en revision de planos.
- Mitigacion: regla unica de posicionamiento y actualizacion al recomputar.

## Perdida de asociacion de puertos

- Problema: puertos quedan sin relacion valida tras cambios de objeto o recarga.
- Riesgo: rutas invalidas o sistema no trazable.
- Mitigacion: sanitizar puertos, validar tipo de puerto y registrar origen-destino.

## Rutas sin recinto o sin conexion valida

- Problema: rutas creadas sin contexto tecnico real.
- Riesgo: documentacion de red inconsistente.
- Mitigacion: bloquear validacion final cuando falte origen, destino o compatibilidad.

## Conflictos de altura entre disciplinas

- Problema: alturas de HVAC, electrico e hidraulico compiten en el mismo volumen.
- Riesgo: interferencias constructivas.
- Mitigacion: parametrizar niveles por proyecto y reservar bandas de altura por disciplina.

## Recompute excesivo y ciclos de dependencias

- Problema: cambios encadenados en propiedades generan recompute inestable.
- Riesgo: degradacion de rendimiento o errores de acceso.
- Mitigacion: usar guardas de reentrada, evitar ciclos de links y limitar escritura en eventos.

## Inconsistencia de factor climatico

- Problema: formula produce resultados no esperados para altitud o humedad extrema.
- Riesgo: sobredimensionamiento o subdimensionamiento preliminar.
- Mitigacion: definir regla explicita de tendencia fisica y permitir ajuste manual controlado.

