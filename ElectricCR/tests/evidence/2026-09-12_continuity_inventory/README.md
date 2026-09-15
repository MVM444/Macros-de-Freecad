# Continuidad ElectricCR - 2026-09-12

Inspeccion previa a cualquier cambio funcional. No se descarto trabajo existente.

- Fuente localizada: `Macros-de-Freecad/ElectricCR`, no `Macros/ElectricCR`.
- Tarea mas reciente: apartado del 2026-09-10 14:01 al final de TAREA_ACTUAL.md, diagnosticar y corregir Access violation en Undo de Demo / PLAN Lifecycle. Los encabezados iniciales del 9/9 son antecedentes.
- El adaptador actual usa `App::FeaturePython` para metadata (linea 100), mientras RESULTADO_CODEX y ESTADO_PROYECTO aun encabezan con el fallo anterior de `App::Feature`.
- Existe `Demo_ElectricCR_A1_Prueba_Arquitectura.FCMacro`, encabezado 2026-09-09 23:14, que llama `create_validated_scaffold()`. Su encabezado afirma validacion manual; esta sesion no la verifico. No se atribuye autoria.
- InitGui.py contiene diferencias reales frente al indice: registro demo y servicios A1, entre otras. Parte coincide con historia documentada; no se considera todo trabajo nuevo ni atribuible a una sola sesion.
- `plan_lifecycle.py` conserva encabezado v0.1.1 del 5/9. No se encontro en los directorios de evidencia listados un resultado posterior del Undo de la demo. Esto no demuestra ausencia de trabajo en otro lugar.

## Git y preservacion

`git status --short` falla: `error: bad tree object HEAD`; en la raiz tambien falla el estado del submodulo. `git rev-parse HEAD` devuelve `df867c97a3773d9bef163f4db90321ece15e10da`, pero no se afirma que el objeto sea legible ni que el historial este sano.

`untracked.txt` inventaria archivos fuera del indice antes de escribir documentos. No implica que sean nuevos funcionalmente: incluye trabajo A1 historico. `index_stat_candidates.txt` recoge `git diff-files --name-status`: sus marcas pueden incluir diferencias de stat; no equivale a una verificacion de contenido de todos los archivos. El diff de InitGui.py si fue leido. No se reparo Git, refresco indice, restauro, limpio, movio, elimino, hizo commit ni push.

`baseline.json` conserva ruta relativa, tamano, mtime y SHA256 de seis archivos funcionales antes de documentar. No se modifico codigo ni modelos.

## Bloqueo y siguiente paso

AGENTS.md padre exige usar `freecad-cr-workbench-architecture` y leer su contrato antes de actuar. No existe en `C:/Users/marco/.codex/skills/freecad-cr-workbench-architecture/SKILL.md`; tampoco se encontro en la busqueda de SKILL.md/architecture-contract.md bajo .codex, .agents del usuario y el arbol local FreeCAD. La skill `freecad-project-memory` si se encontro y leyo en `.agents/skills/freecad-project-memory/SKILL.md` del repositorio.

Las instrucciones del entorno sobre skills exigen detenerse si una skill necesaria no se encuentra. Se detiene el desarrollo y se registra la inspeccion; no se sustituye el contrato ausente por suposiciones. Proximo paso: recuperar o indicar la ubicacion de la skill de arquitectura y su contrato; despues completar lecturas de contexto y diagnostico previo real en FreeCAD 1.1.3 antes de corregir lifecycle. AGENTS de ElectricCR menciona 1.1.1; la tarea vigente exige 1.1.3.

Sin compilacion, pruebas Python, ejecucion FreeCAD, MCP ni revision visual en esta sesion. Causa del Access violation no demostrada. Clasificacion del arreglo: SOPORTE / DESARROLLO / POR VERIFICAR. No se reemplaza ninguna herramienta, no cambia el contrato A1 y no corresponde actualizar mapa, revision de macros ni historial de aceptacion.
