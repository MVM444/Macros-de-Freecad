Descripcion: Registro de chat para el workbench GameEngineExportWB. Mantener ASCII y mensajes claros.
Fecha y hora: 2025-10-13 17:46:58 UTC.
Instrucciones clave:
- Actualizar este archivo con resenas breves de cada sesion.
- Registrar decisiones relevantes y comandos ejecutados.
- Mantener prefijo [GAMEEXPORT] en notas de consola cuando aplique.

[2025-10-13 17:46 UTC] Session note: El usuario solicito instrucciones para abrir el proyecto en Visual Studio Code y verlo en FreeCAD. Se creo esta bitacora y se actualizo el README con pasos detallados.
[2025-10-13 19:09 UTC] Session note: El usuario no localiza el workbench en GitHub ni en el disco. Se agrego una seccion de ubicacion en el README y se recordo la macro GameEngineExportLoader.
[2025-10-13 19:55 UTC] Session note: Se confirmo la ubicacion del loader creando el archivo `GameEngineExportLoader.FCMacro` en la raiz y se actualizo el README con instrucciones detalladas.
[2025-11-21 15:16 UTC] Session note: Se agrego una comparacion Workbench vs macro en el README para explicar ventajas y usos de cada enfoque; se mantiene la eleccion de Workbench y la macro loader solo para recarga rapida.
[2025-11-21 15:39 UTC] Session note: Se brindo al usuario una explicacion en el chat sobre el estado actual del workbench y de la macro GameEngineExportLoader; se actualizo la bitacora segun lo solicitado.
[2025-11-21 15:41 UTC] Session note: El usuario pidio ver la explicacion en el chat sobre por que se usa un workbench y no solo una macro; se respondio directamente en el chat con ventajas y casos de uso, y se registro esta nota.
[2025-11-21 16:30 UTC] Session note: Se ajusto el TaskPanel para evitar la salida duplicada entre Config y Escena y se establecieron valores por defecto tomando la carpeta y el nombre base del documento activo.
[2025-11-21 17:20 UTC] Session note: Se documento en el README como aplicar cambios en Visual Studio Code y recargar el workbench usando la macro loader.
[2026-03-11 00:00 UTC] Session note: Se corrigio la apertura del panel cerrando cualquier TaskDialog activo antes de showDialog y se habilito seleccion con mouse en 3D para llenar la lista de exportacion (boton Use 3D selection, refresco desde raiz/seleccion, mover items entre listas).
[2026-03-11 17:50 UTC] Session note: Se registro como regla fija de exportacion aplicar conversion de ejes FreeCAD->X3D (scale 0.001 y rotacion -90 en X) para evitar que el piso se vea como pared. Se implemento soporte para X3D comprimido (gzip) sin perder la conversion.
[2026-03-11 18:00 UTC] Session note: Se ajusto exporter_x3d para nunca dejar un archivo .x3d comprimido (solo .x3dz usa gzip). Ademas se agrega reporte de objetos no exportables en consola con razon (tipo/helper/sin geometria) antes de exportar.
