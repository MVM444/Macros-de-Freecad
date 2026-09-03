# -*- coding: utf-8 -*-
"""Smoke tests for the Phase 2 macro catalog and usage classification."""

import json
import os
import sys
import tempfile

HERE = os.path.abspath(os.path.dirname(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from ElectricCR import catalog, usage_log


def main():
    old = {name: getattr(catalog, name) for name in ("REPO_ROOT", "DATA_DIR", "CATALOG_PATH", "MARKDOWN_PATH")}
    old_usage = {name: getattr(usage_log, name) for name in ("LOGS_DIR", "STATS_PATH", "EVENTS_PATH")}
    with tempfile.TemporaryDirectory(prefix="electriccr_phase2_") as temp:
        macro_dir = os.path.join(temp, "Areas")
        os.makedirs(macro_dir)
        macro_path = os.path.join(macro_dir, "Demo.FCMacro")
        with open(macro_path, "w", encoding="utf-8") as fh:
            fh.write('__Name__ = "Demo area"\n__Comment__ = "Descripcion de prueba."\n')
        catalog.REPO_ROOT = temp
        catalog.DATA_DIR = os.path.join(temp, "data")
        catalog.CATALOG_PATH = os.path.join(catalog.DATA_DIR, "macros_catalog.json")
        catalog.MARKDOWN_PATH = os.path.join(temp, "MACROS_CATALOGO.md")
        data = catalog.ensure_catalog([])
        assert len(data["entries"]) == 1
        entry = next(iter(data["entries"].values()))
        assert entry["description"] == "Descripcion de prueba."
        assert entry["description_source"] == "macro_metadata"
        catalog.update_entry(entry["path"], {"comment": "Nota manual", "manual_status": "REVISADA", "decision": "MANTENER"})
        loaded = catalog.load_catalog()
        saved = loaded["entries"][entry["path"]]
        assert saved["comment"] == "Nota manual"
        assert saved["manual_status"] == "REVISADA"
        assert saved["decision"] == "MANTENER"
        before = open(catalog.MARKDOWN_PATH, encoding="utf-8").read()
        catalog.regenerate_markdown(loaded)
        after = open(catalog.MARKDOWN_PATH, encoding="utf-8").read()
        assert before == after
        with open(catalog.CATALOG_PATH, "w", encoding="utf-8") as fh:
            fh.write("{invalid")
        assert catalog.load_catalog()["entries"] == {}

        # GPT description integration must not overwrite review fields or a
        # concrete local description.
        seed = {
            "schema_version": 1,
            "entries": {
                "Areas/Empty.FCMacro": {"path": "Areas/Empty.FCMacro", "description": "", "comment": "Nota Marco", "manual_status": "REVISAR", "decision": "MANTENER"},
                "Areas/Local.FCMacro": {"path": "Areas/Local.FCMacro", "description": "Descripcion local concreta", "comment": "Otra nota", "manual_status": "REVISADA", "decision": "MEJORAR"},
            },
        }
        catalog.save_catalog(seed)
        gpt_path = os.path.join(temp, "MACROS_DESCRIPCIONES_GPT.json")
        with open(gpt_path, "w", encoding="utf-8") as fh:
            json.dump({"generado": "test", "items": [
                {"ruta": "Areas/Empty.FCMacro", "descripcion": "Descripcion suministrada.", "fuente_descripcion": "codigo_revisado_gpt", "confianza_descripcion": "alta"},
                {"ruta": "Areas/Local.FCMacro", "descripcion": "Alternativa GPT.", "fuente_descripcion": "codigo_revisado_gpt", "confianza_descripcion": "media"},
            ]}, fh)
        stats = catalog.integrate_gpt_descriptions(gpt_path)
        integrated = catalog.load_catalog()["entries"]
        assert stats["matched"] == 2 and stats["discrepancies"] == 1
        assert integrated["Areas/Empty.FCMacro"]["description"] == "Descripcion suministrada."
        assert integrated["Areas/Empty.FCMacro"]["comment"] == "Nota Marco"
        assert integrated["Areas/Empty.FCMacro"]["manual_status"] == "REVISAR"
        assert integrated["Areas/Empty.FCMacro"]["decision"] == "MANTENER"
        assert integrated["Areas/Local.FCMacro"]["description"] == "Descripcion local concreta"
        assert integrated["Areas/Local.FCMacro"]["description_discrepancy"] is True
        assert integrated["Areas/Local.FCMacro"]["description_alternative"] == "Alternativa GPT."
        assert "Fuente/confianza" in open(catalog.MARKDOWN_PATH, encoding="utf-8").read()

        usage_log.LOGS_DIR = os.path.join(temp, "logs")
        usage_log.STATS_PATH = os.path.join(usage_log.LOGS_DIR, "tool_usage.json")
        usage_log.EVENTS_PATH = os.path.join(usage_log.LOGS_DIR, "tool_events.jsonl")
        usage_log.log_tool("macro:test", {"usage_kind": "legacy/unclassified"})
        usage_log.log_tool("macro:test", {"usage_kind": "real"})
        usage_log.log_tool("macro:test", {"usage_kind": "test"})
        stats = usage_log.get_stats()["tools"]["macro:test"]
        assert stats["count"] == 3
        assert stats["historical_count"] == 1
        assert stats["real_count"] == 1
        assert stats["test_count"] == 1
    for name, value in old.items():
        setattr(catalog, name, value)
    for name, value in old_usage.items():
        setattr(usage_log, name, value)
    print("PASS smoke_macro_panel_phase2 catalog=1 usage=real/test/historical")


if __name__ == "__main__":
    main()
