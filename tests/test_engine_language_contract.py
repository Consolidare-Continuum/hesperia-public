from __future__ import annotations

import pytest

from core.engine.context_guard import GuardedContext
from core.engine.language import language_schema, validate_signals


def test_language_schema_has_ctx_signal_result() -> None:
    schema = language_schema()
    assert set(schema.keys()) == {"ctx", "signal", "result"}
    assert "modules" in schema["ctx"]


def test_signal_contract_validation_codes() -> None:
    ok = validate_signals([{"family_id": 3, "strength": 0.4, "source": None}])
    assert ok[0]["family_id"] == 3
    with pytest.raises(ValueError, match="signal_missing_family_id"):
        validate_signals([{"strength": 0.1}])
    with pytest.raises(ValueError, match="signal_invalid_strength_type"):
        validate_signals([{"family_id": 1, "strength": "0.1"}])


def test_engine_context_guard_blocks_mutation() -> None:
    ctx = GuardedContext({"input": {}, "signals": {}, "families": {}, "areas": {}, "metrics": {}, "modules": {}})
    ctx.allow(module="tfp.v1", path="modules.tfp.v1.*")
    with pytest.raises(ValueError, match="engine_context_module_scope_violation"):
        ctx["metrics"] = {"x": 1}
    assert "blocked_module_write:tfp.v1:metrics" in ctx.mutation_log


def test_engine_context_guard_blocks_forbidden_read_scope() -> None:
    ctx = GuardedContext({"input": {}, "signals": {}, "families": {}, "areas": {}, "metrics": {}, "modules": {}, "meta": {}})
    ctx.allow(module="tfp.v1", path="modules.tfp.v1.*")
    ctx.allow_read(module="tfp.v1", path="signals.*")
    with pytest.raises(ValueError, match="engine_context_read_scope_violation"):
        _ = ctx.get("modules")
