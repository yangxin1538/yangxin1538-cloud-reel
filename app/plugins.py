"""Tiny plugin system, NextFind plugin-market style.

A plugin is a .py file in plugins/ with a PLUGIN dict:
  PLUGIN = {"name": "...", "description": "...", "version": "..."}
and an optional run(query, settings) function. Plugins are loaded
lazily and never run on import.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def list_plugins(plugins_dir: Path) -> list[dict]:
    out = []
    if not plugins_dir.exists():
        return out
    for path in sorted(plugins_dir.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(f"plugin_{path.stem}", path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            plugin = getattr(mod, "PLUGIN", {})
            out.append({
                "file": path.name,
                "name": plugin.get("name", path.stem),
                "description": plugin.get("description", ""),
                "version": plugin.get("version", "0.1.0"),
            })
        except Exception as exc:  # noqa: BLE001
            out.append({"file": path.name, "name": path.stem, "description": f"load failed: {exc}", "version": ""})
    return out


def run_plugin(plugins_dir: Path, name: str, query: str, settings) -> dict:
    for path in plugins_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(f"plugin_{path.stem}", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if getattr(mod, "PLUGIN", {}).get("name") == name:
            run = getattr(mod, "run", None)
            if run is None:
                return {"ok": False, "error": "plugin has no run()"}
            return {"ok": True, "name": name, "result": run(query, settings)}
    return {"ok": False, "error": f"plugin not found: {name}"}
