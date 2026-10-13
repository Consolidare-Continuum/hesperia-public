#!/usr/bin/env python3
# HESPERIA — Task 6 Phase 1.8: version authority quick check.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: python3 tools/validate_version_consistency.py

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_VERSION_YAML = _REPO / "VERSION.yaml"
_PYPROJECT = _REPO / "pyproject.toml"


def main() -> int:
    errs: list[str] = []
    if not _VERSION_YAML.is_file():
        errs.append(f"missing {_VERSION_YAML}")
    if not _PYPROJECT.is_file():
        errs.append("missing pyproject.toml")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1

    import yaml

    doc = yaml.safe_load(_VERSION_YAML.read_text(encoding="utf-8")) or {}
    sys_v = str(doc.get("system_version", ""))
    pp = _PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', pp, re.M)
    pp_v = m.group(1) if m else ""
    if sys_v != pp_v:
        errs.append(f"VERSION.yaml system_version ({sys_v!r}) != pyproject version ({pp_v!r})")

    # Hard requirement: no filesystem/symlink dependency.
    # `hesperia/VERSION.yaml` must be a real file with the same content as the root `VERSION.yaml`.
    hesperia_path = _REPO / "hesperia" / "VERSION.yaml"
    if hesperia_path.is_file():
        root_text = _VERSION_YAML.read_text(encoding="utf-8").strip()
        hesperia_text = hesperia_path.read_text(encoding="utf-8").strip()
        if root_text != hesperia_text:
            errs.append("hesperia/VERSION.yaml content differs from root VERSION.yaml")
    else:
        errs.append("hesperia/VERSION.yaml missing (expected identical copy of ../VERSION.yaml)")

    sch = doc.get("schema") or {}
    if not sch.get("public_output"):
        errs.append("VERSION.yaml schema.public_output missing")

    defaults = doc.get("defaults") or {}
    pack = defaults.get("active_calibration_dict_pack")
    tfp_v1 = doc.get("tfp_module_v1")
    if not isinstance(tfp_v1, dict):
        errs.append("VERSION.yaml tfp_module_v1 block missing (TFP module v1 compatibility)")
    else:
        tfp_pin = tfp_v1.get("pinned_calibration_dict_pack")
        if not tfp_pin:
            errs.append("VERSION.yaml tfp_module_v1.pinned_calibration_dict_pack missing")
        elif pack and str(tfp_pin) != str(pack):
            errs.append(
                "VERSION.yaml tfp_module_v1.pinned_calibration_dict_pack must match "
                f"defaults.active_calibration_dict_pack (got {tfp_pin!r} vs {pack!r})"
            )
        if str(tfp_v1.get("data_layout") or "") != "tfp_v1":
            errs.append(
                "VERSION.yaml tfp_module_v1.data_layout must be 'tfp_v1' (TFP-DATA-T17)"
            )
    archive = doc.get("archive") or {}
    placeholder_pack = archive.get("public_archive_placeholder_dict_pack")
    if placeholder_pack and str(placeholder_pack) != "archive_063_minimal":
        errs.append(
            "VERSION.yaml archive.public_archive_placeholder_dict_pack should stay 'archive_063_minimal'"
        )
    if not pack:
        errs.append("VERSION.yaml defaults.active_calibration_dict_pack missing (pin calibration dir name)")
    else:
        pack_dir = _REPO / "assets" / "calibration" / "dicts" / str(pack)
        if pack_dir.is_dir():
            required = [pack_dir / "dict_a.jsonl", pack_dir / "dict_b.jsonl", pack_dir / "links.jsonl"]
            for required_path in required:
                if not required_path.is_file():
                    errs.append(
                        f"defaults.active_calibration_dict_pack {pack!r}: expected {required_path} (missing)"
                    )
            metrics_candidates = [
                pack_dir / "metrics.json",
                pack_dir / "metrics_baseline_v052_2.json",
            ]
            if not any(candidate.is_file() for candidate in metrics_candidates):
                fallback_candidates = list(pack_dir.glob("metrics_baseline*.json"))
                if not fallback_candidates:
                    errs.append(
                        f"defaults.active_calibration_dict_pack {pack!r}: missing metrics.json or metrics_baseline*.json"
                    )
        else:
            print(
                f"validate_version_consistency: SKIP calibration pack path check (no {pack_dir}; minimal clone)",
                file=sys.stderr,
            )

    if errs:
        print("validate_version_consistency: FAIL", file=sys.stderr)
        for e in errs:
            print(" ", e, file=sys.stderr)
        return 1

    pack_s = str(pack) if pack else ""
    print(
        f"validate_version_consistency: OK system_version={sys_v} "
        f"public_output_schema={sch.get('public_output')} active_calibration_dict_pack={pack_s}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
