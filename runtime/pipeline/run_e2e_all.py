#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
E2E: single session run — runtime sphere stack + Hesperia engine (KME, TRIZ, clinical session).

Engine Dynamics v0.5 (docs/HESPERIA_v0_5_ENGINE_DYNAMICS.md):
  Canonical release proof: steps 1–9, 10b–10c, 11–11d (+ optional field_dynamics). TFP smoke (step 10) =
  Kernberg testing collateral — runs for CI parity, not the generic v0.5 product definition.

Writes ~19 JSON (+ optional field_dynamics; + optional DLCR when ``HESPERIA_E2E_DLCR=1``): sealed multiscale, hex microstructure, semantic field, HCI, …
Order: docs/E2E_RUN_ORDER.md. Swampy: sphere vs core.layers dual paths — refactor target.
Usage: python3 -m runtime.pipeline.run_e2e_all [--out-dir path]
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_HESPERIA = _HERE.parents[1]
if str(_HESPERIA) not in sys.path:
    sys.path.insert(0, str(_HESPERIA))

# Canonical e2e artifact directory
DEFAULT_E2E_DIR = _HESPERIA / "assets" / "artifacts" / "e2e"

# Planned output basenames (all under out_dir)
# Order matches run_all() — see docs/E2E_RUN_ORDER.md
E2E_OUTPUTS = (
    "run_output_e2e_sentence.json",
    "run_output_e2e_l1_l9.json",
    "run_output_e2e_r1_r4.json",
    "run_output_e2e_sphere_math_values.json",
    "run_output_e2e_sphere_math_100.json",
    "run_output_e2e_calibration_100_structural.json",
    "run_output_e2e_calibration_100_summary.json",
    "run_output_e2e_domain_metrics.json",
    "run_output_e2e_session_kme.json",
    "run_output_e2e_triz_complete.json",
    "run_output_e2e_session_topology.json",
    "run_output_e2e_tfp_smoke.json",
    "run_output_e2e_hex_microstructure_tfp.json",
    "run_output_e2e_sealed_multiscale.json",
    "run_output_e2e_capability_matrix.json",
    "run_output_e2e_semantic_field.json",
    "run_output_e2e_field_calibration.json",
    "run_output_e2e_field_calibration_best.json",
    "run_output_e2e_field_calibration_topk.json",
)
# Optional artifact when HESPERIA_FIELD_DYNAMICS=1
E2E_OUTPUT_FIELD_DYNAMICS = "run_output_e2e_field_dynamics.json"
# Optional DLCR pipeline artifact when HESPERIA_E2E_DLCR=1
E2E_OUTPUT_DLCR = "run_output_e2e_dlcr.json"
# Full manifest when dynamics flag is set (19 base + field_dynamics)
E2E_OUTPUTS_WITH_FIELD_DYNAMICS = E2E_OUTPUTS + (E2E_OUTPUT_FIELD_DYNAMICS,)
# Optional 21st artifact when HESPERIA_E2E_DLCR=1 (independent of field dynamics)
E2E_OUTPUTS_WITH_FIELD_DYNAMICS_AND_DLCR = E2E_OUTPUTS_WITH_FIELD_DYNAMICS + (E2E_OUTPUT_DLCR,)


def _ensure_e2e_run_id() -> str:
    rid = os.environ.get("HESPERIA_E2E_RUN_ID", "").strip()
    if not rid:
        rid = str(uuid.uuid4())
        os.environ["HESPERIA_E2E_RUN_ID"] = rid
    return rid


def _finalize_e2e_payload(data: dict[str, Any], modules_used: list[str]) -> dict[str, Any]:
    from hesperia.system.version import attach_public_output_metadata, default_calibration_profile, e2e_pipeline_version

    rid = os.environ.get("HESPERIA_E2E_RUN_ID", "").strip() or None
    return attach_public_output_metadata(
        data,
        calibration_profile=default_calibration_profile(),
        pipeline_version=e2e_pipeline_version(),
        execution_flow_version=e2e_pipeline_version(),
        orchestration_mode="E2E_BATCH",
        run_id=rid,
        modules_used=modules_used,
    )


def _write_e2e_json(path: Path, data: dict[str, Any], modules_used: list[str]) -> None:
    merged = _finalize_e2e_payload(data, modules_used)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_round_floats(merged), indent=2), encoding="utf-8")


def _post_envelope_e2e_file(path: Path, modules_used: list[str]) -> None:
    """Attach E2E envelope to an existing JSON file (dict or list root)."""
    if not path.exists():
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and raw.get("run_id") and raw.get("system_version"):
        return
    if isinstance(raw, list):
        body = {"payload": raw}
    else:
        body = raw
    path.write_text(json.dumps(_round_floats(_finalize_e2e_payload(body, modules_used)), indent=2), encoding="utf-8")


def _round_floats(obj, ndigits=6):
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x, ndigits) for x in obj]
    return obj


def run_e2e_sentence(out_path: Path, text: str) -> None:
    """Run analyze (6-key + attribution + dict_b + R1–R4); write JSON."""
    from runtime.pipeline.analyze import analyze

    minimal, extended = analyze(
        text,
        r1_r4=True,
        r1_r4_book_id="e2e",
        r1_r4_levels=["R1", "R2", "R3", "R4"],
    )
    out = {
        "raw_text": {"text_preview": text[:200] + ("..." if len(text) > 200 else ""), "length": len(text)},
        "summary": minimal,
        "diagnostics": dict(extended),
    }
    if isinstance(out["diagnostics"].get("family_vector"), list):
        out["diagnostics"]["family_vector"] = {"length": len(out["diagnostics"]["family_vector"]), "_truncated": True}
    if isinstance(out["diagnostics"].get("family_vector_pre_sharpen"), list):
        out["diagnostics"]["family_vector_pre_sharpen"] = {
            "length": len(out["diagnostics"]["family_vector_pre_sharpen"]),
            "_truncated": True,
        }
    out = _round_floats(out)
    from core.projection import apply_public_projection
    out = apply_public_projection(out)
    _write_e2e_json(out_path, out, ["runtime.pipeline.analyze", "core.projection"])


def run_e2e_l1_l9(out_path: Path, text: str) -> None:
    """Run L1–L9 pipeline; write JSON."""
    from runtime.pipeline.run_l1_through_l9 import run_pipeline_for_text

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    out = run_pipeline_for_text(text, assets_root=assets)
    try:
        from research.hex_outputs_e2e import hex_microstructure_bundle_for_text

        out["narrative_microstructure_e2e"] = hex_microstructure_bundle_for_text(
            text, assets, list_cap=64
        )
    except Exception as e:
        out["narrative_microstructure_e2e"] = {"_error": str(e)}
    from core.projection import apply_public_projection
    out = apply_public_projection(out)
    _write_e2e_json(out_path, out, ["runtime.pipeline.run_l1_through_l9", "core.engine.hex_outputs"])


