---
name: freecad-project-memory
description: Mantener continuidad tecnica de proyectos FreeCAD entre sesiones de Codex; diagnosticar FreeCAD por MCP; comparar dos computadoras; probar cambios de Workbenches; registrar estado, incidentes y resultados; preparar contexto para ChatGPT/GitHub. Activar ante frases como "continuar proyecto FreeCAD", "diagnosticar FreeCAD", "comparar equipos", "probar cambio", "cerrar sesion FreeCAD" o "preparar para ChatGPT". No usar para consultas generales de FreeCAD que no requieran memoria, diagnostico, pruebas o continuidad del proyecto.
---

# FreeCAD Project Memory

Version: 0.1.1  
Fecha y hora: 2026-08-11 19:49 -06:00

## Objetivo

Mantener una memoria tecnica corta, verificable y sincronizable del desarrollo de FreeCAD. No guardar la conversacion completa. Guardar solo decisiones, cambios, pruebas, errores, diferencias de entorno y proximos pasos.

La memoria debe distinguir siempre entre:

- `programado`: cambio realizado en archivos.
- `compilado`: Python compila o importa sin error.
- `probado`: se ejecuto una prueba real.
- `verificado_mcp`: FreeCAD confirmo el resultado mediante MCP.
- `verificado_visual`: se reviso una captura o la vista 3D cuando aplica.

Nunca presentar un cambio como probado si solo fue editado o compilado.

## Reglas de convivencia con el repositorio

1. Leer primero `AGENTS.md` del repositorio.
2. Si `AGENTS.md` exige otra skill, usarla tambien. En este repositorio, la skill de arquitectura FreeCAD tiene prioridad para decisiones de arquitectura.
3. No reemplazar `AGENTS.md`.
4. No guardar ni modificar un `.FCStd` original sin autorizacion explicita.
5. No hacer `commit`, `push`, merge, rebase ni borrar ramas sin solicitud explicita del usuario.
6. Antes de reemplazar una solucion que funcionaba, revisar Git/historial y preservar las caracteristicas utiles de la version anterior.
7. Preferir rutas relativas al repositorio y evitar rutas absolutas de usuario.
8. Si OneDrive esta involucrado, verificar que el archivo sea legible localmente y registrar ruta, tamano, mtime y hash de archivos clave.

## Archivos de memoria

Usar, en la raiz del repositorio:

- `ESTADO_PROYECTO.md`: estado actual corto. Actualizar; no convertir en historial.
- `TAREA_ACTUAL.md`: objetivo y alcance de la tarea en curso.
- `RESULTADO_CODEX.md`: ultimo resultado preparado para revision humana/ChatGPT.
- `Memoria_FreeCAD/equipos/<HOST>.json`: diagnostico mas reciente por computadora.
- `Memoria_FreeCAD/sesiones/YYYY-MM-DD_HHMM_<proyecto>_<host>.md`: historial resumido.
- `Memoria_FreeCAD/incidentes/`: problemas recurrentes que merecen conservarse.
- `Memoria_FreeCAD/comparaciones/`: comparaciones entre entornos cuando se soliciten.

Si faltan, ejecutar `scripts/init_memory.py` desde la raiz del repositorio.

## Flujo: continuar proyecto

Cuando el usuario pida continuar, retomar o recuperar un proyecto:

1. Leer `AGENTS.md`, `ESTADO_PROYECTO.md`, `TAREA_ACTUAL.md` y `RESULTADO_CODEX.md` si existen.
2. Leer solo la ultima sesion relevante; no cargar todo el historial salvo necesidad.
3. Ejecutar `git status --short`, identificar rama y commit.
4. Identificar el Workbench/proyecto activo.
5. Antes de usar MCP, ejecutar la precondicion obligatoria de disponibilidad de FreeCAD indicada abajo y obtener diagnostico real antes de editar.
6. Verificar que FreeCAD cargue el Workbench desde la ruta esperada y detectar copias duplicadas.
7. Comparar el diagnostico actual con el ultimo guardado para ese host.
8. Resumir en pocas lineas: equipo, commit, Workbench, estado, ultimo resultado y pendiente principal.
9. Solo despues iniciar cambios.

