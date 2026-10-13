"""Modular execution kernel for Hesperia."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Protocol

import yaml  # type: ignore[import-untyped]
from core.engine.aggregation import aggregate_modules
from core.engine.context_schema import build_context, validate_context
from core.engine.context_guard import GuardedContext
from core.engine.execution_graph import PHASES, build_execution_graph
from core.engine.context_snapshot import freeze_context, hash_context
from core.engine.module_loader import load_module, resolve_module_path
from core.engine.module_validator import validate_module_contract


class HesperiaModule(Protocol):
    name: str
    version: str
    provides: list[str] | dict[str, list[str]]
    requires: list[str] | dict[str, list[str]]
    capabilities: dict[str, bool]
    output_schema: dict[str, type]

    def configure(self, config: dict[str, Any]) -> None: ...
    def preprocess(self, ctx: dict[str, Any]) -> None: ...
    def project(self, ctx: dict[str, Any]) -> None: ...
    def postprocess(self, ctx: dict[str, Any]) -> None: ...


@dataclass
class HesperiaEngine:
    modules: list[HesperiaModule] = field(default_factory=list)
    _required_versions: dict[str, str] = field(default_factory=dict)
    _module_paths: dict[str, str] = field(default_factory=dict)
    module_runtime_config: dict[str, dict[str, Any]] = field(default_factory=dict)
    failure_mode: str = "strict"

    def load_module(self, module_path_or_alias: str, config: dict[str, Any] | None = None) -> None:
        module_path = resolve_module_path(module_path_or_alias)
        module = load_module(module_path)
        validate_module_contract(module)
        module.configure(config or {})
        self.module_runtime_config[module.name] = dict(config or {})
        self._module_paths[module.name] = module_path
        self.modules.append(module)

    def load_from_config(self, config_path: Path) -> None:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        module_list = list(payload.get("modules") or [])
        if len(set(module_list)) != len(module_list):
            raise ValueError("module_config_duplicate_entries")
        module_cfg = dict(payload.get("module_config") or {})
        self.failure_mode = str(payload.get("failure_mode", "strict"))
        aggregation_strategy = str(payload.get("aggregation_strategy", "weighted_merge"))
        self.module_runtime_config = {}
        for key in module_list:
            if isinstance(key, dict):
                key_name = str(key.get("name") or "")
                cfg = dict(module_cfg.get(key_name, {}))
                cfg.update({k: v for k, v in key.items() if k != "name"})
            else:
                key_name = str(key)
                cfg = dict(module_cfg.get(key_name, {}))
            req_ver = cfg.pop("required_version", None)
            enabled = bool(cfg.pop("enabled", True))
            if not enabled:
                continue
            self.load_module(key_name, config=cfg)
            if req_ver:
                self._required_versions[self.modules[-1].name] = str(req_ver)
        self._validate_dependencies()
        self.module_runtime_config["__engine__"] = {"aggregation_strategy": aggregation_strategy}

    def _validate_dependencies(self) -> None:
        loaded_names = [m.name for m in self.modules]
        for m in self.modules:
            version = str(getattr(m, "version", "") or "").strip()
            if not version:
                raise ValueError(f"module_version_missing:{m.name}")
            req = self._required_versions.get(m.name)
            if req and version != req:
                raise ValueError(f"module_version_mismatch:{m.name}:{version}:{req}")
            if loaded_names.count(m.name) > 1:
                raise ValueError(f"module_duplicate_name:{m.name}")

    @staticmethod
    def _snapshot_modules(ctx: dict[str, Any]) -> dict[str, str]:
        out: dict[str, str] = {}
        for name, payload in dict(ctx.get("modules") or {}).items():
            out[str(name)] = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return out

    @staticmethod
    def _assert_module_scope(before: dict[str, str], after_ctx: dict[str, Any], active_module: str) -> None:
        after = HesperiaEngine._snapshot_modules(after_ctx)
        for name, blob in before.items():
            if name != active_module and after.get(name) != blob:
                raise ValueError(f"engine_context_module_scope_violation:{active_module}:wrote:{name}")

    def run(
        self,
        text: str,
        *,
        signals: list[dict[str, Any]] | None = None,
        until_phase: str | None = None,
        only_modules: set[str] | None = None,
    ) -> dict[str, Any]:
        base_ctx = build_context(text, signals=signals)
        ctx = GuardedContext(base_ctx)
        ctx["meta"]["module_config_resolved"] = self.module_runtime_config
        ctx["meta"]["aggregation_strategy"] = str(
            (self.module_runtime_config.get("__engine__", {}) or {}).get("aggregation_strategy", "weighted_merge")
        )
        validate_context(ctx, "start")
        graph = build_execution_graph(self.modules)
        ctx["meta"]["execution_graph"] = {phase: [m.name for m in modules] for phase, modules in graph.items()}
        snapshot = freeze_context(ctx)
        for phase in PHASES:
            for m in graph[phase]:
                if only_modules and m.name not in only_modules and self._module_paths.get(m.name, "") not in only_modules:
                    continue
                ctx.allow(module=m.name, path=f"modules.{m.name}.*")
                ctx.allow_read(module=m.name, path="input.*")
                ctx.allow_read(module=m.name, path="signals.*")
                ctx.allow_read(module=m.name, path="modules.*")
                ctx.allow_read(module=m.name, path="meta.trace")
                ctx.deny_read("metrics.final")
                ctx.set_module_slot(m.name, dict(ctx.get("modules", {}).get(m.name) or {}))
                before = self._snapshot_modules(ctx)
                if m.capabilities.get(phase):
                    phase_error: str | None = None
                    try:
                        getattr(m, phase)(ctx)
                    except Exception as e:
                        phase_error = str(e)
                        dict.__getitem__(ctx, "meta")["trace"].append({"module": m.name, "phase": phase, "error": str(e)})
                        if self.failure_mode == "strict":
                            raise
                        dict.__getitem__(ctx, "meta").setdefault("failed_modules", []).append(m.name)
                    if phase_error is None:
                        self._validate_output_schema(m, ctx)
                self._assert_module_scope(before, ctx, m.name)
                dict.__getitem__(ctx, "meta")["trace"].append(
                    {"module": m.name, "phase": phase, "inputs": list(snapshot.keys()), "outputs": list(ctx["modules"][m.name].keys())}
                )
                validate_context(ctx, f"{phase}:{m.name}")
                ctx.clear_allow()
            snapshot = freeze_context(ctx)
            ctx["meta"][f"hash_{phase}"] = hash_context(ctx)
            if until_phase and phase == until_phase:
                return ctx
        aggregate_modules(ctx)
        validate_context(ctx, "aggregated")
        ctx["meta"]["hash_aggregated"] = hash_context(ctx)
        return ctx

    @staticmethod
    def _validate_output_schema(module: HesperiaModule, ctx: dict[str, Any]) -> None:
        payload = dict((ctx.get("modules") or {}).get(module.name) or {})
        schema = dict(getattr(module, "output_schema", {}))
        for key, expected in schema.items():
            if key not in payload:
                raise ValueError(f"module_output_missing:{module.name}:{key}")
            if not isinstance(payload[key], expected):
                raise ValueError(f"module_output_invalid_type:{module.name}:{key}")