def run_e2e_r1_r4(out_path: Path, text: str) -> None:
    """Run R1–R4 pipeline; write single JSON with units + book_profile."""
    from runtime.pipeline.r1_r4_pipeline import run_full_pipeline_to_json

    summary_payload = run_full_pipeline_to_json(text, book_id="e2e", levels=["R1", "R2", "R3", "R4"])
    from core.projection import apply_public_projection
    summary_payload = apply_public_projection(summary_payload)
    _write_e2e_json(out_path, summary_payload, ["runtime.pipeline.r1_r4_pipeline"])


def run_e2e_sphere_math_values(out_path: Path, text: str) -> None:
    """Run sphere math values flow; write JSON (via main with patched argv)."""
    from runtime.pipeline import run_sphere_math_values

    old_argv = list(sys.argv)
    try:
        sys.argv = ["", "--out", str(out_path), "--text", text]
        run_sphere_math_values.main()
    finally:
        sys.argv = old_argv
    _post_envelope_e2e_file(out_path, ["runtime.pipeline.run_sphere_math_values"])


def run_e2e_domain_metrics(out_path: Path, text: str) -> None:
    """Run structural analysis with domain metrics; write domain_metrics to JSON via service."""
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.artifact_writer import write_public_json

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    domain_constants_path = _HESPERIA / "assets" / "data" / "domain_constants.json"
    summary_payload = run_structural_analysis(
        text,
        assets_root=assets,
        stages="full",
        enable_domain_metrics=True,
        domain_constants_path=domain_constants_path if domain_constants_path.exists() else None,
    )
    out_data = summary_payload.get("domain_metrics")
    if not out_data:
        out_data = {"_error": "domain_metrics not in summary_payload", "sourceId": "e2e_domain_metrics"}
    write_public_json(out_path, out_data)


def run_e2e_sphere_math_100(out_path: Path, limit: int = 3) -> None:
    """Run sphere math on first N calibration sentences; write JSON."""
    from runtime.pipeline import run_sphere_math_100_sentences

    sentences_path = _HESPERIA / "tools" / "calibration" / "data" / "calibration_100_sentences.json"
    if not sentences_path.exists():
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([
                {"id": 1, "domain": "e2e", "text": "Justice and fairness support order."},
                {"id": 2, "domain": "e2e", "text": "Harm and conflict reduce trust."},
            ], f, indent=2)
            tmp_path = f.name
        use_path = tmp_path
        try:
            old_argv = list(sys.argv)
            sys.argv = ["", "--out", str(out_path), "--sentences", use_path, "--limit", str(limit)]
            run_sphere_math_100_sentences.main()
        finally:
            sys.argv = old_argv
            Path(tmp_path).unlink(missing_ok=True)
        _post_envelope_e2e_file(out_path, ["runtime.pipeline.run_sphere_math_100_sentences"])
        return
    old_argv = list(sys.argv)
    try:
        sys.argv = ["", "--out", str(out_path), "--sentences", str(sentences_path), "--limit", str(limit)]
        run_sphere_math_100_sentences.main()
    finally:
        sys.argv = old_argv
    _post_envelope_e2e_file(out_path, ["runtime.pipeline.run_sphere_math_100_sentences"])


def run_e2e_calibration_batch_artifacts(
    out_structural: Path,
    out_summary: Path,
    *,
    limit: int = 100,
) -> None:
    """
    Full calibration batch: structural L1–L9 per sentence (same as sphere_math_100 pipeline)
    plus a compact summary artifact (histograms, means). Separate from run_output_e2e_sphere_math_100.json (smoke N=3).
    """
    from collections import Counter
    from runtime.services.analysis_service import run_structural_analysis_batch
    from runtime.artifact_writer import write_public_json

    sentences_path = _HESPERIA / "tools" / "calibration" / "data" / "calibration_100_sentences.json"
    assets = _HESPERIA / "assets" / "lexicon" / "curated"

    if not sentences_path.exists():
        stub = [
            {"id": 1, "domain": "e2e", "text": "Justice and fairness support order."},
            {"id": 2, "domain": "e2e", "text": "Harm and conflict reduce trust."},
        ]
        sentences = stub[: min(limit, len(stub))]
    else:
        with open(sentences_path, encoding="utf-8") as f:
            sentences = json.load(f)
        sentences = sentences[:limit]

    texts = [str(s.get("text") or "") for s in sentences]
    results = run_structural_analysis_batch(texts, assets_root=assets, attach_version=False)

    out_list: list[dict[str, Any]] = []
    area_h: Counter[int] = Counter()
    fam_h: Counter[int] = Counter()
    domain_h: Counter[str] = Counter()
    cov_vals: list[float] = []
    stab_vals: list[float] = []
    tok_vals: list[int] = []

    for i, (s, res) in enumerate(zip(sentences, results)):
        out_list.append({
            "id": s.get("id", i + 1),
            "domain": s.get("domain", ""),
            "text_preview": (s.get("text", ""))[:80],
            **res,
        })
        l1 = res.get("L1") or {}
        try:
            area_h[int(l1.get("DOMINANT_AREA_ID") or 0)] += 1
        except (TypeError, ValueError):
            area_h[0] += 1
        try:
            fam_h[int(l1.get("DOMINANT_FAMILY_ID") or 0)] += 1
        except (TypeError, ValueError):
            fam_h[0] += 1
        domain_h[str(s.get("domain") or "unknown")] += 1
        try:
            cov_vals.append(float(l1.get("COVERAGE_RATIO") or 0.0))
        except (TypeError, ValueError):
            pass
        try:
            stab_vals.append(float(l1.get("STRUCTURAL_STABILITY_INDEX") or 0.0))
        except (TypeError, ValueError):
            pass
        try:
            tok_vals.append(int(l1.get("TOTAL_TOKENS") or 0))
        except (TypeError, ValueError):
            pass

    def _mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 6) if xs else 0.0

    summary = {
        "run": "e2e_calibration_batch_summary",
        "sentence_count": len(sentences),
        "limit_applied": limit,
        "source_file": str(sentences_path.relative_to(_HESPERIA)) if sentences_path.exists() else "_inline_stub",
        "by_input_domain": dict(sorted(domain_h.items())),
        "dominant_area_histogram": {str(k): v for k, v in sorted(area_h.items())},
        "dominant_family_top": {str(k): fam_h[k] for k in sorted(fam_h, key=lambda x: -fam_h[x])[:12]},
        "dominant_area_top": {str(k): area_h[k] for k in sorted(area_h, key=lambda x: -area_h[x])[:12]},
        "mean_L1_coverage_ratio": _mean(cov_vals),
        "mean_L1_structural_stability": _mean(stab_vals),
        "total_tokens_min": min(tok_vals) if tok_vals else 0,
        "total_tokens_max": max(tok_vals) if tok_vals else 0,
        "total_tokens_mean": round(sum(tok_vals) / len(tok_vals), 4) if tok_vals else 0.0,
    }
    summary = _round_floats(summary)

    out_structural.parent.mkdir(parents=True, exist_ok=True)
    write_public_json(
        out_structural,
        _round_floats({"run": "e2e_calibration_structural", "rows": out_list}),
    )
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    write_public_json(out_summary, summary)
    _post_envelope_e2e_file(out_structural, ["run_e2e_calibration_batch_artifacts"])
    _post_envelope_e2e_file(out_summary, ["run_e2e_calibration_batch_artifacts"])


