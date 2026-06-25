# Organizacion del directorio Macros

Fecha de referencia: 2026-06-22.

Nota: esta es una copia de referencia dentro de `Macros-de-Freecad` para que otros GPTs o revisiones futuras encuentren la organizacion aunque abran solo este proyecto. La otra copia esta en `Macros/Documentacion_organizacion`.

Este directorio se limpio para que la raiz de `Macros` funcione como punto de entrada de FreeCAD, no como bodega general.

## Regla principal

En la raiz de `Macros` deben quedar solo:

- loaders de workbench;
- macros generales que ayudan a administrar otras macros;
- iconos SVG usados directamente por esas macros de raiz;
- archivos de configuracion/documentacion propios de la raiz.

Las macros especializadas, pruebas, ejemplos, importaciones puntuales y utilidades deben vivir en subdirectorios.

## Archivos que deben quedarse en la raiz

- `ElectricCRLoader.FCMacro`: carga y recarga el workbench ElectricCR.
- `MEPWorkbenchCRLoader.FCMacro`: carga y recarga el workbench MEPWorkbenchCR.
- `GameEngineExportLoader.FCMacro`: carga y recarga el workbench GameEngineExportWB.
- `Alias.FCMacro`: herramienta general para asignar alias en hojas Spreadsheet.
- `AbrirDirectorioDocumento.FCMacro`: abre la carpeta donde esta guardado el documento activo.
- `VentanadeMacros.FCMacro`: ventana general para buscar y ejecutar macros.
- `MacrosPersonalizadas.FCMacro`: crea menus de macros personalizadas y recientes.

Los SVG de esas macros pueden quedar junto a los `.FCMacro` porque FreeCAD suele resolver mejor los iconos de barra cuando estan al lado de la macro.

## Directorios importantes

- `Macros-de-Freecad`: proyecto principal con ElectricCR, MEPWorkbenchCR, GameEngineExportWB y macros asociadas.
- `Scripts Varios`: macros y scripts utiles, pero no centrales para el arranque de FreeCAD.
- `Respaldos`: archivos archivados, copias antiguas, recursos duplicados y movimientos conservadores.
- `Reportes`: salidas generadas por herramientas de diagnostico.
- `Documentacion_organizacion`: esta documentacion.

## Workbenches separados

- `Macros-de-Freecad/ElectricCR`: codigo del workbench ElectricCR.
- `Macros-de-Freecad/MEPWorkbenchCR`: codigo del workbench MEPWorkbenchCR.
- `Macros-de-Freecad/GameEngineExportWB`: codigo del workbench GameEngineExportWB.

ElectricCR, MEPWorkbenchCR y GameEngineExportWB son workbenches diferentes. No se deben registrar como grupos internos unos de otros.

## Nota sobre caches

Los directorios `__pycache__` son generados automaticamente por Python/FreeCAD. Si se borran o archivan, normalmente se regeneran. No deben usarse como fuente de verdad para recuperar codigo.
