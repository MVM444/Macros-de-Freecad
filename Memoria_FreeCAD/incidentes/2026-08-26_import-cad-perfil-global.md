# Importacion CAD dependiente del perfil global DXF

Fecha: 2026-08-26  
Equipo: DESKTOP-5586S7P  
FreeCAD: 1.1.3  
Workbench: FacilArquitecturaWB 0.14.3 / 2026.08.26.1

## Hallazgo generalizable

`importDXF.readPreferences()` no confia solamente en `DxfImportMode`.
Antes de cada importacion reconstruye ese entero desde:

- `dxfImportAsDraft`;
- `dxfImportAsPrimitives`;
- `dxfImportAsFused`;
- y el valor predeterminado de formas individuales.

Por eso un wrapper que solo fuerce `dxfScaling` y `dxfShowDialog` sigue
dependiendo de la configuracion global del usuario.

En el mismo DXF convertido:

- fusionado rico: 139 objetos;
- formas individuales: 5.679 objetos.

Cuando un Workbench necesita un resultado reproducible, debe aplicar un perfil
temporal completo, ejecutar el importador y restaurar exactamente cada clave,
incluidas las que no existian antes. No debe dejar las preferencias alteradas.

## Diagnostico MCP

Un timeout MCP no demuestra que FreeCAD siga importando. En una corrida, la
llamada de consulta agoto 90 s, pero el estado almacenado mostro:

- comando terminado en 6.60 s;
- QMessageBox cerrado;
- QTimer de 0/100/500/1000/2000 ms ejecutados;
- FreeCAD marcado por Windows como respondiendo;
- CPU sin incremento.

Separar siempre tiempo del comando y tiempo de despacho MCP.

## Escala

No confiar ciegamente en `$INSUNITS`. El caso real declara milimetros, pero sus
coordenadas estan en metros. La validacion geometrica autoritativa fue el muro:
10.788 x 23.530 m al elegir unidad real `m`.

Los limites globales pueden contaminarse por bloques dinamicos con origen o
geometria extrema. Validar escala sobre capas/objetos arquitectonicos conocidos,
no solo con la envolvente total.