def _text_preview(text: str, n: int = 200) -> dict[str, Any]:
    return {"text_preview": text[:n] + ("..." if len(text) > n else ""), "length": len(text)}


def _activation_topology_maps(
    activation: dict[str, Any], node_ids: set[str]
) -> dict[str, Any] | None:
    """Same binding as clinical KME TRIZ: concept_to_area + concept_to_family for active nodes."""
    c2a = activation.get("concept_to_area") or {}
    c2f = activation.get("concept_to_family") or {}

    def _ival(x: Any) -> int | None:
        try:
            return int(x)
        except (TypeError, ValueError):
            try:
                return int(float(x))
            except (TypeError, ValueError):
                return None

    ca = {str(k): v for k, v in c2a.items() if str(k) in node_ids and _ival(v) is not None}
    cf = {str(k): v for k, v in c2f.items() if str(k) in node_ids and _ival(v) is not None}
    ca = {k: _ival(v) for k, v in ca.items()}
    cf = {k: _ival(v) for k, v in cf.items()}
    if not ca and not cf:
        return None
    topo: dict[str, Any] = {}
    if ca:
        topo["concept_to_area"] = dict(sorted(ca.items()))
    if cf:
        topo["concept_to_family"] = dict(sorted(cf.items()))
    return topo or None


def _slim_csv_exports(obj: dict[str, Any]) -> None:
    ce = obj.get("csv_exports")
    if isinstance(ce, dict):
        obj["csv_exports"] = {
            k: {"byte_length": len(v) if isinstance(v, str) else 0} for k, v in sorted(ce.items())
        }


def run_e2e_session_kme(out_path: Path, text: str) -> None:
    """NLP session → clinical ActiveGraph → KME primitives/derived/fingerprint + TRIZ."""
    from hesperia.engine.kme.clinical_bridge import run_session_kme_pipeline
    from core.domain.pipeline import metric_report_to_dict

    try:
        report = run_session_kme_pipeline(text, source_id="e2e_session")
        body = {"report": metric_report_to_dict(report)}
    except Exception as e:
        body = {"_error": str(e), "sourceId": "e2e_session"}
    out = {"raw_text": _text_preview(text), **body, "input": _text_preview(text)}
    out = _round_floats(out)
    from core.projection import apply_public_projection

    out = apply_public_projection(out)
    _write_e2e_json(out_path, out, ["hesperia.engine.kme.clinical_bridge", "core.domain.pipeline"])


def run_e2e_triz_complete(out_path: Path, text: str) -> None:
    """Session activation → ActiveGraph → run_triz_analysis_complete (API /analysis/triz parity)."""
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph
    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
    from hesperia.nlp.session_parser import analyze_session

    try:
        try:
            from sphere.topology.family_embedding import load_family_embedding_tfp

            embedding = load_family_embedding_tfp()
        except Exception:
            embedding = {}
        activation = analyze_session(text, embedding=embedding)
        ag = build_clinical_active_graph(activation)
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
        topo = _activation_topology_maps(activation, set(ag.nodes.keys()))
        ag2 = active_graph_from_payload(payload)
        content = run_triz_analysis_complete(
            ag2,
            topo,
            narrative_id="e2e_narrative",
            run_id=None,
            topology_mode=True,
        )
        _slim_csv_exports(content)
        body = {"triz_complete": content}
    except Exception as e:
        body = {"_error": str(e)}
    out = {"raw_text": _text_preview(text), **body, "input": _text_preview(text)}
    out = _round_floats(out)
    from core.projection import apply_public_projection

    out = apply_public_projection(out)
    _write_e2e_json(out_path, out, ["hesperia.extensions.triz.pipeline", "hesperia.nlp.session_parser"])


def run_e2e_session_topology(out_path: Path, text: str) -> None:
    """Clinical session topology: segmented activation, transitions, aggression curve, defenses."""
    try:
        from hesperia.tfp import run_session_topology
    except Exception as e:
        out = _round_floats(
            {
                "input": _text_preview(text),
                "run": "e2e_session_topology",
                "_skipped": "hesperia.tfp_unavailable",
                "_error": str(e),
            }
        )
        _write_e2e_json(out_path, out, ["runtime.pipeline.run_e2e_all"])
        return

    max_segments = 12
    try:
        full = run_session_topology(text, window_size=80)
        segs = full.get("segments") or []
        if len(segs) > max_segments:
            full = {
                **full,
                "segments": segs[:max_segments],
                "_segments_truncated": True,
                "_segments_total": len(segs),
            }
        body = {"session_topology": full}
    except Exception as e:
        body = {"_error": str(e)}
    out = _round_floats({"input": _text_preview(text), **body})
    # Not apply_public_projection: clinical topology keys are not on the public allowlist.
    _write_e2e_json(out_path, out, ["hesperia.tfp"])


