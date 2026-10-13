#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Repo root on sys.path: this script lives under tools/openai_calibration/, two levels below
# root, but its own directory (already on sys.path[0] for direct execution) only satisfies the
# same-dir openai_calibration_utils import below, not the repo-root-relative sphere.* one.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openai_calibration_utils import (
    DEFAULT_OPENAI_MODEL,
    StructuredCall,
    load_jsonl,
    log_stderr,
    log_tool_banner,
    log_tool_progress,
    save_json,
    timestamp_dir,
)
from sphere.calibration.llm_calibration import call_governed_calibration


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(x: Any) -> str | None:
    return x if isinstance(x, str) and x else None


def _segment_text(row: dict[str, Any]) -> str | None:
    for k in ("text", "segment_text", "segment", "content"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


_A_RE = re.compile(r"^A([1-9]|10)$")


def _area_sort_key(a: str) -> tuple[int, str]:
    m = _A_RE.match(a)
    if not m:
        return (999, a)
    return (int(m.group(1)), a)


def _entropy(p: list[float]) -> float:
    eps = 1e-12
    return float(-sum((x + eps) * math.log(x + eps) for x in p))


def _build_area_schema(area_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["segment_id", "areas", "dominant_area"],
        "properties": {
            "segment_id": {"type": "string"},
            "areas": {
                "type": "object",
                "additionalProperties": False,
                "required": area_ids,
                "properties": {a: {"type": "number", "minimum": 0.0, "maximum": 1.0} for a in area_ids},
            },
            "dominant_area": {"type": "string", "enum": area_ids},
        },
    }


def _load_tfp_values_list(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "docs" / "specs" / "TFP_VALUES_LIST"
    if not p.is_file():
        return {"found": False}
    txt = p.read_text(encoding="utf-8")
    knob_doc = "docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md" if "TFP_CALIBRATION_KNOBS_v0_1.md" in txt else None
    return {"found": True, "knob_doc": knob_doc}


def main() -> int:
    ap = argparse.ArgumentParser(description="OpenAI-backed concepts→areas calibration (diagnostics-only).")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, default=Path("data/calibration_corpus.jsonl"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0, help="Cap corpus rows (0 = all)")
    ap.add_argument("--session-id", type=str, default=None, help="Optional corpus/session filter")
    ap.add_argument("--model", type=str, default=DEFAULT_OPENAI_MODEL)
    ap.add_argument("--areas", type=str, default=None, help="Comma-separated override (default: A1..A10 from bundle)")
    ap.add_argument("--dry-run", action="store_true", help="No OpenAI; emit uniform distributions")
    ap.add_argument(
        "--progress-every",
        type=int,
        default=1,
        metavar="N",
        help="stderr progress every N segments (0 disables)",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    tfp_values = _load_tfp_values_list(repo_root)

    bundle_dir = args.bundle_dir.resolve()
    stages_path = bundle_dir / "02_session_tfp_stages.json"
    if not stages_path.is_file():
        raise SystemExit(json.dumps({"error": "missing_bundle_artifact", "path": str(stages_path)}))

    corpus_path = args.corpus.resolve()
    if not corpus_path.is_file():
        raise SystemExit(json.dumps({"error": "missing_corpus", "path": str(corpus_path)}))

    out_dir = args.out.resolve() if args.out else timestamp_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    stages = _read_json(stages_path)
    stage_rows = stages.get("session_tfp_stages")
    if not isinstance(stage_rows, list) or not stage_rows:
        raise SystemExit(json.dumps({"error": "invalid_stages", "path": str(stages_path)}))

    by_session: dict[str, dict[str, Any]] = {}
    area_union: set[str] = set()
    for r in stage_rows:
        if not isinstance(r, dict):
            continue
        sid = _as_str(r.get("session_id"))
        if sid:
            by_session[sid] = r
        at = r.get("areas_top")
        if isinstance(at, dict):
            for k in at.keys():
                if isinstance(k, str) and _A_RE.match(k):
                    area_union.add(k)

    if args.areas:
        area_ids = [x.strip() for x in args.areas.split(",") if x.strip()]
    else:
        area_ids = sorted(area_union or {f"A{i}" for i in range(1, 11)}, key=_area_sort_key)

    schema = _build_area_schema(area_ids)
    cfg = StructuredCall(model=args.model)

    corpus = load_jsonl(corpus_path)
    if args.limit and args.limit > 0:
        corpus = corpus[: args.limit]

    filtered: list[dict[str, Any]] = []
    for row in corpus:
        sid = _as_str(row.get("session_id")) or _as_str(row.get("session"))
        if args.session_id and sid != args.session_id:
            continue
        if sid and sid in by_session:
            filtered.append(row)
    if args.session_id and not filtered:
        raise SystemExit(
            json.dumps(
                {
                    "error": "no_corpus_rows_for_session",
                    "session_id": args.session_id,
                    "bundle_sessions": sorted(by_session.keys()),
                }
            )
        )
    if not filtered:
        # Fallback: if corpus has no session_id, assume single-session bundle.
        if len(by_session) == 1:
            only_sid = next(iter(by_session.keys()))
            for r in corpus:
                r2 = dict(r)
                r2.setdefault("session_id", only_sid)
                filtered.append(r2)
        else:
            raise SystemExit(
                json.dumps(
                    {
                        "error": "corpus_rows_missing_session_id",
                        "hint": "Add session_id per row or pass --session-id",
                        "bundle_sessions": sorted(by_session.keys()),
                    }
                )
            )

    def _eligible_area_row(row: dict[str, Any]) -> tuple[str, str, str] | None:
        sid = _as_str(row.get("session_id")) or _as_str(row.get("session"))
        if not sid or sid not in by_session:
            return None
        seg_id = _as_str(row.get("segment_id")) or _as_str(row.get("id")) or _as_str(row.get("uid"))
        txt = _segment_text(row)
        if not seg_id or not txt:
            return None
        return sid, seg_id, txt

    total_segments = sum(1 for row in filtered if _eligible_area_row(row) is not None)
    log_tool_banner(
        "openai_calibrate_areas",
        model=args.model,
        dry_run=bool(args.dry_run),
        segments=total_segments,
        areas=len(area_ids),
        out_dir=str(out_dir),
    )

    preds_path = out_dir / "area_openai_segments.jsonl"
    with preds_path.open("w", encoding="utf-8") as fh:
        per_session_scores: dict[str, list[list[float]]] = defaultdict(list)
        per_session_dominant: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        uniform = [1.0 / len(area_ids) for _ in area_ids]

        seg_done = 0
        for row in filtered:
            el = _eligible_area_row(row)
            if not el:
                continue
            sid, seg_id, text = el

            if args.dry_run:
                areas_vec = list(uniform)
                dom = area_ids[0]
                out_obj = {"segment_id": seg_id, "areas": {a: areas_vec[i] for i, a in enumerate(area_ids)}, "dominant_area": dom}
            else:
                task_instructions = (
                    "You classify a transcript segment into TFP areas.\n"
                    "Return JSON matching the schema.\n"
                    "Provide a probability-like distribution (0..1) over the areas; values should sum to ~1.\n"
                    "Pick dominant_area as the argmax."
                )
                out_obj = call_governed_calibration(
                    tool="areas",
                    task_instructions=task_instructions,
                    substrate={
                        "segment_id": seg_id,
                        "text": text,
                        "area_ids": area_ids,
                    },
                    schema=schema,
                    cfg=cfg,
                    dry_run=False,
                )

            areas = out_obj.get("areas")
            if not isinstance(areas, dict):
                continue

            vec = []
            for a in area_ids:
                v = areas.get(a)
                vec.append(float(v) if isinstance(v, (int, float)) else 0.0)

            # Normalize defensively for downstream comparability.
            s = sum(vec)
            if s > 0:
                vec = [v / s for v in vec]
            else:
                vec = list(uniform)

            dom = out_obj.get("dominant_area")
            if dom not in area_ids:
                dom = area_ids[max(range(len(vec)), key=lambda i: (vec[i], -i))]
            per_session_scores[sid].append(vec)
            per_session_dominant[sid][dom] += 1

            fh.write(
                json.dumps(
                    {
                        "session_id": sid,
                        "segment_id": seg_id,
                        "areas": {a: vec[i] for i, a in enumerate(area_ids)},
                        "dominant_area": dom,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

            seg_done += 1
            log_tool_progress(
                "openai_calibrate_areas",
                seg_done,
                total_segments,
                every=args.progress_every,
                detail=f"session={sid} segment={seg_id} dominant={dom}",
            )

    # Aggregate + compare to bundle session-level areas_top.
    session_reports: list[dict[str, Any]] = []
    dom_agree = 0
    dom_total = 0
    entropy_deltas: list[float] = []
    inflation: list[float] = []

    for sid, scores in sorted(per_session_scores.items()):
        if not scores:
            continue
        mean = [sum(v[i] for v in scores) / len(scores) for i in range(len(area_ids))]
        # Hesperia areas_top may not be normalized.
        hes = by_session[sid].get("areas_top")
        hes_vec = [0.0 for _ in area_ids]
        if isinstance(hes, dict):
            for i, a in enumerate(area_ids):
                v = hes.get(a)
                if isinstance(v, (int, float)):
                    hes_vec[i] = float(v)
        # Normalize and compute.
        s = sum(hes_vec)
        if s > 0:
            hes_vec = [v / s for v in hes_vec]
        else:
            hes_vec = [1.0 / len(area_ids) for _ in area_ids]

        openai_dom = area_ids[max(range(len(mean)), key=lambda i: (mean[i], -i))]
        hes_dom = area_ids[max(range(len(hes_vec)), key=lambda i: (hes_vec[i], -i))]

        dom_total += 1
        if openai_dom == hes_dom:
            dom_agree += 1

        e_openai = _entropy(mean)
        e_hes = _entropy(hes_vec)
        entropy_deltas.append(e_openai - e_hes)

        # "Multi-area inflation": extra mass outside dominant.
        inflation.append(1.0 - max(mean))

        session_reports.append(
            {
                "session_id": sid,
                "openai_areas_mean": {a: mean[i] for i, a in enumerate(area_ids)},
                "hesperia_areas_top_norm": {a: hes_vec[i] for i, a in enumerate(area_ids)},
                "openai_dominant_area": openai_dom,
                "hesperia_dominant_area": hes_dom,
                "dominant_agrees": openai_dom == hes_dom,
                "entropy_openai": e_openai,
                "entropy_hesperia": e_hes,
                "dominance_openai": max(mean),
                "dominance_hesperia": max(hes_vec),
                "multi_area_inflation": 1.0 - max(mean),
            }
        )

    report = {
        "tool": "openai_calibrate_areas.py",
        "bundle_dir": str(bundle_dir),
        "corpus": str(corpus_path),
        "out_dir": str(out_dir),
        "openai": {"model": args.model, "temperature": 0, "dry_run": bool(args.dry_run)},
        "areas": area_ids,
        "tfp_values_list": tfp_values,
        "metrics": {
            "sessions_evaluated": dom_total,
            "dominant_area_agreement_rate": (dom_agree / dom_total) if dom_total else 0.0,
            "entropy_delta_mean": (sum(entropy_deltas) / len(entropy_deltas)) if entropy_deltas else 0.0,
            "multi_area_inflation_mean": (sum(inflation) / len(inflation)) if inflation else 0.0,
        },
        "sessions": session_reports,
        "suggestions": {
            "softmax_temperature": 0.7,
            "enable_area_competition": True,
            "aggregation_adjustments": [
                {
                    "knob": "evidence_volume_normalize",
                    "why": "If OpenAI entropy is lower than Hesperia, normalize evidence volume to avoid over-confident dominance.",
                },
                {
                    "knob": "per_concept_score_cap",
                    "why": "If OpenAI dominance is consistently lower, cap per-concept spikes less aggressively or adjust scoring caps.",
                },
                {
                    "knob": "use_log1p_concept_scores",
                    "why": "If Hesperia over-inflates multi-area mass, log1p can reduce heavy-tail concepts.",
                },
            ],
        },
        "artifacts": {
            "openai_segments_jsonl": str(preds_path),
            "report_json": str(out_dir / "area_calibration_report.json"),
        },
    }

    save_json(out_dir / "area_calibration_report.json", report)
    m = report["metrics"]
    log_stderr(
        f"[openai_calibrate_areas] done sessions={m['sessions_evaluated']} "
        f"dom_agree_rate={m['dominant_area_agreement_rate']:.3f}"
    )
    print(json.dumps({"out_dir": str(out_dir), "report": str(out_dir / "area_calibration_report.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
