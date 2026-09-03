# FreeCAD Project Memory - paquete listo para Codex

Version: 0.1.0  
Fecha y hora: 2026-08-11 16:44 -06:00

Este paquete crea una Skill repo-scoped para mantener continuidad tecnica entre Codex, FreeCAD, MCP, OneDrive y GitHub.

## Por que esta ubicacion

La skill se incluye en:

`.agents/skills/freecad-project-memory/`

La documentacion actual de OpenAI indica que Codex detecta skills de repositorio en `.agents/skills`, desde el directorio de trabajo hasta la raiz del repositorio.

## Instalacion recomendada

1. Copie el contenido de este paquete en la raiz de `MVM444/Macros-de-Freecad`.
2. Abra Codex en ese repositorio.
3. Pegue el contenido de `PROMPT_INSTALAR_EN_CODEX.txt`.
4. Codex inicializara:
   - `ESTADO_PROYECTO.md`
   - `TAREA_ACTUAL.md`
   - `RESULTADO_CODEX.md`
   - `Memoria_FreeCAD/...`
5. Codex debe diagnosticar FreeCAD por MCP y guardar el primer snapshot del equipo.

## Compatibilidad con la skill de arquitectura existente

El repositorio ya exige `$freecad-cr-workbench-architecture` desde `AGENTS.md`. Esta nueva skill NO la reemplaza.

- `freecad-cr-workbench-architecture`: decisiones y contrato de arquitectura.
- `freecad-project-memory`: continuidad, diagnostico, pruebas, comparacion de equipos y traspaso de contexto.

## Frases de uso

- `Continuar proyecto FreeCAD`
- `Diagnosticar FreeCAD`
- `Comparar equipos`
- `Probar cambio`
- `Cerrar sesion FreeCAD`
- `Preparar para ChatGPT`

Tambien puede invocarse explicitamente como:

`$freecad-project-memory`

## Archivos principales

- `SKILL.md`: flujo principal.
- `scripts/init_memory.py`: inicializa la memoria sin sobrescribir archivos.
- `scripts/freecad_diag.py`: diagnostico read-only para ejecutar dentro de FreeCAD mediante MCP.
- `scripts/compare_envs.py`: compara dos snapshots JSON.
- `references/workbench-test-profiles.json`: perfiles de ElectricCR, MEPWorkbenchCR, GameEngineExportWB y FacilArquitecturaWB.
- `AGENTS_APPEND_BLOCK.md`: bloque seguro para anexar al AGENTS existente.

## Seguridad

- No guarda, cierra ni modifica documentos FreeCAD durante el diagnostico.
- No hace commit/push automaticamente.
- No sobrescribe AGENTS.md.
- No debe registrar tokens ni credenciales.
