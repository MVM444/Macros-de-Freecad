# -*- coding: utf-8 -*-
"""
FreeCAD Project Memory - repository initializer
Version: 0.1.0
Date: 2026-08-11 16:44 -06:00

Purpose:
- Create memory folders and starter Markdown files.
- Never overwrite existing files unless --force is supplied.
- Does not modify AGENTS.md.
"""

from __future__ import print_function

import argparse
from pathlib import Path


FILES = {
    "ESTADO_PROYECTO.md": """# ESTADO DEL PROYECTO

Ultima actualizacion: pendiente

## Proyecto activo

Pendiente.

## Estado actual

Pendiente.

## Funciona

- Pendiente.

## No funciona / riesgos

- Pendiente.

## Ultima verificacion MCP

NO_VERIFICADO_MCP

## Git

- Rama: pendiente
- Commit: pendiente
- Cambios sin commit: pendiente

## Siguiente paso

Pendiente.
""",
    "TAREA_ACTUAL.md": """# TAREA ACTUAL

Ultima actualizacion: pendiente

## Objetivo

Pendiente.

## Alcance

Pendiente.

## Fuera de alcance

Pendiente.

## Criterios de aceptacion

- Pendiente.

## Pruebas requeridas

- Pendiente.
""",
    "RESULTADO_CODEX.md": """# RESULTADO CODEX

Fecha/hora: pendiente
Equipo: pendiente
Proyecto/Workbench: pendiente
Estado de verificacion: NO_VERIFICADO_MCP

## Objetivo

Pendiente.

## Archivos modificados

- Pendiente.

## Cambios realizados

- Pendiente.

## Pruebas ejecutadas

- Pendiente.

## Resultado MCP

NO_VERIFICADO_MCP

## Errores o pendientes

- Pendiente.

## Git

- Rama: pendiente
- Commit: pendiente
- Cambios sin commit: pendiente

## Siguiente paso recomendado

Pendiente.
""",
}

DIRS = [
    "Memoria_FreeCAD/equipos",
    "Memoria_FreeCAD/sesiones",
    "Memoria_FreeCAD/incidentes",
    "Memoria_FreeCAD/comparaciones",
]


def write_file(path, content, force=False):
    if path.exists() and not force:
        print("[SKIP] " + str(path))
        return
    path.write_text(content, encoding="utf-8")
    print("[OK] " + str(path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    for rel in DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)

    for rel, content in FILES.items():
        write_file(root / rel, content, force=args.force)

    for rel in DIRS:
        keep = root / rel / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    print("FreeCAD Project Memory initialized at: " + str(root))


if __name__ == "__main__":
    main()
