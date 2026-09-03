# -*- coding: utf-8 -*-
"""
FreeCAD Project Memory - environment comparison
Version: 0.1.0
Date: 2026-08-11 16:44 -06:00

Usage:
    python compare_envs.py equipo1.json equipo2.json
    python compare_envs.py equipo1.json equipo2.json --output comparacion.md

Purpose:
- Compare two saved FreeCAD diagnostics.
- Highlight differences likely to explain Workbench or macro failures.
"""

from __future__ import print_function

import argparse
import json
from pathlib import Path


IMPORTANT_PATHS = [
    ("host",),
    ("freecad", "version_text"),
    ("python", "version"),
    ("python", "executable"),
    ("qt", "binding"),
    ("qt", "qt_version"),
    ("active_workbench",),
    ("paths", "user_app_data_dir"),
    ("paths", "user_macro_dir"),
    ("paths", "macro_path"),
    ("onedrive_detected",),
]


def _get(data, path):
    value = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _module_rows(a, b):
    names = sorted(set((a.get("modules") or {})) | set((b.get("modules") or {})))
    rows = []
    for name in names:
        pa = (a.get("modules") or {}).get(name, "")
        pb = (b.get("modules") or {}).get(name, "")
        if pa != pb:
            rows.append((f"module:{name}", pa, pb))
    return rows


def _hash_rows(a, b):
    fa = a.get("key_files") or {}
    fb = b.get("key_files") or {}

    def by_basename(files):
        out = {}
        for path, meta in files.items():
            name = Path(path).name.lower()
            out.setdefault(name, []).append((path, meta))
        return out

    aa = by_basename(fa)
    bb = by_basename(fb)
    rows = []
    for name in sorted(set(aa) & set(bb)):
        left = aa[name]
        right = bb[name]
        if len(left) != 1 or len(right) != 1:
            continue
        lpath, lmeta = left[0]
        rpath, rmeta = right[0]
        lhash = str((lmeta or {}).get("sha256", ""))
        rhash = str((rmeta or {}).get("sha256", ""))
        if lhash and rhash and lhash != rhash:
            rows.append((f"hash:{name}", lhash[:16], rhash[:16]))
    return rows


def build_markdown(a, b, left_name, right_name):
    rows = []
    for path in IMPORTANT_PATHS:
        va = _get(a, path)
        vb = _get(b, path)
        if va != vb:
            rows.append((".".join(path), va, vb))

    rows.extend(_module_rows(a, b))
    rows.extend(_hash_rows(a, b))

    lines = [
        "# Comparacion de entornos FreeCAD",
        "",
        f"- Izquierda: `{left_name}`",
        f"- Derecha: `{right_name}`",
        "",
    ]

    if not rows:
        lines += [
            "No se detectaron diferencias en los campos comparados.",
            "",
            "Nota: esto no demuestra que los entornos sean identicos; solo que los datos guardados coinciden.",
        ]
        return "\n".join(lines) + "\n"

    lines += [
        "| Campo | Izquierda | Derecha |",
        "|---|---|---|",
    ]
    for field, va, vb in rows:
        sa = str(va).replace("|", "\\|").replace("\n", " ")
        sb = str(vb).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{field}` | `{sa}` | `{sb}` |")

    lines += [
        "",
        "## Prioridad de revision",
        "",
        "Revisar primero version FreeCAD/Python/PySide, rutas de Workbench, MacroPath y hashes diferentes.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--output")
    args = parser.parse_args()

    a = _load(args.left)
    b = _load(args.right)
    md = build_markdown(a, b, args.left, args.right)

    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(args.output)
    else:
        print(md)


if __name__ == "__main__":
    main()
