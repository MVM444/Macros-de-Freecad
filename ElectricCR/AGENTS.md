# ElectricCR - Instrucciones para agentes de desarrollo

**Proposito:** Definir las reglas permanentes para ChatGPT, Codex y otros agentes que trabajen dentro de `ElectricCR/`.

**Version:** 2026-08-06 12:35, America/Costa_Rica.

**Alcance:** Este archivo aplica a todos los archivos y subdirectorios contenidos en `ElectricCR/`, salvo que exista un `AGENTS.md` mas especifico en un subdirectorio.

## Orden obligatorio de lectura

Antes de analizar o modificar el proyecto, leer en este orden:

1. `AGENTS.md`
2. `ESTADO_PROYECTO.md`
3. `DECISIONES_TECNICAS.md`
4. `TAREA_ACTUAL.md`
5. El codigo y los recursos relacionados con la tarea

Al finalizar, actualizar `RESULTADO_CODEX.md`. Solo actualizar `HISTORIAL_CAMBIOS.md` cuando un cambio haya sido probado y aceptado.

## Entorno objetivo

- Version objetivo: FreeCAD 1.1.1.
- Sistema principal: Windows.
- Las macros se encuentran dentro del directorio de macros de FreeCAD o en sus subdirectorios.
- Utilizar Python y PySide compatibles con FreeCAD 1.1.1.
- Mantener compatibilidad razonable con documentos ElectricCR existentes.

## Reglas antes de programar

- Buscar primero en Internet si existe un programa, Workbench, macro de FreeCAD, complemento o patron oficial que resuelva un problema similar.
- Revisar tambien el propio repositorio, en especial `MEPWorkbenchCR`, antes de crear una solucion nueva.
- Explicar la causa probable y proponer un plan antes de modificar archivos funcionales.
- No asumir que todos los objetos son `Part::Feature`; verificar `TypeId`, `Proxy`, `LinkedObject`, propiedades y estructura real.
- No modificar archivos ajenos al alcance indicado en `TAREA_ACTUAL.md`.
- No eliminar funciones, propiedades, grupos, recursos ni compatibilidad existente sin autorizacion expresa.
- Preferir cambios pequenos, reversibles y verificables.

## Reglas de codigo

- En codigo fuente, comentarios, identificadores, nombres internos, propiedades, expresiones y nombres de hojas o grupos, utilizar caracteres ASCII sin tildes ni caracteres especiales cuando puedan causar problemas de codificacion.
- Mantener encabezado en cada macro o modulo modificado con descripcion, instrucciones importantes, fecha, hora y revision.
- Comentar claramente la logica no evidente.
- Mostrar mensajes de depuracion en la consola de FreeCAD con prefijos claros y consistentes.
- Registrar como minimo: objeto procesado, tipo detectado, propiedad modificada, valor anterior, valor nuevo, resultado y motivo de omision.
- Usar transacciones de documento para cambios realizados sobre varios objetos.
- Evitar ciclos de recompute, cambios recursivos en `onChanged` y reasignaciones repetitivas de `App::Link`.
- No ejecutar automaticamente codigo generado fuera del flujo normal de la herramienta.

## Reglas para objetos con 2D y 3D

- No usar `Placement.Base.z` como altura de instalacion cuando el mismo objeto contiene un simbolo 2D que debe permanecer en planta.
- Diferenciar siempre entre cota base del nivel y altura relativa de instalacion.
- Conservar la posicion XY, la rotacion y la pertenencia a grupos al cambiar la altura de instalacion.
- Para `App::Link`, verificar si la altura pertenece al maestro vinculado antes de escribir solamente una propiedad informativa en el enlace.
- Para objetos `FeaturePython`, forzar de manera controlada `touch()` y `recompute()` cuando la geometria dependa de una propiedad.
- No duplicar la logica de MEPWorkbenchCR si ya existe una funcion segura de sincronizacion o reasignacion de maestro.

## Pruebas minimas

Toda modificacion funcional debe probar, cuando corresponda:

- Un sensor de incendio directo creado por `ColocarDetectores_NFPA.FCMacro`.
- Un dispositivo ElectricCR creado como `App::Link`.
- Una luminaria con simbolo 2D.
- Un equipo HVAC de MEPWorkbenchCR.
- Un objeto sencillo con `Placement` y sin simbolo 2D.
- Cambio absoluto y cambio por delta.
- Rotacion sin perder orientaciones 3D existentes.
- Documento guardado, cerrado y reabierto.
- Undo y redo mediante transaccion de FreeCAD.

## Informe final

`RESULTADO_CODEX.md` debe indicar:

- Busqueda previa realizada.
- Causa confirmada.
- Archivos revisados y modificados.
- Decisiones aplicadas.
- Pruebas ejecutadas y resultados.
- Mensajes de consola relevantes.
- Riesgos, limitaciones y pendientes.

No declarar una tarea como terminada si no se ejecutaron pruebas dentro de FreeCAD o si las pruebas requieren validacion manual pendiente.