# Sesion FreeCAD - Facil Arquitectura - puerta doble BIM

Fecha/hora: 2026-08-12 17:18:46 -06:00  
Equipo: DESKTOP-5586S7P  
Rama/commit: `agent/respaldo-electriccr-2026-08-10` / `707a0fc`  
Estado: `PROGRAMADO / COMPILADO / PROBADO / VERIFICADO_MCP / VERIFICADO_VISUAL`

## Objetivo

Corregir la puerta doble BIM de Facil Arquitectura para materiales RGBA,
alojamiento y hueco nativos, movimiento con host, apertura y barras idempotentes.

## Resultado

- version final `0.11.1`, build `2026.08.12.2`;
- aluminio y panel escriben `Transparency = 0`; vidrio usa 70;
- `ArchWindow.colorize()` aprobado sin `IndexError`;
- `Hosts = [wall]` es el unico enlace BIM al muro y evita movimiento triple;
- `HoleWire = 1`, `HoleDepth = 0` y Subvolume nativo;
- corte nuevo y hueco preexistente validados;
- movimiento exacto una vez, persistencia y eliminacion aprobados;
- `Opening = 0, 25, 50, 100, 0` aprobado en ambas hojas;
- 139/139 pruebas unitarias y smokes MCP aprobados;
- cinco barras presentes exactamente una vez despues de dos hot restarts;
- captura isometrica revisada: tres materiales distinguibles y hueco real.

## Seguridad

El FCStd original de La Cruz no se guardo ni modifico. Conserva 4 568 346 bytes,
mtime `2026-08-12T15:09:24.6116772-06:00` y SHA-256
`383B114507245A809C3F1E36F1DF5E74488698BBC84B314CCE2A076FC3741A72`.
Solo ese documento queda abierto en FreeCAD.

## Incidencia externa

La copia duplicada de FacilArquitecturaWB bajo `AppData/Roaming/FreeCAD/v1-1/Mod`
tiene una ruta interna inexistente e impide iniciar `FreeCADCmd` separado. No se
modifico. MCP carga la copia correcta de `Macros-de-Freecad` y todas las pruebas
reales pasaron dentro de FreeCAD 1.1.3.

## Siguiente paso

Marco debe ejecutar la prueba manual corta descrita en
`Scripts Varios/FacilArquitectura_BIM/Puriscal/RESULTADO_CODEX.md` antes de agregar
nuevas funciones de puertas.
