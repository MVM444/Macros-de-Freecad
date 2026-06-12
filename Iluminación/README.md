# Iluminacion

## Bitacora de modificaciones

Fecha de inicio: 2026-06-08 17:53:46 America/Costa_Rica

### Respaldo base

Antes de modificar archivos se creo el respaldo:

`../Respaldos/Iluminacion_20260608_175346/`

Archivos respaldados:

- `lighting_schedule_export.py`
- `Actualizar_Tabla_Iluminacion.FCMacro`
- `Hoja_Iluminacion.FCMacro` (archivo real con acento en el nombre)

### Cambios aplicados

- 2026-06-08 17:53:46: se creo este README como bitacora de trabajo.
- 2026-06-08 17:53:46: se genero el respaldo base antes de modificar logica.
- 2026-06-08 17:55: se ajusto `lighting_schedule_export.py` para detectar variantes de grupos de iluminacion como `Electric/ILUMINACION`, `electrico/Iluminacion` y contenedores `CIRCUITOS DE ILUMINACION`.
- 2026-06-08 17:55: si no existe grupo de iluminacion, el exportador ahora crea la estructura minima `Electric/ILUMINACION` antes de generar las hojas.
- 2026-06-08 18:00: se amplio la deteccion de luminarias para considerar nombres/etiquetas del `App::Link` y del objeto enlazado.
- 2026-06-08 18:00: si el grupo de iluminacion esta vacio, el exportador ahora busca luminarias en todo el documento y reconstruye la ruta de grupos desde `InList`.
- 2026-06-08 18:17: antes de modificar `Etiquetas.FCMacro`, se creo respaldo en `../Respaldos/Iluminacion_Etiquetas_20260608_181721/`.
- 2026-06-08 18:17: `Etiquetas.FCMacro` ahora intenta importar `QInputDialog` desde `PySide2`, `PySide6` o `PySide` clasico segun la version disponible en FreeCAD.
- 2026-06-10 08:20: antes de actualizar esta bitacora, se respaldo `README.md` en `../Respaldos/Iluminacion_Completa_20260610_082008/`.
- 2026-06-10 08:20: se agrego `Actualizar_Iluminacion_Completa.FCMacro`, macro nueva que no modifica las macros anteriores.
- 2026-06-10 08:20: la macro completa actualiza `DatosRecintos`, corrige/infiere `Descripcion`, reescribe `Tabla Iluminacion Legacy` sin duplicarla y recrea el subgrupo `Etiquetas`.
- 2026-06-10 08:20: si una descripcion no se puede inferir, se usa `Oficina` como valor aceptado de respaldo y se avisa en consola.
- 2026-06-10 08:20: se agregaron alias simples para inferir descripciones desde nombres de recintos como `Boveda`, `Cuarto de Aseo`, `Suministros`, `Comedor` y `Servidor`.
- 2026-06-10 08:59: antes de modificar `Actualizar_Iluminacion_Completa.FCMacro`, se respaldo la macro y este README en `../Respaldos/Iluminacion_Completa_Panel_20260610_085902/`.
- 2026-06-10 08:59: `Actualizar_Iluminacion_Completa.FCMacro` ahora tiene panel para escoger grupo de recintos, hoja de datos, hoja legacy y grupo de etiquetas.
- 2026-06-10 08:59: el panel guarda la ultima configuracion en preferencias de FreeCAD para evitar seleccionar lo mismo en cada ejecucion.
- 2026-06-10 08:59: se agrego validacion visual de descripciones mediante lista desplegable por recinto, usando los valores aceptados por el calculo.
- 2026-06-10 08:59: se agrego `Actualizar_Iluminacion_Completa.svg` y la cabecera `Icon` para que ElectricCR muestre icono propio en la seccion `Iluminacion`.
- 2026-06-10 09:19: antes de ajustar pasillos y toolbar, se respaldo la macro y este README en `../Respaldos/Iluminacion_Pasillos_Toolbar_20260610_091937/`.
- 2026-06-10 09:19: la inferencia de `Descripcion` ahora prioriza `Pasillo` antes que `Servicio Sanitario`, para nombres como `Pasillo S.S.` o pasillos con referencia al recinto vecino.
- 2026-06-10 09:19: si el nombre del recinto contiene `Pasillo`, la macro fuerza la descripcion `Pasillo` aunque antes existiera otra descripcion valida guardada.
- 2026-06-10 09:19: se cambio la cabecera de toolbar de la macro completa a `Iluminación` y se ajusto `ElectricCR/config.json` para evitar una segunda barra `Iluminacion`.
- 2026-06-10 09:28: se archivaron macros/archivos antiguos o reemplazados en `../Respaldos/Iluminacion_Archivadas_20260610_092800/`.
- 2026-06-10 09:28: archivos archivados: `Actualizar_Tabla_Iluminacion.FCMacro`, `Etiquetas.FCMacro`, `Hoja_Iluminación_Legacy.FCMacro`, `AsisCSV2Pasos.nobom.tmp`, `AsisCSV2Pasos.WIP.txt`, `test_small_file.txt`.
- 2026-06-10 09:51: antes de agregar la guia visible, se respaldo este README en `../Respaldos/Iluminacion_Guia_20260610_095141/`.
- 2026-06-10 09:51: se agrego `Guia_Iluminacion.FCMacro` con una ventana de flujo recomendado y botones para ejecutar la macro principal o abrir este README.
- 2026-06-10 09:51: se agrego `Guia_Iluminacion.svg` para que la guia sea visible como herramienta en la barra `Iluminación`.
- 2026-06-10 10:08: antes de mejorar la guia visible, se respaldo `Guia_Iluminacion.FCMacro` y este README en `../Respaldos/Iluminacion_Guia_Mejorada_20260610_100837/`.
- 2026-06-10 10:08: `Guia_Iluminacion.FCMacro` ahora explica el flujo desde la base del proyecto hasta organizacion/exportacion, e incluye boton para ejecutar `Areas/AsignarNombreEstandar.FCMacro`.
- 2026-06-10 10:18: antes de reorganizar la guia como lista operativa, se respaldo `Guia_Iluminacion.FCMacro` y este README en `../Respaldos/Iluminacion_Guia_Operativa_20260610_101800/`.
- 2026-06-10 10:18: `Guia_Iluminacion.FCMacro` se reorganizo para uso practico al retomar un proyecto: incluye lista de verificacion, tabla de flujo completo, ejemplos de descripcion, advertencias sobre luminarias y errores frecuentes.
- 2026-06-10 10:51: antes de corregir contraste visual, se respaldo `Guia_Iluminacion.FCMacro` y este README en `../Respaldos/Iluminacion_Guia_Contraste_20260610_105126/`.
- 2026-06-10 10:51: `Guia_Iluminacion.FCMacro` ahora fija colores explicitos en el visor HTML, recuadros, tablas y bloques preformateados para evitar texto blanco sobre fondo claro en temas oscuros de FreeCAD.

