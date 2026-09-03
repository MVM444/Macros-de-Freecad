# Contrato de memoria FreeCAD

Version: 0.1.0  
Fecha y hora: 2026-08-11 16:44 -06:00

## Principio

La memoria del proyecto no sustituye Git ni el estado real de FreeCAD. Sirve para conectar sesiones y equipos con un resumen tecnico pequeno.

## Estados de verificacion

Usar estas etiquetas en `RESULTADO_CODEX.md` y sesiones:

- `PROGRAMADO`
- `COMPILADO`
- `PROBADO`
- `VERIFICADO_MCP`
- `VERIFICADO_VISUAL`
- `NO_VERIFICADO_MCP`
- `PENDIENTE`

## Esquema minimo de equipo

```json
{
  "schema_version": 1,
  "captured_at": "",
  "host": "",
  "freecad": {},
  "python": {},
  "qt": {},
  "active_workbench": "",
  "active_document": "",
  "paths": {},
  "workbenches": [],
  "commands": {},
  "modules": {},
  "key_files": {},
  "onedrive_detected": false
}
```

## Regla de precedencia

1. Estado real consultado a FreeCAD por MCP.
2. Archivos actuales y Git.
3. Diagnostico guardado mas reciente.
4. `ESTADO_PROYECTO.md`.
5. Sesiones historicas.

Si dos niveles contradicen, actualizar los niveles inferiores.
