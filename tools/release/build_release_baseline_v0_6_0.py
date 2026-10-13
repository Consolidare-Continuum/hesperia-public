#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
RELEASE_DIR = REPO / "release" / "v0.6.0"
SCHEMA_SRC = REPO / "schemas" / "public" / "public_output_schema.json"
CAPS_SRC = REPO / "hesperia" / "system" / "capabilities.yaml"
VERSION_SRC = REPO / "VERSION.yaml"
CANONICAL_INPUT = REPO / "tests" / "fixtures" / "release_v0_5_0" / "canonical_input.txt"
E2E_ARTIFACT_ROOT = REPO / "assets" / "artifacts" / "e2e_full_stack"
PUBLIC_RELEASE_FORBIDDEN_OUTPUT_TERMS = ("sphere",)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=check)


def _git_commit() -> str:
    try:
        return _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def _git_dirty() -> bool:
    try:
        return bool(_run(["git", "status", "--porcelain"]).stdout.strip())
    except subprocess.CalledProcessError:
        return True


def _version_doc() -> dict:
    return yaml.safe_load(VERSION_SRC.read_text(encoding="utf-8")) or {}


def _load_e2e_outputs() -> list[str]:
    text = (REPO / "runtime" / "pipeline" / "run_e2e_all.py").read_text(encoding="utf-8")
    module = ast.parse(text)
    names = {
        "E2E_OUTPUTS",
        "E2E_OUTPUT_FIELD_DYNAMICS",
        "E2E_OUTPUT_DLCR",
    }
    values: dict[str, object] = {}
    for node in module.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in names:
                values[name] = ast.literal_eval(node.value)
    outputs = list(values.get("E2E_OUTPUTS", ()))
    if "E2E_OUTPUT_FIELD_DYNAMICS" in values:
        outputs.append(str(values["E2E_OUTPUT_FIELD_DYNAMICS"]))
    if "E2E_OUTPUT_DLCR" in values:
        outputs.append(str(values["E2E_OUTPUT_DLCR"]))
    return outputs


def _is_public_release_output(name: str) -> bool:
    lowered = name.lower()
    return not any(term in lowered for term in PUBLIC_RELEASE_FORBIDDEN_OUTPUT_TERMS)


def _artifact_entry(name: str) -> dict[str, object]:
    path = E2E_ARTIFACT_ROOT / name
    entry: dict[str, object] = {
        "name": name,
        "required_for_full_stack_example": name != "run_output_e2e_dlcr.json",
    }
    if path.is_file():
        entry["example_path"] = path.relative_to(REPO).as_posix()
        entry["bytes"] = path.stat().st_size
        entry["sha256"] = _sha256_file(path)
    else:
        entry["example_path"] = None
    return entry


def _load_public_system_seal() -> dict[str, object]:
    path = RELEASE_DIR / "system_seal.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    checks = dict(raw.get("checks") or {})
    notes = dict(raw.get("notes") or {})
    if "hex_dependency" in checks:
        checks["dependency_guard"] = checks.pop("hex_dependency")
    if "pipeline" in checks:
        checks["shipping_path"] = checks.pop("pipeline")
    if "hex_dependency" in notes:
        notes["dependency_guard"] = "required tensors enforced (ValueError as expected)"
        notes.pop("hex_dependency", None)
    if "pipeline" in notes:
        notes["shipping_path"] = "canonical shipping modules do not invoke legacy pipeline entrypoints"
        notes.pop("pipeline", None)
    raw["checks"] = checks
    raw["notes"] = notes
    return raw


def _build_reference_output() -> dict:
    sys.path.insert(0, str(REPO))
    from runtime.services.analysis_service import run_structural_analysis

    text = CANONICAL_INPUT.read_text(encoding="utf-8").strip()
    return run_structural_analysis(text, assets_root=REPO / "assets" / "lexicon" / "curated", stages="full")


