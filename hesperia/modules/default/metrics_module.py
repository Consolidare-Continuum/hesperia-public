"""Metrics module over deterministic context state."""

from __future__ import annotations

from core.engine.calculus import compute_metrics_bundle


class MetricsModule:
    name = "metrics.base"
    version = "v1"
    provides = {"project": ["metrics_bundle"]}
    requires = {"project": ["family_scores_raw", "area_scores_normalized"]}
    capabilities = {"preprocess": False, "project": True, "postprocess": False}
    output_schema = {"metrics": dict, "area_scores": dict, "family_scores": dict}

    def configure(self, config: dict) -> None:
        self.family_count = int(config.get("family_count", 24))
        self.area_count = int(config.get("area_count", 12))

    def project(self, ctx: dict) -> None:
        modules = ctx.get("modules") or {}
        area_scores = dict(modules.get("topology.core", {}).get("area_scores") or {})
        family_scores = dict(modules.get("core.dict_b", {}).get("family_scores") or {})
        metrics = compute_metrics_bundle(
            area_scores=area_scores,
            family_scores=family_scores,
            area_count=self.area_count,
            family_count=self.family_count,
        )
        ctx["modules"][self.name]["metrics"] = metrics
        ctx["modules"][self.name]["area_scores"] = area_scores
        ctx["modules"][self.name]["family_scores"] = family_scores


def create() -> MetricsModule:
    return MetricsModule()