def run_e2e_tfp_smoke(out_path: Path, primary_text: str | None = None) -> None:
    """
    TFP / Kernberg TESTING GROUNDS — excluded from Engine Dynamics canonical release (v0.5)
    (see docs/HESPERIA_v0_5_ENGINE_DYNAMICS.md §2). CI + clinical regression only.

    Structural batch on smoke sessions; analyze_session + detect_tfp_stage; speaker-aware smoke.
    When ``primary_text`` is set (same string as E2E ``--text``), a synthetic session
    ``e2e_primary`` is prepended so clinical Markdown / transcripts drive TFP smoke + hex bundle.
    """
    try:
        from hesperia.tfp import TFP_STAGES, detect_tfp_stage
        from hesperia.nlp.session_parser import analyze_session, analyze_session_speaker_aware
        from runtime.services.analysis_service import run_structural_analysis_batch
    except Exception as e:
        out = _round_floats(
            {
                "run": "e2e_tfp_smoke",
                "_skipped": "hesperia.tfp_unavailable",
                "_error": str(e),
                "structural_batch_sessions": 0,
                "session_tfp_stages": [],
            }
        )
        _write_e2e_json(out_path, out, ["runtime.pipeline.run_e2e_all"])
        return

    smoke_path = _HESPERIA / "tests" / "fixtures" / "clinical_tfp" / "tfp_kernberg" / "session_transcripts_smoke_english.json"
    if smoke_path.exists():
        payload = json.loads(smoke_path.read_text(encoding="utf-8"))
        sessions = list(payload.get("sessions") or [])
    else:
        sessions = [
            {
                "session_id": "inline_01",
                "text": (
                    "Patient: I feel empty and furious when you interpret my silence. "
                    "Therapist: What do you imagine I am thinking?"
                ),
            },
            {
                "session_id": "inline_02",
                "text": "Boundaries, trust, transference, and integration of self and other.",
            },
        ]

    primary = (primary_text or "").strip()
    if primary:
        sessions = [{"session_id": "e2e_primary", "text": primary}, *sessions]

    texts = [str(s.get("text") or "") for s in sessions]
    sids = [str(s.get("session_id") or f"s{i}") for i, s in enumerate(sessions)]
    assets = _HESPERIA / "assets" / "lexicon" / "curated"

    structural_batch: list[dict[str, Any]] = []
    try:
        batch = run_structural_analysis_batch(texts, assets_root=assets, attach_version=False)
        for i, row in enumerate(batch):
            sid = sids[i] if i < len(sids) else f"batch_{i}"
            one = dict(row)
            one["session_id"] = sid
            structural_batch.append(one)
    except Exception as e:
        structural_batch = [{"_error": str(e), "session_id": "_batch"}]

    try:
        from sphere.topology.family_embedding import load_family_embedding_tfp

        embedding = load_family_embedding_tfp()
    except Exception:
        embedding = {}

    session_tfp_stages: list[dict[str, Any]] = []
    for sid, t in zip(sids, texts):
        if not t.strip():
            continue
        try:
            act = analyze_session(t, embedding=embedding or None)
            areas = act.get("areas") or {}
            stage = detect_tfp_stage({k: float(v) for k, v in areas.items() if v is not None})
            session_tfp_stages.append(
                {
                    "session_id": sid,
                    "tfp_stage": stage,
                    "areas_top": dict(sorted(areas.items(), key=lambda x: -float(x[1] or 0))[:8]),
                }
            )
        except Exception as ex:
            session_tfp_stages.append({"session_id": sid, "_error": str(ex)})

    dialogue_smoke = (
        "Patient: I hate waiting; you always leave me alone in the room.\n"
        "Therapist: Say more about what alone feels like for you right now."
    )
    dialogue_for_speaker_aware = dialogue_smoke
    if primary and len(primary) <= 200_000:
        dialogue_for_speaker_aware = primary
    session_hex_microstructure_tfp: list[dict[str, Any]] = []
    try:
        from research.hex_outputs_e2e import hex_microstructure_bundle_for_text

        for sid, t in zip(sids, texts):
            if not (t or "").strip():
                continue
            try:
                session_hex_microstructure_tfp.append(
                    {"session_id": sid, **hex_microstructure_bundle_for_text(t, assets, list_cap=48)}
                )
            except Exception as ex:
                session_hex_microstructure_tfp.append({"session_id": sid, "_error": str(ex)})
    except Exception:
        pass

    speaker_aware_smoke: dict[str, Any] = {}
    try:
        sa = analyze_session_speaker_aware(dialogue_for_speaker_aware, embedding=embedding or None)
        areas_sa = sa.get("areas") or {}
        speaker_aware_smoke = {
            "tfp_stage": detect_tfp_stage({k: float(v) for k, v in areas_sa.items() if v is not None}),
            "areas_top": dict(sorted(areas_sa.items(), key=lambda x: -float(x[1] or 0))[:8]),
            "has_speaker_activation": "speaker_activation" in sa,
        }
        if dialogue_for_speaker_aware is not dialogue_smoke:
            speaker_aware_smoke["speaker_aware_source"] = "e2e_primary"
    except Exception as e:
        speaker_aware_smoke = {"_error": str(e)}

    session_dlcr_bundles: list[dict[str, Any]] = []
    if os.environ.get("HESPERIA_TFP_DLCR", "").strip().lower() in ("1", "true", "yes", "on"):
        try:
            from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

            for sid, t in zip(sids, texts):
                if not (t or "").strip():
                    continue
                try:
                    d = run_dlcr_pipeline(t, repo_root=_HESPERIA)
                    session_dlcr_bundles.append(
                        {
                            "session_id": sid,
                            "lexical_hits_accepted": d.get("lexical_hits_accepted"),
                            "degradation_flags": d.get("degradation_flags"),
                            "microcell_concentration": d.get("hex_concentration"),
                            "span_count": len(d.get("span_resolutions") or []),
                        }
                    )
                except Exception as ex:  # noqa: BLE001
                    session_dlcr_bundles.append({"session_id": sid, "_error": str(ex)})
        except Exception as ex:  # noqa: BLE001
            session_dlcr_bundles = [{"_error": str(ex)}]

    out: dict[str, Any] = {
        "run": "e2e_tfp_smoke",
        "tfp_stages_enum": list(TFP_STAGES),
        "structural_batch_sessions": len(structural_batch),
        "structural_batch": structural_batch,
        "session_tfp_stages": session_tfp_stages,
        "session_hex_microstructure_tfp": session_hex_microstructure_tfp,
        "speaker_aware_smoke": speaker_aware_smoke,
    }
    if session_dlcr_bundles:
        out["session_dlcr_bundles"] = session_dlcr_bundles
    out = _round_floats(out)
    _write_e2e_json(out_path, out, ["runtime.services.analysis_service", "hesperia.tfp", "hesperia.nlp.session_parser"])


def run_e2e_dlcr(out_path: Path, text: str) -> None:
    """DLCR L0–L6 bundle for primary E2E text (Ethan INT-015)."""
    from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

    t = (text or "").strip() or "justice order fairness truth"
    body = run_dlcr_pipeline(t, repo_root=_HESPERIA)
    # Preserve artifact run id (pipeline body also sets run=dlcr_pipeline_v1).
    out = _round_floats({**body, "run": "e2e_dlcr", "input": _text_preview(t)})
    _write_e2e_json(out_path, out, ["core.engine.lexical_concept.pipeline"])


def run_e2e_sealed_multiscale(out_path: Path, text: str) -> None:
    """Sealed multiscale: hex → family bridge → area → product signals → hspr_index."""
    from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    use_triz = os.environ.get("HESPERIA_SEALED_E2E_TRIZ", "").strip() in ("1", "true", "yes")
    out = run_sealed_multiscale_stack(
        text.strip() or "justice order fairness care",
        assets,
        use_triz_contradiction=use_triz,
    )
    out = _round_floats({"run": "e2e_sealed_multiscale", **out})
    _write_e2e_json(out_path, out, ["core.engine.sealed_multiscale_stack"])


def run_e2e_hex_microstructure_tfp(out_path: Path, text: str) -> None:
    """
    Dedicated artifact: hex microstructure + Option A closure + TFP topology provenance
    for primary E2E text and each TFP smoke session transcript.
    """
    from research.hex_outputs_e2e import hex_microstructure_bundle_for_text

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    smoke_path = _HESPERIA / "tests" / "fixtures" / "clinical_tfp" / "tfp_kernberg" / "session_transcripts_smoke_english.json"
    if smoke_path.exists():
        payload = json.loads(smoke_path.read_text(encoding="utf-8"))
        sessions = list(payload.get("sessions") or [])
    else:
        sessions = [
            {"session_id": "inline_01", "text": "Patient: emptiness and rage. Therapist: say more."},
            {"session_id": "inline_02", "text": "Boundaries trust transference integration."},
        ]

    primary = hex_microstructure_bundle_for_text(text.strip() or "justice order fairness truth", assets)
    session_bundles: list[dict[str, Any]] = []
    for s in sessions:
        sid = str(s.get("session_id") or "s")
        t = str(s.get("text") or "")
        if not t.strip():
            continue
        try:
            session_bundles.append(
                {"session_id": sid, **hex_microstructure_bundle_for_text(t, assets, list_cap=56)}
            )
        except Exception as e:
            session_bundles.append({"session_id": sid, "_error": str(e)})

    out = _round_floats(
        {
            "run": "e2e_hex_microstructure_tfp",
            "input_text_preview": (text or "")[:160],
            "primary_bundle": primary,
            "tfp_smoke_session_bundles": session_bundles,
        }
    )
    _write_e2e_json(out_path, out, ["research.hex_outputs_e2e"])


