# Resultado Codex - Reconstruccion BIM nativa desde Sketches

Fecha: 2026-08-09  
Version: FacilArquitecturaWB `0.9.0`, build `2026.08.09.5`  
FreeCAD validado: `1.1.3`

## 1. Resultado ejecutivo

FacilArquitecturaWB puede reconstruir un modelo BIM nativo desde un documento que
contenga solamente Sketches. El flujo funciona dentro de FreeCAD, sin Internet,
Codex, MCP ni scripts manuales en runtime.

Se agregaron comandos independientes y un coordinador:

- `FA_CreateBIMStructure`
- `FA_CreateWallsFromSketch`
- `FA_CreateColumnsFromSketch`
- `FA_CreateDoorsFromSketch`
- `FA_CreateWindowsFromSketch`
- `FA_RebuildBIMModel`

Los nombres anteriores permanecen como aliases de compatibilidad.

## 2. Investigacion realizada

Se revisaron el repositorio, el trabajo previo de Puriscal, los modulos actuales de
FA y el codigo BIM instalado en FreeCAD 1.1.3. Tambien se consultaron fuentes
oficiales:

- [FreeCAD Arch Workbench](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Arch_Workbench.md?plain=1)
- [FreeCAD Arch.py](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/Arch.py)
- [FreeCAD 1.0 release notes](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Release_notes_1.0.md)

La implementacion se contrasto finalmente con el codigo instalado localmente en
`Mod/BIM`, que es la autoridad para FreeCAD 1.1.3.

## 3. APIs BIM nativas encontradas

| Necesidad | API usada | Resultado real |
|---|---|---|
| Edificio | `Arch.makeBuilding()` | `IfcType = Building` |
| Nivel | `Arch.makeFloor()` | `IfcType = Building Storey` |
| Muro | `Arch.makeWall(sketch)` | `Draft.getType = Wall`, `Base = Sketch` |
| Columnas | `Arch.makeStructure()` | `Draft.getType = Structure`, `IfcType = Column` |
| Ejes | `Arch.makeAxis()` / `Arch.makeAxisSystem()` | reticula BIM nativa |
| Puerta | `Arch.makeWindowPreset("Simple door")` | `Draft.getType = Window`, `IfcType = Door` |
| Ventana | `Arch.makeWindowPreset(...)` | `Draft.getType = Window`, `IfcType = Window` |
| Host/hueco | `Hosts = [wall]` | corte real mediante subvolumen nativo |
| Space | `Arch.makeSpace()` | disponible, diferido en esta fase |

## 4. Codigo existente reutilizado

- `core/bim_utils.py`: `Arch.makeWall` directo, parametros y trazabilidad de muros.
- `core/axis_utils.py`: deteccion de dos familias, cruces reales y columnas.
- `core/opening_utils.py`: seleccion geometrica del host, presets nativos, huecos e
  idempotencia desarrollados para Puriscal.
- `core/project_structure.py`: mensajes `[FACILARQ]` y utilidades de propiedades.
- Dialogos pequenos y transacciones existentes del Workbench.

El coordinador no contiene copias de esos algoritmos: llama los mismos servicios.

## 5. Codigo retirado o limitado

El flujo nuevo no usa ni crea:

- `FA_Project`;
- `00_Reference` a `05_Electromechanical`;
- `FA_ReconstructedWallBase`;
- copias `Part::Feature` del Sketch de muros;
- grupos esteticos `FA_Columns`, `FA_Doors` o `FA_Windows`;
- `ArchGrid` como paso obligatorio.

El flujo anterior de `building_grid_utils.py` permanece disponible para reconstruir
un DXF, pero no forma parte de `Sketch depurado -> BIM`.

## 6. Arquitectura final

```text
Building [IfcType = Building]
`-- Level [IfcType = Building Storey]
    |-- Sketch de muros
    |-- Wall [Base = el mismo Sketch]
    |-- Axis / AxisSystem
    |-- Columns [IfcType = Column]
    |-- Door + Sketch Base nativo [Hosts = Wall]
    |-- Window + Sketch Base nativo [Hosts = Wall]
    `-- Sketches de referencia elegidos
```

`Level.Group` es la contencion nativa. `FA_TargetLevel` se almacena como nombre en
texto; un enlace inverso al Level produjo ciclos del grafo de FreeCAD durante las
pruebas y fue eliminado.

## 7. Relacion Sketch - Wall

La relacion comprobada es directa:

