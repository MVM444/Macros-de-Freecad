# PROMPT PARA CODEX - Ejecutar tarea FA Aberturas BIM desde Sketch

Usa la skill repo-scoped de continuidad FreeCAD (`freecad-project-memory`) y cualquier otra skill exigida por `AGENTS.md`.

Lee primero `AGENTS.md` y luego `TAREA_ACTUAL.md` de la copia local sincronizada del repositorio `Macros-de-Freecad`.

Ejecuta completamente la tarea **FA Aberturas BIM desde Sketch** que figura en `TAREA_ACTUAL.md`.

Puntos no negociables:

- FreeCAD objetivo: 1.1.3.
- Antes de programar, investiga en fuentes primarias si FreeCAD ya dispone de `Opening only`, `Opening Element` o mecanismo BIM equivalente y documenta lo encontrado.
- Revisa primero la implementacion actual de puertas y ventanas BIM desde Sketch y reutiliza su deteccion de host, validacion y reemplazo seguro.
- Regla: `1 Sketch = 1 tipo/familia + N instancias`.
- Un Sketch puede contener muchas lineas.
- Cada linea representa **solo un buque/vano**.
- Ancho = longitud de la linea.
- Altura predeterminada = 2100 mm, pero editable.
- Altura desde piso = 0 mm por defecto, pero editable.
- Crear un corte BIM real en el Wall anfitrion.
- No crear hoja, marco, vidrio ni simbolo de puerta.
- No borrar puertas, ventanas, aberturas manuales ni objetos ajenos.
- Procesar por lotes y evitar recomputes innecesarios.
- Mantener mensajes `[FACILARQ][ABERTURAS]` en consola.
- No modificar ElectricCR, MEPWorkbenchCR ni GameEngineExportWB.
- No usar rutas absolutas de usuario.
- Actualiza version/build conforme al esquema actual.
- Ejecuta pruebas unitarias, regresion y smoke tests que sean razonables.
- Al finalizar actualiza `RESULTADO_CODEX.md` o el resultado indicado por `AGENTS.md` con archivos modificados, pruebas, version/build y procedimiento exacto de prueba en FreeCAD.

No reescribas desde cero lo que ya funciona. Extiende la arquitectura existente de Facil Arquitectura de la forma mas pequena, reusable y segura posible.

Si encuentras una incompatibilidad real que impida cumplir el requisito sin riesgo de romper el Workbench, detente antes de una refactorizacion grande y documenta exactamente el bloqueo en el resultado.
