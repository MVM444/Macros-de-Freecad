# Archivo - FA Techo BIM legado

Fecha de archivo: 2026-08-31 America/Costa_Rica  
Workbench: FacilArquitecturaWB  
Comando: `FA_CreateRoofSystemBIM`  
Texto visible anterior: `FA Techo BIM`

## Motivo

El comando fue retirado de la interfaz porque la ruta vigente de techo rectangular es
`FA Techo desde rectangulo`, basada en `Arch Axis`, `Arch Truss`, `Arch Structure/Beam` y `Arch Roof`.

## Archivo conservado

- `cmd_create_roof_system_bim.py`

El archivo se movio desde `commands/` conservando su identidad de Drive para permitir consulta o
recuperacion futura.

## Dependencias historicas

La implementacion archivada dependia de modulos del Workbench como `roof_command_common.py` y
utilidades del nucleo. Esos modulos no se archivan aqui si siguen siendo compartidos o utiles para
la implementacion vigente.

## Restauracion

Para restaurar el comando seria necesario, como minimo:

1. devolver `cmd_create_roof_system_bim.py` a `commands/`;
2. restaurar su importacion y `register()` en `InitGui.py`;
3. volver a incorporarlo a la barra/menu deseados;
4. probarlo nuevamente en FreeCAD 1.1.3 antes de considerarlo vigente.