def run_e2e_capability_matrix(out_path: Path, text: str) -> None:
    """
    Gena capability sweep: one JSON bundling thin calls across runtime, sphere, hesperia.engine,
    clinical, nlp, triz, product, evaluation baselines, topology propagation, reading multiscale (optional).
    """
    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    text_s = (text or "").strip()[:2000]
    blocks: dict[str, Any] = {}

    def _put(name: str, fn: Any) -> None:
        try:
            blocks[name] = fn()
        except Exception as e:
            blocks[name] = {"_error": str(e)}

    _put(
        "structural_L1_L2",
        lambda: (
            lambda r: {
                "run": r.get("run"),
                "L1_total_tokens": (r.get("L1") or {}).get("total_tokens"),
                "L2_present": "L2" in r,
                "hspr_present": (r.get("multiscale_signals") or {}).get("hspr_index") is not None,
            }
        )(
            __import__("runtime.services.analysis_service", fromlist=["run_structural_analysis"]).run_structural_analysis(
                text_s[:800], assets_root=assets, stages="full"
            )
        ),
    )
    _put(
        "structural_L1_L2_L3",
        lambda: (
            lambda r: {
                "run": r.get("run"),
                "L3_present": "L3" in r,
                "L1_total_tokens": (r.get("L1") or {}).get("total_tokens"),
                "hspr_present": (r.get("multiscale_signals") or {}).get("hspr_index") is not None,
            }
        )(
            __import__("runtime.services.analysis_service", fromlist=["run_structural_analysis"]).run_structural_analysis(
                text_s[:800], assets_root=assets, stages="full"
            )
        ),
    )

    def _compare() -> dict[str, Any]:
        rsa = __import__("runtime.services.analysis_service", fromlist=["run_structural_analysis"]).run_structural_analysis
        r1 = rsa("justice order fairness", assets_root=assets, stages="full")
        r2 = rsa("crisis chaos threat block", assets_root=assets, stages="full")
        d1, d2 = (r1.get("L7") or {}), (r2.get("L7") or {})
        dom1 = (r1.get("usf") or {}).get("raw_metrics") or {}
        dom2 = (r2.get("usf") or {}).get("raw_metrics") or {}

        def _same_dominant(m1: dict, m2: dict) -> bool:
            v1 = m1.get("macro_domain_vector") or m1.get("dominant_macro_domain")
            v2 = m2.get("macro_domain_vector") or m2.get("dominant_macro_domain")
            if isinstance(v1, list) and isinstance(v2, list) and v1 and v2:
                i1 = max(range(len(v1)), key=lambda i: v1[i])
                i2 = max(range(len(v2)), key=lambda i: v2[i])
                return i1 == i2
            return False

        cmp = {
            "run": "compare",
            "dominant_match": _same_dominant(dom1, dom2),
            "trust1": d1.get("OUTPUT_TRUST_TAG"),
            "trust2": d2.get("OUTPUT_TRUST_TAG"),
        }
        __import__("runtime.shipping.schema_guard", fromlist=["validate_against_public_schema"]).validate_against_public_schema(
            cmp
        )
        return cmp

    _put("shipping_compare", _compare)

    def _interpret() -> dict[str, Any]:
        from hesperia.tfp import interpret_session
        from hesperia.nlp.session_parser import analyze_session

        try:
            from sphere.topology.family_embedding import load_family_embedding_tfp

            emb = load_family_embedding_tfp()
        except Exception:
            emb = None
        act = analyze_session(text_s[:1200], embedding=emb)
        return interpret_session(act)

    _put("interpret_session", _interpret)

    def _micro_hex_tfp() -> dict[str, Any]:
        from research.hex_outputs_e2e import hex_microstructure_bundle_for_text

        return hex_microstructure_bundle_for_text(text_s[:2000], assets, list_cap=40)

    _put("narrative_microstructure_tfp_wire", _micro_hex_tfp)

    def _sealed_stack() -> dict[str, Any]:
        from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack

        r = run_sealed_multiscale_stack(text_s[:1500], assets, use_triz_contradiction=False)
        av = r.get("area_activation_vector") or []
        return {
            "hspr_index": r.get("hspr_index"),
            "propagation_strength": r.get("propagation_strength"),
            "area_max": max(av) if av else None,
        }

    _put("sealed_multiscale_hspr", _sealed_stack)

    def _dlcr_cap() -> dict[str, Any]:
        from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

        d = run_dlcr_pipeline(text_s[:1500], repo_root=_HESPERIA)
        return {
            "run": "dlcr_pipeline",
            "lexical_hits_accepted": d.get("lexical_hits_accepted"),
            "resource_versions": d.get("resource_versions"),
            "microcell_concentration": d.get("hex_concentration"),
        }

    _put("dlcr_pipeline", _dlcr_cap)

    _put(
        "session_enhanced",
        lambda: (
            lambda a: {
                "areas_n": len(a.get("areas") or {}),
                "top_area": max((a.get("areas") or {}).items(), key=lambda x: float(x[1] or 0))[0]
                if (a.get("areas") or {})
                else None,
            }
        )(
            __import__("hesperia.nlp.session_parser", fromlist=["analyze_session_enhanced"]).analyze_session_enhanced(
                "Patient: denial projection splitting toward therapist boundaries."
            )
        ),
    )

    _put(
        "transcript_parse",
        lambda: {
            "turns": len(
                __import__("hesperia.nlp.transcript_parser", fromlist=["parse_speaker_turns"]).parse_speaker_turns(
                    "Patient: Rage and emptiness.\nTherapist: What do you notice now?"
                )
            )
        },
    )

    _put(
        "baseline_keyword",
        lambda: __import__(
            "research.evaluation.baselines.keyword_baseline", fromlist=["run_keyword_baseline"]
        ).run_keyword_baseline(text_s),
    )

    def _graph() -> dict[str, Any]:
        return __import__(
            "research.evaluation.baselines.graph_baseline", fromlist=["run_graph_baseline"]
        ).run_graph_baseline(
            "growth freedom market cut ban crisis against support " * 3
        )

    _put("baseline_graph", _graph)
    _put(
        "baseline_tfidf",
        lambda: __import__(
            "research.evaluation.baselines.tfidf_baseline", fromlist=["run_tfidf_style_baseline"]
        ).run_tfidf_style_baseline(text_s),
    )

    _put(
        "compare_triz_direct",
        lambda: __import__(
            "hesperia.extensions.triz.direct_outputs", fromlist=["TRIZDirectMetrics", "compare_triz_direct"]
        ).compare_triz_direct(
            __import__("hesperia.extensions.triz.direct_outputs", fromlist=["TRIZDirectMetrics"]).TRIZDirectMetrics(
                contradiction_count=2, innovation_score=0.3
            ),
            __import__("hesperia.extensions.triz.direct_outputs", fromlist=["TRIZDirectMetrics"]).TRIZDirectMetrics(
                contradiction_count=5, innovation_score=0.7
            ),
        ),
    )

    _put(
        "compare_triz_corpora",
        lambda: __import__(
            "hesperia.extensions.triz.commercial_intelligence", fromlist=["compare_triz_corpora"]
        ).compare_triz_corpora(
            __import__("hesperia.extensions.triz.direct_outputs", fromlist=["TRIZDirectMetrics"]).TRIZDirectMetrics(
                contradiction_count=1
            ),
            __import__("hesperia.extensions.triz.direct_outputs", fromlist=["TRIZDirectMetrics"]).TRIZDirectMetrics(
                contradiction_count=4
            ),
        ),
    )

    _put(
        "topology_families_tfp",
        lambda: (
            lambda d: {"families_loaded": isinstance(d, dict) and len(d) > 0}
        )(__import__("sphere.topology", fromlist=["load_families_structure_tfp"]).load_families_structure_tfp()),
    )

    def _propagate() -> dict[str, Any]:
        from hesperia.nlp.session_parser import analyze_session
        from sphere.topology.activation_propagation import propagate_activation
        from sphere.topology.family_embedding import load_family_embedding_tfp

        emb = load_family_embedding_tfp()
        act = analyze_session("defense aggression object relations trust", embedding=emb)
        out = propagate_activation(act, emb, propagation_trace=False)
        return {"families_out": len(out.get("families") or {}), "areas_out": len(out.get("areas") or {})}

    _put("propagate_activation", _propagate)

    _put(
        "run_triz_analysis_core",
        lambda: (
            lambda sig: {
                "contradictions": len(sig.contradictions),
                "clusters": len(sig.innovation_clusters),
                "narratives": len(sig.narratives),
            }
        )(
            __import__("hesperia.extensions.triz.triz_pipeline", fromlist=["run_triz_analysis"]).run_triz_analysis(
                [
                    __import__("hesperia.extensions.triz.models", fromlist=["ConceptActivation", "MatrixCoordinate"]).ConceptActivation(
                        "cap_c1", 1.0, __import__("hesperia.extensions.triz.models", fromlist=["MatrixCoordinate"]).MatrixCoordinate(2, 1, None)
                    ),
                    __import__("hesperia.extensions.triz.models", fromlist=["ConceptActivation", "MatrixCoordinate"]).ConceptActivation(
                        "cap_c2", 0.85, __import__("hesperia.extensions.triz.models", fromlist=["MatrixCoordinate"]).MatrixCoordinate(3, 2, None)
                    ),
                ],
                [
                    __import__("hesperia.extensions.triz.models", fromlist=["ConceptRelation"]).ConceptRelation(
                        "cap_c1", "cap_c2", "opposes", 1.0
                    )
                ],
                {2: [3], 3: [2, 4], 4: [3]},
            )
        ),
    )

    _put(
        "product_compare_policy",
        lambda: __import__(
            "hesperia.product.comparison_engine", fromlist=["compare_policy_reports"]
        ).compare_policy_reports(
            {"global_tension_score": 0.4, "top_cross_domain_conflicts": [], "top_conflict_clusters": []},
            {"global_tension_score": 0.6, "top_cross_domain_conflicts": [{"a": 1}], "top_conflict_clusters": []},
        ),
    )

    _put(
        "ontology_version",
        lambda: {"ontology_version": __import__("hesperia.ontology.registry", fromlist=["get_ontology_version"]).get_ontology_version()},
    )

    _put(
        "temporal_activation_timeline",
        lambda: {
            "timeline_steps": len(
                __import__("hesperia.nlp.temporal_dynamics", fromlist=["build_activation_timeline"]).build_activation_timeline(
                    "Patient: Angry.\nTherapist: Where?\nPatient: At you.\nTherapist: Say more.",
                    window_utterances=2,
                )
            )
        },
    )

    def _kme_doc_corpus() -> dict[str, Any]:
        from core.domain.models import (
            ConceptHit,
            DocumentInput,
            DomainConstants,
            DomainEdge,
            DomainGraph,
            DomainNode,
            RelationCandidate,
        )
        from core.domain.pipeline import metric_report_to_dict, run_corpus, run_document

        nodes = {"kme_a": DomainNode("kme_a"), "kme_b": DomainNode("kme_b")}
        edges = [DomainEdge("kme_a", "kme_b", "relates")]
        dg = DomainGraph(nodes=nodes, edges=edges)
        dc = DomainConstants(domain_node_count=50, domain_degree_p95=6.0, domain_distance_p95=4.0)
        hits = [ConceptHit("kme_a", 0), ConceptHit("kme_b", 1)]
        rel = [RelationCandidate("kme_a", "kme_b", "relates")]
        doc_rep = run_document(dg, dc, "gena_kme_single", hits, rel)
        ddict = metric_report_to_dict(doc_rep)
        docs = [
            DocumentInput("gena_kme_c1", [ConceptHit("kme_a", 0)], []),
            DocumentInput("gena_kme_c2", [ConceptHit("kme_b", 0), ConceptHit("kme_a", 1)], rel),
        ]
        corp_reports = run_corpus(docs, dg, dc)
        fp = ddict.get("fingerprint") or {}
        vh = fp.get("vectorHash") if isinstance(fp, dict) else None
        return {
            "run_document": {
                "sourceId": ddict.get("sourceId"),
                "primitives_n": len(ddict.get("primitives") or {}),
                "fingerprint_hash_prefix": (vh or "")[:20],
                "triz_bundle": bool(ddict.get("triz")),
            },
            "run_corpus": {
                "report_count": len(corp_reports),
                "source_ids": [r.source_id for r in corp_reports],
                "distinct_hashes": len({r.fingerprint.vector_hash for r in corp_reports}),
            },
        }

    _put("kme_run_document_and_corpus", _kme_doc_corpus)

    def _batch_runner_dossiers() -> dict[str, Any]:
        import tempfile

        from runtime.pipeline.batch_runner import run_batch

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            inp = tdp / "batch_in.json"
            inp.write_text(json.dumps(["justice fairness order", "harm crisis block"]), encoding="utf-8")
            outd = tdp / "dossiers"
            idx = tdp / "dossier_index.json"
            paths = run_batch([inp], outd, workers=1, validate_dossier=False, index_path=idx)
            return {"dossiers_written": len(paths), "filenames": sorted(p.name for p in paths)}

    _put("batch_runner_dossiers", _batch_runner_dossiers)

    def _mvp_acceptance() -> dict[str, Any]:
        import tempfile

        from hesperia.product.mvp_acceptance import run_mvp_acceptance

        with tempfile.TemporaryDirectory() as td:
            r = run_mvp_acceptance(tmp_output=Path(td) / "mvp_proj")
            return {
                "passed": r.passed,
                "passed_checks": r.passed_checks,
                "failed_checks": r.failed_checks,
            }

    _put("mvp_acceptance", _mvp_acceptance)

    def _experiment_runner() -> dict[str, Any]:
        from research.experiments.experiment_runner import run_experiment
        from hesperia.nlp.session_parser import analyze_session

        def slim_analyze(t: str) -> dict[str, Any]:
            a = analyze_session((t or "")[:500])
            ar = a.get("areas") or {}
            return {"areas_n": len(ar), "area_keys_sample": list(ar.keys())[:6]}

        rows = run_experiment(
            [
                {"session_id": "gena_exp_1", "text": "Patient: rage displacement toward therapist."},
                {"session_id": "gena_exp_2", "text": "Therapist: boundaries transference interpretation."},
            ],
            slim_analyze,
        )
        return {
            "sessions": len(rows),
            "session_ids": [x.get("session_id") for x in rows],
            "first_areas_n": (rows[0].get("activation") or {}).get("areas_n"),
        }

    _put("experiment_runner", _experiment_runner)

    if os.environ.get("HESPERIA_E2E_MULTISCALE") == "1":

        def _ms() -> dict[str, Any]:
            from runtime.pipeline.reading_scales import run_multiscale

            ms = run_multiscale(
                "Justice and order. Harm and crisis.",
                assets_root=assets,
            )
            gs = ms.get("global_structure") or {}
            return {
                "R1_segments": len(ms.get("R1") or []),
                "R2_segments": len(ms.get("R2") or []),
                "R3_segments": len(ms.get("R3") or []),
                "R4_segments": len(ms.get("R4") or []),
                "tension_axes": gs.get("tension_axes"),
            }

        _put("reading_multiscale", _ms)
    else:
        blocks["reading_multiscale"] = {"_skipped": "HESPERIA_E2E_MULTISCALE=1 for R1–R4 reading_scales.run_multiscale"}

    def _semantic_field_capability() -> dict[str, Any]:
        from hesperia.extensions.dynamics.calibration import compute_hspr_calibration_index
        from runtime.semantic_field.run_semantic_field import run_semantic_field

        r = run_semantic_field(
            {
                "family_count": 2,
                "families_per_area": 1,
                "area_count": 2,
                "ontology": {
                    "family_ids": ["cap_x", "cap_y"],
                    "relations": [["cap_x", "cap_y"]],
                    "contradictions": [],
                    "resistance_default": 0.1,
                },
                "alpha": 0.09,
                "beta": 0.05,
                "gamma": 0.0,
                "delta": 0.28,
                "initial_mode": "uniform",
                "documents": [{"source_family_id": "cap_x"}],
                "max_steps": 8,
            }
        )
        hci = compute_hspr_calibration_index(
            stability_score=0.75,
            source_alignment=0.5,
            energy_value=0.2,
            contradiction_load=0.1,
            diffusion_load=0.15,
            resistance_load=0.12,
        )
        return {
            "semantic_field_matrices_provenance": r.get("matrices_provenance"),
            "semantic_field_steps": r.get("steps"),
            "hspr_calibration_index_smoke": hci.get("hspr_calibration_index"),
        }

    _put("semantic_field_and_hci", _semantic_field_capability)

    out = _round_floats(
        {
            "run": "e2e_capability_matrix",
            "blocks": blocks,
            "block_names": sorted(blocks.keys()),
        }
    )
    _write_e2e_json(out_path, out, ["runtime.pipeline.run_e2e_capability_matrix"])


