# TAREA_ACTUAL - MEPWorkbenchCR Sanitario Esparza

**Codigo:** `MEP-SAN-ESPARZA-20260826-V03`
**Fecha:** 2026-08-26
**FreeCAD objetivo:** 1.1.3
**Estado de entrada:** nucleo Python v0.5.0 implementado en Drive; incluye referencias espaciales `Boundary2D`; validacion FreeCAD real pendiente.

## Objetivo

Validar en FreeCAD 1.1.3 real el nucleo sanitario y su adaptador experimental sin modificar proyectos productivos. El alcance sigue limitado a:

```text
Tanque septico -> FAFA -> campo de infiltracion
```


## Primera validacion espacial en FreeCAD

Antes de crear tanque, FAFA o zanjas, usar un documento temporal y capturar cuatro referencias:

1. `LimitePropiedad`;
2. `HuellaEdificio`;
3. `AreaTanques`;
4. `AreaDrenaje`.

Aceptar inicialmente Draft Wire cerrado, Sketch cerrado, Part Wire/Face, Draft Rectangle/Polygon y, si es viable, lineas seleccionadas que formen un contorno cerrado. Convertirlas a `Boundary2D` sin modificar la geometria fuente. Verificar area, perimetro, centroide, contencion dentro de propiedad e intersecciones con el edificio. La prueba debe ser de lectura/dry-run antes de crear objetos derivados.

## Fuente de verdad

Trabajar sobre `MEPWorkbenchCR/` existente en Drive/entorno sincronizado. No crear copias paralelas del Workbench.

Archivos principales:

- `MEP/sanitary/septic.py`
- `MEP/sanitary/fafa.py`
- `MEP/sanitary/infiltration.py`
- `MEP/sanitary/system.py`
- `MEP/sanitary/freecad_adapter.py`
- `MEP/sanitary/freecad_objects.py`
- `MEP/sanitary/layout.py`
- `MEP/sanitary/documentation.py`
- `MEP/sanitary/case.py`
- `MEP/sanitary/examples/esparza_input_template.json`
- `tests/test_sanitary_core.py`
- `docs/SANITARIO_ESPARZA.md`
- `docs/ARQUITECTURA.md`

## Reglas

1. Leer `AGENTS.md` y documentacion vigente antes de modificar.
2. No usar el archivo real de Esparza para pruebas de escritura.
3. Crear documento FreeCAD temporal exclusivo para pruebas.
4. Ejecutar primero `dry_run=True` y revisar operaciones devueltas.
5. Despues probar `dry_run=False` en documento temporal.
6. No incorporar `FreeCADGui`, Qt ni dialogs al nucleo.
7. No crear boton ni `.FCMacro` hasta que el adaptador sea estable.
8. No convertir la geometria provisional FAFA 2:1 en dimension de diseno.
9. No seleccionar automaticamente productos comerciales.
10. Conservar una unica identidad futura 2D/3D; no implementar dos objetos manuales independientes.
11. Usar transaccion y comprobar Undo/Redo, guardar/reabrir y recompute.
12. No declarar validacion funcional sin evidencia en FreeCAD 1.1.3 real.

## Pruebas Python esperadas antes de FreeCAD

```text
pytest tests/test_sanitary_core.py
```

Estado conocido previo: `22 passed` y `compileall` aprobado.

## Prueba FreeCAD minima

Usar datos sinteticos claramente identificados como TEST, nunca como Esparza real:

- crear documento temporal;
- calcular sistema con dos tasas de infiltracion validas;
- obtener `geometry_spec`;
- ejecutar `create_preview_objects(..., dry_run=True)`;
- comprobar que no se crea ningun objeto;
- ejecutar dentro del documento temporal `dry_run=False`;
- verificar grupo `MEP_Sanitary_Preview`;
- verificar tanque, FAFA y zanjas generadas;
- Undo/Redo;
- guardar, cerrar y reabrir temporal;
- confirmar propiedades `MEPProvisional` y `MEPSource`.

## Diagnosticos a registrar

- version exacta de FreeCAD;
- ruta real desde la que cargo MEPWorkbenchCR;
- excepciones de `Part.makeBox` o transacciones;
- nombres de objetos creados;
- comportamiento de reejecucion: no duplicar objetos;
- cualquier dependencia accidental de GUI;
- diferencias entre Python normal y FreeCAD Python.

## Siguiente decision despues de la prueba

Si el preview es estable, proponer (no implementar sin revision) la conversion a objetos parametricos sanitarios con:

- identidad unica 2D/3D;
- propiedades autoritativas;
- tanque y FAFA editables;
- zanjas editables/recalculables;
- planta 2D y seccion;
- caja de distribucion;
- futura implantacion sobre poligono real del terreno.

## Documentacion requerida de Codex

Registrar resultado en:

- `RESULTADO_CODEX.md`;
- `ESTADO_PROYECTO.md` correspondiente al Workbench cuando exista/sea identificado;
- `docs/SANITARIO_ESPARZA.md` si cambia el estado tecnico.

No hacer commit/push hasta completar la prueba y revision indicada por el flujo general del proyecto.
