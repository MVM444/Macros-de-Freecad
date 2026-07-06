# Exportar DXF/DWG Plano de Trabajo

Macro asociada:
`Exportar_DXF_DWG_Plano_Trabajo.FCMacro`

## Objetivo

Exportar a DXF/DWG solo elementos 2D del plano de trabajo, convirtiendo unidades de FreeCAD en milimetros a metros en el archivo exportado.

## Estado Actual

- Exporta geometria seleccionada que esta en el plano de trabajo.
- Extrae la parte 2D de objetos compuestos 2D+3D, como tomacorrientes.
- Puede incluir etiquetas de iluminacion mediante panel de opciones.
- En DXF, las etiquetas de iluminacion se insertan como entidades `TEXT` nativas para que sean legibles y editables.
- Por compatibilidad con visores CAD, las entidades `TEXT` se escriben por ahora en capa `0`.
- Si la seleccion actual ya contiene esas etiquetas y tambien se marca `Etiquetas de iluminacion`, se deduplican por `Name`; no deberian exportarse dos veces.
- La conversion a contornos (`ShapeString`) queda desactivada por defecto porque produjo texto hueco y poco legible.
- Si no encuentra Working Plane de Draft, usa plano XY con Z=0.
- Escala de exportacion: `0.001` para mm -> m.
- Debug activo con `DEBUG_EXPORT = True`.

## Panel De Exportacion

La macro muestra opciones para elegir:

- Seleccion actual.
- Etiquetas de iluminacion.

Las etiquetas esperadas son textos tipo `Etiqueta_*`, ubicados dentro del grupo `Etiquetas`, por ejemplo:
`Areas de iluminacion / Etiquetas`.

## Debug

Al ejecutar, revisar la consola de FreeCAD por lineas:

```text
[DXF][DEBUG] Seleccion revisada: ...
[DXF][DEBUG] Seleccion exportable: geometria_2d=X textos=Y
[DXF][DEBUG] Textos candidatos en documento=X | etiquetas iluminacion=Y
[DXF][DEBUG] DXF con textos nativos: exportando geometria a temporal con importDXF.
[DXF][DEBUG] TEXT nativo insertado en DXF: objetos_texto=X lineas_texto=Y capa=0
[DXF][DEBUG] DXF final actualizado desde temporal: ...
[DXF][INFO] Exportado: ... | geometria=X | textos=Y
```

Si las etiquetas no aparecen en el DXF, copiar las lineas `[DXF][DEBUG]`, `[DXF][WARN]` y `[DXF][ERROR]`.

## Resultado Del Debug 2026-07-01

El log mostro que la macro detecto correctamente:

- `46` textos candidatos.
- `46` etiquetas de iluminacion.
- Grupo: `Areas de Iluminacion / Etiquetas`.
- Las etiquetas fueron clonadas, pero el DXF no las mostro como texto Draft.

Primera decision aplicada: exportar las etiquetas como contornos geometricos usando `TEXT_AS_OUTLINES = True`.

Resultado visual posterior: los contornos si aparecieron, pero el texto se veia hueco, cortado y poco legible.

Decision vigente: usar `TEXT_AS_DXF_TEXT = True` y `TEXT_AS_OUTLINES = False`. La macro exporta geometria normal a un DXF temporal, inyecta entidades `TEXT` nativas en la seccion `ENTITIES` y luego reemplaza el archivo final. Las entidades se escriben con estructura `AcDbEntity`/`AcDbText` y capa `0`.

## Pendientes

- Confirmar visualmente que las etiquetas `TEXT` nativas aparecen con buen tamano y posicion en AutoCAD/visor DXF.
- Desactivar `DEBUG_EXPORT` cuando el flujo quede estable.
