# ElectricCR - Historial de cambios aceptados

**Proposito:** Registrar unicamente modificaciones funcionales o de proceso que hayan sido probadas y aceptadas.

## Reglas

- No registrar intentos, propuestas ni cambios sin validar como versiones terminadas.
- Cada entrada debe incluir fecha, alcance, archivos, pruebas y limitaciones.
- Los detalles de una ejecucion en curso pertenecen a `RESULTADO_CODEX.md`.
- Una prueba tecnica no equivale automaticamente a validacion funcional.
- Las herramientas nuevas no se consideran mejoras por defecto.

## Cambios aceptados

### 2026-08-08 - Flujo de validacion GPT-Codex y control de herramientas generadas con IA

Se adopta formalmente un flujo de trabajo para evitar que macros nuevas, experimentos o desarrollos generados con IA se incorporen automaticamente como mejoras de ElectricCR.

**Decisiones principales:**

- Se separa `PROBADA TECNICAMENTE` de `VALIDADA FUNCIONALMENTE`.
- Se establece el ciclo `DEFINIDA -> IMPLEMENTADA -> PROBADA TECNICAMENTE -> VALIDADA FUNCIONALMENTE -> REVISADA POR GPT -> ACEPTADA -> INTEGRADA`.
- Una ejecucion sin errores no demuestra que una herramienta resuelva el objetivo original.
- El numero de ejecuciones no se utiliza como criterio unico de exito porque puede reflejar pruebas y depuracion.
- No se elimina una version anterior solamente porque exista una version nueva.
- Las nuevas herramientas deben compararse contra soluciones existentes antes de crearse o promoverse.
- Se adopta el tercer eje `Resultado comprobado`, junto con `Rol funcional` y `Madurez`.
- Los resultados negativos deben documentarse como `DESVIADA`, `DUPLICADA`, `INCOMPLETA`, `FALLIDA` o `ABANDONADA` cuando exista evidencia.
- Si la evidencia no es suficiente se utiliza `POR VERIFICAR`.

**Archivos afectados:**

- `AGENTS.md`
- `FLUJO_GPT_CODEX.md`
- `ESTADO_PROYECTO.md`
- `DECISIONES_TECNICAS.md`
- `TAREA_ACTUAL.md`
- `RESULTADO_CODEX.md`
- `HISTORIAL_CAMBIOS.md`

**Validacion:** Revision documental y coherencia entre archivos de coordinacion.

**Limitacion:** La clasificacion definitiva de macros existentes requiere revision funcional caso por caso; esta decision no autoriza eliminaciones automaticas.

### 2026-08-06 - Documentacion de coordinacion inicial

- Se definieron instrucciones permanentes para agentes.
- Se documento el estado de objetos directos y `App::Link`.
- Se registro la separacion entre nivel base y altura de instalacion.
- Se preparo la tarea para modernizar la herramienta de altura y rotacion.
- No se modifico codigo funcional.

**Archivos agregados:**

- `AGENTS.md`
- `ESTADO_PROYECTO.md`
- `DECISIONES_TECNICAS.md`
- `TAREA_ACTUAL.md`
- `RESULTADO_CODEX.md`
- `HISTORIAL_CAMBIOS.md`

**Validacion:** Revision documental. Las pruebas funcionales permanecen pendientes.
