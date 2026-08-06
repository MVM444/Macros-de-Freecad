# ElectricCR - Tarea actual

**Fecha:** 2026-08-06 12:41, America/Costa_Rica.

## Objetivo

Modernizar la herramienta para cambiar altura y rotacion, de manera que pueda trabajar con sensores, luminarias, equipos HVAC y otros objetos con simbolo 2D sin elevar el simbolo de planta.

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
4. Explicar la causa confirmada y presentar un plan antes de modificar codigo.

## Requisitos funcionales

- Detectar objetos ElectricCR directos y cambiar `AlturaRel` con regeneracion controlada.
- Detectar `App::Link` ElectricCR y reasignar el maestro correspondiente a la nueva altura.
- Detectar equipos HVAC y usar su propiedad `Height` y su mecanismo existente de sincronizacion.
- Usar `Placement.Base.z` solo para objetos sencillos sin altura semantica ni simbolo 2D.
- Permitir altura absoluta y delta.
- Mantener XY, cota base, rotacion, etiqueta, grupo y metadatos.
- No elevar el simbolo 2D respecto al nivel base.
- Mantener soporte de rotacion, evitando destruir orientaciones tecnicas existentes.
- Mostrar depuracion detallada en consola.
- Ejecutar los cambios dentro de una transaccion.

## Restricciones

- No modificar aun el codigo hasta completar analisis y plan.
- No eliminar la herramienta antigua sin conservar compatibilidad.
- No cambiar nombres actuales de grupos o recursos.
- No modificar archivos ajenos a la tarea.
- No crear migraciones automaticas al abrir documentos.

## Pruebas requeridas

- Sensor directo creado por la macro NFPA.
- Luminaria con simbolo 2D.
- Dispositivo ElectricCR `App::Link`.
- Evaporadora MEP.
- Objeto sencillo.
- Altura absoluta y delta.
- Rotacion absoluta y delta.
- Undo/redo.
- Guardar, cerrar y reabrir el documento.

## Resultado esperado

Una propuesta y posteriormente una implementacion minima que cambie la altura fisica 3D sin alterar la cota de planta del simbolo 2D. Documentar todo en `RESULTADO_CODEX.md`.