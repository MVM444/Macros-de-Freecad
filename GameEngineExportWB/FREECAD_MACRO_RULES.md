# Regla general para macros de FreeCAD y MCP

Version: 1.0
Fecha: 2026-08-15

## Regla principal

Toda macro nueva o modernizada debe separar la logica de trabajo de su boton,
dialogo o archivo `.FCMacro`. Cuando la funcion sea util para automatizacion,
debe poder ejecutarse desde FreeCAD y exponerse de forma controlada mediante
MCP o JSON, usando el mismo algoritmo.

## Arquitectura obligatoria para herramientas no triviales

1. **Nucleo independiente**
   - No importa `FreeCADGui`, Qt ni componentes visuales.
   - Recibe parametros explicitos, preferiblemente un diccionario compatible
     con JSON.
   - Devuelve un diccionario estructurado y versionado.
   - Puede probarse sin abrir un dialogo.

2. **Adaptador de FreeCAD**
   - Obtiene el documento activo, la seleccion y las preferencias.
   - Presenta dialogos, mensajes y progreso.
   - Llama al nucleo; no duplica el algoritmo.

3. **Macro `.FCMacro`**
   - Debe ser un acceso pequeno al comando o al nucleo.
   - No debe contener otra copia completa del algoritmo.

4. **Adaptador MCP**
   - Solo expone herramientas registradas y autorizadas.
   - Valida la entrada contra un esquema conocido.
   - Nunca ejecuta nombres de macros o codigo arbitrario recibido del modelo.

## Contrato recomendado

```python
def execute(context, parameters):
    """Return a JSON-compatible result dictionary."""
```

El resultado debe incluir, cuando corresponda:

```json
{
  "schema_version": "1.0",
  "success": true,
  "operation": "tool_identifier",
  "document": "DocumentName",
  "source_unchanged": true,
  "warnings": [],
  "outputs": {}
}
```

## Seguridad y trazabilidad

- Las consultas y diagnosticos son de solo lectura por defecto.
- Las modificaciones deben declararse y usar transacciones de FreeCAD para
  permitir `Deshacer`.
- Una herramienta destructiva debe ofrecer `dry_run` cuando sea viable.
- No reutilizar rutas de un documento anterior cuando el documento activo no
  esta guardado.
- No sobrescribir archivos existentes sin una instruccion explicita.
- Usar `Object.Name` como identificador estable y `Label` solo como nombre
  visible.
- Registrar version del algoritmo, fecha, parametros, advertencias y salidas.
- Los archivos temporales deben usar una carpeta aislada y reconocible.

## Compatibilidad MCP

Cada herramienta candidata a MCP debe declarar:

- Identificador estable.
- Descripcion breve.
- Esquema de entrada.
- Esquema de salida.
- Modo `read_only` o `write`.
- Si requiere documento activo, seleccion u objetos concretos.
- Rutas que puede leer o escribir.

El servidor MCP debe llamar al mismo nucleo usado por FreeCAD. No debe abrir
dialogos modales ni depender de coordenadas de pantalla.

## Excepcion

Una macro pequena, puramente visual o de uso temporal puede mantenerse en un
solo archivo. Si empieza a calcular, modificar documentos, generar archivos o
ser reutilizada por otra herramienta, debe migrarse a esta arquitectura.
