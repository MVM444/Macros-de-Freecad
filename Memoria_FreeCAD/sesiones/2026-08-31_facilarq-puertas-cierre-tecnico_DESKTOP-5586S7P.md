# Sesion FacilArquitecturaWB - cierre tecnico FA Puertas BIM

Fecha: 2026-08-31
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.11 / build 2026.08.31.3
Estado: baseline_tecnica_cerrada / limitacion_conocida

## Decision

GeometryIndex 1 del levantamiento 1416 no aprobo la validacion visual manual del
usuario. Se registra como limitacion conocida no resuelta. No se agregaron nuevas
heuristicas, offsets, scores ni tolerancias; tampoco se modificaron el algoritmo,
la version o el build.

La ruta futura recomendada es un override persistente por elemento que distinga
`AUTO_OK`, `AUTO_AMBIGUOUS` y `MANUAL_OVERRIDE`. Hasta entonces, la excepcion se
revisa y ajusta manualmente en una copia del documento.

## Evidencia de baseline

- modulos cargados desde la copia DEV sincronizada;
- `VERSION=0.14.11`, `BUILD_ID=2026.08.31.3`;
- `FA_CreateDoorsBIM` registrado;
- compilacion en memoria aprobada;
- pruebas focales: 63/63;
- smoke MCP corto: puerta BIM de 900 mm, host correcto, subvolumen positivo y
  corte real de 283500000 mm3;
- el E2E grande de nueve puertas excedio el timeout MCP de 90 s en esta corrida y
  no se contabilizo como una nueva aprobacion;
- huellas de cierre: `opening_utils.py=548E6D3D...AE034` y
  `door_corner_utils.py=256EAD08...444FE`.

## Limpieza y preservacion

Se cerro solamente `FA_Geom1_Downstream` y se eliminaron de
`%TEMP%/facilarq_codex` su `FCStd`, dos `FCBak` y la captura PNG. El original quedo
como unico documento abierto y mantuvo 157 objetos, estado guardado y
`isTouched()==False` antes/despues.

Se conservaron:

- `FacilArquitecturaWB/Respaldos_2026-08-31_FA_puertas_bounded_pre_build2/`;
- `FacilArquitecturaWB/Respaldos_2026-08-31_FA_puertas_base_archwindow_pre_build3/`;
- todos los cambios previos y ajenos del worktree.

"Baseline limpia" significa limpia dentro del alcance de runtime/build, modulos
de puertas, smoke y temporales de esta tarea; no implica que todo el repositorio
este sin cambios.
