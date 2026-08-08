# ElectricCR - Tarea actual

**Fecha:** 2026-08-08 11:46, America/Costa_Rica.

**Estado:** IMPLEMENTADA -> PROBADA TECNICAMENTE -> VALIDACION FUNCIONAL PENDIENTE.

## Objetivo

Modernizar la herramienta para cambiar altura y rotacion, de manera que pueda trabajar con sensores, luminarias, equipos HVAC y otros objetos con simbolo 2D sin elevar el simbolo de planta.

La tarea se define por el problema funcional anterior, no por la obligacion de crear una macro nueva. Si una solucion existente puede corregirse o ampliarse de manera segura, debe preferirse esa ruta.

## Problema observado

- Cambiar `Placement.Base.z` eleva conjuntamente el modelo 3D y el simbolo 2D.
- Cambiar `AlturaRel` en ciertos `App::Link` no modifica la geometria porque el enlace conserva el mismo maestro.
- La herramienta existente trata todos los objetos como objetos sencillos con `Placement`.

## Archivos iniciales a revisar

- `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro`
- `ElectricCR/electriccr/features/objeto_toma_uno.py`
- `Deteccion/ColocarDetectores_NFPA.FCMacro`
- Macros activas de iluminacion que creen objetos directos o `App::Link`
- `MEPWorkbenchCR/MEP/hvac/hvac_equipment.py`
- `Resources/registry/registry_electric.json`

## Trabajo previo obligatorio

1. Buscar en Internet soluciones o patrones existentes en FreeCAD para separar representacion 2D y altura 3D.
2. Revisar el patron implementado en MEPWorkbenchCR.
3. Identificar los tipos reales de objetos creados por sensores y luminarias.
4. Revisar si ya existen macros o variantes dentro del repositorio que resuelvan total o parcialmente el problema.
5. Explicar la causa confirmada y presentar un plan antes de modificar codigo.
6. Justificar cualquier macro, modulo o variante nueva indicando que mejora funcional aporta frente a lo existente.

## Requisitos funcionales

- Detectar objetos ElectricCR directos y cambiar `AlturaRel` con regeneracion controlada.
- Detectar `App::Link` ElectricCR y reasignar el maestro correspondiente a la nueva altura.
- Detectar equipos HVAC y usar su propiedad o API semantica de altura y su mecanismo existente de sincronizacion.
- Usar `Placement.Base.z` solo para objetos sencillos sin altura semantica ni simbolo 2D.
- Permitir altura absoluta y delta.
- Mantener XY, cota base, rotacion, etiqueta, grupo y metadatos.
- No elevar el simbolo 2D respecto al nivel base.
- Mantener soporte de rotacion, evitando destruir orientaciones tecnicas existentes.
- Mostrar depuracion detallada en consola.
- Ejecutar los cambios dentro de una transaccion.

## Restricciones

- No eliminar la herramienta anterior sin conservar compatibilidad hasta validar la solucion nueva.
- No cambiar nombres actuales de grupos o recursos.
- No modificar archivos ajenos a la tarea.
- No crear migraciones automaticas al abrir documentos.
- No considerar una ejecucion sin errores como demostracion suficiente de mejora funcional.
- No utilizar cantidad de ejecuciones como unico criterio de exito; durante desarrollo puede reflejar pruebas repetidas.
- Si la solucion se desvia del objetivo original, detener la promocion y documentar la desviacion en `RESULTADO_CODEX.md`.

## Pruebas tecnicas requeridas

- Sensor directo creado por la macro NFPA.
- Luminaria con simbolo 2D.
- Dispositivo ElectricCR `App::Link`.
- Evaporadora MEP.
- Objeto sencillo.
- Altura absoluta y delta.
- Rotacion absoluta y delta.
- Undo/redo.
- Guardar, cerrar y reabrir el documento.

## Validacion funcional requerida

Despues de las pruebas tecnicas, Marco debe verificar al menos uno o dos casos reales desde la interfaz habitual de FreeCAD y confirmar:

- que el resultado visual y geometrico coincide con el objetivo;
- que el simbolo 2D permanece en la cota correcta;
- que el cambio de altura y rotacion resulta util en el flujo real;
- que no aparece una regresion evidente en objetos existentes;
- que la herramienta modernizada representa una mejora o complemento real frente a la version anterior.

Si la validacion no confirma lo anterior, la herramienta debe volver a `DESARROLLO` y clasificarse segun corresponda como `COMPROBADA-PARCIAL`, `EXPERIMENTAL`, `DESVIADA`, `INCOMPLETA`, `FALLIDA` o `POR VERIFICAR`.

## Clasificacion provisional

Mientras la validacion funcional siga pendiente:

```text
Rol funcional:       NUCLEO
Madurez:              CANDIDATA
Resultado comprobado: PROMETEDORA
```

No promover a `ESTABLE / COMPROBADA` antes de la validacion funcional y revision posterior.

## Resultado esperado

Una implementacion minima que cambie la altura fisica 3D sin alterar la cota de planta del simbolo 2D, conserve orientaciones tecnicas y pueda demostrarse en trabajo real.

Documentar todo en `RESULTADO_CODEX.md` y aplicar el flujo definido en `FLUJO_GPT_CODEX.md`.