### Recuento actual

Macros activas en `Iluminación`:

- `Actualizar_Iluminacion_Completa.FCMacro`: flujo principal actual; actualiza recintos, hoja legacy y etiquetas con panel persistente.
- `AsisCSV2Pasos.FCMacro`: asistente de importacion CSV a sketches/objetos.
- `ColocarLuminarias_Link.FCMacro`: coloca luminarias por rejilla usando `App::Link`.
- `ColocarLuminarias_Objeto.FCMacro`: coloca luminarias como objeto parametricos.
- `Exportar_Luminarias_CSV_ElectricCR.FCMacro`: exporta luminarias `App::Link` a CSV.
- `Hoja_Iluminación.FCMacro`: exportador nuevo de hojas por circuito/detalle mediante `lighting_schedule_export.py`.
- `Guia_Iluminacion.FCMacro`: recordatorio visual del flujo recomendado dentro de FreeCAD.
- `Luminaria_Link_Sketch.FCMacro`: inserta `App::Link` desde puntos de sketch.
- `Organizar_Luminarias_por_Circuito_y_Apagador.FCMacro`: organiza luminarias por circuito, recinto y apagador.
- `Reemplazar_Luminaria.FCMacro`: utilidad para sustituir luminarias.

Archivos de soporte activos:

- `Actualizar_Iluminacion_Completa.svg`
- `Guia_Iluminacion.svg`
- `Organizar_Luminarias_por_Circuito_y_Apagador.svg`
- `lighting_schedule_export.py`

### Flujo recomendado actual

Abrir primero `Guia_Iluminacion.FCMacro` si no se recuerda el flujo. Esa ventana resume los pasos y permite ejecutar `Areas/AsignarNombreEstandar.FCMacro` o `Actualizar_Iluminacion_Completa.FCMacro`.

