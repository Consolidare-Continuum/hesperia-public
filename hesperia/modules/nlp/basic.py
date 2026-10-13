"""Deterministic NLP basic module."""

from __future__ import annotations

from core.lexical.normalization import normalize_text


class NLPModule:
    name = "nlp.basic"
    version = "v1"
    provides = {"preprocess": ["normalized_tokens", "canonical_text"]}
    requires: dict[str, list[str]] = {"preprocess": ["input.text"]}
    capabilities = {"preprocess": True, "project": False, "postprocess": False}
    output_schema = {"tokens": list, "canonical_text": str}

    def configure(self, config: dict) -> None:
        self.stopwords = set(config.get("stopwords", []))

    def preprocess(self, ctx: dict) -> None:
        norm = normalize_text(str((ctx.get("input") or {}).get("text") or ""))
        tokens = [t for t in (norm.get("tokens") or []) if t and t not in self.stopwords]
        ctx["modules"][self.name]["tokens"] = tokens
        ctx["modules"][self.name]["canonical_text"] = norm.get("canonical_text", "")


def create() -> NLPModule:
    return NLPModule()