def run_e2e_semantic_field(out_path: Path) -> None:
    """
    Ontology → matrix_builders → semantic field engine (runtime/configs/semantic_field_ontology_example.json).
    Timeline truncated in artifact for size; full numeric endpoints retained.
    """
    cfg_path = _HESPERIA / "runtime" / "configs" / "semantic_field_ontology_example.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    else:
        cfg = {
            "family_count": 4,
            "families_per_area": 2,
            "area_count": 2,
            "ontology": {
                "family_ids": ["A01", "A02", "A03", "A04"],
                "relations": [["A01", "A02"], ["A02", "A03"], ["A03", "A04"]],
                "contradictions": [["A01", "A04", 0.2]],
                "resistance_default": 0.1,
            },
            "alpha": 0.1,
            "beta": 0.05,
            "gamma": 0.1,
            "delta": 0.3,
            "initial_mode": "uniform",
            "documents": [{"source_family_id": "A02", "source_strength": 1.0}],
            "max_steps": 20,
        }
    cfg = dict(cfg)
    cfg["max_steps"] = min(int(cfg.get("max_steps", 25)), 25)

    from runtime.semantic_field.run_semantic_field import run_semantic_field

    out = run_semantic_field(cfg)
    tl = out.get("timeline")
    if isinstance(tl, list) and len(tl) > 6:
        out["timeline"] = {
            "run": "e2e_semantic_field_truncated",
            "steps_total": len(tl),
            "head": tl[:2],
            "tail": tl[-2:],
        }
    out["run"] = "e2e_semantic_field"
    out = _round_floats(out)
    _write_e2e_json(out_path, out, ["runtime.semantic_field.run_semantic_field"])


