# HESPERIA — CD row validation (Phase 1 + ignored Phase 2+ keys). Copyright © 2026 igareosh.com.
from __future__ import annotations

from typing import Any


class CDValidationError(ValueError):
    pass


_ALLOWED_TYPES = frozenset({"state", "action", "relation", "modifier"})


def validate_cd_row(row: dict[str, Any], *, line_no: int | None = None) -> None:
    prefix = f"line {line_no}: " if line_no else ""
    if not isinstance(row, dict):
        raise CDValidationError(f"{prefix}row must be object")
    cid = row.get("concept_id")
    if not cid or not isinstance(cid, str):
        raise CDValidationError(f"{prefix}concept_id required (string)")
    t = row.get("type")
    if t not in _ALLOWED_TYPES:
        raise CDValidationError(f"{prefix}type must be one of {_ALLOWED_TYPES}")
    act = row.get("activation")
    if not isinstance(act, dict):
        raise CDValidationError(f"{prefix}activation object required")
    for k in ("base_weight", "cap", "saturation_k", "threshold"):
        if k not in act:
            raise CDValidationError(f"{prefix}activation.{k} required")
        float(act[k])  # raises if bad
    cons = row.get("constraints")
    if not isinstance(cons, dict):
        raise CDValidationError(f"{prefix}constraints object required")
    for k in ("requires", "excludes", "co_occurs"):
        v = cons.get(k, [])
        if v is None:
            v = []
        if not isinstance(v, list):
            raise CDValidationError(f"{prefix}constraints.{k} must be list")
        if k != "co_occurs" and len(v) > 2:
            raise CDValidationError(f"{prefix}at most 2 entries in constraints.{k} for MVP guardrail")
        for x in v:
            if not isinstance(x, str) or not x.strip():
                raise CDValidationError(f"{prefix}constraints.{k} must be non-empty strings")
    eff = row.get("effects")
    if eff is not None:
        if not isinstance(eff, dict):
            raise CDValidationError(f"{prefix}effects must be object")
        for ek in ("amplifies", "inhibits"):
            ev = eff.get(ek, {})
            if ev is None:
                continue
            if not isinstance(ev, dict):
                raise CDValidationError(f"{prefix}effects.{ek} must be object")
            if len(ev) > 3:
                raise CDValidationError(f"{prefix}at most 3 keys in effects.{ek} for MVP")
            for kk, vv in ev.items():
                if not isinstance(kk, str):
                    raise CDValidationError(f"{prefix}effects keys must be strings")
                fv = float(vv)
                if fv > 2.0 or fv < 0.0:
                    raise CDValidationError(f"{prefix}effect factor must be in [0, 2]")
    st = row.get("structure")
    if st is not None:
        if not isinstance(st, dict):
            raise CDValidationError(f"{prefix}structure must be object")
        pa = st.get("primary_area", "")
        if pa is not None and not isinstance(pa, str):
            raise CDValidationError(f"{prefix}structure.primary_area must be string")