## Precondicion obligatoria: FreeCAD disponible antes de MCP

Antes de cualquier diagnostico, prueba, captura o verificacion mediante MCP:

1. Identificar la version objetivo de FreeCAD a partir de `ESTADO_PROYECTO.md`, `TAREA_ACTUAL.md` o del diagnostico mas reciente del host. En este proyecto la version objetivo actual es FreeCAD 1.1.3, pero no hardcodear rutas personales.
2. Comprobar primero si MCP responde. Si responde, continuar sin reiniciar FreeCAD.
3. Si MCP no responde, comprobar si FreeCAD esta ejecutandose. Tratar errores de conexion rechazada, incluido `WinError 10061`, como una condicion recuperable antes de clasificarlos como fallo MCP.
4. Si FreeCAD esta cerrado, abrir automaticamente la version objetivo usando, en este orden:
   - la ruta ejecutable registrada en `Memoria_FreeCAD/equipos/<HOST>.json`;
   - una ruta detectada de forma segura en el equipo;
   - configuracion documentada del proyecto.
5. No iniciar una segunda instancia si la version objetivo ya esta ejecutandose. No cerrar ni reiniciar una instancia del usuario solo para verificar MCP.
6. Esperar de forma acotada a que FreeCAD termine de iniciar y reintentar la conexion MCP varias veces con pausas cortas. Registrar cantidad de intentos y ultimo error.
7. Si FreeCAD esta abierto pero MCP sigue sin responder, intentar unicamente el mecanismo de inicio/reconexion MCP documentado en `references/mcp-diagnostic-usage.md` o disponible realmente en el entorno. No inventar servicios, puertos ni comandos no documentados.
8. Solo despues de estos intentos marcar `NO_VERIFICADO_MCP`. Distinguir claramente entre:
   - FreeCAD no pudo abrirse;
   - FreeCAD abrio pero MCP no conecto;
   - MCP conecto pero la prueba fallo;
   - verificacion MCP completada.
9. FreeCAD cerrado por si solo NO es un fallo de la implementacion. Es una precondicion recuperable que la skill debe intentar resolver.
10. No cerrar FreeCAD al terminar salvo solicitud explicita del usuario.

Registrar el resultado de disponibilidad, por ejemplo:

```text
FreeCAD: cerrado -> iniciado automaticamente
Version: 1.1.3
MCP: conectado
Estado: VERIFICADO_MCP
```

o, si no se logra:

```text
FreeCAD: iniciado correctamente
MCP: no disponible despues de <N> intentos
Estado: NO_VERIFICADO_MCP
Causa: <ultimo error concreto>
```

## Flujo: diagnosticar FreeCAD

Cuando el usuario pida diagnostico o cuando un cambio funcione en una computadora y falle en otra:

1. Ejecutar primero la precondicion obligatoria de disponibilidad de FreeCAD y despues usar el MCP conectado al equipo objetivo.
2. Obtener al menos:
   - host;
   - version FreeCAD;
   - Python;
   - binding Qt/PySide;
   - Workbench activo;
   - documento activo;
   - `UserAppDataDir`;
   - `UserMacroDir`;
   - `MacroPath`;
   - Workbenches registrados;
   - comandos relevantes registrados;
   - rutas reales de modulos cargados;
   - hash de archivos clave;
   - indicio de ruta OneDrive.
3. Preferir `scripts/freecad_diag.py` ejecutado dentro de FreeCAD mediante la herramienta MCP capaz de ejecutar Python.
4. Guardar el JSON en `Memoria_FreeCAD/equipos/<HOST>.json`.
5. No incluir secretos, tokens, credenciales ni contenido sensible de documentos.

Si MCP sigue sin estar disponible despues del flujo de recuperacion anterior, hacer diagnostico solo de archivos/Git y marcar el resultado como `NO_VERIFICADO_MCP`, registrando si FreeCAD estaba cerrado, si fue iniciado y cual fue el ultimo error de conexion.

## Flujo: comparar equipos