def run_e2e_field_calibration_bundle(out_dir: Path) -> dict[str, Path]:
    """
    Mini HCI grid (ontology matrices); writes run_output_e2e_field_calibration*.json (3 files).
    """
    from runtime.semantic_field.run_field_calibration import run_field_calibration, write_field_calibration_artifacts

    cfg = {
        "family_count": 2,
        "families_per_area": 1,
        "area_count": 2,
        "ontology": {
            "family_ids": ["sf_a", "sf_b"],
            "relations": [["sf_a", "sf_b"]],
            "contradictions": [["sf_a", "sf_b", 0.15]],
            "resistance_default": 0.08,
        },
        "initial_mode": "uniform",
        "documents": [{"source_family_id": "sf_a", "weight": 1.0, "quality": 1.0}],
        "parameter_grid": {
            "alpha": [0.07, 0.11],
            "beta": [0.04],
            "gamma": [0.02],
            "delta": [0.22, 0.32],
            "mu": [0.0],
            "dt": [1.0],
        },
        "max_steps": 14,
        "epsilon": 1e-5,
        "tau": 1e-5,
        "top_k": 4,
        "include_all_results": False,
    }
    result = run_field_calibration(cfg)
    base = out_dir / "run_output_e2e_field_calibration.json"
    p_main, p_best, p_topk = write_field_calibration_artifacts(result, base)
    meta = json.loads(p_main.read_text(encoding="utf-8"))
    meta["run"] = "e2e_field_calibration"
    p_main.write_text(json.dumps(_round_floats(meta), indent=2), encoding="utf-8")
    return {
        "run_output_e2e_field_calibration.json": p_main,
        "run_output_e2e_field_calibration_best.json": p_best,
        "run_output_e2e_field_calibration_topk.json": p_topk,
    }


