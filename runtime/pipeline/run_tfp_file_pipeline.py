#!/usr/bin/env python3
# HESPERIA — RAD. Gena: file-in → multi-artifact TFP + main engine paths (testing / research).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""
Run TFP-oriented pipelines on one or more session texts from a file.

**Input**
  - ``.json`` — ``{"sessions": [{"session_id": "...", "text": "..."}, ...]}`` (same shape as Kernberg smoke).
  - Any other extension — whole file is one session (``session_id`` = stem of filename).

**Outputs** (under ``--out-dir``)
  - ``00_manifest.json`` — scope, flags, session ids, artifact list, **tfp_signal_calibration** (topology + Dict-A knobs), **operational_envelope** (Task 7).
  - ``01_structural_batch.json`` — frozen lexicon structural batch (plane A); per-row + file envelope.
  - ``02_session_tfp_stages.json`` — ``analyze_session`` + ``detect_tfp_stage`` per session (plane B).
  - ``03_hex_microstructure_tfp.json`` — hex microstructure + TFP provenance per session.
  - ``04_dlcr_full.json`` — full ``run_dlcr_pipeline`` payload per session.
  - ``05_sealed_multiscale.json`` — ``run_sealed_multiscale_stack`` per session.
  - ``06_product_analyze.json`` — ``runtime.pipeline.analyze.analyze`` minimal + extended per session.
  - Optional: ``07_session_kme.json``, ``08_triz_complete.json``, ``09_session_topology.json`` (flags).
    ``09_session_topology.json`` sessions carry both ``areas_final`` (whole-session cumulative mass,
    unchanged) and ``areas_working`` (segment-weighted, opening contract/frame window down-weighted)
    plus their ``*_dominant`` ids (CHI-003-02, per CHI-003-01 verdict). Product "dominant area" =
    ``areas_working``; calibration/audit code should keep citing ``areas_final``.
  - With ``--with-topology``: flat ``12_<session_id>_<artifact>.json`` in ``--out-dir`` (coactivation, contradictions,
    metrics, sparse family weights, ``cross_plane_audit.json``; no subfolders) unless ``--skip-triz-activation``.
    Pipeline exits **3** on ``TRIZ_DEAD_LAYER`` / topology+activation write failure.
  - Post-run: ``python3 tools/tfp_calibration_audit.py`` → ``10_calibration_audit.json``; ``tools/calibration_release_gate.py`` → ``11_calibration_release_gate.json``.

Usage::

  python3 -m runtime.pipeline.run_tfp_file_pipeline --input path/to/note.md
  python3 -m runtime.pipeline.run_tfp_file_pipeline --input path/to/note.md --out-dir outputs/tfp/runs/my_named_run

**Gena all-in-one** (same pipeline + audit + schema validation + release gate): ``python3 tools/gena_tfp_bundle_run.py -i path/to/note.md``.

**Output folder discipline:** If ``--out-dir`` is omitted, defaults to ``outputs/tfp/runs/tfp_pipeline_run/<run_id>``. Wrappers: ``gena_tfp_bundle_run`` → ``outputs/tfp/runs/tfp_gena_<stem>``; ``tfp_pipeline_standard_run`` → ``outputs/tfp/runs/tfp_pipeline_run/<uuid>``. See ``docs/specs/TFP_VALUES_LIST`` §0 and ``outputs/README.md``.

Forces ``HESPERIA_DLCR_DOMAIN_PACK=tfp`` unless ``--no-dlcr-domain-pack``. Optional: ``HESPERIA_ANALYZE_DLCR_EVIDENCE=1`` for DLCR evidence inside ``analyze()``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hesperia.extensions.triz.topology_activation_pipeline import concept_id_to_area_family
from hesperia.engine.calibration_dict_paths import resolve_dict_file
from hesperia.modules.tfp.data.tfp_v1.postgres.corpus_grounding import corpus_support

CANONICAL_CONTRADICTION_SOURCE = "12_topology_derived_contradictions"
MIN_CANONICAL_CONTRADICTION_SCORE = 0.15
MAX_CANONICAL_CONTRADICTIONS_FOR_ACTIVATION = 250
GROUNDING_GRANULARITY = "family"


def _round_floats(obj: Any, ndigits: int = 6) -> Any:
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x, ndigits) for x in obj]
    return obj


def _top_keys(values: dict[str, Any], n: int = 12) -> list[str]:
    return sorted(values.keys(), key=lambda k: float(values.get(k) or 0.0), reverse=True)[:n]


def _text_preview(text: str, n: int = 200) -> dict[str, Any]:
    return {"text_preview": text[:n] + ("..." if len(text) > n else ""), "length": len(text)}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_round_floats(data), indent=2, ensure_ascii=False), encoding="utf-8")


def _stable_contradiction_sort_key(row: dict[str, Any], idx: int) -> tuple[str, str, float, int]:
    pair = row.get("pair")
    concept_a = None
    concept_b = None
    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
        concept_a = pair[0]
        concept_b = pair[1]
    else:
        concept_a = row.get("concept_a")
        concept_b = row.get("concept_b")
    a = "" if concept_a is None else str(concept_a)
    b = "" if concept_b is None else str(concept_b)
    left, right = (a, b) if a <= b else (b, a)
    score_raw = row.get("raw_contradiction_score", row.get("score", 0.0))
    try:
        score = float(score_raw)
    except (TypeError, ValueError):
        score = 0.0
    return (left, right, -score, idx)


def _normalize_contradictions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = list(enumerate(rows))
    ordered.sort(key=lambda item: _stable_contradiction_sort_key(item[1], item[0]))
    return [dict(row) for _, row in ordered]


def _extract_contradictions_from_08(path_08: Path, session_id: str) -> list[dict[str, Any]]:
    if not path_08.is_file():
        return []
    try:
        data = json.loads(path_08.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, list):
        return []
    for row in sessions:
        if not isinstance(row, dict):
            continue
        if str(row.get("session_id") or "") != session_id:
            continue
        tc = row.get("triz_complete")
        if isinstance(tc, dict):
            nested = tc.get("triz_complete")
            if isinstance(nested, dict) and isinstance(nested.get("contradictions"), list):
                return _normalize_contradictions([x for x in nested["contradictions"] if isinstance(x, dict)])
            if isinstance(tc.get("contradictions"), list):
                return _normalize_contradictions([x for x in tc["contradictions"] if isinstance(x, dict)])
    return []


def _extract_contradictions_from_12(bundle_dir: Path, session_id: str) -> list[dict[str, Any]]:
    pattern = f"12_{session_id}_*contradictions*.json"
    files = sorted(bundle_dir.glob(pattern), key=lambda p: p.name)
    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("contradictions"), list):
            rows = [x for x in data["contradictions"] if isinstance(x, dict)]
            return _normalize_contradictions(rows)
        if isinstance(data, list):
            rows = [x for x in data if isinstance(x, dict)]
            return _normalize_contradictions(rows)
    return []


def _concept_pair(row: dict[str, Any]) -> tuple[str, str]:
    pair = row.get("pair")
    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
        left = str(pair[0] or "")
        right = str(pair[1] or "")
        return (left, right) if left <= right else (right, left)
    left = str(row.get("concept_a") or "")
    right = str(row.get("concept_b") or "")
    return (left, right) if left <= right else (right, left)


def _structural_family_key(concept_id: str) -> str:
    parsed = concept_id_to_area_family(concept_id)
    if parsed:
        return parsed[1]
    cid = str(concept_id or "").strip()
    return cid or "_unparsed"


def _structural_area_key(concept_id: str) -> str:
    parsed = concept_id_to_area_family(concept_id)
    if parsed:
        return parsed[0]
    cid = str(concept_id or "").strip()
    return cid or "_unparsed"