def _baseline_scope_md(version: str, dict_pack: str) -> str:
    return f"""# HESPERIA v{version} baseline sealed release

Ship the existing engine as-is.
Do not ship calibration dict payloads.
Do not ship corpus payloads.
Do not ship Chroma state.

Treat this folder as the baseline release contract.
Use it before Docker packaging.

## Include

- Ship runtime, core, hesperia, lexicon, schemas, matrices, P_CH, calibration profiles, public schema, capability flags.
- Ship current public routes only: `GET /health`, `POST /analyze`, `POST /compare`, `POST /batch`, `POST /batch-analyze`.
- Ship reference output and output inventory from working examples.

## Exclude

- Exclude `assets/calibration/dicts/`.
- Exclude corpus session payload trees.
- Exclude Chroma persist directories and snapshots.
- Exclude ad-hoc outputs and local run state.

## Pin

- Pin system version to `0.6.0`.
- Pin active calibration profile to `default_v1`.
- Pin expected dict pack name to `{dict_pack}`.
- Keep dicts external. Prebuild them before sealed validation.
"""


def _dict_prebuild_md(dict_pack: str) -> str:
    return f"""# Dict prebuild

Do not bundle dict payloads in release.
Prebuild them outside the release zip.
Stage them under `assets/calibration/dicts/{dict_pack}/` before full product seal.

## Required files

- `dict_a.jsonl`
- `dict_b.jsonl`
- `dict_c.jsonl`
- `links.jsonl`
- `weights.jsonl`
- `metrics.json`

## Do

- Build the pinned pack name exactly.
- Keep filenames exact.
- Keep JSONL schema stable.
- Keep `metrics.json` present for gate checks.
- Run `python3 tools/validate_version_consistency.py`.
- Run the calibration gates after dict placement.

## Do not

- Do not rename the pack dir.
- Do not commit private source corpora into the release bundle.
- Do not ship draft dict waves as product baseline.
"""


def _corpus_chroma_md() -> str:
    return """# Corpus and Chroma

Do not ship corpus payloads in baseline release.
Do not ship Chroma storage in baseline release.
Describe them. Prebuild them outside the package.

## Corpus

- Store corpus text outside release payload.
- Use a manifest with `session_id`, `therapist_id`, `patient_id`, `session_number`, `date`, `path`.
- Use working examples from `tests/fixtures/tfp_calibration/` and `tests/fixtures/dict_calibration/corpus/sample.md`.
- Keep relative file paths valid from the manifest base dir.
- Load through `hesperia/corpus/session_corpus.py`.

## Chroma

- Treat Chroma as external runtime state.
- Precreate collections before retrieval tasks.
- Keep persist dirs or remote stores outside git and outside release zip.
- Record collection names, source layer, version, and ingestion command in deployment notes.
- Use working retrieval examples from the Hesperia integration layer only as reference behavior, not as bundled state.

## Required operator rule

- Prepare corpus first.
- Prepare dict pack second.
- Build or ingest Chroma third.
- Run system seal only after all three are in place.
"""


def _outputs_md(outputs: list[dict[str, object]]) -> str:
    lines = [
        "# Output surface",
        "",
        "Use these as the baseline output catalog.",
        "Treat listed example paths as working references.",
        "",
        "## Public envelope",
        "",
        "- Require `system_version`.",
        "- Require `schema_version`.",
        "- Require `build_id`.",
        "- Require `calibration_profile`.",
        "",
        "## Output files",
        "",
    ]
    for item in outputs:
        path = item.get("example_path") or "no checked-in example"
        lines.append(f"- `{item['name']}` — example: `{path}`")
    return "\n".join(lines) + "\n"


def _release_contents_md() -> str:
    return """# Release contents

Use this folder as the `0.6.0` release contract.
Read the files in this order.

## Read first

- `manifest.json` — release identity, routes, payload policy, doc list.
- `final_gate_status.json` — sealed gate result for this baseline.
- `system_seal.json` — latest full system seal result.

## Prepare externals

- `DICT_PREBUILD.md` — required dict pack name, filenames, and prebuild rules.
- `CORPUS_AND_CHROMA.md` — required corpus and Chroma preparation rules.

## Ship runtime

- `DOCKER_BUNDLE.md` — Docker bundle build and smoke contract.
- `docker_bundle_manifest.json` — Docker image tag and tar hash.
- `docker_bundle_verification.json` — Docker check result.
- `docker_requirements_used.txt` — runtime dependency lock used in shipping image.

## Validate behavior

- `OUTPUT_SURFACE.md` — output catalog and public envelope requirements.
- `output_inventory.json` — output examples and hashes.
- `e2e_reference_output.json` — checked reference behavior.
- `schema.json` — public output schema.
- `capabilities.yaml` — capability flags shipped with the engine.

## Trace build

- `BUILD_PROVENANCE.json` — generator and source trace.
- `checksums.txt` — file integrity list for this folder.
"""