```text
FA_GridWallTrace (Sketcher::SketchObject)
`-- Wall.Base = FA_GridWallTrace
```

No existe `FA_ReconstructedWallBase` en los modelos de prueba nuevos.

## 8. Parametricidad y persistencia

La prueba `freecad_bim_rebuild_phase1.py` realizo:

1. creacion de Building/Level/Wall;
2. cambio de una restriccion del Sketch de 5000 a 6000 mm;
3. comprobacion del cambio de la caja del Wall;
4. guardado y reapertura;
5. segundo cambio a 7000 mm;
6. reejecucion idempotente;
7. Undo/Redo.

Resultado: `base=direct parametricity=ok persistence=ok idempotence=ok undo_redo=ok`.

## 9. Building y Level

`ensure_bim_structure()` crea o reutiliza una estructura compatible. Repetir el
comando conserva un Building y un Level. La prueba de persistencia confirmo la
relacion `Building.Group -> Level` despues de guardar y reabrir.

## 10. Columnas

Las columnas ya no se guardan dentro de un grupo `FA_Columns`. Se agregan
directamente al Level y conservan el enlace al Sketch fuente. La prueba sintetica
confirmo dimensiones parametricas, guardado/reapertura, idempotencia y Undo/Redo.

En La Cruz se detectaron 14 cruces reales dentro de una reticula teorica de 18;
solo se crearon las 14 columnas presentes.

## 11. Puertas

Las puertas son objetos `ArchWindow._Window` nativos con:

- `IfcType = Door`;
- `Hosts = [wall]`;
- Sketch `Base` nativo;
- ancho derivado del eje;
- `FA_CutVolume_mm3 > 0`;
- disminucion comprobada del volumen del Wall.

La prueba completa de La Cruz creo 17 puertas desde los 17 ejes no constructivos.

## 12. Ventanas y correccion solicitada

Los cuatro Sketches reportados se aceptan al seleccionarlos explicitamente:

- `Sketch_Centros_Ventanas_de_S_S`
- `Sketch_Centros_Ventanas001`
- `Sketch_Centros_Ventanales`
- `Sketch_Centros_Seleccion_14_objetos`

Los tres Sketches identificados por ventana/ventanal se detectan automaticamente,
aunque conserven el metadato historico incorrecto `FA_CenterlineKind = walls`. El
Sketch generico se muestra para asignacion manual. Un Sketch con espesor real de
muro sigue rechazandose como fuente de abertura.

La prueba completa de La Cruz creo 26 ventanas, sin ejes rechazados.

## 13. Asistente `FA_RebuildBIMModel`

El dialogo permite confirmar o cambiar:

- Sketch de muros;
- Sketch de columnas;
- Sketch de puertas;
- varios Sketches de ventanas;
- varios Sketches de referencia;
- nombres de Building/Level y dimensiones principales.

Los Sketches sin evidencia suficiente se muestran como no clasificados, pero siguen
disponibles en todos los controles. La losa se muestra como fase diferida.

## 14. Validacion de La Cruz

Entrada original del usuario: `La Cruz Version 2.1.FCStd`. Se trabajo exclusivamente
sobre la copia `.codex_tmp/La_Cruz_V2_1_clean_audit.FCStd`.

Resultados completos:

```text
LA_CRUZ_BIM_FULL_OK
columns=14
doors=17
windows=26
rejected_doors=0
rejected_windows=0
persistence=ok
```

Archivo resultante:

```text
.codex_tmp/La_Cruz_V2_1_BIM_full.FCStd
```

Una segunda prueba acotada repitio la reconstruccion, guardo/reabrio y verifico
Undo/Redo para muro completo, 14 columnas y una abertura de cada tipo.

## 15. Compatibilidad BIM, ElectricCR y MEP

La prueba completa uso `Draft.getType` y `IfcType` despues de crear el modelo y
despues de reabrirlo:

- Wall: `Draft.getType = Wall`, `IfcType = Wall`;
- Column: `Draft.getType = Structure`, `IfcType = Column`;
- Door/Window: `Draft.getType = Window`, con `IfcType` correspondiente;
- Building/Level: tipos IFC nativos.

ElectricCR y MEP pueden localizar estos elementos por tipos nativos y no necesitan
interpretar propiedades `FA_*`. Las propiedades FA solo aportan trazabilidad e
idempotencia.

## 16. Pruebas ejecutadas

- 128 pruebas unitarias del Workbench: aprobadas.
- `freecad_bim_rebuild_phase1.py`: aprobado.
- `freecad_bim_rebuild_phase2.py`: aprobado.
- `freecad_openings_end_to_end.py`: 2 puertas + 2 ventanas, aprobado.
- `freecad_la_cruz_rebuild_validation.py`: persistencia/idempotencia/Undo, aprobado.
- `freecad_la_cruz_full_rebuild.py`: 14 columnas, 17 puertas, 26 ventanas, aprobado.
- `freecad_rebuild_dialog_smoke.py`: asignaciones y parametros PySide, aprobado.
- `compileall`: aprobado.

## 17. Problemas conocidos

- `Arch.makeWindowPreset()` ejecuta tres recomputaciones nativas por abertura. La
  reconstruccion completa de La Cruz tardo aproximadamente 266 segundos. La GUI no
  esta bloqueada por codigo externo, pero FreeCAD puede parecer ocupado.
- Dos geometrías del Sketch de puertas de La Cruz son constructivas; por eso 19
  geometrías producen 17 puertas utilizables.
- La orientacion hacia recintos y la doble hoja especializada permanecen en las
  herramientas historicas; el comando general garantiza primero tipo, host y hueco.
- Slab y Space se difirieron para no debilitar las fases estabilizadas.
- La instalacion principal del usuario conserva dos advertencias ajenas a este
  desarrollo (`DevPathsBootstrap` y una ruta AppData incompleta). Las pruebas se
  ejecutaron con un perfil FreeCAD aislado.

## 18. Siguiente etapa recomendada

1. Optimizar la creacion masiva de presets para reducir recomputaciones.
2. Crear `FA_CreateSlabFromSketch` solo con Sketch cerrado y `Arch.makeStructure`
   clasificado como Slab.
3. Crear `FA_CreateSpaces` con `Arch.makeSpace()` y poligonos cerrados validados.
4. Integrar la orientacion de puertas hacia el recinto sin cambiar el contrato nativo.

La condicion final queda cumplida: una instalacion de FreeCAD 1.1.3 con
FacilArquitecturaWB puede reconstruir y continuar editando el modelo sin Codex/MCP.
