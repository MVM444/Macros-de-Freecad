# Demo ElectricCR A1 v0.1 - primer fallo reproducible

Registro: 2026-09-09 22:39 -0600, America/Costa_Rica. Test: freecad_electric_demo_smoke.py v0.1.0, SHA256 `4368b8a687f95ccb04da7f6475b3e3e4438f29ac4814351363dd5ebf384caae5` sin cambios.

**FAIL en FreeCAD 1.1.3. Detenido antes de modificar codigo.** Ejecucion 2026-09-09T22:37:32.318785-06:00 a 2026-09-09T22:37:32.706730-06:00; version revision 20260725, commit 145529fe741292ff0b3977a01195bf0247425794.

Primer fallo del smoke: run() linea63 -> create_fixed_demo() linea294 -> _create_metadata() linea100 de electriccr/demo/electric_demo_freecad.py.

```text
obj = doc.addObject("App::Feature", "ECR_Demo_Metadata")
TypeError: Document::addObject: 'App::Feature' is not a document object type
```

Reproduccion minima independiente: documento vacio nuevo, misma llamada addObject; mismo TypeError. Confirma rechazo del TypeId por la API real de FreeCAD, antes de cualquier geometria, dispositivo, RoomResolver o runtime A1. No se ensayaron tipos alternativos ni se propuso/aplico reparacion.

El generador cerro la demo incompleta; al terminar el smoke y la reproduccion no quedaron documentos abiertos. No se alcanzo initial audit, movimiento, Undo/Redo, Delete ni save/reopen. Oficina, Bodega, muros y siete dispositivos no llegaron a generarse; **revision visual NO EJECUTABLE**, no aprobada por inferencia. No hay captura de una demo inexistente.

Contexto de arranque: ElectricCRWorkbench no estaba registrado en esta sesion. Una llamada previa del envoltorio para activarlo produjo KeyError antes de ejecutar el test; se importo el archivo solicitado directamente desde DEV, sin instalar/modificar el Workbench. Este incidente de preparacion se distingue del fallo reproducido de addObject, que tambien aparece en documento vacio. Se utilizo el run() original sin reemplazar funciones ni cambiar el archivo.

Evidencia: run.json conserva version, hash, tiempo, estado y traceback; first_failure_reproduction.json conserva la reproduccion; stdout.txt y console.txt son las salidas capturadas. execution_trace.txt separa explicitamente las excepciones capturadas por el envoltorio del texto de Report view. La excepcion fue capturada para conservar evidencia, por lo que el transporte MCP pudo responder success mientras el test registro FAIL.

Sin cambios funcionales, IFC, Upala, reparaciones, commit ni push. A1 aprobado no cambia de estado: esta prueba se detuvo en la creacion de metadata de la demo. Solo se leyo la tarea vigente y el script/fragmento directamente necesario para ejecutar y diagnosticar este primer fallo.
