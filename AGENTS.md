# Instrucciones de arquitectura FreeCAD CR

Estas instrucciones aplican a todo el repositorio.

Al analizar o modificar ElectricCR, MEPWorkbenchCR, FacilArquitecturaWB, macros compartidas o modelos relacionados, usar la habilidad personal `$freecad-cr-workbench-architecture` y leer su contrato antes de actuar.

Principios obligatorios:

- Mantener separados los Workbenches y compartir un núcleo neutral.
- Usar BIM/Arch nativo para IFC, Building Storey, Arch Space, Host y Equipment.
- Mantener una única identidad semántica por elemento y vincular 3D, Symbol2D e Info2D.
- Usar PropertyLink para Space, Host, Circuit, Panel, System y equipos conectados.
- No sustituir el resultado térmico calculado por la capacidad del equipo seleccionado.
- Mantener comandos y migraciones idempotentes, con identificadores estables.
- Exportar IFC/DXF por propiedades y relaciones semánticas, no solo por nombres o visibilidad.
- Conservar compatibilidad heredada mediante adaptadores y migración no destructiva.
- No guardar ni modificar un FCStd original sin autorización explícita.

La referencia canónica está en:

`C:\Users\marco\.codex\skills\freecad-cr-workbench-architecture\references\architecture-contract.md`