def _agentic_install_md(version: str, dict_pack: str) -> str:
    return f"""# Agentic install

Install `HESPERIA {version}` in this order.
Do not improvise the order.
Do not bake mutable data into the image.

## Inputs

- Docker image tag: `hesperia-api:{version}`
- Docker tar: `release/v{version}/hesperia-api-v{version}.tar`
- Required dict pack: `{dict_pack}`
- Required external state: dicts, corpus, Chroma

## Prepare host

- Create host dirs for `dicts`, `corpus`, `chroma`, and `runtime-output`.
- Keep them outside the repo checkout.
- Keep ownership writable by the runtime user.

## Prepare externals

- Build dict pack `{dict_pack}` exactly.
- Place dict files under `assets/calibration/dicts/{dict_pack}/` inside the runtime mount root.
- Prepare corpus manifests and corpus files.
- Prepare or ingest Chroma collections before retrieval runs.

## Load image

- Load tar with `docker load -i release/v{version}/hesperia-api-v{version}.tar`.
- Verify image tag `hesperia-api:{version}` exists.

## Run check container

- Start container with external mounts only.
- Expose port `8000`.
- Use `HESPERIA_LICENSE_SKIP=1` only for local smoke.
- Use `HESPERIA_EXPOSE_VERSION=1` for verification only.

## Verify

- Call `GET /health`. Expect `status=ok`.
- Call `GET /version`. Expect `system_version={version}`.
- Call `POST /analyze` with canonical smoke text.
- Verify response contains `system_version`, `schema_version`, `build_id`, `calibration_profile`.

## Gate

- Require `final_gate_status.json` sealed result.
- Require `docker_bundle_verification.json` with `health_ok=true`.
- Require `docker_bundle_verification.json` with `analyze_ok=true`.
- Require forbidden dev dirs absent from `/app`.

## Production rule

- Keep dicts external.
- Keep corpus external.
- Keep Chroma external.
- Replace local verification env with production license/env policy before ship.
"""


def _manifest(version_doc: dict, reference_output: dict, outputs: list[dict[str, object]]) -> dict:
    version = str(version_doc.get("system_version"))
    defaults = version_doc.get("defaults") or {}
    schema = version_doc.get("schema") or {}
    return {
        "system_version": version,
        "release_stage": str(version_doc.get("release_stage") or ""),
        "release_kind": "sealed_baseline_without_dict_payloads",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "schema_version": str(schema.get("public_output") or ""),
        "calibration_profile_default": str(defaults.get("calibration_profile") or ""),
        "dict_pack_expected_external": str(defaults.get("active_calibration_dict_pack") or ""),
        "shipping_api_routes": [
            "GET /health",
            "POST /analyze",
            "POST /compare",
            "POST /batch",
            "POST /batch-analyze",
        ],
        "bundle_payload_policy": {
            "dict_payloads_included": False,
            "corpus_payloads_included": False,
            "chroma_state_included": False,
        },
        "reference_output": {
            "run": reference_output.get("run"),
            "system_version": reference_output.get("system_version"),
            "schema_version": reference_output.get("schema_version"),
            "calibration_profile": reference_output.get("calibration_profile"),
            "build_id": reference_output.get("build_id"),
        },
        "output_inventory_file": "output_inventory.json",
        "release_docs": [
            "RELEASE_SCOPE.md",
            "RELEASE_CONTENTS.md",
            "DICT_PREBUILD.md",
            "CORPUS_AND_CHROMA.md",
            "OUTPUT_SURFACE.md",
            "DOCKER_BUNDLE.md",
            "AGENTIC_INSTALL.md",
        ],
        "artifact_count_described": len(outputs),
    }