def _aggregate_structural_hits(lexical_concept_counts: dict[str, int]) -> tuple[dict[str, int], dict[str, int]]:
    """Roll per-concept lexical hits up to family and area keys used by coactivation."""
    family_hits: dict[str, int] = {}
    area_hits: dict[str, int] = {}
    for cid, n in lexical_concept_counts.items():
        hits = int(n)
        family_key = _structural_family_key(cid)
        area_key = _structural_area_key(cid)
        family_hits[family_key] = family_hits.get(family_key, 0) + hits
        area_hits[area_key] = area_hits.get(area_key, 0) + hits
    return family_hits, area_hits


def _pair_family_hits(
    left: str,
    right: str,
    family_hits: dict[str, int],
) -> tuple[int, int]:
    return (
        int(family_hits.get(_structural_family_key(left), 0)),
        int(family_hits.get(_structural_family_key(right), 0)),
    )


def _pair_family_grounded(left: str, right: str, family_hits: dict[str, int]) -> bool:
    left_family_hits, right_family_hits = _pair_family_hits(left, right, family_hits)
    return left_family_hits > 0 and right_family_hits > 0


def _score_value(row: dict[str, Any]) -> float:
    raw = row.get("raw_contradiction_score", row.get("score", 0.0))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _contradiction_id(row: dict[str, Any], *, idx: int) -> str:
    left, right = _concept_pair(row)
    score = _score_value(row)
    segment = row.get("segment_id")
    suffix = f":seg={segment}" if segment is not None else f":idx={idx}"
    return f"{left}|{right}|{score:.6f}{suffix}"


def _build_contradiction_reconciliation(
    *,
    session_id: str,
    direct_rows: list[dict[str, Any]],
    topology_rows: list[dict[str, Any]],
    lexical_hits_accepted: int,
    lexical_concept_counts: dict[str, int],
    dict_b_path: Path | None = None,
) -> dict[str, Any]:
    """Reconcile direct TRIZ vs topology-derived contradictions.

    Grounding for ``zero_lexical_evidence_share`` / ``inferred_share`` is family
    granularity: topology pairs are family-expanded, so a never-hit sibling is
    still grounded when another member of that family was lexically hit.
    Concept-level shares stay in ``*_concept`` fields as diagnostics.

    ``truth_point_accumulation`` (per-pair ``T = max(L, S*W)``, mean across the
    session) is a second, additive signal, not a replacement for the family-grain
    checks above and not wired into any gate yet: ``L`` is the existing family
    grounding (0/1), ``S``/``W`` come from ``tfp_corpus`` (Postgres) trigram
    support + corpus-document-redundancy weight -- see corpus_grounding.py. If
    Postgres is unreachable, S=W=0 for everything and T reduces to L, so this
    never changes pipeline behavior on its own, only reports.
    """
    direct_ids: dict[str, dict[str, Any]] = {}
    topology_ids: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(direct_rows):
        direct_ids[_contradiction_id(row, idx=idx)] = row
    for idx, row in enumerate(topology_rows):
        topology_ids[_contradiction_id(row, idx=idx)] = row

    shared_ids = sorted(set(direct_ids) & set(topology_ids))
    only_in_direct = sorted(set(direct_ids) - set(topology_ids))
    only_in_topology = sorted(set(topology_ids) - set(direct_ids))
    canonical_count = len(topology_rows)
    ratio = float(canonical_count) / float(max(lexical_hits_accepted, 1))

    family_hits, area_hits = _aggregate_structural_hits(lexical_concept_counts)
    all_concept_ids: set[str] = set()
    for row in topology_rows:
        left, right = _concept_pair(row)
        all_concept_ids.add(left)
        all_concept_ids.add(right)
    truth_support = corpus_support(all_concept_ids, dict_b_path) if all_concept_ids else {}

    per_contradiction_audit: list[dict[str, Any]] = []
    inferred_count = 0
    zero_lex_count = 0
    zero_concept_count = 0
    inferred_concept_count = 0
    zero_area_count = 0
    truth_sum = 0.0
    seg_counts: dict[str, int] = {}
    for idx, row in enumerate(topology_rows):
        left, right = _concept_pair(row)
        left_hits = int(lexical_concept_counts.get(left, 0))
        right_hits = int(lexical_concept_counts.get(right, 0))
        direct_support = left_hits + right_hits
        left_family_key = _structural_family_key(left)
        right_family_key = _structural_family_key(right)
        left_area_key = _structural_area_key(left)
        right_area_key = _structural_area_key(right)
        left_family_hits, right_family_hits = _pair_family_hits(left, right, family_hits)
        left_area_hits = int(area_hits.get(left_area_key, 0))
        right_area_hits = int(area_hits.get(right_area_key, 0))
        family_both = left_family_hits > 0 and right_family_hits > 0
        area_both = left_area_hits > 0 and right_area_hits > 0
        segment_id = row.get("segment_id")
        if segment_id is not None:
            seg_key = str(segment_id)
            seg_counts[seg_key] = seg_counts.get(seg_key, 0) + 1
        if not family_both:
            zero_lex_count += 1
        if left_family_hits <= 0 and right_family_hits <= 0:
            inferred_count += 1
        if direct_support <= 0:
            zero_concept_count += 1
            inferred_concept_count += 1
        if not area_both:
            zero_area_count += 1
        left_support = truth_support.get(left, {"S": 0.0, "W": 0.0, "status": "unavailable"})
        right_support = truth_support.get(right, {"S": 0.0, "W": 0.0, "status": "unavailable"})
        s_pair = min(float(left_support["S"]), float(right_support["S"]))
        w_pair = min(float(left_support["W"]), float(right_support["W"]))
        l_value = 1.0 if family_both else 0.0
        truth_point = max(l_value, s_pair * w_pair)
        truth_sum += truth_point
        per_contradiction_audit.append(
            {
                "id": _contradiction_id(row, idx=idx),
                "concept_pair": [left, right],
                "segment_id": segment_id,
                "lexical_evidence": {
                    "left_concept_hits": left_hits,
                    "right_concept_hits": right_hits,
                    "total_hits": direct_support,
                    "left_family_key": left_family_key,
                    "right_family_key": right_family_key,
                    "left_family_hits": left_family_hits,
                    "right_family_hits": right_family_hits,
                    "left_area_key": left_area_key,
                    "right_area_key": right_area_key,
                    "left_area_hits": left_area_hits,
                    "right_area_hits": right_area_hits,
                },
                "direct_vs_inferred": "direct" if family_both else "inferred",
                "confidence": round(_score_value(row), 6),
                "provenance_class": row.get("triz_class") or "topology_derived",
                "truth_point": {
                    "L": l_value,
                    "S": round(s_pair, 6),
                    "W": round(w_pair, 6),
                    "T": round(truth_point, 6),
                    "corpus_status": [left_support.get("status"), right_support.get("status")],
                },
            }
        )

    seg_entropy = 0.0
    if seg_counts:
        # Shannon entropy over per-segment contradiction distribution.
        total = float(sum(seg_counts.values()))
        for c in seg_counts.values():
            p = float(c) / total if total > 0 else 0.0
            if p > 0:
                import math

                seg_entropy -= p * math.log(p + 1e-15)

    return {
        "session_id": session_id,
        "contradictions_direct_triz": len(direct_rows),
        "contradictions_topology_derived": len(topology_rows),
        "delta_count": len(topology_rows) - len(direct_rows),
        "shared_ids": shared_ids,
        "only_in_direct": only_in_direct,
        "only_in_topology": only_in_topology,
        "canonical_source": CANONICAL_CONTRADICTION_SOURCE,
        "promotion_reason": (
            "Topology-derived contradiction artifacts are canonical for v0.5.9 authority chain; "
            "direct TRIZ remains reconciliation-only."
        ),
        "lexical_support": {
            "lexical_hits_accepted": int(lexical_hits_accepted),
            "canonical_contradiction_count": canonical_count,
            "contradictions_per_accepted_lexical_hit": round(ratio, 6),
            "suspicious_overproduction": bool(canonical_count > lexical_hits_accepted * 5),
            "grounding_granularity": GROUNDING_GRANULARITY,
            "zero_lexical_evidence_share": round(float(zero_lex_count) / float(max(canonical_count, 1)), 6),
            "inferred_share": round(float(inferred_count) / float(max(canonical_count, 1)), 6),
            "zero_lexical_evidence_share_concept": round(
                float(zero_concept_count) / float(max(canonical_count, 1)), 6
            ),
            "inferred_share_concept": round(
                float(inferred_concept_count) / float(max(canonical_count, 1)), 6
            ),
            "truth_point_accumulation": round(truth_sum / float(max(canonical_count, 1)), 6),
            "zero_area_lexical_evidence_share": round(
                float(zero_area_count) / float(max(canonical_count, 1)), 6
            ),
            "segment_entropy": round(seg_entropy, 6),
        },
        "per_contradiction_audit": per_contradiction_audit,
    }


