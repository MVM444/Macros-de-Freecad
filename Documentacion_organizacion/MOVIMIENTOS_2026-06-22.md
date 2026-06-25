# Movimientos realizados el 2026-06-22

Este registro ayuda a rastrear archivos si una prueba futura muestra un error despues de la reorganizacion.

## Movimientos desde la raiz de Macros

| Archivo original | Nueva ubicacion | Motivo |
| --- | --- | --- |
| `Nodes_Cubos_Onda.FCMacro` | `Scripts Varios/Nodes_Cubos_Onda.FCMacro` | Ejemplo de cubos con onda senoidal; no es macro central. |
| `Prueba exportar.FCMacro` | `Scripts Varios/Pruebas_exportacion/Prueba exportar.FCMacro` | Macro grabada, dependia del documento `Casa_Prueba`. |
| `AutoCorreccion_Local.FCMacro` | `Scripts Varios/Diagnostico/AutoCorreccion_Local.FCMacro` | Herramienta de diagnostico y reportes JSON. |
| `DistribucionSucursalGA.FCMacro` | `Scripts Varios/DistribucionSucursalGA/DistribucionSucursalGA.FCMacro` | Herramienta especializada de distribucion arquitectonica. |
| `DistribucionSucursalGA_README.md` | `Scripts Varios/DistribucionSucursalGA/DistribucionSucursalGA_README.md` | Documentacion de la macro anterior. |
| `programa_sucursal_template.csv` | `Scripts Varios/DistribucionSucursalGA/programa_sucursal_template.csv` | Plantilla usada por `DistribucionSucursalGA`. |
| `Importar_Luminarias_CSV_ElectricCR.FCMacro` | `Scripts Varios/Importaciones_especificas/Importar_Luminarias_CSV_ElectricCR.FCMacro` | Importacion puntual con ruta fija de proyecto. |
| `SheetMetalUnfoldUpdater.FCMacro` | `Scripts Varios/SheetMetal/SheetMetalUnfoldUpdater.FCMacro` | Herramienta externa/especializada de SheetMetal. |
| `Symbols_Library_Arreglado.FCMacro` | `Scripts Varios/Simbolos/Symbols_Library_Arreglado.FCMacro` | Explorador de libreria SVG, no central. |
| `WalkTrough_747Developments.FCMacro` | `Scripts Varios/Navegacion/WalkTrough_747Developments.FCMacro` | Navegacion/camara, utilidad externa. |
| `rename_joints_macro.py` | `Scripts Varios/Assembly/rename_joints_macro.py` | Macro para Assembly. |
| `rename_joints_icon.png` | `Scripts Varios/Assembly/rename_joints_icon.png` | Icono de `rename_joints_macro.py`. |
| `dxfColorMap.py` | `Scripts Varios/DXF/dxfColorMap.py` | Libreria DXF. |
| `dxfImportObjects.py` | `Scripts Varios/DXF/dxfImportObjects.py` | Libreria DXF. |
| `dxfLibrary.py` | `Scripts Varios/DXF/dxfLibrary.py` | Libreria DXF. |
| `dxfReader.py` | `Scripts Varios/DXF/dxfReader.py` | Libreria DXF. |
| `Lampara de emergencia.dxf` | `Scripts Varios/DXF/Lampara de emergencia.dxf` | Recurso DXF suelto. |
| `Visor Dinamico.html` | `Scripts Varios/Visualizacion/Visor Dinamico.html` | Utilidad HTML de visualizacion. |
| `AbrirDirectorioElectricCR.FCMacro` | `Macros-de-Freecad/Organizacion del proyecto/AbrirDirectorioElectricCR.FCMacro` | Macro relacionada con ElectricCR. |
| `Electrical_Schedule_Base.FCMacro` | `Macros-de-Freecad/Tableros/Electrical_Schedule_Base.FCMacro` | Macro electrica; queda bajo ElectricCR/Tableros. |

## Movimientos de workbench/proyecto

| Origen | Nueva ubicacion | Nota |
| --- | --- | --- |
| `GameEngineExport/` | `Macros-de-Freecad/GameEngineExport/` | Macros relacionadas con exportacion a motor de juego. |
| `Mod/GameEngineExportWB/` | `Macros-de-Freecad/GameEngineExportWB/` | Workbench real de GameEngineExport. |
| macros sueltas de ElectricCR en `Macros-de-Freecad` | carpetas tematicas dentro de `Macros-de-Freecad` | Se elimino ruido de la raiz del proyecto. |

## Archivos archivados previamente

Varios archivos temporales, reportes, respaldos de prueba y recursos duplicados se movieron a:

- `Reportes/AutoCorreccion`
- `Reportes/Analisis_documentos`
- `Respaldos/Proyectos_prueba`
- `Respaldos/Archivos_vacios_o_obsoletos`
- `Respaldos/Recursos_duplicados`
- `Respaldos/Registros_antiguos`
- `Respaldos/Caches_temporales`
- `scripts/analisis_documentos`
- `scripts/mantenimiento_freecad`
- `scripts/utilidades`

## Cambios de codigo asociados

- `Alias.FCMacro`: cambio de `exec_()` a llamada compatible `exec`/`exec_`.
- `AutoCorreccion_Local.FCMacro`: reportes dirigidos a `Macros/Reportes/AutoCorreccion`.
- `SheetMetalUnfoldUpdater.FCMacro`: se agrego `FreeCADGui as Gui` y `App = FreeCAD`.
- `WalkTrough_747Developments.FCMacro`: se agrego alias `Gui`.
- `Symbols_Library_Arreglado.FCMacro`: fallback para `QSvgWidget` en PySide6.
- `Mod/DevPathsBootstrap/InitGui.py`: ya no depende estrictamente de `__file__`.
- `GameEngineExportLoader.FCMacro`: busca `GameEngineExportWB` dentro de `Macros-de-Freecad`.
- `Macros-de-Freecad/ElectricCR/commands/macros.py`: ignora `MEPWorkbenchCR`, `GameEngineExport`, `GameEngineExportWB` y `scripts` al crear barras de ElectricCR.
- `Macros-de-Freecad/ElectricCR/config.json`: se agrego `Tableros` al orden de barras.

## Archivos que se decidio mantener en raiz

- `Alias.FCMacro`
- `VentanadeMacros.FCMacro`
- `MacrosPersonalizadas.FCMacro`
- `ElectricCRLoader.FCMacro`
- `MEPWorkbenchCRLoader.FCMacro`
- `GameEngineExportLoader.FCMacro`