def _final_gate_status(version: str) -> dict:
    seal_path = RELEASE_DIR / "system_seal.json"
    seal = {}
    if seal_path.is_file():
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
    checks = {
        "version_authority": False,
        "prod_code_only_shipping_context": False,
        "portable_bundle": False,
        "system_seal": bool(seal.get("status") == "PASS"),
        "dict_payloads_excluded": True,
        "corpus_payloads_excluded": True,
        "chroma_state_excluded": True,
    }
    reasons_fail: list[str] = []
    try:
        _run([sys.executable, "tools/validate_version_consistency.py"])
        checks["version_authority"] = True
    except subprocess.CalledProcessError as e:
        reasons_fail.append(f"validate_version_consistency failed: {e.returncode}")
    try:
        _run(["bash", "tools/ci/verify_prod_code_only.sh", ".", "--shipping-context"])
        checks["prod_code_only_shipping_context"] = True
    except subprocess.CalledProcessError as e:
        reasons_fail.append(f"verify_prod_code_only failed: {e.returncode}")
    try:
        _run([sys.executable, "tools/build_release_bundle.py"])
        _run([sys.executable, "tools/verify_release_bundle.py"])
        checks["portable_bundle"] = True
    except subprocess.CalledProcessError as e:
        reasons_fail.append(f"portable bundle verification failed: {e.returncode}")
    finally:
        for suffix in ("", ".sha256"):
            p = REPO / f"release_bundle_v{version}.zip{suffix}"
            if p.exists():
                p.unlink()
    if not checks["system_seal"]:
        reasons_fail.append("system_seal.json missing PASS status")
    sealed = all(checks.values())
    return {
        "system_version": version,
        "sealed": sealed,
        "critical_checks": {k: ("pass" if v else "fail") for k, v in checks.items()},
        "reasons_fail": reasons_fail,
        "note": "Baseline release is valid only as a code-and-contract package. Prepare dicts, corpus, and Chroma outside the bundle before runtime seal on target.",
    }


def _write_checksums() -> None:
    lines: list[str] = []
    for path in sorted(RELEASE_DIR.iterdir()):
        if path.name == "checksums.txt" or path.is_dir():
            continue
        lines.append(f"{_sha256_file(path)}  {path.name}")
    (RELEASE_DIR / "checksums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    version_doc = _version_doc()
    version = str(version_doc.get("system_version") or "")
    if version != "0.6.0":
        print(f"expected VERSION.yaml system_version 0.6.0, got {version!r}", file=sys.stderr)
        return 1
    defaults = version_doc.get("defaults") or {}
    dict_pack = str(defaults.get("active_calibration_dict_pack") or "")
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCHEMA_SRC, RELEASE_DIR / "schema.json")
    shutil.copyfile(CAPS_SRC, RELEASE_DIR / "capabilities.yaml")

    reference_output = _build_reference_output()
    outputs = [_artifact_entry(name) for name in _load_e2e_outputs() if _is_public_release_output(name)]
    public_system_seal = _load_public_system_seal()

    (RELEASE_DIR / "e2e_reference_output.json").write_text(
        json.dumps(reference_output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (RELEASE_DIR / "output_inventory.json").write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "artifact_root_example": E2E_ARTIFACT_ROOT.relative_to(REPO).as_posix(),
                "outputs": outputs,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (RELEASE_DIR / "manifest.json").write_text(
        json.dumps(_manifest(version_doc, reference_output, outputs), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if public_system_seal:
        (RELEASE_DIR / "system_seal.json").write_text(
            json.dumps(public_system_seal, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (RELEASE_DIR / "BUILD_PROVENANCE.json").write_text(
        json.dumps(
            {
                "system_version": version,
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "git_commit": _git_commit(),
                "git_dirty": _git_dirty(),
                "generator": "tools/release/build_release_baseline_v0_6_0.py",
                "source_files": [
                    "VERSION.yaml",
                    "hesperia/system/capabilities.yaml",
                    "runtime/pipeline/run_e2e_all.py",
                    "tests/fixtures/release_v0_5_0/canonical_input.txt",
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (RELEASE_DIR / "RELEASE_SCOPE.md").write_text(_baseline_scope_md(version, dict_pack), encoding="utf-8")
    (RELEASE_DIR / "RELEASE_CONTENTS.md").write_text(_release_contents_md(), encoding="utf-8")
    (RELEASE_DIR / "DICT_PREBUILD.md").write_text(_dict_prebuild_md(dict_pack), encoding="utf-8")
    (RELEASE_DIR / "CORPUS_AND_CHROMA.md").write_text(_corpus_chroma_md(), encoding="utf-8")
    (RELEASE_DIR / "OUTPUT_SURFACE.md").write_text(_outputs_md(outputs), encoding="utf-8")
    (RELEASE_DIR / "AGENTIC_INSTALL.md").write_text(_agentic_install_md(version, dict_pack), encoding="utf-8")
    (RELEASE_DIR / "final_gate_status.json").write_text(
        json.dumps(_final_gate_status(version), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_checksums()
    print(f"baseline release written to {RELEASE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
