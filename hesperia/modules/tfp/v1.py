"""TFP module as external pluggable layer."""

from __future__ import annotations

from core.engine.calculus import compute_tfp_bundle

from hesperia.modules.tfp.seal import enforce_tfp_module_seal_on_project


class TFPModule:
    name = "tfp.v1"
    version = "v0.5.3"
    provides = {"project": ["tfp_vector", "tfp_profile", "tfp_conflicts"]}
    requires = {
        "project": ["family_scores_raw", "area_scores_raw", "concept_hits", "input.text", "normalized_tokens"]
    }
    capabilities = {"preprocess": False, "project": True, "postprocess": False}
    output_schema = {"tfp_vector": dict, "tfp_profile": dict, "tfp_conflicts": list}

    def configure(self, config: dict) -> None:
        self.labels = list(config.get("labels", ["control", "aggression", "identity", "trust"]))

    def project(self, ctx: dict) -> None:
        enforce_tfp_module_seal_on_project()
        modules = ctx.get("modules") or {}
        vector, profile, conflicts = compute_tfp_bundle(
            family_scores=dict(modules.get("core.dict_b", {}).get("family_scores") or {}),
            area_scores=dict(modules.get("core.dict_b", {}).get("area_scores") or {}),
            concept_hits=list(modules.get("core.dict_a", {}).get("concept_hits") or []),
            text=str((ctx.get("input") or {}).get("text") or ""),
            tokens=list(modules.get("nlp.basic", {}).get("tokens") or []),
            labels=self.labels,
        )
        ctx["modules"][self.name]["tfp_vector"] = vector
        ctx["modules"][self.name]["tfp_profile"] = profile
        ctx["modules"][self.name]["tfp_conflicts"] = conflicts


def create() -> TFPModule:
    return TFPModule()