El flujo de iluminacion empieza antes de las macros de iluminacion. Primero debe existir una base arquitectonica o grafica del proyecto.

Orden corto para recordar:

```text
Base -> Areas -> Nombres estandar -> Actualizar iluminacion completa -> Luminarias -> Circuitos/exportacion
```

1. Importar o preparar la base del proyecto: CAD, imagen, PDF usado como referencia, PDF convertido o dibujo base en FreeCAD.
2. Crear rectangulos que representen cada recinto o area funcional.
3. Agrupar esos rectangulos dentro de un grupo de areas, por ejemplo `Areas`.
4. Ejecutar `Areas/AsignarNombreEstandar.FCMacro` para evitar nombres genericos como `Rectangle001`.
5. Revisar que los recintos tengan nombres claros: `Oficina`, `Pasillo`, `Sala_Espera`, `Bodega`, `Servicio_Sanitario`, etc.
6. Ejecutar `Iluminación/Actualizar_Iluminacion_Completa.FCMacro`.
7. En el panel, escoger grupo de recintos, hoja de datos, hoja legacy y grupo de etiquetas.
8. Validar la descripcion de cada recinto en la lista desplegable.
9. Confirmar para actualizar `DatosRecintos`, `Tabla Iluminacion Legacy` y `Etiquetas`.
10. Colocar luminarias registradas o usar el flujo de sketch/base object cuando corresponda.
11. Organizar por circuito y apagador.
12. Exportar resultados si corresponde.

Ejemplo de grupo:

```text
Areas
+-- Oficina
+-- Pasillo
+-- Sala_Espera
+-- Servicio_Sanitario
+-- Bodega
+-- Comedor
```

La descripcion de recintos es importante porque define el criterio de iluminacion. Ejemplo: `Pasillo S.S.` debe clasificarse como `Pasillo`, no como `Servicio Sanitario`.

Si se esta retomando un proyecto existente, primero revisar:

1. Que exista el grupo de areas.
2. Que no queden recintos con nombres genericos como `Rectangle001`.
3. Que la macro completa apunte a las hojas correctas.
4. Que la descripcion de cada recinto se valide desde el panel, no escribiendola manualmente en `DatosRecintos`.

### Macros de calculo

- Usar `Actualizar_Iluminacion_Completa.FCMacro` como flujo principal.
- No usar directamente `Hoja_Iluminación_Legacy.FCMacro` ni `Etiquetas.FCMacro`; quedaron archivadas porque la macro completa incorporo ese flujo que era el que funcionaba.
- `Hoja_Iluminación.FCMacro` queda como exportador nuevo por circuito/detalle. Si no da el resultado esperado para un proyecto, usar la macro completa hasta estabilizar ese exportador.

### Colocar luminarias

- `ColocarLuminarias_Link.FCMacro` no sirve para seleccionar cualquier objeto como luminaria. Usa el registro `Resources/registry/registry_electric.json` y crea `App::Link` a un master generado desde ElectricCR.
- `ColocarLuminarias_Objeto.FCMacro` tambien usa el registro y `crear_toma_uno`; no es el flujo "seleccionar cualquier objeto y repetirlo como luminaria".
- `Luminaria_Link_Sketch.FCMacro` si tiene dos motores: `Base object` para enlazar a un objeto base existente y `Registry master` para usar el registro. Es la opcion mas cercana al flujo de "usar un objeto como luminaria", pero requiere puntos de sketch como posiciones.
- Para evitar retrabajo, no asumir que las macros de colocar luminarias aceptan cualquier objeto seleccionado hasta que ese flujo se rediseñe explicitamente.

### Registro y nombres

- Las macros de colocar luminarias con registro leen `Resources/registry/registry_electric.json`.
- La inferencia de descripcion de recintos en `Actualizar_Iluminacion_Completa.FCMacro` es solo una ayuda. Para proyectos grandes conviene usar `NombresEstandar` como fuente editable de nombres y, mas adelante, agregar ahi la descripcion de iluminacion.

### Notas de trabajo

- `Hoja_Iluminación.FCMacro` funciona como lanzador de `lighting_schedule_export.py`.
- Cualquier ajuste nuevo debe conservar compatibilidad con FreeCAD y PySide2.
