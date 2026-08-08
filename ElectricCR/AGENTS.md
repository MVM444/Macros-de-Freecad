# ElectricCR - Instrucciones para agentes de desarrollo

**Proposito:** Definir las reglas permanentes para ChatGPT, Codex y otros agentes que trabajen dentro de `ElectricCR/`.

**Version:** 2026-08-08 11:46, America/Costa_Rica.

**Alcance:** Este archivo aplica a todos los archivos y subdirectorios contenidos en `ElectricCR/`, salvo que exista un `AGENTS.md` mas especifico en un subdirectorio.

## Orden obligatorio de lectura

Antes de analizar o modificar el proyecto, leer en este orden:

1. `AGENTS.md`
2. `ESTADO_PROYECTO.md`
3. `DECISIONES_TECNICAS.md`
4. `FLUJO_GPT_CODEX.md`
5. `TAREA_ACTUAL.md`
6. El codigo y los recursos relacionados con la tarea

Al finalizar, actualizar `RESULTADO_CODEX.md`. Solo actualizar `HISTORIAL_CAMBIOS.md` cuando un cambio haya sido probado, validado funcionalmente cuando corresponda y aceptado.

## Entorno objetivo

- Version objetivo: FreeCAD 1.1.1.
- Sistema principal: Windows.
- Las macros se encuentran dentro del directorio de macros de FreeCAD o en sus subdirectorios.
- Utilizar Python y PySide compatibles con FreeCAD 1.1.1.
- Mantener compatibilidad razonable con documentos ElectricCR existentes.

## Reglas antes de programar

- Buscar primero en Internet si existe un programa, Workbench, macro de FreeCAD, complemento o patron oficial que resuelva un problema similar.
- Revisar tambien el propio repositorio, en especial `ElectricCR`, `MEPWorkbenchCR`, versiones anteriores y macros de la misma familia funcional antes de crear una solucion nueva.
- Explicar la causa probable y proponer un plan antes de modificar archivos funcionales.
- No asumir que todos los objetos son `Part::Feature`; verificar `TypeId`, `Proxy`, `LinkedObject`, propiedades y estructura real.
- No modificar archivos ajenos al alcance indicado en `TAREA_ACTUAL.md`.
- No eliminar funciones, propiedades, grupos, recursos ni compatibilidad existente sin autorizacion expresa.
- Preferir cambios pequenos, reversibles y verificables.

## Control de nuevas macros y cambios generados con IA

No asumir que una solucion nueva es mejor que una existente.

Antes de crear una nueva macro, comando, modulo o variante:

1. Buscar primero dentro del repositorio si ya existe una herramienta que resuelva total o parcialmente el problema.
2. Revisar versiones anteriores, documentacion, resultados y pruebas relacionadas.
3. Determinar si conviene corregir, ampliar o reutilizar una herramienta existente antes de crear otra.
4. Revisar tambien si FreeCAD, algun Workbench, macro o plugin existente ofrece una solucion similar.
5. Si se crea una nueva variante, documentar por que era necesaria y que diferencia funcional aporta.

Evitar crear varias macros paralelas para resolver el mismo problema sin una justificacion tecnica clara.

Una macro que ejecuta sin errores no se considera automaticamente correcta, mejor ni terminada.

El numero de ejecuciones tampoco demuestra por si solo uso operativo: puede corresponder a pruebas, depuracion o intentos repetidos durante desarrollo.

No continuar desarrollando una solucion que se haya desviado del objetivo original sin documentar primero esa desviacion.

No eliminar una version anterior solamente porque exista una version nueva. La sustitucion requiere evidencia de que la nueva solucion cubre los casos funcionales necesarios.

## Clasificacion obligatoria de soluciones

Toda herramienta relevante debe poder evaluarse mediante tres ejes independientes:

### Rol funcional

- NUCLEO
- OPERATIVA
- SOPORTE
- ESPECIALIZADA
- MANTENIMIENTO
- SISTEMA

### Madurez

- ESTABLE
- ACTIVA
- CANDIDATA
- BETA
- REVISAR
- REVISAR-SOLAPAMIENTO
- REVISAR-INTEGRIDAD
- LEGACY-DEPENDENCIA
- LEGACY-REEMPLAZADA
- DESARROLLO
- ARCHIVADA / ARCHIVABLE

### Resultado comprobado

- COMPROBADA
- COMPROBADA-PARCIAL
- PROMETEDORA
- EXPERIMENTAL
- DESVIADA
- DUPLICADA
- INCOMPLETA
- FALLIDA
- ABANDONADA
- POR VERIFICAR
- NO APLICA

Las herramientas nuevas no deben declararse ESTABLES ni COMPROBADAS automaticamente.

Hasta disponer de evidencia suficiente utilizar clasificaciones como `PROMETEDORA`, `EXPERIMENTAL`, `POR VERIFICAR` o `COMPROBADA-PARCIAL`.

Si durante las pruebas se comprueba que el desarrollo no resuelve el objetivo, indicarlo expresamente como `DESVIADA`, `INCOMPLETA`, `FALLIDA`, `DUPLICADA` o `ABANDONADA`, segun corresponda.

Cuando no exista evidencia suficiente, utilizar `POR VERIFICAR` en lugar de inferir exito o fracaso.

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

Las pruebas tecnicas no sustituyen la validacion funcional del usuario cuando el comportamiento depende de geometria real, flujo visual, documentos reales o criterios de trabajo de ElectricCR.

## Informe final

`RESULTADO_CODEX.md` debe indicar:

- Objetivo original de la tarea.
- Busqueda previa realizada.
- Causa confirmada.
- Archivos revisados, creados y modificados.
- Decisiones aplicadas.
- Pruebas ejecutadas y resultados.
- Resultado tecnico observado.
- Mensajes de consola relevantes.
- Riesgos, limitaciones y pendientes.
- Herramientas anteriores relacionadas.
- Si la solucion reemplaza, complementa, duplica o se desvia de otra herramienta.
- Aspectos que requieren validacion de Marco en FreeCAD.
- Clasificacion provisional por Rol funcional, Madurez y Resultado comprobado.

No declarar una tarea como terminada si no se ejecutaron pruebas dentro de FreeCAD o si las pruebas requieren validacion manual pendiente.

## Estados del ciclo de vida

Utilizar como referencia el siguiente ciclo:

```text
DEFINIDA
  -> IMPLEMENTADA
  -> PROBADA TECNICAMENTE
  -> VALIDADA FUNCIONALMENTE
  -> REVISADA POR GPT
  -> ACEPTADA
  -> INTEGRADA
```

Una tarea puede volver a `DESARROLLO` si aparecen errores, regresiones o desviaciones.

La integracion definitiva a ElectricCR requiere validacion funcional cuando corresponda y posterior revision de GPT/Marco.

Principio del proyecto:

```text
"Nueva" no significa "mejor".
"Ejecuta sin errores" no significa "resuelve el problema".
La solucion que permanece debe ser la que mejor funcione en el trabajo real.
```
