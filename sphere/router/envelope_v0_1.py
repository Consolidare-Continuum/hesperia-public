"""RouterInputEnvelope v0.1 builder (HSR-V7-03)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sphere.router.fingerprint import compute_router_fingerprint

SCHEMA_ID = "hesperia.router_input_envelope.v0_1"
DEFAULT_ROUTER_VERSION = "v7-router-0.1"


@dataclass
class RouterInputEnvelope:
    router_version: str
    input_hash: str
    input_text: str
    engine_trace: dict[str, Any]
    logic_mapping: dict[str, Any]
    retrieval_context: dict[str, Any]
    relation_context: dict[str, Any]
    policy_block: dict[str, Any]
    corpus_snapshot_id: str
    policy_snapshot_id: str
    enabled_modules: list[str] = field(default_factory=list)
    calculable: dict[str, Any] | None = None
    coherence_hints: dict[str, Any] | None = None
    observability: dict[str, Any] | None = None
    gtp: dict[str, Any] | None = None
    router_fingerprint: str = ""

    def finalize(self) -> RouterInputEnvelope:
        """Compute router_fingerprint after all blocks are set."""
        self.router_fingerprint = compute_router_fingerprint(
            input_hash=self.input_hash,
            engine_trace=self.engine_trace,
            retrieval_context=self.retrieval_context,
            policy_snapshot_id=self.policy_snapshot_id,
            router_version=self.router_version,
            enabled_modules=self.enabled_modules,
        )
        return self


def envelope_to_dict(env: RouterInputEnvelope) -> dict[str, Any]:
    """Serialize for JSON schema validation and LLM prompt envelope."""
    if not env.router_fingerprint:
        env.finalize()
    out: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "router_version": env.router_version,
        "input_hash": env.input_hash,
        "input_text": env.input_text,
        "engine_trace": env.engine_trace,
        "logic_mapping": env.logic_mapping,
        "retrieval_context": env.retrieval_context,
        "relation_context": env.relation_context,
        "policy_block": env.policy_block,
        "corpus_snapshot_id": env.corpus_snapshot_id,
        "policy_snapshot_id": env.policy_snapshot_id,
        "router_fingerprint": env.router_fingerprint,
        "enabled_modules": list(env.enabled_modules),
    }
    if env.calculable is not None:
        out["calculable"] = env.calculable
    if env.coherence_hints is not None:
        out["coherence_hints"] = env.coherence_hints
    if env.observability is not None:
        out["observability"] = env.observability
    if env.gtp is not None:
        out["gtp"] = env.gtp
    return out
