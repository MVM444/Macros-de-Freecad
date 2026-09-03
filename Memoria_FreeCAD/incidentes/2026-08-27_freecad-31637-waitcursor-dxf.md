# FreeCAD #31637 - WaitCursor persistente al importar DXF por Python

Fecha: 2026-08-27 America/Costa_Rica
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.4 / 2026.08.27.1
Estado: WORKAROUND IMPLEMENTADO Y VERIFICADO MCP / PENDIENTE USUARIO

## Sintoma generalizable

Una importacion DXF/DWG mediante `importDXF.insert()` puede terminar, mostrar
geometria y permitir dialogos modales, mientras la ventana principal parece
trabada. Windows puede reportar `Responding=True` y los QTimer pueden ejecutarse.
El indicador decisivo es `QApplication.overrideCursor() = Qt.WaitCursor` junto
con ausencia de eventos de botones y teclado.

## Evidencia

Prueba A stock con el boton real:

- cursor previo: `None`;
- cursor posterior: WaitCursor shape 3 durante mas de 24 s;
- QTimer y CPU activos;
- movimiento/rueda presentes;
- cero press/release y cero teclas despues del mensaje.

Prueba B en sesion nueva:

- se verifico que `FreeCADGui.suspendWaitCursor` y `resumeWaitCursor` son
  reemplazables;
- no existia cursor externo antes de instalar la sonda;
- ambas se reemplazaron por no-op solo durante `importDXF.insert` y se restauraron
  en `finally`;
- cursor siempre `None`;
- pan, zoom, seleccion y teclado respondieron inmediatamente.

La geometria fue identica: 139 importados/140 totales, 15 textos, 15 capas,
53 links, Puertas=11, Ventanas=15 y escala correcta.

## Conclusion

El resultado A bloquea / B responde confirma practicamente la causa descrita en:

- https://github.com/FreeCAD/FreeCAD/issues/31637
- https://github.com/FreeCAD/FreeCAD/pull/31639
- https://github.com/FreeCAD/FreeCAD/commit/57456ac

No confundir este estado con una operacion CAD todavia ejecutandose ni con un
freeze de Coin3D. No aplicar llamadas extra de `resumeWaitCursor()` sin entender
el balance de instancias.

## Compatibilidad productiva 0.14.4

`core/freecad_compat.py` inspecciona mediante AST o bytecode la implementacion
real de `importDXF._import_dxf_file()` y devuelve `affected`, `not_affected` o
`unknown`.

- `affected`: neutraliza temporalmente `suspendWaitCursor` y
  `resumeWaitCursor` solo durante la llamada sincrona a `importDXF.insert()`;
- `not_affected`: ejecuta el importador normal y registra que la correccion fue
  detectada;
- `unknown`: advierte y no modifica agresivamente funciones globales.

FreeCAD 1.1.3 tiene respaldo explicito cuando la inspeccion no esta disponible,
porque fue verificado A/B. Una deteccion estructural de codigo corregido siempre
prevalece, incluso si la version sigue reportando 1.1.3 por un backport.

Las identidades originales se restauran en `finally`. Una prueba con excepcion
controlada en FreeCAD real y las pruebas unitarias confirmaron esa restauracion.
No se modifico `src/Mod/Draft/importDXF.py` ni parametros globales permanentes.

## Verificacion productiva

En una sesion nueva se ejecutaron tres DWG consecutivos y un DXF desde el boton
real. Los DWG produjeron 139/140 objetos y el DXF 137/138. Cero muestras quedaron
en WaitCursor; mouse, pan, zoom, seleccion y teclado respondieron. Preferencias y
funciones nativas coincidieron con el baseline despues de cada importacion.

Para retirar o desactivar el workaround en FreeCAD futuro, confirmar que el log
muestre `not_affected` y `FreeCAD DXF WaitCursor fix detected; workaround
disabled`, y ejecutar la regresion sin monkeypatch. La aceptacion de 0.14.4 sigue
pendiente de la prueba manual del usuario.
