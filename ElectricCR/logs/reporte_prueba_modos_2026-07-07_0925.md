# Reporte prueba modos - ElectricCR

## Objetivo

Implementar una primera prueba pequena, reversible y funcional de interfaz por
modos manuales dentro del unico Workbench ElectricCR.

La prueba no reorganiza macros, no crea workbenches separados, no separa aun
la barra `Conectar` y no implementa un ribbon.

## Investigacion previa

Fuentes revisadas:

- FreeCAD Workbench creation:
  https://wiki.freecad.org/Workbench_creation/es
- FreeCAD PySide:
  https://wiki.freecad.org/PySide
- Qt for Python QDockWidget:
  https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QDockWidget.html
- FreeCAD source example with `FreeCADGui.getMainWindow()`:
  https://github.com/FreeCAD/FreeCAD/blob/main/src/Tools/embedded/PySide/mainwindow.py

Hallazgos:

- FreeCAD Python workbenches se inicializan desde `InitGui.py` y usan
  `appendToolbar` / `appendMenu` para publicar comandos.
- PySide es la via esperada para crear paneles Qt dentro de FreeCAD.
- `QDockWidget` es adecuado para una paleta acoplable reutilizable dentro de
  un `QMainWindow`.
- FreeCAD expone la ventana principal con `FreeCADGui.getMainWindow()`.
- Para evitar paneles duplicados, la opcion mas segura es buscar un
  `QDockWidget` por `objectName` estable antes de crear uno nuevo.

Enfoque seleccionado:

- Crear un `QDockWidget` simple llamado `ElectricCRModePanel`.
- Reutilizarlo si ya existe.
- Mantener `InitGui.py` como punto de registro y mover la logica nueva a
  modulos `ElectricCR/ui/mode_manager.py` y `ElectricCR/ui/mode_panel.py`.
- Controlar solo las barras de macros administradas por modos.
- Dejar Draft, BIM y Arch fuera de esta primera prueba.

## Mapeo final de modos y barras

| Modo | Barras visibles administradas |
|---|---|
| General | Areas, Objetos |
| Iluminacion 2D | Iluminacion |
| Tomacorrientes 2D | Tomacorrientes |
| Conexiones 2D | Conectar |
| Conexiones 3D | Conectar, Cajas |
| Tableros | Tableros |

La barra `ElectricCR` permanece visible siempre.

## Archivos creados

- `ElectricCR/ui/__init__.py`
- `ElectricCR/ui/mode_combo.py`
- `ElectricCR/ui/mode_manager.py`
- `ElectricCR/ui/mode_panel.py`
- `ElectricCR/tests/simulate_mode_interface.py`
- `ElectricCR/logs/reporte_prueba_modos_2026-07-07_0925.md`

## Archivos modificados

- `ElectricCR/InitGui.py`
- `ElectricCR/config.json`
- `ElectricCR/README.md`

Tambien hay cambios previos de esta sesion en:

- `ElectricCR/usage_log.py`
- `ElectricCR/commands/macro_launcher.py`
- `ElectricCR/logs/tool_usage.json`
- `ElectricCR/logs/reporte_macros_mas_usadas_2026-07-07.md`
- `ElectricCR/logs/analisis_flujos_barras_2026-07-07.md`
- `ElectricCR/logs/reporte_trabajo_2026-07-07_0835-0900.md`

## Configuracion agregada

`ElectricCR/config.json` ahora incluye:

- `interface_mode: "modes_prototype"`
- `mode_panel_enabled: true`
- `work_modes`
- `mode_toolbar_names`

Para volver al comportamiento anterior:

```json
"interface_mode": "legacy"
```

## Ajuste posterior: selector desplegable

Se agrego `ElectricCR/ui/mode_combo.py` para mostrar una lista desplegable de
modos directamente en la barra `ElectricCR`, similar conceptualmente al
selector de Workbench de FreeCAD.

El combo usa:

```text
objectName = ElectricCRModeCombo
```

Al recargar ElectricCR, el codigo busca ese widget antes de crear otro. Si ya
existe, lo reutiliza y reconecta su senal de cambio de modo.

## Como se evita duplicar el panel

El panel usa:

```text
objectName = ElectricCRModePanel
```

Antes de crear un panel nuevo, `mode_panel.ensure_panel()` busca en
`FreeCADGui.getMainWindow()` un `QDockWidget` con ese `objectName`.

Si existe:

