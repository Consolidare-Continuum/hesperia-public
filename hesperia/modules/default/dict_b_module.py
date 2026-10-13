"""Dict B module: concepts to family/area scores (ctx/config only)."""

from __future__ import annotations
import json
from pathlib import Path

from hesperia.engine.calibration_dict_paths import resolve_dict_file
from core.engine.calculus import concepts_to_family_area_scores


class DictBModule:
    name = "core.dict_b"
    version = "v1"
    provides = {"project": ["family_scores_raw", "area_scores_raw"]}
    requires = {"project": ["concept_hits"]}
    capabilities = {"preprocess": False, "project": True, "postprocess": False}
    output_schema = {"family_scores": dict, "area_scores": dict, "families": list, "areas": list}

    def configure(self, config: dict) -> None:
        rows = list(config.get("entries") or [])
        if not rows:
            repo = Path(__file__).resolve().parents[3]
            calib_path = resolve_dict_file(repo, "dict_b.jsonl", explicit_version=config.get("calibration_dict_version"))
            default_path = calib_path or (repo / "assets" / "data" / "engine_dynamics_v060" / "dict_b" / "dict_b_seed.jsonl")
            p = Path(config.get("path") or default_path)
            if p.exists():
                rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.map: dict[str, dict] = {}
        for row in rows:
            cid = str(row.get("concept_id") or "")
            if cid:
                self.map[cid] = row

    def project(self, ctx: dict) -> None:
        concept_hits = list((ctx.get("modules") or {}).get("core.dict_a", {}).get("concept_hits") or [])
        family_scores, area_scores, families, areas = concepts_to_family_area_scores(
            concept_hits, self.map
        )
        ctx["modules"][self.name]["family_scores"] = family_scores
        ctx["modules"][self.name]["area_scores"] = area_scores
        ctx["modules"][self.name]["families"] = families
        ctx["modules"][self.name]["areas"] = areas


def create() -> DictBModule:
    return DictBModule()

