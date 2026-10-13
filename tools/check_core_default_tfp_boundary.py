#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Seal: DEFAULT/core/syzif must never silently inherit Class B TFP calibration.

Invariant (Grace seal 2026-09-14):
  DEFAULT = hesperia/modules/default = CORE = syzif corpus / v0_core_syzif_001
  TFP     = hesperia/modules/tfp     = Class B = tfp corpus only (opt-in --domain tfp)

Fails CI/local if propose defaults, catalog defaults, or core seed drift back to TFP.
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def check_propose_llm_defaults() -> list[str]:
    errs: list[str] = []
    sys.path.insert(0, str(REPO))
    from tools.dict_calibration import propose_llm as pl

    if pl.SYSTEM is not pl.SYSTEM_CORE:
        errs.append("propose_llm.SYSTEM must alias SYSTEM_CORE (not SYSTEM_TFP)")
    for name in ("_catalog_rows", "call_propose_chunk", "propose_concepts"):
        default = inspect.signature(getattr(pl, name)).parameters["domain"].default
        if default != "core":
            errs.append(f"propose_llm.{name} domain default={default!r} (must be 'core')")
    # Source-level: no Domain = "tfp" as default
    src = (REPO / "tools/dict_calibration/propose_llm.py").read_text(encoding="utf-8")
    if 'domain: Domain = "tfp"' in src:
        errs.append('propose_llm.py still contains domain: Domain = "tfp" defaults')
    if "SYSTEM = SYSTEM_TFP" in src:
        errs.append("propose_llm.py still sets SYSTEM = SYSTEM_TFP")
    return errs


def check_default_engine_paths() -> list[str]:
    errs: list[str] = []
    sys.path.insert(0, str(REPO))
    from tools.dict_calibration.run_pipeline import _default_engine_paths

    core_b, core_a = _default_engine_paths(REPO)
    if not any("v0_core_syzif_001" in str(p) for p in core_b):
        errs.append(f"default (core) dict_b paths miss v0_core_syzif_001: {core_b}")
    if any("tfp" in p.name.lower() for p in core_b):
        errs.append(f"default (core) dict_b paths include TFP files: {core_b}")
    if "concept_hex_anchors_tfp" in str(core_a):
        errs.append(f"default (core) anchors point at TFP registry: {core_a}")

    tfp_b, tfp_a = _default_engine_paths(REPO, domain="tfp")
    if not any("tfp" in p.name.lower() for p in tfp_b):
        errs.append(f"domain=tfp paths should include dict_b_tfp*: {tfp_b}")
    if not tfp_b:
        errs.append("domain=tfp returned empty dict_b list")
    _ = tfp_a
    return errs


def check_modules_default_no_tfp_paths() -> list[str]:
    errs: list[str] = []
    root = REPO / "hesperia/modules/default"
    if not root.is_dir():
        return ["missing hesperia/modules/default/"]
    hits = [p for p in root.rglob("*") if "tfp" in p.name.lower() and "__pycache__" not in str(p)]
    if hits:
        errs.append(
            "modules/default must not contain *tfp* paths: "
            + ", ".join(str(p.relative_to(REPO)) for p in hits[:20])
        )
    return errs


def check_core_seed_no_tfp_concept_ids() -> list[str]:
    errs: list[str] = []
    seed_dir = REPO / "assets/calibration/dicts/v0_core_syzif_001"
    for name in ("dict_b.jsonl", "dict_b_seed.jsonl"):
        path = seed_dir / name
        if not path.is_file():
            continue
        bad = 0
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            if '"concept_id": "tfp.' in line or '"concept_id": "TFP_' in line:
                bad += 1
                if bad <= 3:
                    errs.append(f"{path.relative_to(REPO)}:{i}: TFP concept_id in core seed")
        if bad > 3:
            errs.append(f"{path.relative_to(REPO)}: {bad} TFP concept_id rows (showing first 3)")
    return errs


def check_cli_domain_flag() -> list[str]:
    errs: list[str] = []
    cli = REPO / "tools/run_dict_calibration_clearance.py"
    text = cli.read_text(encoding="utf-8")
    if '"--domain"' not in text and "'--domain'" not in text:
        errs.append("run_dict_calibration_clearance.py missing --domain flag")
    if 'default="core"' not in text and "default='core'" not in text:
        errs.append("run_dict_calibration_clearance.py --domain must default to core")
    # AST: ensure propose path passes domain=
    tree = ast.parse(text)
    # lightweight string check for call sites
    if "domain=args.domain" not in text:
        errs.append("clearance CLI must pass domain=args.domain into propose/post/run")
    _ = tree
    return errs


def main() -> int:
    checks = [
        ("propose_llm defaults", check_propose_llm_defaults),
        ("_default_engine_paths", check_default_engine_paths),
        ("modules/default paths", check_modules_default_no_tfp_paths),
        ("v0_core_syzif concept ids", check_core_seed_no_tfp_concept_ids),
        ("clearance CLI --domain", check_cli_domain_flag),
    ]
    all_errs: list[str] = []
    for label, fn in checks:
        errs = fn()
        if errs:
            print(f"[{label}]", file=sys.stderr)
            for e in errs:
                _fail(e)
            all_errs.extend(errs)
    if all_errs:
        print(
            f"Total core-default/TFP boundary violations: {len(all_errs)}",
            file=sys.stderr,
        )
        return 1
    print(
        "Core-default/TFP calibration boundary: OK "
        "(DEFAULT=core=syzif; TFP=opt-in Class B only).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
