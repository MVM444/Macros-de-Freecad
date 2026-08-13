# Resultado Codex: puertas y ventanas BIM

Fecha: 2026-08-09  
Version: 0.8.1  
Build: 2026.08.09.4

## 1. Resumen de Puriscal

La solucion anterior se recupero antes de implementar. La copia actual de `Puriscal
Depurado.FCStd` contiene 19 hojas de puerta y 8 ventanas nativas. Los 27 objetos son
`ArchWindow._Window`, tienen `IfcType` correcto, Sketch Base y `Hosts = [Wall002]`.
El archivo original no se modifico.

## 2. Archivos reutilizados

- `InsertarPuertasBIMDesdeRecintos.FCMacro`: proyeccion, Placement y preset puerta.
- `InsertarVentanasBIMDesdeRecintos.FCMacro`: soporte colineal y presets ventana.
- `AgregarPuertasFrentePuriscal.FCMacro`: referencia del caso de doble hoja.
- `core/bim_utils.py`: adaptador de la API Arch y propiedades comunes.
- `GameEngineExportWB/macros/bim_from_selected_sketch.py`: referencia tecnica de
  perfiles y `WindowParts`; no se importaron dependencias `GEE_*`.

## 3. Archivos creados

- `AUDITORIA_PUERTAS_VENTANAS_PURISCAL.md`.
- `core/opening_utils.py`.
- `ui/dialog_opening_parameters.py`.
- `commands/cmd_create_doors_bim.py`.
- `commands/cmd_create_windows_bim.py`.
- `tests/test_opening_utils.py`.
- `tests/freecad_arch_window_api_probe.py`.
- `tests/freecad_openings_end_to_end.py`.
- `tests/freecad_puriscal_openings_audit.py`.
- `tests/freecad_puriscal_openings_compatibility.py`.

## 4. Archivos modificados

- `core/bim_utils.py`, `core/constants.py`.
- `Init.py`, `InitGui.py`, `__init__.py`, `package.xml`.
- Comandos de centros de puertas y ventanas: identificadores estabilizados.
- `README.md` y `DOCUMENTACION_WORKBENCH.md`.

No se modificaron ElectricCR ni GameEngineExportWB.

## 5. Arquitectura final

Los ejes DXF siguen siendo fuentes autoritativas. `opening_utils.py` transforma cada
linea en una solicitud de abertura, resuelve un Arch Wall y crea un objeto nativo
Arch Window con `IfcType = Door` o `Window`. El Sketch creado por el preset es `Base`;
el muro se enlaza mediante la propiedad nativa `Hosts` y mediante `FA_HostWall`.

## 6. Uso de FA Puertas BIM

1. Seleccionar uno o varios Sketches de centros de puertas.
2. Opcionalmente seleccionar uno o varios muros BIM.
3. Ejecutar `FA Puertas BIM`.
4. Indicar altura y tolerancia.

El ancho procede de cada linea. Se usa el preset `Simple door`, `Opening = 100` y
antepecho cero.

## 7. Uso de FA Ventanas BIM

1. Seleccionar uno o varios Sketches de centros de ventanas.
2. Opcionalmente seleccionar los muros candidatos.
3. Ejecutar `FA Ventanas BIM`.
4. Indicar altura, antepecho y tolerancia.

Se usa `Open 1-pane` bajo 900 mm y `Sliding 2-pane` desde 900 mm.

Correccion 0.8.1: la seleccion se lee antes de actualizar `FA_Project`, se aceptan
Sketches seleccionados mediante `App::Link` y, si no hay una seleccion valida, se
detecta automaticamente `Sketch_Centros_Ventanas` por nombre o metadatos.

## 8. Seleccion del host

Para cada eje se comparan orientacion, distancia perpendicular, proyeccion, soporte
de segmentos colineales, sobrepaso y cota Z. Una seleccion manual restringe la lista,
pero el muro aun debe ser compatible. Si dos muros obtienen puntuaciones equivalentes,
el eje se rechaza como ambiguo y se informa en consola.

## 9. Prevencion de duplicados

La clave es `FA_SourceSketch + FA_SourceGeometryIndex + FA_GeneratedBy`. Al reemplazar,
solo se eliminan resultados del comando actual y de las fuentes seleccionadas. Los
generadores historicos `FA_InsertDoorsBIM` y `FA_InsertWindowsBIM` son aliases de
lectura: satisfacen la clave y nunca se borran automaticamente.

## 10. Resultado de pruebas

- 116 pruebas unitarias aprobadas.
- API FreeCAD 1.1.3: puerta y ventana nativas, hosts, cortes exactos y persistencia.
- Caso sintetico: 2 muros, uno diagonal; 2 puertas; 2 ventanas; Undo/Redo;
  reejecucion sin duplicados; guardar/cerrar/reabrir.

## 11. Resultado Puriscal

La prueba uso una copia temporal. Reconocio 19 indices de puerta y 8 de ventana,
creo cero objetos nuevos, conservo 27 hosts y mantuvo los conteos al reabrir. El
original permanecio intacto.

## 12. Estado para La Cruz

El nucleo no depende de nombres Puriscal, de `Wall002`, de espesores 100/200 ni de
muros ortogonales. Esta listo para una prueba funcional con los Sketches y Arch Walls
de La Cruz.

## 13. Problemas conocidos

- La primera version general usa la apertura predeterminada de la puerta; no infiere
  aun el recinto interior.
- No agrupa automaticamente dos ejes en una puerta doble.
- Los presets de ventana se eligen por ancho y aun no tienen selector de catalogo.
- Un muro BIM sin Sketch Base o centro trazable se omite.

## 14. Siguiente paso recomendado

Probar La Cruz con una copia del modelo. Luego integrar una opcion de orientacion por
Arch Space/poligonos de recinto y una regla general explicita para puertas dobles.
