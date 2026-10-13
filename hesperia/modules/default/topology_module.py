"""Topology module: area propagation and tension-ready vector."""

from __future__ import annotations

from core.engine.calculus import normalize_area_scores


class TopologyModule:
    name = "topology.core"
    version = "v1"
    provides = {"project": ["area_scores_normalized"]}
    requires = {"project": ["area_scores_raw"]}
    capabilities = {"preprocess": False, "project": True, "postprocess": False}
    output_schema = {"area_scores": dict}

    def configure(self, config: dict) -> None:
        self.area_count = int(config.get("area_count", 12))

    def project(self, ctx: dict) -> None:
        area_scores = dict((ctx.get("modules") or {}).get("core.dict_b", {}).get("area_scores") or {})
        ctx["modules"][self.name]["area_scores"] = normalize_area_scores(area_scores, self.area_count)


def create() -> TopologyModule:
    return TopologyModule()

