# HSR-V7-06 pre-LLM compiler tests.

from __future__ import annotations

from sphere.router.pre_llm_compiler import compile_router_envelope
from sphere.router.thinking_map_bridge import logic_mapping_from_thinking_map


def test_compile_router_envelope_minimal() -> None:
    env = compile_router_envelope("Compiler smoke text.")
    assert env["schema"] == "hesperia.router_input_envelope.v0_1"
    assert env["engine_trace"]["trace"]
    assert env["router_fingerprint"]


def test_compile_with_context_packet() -> None:
    ctx = {
        "calculable": {"grid": "12x24"},
        "coherence_hints": {"ring": 3},
        "retrieval": {"chunks": []},
    }
    env = compile_router_envelope("Context packet merge.", context_packet=ctx)
    assert env["calculable"] == ctx["calculable"]
    assert env["coherence_hints"] == ctx["coherence_hints"]
    assert env["retrieval_context"] == {"chunks": []}


def test_compile_with_thinking_map_outcome() -> None:
    outcome = {
        "kind": "OutcomeKind.CONTINUE",
        "llm_prompt_state": {
            "logic": {"actions": [{"rule": "ci_ready", "satisfied": True}]},
            "gate_status": {},
            "risk_level": "normal",
        },
    }
    env = compile_router_envelope("Thinking map merge.", thinking_map_outcome=outcome)
    assert env["logic_mapping"] == logic_mapping_from_thinking_map(outcome)
    assert env["policy_block"]["source"] == "fpf-thinking-map"
