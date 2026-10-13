"""Dict A module: token to concept hits (ctx/config only)."""

from __future__ import annotations
import json
from pathlib import Path

from hesperia.engine.calibration_dict_paths import resolve_dict_file


class DictAModule:
    name = "core.dict_a"
    version = "v1"
    provides = {"project": ["concept_hits"]}
    requires = {"project": ["normalized_tokens"]}
    capabilities = {"preprocess": False, "project": True, "postprocess": False}
    output_schema = {"concept_hits": list}

    def configure(self, config: dict) -> None:
        rows = list(config.get("entries") or [])
        if not rows:
            repo = Path(__file__).resolve().parents[3]
            calib_path = resolve_dict_file(repo, "dict_a.jsonl", explicit_version=config.get("calibration_dict_version"))
            default_path = calib_path or (repo / "assets" / "data" / "engine_dynamics_v060" / "dict_a" / "dict_a_seed.jsonl")
            p = Path(config.get("path") or default_path)
            if p.exists():
                rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.entries: dict[str, list[str]] = {}
        for row in rows:
            nf = str(row.get("normalized_form") or "").strip()
            if not nf:
                continue
            self.entries[nf] = list(row.get("candidate_concept_ids") or [])

    def project(self, ctx: dict) -> None:
        hits: list[str] = []
        tokens = list((ctx.get("modules") or {}).get("nlp.basic", {}).get("tokens") or [])
        for token in tokens:
            hits.extend(self.entries.get(str(token), []))
        ctx["modules"][self.name]["concept_hits"] = sorted(hits)


def create() -> DictAModule:
    return DictAModule()

