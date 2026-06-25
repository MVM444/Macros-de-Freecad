# Guia para investigar errores despues de la organizacion

Si FreeCAD muestra un error despues de la reorganizacion, usar esta guia antes de mover archivos de nuevo.

## 1. Identificar el tipo de error

### `No such file`, `FileNotFoundError`, `Unknown document`

Probable causa:

- la macro tiene una ruta fija;
- la macro era una prueba grabada;
- el archivo esperado se movio a `Scripts Varios` o `Respaldos`.

Primero revisar:

- `Documentacion_organizacion/MOVIMIENTOS_2026-06-22.md`
- `Scripts Varios`
- `Respaldos`

### `No module named ...`

Probable causa:

- falta agregar una carpeta al `sys.path`;
- se movio un modulo Python junto con sus dependencias;
- una macro espera que el modulo este en la raiz.

Casos conocidos:

- librerias `dxf*.py` ahora estan juntas en `Scripts Varios/DXF`.
- `GameEngineExportWB` ahora esta en `Macros-de-Freecad/GameEngineExportWB`.
- `MEPWorkbenchCR` real esta en `Macros-de-Freecad/MEPWorkbenchCR`; la carpeta raiz `MEPWorkbenchCR/` es un shim.
- `MEP/` en raiz es un shim legado para documentos que importan `MEP.*`.

### Iconos desaparecidos

Revisar:

- encabezado `# Icon:` al inicio de la macro;
- iconos dentro de `Macros-de-Freecad/ElectricCR/icons`;
- iconos junto a la macro si es una macro suelta;
- rutas en loaders.

### ElectricCR muestra barras que no corresponden

Revisar:

- `Macros-de-Freecad/ElectricCR/config.json`
- `Macros-de-Freecad/ElectricCR/commands/macros.py`

ElectricCR debe ignorar:

- `ElectricCR`
- `MEPWorkbenchCR`
- `GameEngineExport`
- `GameEngineExportWB`
- `Resources`
- `scripts`
- `Respaldos`
- `Xcluidos`

## 2. Revisar ubicaciones actuales

Raiz de `Macros` esperada:

```text
Alias.FCMacro
AbrirDirectorioDocumento.FCMacro
ElectricCRLoader.FCMacro
GameEngineExportLoader.FCMacro
MacrosPersonalizadas.FCMacro
MEPWorkbenchCRLoader.FCMacro
VentanadeMacros.FCMacro
```

Los iconos SVG de esas macros tambien pueden estar en la raiz, por ejemplo:

```text
AbrirDirectorioDocumento.svg
ElectricCRLoader.svg
GameEngineExportLoader.svg
MEPWorkbenchCRLoader.svg
```

Herramientas generales movidas:

```text
Scripts Varios/
```

Macros de ElectricCR:

```text
Macros-de-Freecad/
```

Workbenches:

```text
Macros-de-Freecad/ElectricCR/
Macros-de-Freecad/MEPWorkbenchCR/
Macros-de-Freecad/GameEngineExportWB/
```

## 3. No borrar inmediatamente

Si algo falla, primero buscar el archivo movido. Evitar borrar o rehacer estructura hasta confirmar:

- nombre exacto del archivo en el error;
- ruta que FreeCAD intenta abrir;
- si el archivo existe en `Scripts Varios`, `Macros-de-Freecad` o `Respaldos`.

## 4. Comandos utiles en PowerShell

Buscar archivo por nombre:

```powershell
Get-ChildItem -Recurse -Force -Filter "NombreArchivo*"
```

Buscar texto en macros:

```powershell
rg -n "texto_a_buscar" .
```

Listar macros visibles en la raiz:

```powershell
Get-ChildItem -File -Filter *.FCMacro
```

Validar sintaxis Python de una macro:

```powershell
python -m py_compile "ruta\macro.FCMacro"
```

## 5. Criterio para decidir si un archivo vuelve a raiz

Vuelve a raiz solo si:

- se ejecuta frecuentemente desde el dialogo de macros de FreeCAD;
- es un loader de workbench;
- es una herramienta general como `Alias`, `AbrirDirectorioDocumento`, `VentanadeMacros` o `MacrosPersonalizadas`.
- es el icono SVG asociado directamente a una macro de raiz.

No vuelve a raiz si:

- depende de un proyecto especifico;
- es ejemplo o prueba;
- es libreria de soporte;
- pertenece a ElectricCR, MEPWorkbenchCR o GameEngineExportWB.
