# Uso del diagnostico con MCP

## Objetivo

Obtener el estado real de la instancia de FreeCAD controlada por Codex.

## Metodo recomendado

1. Identificar la herramienta MCP que ejecuta Python dentro de FreeCAD.
2. Ejecutar el contenido de `scripts/freecad_diag.py` en esa instancia.
3. Capturar la linea que empieza con:

`[FREECAD-PROJECT-MEMORY]`

4. El resto de esa linea es JSON.
5. Guardarlo en `Memoria_FreeCAD/equipos/<HOST>.json`.

## Dos computadoras

Si existen dos conexiones MCP, nombrarlas de forma inequívoca en la configuracion de Codex, por ejemplo:

- `freecad_local`
- `freecad_remoto`

Antes de una prueba destructiva o de una modificacion de documento, confirmar que la herramienta apunta al equipo correcto.

## Seguridad

El diagnostico es de solo lectura. No debe:

- guardar documentos;
- cerrar documentos;
- borrar objetos;
- cambiar preferencias;
- modificar rutas;
- instalar complementos.

Si no se puede ejecutar el diagnostico por MCP, registrar `NO_VERIFICADO_MCP`.