def run_all(out_dir: Path | None = None, text: str | None = None) -> dict[str, Path]:
    """Run all e2e flows; write to out_dir. Returns map output_basename -> path written."""
    out_dir = out_dir or DEFAULT_E2E_DIR
    out_dir = Path(out_dir)
    text = (text or "Justice and fairness support social order. Harm and conflict reduce trust.").strip()
    _ensure_e2e_run_id()

    written: dict[str, Path] = {}

    # 1. Analyze sentence
    p = out_dir / "run_output_e2e_sentence.json"
    run_e2e_sentence(p, text)
    written["run_output_e2e_sentence.json"] = p

    # 2. L1–L9
    p = out_dir / "run_output_e2e_l1_l9.json"
    run_e2e_l1_l9(p, text)
    written["run_output_e2e_l1_l9.json"] = p

    # 3. R1–R4
    p = out_dir / "run_output_e2e_r1_r4.json"
    run_e2e_r1_r4(p, text)
    written["run_output_e2e_r1_r4.json"] = p

    # 4. Sphere math values
    p = out_dir / "run_output_e2e_sphere_math_values.json"
    run_e2e_sphere_math_values(p, text)
    written["run_output_e2e_sphere_math_values.json"] = p

    # 5. Sphere math 100 (limit 3 — fast smoke, distinct from full calibration batch)
    p = out_dir / "run_output_e2e_sphere_math_100.json"
    run_e2e_sphere_math_100(p, limit=3)
    written["run_output_e2e_sphere_math_100.json"] = p

    # 5b–5c. Calibration batch N sentences → structural list + summary (default N=100; override HESPERIA_E2E_CALIBRATION_BATCH_N)
    cal_n = int(os.environ.get("HESPERIA_E2E_CALIBRATION_BATCH_N", "100"))
    cal_n = max(1, min(cal_n, 500))
    p_cal = out_dir / "run_output_e2e_calibration_100_structural.json"
    p_sum = out_dir / "run_output_e2e_calibration_100_summary.json"
    run_e2e_calibration_batch_artifacts(p_cal, p_sum, limit=cal_n)
    written["run_output_e2e_calibration_100_structural.json"] = p_cal
    written["run_output_e2e_calibration_100_summary.json"] = p_sum

    # 6. Domain metrics (41 signals, fingerprint, hash) — structural pipeline + KME bridge
    p = out_dir / "run_output_e2e_domain_metrics.json"
    run_e2e_domain_metrics(p, text)
    written["run_output_e2e_domain_metrics.json"] = p

    # 7. Session → KME + TRIZ (hesperia.engine.kme clinical path)
    p = out_dir / "run_output_e2e_session_kme.json"
    run_e2e_session_kme(p, text)
    written["run_output_e2e_session_kme.json"] = p

    # 8. TRIZ complete report (same session graph; API parity)
    p = out_dir / "run_output_e2e_triz_complete.json"
    run_e2e_triz_complete(p, text)
    written["run_output_e2e_triz_complete.json"] = p

    # 9. Clinical session topology (segmented windows)
    p = out_dir / "run_output_e2e_session_topology.json"
    run_e2e_session_topology(p, text)
    written["run_output_e2e_session_topology.json"] = p

    # 10. TFP smoke: batch structural + session stages + speaker-aware (testing collateral)
    p = out_dir / "run_output_e2e_tfp_smoke.json"
    run_e2e_tfp_smoke(p, primary_text=text)
    written["run_output_e2e_tfp_smoke.json"] = p

    # 10b. Hex microstructure + Option A + TFP provenance (primary text + smoke sessions)
    p_hex = out_dir / "run_output_e2e_hex_microstructure_tfp.json"
    run_e2e_hex_microstructure_tfp(p_hex, text)
    written["run_output_e2e_hex_microstructure_tfp.json"] = p_hex

    # 10c. Sealed stack: hex bridge + local microphysics + F/area + product signals + HSPR index
    p_sealed = out_dir / "run_output_e2e_sealed_multiscale.json"
    run_e2e_sealed_multiscale(p_sealed, text)
    written["run_output_e2e_sealed_multiscale.json"] = p_sealed

    if os.environ.get("HESPERIA_E2E_DLCR", "").strip().lower() in ("1", "true", "yes", "on"):
        p_dlcr = out_dir / E2E_OUTPUT_DLCR
        run_e2e_dlcr(p_dlcr, text)
        written[E2E_OUTPUT_DLCR] = p_dlcr

    # 11. Capability matrix: shipping stages, clinical, NLP, TRIZ core, product, baselines, topology
    p = out_dir / "run_output_e2e_capability_matrix.json"
    run_e2e_capability_matrix(p, text)
    written["run_output_e2e_capability_matrix.json"] = p

    # 11a–11d. Semantic field (ontology → matrices) + HCI calibration artifacts
    p_sf = out_dir / "run_output_e2e_semantic_field.json"
    run_e2e_semantic_field(p_sf)
    written["run_output_e2e_semantic_field.json"] = p_sf
    written.update(run_e2e_field_calibration_bundle(out_dir))
    for _fc in (
        "run_output_e2e_field_calibration.json",
        "run_output_e2e_field_calibration_best.json",
        "run_output_e2e_field_calibration_topk.json",
    ):
        if _fc in written:
            _post_envelope_e2e_file(written[_fc], ["runtime.semantic_field.run_field_calibration"])

    from hesperia.extensions.dynamics.e2e_bridge import run_field_dynamics_e2e_artifact
    from hesperia.extensions.dynamics.phase1 import field_dynamics_enabled

    if field_dynamics_enabled():
        assets = _HESPERIA / "assets" / "lexicon" / "curated"
        _prev_sf = os.environ.get("HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1")
        try:
            os.environ["HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1"] = "1"
            fd = run_field_dynamics_e2e_artifact(text, assets, out_dir)
        finally:
            if _prev_sf is None:
                os.environ.pop("HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1", None)
            else:
                os.environ["HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1"] = _prev_sf
        pfd = out_dir / E2E_OUTPUT_FIELD_DYNAMICS
        pfd.parent.mkdir(parents=True, exist_ok=True)
        _write_e2e_json(pfd, _round_floats(fd), ["hesperia.extensions.dynamics"])
        written[E2E_OUTPUT_FIELD_DYNAMICS] = pfd

    return written


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Run all e2e flows; write multiple outputs to assets/artifacts/e2e/.")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_E2E_DIR, help="Output directory for e2e artifacts")
    ap.add_argument("--text", default=None, help="Input text for sentence/L1–L9/R1–R4 flows")
    ap.add_argument(
        "--calibration-batch-n",
        type=int,
        default=None,
        metavar="N",
        help="Sentences for calibration structural+summary artifacts (default: env HESPERIA_E2E_CALIBRATION_BATCH_N or 100)",
    )
    args = ap.parse_args()

    if args.calibration_batch_n is not None:
        os.environ["HESPERIA_E2E_CALIBRATION_BATCH_N"] = str(max(1, args.calibration_batch_n))

    try:
        written = run_all(out_dir=args.out_dir, text=args.text)
    except Exception as e:
        print(f"E2E run failed: {e}", file=sys.stderr)
        return 1

    for name, path in written.items():
        print(path.resolve(), file=sys.stderr)
    print("e2e_run_ok", len(written), "outputs", file=sys.stderr)
    from hesperia.extensions.dynamics.phase1 import field_dynamics_enabled as _fd_on

    extra = " + field_dynamics" if _fd_on() else ""
    print(
        f"Order: docs/E2E_RUN_ORDER.md | outputs: assets/artifacts/e2e/E2E_OUTPUTS.md{extra}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
