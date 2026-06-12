# Areas - notas de avance

Fecha: 2026-06-08

Este directorio contiene macros para crear, nombrar y usar poligonos/rectangulos de recintos en FreeCAD/ElectricCR.

## Bitacora

- 2026-06-10: antes de agregar la guia visible de Areas, se respaldo `README.md` y posibles archivos de guia en `../Respaldos/Areas_Guia_Areas_20260610_105630/`.
- 2026-06-10: se agrego `Guia_Areas.FCMacro` como ventana practica de flujo de trabajo para la barra `Areas`.
- 2026-06-10: se agrego `Guia_Areas.svg` junto a la macro y en `ElectricCR/icons/Areas/Guia_Areas.svg`; el icono usa un signo de pregunta para identificarlo como ayuda/guia.

## Convenciones actuales

- Las areas generadas deben vivir preferiblemente en el grupo `Areas`.
- Tambien se reconocen grupos destino con nombres tipo `Recintos`, `Espacios` o `Zonas`.
- Los objetos generados deben mantener coherencia con `AreaPorClick`:
  - `ElectricCRTipo = "Area"`
  - `GeneratedBy = <macro>`
  - `AreaM2`
  - `VirtualClosures`
  - `Confidence`
  - color de linea verde, cara verde y transparencia.
- Los iconos de macros nuevas deben existir junto a la macro y tambien en `ElectricCR/icons/Areas`.
- Si se agregan macros o iconos, recargar el workbench ElectricCR.

## AreaPorClick.FCMacro

Macro principal de trabajo por recintos.

### Modo poligono

Boton: `Iniciar clicks`

Flujo:

1. `Reconstruir` arma una red desde objetos visibles, seleccion, grupo fuente o modo auto.
2. El usuario hace click dentro de un recinto.
3. La macro puede usar radar por click y calco de muros.
4. Crea un poligono tipo `Area_###`.

Cambios importantes aplicados hoy:

- Se admiten lineas auxiliares seleccionadas como cierres de area.
- Una linea simple dentro del grupo `Areas` ya no se descarta automaticamente si sirve como limite.
- `Origen=Auto` mantiene los objetos visibles y suma la seleccion como ayuda; ya no reemplaza todo el dibujo por solo lo seleccionado.
- Se mantiene el boton `Cerrar`.

### Modo rectangulo

Boton: `Iniciar rectangulos`

La primera version convertia el poligono detectado a una caja envolvente; eso produjo rectangulos erraticos en recintos con recovecos o trazos raros.

La version estable actual usa un metodo parecido a `RectFromBoundaryLines.FCMacro`, pero automatico:

1. El click dispara el radar.
2. Se toman los segmentos reales tocados por los rayos alrededor del click.
3. Se agrupan las lineas por orientacion.
4. Se buscan los limites a ambos lados del click.
5. Se calculan las 4 esquinas por interseccion de limites.
6. Se crea un rectangulo tipo `Area_###`.

Este metodo evita que una linea larga que atraviesa varios recintos deforme el rectangulo, porque selecciona limites alrededor del click.

Mensajes utiles en consola:

- `Rectangulo por limites: ...`
- `No se pudo calcular rectangulo por limites...`
- `Red lista: ...`

## PoligonoFromBoundaryLines.FCMacro

Macro creada hoy como alternativa basada en `RectFromBoundaryLines.FCMacro`, pero para poligonos.

Uso:

1. Seleccionar aristas o un objeto con aristas.
2. Ejecutar la macro.
3. La macro infiere lineas soporte, calcula intersecciones, recorta/omite sobrantes y crea el poligono mayor cerrado.

Notas:

- No requiere que las lineas formen un contorno cerrado exacto.
- Puede extender lineas cortas hasta esquinas cercanas.
- Puede recortar lineas largas.
- El resultado mantiene propiedades y estilo de `AreaPorClick`.

## AsignarNombreEstandar.FCMacro

Macro para asignar nombres desde la hoja `NombresEstandar`.

Cambios aplicados hoy:

- Importacion Qt compatible:
  - `PySide2`
  - `PySide`
  - `PySide6`
- Boton `Actualizar` para releer la hoja si se modifica la tabla.
- Los cuadros de advertencia usan la ventana principal como padre para aparecer encima.
- La ventana se autodimensiona segun los botones y usa scroll si hay muchos.

## Guia_Areas.FCMacro

Guia visual agregada a la barra `Areas`.

Incluye:

- Lista de revision para retomar un proyecto.
- Flujo recomendado desde base arquitectonica hasta areas nombradas.
- Explicacion rapida de `AreaPorClick`, `Iniciar rectangulos`, `PoligonoFromBoundaryLines` y `AsignarNombreEstandar`.
- Errores frecuentes y que revisar.
- Botones para abrir macros principales y este README.

## Respaldos relevantes del dia

Los cambios de hoy se respaldaron en `Respaldos/`.

Algunos puntos de restauracion utiles:

- `Areas_AreaPorClick_linea_auxiliar_20260608_121126`
- `Areas_PoligonoFromBoundaryLines_20260608_122238`
- `Areas_PoligonoFromBoundaryLines_abiertas_20260608_123204`
- `Areas_AreaPorClick_boton_rectangulos_20260608_133939`
- `Areas_AreaPorClick_rect_auto_boundary_20260608_135618`
- `Areas_AsignarNombreEstandar_pyside_20260608_142311`
- `Areas_AsignarNombreEstandar_refresh_20260608_173932`

Tambien existen respaldos experimentales de `AreaPorClick`; no todos son estables.

## Verificaciones realizadas

- `py_compile` en macros modificadas.
- Pruebas geometricas simuladas para:
  - poligono irregular tipo L;
  - rectangulo abierto;
  - linea larga recortada;
  - rectangulo por limites desde radar.

## Pendientes sugeridos

- Probar `Iniciar rectangulos` en mas recintos reales con columnas, buques y lineas largas.
- Si un recinto no genera rectangulo, activar debug visual y revisar que existan dos familias claras de limites alrededor del click.
- Mantener `pseudocodigo_area_por_click.md` como documento de diseno del algoritmo de areas.
