\# PROMPT CODEX \- FA Cambiar tipo de puerta

Usa la skill repo-scoped \`freecad-project-memory\` y las skills adicionales exigidas por \`AGENTS.md\`.

Lee primero \`AGENTS.md\` y luego el \`TAREA\_ACTUAL.md\` sincronizado en el repositorio \`Macros-de-Freecad\`.

Ejecuta completamente la tarea \*\*FA Cambiar tipo de puerta\*\*.

Antes de editar, confirma que trabajas sobre la copia local mas reciente de \`FacilArquitecturaWB\` sincronizada con Drive/OneDrive y no sobre una version vieja de GitHub.

Puntos no negociables:

\- FreeCAD objetivo 1.1.3.  
\- Investiga/verifica el \`ArchWindowPresets\` instalado antes de programar.  
\- Usa solamente presets BIM nativos disponibles; no inventes familias FA.  
\- No supongas que cambiar \`obj.Preset\` reconstruye la puerta.  
\- Preserva Width, Height, Placement, Hosts, Normal, IfcType, contenedor y metadatos \`FA\_\*\`.  
\- Preferir conservar la identidad del objeto si es seguro; si no, reemplazo transaccional con validacion antes de borrar el original.  
\- Debe funcionar con seleccion multiple.  
\- Validar que el Wall siga perforado despues del cambio.  
\- No dejar puertas/Sketches temporales ni duplicados.  
\- No romper \`FA\_CreateDoorsFromSketch\`, ventanas, openings ni puerta doble.  
\- Si una puerta doble especial no es compatible, rechazala de forma segura.  
\- Mantener logging \`\[FACILARQ\]\[PUERTAS\]\`.  
\- Ejecuta pruebas y verificacion en FreeCAD real/MCP cuando este disponible.  
\- Actualiza version/build y documentacion segun las reglas del proyecto.  
\- Al finalizar escribe \`RESULTADO\_CODEX.md\`/\`ESTADO\_PROYECTO.md\` segun AGENTS.md con el procedimiento exacto para probar la nueva herramienta.

No hagas una refactorizacion amplia si no es necesaria. Conserva todo lo que ya funciona y limita los cambios al nuevo comando y al motor reusable estrictamente necesario.  