1. Usar los diagnosticos mas recientes de los dos hosts.
2. Ejecutar `scripts/compare_envs.py <equipo1.json> <equipo2.json>`.
3. Priorizar diferencias que expliquen fallos:
   - version FreeCAD/Python/PySide;
   - `MacroPath`;
   - ruta real del Workbench;
   - hash de `InitGui.py` y modulos clave;
   - comandos disponibles;
   - copias duplicadas;
   - archivos no locales o no legibles.
4. Guardar la comparacion en `Memoria_FreeCAD/comparaciones/`.
5. No asumir que dos carpetas OneDrive iguales implican dos entornos FreeCAD iguales.

## Flujo: antes de modificar codigo

1. Confirmar archivo fuente real cargado por FreeCAD.
2. Revisar `git diff` y cambios locales.
3. Buscar duplicados del mismo Workbench en rutas de macros y `Mod`.
4. Registrar baseline de archivos clave.
5. Revisar historial cuando el cambio pueda perder comportamiento visual o funcional previo.
6. Para cambios grandes, separar el trabajo en pasos pequenos y verificables.

## Flujo: probar cambio

1. Si la prueba requiere MCP o FreeCAD GUI, ejecutar primero la precondicion obligatoria de disponibilidad de FreeCAD.
2. Seleccionar el perfil del Workbench en `references/workbench-test-profiles.json`.
3. Ejecutar primero pruebas no destructivas.
4. Si hace falta crear objetos, usar documento temporal.
5. Recargar el Workbench si el proyecto lo soporta.
6. Comprobar registro/activacion de Workbench y comandos.
7. Ejecutar solo las pruebas relacionadas con los archivos modificados, salvo que el usuario pida regresion completa.
8. Si el cambio es visual o geometrico, obtener captura por MCP y revisar el resultado.
9. Registrar errores con contexto suficiente para reproducirlos.
10. Cerrar/eliminar solo documentos temporales creados por la prueba.
11. No cerrar documentos del usuario.

## Flujo: cerrar sesion FreeCAD

Cuando el usuario diga "cerrar sesion FreeCAD", "terminar por hoy", "wrap-up" o equivalente:

1. Revisar `git status` y `git diff`.
2. Ejecutar las pruebas pertinentes.
3. Obtener diagnostico MCP final si esta disponible.
4. Actualizar `ESTADO_PROYECTO.md`.
5. Actualizar `TAREA_ACTUAL.md` con lo pendiente; si no hay pendiente, indicarlo.
6. Actualizar `RESULTADO_CODEX.md`.
7. Crear una sesion historica corta.
8. Actualizar `Memoria_FreeCAD/equipos/<HOST>.json`.
9. Registrar incidentes nuevos solo si son recurrentes o de alto valor.
10. Informar al usuario:
    - que cambio;
    - que se probo;
    - que fue verificado por MCP;
    - que queda pendiente;
    - estado Git.
11. No hacer commit/push sin autorizacion.

## Flujo: preparar para ChatGPT

Actualizar `RESULTADO_CODEX.md` con un resumen que pueda entenderse sin leer la conversacion de Codex:

- fecha/hora;
- equipo;
- proyecto/Workbench;
- objetivo;
- archivos modificados;
- cambios principales;
- pruebas ejecutadas;
- resultado MCP;
- errores pendientes;
- commit actual;
- cambios sin commit;
- siguiente paso recomendado.

Si el usuario desea que ChatGPT lo revise desde GitHub, recordar que los cambios locales no son visibles hasta que sean publicados en GitHub.

## Calidad de la memoria

- Mantener `ESTADO_PROYECTO.md` preferiblemente por debajo de 200 lineas.
- Las sesiones deben resumir decisiones y resultados, no transcribir chats.
- Guardar datos estructurados de equipos en JSON.
- Si una conclusion no fue verificada en FreeCAD, etiquetarla.
- Si hay contradiccion entre memoria y estado real de FreeCAD, prevalece el estado real y se corrige la memoria.

## Referencias

Leer solo cuando hagan falta:

- `references/memory-contract.md`
- `references/workbench-test-profiles.json`
- `references/mcp-diagnostic-usage.md`