def _filter_canonical_contradictions_for_activation(
    rows: list[dict[str, Any]],
    *,
    lexical_concept_counts: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Produce a conservative contradiction set for activation.

    Prefer family-grounded rows (same grain as coactivation), then score threshold, then cap.
    """
    family_hits, _ = _aggregate_structural_hits(lexical_concept_counts)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for row in rows:
        left, right = _concept_pair(row)
        family_both = _pair_family_grounded(left, right, family_hits)
        score = _score_value(row)
        if family_both or score >= MIN_CANONICAL_CONTRADICTION_SCORE:
            kept.append(row)
        else:
            dropped.append(row)

    # Prefer higher-confidence rows when capping.
    kept.sort(key=lambda r: -_score_value(r))
    capped = kept[:MAX_CANONICAL_CONTRADICTIONS_FOR_ACTIVATION]
    dropped_extra = kept[MAX_CANONICAL_CONTRADICTIONS_FOR_ACTIVATION :]
    dropped.extend(dropped_extra)

    stats = {
        "min_score": MIN_CANONICAL_CONTRADICTION_SCORE,
        "cap": MAX_CANONICAL_CONTRADICTIONS_FOR_ACTIVATION,
        "input_count": len(rows),
        "kept_count": len(capped),
        "dropped_count": len(dropped),
        "dropped_low_signal": sum(
            1
            for r in dropped
            if _score_value(r) < MIN_CANONICAL_CONTRADICTION_SCORE
            and not _pair_family_grounded(*_concept_pair(r), family_hits)
        ),
        "dropped_by_cap": len(dropped_extra),
    }
    return capped, stats


def _load_contradictions(bundle_dir: Path, session_id: str) -> tuple[list[dict[str, Any]], str]:
    rows_12 = _extract_contradictions_from_12(bundle_dir, session_id)
    return rows_12, CANONICAL_CONTRADICTION_SOURCE


def _contradiction_rows_from_triz_session(triz_row: dict[str, Any] | None) -> list[dict[str, Any]]:
    """In-memory TRIZ session row (same shape as ``08_triz_complete.json`` session entries)."""
    if not triz_row or triz_row.get("_error"):
        return []
    tc = triz_row.get("triz_complete")
    if not isinstance(tc, dict):
        return []
    inner = tc.get("triz_complete")
    if isinstance(inner, dict) and isinstance(inner.get("contradictions"), list):
        return [x for x in inner["contradictions"] if isinstance(x, dict)]
    if isinstance(tc.get("contradictions"), list):
        return [x for x in tc["contradictions"] if isinstance(x, dict)]
    return []


def _build_activation_with_bundle_contradictions(
    *,
    session_id: str,
    text: str,
    bundle_dir: Path,
    embedding: dict[str, Any] | None,
    lexical_concept_counts: dict[str, int] | None = None,
    contradiction_calibration: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from hesperia.nlp.session_parser import analyze_session

    contradictions, source = _load_contradictions(bundle_dir, session_id)
    filter_stats: dict[str, Any] | None = None
    if lexical_concept_counts is not None and contradictions:
        contradictions, filter_stats = _filter_canonical_contradictions_for_activation(
            contradictions,
            lexical_concept_counts=lexical_concept_counts,
        )
    activation = analyze_session(
        text,
        embedding=embedding or None,
        contradictions=contradictions if contradictions else None,
        contradiction_calibration=contradiction_calibration,
    )
    used = int((activation.get("contradiction_count_used") or 0))
    coupling_active = bool(activation.get("contradiction_coupling_active"))
    row = {
        "session_id": session_id,
        "contradiction_pipeline": {
            "source": source,
            "count": len(contradictions),
            "used_in_activation": bool(coupling_active and used > 0),
        },
        "contradiction_filter": filter_stats,
        "activation": activation,
    }
    trace = {
        "session_id": session_id,
        "source": source,
        "count": len(contradictions),
        "used_in_activation": bool(coupling_active and used > 0),
        "contradiction_count_used": used,
    }
    return row, trace


def load_sessions(path: Path) -> list[tuple[str, str]]:
    suf = path.suffix.lower()
    if suf == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        sessions = data.get("sessions")
        if not isinstance(sessions, list):
            raise ValueError("JSON must be an object with key 'sessions': [...]")
        out: list[tuple[str, str]] = []
        for i, s in enumerate(sessions):
            if not isinstance(s, dict):
                continue
            sid = str(s.get("session_id") or f"session_{i}")
            text = str(s.get("text") or "")
            out.append((sid, text))
        return out
    text = path.read_text(encoding="utf-8")
    sid = path.stem or "document"
    return [(sid, text)]


def _maybe_speaker_aware(text: str, embedding: dict[str, Any] | None) -> dict[str, Any] | None:
    from hesperia.nlp.transcript_speaker_labels import transcript_has_both_clinical_speakers

    if not transcript_has_both_clinical_speakers(text):
        return None
    try:
        from research.clinical_tfp.stage_detection import detect_tfp_stage
        from hesperia.nlp.session_parser import analyze_session_speaker_aware

        sa = analyze_session_speaker_aware(text, embedding=embedding or None)
        areas_sa = sa.get("areas") or {}
        return {
            "tfp_stage": detect_tfp_stage({k: float(v) for k, v in areas_sa.items() if v is not None}),
            "areas_top": dict(sorted(areas_sa.items(), key=lambda x: -float(x[1] or 0))[:8]),
            "has_speaker_activation": "speaker_activation" in sa,
            "activation_path_id": ((sa.get("invariant_activation") or {}).get("path_id")),
        }
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def run_pipeline(
    *,
    sessions: list[tuple[str, str]],
    out_dir: Path,
    with_kme: bool,
    with_triz: bool,
    with_topology: bool,
    with_r1_r4: bool,
    skip_structural: bool,
    skip_stages: bool,
    skip_hex: bool,
    skip_dlcr: bool,
    skip_sealed: bool,
    skip_analyze: bool,
    dlcr_mode: str,
    skip_triz_activation: bool = False,
    topology_run_params: dict[str, Any] | None = None,
    contradiction_calibration_path: Path | None = None,
) -> dict[str, Any]:
    from core.engine.lexical_concept.pipeline import run_dlcr_pipeline
    from research.hex_outputs_e2e import hex_microstructure_bundle_for_text
    from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack
    from hesperia.nlp.session_parser import analyze_session
    from research.clinical_tfp.stage_detection import TFP_STAGES, detect_tfp_stage
    from runtime.pipeline.analyze import analyze
    from runtime.services.analysis_service import run_structural_analysis_batch

    from core.engine.output_anomalies import (
        aggregate_file_envelope,
        apply_envelopes_standalone_sealed_analyze,
        apply_session_envelopes,
        default_operational_envelope,
    )
    from hesperia.engine.tfp_signal_calibration import load_tfp_runtime_bundle
    from hesperia.extensions.triz.topology_activation_pipeline import triz_activation_bundle_filename
    from hesperia.ontology.dictA.loader import CONFIDENCE_TYPE_MULTIPLIER
    from research.clinical_tfp.session_topology import (
        AREA_CURVE_MAP,
        CURVE_CALIBRATION_REFERENCE,
        DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS,
        run_session_topology,
        compute_areas_working,
    )
    from research.clinical_tfp.interpretation import get_dominant_area
    from research.clinical_tfp.pole_cascade import build_pole_cascade
    from hesperia.extensions.triz.contradiction_calibration import (
        build_calibration_snapshot,
        build_calibration_usage_trace,
        default_calibration_path,
        get_default_contradiction_calibration,
        load_contradiction_calibration,
    )

    tfp_runtime = load_tfp_runtime_bundle()
    tfp_calibration = dict(tfp_runtime["calibration"])
    tfp_inhibition = dict(tfp_runtime["inhibition_matrix"])
    topo_params: dict[str, Any] = dict(DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS)
    if topology_run_params:
        topo_params.update(topology_run_params)

    assets = _REPO / "assets" / "lexicon" / "curated"
    texts = [t for _, t in sessions]
    sids = [sid for sid, t in sessions]

    written: dict[str, str] = {}
    errors: list[str] = []

    contradiction_calibration_resolved_path: str | None = None
    try:
        if contradiction_calibration_path is not None:
            pcal = Path(contradiction_calibration_path).resolve()
            contradiction_calibration = load_contradiction_calibration(pcal)
            contradiction_calibration_resolved_path = str(pcal)
        else:
            dp = default_calibration_path()
            if dp.is_file():
                contradiction_calibration = load_contradiction_calibration(dp)
                contradiction_calibration_resolved_path = str(dp)
            else:
                contradiction_calibration = get_default_contradiction_calibration()
    except (OSError, ValueError, TypeError) as exc:
        contradiction_calibration = get_default_contradiction_calibration()
        errors.append(f"contradiction_calibration_load:{exc}")
    triz_activation_paths: dict[str, dict[str, str]] = {}
    triz_activation_critical = False

    try:
        from sphere.topology.family_embedding import load_family_embedding_tfp

        embedding = load_family_embedding_tfp()
    except Exception:
        embedding = {}

    # 1 Structural batch (all sessions in one call)
    structural_batch: list[dict[str, Any]] = []
    if not skip_structural:
        try:
            batch = run_structural_analysis_batch(texts, assets_root=assets, attach_version=False)
            for i, row in enumerate(batch):
                sid = sids[i] if i < len(sids) else f"batch_{i}"
                one = dict(row)
                one["session_id"] = sid
                structural_batch.append(one)
        except Exception as e:  # noqa: BLE001
            structural_batch = [{"_error": str(e), "session_id": "_batch"}]
            errors.append(f"structural_batch: {e}")
        p = out_dir / "01_structural_batch.json"
        envs01 = [r.get("operational_envelope") or default_operational_envelope() for r in structural_batch]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_structural",
                "session_count": len(sessions),
                "structural_batch": structural_batch,
                "operational_envelope": aggregate_file_envelope(envs01),
            },
        )
        written["01_structural_batch.json"] = str(p)

    # Per-session bundles
    session_tfp_stages: list[dict[str, Any]] = []
    session_hex: list[dict[str, Any]] = []
    session_dlcr: list[dict[str, Any]] = []
    session_sealed: list[dict[str, Any]] = []
    session_analyze: list[dict[str, Any]] = []
    session_speaker_aware: list[dict[str, Any]] = []
    session_kme: list[dict[str, Any]] = []
    session_triz: list[dict[str, Any]] = []
    session_topo: list[dict[str, Any]] = []
    session_main_engine_full_context: list[dict[str, Any]] = []
    contradiction_pipeline_rows: list[dict[str, Any]] = []
    crossplane_by_session: dict[str, dict[str, Any]] = {}
    contradiction_reconciliation_rows: list[dict[str, Any]] = []
    lexical_support_by_session: dict[str, dict[str, Any]] = {}

    for sid, t in zip(sids, texts):
        t = (t or "").strip()
        if not t:
            continue

        if not skip_stages:
            try:
                act = analyze_session(t, embedding=embedding or None)
                areas = act.get("areas") or {}
                stage = detect_tfp_stage({k: float(v) for k, v in areas.items() if v is not None})
                session_tfp_stages.append(
                    {
                        "session_id": sid,
                        "tfp_stage": stage,
                        "areas_top": dict(sorted(areas.items(), key=lambda x: -float(x[1] or 0))[:8]),
                        "areas_raw": act.get("areas_raw") or {},
                        "areas_inhibited": act.get("areas_inhibited") or {},
                        "areas_final": act.get("areas_final") or areas,
                        "activation_path_id": (act.get("invariant_activation") or {}).get("path_id"),
                        "config_version": (act.get("invariant_activation") or {}).get("config_version"),
                        "hex_feedback_active": (act.get("invariant_activation") or {}).get(
                            "hex_feedback_active"
                        ),
                    }
                )
            except Exception as ex:  # noqa: BLE001
                session_tfp_stages.append({"session_id": sid, "_error": str(ex)})

        saw = _maybe_speaker_aware(t, embedding)
        if saw is not None:
            session_speaker_aware.append({"session_id": sid, **saw})

        if not skip_hex:
            try:
                session_hex.append(
                    {"session_id": sid, **hex_microstructure_bundle_for_text(t, assets, list_cap=56)}
                )
            except Exception as ex:  # noqa: BLE001
                session_hex.append({"session_id": sid, "_error": str(ex)})

        triz_row_for_sid: dict[str, Any] | None = None
        if with_triz:
            try:
                from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph
                from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
                from runtime.pipeline.run_e2e_all import _activation_topology_maps, _slim_csv_exports

                act_triz = analyze_session(t, embedding=embedding or None)
                ag = build_clinical_active_graph(act_triz)
                payload = {
                    "nodes": {cid: {"hitCount": n.hit_count} for cid, n in sorted(ag.nodes.items())},
                    "edges": [
                        {
                            "source": e.source_concept_id,
                            "target": e.target_concept_id,
                            "type": e.relation_type or "",
                        }
                        for e in sorted(
                            ag.edges,
                            key=lambda x: (x.source_concept_id, x.target_concept_id, x.relation_type or ""),
                        )
                    ],
                }
                topo_maps = _activation_topology_maps(act_triz, set(ag.nodes.keys()))
                ag2 = active_graph_from_payload(payload)
                content = run_triz_analysis_complete(
                    ag2,
                    topo_maps,
                    narrative_id=sid,
                    run_id=None,
                    topology_mode=True,
                )
                _slim_csv_exports(content)
                from core.projection import apply_public_projection

                triz_row_for_sid = apply_public_projection(
                    _round_floats({"session_id": sid, "input": _text_preview(t), "triz_complete": content})
                )
                session_triz.append(triz_row_for_sid)
            except Exception as ex:  # noqa: BLE001
                triz_row_for_sid = {"session_id": sid, "_error": str(ex)}
                session_triz.append(triz_row_for_sid)

        contra_rows: list[dict[str, Any]] = []
        if with_triz:
            contra_rows = _contradiction_rows_from_triz_session(triz_row_for_sid)
        if not contra_rows:
            disk_rows, _src = _load_contradictions(out_dir, sid)
            contra_rows = disk_rows

        try:
            act_plain = analyze_session(t, embedding=embedding or None, contradictions=None)
        except Exception as ex:  # noqa: BLE001
            act_plain = {"_error": str(ex), "concepts": {}}

        dlcr_body: dict[str, Any] | None = None
        if not skip_dlcr:
            try:
                dlcr_body = run_dlcr_pipeline(
                    t,
                    repo_root=_REPO,
                    mode=dlcr_mode,
                    contradiction_package=None,
                )
            except Exception as ex:  # noqa: BLE001
                dlcr_body = {"_error": str(ex)}

        lexical_neg_summary: dict[str, Any] | None = None
        if isinstance(dlcr_body, dict) and not dlcr_body.get("_error"):
            neg_raw = dlcr_body.get("negation_summary")
            lexical_neg_summary = dict(neg_raw) if isinstance(neg_raw, dict) else None

        from hesperia.extensions.triz.contradiction_uncertainty import build_uncertainty_package
        from hesperia.extensions.triz.contradiction_coupling import enrich_contradiction_rows

        unc = build_uncertainty_package(dlcr_body if isinstance(dlcr_body, dict) else {}, act_plain)
        concepts_plain = act_plain.get("concepts") if isinstance(act_plain, dict) else {}
        stab_plain = act_plain.get("concept_weights_stabilized") if isinstance(act_plain, dict) else None
        hex_plain = act_plain.get("hex_feedback_delta") if isinstance(act_plain, dict) else None
        ce = enrich_contradiction_rows(
            contra_rows,
            unc,
            concepts_plain if isinstance(concepts_plain, dict) else {},
            concept_weights_stabilized=stab_plain if isinstance(stab_plain, dict) else None,
            hex_feedback_delta=hex_plain if isinstance(hex_plain, dict) else None,
            lexical_negation_summary=lexical_neg_summary,
            contradiction_calibration=contradiction_calibration,
        )

        if with_topology:
            try:
                full = run_session_topology(
                    t,
                    contradictions=ce if ce else None,
                    contradiction_calibration=contradiction_calibration,
                    **topo_params,
                )
                segs = full.get("segments") or []
                if len(segs) > 12:
                    full = {
                        **full,
                        "segments": segs[:12],
                        "_segments_truncated": True,
                        "_segments_total": len(segs),
                    }
                # CHI-003-02: dual signal per CHI-003-01 verdict — areas_final (cumulative,
                # unchanged) stays the calibration-audit figure; areas_working (segment-weighted,
                # opening contract/frame window down-weighted) is the product "dominant area".
                areas_final_here = (
                    act_plain.get("areas_final") if isinstance(act_plain, dict) else None
                ) or {}
                areas_working = compute_areas_working(full.get("segments") or [])
                # TFP-POLES-01: pole_cascade audit — seed/hop-1/hop-2/tension for A11/A12,
                # from the pre-/post-inhibition vectors (act_plain), not areas_final/working
                # (those are cumulative/segment-weighted, not the raw inhibition seed).
                areas_raw_here = (
                    act_plain.get("areas_raw") if isinstance(act_plain, dict) else None
                ) or {}
                areas_inhibited_here = (
                    act_plain.get("areas_inhibited") if isinstance(act_plain, dict) else None
                ) or {}
                full = {
                    **full,
                    "areas_final": areas_final_here,
                    "areas_final_dominant": get_dominant_area(areas_final_here) or None,
                    "areas_working": areas_working,
                    "areas_working_dominant": get_dominant_area(areas_working) or None,
                    "pole_cascade": build_pole_cascade(areas_raw_here, areas_inhibited_here),
                }
                session_topo.append({"session_id": sid, "session_topology": full})
            except Exception as ex:  # noqa: BLE001
                session_topo.append({"session_id": sid, "_error": str(ex)})

        contradiction_package: dict[str, Any] | None = None
        try:
            from hesperia.extensions.triz.crossplane_contradiction import build_crossplane_contradiction_package

            act_for_pkg = analyze_session(
                t,
                embedding=embedding or None,
                contradictions=ce if ce else None,
                uncertainty_package=unc,
                lexical_negation_summary=lexical_neg_summary,
                contradiction_calibration=contradiction_calibration,
            )
            topo_full: dict[str, Any] = {}
            for tp in session_topo:
                if str(tp.get("session_id")) == str(sid) and not tp.get("_error"):
                    topo_full = tp.get("session_topology") or {}
                    break
            contradiction_package = build_crossplane_contradiction_package(
                activation=act_for_pkg,
                topology=topo_full,
                contradictions=ce if ce else None,
                uncertainty_package=unc,
                contradiction_calibration=contradiction_calibration,
            )
            crossplane_by_session[str(sid)] = _round_floats(dict(contradiction_package))
        except Exception as ex:  # noqa: BLE001
            contradiction_package = None
            crossplane_by_session[str(sid)] = {"_error": str(ex)}

        if not skip_dlcr:
            try:
                from core.engine.lexical_concept.pipeline import apply_crossplane_contradiction_fields_to_dlcr_result

                if dlcr_body is not None and not dlcr_body.get("_error"):
                    body = dict(dlcr_body)
                    body = apply_crossplane_contradiction_fields_to_dlcr_result(body, contradiction_package)
                    body["run"] = "tfp_file_pipeline_dlcr"
                    body["session_id"] = sid
                    body["input"] = _text_preview(t)
                    body["uncertainty_package"] = _round_floats(dict(unc))
                    if contradiction_package:
                        body["crossplane_contradiction_package"] = _round_floats(dict(contradiction_package))
                    session_dlcr.append(body)
                else:
                    body = run_dlcr_pipeline(
                        t,
                        repo_root=_REPO,
                        mode=dlcr_mode,
                        contradiction_package=contradiction_package,
                    )
                    body = dict(body)
                    body["run"] = "tfp_file_pipeline_dlcr"
                    body["session_id"] = sid
                    body["input"] = _text_preview(t)
                    body["uncertainty_package"] = _round_floats(dict(unc))
                    if contradiction_package:
                        body["crossplane_contradiction_package"] = _round_floats(dict(contradiction_package))
                    session_dlcr.append(body)
                    lexical_counts: dict[str, int] = {}
                    for span in body.get("span_resolutions") or []:
                        if not isinstance(span, dict):
                            continue
                        cid = str(span.get("winning_concept_id") or "").strip()
                        if cid:
                            lexical_counts[cid] = lexical_counts.get(cid, 0) + 1
                    lexical_support_by_session[str(sid)] = {
                        "lexical_hits_accepted": int(body.get("lexical_hits_accepted") or 0),
                        "concept_counts": lexical_counts,
                    }
            except Exception as ex:  # noqa: BLE001
                session_dlcr.append({"session_id": sid, "_error": str(ex), "input": _text_preview(t)})

        if not skip_sealed:
            try:
                bundle = run_sealed_multiscale_stack(
                    t,
                    assets,
                    use_triz_contradiction=False,
                    contradiction_package=contradiction_package,
                )
                sealed_body = _round_floats(dict(bundle))
                sealed_body["crossplane_contradiction_package"] = (
                    _round_floats(dict(contradiction_package)) if contradiction_package else None
                )
                session_sealed.append(
                    {"session_id": sid, "run": "tfp_file_pipeline_sealed", **sealed_body}
                )
            except Exception as ex:  # noqa: BLE001
                session_sealed.append({"session_id": sid, "_error": str(ex)})

        if not skip_analyze:
            try:
                minimal, extended = analyze(
                    t,
                    r1_r4=with_r1_r4,
                    contradiction_package=contradiction_package,
                )
                analyze_row = {
                    "session_id": sid,
                    "input": _text_preview(t),
                    "result": minimal,
                    "extended": dict(extended),
                }
                if contradiction_package:
                    analyze_row["crossplane_contradiction_package"] = _round_floats(dict(contradiction_package))
                session_analyze.append(analyze_row)
            except Exception as ex:  # noqa: BLE001
                session_analyze.append({"session_id": sid, "_error": str(ex), "input": _text_preview(t)})

        if with_kme:
            try:
                from hesperia.engine.kme.clinical_bridge import run_session_kme_pipeline
                from core.domain.pipeline import metric_report_to_dict
                from core.projection import apply_public_projection
                from hesperia.ontology.dictA import build_marker_to_concepts

                # CHI-002-01: make the single-token marker channel explicit at this call site
                # (verified: session_parser._get_marker_index() already resolves to the same
                # build_marker_to_concepts() when marker_index is left None, so this is a
                # no-behavior-change robustness/clarity pin, not a live-bug fix).
                report = run_session_kme_pipeline(
                    t, source_id=sid, marker_index=build_marker_to_concepts()
                )
                body = apply_public_projection(
                    {"session_id": sid, "input": _text_preview(t), "report": metric_report_to_dict(report)}
                )
                session_kme.append(_round_floats(body))
            except Exception as ex:  # noqa: BLE001
                session_kme.append({"session_id": sid, "_error": str(ex)})

    if with_topology and not skip_triz_activation:
        from hesperia.extensions.triz.topology_activation_pipeline import (
            run_topology_triz_activation,
            triz_activation_pipeline_fail,
        )

        for topo_row in session_topo:
            sid = str(topo_row.get("session_id") or "")
            if topo_row.get("_error"):
                triz_activation_critical = True
                errors.append(f"triz_activation_blocked_bad_topology:{sid}")
                continue
            st_full = topo_row.get("session_topology") or {}
            tc: dict[str, Any] | None = None
            for tr in session_triz:
                if str(tr.get("session_id")) == sid and tr.get("triz_complete") is not None:
                    tc = tr
                    break
            try:
                bundle = run_topology_triz_activation(st_full, triz_complete=tc)
                rel_files: dict[str, str] = {}
                for fn, data in bundle.items():
                    flat = triz_activation_bundle_filename(sid, fn)
                    p = out_dir / flat
                    _write_json(p, data)
                    rel_files[fn] = str(p)
                triz_activation_paths[sid] = rel_files
                audit = bundle["cross_plane_audit.json"]
                if triz_activation_pipeline_fail(audit):
                    triz_activation_critical = True
                    errors.append(f"TRIZ_DEAD_LAYER:{sid}")
            except Exception as ex:  # noqa: BLE001
                triz_activation_critical = True
                errors.append(f"triz_activation_write:{sid}:{ex}")

    if not skip_structural and structural_batch:
        if session_sealed or session_analyze:
            apply_session_envelopes(
                structural_batch=structural_batch,
                session_sealed=session_sealed,
                session_analyze=session_analyze,
            )
    elif session_sealed or session_analyze:
        apply_envelopes_standalone_sealed_analyze(session_sealed, session_analyze)

    if not skip_stages:
        p = out_dir / "02_session_tfp_stages.json"
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_stages",
                "tfp_stages_enum": list(TFP_STAGES),
                "session_tfp_stages": session_tfp_stages,
                "session_speaker_aware": session_speaker_aware,
                "operational_envelope": default_operational_envelope(),
            },
        )
        written["02_session_tfp_stages.json"] = str(p)

    if not skip_hex:
        p = out_dir / "03_hex_microstructure_tfp.json"
        for _hx in session_hex:
            _hx.setdefault("operational_envelope", default_operational_envelope())
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_hex",
                "sessions": session_hex,
                "operational_envelope": default_operational_envelope(),
            },
        )
        written["03_hex_microstructure_tfp.json"] = str(p)

    if not skip_dlcr:
        p = out_dir / "04_dlcr_full.json"
        for _dc in session_dlcr:
            _dc.setdefault("operational_envelope", default_operational_envelope())
        envs04 = [s.get("operational_envelope") or default_operational_envelope() for s in session_dlcr]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_dlcr",
                "sessions": session_dlcr,
                "operational_envelope": aggregate_file_envelope(envs04) if envs04 else default_operational_envelope(),
            },
        )
        written["04_dlcr_full.json"] = str(p)

    if not skip_sealed:
        p = out_dir / "05_sealed_multiscale.json"
        envs05 = [s.get("operational_envelope") or default_operational_envelope() for s in session_sealed]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_sealed",
                "sessions": session_sealed,
                "operational_envelope": aggregate_file_envelope(envs05) if envs05 else default_operational_envelope(),
            },
        )
        written["05_sealed_multiscale.json"] = str(p)

    if not skip_analyze:
        p = out_dir / "06_product_analyze.json"
        envs06 = [s.get("operational_envelope") or default_operational_envelope() for s in session_analyze]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_analyze",
                "with_r1_r4": with_r1_r4,
                "sessions": session_analyze,
                "operational_envelope": aggregate_file_envelope(envs06) if envs06 else default_operational_envelope(),
            },
        )
        written["06_product_analyze.json"] = str(p)

    if with_kme and session_kme:
        p = out_dir / "07_session_kme.json"
        for _km in session_kme:
            _km.setdefault("operational_envelope", default_operational_envelope())
        envs07 = [s.get("operational_envelope") or default_operational_envelope() for s in session_kme]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_kme",
                "sessions": session_kme,
                "operational_envelope": aggregate_file_envelope(envs07) if envs07 else default_operational_envelope(),
            },
        )
        written["07_session_kme.json"] = str(p)

    if with_triz and session_triz:
        p = out_dir / "08_triz_complete.json"
        for _tz in session_triz:
            _tz.setdefault("operational_envelope", default_operational_envelope())
        envs08 = [s.get("operational_envelope") or default_operational_envelope() for s in session_triz]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_triz",
                "sessions": session_triz,
                "operational_envelope": aggregate_file_envelope(envs08) if envs08 else default_operational_envelope(),
            },
        )
        written["08_triz_complete.json"] = str(p)

    if with_topology and session_topo:
        p = out_dir / "09_session_topology.json"
        for _tp in session_topo:
            _tp.setdefault("operational_envelope", default_operational_envelope())
        envs09 = [s.get("operational_envelope") or default_operational_envelope() for s in session_topo]
        _write_json(
            p,
            {
                "run": "tfp_file_pipeline_topology",
                "topology_run_params": dict(topo_params),
                "tfp_signal_calibration_version": str(tfp_calibration.get("version") or "unknown"),
                "area_curve_map": dict(AREA_CURVE_MAP),
                "curve_calibration_reference": dict(CURVE_CALIBRATION_REFERENCE),
                "dict_a_confidence_multiplier": dict(CONFIDENCE_TYPE_MULTIPLIER),
                "sessions": session_topo,
                "operational_envelope": aggregate_file_envelope(envs09) if envs09 else default_operational_envelope(),
            },
        )
        written["09_session_topology.json"] = str(p)

    # Derive lexical grounding stats from DLCR output (source-of-truth).
    for _dc in session_dlcr:
        if not isinstance(_dc, dict) or _dc.get("_error"):
            continue
        sid = str(_dc.get("session_id") or "")
        if not sid:
            continue
        lexical_counts: dict[str, int] = {}
        for span in _dc.get("span_resolutions") or []:
            if not isinstance(span, dict):
                continue
            cid = str(span.get("winning_concept_id") or "").strip()
            if cid:
                lexical_counts[cid] = lexical_counts.get(cid, 0) + 1
        lexical_support_by_session[sid] = {
            "lexical_hits_accepted": int(_dc.get("lexical_hits_accepted") or 0),
            "concept_counts": lexical_counts,
        }

    # Explicit contradiction truth table (v0.5.9 authority-chain reconciliation).
    dict_b_path = resolve_dict_file(_REPO, "dict_b.jsonl")
    for sid in sids:
        direct_rows = _extract_contradictions_from_08(out_dir / "08_triz_complete.json", sid)
        topology_rows = _extract_contradictions_from_12(out_dir, sid)
        lexical = lexical_support_by_session.get(str(sid), {})
        contradiction_reconciliation_rows.append(
            _build_contradiction_reconciliation(
                session_id=str(sid),
                direct_rows=direct_rows,
                topology_rows=topology_rows,
                lexical_hits_accepted=int(lexical.get("lexical_hits_accepted") or 0),
                lexical_concept_counts=dict(lexical.get("concept_counts") or {}),
                dict_b_path=dict_b_path,
            )
        )
    p13 = out_dir / "13_contradiction_reconciliation.json"
    _write_json(
        p13,
        {
            "run": "tfp_file_pipeline_contradiction_reconciliation_v1",
            "canonical_source": CANONICAL_CONTRADICTION_SOURCE,
            "sessions": contradiction_reconciliation_rows,
            "operational_envelope": default_operational_envelope(),
        },
    )
    written["13_contradiction_reconciliation.json"] = str(p13)

    # Main-engine activation pass with contradiction injection from bundle artifacts.
    stage_rows_by_sid = {
        str(row.get("session_id")): row for row in session_tfp_stages if isinstance(row, dict) and row.get("session_id")
    }
    for sid, t in zip(sids, texts):
        t = (t or "").strip()
        if not t:
            continue
        try:
            lexical = lexical_support_by_session.get(str(sid), {})
            lexical_counts = dict(lexical.get("concept_counts") or {})
            row, trace = _build_activation_with_bundle_contradictions(
                session_id=sid,
                text=t,
                bundle_dir=out_dir,
                embedding=embedding or None,
                lexical_concept_counts=lexical_counts,
                contradiction_calibration=contradiction_calibration,
            )
            cp = crossplane_by_session.get(str(sid))
            if cp is not None:
                row["crossplane_contradiction"] = cp
            stage_row = stage_rows_by_sid.get(str(sid)) or {}
            before_areas = dict(stage_row.get("areas_raw") or {})
            after_areas = dict(row.get("activation", {}).get("areas_final") or {})
            hex_delta_map = dict(row.get("activation", {}).get("hex_feedback_delta") or {})
            before_rank = _top_keys(before_areas, 12)
            after_rank = _top_keys(after_areas, 12)
            rank_changes = {
                area: (before_rank.index(area) if area in before_rank else None, after_rank.index(area) if area in after_rank else None)
                for area in sorted(set(before_rank) | set(after_rank))
            }
            top_before = before_rank[0] if before_rank else None
            top_after = after_rank[0] if after_rank else None
            top_before_val = float(before_areas.get(top_before) or 0.0) if top_before else 0.0
            top_after_val = float(after_areas.get(top_after) or 0.0) if top_after else 0.0
            row["invariant_path_effect"] = {
                "areas_before_invariant_path": before_areas,
                "areas_after_invariant_path": after_areas,
                "hex_contribution_delta_l1": round(sum(abs(float(v)) for v in hex_delta_map.values()), 6),
                "rank_changes": rank_changes,
                "top_area_before": top_before,
                "top_area_after": top_after,
                "top_area_change_magnitude": round(abs(top_after_val - top_before_val), 6),
            }
            session_main_engine_full_context.append(row)
            contradiction_pipeline_rows.append(trace)
        except Exception as exc:  # noqa: BLE001
            contradictions, source = _load_contradictions(out_dir, sid)
            session_main_engine_full_context.append(
                {
                    "session_id": sid,
                    "contradiction_pipeline": {
                        "source": source,
                        "count": len(contradictions),
                        "used_in_activation": False,
                    },
                    "_error": str(exc),
                }
            )
            contradiction_pipeline_rows.append(
                {
                    "session_id": sid,
                    "source": source,
                    "count": len(contradictions),
                    "used_in_activation": False,
                    "contradiction_count_used": 0,
                }
            )

    p = out_dir / "20_main_engine_full_context.json"
    from hesperia.extensions.triz.contradiction_contract import (
        CONTRADICTION_CONTRACT_SPEC_VERSION,
        validate_contradiction_contract,
    )

    feedback_sessions = 0
    risky_concepts_sessions = 0
    for _sid, cp in crossplane_by_session.items():
        if not isinstance(cp, dict):
            continue
        if cp.get("feedback_summary"):
            feedback_sessions += 1
        if cp.get("top_risky_concepts"):
            risky_concepts_sessions += 1

    body20 = {
        "run": "tfp_file_pipeline_main_engine_full_context",
        "sessions": session_main_engine_full_context,
        "contradiction_pipeline": contradiction_pipeline_rows,
        "canonical_contradiction_source": CANONICAL_CONTRADICTION_SOURCE,
        "contradiction_reconciliation_artifact": "13_contradiction_reconciliation.json",
        "crossplane_contradiction_by_session": crossplane_by_session,
        "feedback_summary": {
            "sessions_with_feedback_summary": feedback_sessions,
            "sessions_with_top_risky_concepts": risky_concepts_sessions,
        },
        "activation_topology_linkage_summary": {
            "sessions_total": len(session_main_engine_full_context),
            "sessions_with_crossplane_package": sum(
                1 for _sid, cp in crossplane_by_session.items() if isinstance(cp, dict) and not cp.get("_error")
            ),
        },
        "conflict_release_summary": {
            "status": "pending_inspection",
            "inspection_artifact": "99_tfp_bundle_inspect.json",
        },
        "contradiction_calibration_snapshot": build_calibration_snapshot(
            contradiction_calibration,
            source_path=contradiction_calibration_resolved_path
            or "assets/data/engine_dynamics_v060/tfp/contradiction_calibration_v1.json",
        ),
        "contradiction_calibration_usage": build_calibration_usage_trace(contradiction_calibration),
        "operational_envelope": default_operational_envelope(),
    }
    pre_contract = validate_contradiction_contract(
        {
            "04_dlcr_full.json": {"sessions": session_dlcr} if session_dlcr else None,
            "05_sealed_multiscale.json": {"sessions": session_sealed} if session_sealed else None,
            "06_product_analyze.json": {"sessions": session_analyze} if session_analyze else None,
            "09_session_topology.json": {"sessions": session_topo} if session_topo else None,
            "20_main_engine_full_context.json": body20,
        }
    )
    contract_summary = {
        "spec_version": CONTRADICTION_CONTRACT_SPEC_VERSION,
        "contract_valid": bool(pre_contract.get("contract_valid")),
        "missing_required_fields": list(pre_contract.get("missing_required_fields") or []),
        "deprecated_fields_found": list(pre_contract.get("deprecated_fields_found") or []),
        "authority_conflicts": list(pre_contract.get("authority_conflicts") or []),
    }
    body20["contradiction_contract"] = contract_summary
    _write_json(
        p,
        body20,
    )
    written["20_main_engine_full_context.json"] = str(p)

    manifest_parts: list[dict[str, Any]] = []
    if not skip_structural and structural_batch:
        manifest_parts.extend(
            [r.get("operational_envelope") or default_operational_envelope() for r in structural_batch]
        )
    if session_sealed:
        manifest_parts.extend(
            [s.get("operational_envelope") or default_operational_envelope() for s in session_sealed]
        )
    if session_analyze:
        manifest_parts.extend(
            [s.get("operational_envelope") or default_operational_envelope() for s in session_analyze]
        )
    manifest_operational_envelope = (
        aggregate_file_envelope(manifest_parts) if manifest_parts else default_operational_envelope()
    )

    manifest = {
        "run": "tfp_file_pipeline_manifest",
        "run_id": os.environ.get("HESPERIA_TFP_PIPELINE_RUN_ID") or str(uuid.uuid4()),
        "repo_root": str(_REPO),
        "session_ids": sids,
        "non_empty_sessions": sum(1 for _, t in sessions if (t or "").strip()),
        "tfp_signal_calibration": {
            "config_version": str(tfp_calibration.get("version") or "unknown"),
            "invariant_path_id": str(tfp_calibration.get("invariant_path_id") or "unknown"),
            "session_topology_run_params": dict(topo_params),
            "loaded_config": tfp_calibration,
            "area_curve_map": dict(AREA_CURVE_MAP),
            "curve_calibration_reference": dict(CURVE_CALIBRATION_REFERENCE),
            "dict_a_confidence_multiplier": dict(CONFIDENCE_TYPE_MULTIPLIER),
            "inhibition_matrix": {
                "version": tfp_inhibition.get("version"),
                "date": tfp_inhibition.get("date"),
                "area_ids": tfp_inhibition.get("area_ids"),
                "intended_range": tfp_inhibition.get("intended_range"),
            },
            "notes": (
                "Invariant TFP path: stabilized concepts -> hex feedback -> area inhibition -> softmax. "
                "session_topology_run_params control segmentation and topology metadata only; "
                "per-session curve_projection_meta and stage rows expose authoritative diagnostic vectors."
            ),
        },
        "flags": {
            "with_kme": with_kme,
            "with_triz": with_triz,
            "with_topology": with_topology,
            "with_r1_r4": with_r1_r4,
            "skip_structural": skip_structural,
            "skip_stages": skip_stages,
            "skip_hex": skip_hex,
            "skip_dlcr": skip_dlcr,
            "skip_sealed": skip_sealed,
            "skip_analyze": skip_analyze,
            "skip_triz_activation": skip_triz_activation,
            "dlcr_mode": dlcr_mode,
            "HESPERIA_DLCR_DOMAIN_PACK": os.environ.get("HESPERIA_DLCR_DOMAIN_PACK"),
            "HESPERIA_ANALYZE_DLCR_EVIDENCE": os.environ.get("HESPERIA_ANALYZE_DLCR_EVIDENCE"),
        },
        "artifacts": written,
        "canonical_contradiction_source": CANONICAL_CONTRADICTION_SOURCE,
        "contradiction_pipeline": contradiction_pipeline_rows,
        "contradiction_reconciliation": {
            "artifact": "13_contradiction_reconciliation.json",
            "canonical_source": CANONICAL_CONTRADICTION_SOURCE,
        },
        "crossplane_contradiction_by_session": crossplane_by_session,
        "contradiction_contract": {
            "spec_version": CONTRADICTION_CONTRACT_SPEC_VERSION,
            "contract_valid": contract_summary["contract_valid"],
            "authoritative_artifact": "20_main_engine_full_context.json",
            "inspection_artifact": "99_tfp_bundle_inspect.json",
            "missing_required_fields": contract_summary["missing_required_fields"],
            "deprecated_fields_found": contract_summary["deprecated_fields_found"],
            "authority_conflicts": contract_summary["authority_conflicts"],
        },
        "contradiction_calibration_snapshot": build_calibration_snapshot(
            contradiction_calibration,
            source_path=contradiction_calibration_resolved_path
            or "assets/data/engine_dynamics_v060/tfp/contradiction_calibration_v1.json",
        ),
        "triz_activation": triz_activation_paths,
        "errors": errors,
        "operational_envelope": manifest_operational_envelope,
        "scope_note": (
            "TFP testing / research bundle — not the sealed v0.5.1 product proof. "
            "Planes: A=structural batch, B=session_parser+TFP stage, C=DLCR JSONL v0.6.0, "
            "plus sealed multiscale and analyze()."
        ),
    }
    mp = out_dir / "00_manifest.json"
    _write_json(mp, manifest)
    written_out = dict(written)
    written_out["00_manifest.json"] = str(mp)
    for _sid, sid_paths in triz_activation_paths.items():
        for _fn, pth in sid_paths.items():
            written_out[triz_activation_bundle_filename(_sid, _fn)] = pth
    return {
        "manifest": manifest,
        "paths": written_out,
        "triz_activation_critical": triz_activation_critical,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="TFP file pipeline: input .json sessions or plain text → multi-artifact output directory."
    )
    ap.add_argument("--input", "-i", type=Path, required=True, help="Input .json (sessions[]) or text/markdown file")
    ap.add_argument(
        "--out-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: outputs/tfp/runs/tfp_pipeline_run/<run_id>)",
    )
    ap.add_argument("--with-kme", action="store_true", help="Include KME clinical report per session (07_…)")
    ap.add_argument("--with-triz", action="store_true", help="Include TRIZ complete per session (08_…)")
    ap.add_argument(
        "--with-topology",
        action="store_true",
        help="Include clinical session topology (09_…) and flat 12_<session>_*.json triz_activation artifacts (unless --skip-triz-activation)",
    )
    ap.add_argument(
        "--skip-triz-activation",
        action="store_true",
        help="With --with-topology: do not write 12_* triz_activation files or enforce TRIZ-from-topology gate",
    )
    ap.add_argument("--with-r1-r4", action="store_true", help="Pass r1_r4=True into analyze()")
    ap.add_argument(
        "--dlcr-mode",
        default="clinical_speech",
        help="Mode for run_dlcr_pipeline (default: clinical_speech)",
    )
    ap.add_argument("--skip-structural", action="store_true")
    ap.add_argument("--skip-stages", action="store_true")
    ap.add_argument("--skip-hex", action="store_true")
    ap.add_argument("--skip-dlcr", action="store_true")
    ap.add_argument("--skip-sealed", action="store_true")
    ap.add_argument("--skip-analyze", action="store_true")
    ap.add_argument(
        "--no-dlcr-domain-pack",
        action="store_true",
        help="Do not force HESPERIA_DLCR_DOMAIN_PACK=tfp (leave env as-is)",
    )
    ap.add_argument(
        "--topology-params-json",
        type=Path,
        default=None,
        help="Optional JSON object merged over DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS for run_session_topology",
    )
    ap.add_argument(
        "--contradiction-calibration-json",
        type=Path,
        default=None,
        help="Optional contradiction calibration profile JSON (default: assets/.../contradiction_calibration_v1.json)",
    )
    args = ap.parse_args()

    if args.with_topology and not args.with_triz:
        print(
            "WARNING: --with-topology without --with-triz uses a coarse synthetic "
            "family-cluster fallback (synthetic_clusters_from_coactivation_edges), not real "
            "TRIZ innovation_clusters. This can trip family_weights_sparsify's uniformity "
            "gate (errors: ['triz_activation_write:...uniformity:...']) on real fixtures — "
            "that's the fallback's coarse clustering, not a calibration regression. Pass "
            "--with-triz too if you want the real cluster source. "
            "See docs/foundations/parameter_synergies.md §7.",
            file=sys.stderr,
        )

    inp = args.input.resolve()
    if not inp.is_file():
        print(f"ERROR: input not a file: {inp}", file=sys.stderr)
        return 2

    if not args.no_dlcr_domain_pack:
        os.environ["HESPERIA_DLCR_DOMAIN_PACK"] = "tfp"

    # CHI-002-01: batch KME never called apply_analyze_profile_defaults(profile="tfp") like
    # live /analyze does, so area_math_grain silently resolved to the core default (12) instead
    # of TFP's own 10-area ontology. setdefault only — explicit HESPERIA_AREA_MATH_GRAIN still wins.
    os.environ.setdefault("HESPERIA_AREA_MATH_GRAIN", "10")

    try:
        sessions = load_sessions(inp)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: load_sessions: {e}", file=sys.stderr)
        return 2

    if not sessions:
        print("ERROR: no sessions loaded", file=sys.stderr)
        return 2

    topology_run_params: dict[str, Any] | None = None
    if args.topology_params_json is not None:
        tp = args.topology_params_json.resolve()
        if not tp.is_file():
            print(f"ERROR: --topology-params-json not a file: {tp}", file=sys.stderr)
            return 2
        try:
            topology_run_params = json.loads(tp.read_text(encoding="utf-8"))
            if not isinstance(topology_run_params, dict):
                print("ERROR: topology JSON must be an object", file=sys.stderr)
                return 2
        except json.JSONDecodeError as e:
            print(f"ERROR: topology JSON: {e}", file=sys.stderr)
            return 2

    run_id = str(uuid.uuid4())
    os.environ["HESPERIA_TFP_PIPELINE_RUN_ID"] = run_id
    out_dir = args.out_dir
    if out_dir is None:
        out_dir = _REPO / "outputs" / "tfp" / "runs" / "tfp_pipeline_run" / run_id
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = run_pipeline(
        sessions=sessions,
        out_dir=out_dir,
        with_kme=args.with_kme,
        with_triz=args.with_triz,
        with_topology=args.with_topology,
        with_r1_r4=args.with_r1_r4,
        skip_structural=args.skip_structural,
        skip_stages=args.skip_stages,
        skip_hex=args.skip_hex,
        skip_dlcr=args.skip_dlcr,
        skip_sealed=args.skip_sealed,
        skip_analyze=args.skip_analyze,
        dlcr_mode=args.dlcr_mode,
        skip_triz_activation=args.skip_triz_activation,
        topology_run_params=topology_run_params,
        contradiction_calibration_path=args.contradiction_calibration_json,
    )

    print(f"tfp_file_pipeline_ok wrote {len(summary['paths'])} files under {out_dir}", file=sys.stderr)
    for name in sorted(summary["paths"]):
        print(summary["paths"][name], file=sys.stderr)
    if summary.get("triz_activation_critical"):
        print("ERROR: triz_activation gate failed (see manifest errors)", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
