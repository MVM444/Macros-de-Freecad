"""Sincroniza el runtime CRBIMCore incluido en Facil Arquitectura.

Nombre: sync_bundled_crbimcore.py
Proposito: mantener `_bundled/CRBIMCore` como espejo generado y verificable de la
fuente neutral `CRBIMCore`, sin crear una segunda fuente de verdad.
Funcion principal: comparar hashes SHA-256 y copiar exclusivamente el runtime
necesario para los comandos comunes de Recintos/Espacios.
Mantenimiento: modificar primero la fuente neutral; usar `--check` en CI/RELEASE
y `--dry-run` antes de copiar. No importa FreeCAD, FreeCADGui ni Qt.
Version: 0.1.0
Fecha y hora: 2026-09-02 18:34 America/Costa_Rica
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

FILES = (
    "__init__.py",
    "room_resolver_core.py",
    "room_operations_core.py",
    "freecad_room_adapter.py",
    "freecad_room_operations.py",
    "commands/__init__.py",
    "commands/common_rooms.py",
    "resources/icons/CRBIM_SelectRoom.svg",
    "resources/icons/CRBIM_RoomInfo.svg",
    "resources/icons/CRBIM_NameRoom.svg",
    "resources/icons/CRBIM_RoomGuide.svg",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_paths() -> tuple[Path, Path]:
    fa_root = Path(__file__).resolve().parents[1]
    project_root = fa_root.parent
    return project_root / "CRBIMCore", fa_root / "_bundled" / "CRBIMCore"


def build_report(source: Path, destination: Path) -> dict:
    entries = []
    for relative in FILES:
        src = source / relative
        dst = destination / relative
        src_exists = src.is_file()
        dst_exists = dst.is_file()
        src_hash = _sha256(src) if src_exists else ""
        dst_hash = _sha256(dst) if dst_exists else ""
        entries.append(
            {
                "path": relative,
                "source_exists": src_exists,
                "destination_exists": dst_exists,
                "source_sha256": src_hash,
                "destination_sha256": dst_hash,
                "match": bool(src_exists and dst_exists and src_hash == dst_hash),
            }
        )
    return {
        "schema": "facil-arquitectura.bundle-sync",
        "version": 1,
        "source": str(source),
        "destination": str(destination),
        "ok": all(item["match"] for item in entries),
        "files": entries,
    }


def sync(source: Path, destination: Path, dry_run: bool = False) -> dict:
    before = build_report(source, destination)
    copied = []
    missing_source = []
    for item in before["files"]:
        relative = item["path"]
        src = source / relative
        dst = destination / relative
        if not src.is_file():
            missing_source.append(relative)
            continue
        if item["match"]:
            continue
        copied.append(relative)
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    after = build_report(source, destination) if not dry_run else before
    after["dry_run"] = bool(dry_run)
    after["copied"] = copied
    after["missing_source"] = missing_source
    after["ok"] = (not missing_source) and (after["ok"] if not dry_run else True)
    return after


def main() -> int:
    default_source, default_destination = default_paths()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=default_source)
    parser.add_argument("--destination", type=Path, default=default_destination)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true", help="Solo verificar; no copiar.")
    parser.add_argument("--json", action="store_true", help="Emitir resultado JSON.")
    args = parser.parse_args()

    if args.check:
        report = build_report(args.source, args.destination)
    else:
        report = sync(args.source, args.destination, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for item in report["files"]:
            state = "OK" if item["match"] else "CAMBIO"
            print(f"[{state}] {item['path']}")
        if report.get("copied"):
            prefix = "DRY-RUN" if report.get("dry_run") else "COPIADO"
            for relative in report["copied"]:
                print(f"[{prefix}] {relative}")
        print("RESULTADO:", "OK" if report.get("ok") else "NO_MATCH")

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
