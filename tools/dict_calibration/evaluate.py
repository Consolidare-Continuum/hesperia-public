# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 6 — Run DLCR (Hesperia) evaluation over sample texts + calibration dicts."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

from . import repo_root
from .candidate_validation import MANIFEST_V2, validate_v2_artifacts


Runner = Callable[..., dict[str, Any]]
FREEZE_SCHEMA_VERSION = "hesperia.dict_calibration.freeze_manifest.v1"
SUPPORTED_FREEZE_SCHEMAS = frozenset({FREEZE_SCHEMA_VERSION, MANIFEST_V2})
ELIGIBLE_BUNDLE_STATES = frozenset(
    {"candidate", "release_candidate", "active", "last_known_good"}
)
SUPPORTED_MATCH_TYPES = frozenset({"exact", "phrase", "lemma", "stem", "pattern"})


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} invalid JSONL at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path.name} schema requires object rows")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path.name} schema requires at least one row")
    return rows


def _safe_artifact_path(bundle: Path, value: Any, role: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{role} path is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{role} path is unsafe")
    path = bundle / relative
    try:
        path.resolve(strict=True).relative_to(bundle.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"{role} path escapes or is missing from bundle") from exc
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{role} path must be a regular bundle file")
    return path


def _read_bundle(
    bundle: Path,
    *,
    require_manifest_v2: bool = False,
) -> dict[str, Any]:
    manifest_path = bundle / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("manifest path must be a regular bundle file")
    sidecar = bundle / "manifest.json.sha256"
    if not sidecar.is_file():
        raise ValueError("manifest hash sidecar is missing")
    sidecar_digest = sidecar.read_text(encoding="ascii").split()[0]
    if sidecar_digest != _sha256(manifest_path):
        raise ValueError("manifest bytes do not match hash sidecar")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest schema requires an object")
    unsigned = {key: value for key, value in manifest.items() if key != "bundle_id"}
    expected_bundle_id = _sha256_bytes(_canonical_bytes(unsigned))
    if manifest.get("bundle_id") != expected_bundle_id:
        raise ValueError("manifest bundle_id does not match canonical bytes")
    schema_version = manifest.get("schema_version")
    if schema_version not in SUPPORTED_FREEZE_SCHEMAS:
        raise ValueError("manifest schema_version is not supported")
    if require_manifest_v2 and schema_version != MANIFEST_V2:
        raise ValueError("candidate manifest-v2 is required; v1 is baseline-only")
    state = manifest.get("state")
    if state not in ELIGIBLE_BUNDLE_STATES:
        raise ValueError(f"manifest state is quarantined or release-ineligible: {state}")
    if manifest.get("quarantined") is True or manifest.get("release_eligibility") is False:
        raise ValueError("manifest is quarantined or release-ineligible")
    provenance = manifest.get("provenance")
    _validate_frozen_provenance(provenance)

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest artifacts are missing")
    if schema_version == MANIFEST_V2:
        validated_paths, _counts = validate_v2_artifacts(bundle, manifest)
        return {
            "bundle_id": manifest["bundle_id"],
            "dict_a_path": validated_paths["dict_a_matcher"],
            "dict_b_path": validated_paths["dict_b_canonical"],
        }
    paths: dict[str, Path] = {}
    for role in ("dict_a_matcher", "dict_b_canonical"):
        descriptor = artifacts.get(role)
        if not isinstance(descriptor, dict):
            raise ValueError(f"{role} manifest descriptor is missing")
        expected_status = "matcher_ready" if role == "dict_a_matcher" else "canonical"
        if descriptor.get("status") != expected_status:
            raise ValueError(f"{role} status must be {expected_status}")
        path = _safe_artifact_path(bundle, descriptor.get("path"), role)
        if descriptor.get("sha256") != _sha256(path):
            raise ValueError(f"{role} hash does not match artifact bytes")
        paths[role] = path
    return {
        "bundle_id": manifest["bundle_id"],
        "dict_a_path": paths["dict_a_matcher"],
        "dict_b_path": paths["dict_b_canonical"],
    }


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_frozen_provenance(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("manifest provenance must be a frozen object")
    for key in (
        "model",
        "checkpoint",
        "segmentation_rule",
        "statistical_rule",
        "builder_revision",
    ):
        if not _non_empty_text(value.get(key)):
            raise ValueError(f"manifest provenance.{key} is missing")
    if "mock" in str(value.get("model")).casefold():
        raise ValueError("manifest provenance identifies mock data")
    if not _is_sha256(value.get("prompt_sha256")):
        raise ValueError("manifest provenance.prompt_sha256 is invalid")
    resolver = value.get("resolver")
    if (
        not isinstance(resolver, dict)
        or not _non_empty_text(resolver.get("version"))
        or not _is_sha256(resolver.get("configuration_sha256"))
    ):
        raise ValueError("manifest provenance.resolver is incomplete")
    corpus = value.get("corpus")
    source_hashes = corpus.get("source_hashes") if isinstance(corpus, dict) else None
    if (
        not isinstance(corpus, dict)
        or not _non_empty_text(corpus.get("path"))
        or not isinstance(source_hashes, dict)
        or not source_hashes
        or not all(
            _non_empty_text(path) and ".." not in Path(path).parts and _is_sha256(digest)
            for path, digest in source_hashes.items()
        )
    ):
        raise ValueError("manifest provenance.corpus.source_hashes is incomplete")


def _validate_candidate_artifacts(bundle: dict[str, Any]) -> None:
    dict_a_rows = _load_jsonl(bundle["dict_a_path"])
    dict_b_rows = _load_jsonl(bundle["dict_b_path"])

    dict_b_ids: set[str] = set()
    for row in dict_b_rows:
        concept_id = row.get("concept_id")
        related = row.get("related_concept_ids")
        if not isinstance(concept_id, str) or not concept_id:
            raise ValueError("dict_b schema requires concept_id")
        if not isinstance(related, list) or not all(
            isinstance(item, str) and item for item in related
        ):
            raise ValueError(f"{concept_id} Dict B reference schema is invalid")
        if concept_id in dict_b_ids:
            raise ValueError(f"{concept_id} Dict B concept is duplicated")
        dict_b_ids.add(concept_id)

    entry_ids: set[str] = set()
    normalized_forms: set[str] = set()
    for row in dict_a_rows:
        entry_id = row.get("entry_id")
        normalized_form = row.get("normalized_form")
        match_type = row.get("match_type")
        candidates = row.get("candidate_concept_ids")
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError("dict_a matcher schema requires entry_id")
        if not isinstance(normalized_form, str) or not normalized_form:
            raise ValueError("dict_a matcher schema requires normalized_form")
        if match_type not in SUPPORTED_MATCH_TYPES:
            raise ValueError("dict_a matcher schema has unsupported match_type")
        if not isinstance(candidates, list) or not candidates or not all(
            isinstance(item, str) and item for item in candidates
        ):
            raise ValueError("dict_a matcher schema requires candidate_concept_ids")
        if len(set(candidates)) != len(candidates):
            raise ValueError("dict_a matcher has duplicate candidate_concept_ids")
        if entry_id in entry_ids:
            raise ValueError(f"dict_a matcher duplicate entry_id: {entry_id}")
        if normalized_form in normalized_forms:
            raise ValueError(
                f"dict_a matcher duplicate normalized_form: {normalized_form}"
            )
        entry_ids.add(entry_id)
        normalized_forms.add(normalized_form)
        for concept_id in candidates:
            if concept_id not in dict_b_ids:
                raise ValueError(
                    f"{concept_id} candidate concept is missing from Dict B reference set"
                )

    for row in dict_b_rows:
        for concept_id in row["related_concept_ids"]:
            if concept_id not in dict_b_ids:
                raise ValueError(
                    f"{concept_id} Dict B reference closure is incomplete"
                )


def _anchor_for_row(row: dict[str, Any]) -> str:
    explicit = row.get("hex_anchor")
    if isinstance(explicit, str) and explicit.startswith("HX-") and len(explicit) == 7:
        try:
            number = int(explicit[3:])
        except ValueError:
            number = 0
        if 1 <= number <= 288:
            return explicit
    area_ids = row.get("area_ids")
    family_ids = row.get("family_ids")
    if not (
        isinstance(area_ids, list)
        and area_ids
        and isinstance(family_ids, list)
        and family_ids
    ):
        raise ValueError(f"{row.get('concept_id')} Dict B lacks a bundle anchor")
    try:
        area = int(str(area_ids[0]).removeprefix("A"))
        family = int(str(family_ids[0]).removeprefix("F"))
    except ValueError as exc:
        raise ValueError(f"{row.get('concept_id')} Dict B anchor is invalid") from exc
    if not (0 <= area < 12 and 0 <= family < 24):
        raise ValueError(f"{row.get('concept_id')} Dict B anchor is out of range")
    return f"HX-{area * 24 + family + 1:04d}"


def _write_bundle_anchors(bundle: dict[str, Any], path: Path) -> None:
    rows = _load_jsonl(bundle["dict_b_path"])
    anchors = {str(row["concept_id"]): _anchor_for_row(row) for row in rows}
    path.write_text(
        json.dumps(anchors, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _shannon_entropy(weights: dict[str, float]) -> float:
    tot = sum(max(0.0, float(v)) for v in weights.values())
    if tot <= 0:
        return 0.0
    h = 0.0
    for v in weights.values():
        p = max(0.0, float(v)) / tot
        if p > 0:
            h -= p * math.log(p + 1e-15, 2)
    return h


def _coverage(canonical: str, span_outputs: list[dict[str, Any]]) -> float:
    if not canonical:
        return 1.0
    n = len(canonical)
    mask = [0] * n
    for s in span_outputs:
        ss = s.get("source_char_start")
        se = s.get("source_char_end")
        if isinstance(ss, int) and isinstance(se, int) and 0 <= ss < se <= n:
            for j in range(ss, se):
                mask[j] = 1
            continue
        mt = str(s.get("source_text_span") or "")
        if not mt:
            continue
        start = 0
        while True:
            idx = canonical.find(mt, start)
            if idx < 0:
                break
            for j in range(idx, min(n, idx + len(mt))):
                mask[j] = 1
            start = idx + 1
    covered = sum(mask)
    return covered / max(1, n)


def _normalized_distribution(weights: dict[str, float]) -> dict[str, float]:
    total = sum(float(value) for value in weights.values())
    if total <= 0:
        return {}
    return {
        key: round(float(value) / total, 6) for key, value in sorted(weights.items())
    }


def _validated_spans(output: dict[str, Any], canonical: str) -> list[dict[str, Any]]:
    raw_spans = output.get("span_resolutions") or []
    if not isinstance(raw_spans, list):
        raise ValueError("span_resolutions must be a list")
    offsets: set[tuple[int, int]] = set()
    keys: set[tuple[int, int, str]] = set()
    spans: list[dict[str, Any]] = []
    for span in raw_spans:
        if not isinstance(span, dict):
            raise ValueError("span resolution must be an object")
        start = span.get("source_char_start")
        end = span.get("source_char_end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end <= start
            or end > len(canonical)
        ):
            raise ValueError("span source_char_start/source_char_end offsets are invalid")
        source_text = span.get("source_text_span")
        if not isinstance(source_text, str):
            raise ValueError("span source_text_span must be text")
        offset_key = (start, end)
        span_key = (start, end, source_text)
        if offset_key in offsets or span_key in keys:
            raise ValueError("duplicate span offsets are not allowed")
        offsets.add(offset_key)
        keys.add(span_key)
        spans.append(span)
    return spans


def _evaluation_view(output: dict[str, Any]) -> dict[str, Any]:
    canonical = str(output.get("canonical_text") or "")
    spans = _validated_spans(output, canonical)
    accepted = output.get("lexical_hits_accepted")
    rejected = output.get("lexical_hits_rejected")
    if (
        not isinstance(accepted, int)
        or isinstance(accepted, bool)
        or accepted < 0
        or not isinstance(rejected, int)
        or isinstance(rejected, bool)
        or rejected < 0
    ):
        raise ValueError("accepted/rejected metrics must be non-negative integers")
    concept_weights = _validated_weights(output.get("concept_weights"), "concept_weights")
    family_activation = _validated_weights(
        output.get("family_activation"), "family_activation"
    )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "coverage": round(_coverage(canonical, spans), 6),
        "concept_weights": concept_weights,
        "family_activation": family_activation,
        "span_resolutions": spans,
    }


def _validated_weights(value: Any, field: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    validated: dict[str, float] = {}
    for key, raw_weight in sorted(value.items()):
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field} keys must be non-empty text")
        if (
            not isinstance(raw_weight, (int, float))
            or isinstance(raw_weight, bool)
            or not math.isfinite(float(raw_weight))
            or float(raw_weight) < 0
        ):
            raise ValueError(f"{field} values must be finite and non-negative")
        validated[key] = float(raw_weight)
    return validated


def _span_key(span: dict[str, Any]) -> tuple[int, int, str]:
    return (
        span["source_char_start"],
        span["source_char_end"],
        span["source_text_span"],
    )


def _span_diffs(
    sample_id: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_spans = {_span_key(span): span for span in baseline["span_resolutions"]}
    candidate_spans = {_span_key(span): span for span in candidate["span_resolutions"]}
    diffs: list[dict[str, Any]] = []
    for key in sorted(set(baseline_spans) | set(candidate_spans)):
        base = baseline_spans.get(key)
        cand = candidate_spans.get(key)
        if base is None:
            status = "candidate_only"
        elif cand is None:
            status = "baseline_only"
        elif base == cand:
            status = "unchanged"
        else:
            status = "changed"
        start, end, source_text = key
        diffs.append(
            {
                "span_id": _sha256_bytes(
                    f"{sample_id}\0{start}\0{end}\0{source_text}".encode("utf-8")
                ),
                "source_char_start": start,
                "source_char_end": end,
                "source_text_span": source_text,
                "status": status,
                "baseline": base,
                "candidate": cand,
            }
        )
    return diffs


def _aggregate(views: list[dict[str, Any]]) -> dict[str, Any]:
    concept_weights: dict[str, float] = {}
    family_weights: dict[str, float] = {}
    for view in views:
        for concept_id, value in view["concept_weights"].items():
            concept_weights[concept_id] = concept_weights.get(concept_id, 0.0) + value
        for family_id, value in view["family_activation"].items():
            family_weights[family_id] = family_weights.get(family_id, 0.0) + value
    return {
        "accepted": sum(view["accepted"] for view in views),
        "rejected": sum(view["rejected"] for view in views),
        "coverage": round(
            sum(view["coverage"] for view in views) / max(1, len(views)), 6
        ),
        "entropy": round(_shannon_entropy(concept_weights), 6),
        "family_distribution": _normalized_distribution(family_weights),
    }


def _aggregate_delta(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    family_ids = sorted(
        set(baseline["family_distribution"]) | set(candidate["family_distribution"])
    )
    return {
        "accepted": candidate["accepted"] - baseline["accepted"],
        "rejected": candidate["rejected"] - baseline["rejected"],
        "coverage": round(candidate["coverage"] - baseline["coverage"], 6),
        "entropy": round(candidate["entropy"] - baseline["entropy"], 6),
        "family_distribution": {
            family_id: round(
                candidate["family_distribution"].get(family_id, 0.0)
                - baseline["family_distribution"].get(family_id, 0.0),
                6,
            )
            for family_id in family_ids
        },
    }


def evaluate_bundle_comparison(
    texts: list[str],
    *,
    baseline_bundle: Path,
    candidate_bundle: Path,
    repo_path: Path | None = None,
    mode: str = "core",
    runner: Runner = run_dlcr_pipeline,
) -> dict[str, Any]:
    """Compare manifest-pinned bundles over the same ordered sample sequence."""
    if not isinstance(texts, list) or not texts:
        raise ValueError("texts must contain at least one evaluation sample")
    if not all(isinstance(text, str) and bool(text.strip()) for text in texts):
        raise ValueError("each evaluation sample must be non-empty text")
    baseline = _read_bundle(baseline_bundle)
    candidate = _read_bundle(candidate_bundle, require_manifest_v2=True)
    _validate_candidate_artifacts(baseline)
    _validate_candidate_artifacts(candidate)
    repo = repo_path or repo_root()
    baseline_views: list[dict[str, Any]] = []
    candidate_views: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="hesperia-bundle-comparison-") as temp_dir:
        anchor_paths = {
            "baseline": Path(temp_dir) / "baseline-anchors.json",
            "candidate": Path(temp_dir) / "candidate-anchors.json",
        }
        _write_bundle_anchors(baseline, anchor_paths["baseline"])
        _write_bundle_anchors(candidate, anchor_paths["candidate"])
        for ordinal, text in enumerate(texts):
            sample_id = _sha256_bytes(f"{ordinal}\0{text}".encode("utf-8"))
            views: list[dict[str, Any]] = []
            for side, bundle in (("baseline", baseline), ("candidate", candidate)):
                output = runner(
                    text,
                    repo_root=repo,
                    dict_a_paths=[bundle["dict_a_path"]],
                    dict_b_paths=[bundle["dict_b_path"]],
                    anchors_path=anchor_paths[side],
                    mode=mode,
                )
                views.append(_evaluation_view(output))
            baseline_view, candidate_view = views
            baseline_views.append(baseline_view)
            candidate_views.append(candidate_view)
            diffs = _span_diffs(sample_id, baseline_view, candidate_view)
            ambiguous = []
            candidate_by_key = {
                _span_key(span): span for span in candidate_view["span_resolutions"]
            }
            for diff in diffs:
                key = (
                    diff["source_char_start"],
                    diff["source_char_end"],
                    diff["source_text_span"],
                )
                span = candidate_by_key.get(key)
                candidate_concepts = (span or {}).get("candidate_concepts")
                if isinstance(candidate_concepts, list) and len(candidate_concepts) > 1:
                    ambiguous.append(
                        {
                            "span_id": diff["span_id"],
                            "source_char_start": diff["source_char_start"],
                            "source_char_end": diff["source_char_end"],
                            "candidate_concepts": candidate_concepts,
                            "winning_concept_id": span.get("winning_concept_id"),
                        }
                    )
            samples.append(
                {
                    "sample_id": sample_id,
                    "ordinal": ordinal,
                    "text_sha256": _sha256_bytes(text.encode("utf-8")),
                    "baseline": baseline_view,
                    "candidate": candidate_view,
                    "span_diffs": diffs,
                    "ambiguous_candidate_spans": ambiguous,
                }
            )

    baseline_aggregate = _aggregate(baseline_views)
    candidate_aggregate = _aggregate(candidate_views)
    report = {
        "schema_version": "hesperia.dict_calibration.bundle_comparison.v1",
        "baseline": {"bundle_id": baseline["bundle_id"]},
        "candidate": {"bundle_id": candidate["bundle_id"]},
        "samples": samples,
        "aggregate": {
            "baseline": baseline_aggregate,
            "candidate": candidate_aggregate,
            "delta": _aggregate_delta(baseline_aggregate, candidate_aggregate),
        },
        "weight_zero_identity": all(
            sample["baseline"] == sample["candidate"] for sample in samples
        ),
    }
    report["report_sha256"] = _sha256_bytes(_canonical_bytes(report))
    return report


def evaluate_on_texts(
    texts: list[str],
    *,
    dict_a_path: Path,
    dict_b_paths: list[Path],
    anchors_path: Path,
    repo_path: Path | None = None,
    mode: str = "clinical_speech",
) -> dict[str, Any]:
    repo = repo_path or repo_root()
    da = [dict_a_path]
    per_text: list[dict[str, Any]] = []
    agg_cw: dict[str, float] = {}
    agg_fam: dict[str, float] = {}
    total_accepted = 0
    total_rejected = 0
    unmapped_ratios: list[float] = []

    for t in texts:
        out = run_dlcr_pipeline(
            t,
            repo_root=repo,
            dict_a_paths=da,
            dict_b_paths=dict_b_paths,
            anchors_path=anchors_path,
            mode=mode,
        )
        cw = out.get("concept_weights") or {}
        for k, v in cw.items():
            agg_cw[k] = agg_cw.get(k, 0.0) + float(v)
        fam = out.get("family_activation") or {}
        for k, v in fam.items():
            agg_fam[k] = agg_fam.get(k, 0.0) + float(v)
        total_accepted += int(out.get("lexical_hits_accepted") or 0)
        total_rejected += int(out.get("lexical_hits_rejected") or 0)
        canon = str(out.get("canonical_text") or "")
        spans = list(out.get("span_resolutions") or [])
        cov = _coverage(canon, spans)
        unmapped_ratios.append(1.0 - cov)

        per_text.append(
            {
                "lexical_hits_accepted": out.get("lexical_hits_accepted"),
                "lexical_hits_rejected": out.get("lexical_hits_rejected"),
                "concept_weights": out.get("concept_weights"),
                "family_activation": out.get("family_activation"),
                "hex_concentration": out.get("hex_concentration"),
                "degradation_flags": out.get("degradation_flags"),
                "unmapped_lexical_ratio_est": round(1.0 - cov, 4),
            }
        )

    noise_denom = max(1, total_accepted + total_rejected)
    eval_out = {
        "run": "dict_calibration_eval_v1",
        "n_texts": len(texts),
        "per_text": per_text,
        "aggregate": {
            "concept_activation": {k: round(v, 6) for k, v in sorted(agg_cw.items())},
            "concept_entropy": round(_shannon_entropy(agg_cw), 6),
            "family_activation": {k: round(v, 6) for k, v in sorted(agg_fam.items())},
            "family_balance_gini_stub": round(
                1.0 - sum(1 for _ in agg_fam) / max(1, len(agg_fam)), 6
            ),
            "noise_ratio": round(total_rejected / noise_denom, 6),
            "unmapped_lexical_pct_mean": round(
                100.0 * (sum(unmapped_ratios) / max(1, len(unmapped_ratios))), 4
            ),
        },
    }
    return eval_out