- se reutiliza el panel;
- se actualiza su contenido si hace falta;
- se registra en consola `panel_reused=True`.

Si no existe:

- se crea el `QDockWidget`;
- se agrega a la zona derecha;
- se registra `panel_reused=False`.

## Como se guarda el ultimo modo

`mode_manager.py` usa parametros de FreeCAD:

```text
User parameter:BaseApp/Preferences/Mod/ElectricCR
```

Clave:

```text
last_work_mode
```

Al activar el Workbench, ElectricCR lee ese valor y aplica el modo guardado.
Si el valor no existe o no es valido, usa `general`.

## Resultados de validacion

Comandos ejecutados:

```powershell
python -m py_compile ElectricCR\InitGui.py ElectricCR\ui\__init__.py ElectricCR\ui\mode_manager.py ElectricCR\ui\mode_panel.py ElectricCR\ui\mode_combo.py ElectricCR\commands\macro_launcher.py ElectricCR\usage_log.py ElectricCR\tests\simulate_mode_interface.py
python -m json.tool ElectricCR\config.json
python ElectricCR\tests\simulate_mode_interface.py
```

Resultado:

- Compilacion Python: correcta.
- JSON de configuracion: valido.
- Simulacion con stubs: correcta.

La simulacion valido:

- creacion del panel;
- reutilizacion del panel;
- cambio entre los seis modos;
- cambio de modo desde la lista desplegable;
- reutilizacion de la lista desplegable;
- visibilidad esperada por modo;
- permanencia de la barra `ElectricCR`;
- ausencia de error si falta la barra `Cajas`;
- reporte de barra faltante con `missing=Cajas`.

Salida relevante:

```text
[ElectricCR][Mode] selected=Iluminacion_2D
[ElectricCR][Mode] visible=ElectricCR,Iluminacion
[ElectricCR][Mode] hidden=Areas,Objetos,Tomacorrientes,Conectar,Cajas,Tableros
[ElectricCR][Mode] selected=Conexiones_3D
[ElectricCR][Mode] visible=ElectricCR,Conectar,Cajas
[ElectricCR][Mode] hidden=Areas,Objetos,Iluminacion,Tomacorrientes,Tableros
[ElectricCR][Mode] missing=Cajas
simulate_mode_interface: PASS
```

## Limitaciones conocidas

- No se probo visualmente dentro de FreeCAD real.
- La prueba usa barras existentes, no una paleta final de comandos.
- `Conectar` sigue completa en Conexiones 2D y Conexiones 3D.
- Draft, BIM y Arch no se modifican en esta fase.
- La visibilidad depende de que FreeCAD haya creado las barras esperadas.
- La cabecera historica de `InitGui.py` conserva texto viejo de codificacion
  previa; se agrego una cabecera ASCII nueva sin hacer refactor masivo.

## Pasos para prueba manual en FreeCAD

1. Abrir FreeCAD 1.1.1.
2. Activar el Workbench `ElectricCR`.
3. Usar `Recargar ElectricCR` si FreeCAD ya estaba abierto.
4. Confirmar que aparece una lista desplegable de modos en la barra
   `ElectricCR`.
5. Opcional: abrir `ElectricCR Modos` desde el menu ElectricCR para mostrar
   el panel acoplable.
6. Seleccionar `Iluminacion 2D` desde la lista desplegable.
7. Confirmar visibles: `ElectricCR`, `Iluminacion`.
8. Seleccionar `Tomacorrientes 2D`.
9. Confirmar visibles: `ElectricCR`, `Tomacorrientes`.
10. Seleccionar `Conexiones 2D`.
11. Confirmar visibles: `ElectricCR`, `Conectar`; confirmar que `Cajas` no aparece.
12. Seleccionar `Conexiones 3D`.
13. Confirmar visibles: `ElectricCR`, `Conectar`, `Cajas`.
14. Seleccionar `General`.
15. Confirmar visibles: `ElectricCR`, `Areas`, `Objetos`.
16. Cerrar y abrir FreeCAD.
17. Confirmar que se recuerda el ultimo modo seleccionado.
18. Recargar ElectricCR.
19. Confirmar que no aparecen paneles, botones ni listas desplegables duplicadas.

## Siguiente paso sugerido

Usar este prototipo durante trabajo real y revisar `tool_events.jsonl` despues
de acumular eventos. Con esos datos, separar `Conectar` en 2D/3D y convertir
las barras de fase en una paleta de comandos por modo.
