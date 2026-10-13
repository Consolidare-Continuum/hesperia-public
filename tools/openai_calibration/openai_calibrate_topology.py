#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

# Repo root on sys.path: this script lives under tools/openai_calibration/, two levels below
# root, but its own directory (already on sys.path[0] for direct execution) only satisfies the
# same-dir openai_calibration_utils import below, not the repo-root-relative sphere.* one.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openai_calibration_utils import (
    DEFAULT_OPENAI_MODEL,
    StructuredCall,
    ema,
    load_jsonl,
    log_tool_banner,
    log_tool_progress,
    log_stderr,
    save_json,
    timestamp_dir,
)
from sphere.calibration.llm_calibration import call_governed_calibration


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(x: Any) -> str | None:
    return x if isinstance(x, str) and x else None


def _pearson(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    num = sum(x * y for x, y in zip(da, db, strict=True))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    if den == 0.0:
        return 0.0
    return float(num / den)


def _diff(x: list[float]) -> list[float]:
    return [x[i + 1] - x[i] for i in range(len(x) - 1)]


def _spike_index(curve: list[float]) -> int | None:
    if len(curve) < 3:
        return None
    d = _diff(curve)
    if not d:
        return None
    return max(range(len(d)), key=lambda i: (abs(d[i]), -i))


def _resample_linear(xs: list[float], n: int) -> list[float]:
    if n <= 0:
        return []
    if not xs:
        return [0.0] * n
    if len(xs) == 1:
        return [float(xs[0])] * n
    if len(xs) == n:
        return [float(v) for v in xs]
    out: list[float] = []
    for i in range(n):
        t = i * (len(xs) - 1) / (n - 1) if n > 1 else 0.0
        j = int(math.floor(t))
        k = min(j + 1, len(xs) - 1)
        w = t - j
        out.append(float(xs[j] * (1.0 - w) + xs[k] * w))
    return out


def _segment_text(row: dict[str, Any]) -> str | None:
    for k in ("text", "segment_text", "segment", "content"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


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


def _load_area_segments_from_jsonl(path: Path) -> dict[str, list[dict[str, Any]]]:
    rows = load_jsonl(path)
    by_session: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sid = _as_str(r.get("session_id"))
        if not sid:
            continue
        by_session.setdefault(sid, []).append(r)
    return by_session


def _load_tfp_values_list(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "docs" / "specs" / "TFP_VALUES_LIST"
    if not p.is_file():
        return {"found": False}
    txt = p.read_text(encoding="utf-8")
    knob_doc = "docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md" if "TFP_CALIBRATION_KNOBS_v0_1.md" in txt else None
    return {"found": True, "knob_doc": knob_doc}


def main() -> int:
    ap = argparse.ArgumentParser(description="OpenAI-backed topology calibration (diagnostics-only).")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, default=Path("data/calibration_corpus.jsonl"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0, help="Cap corpus rows (0 = all)")
    ap.add_argument("--session-id", type=str, default=None, help="Optional corpus/session filter")
    ap.add_argument("--model", type=str, default=DEFAULT_OPENAI_MODEL)
    ap.add_argument("--curve-name", type=str, default="aggression_curve", help="Topology curve field")
    ap.add_argument("--curve-area", type=str, default="A4", help="Area key to build OpenAI curve from")
    ap.add_argument("--area-segments", type=Path, default=None, help="Use existing area_openai_segments.jsonl")
    ap.add_argument("--curve-smooth-alpha", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true", help="No OpenAI; curve derived only if --area-segments is present")
    ap.add_argument(
        "--progress-every",
        type=int,
        default=1,
        metavar="N",
        help="stderr progress every N segment API calls or topology sessions (0 disables)",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    tfp_values = _load_tfp_values_list(repo_root)

    bundle_dir = args.bundle_dir.resolve()
    topo_path = bundle_dir / "09_session_topology.json"
    if not topo_path.is_file():
        raise SystemExit(json.dumps({"error": "missing_bundle_artifact", "path": str(topo_path)}))

    corpus_path = args.corpus.resolve()
    if not corpus_path.is_file() and not args.area_segments:
        raise SystemExit(json.dumps({"error": "missing_corpus", "path": str(corpus_path)}))

    out_dir = args.out.resolve() if args.out else timestamp_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    topo = _read_json(topo_path)
    topo_sessions = topo.get("sessions")
    if not isinstance(topo_sessions, list) or not topo_sessions:
        raise SystemExit(json.dumps({"error": "invalid_topology", "path": str(topo_path)}))

    topo_by_session: dict[str, dict[str, Any]] = {}
    for s in topo_sessions:
        if not isinstance(s, dict):
            continue
        sid = _as_str(s.get("session_id"))
        st = s.get("session_topology")
        if sid and isinstance(st, dict):
            topo_by_session[sid] = st

    # Load / create OpenAI area segments.
    area_segments_path = args.area_segments.resolve() if args.area_segments else (out_dir / "area_openai_segments.jsonl")
    openai_by_session: dict[str, list[dict[str, Any]]] = {}
    if area_segments_path.is_file():
        log_stderr(
            f"[openai_calibrate_topology] using existing area_segments file={area_segments_path} (no segment API calls)"
        )
        openai_by_session = _load_area_segments_from_jsonl(area_segments_path)
    elif args.dry_run:
        raise SystemExit(
            json.dumps({"error": "missing_area_segments", "path": str(area_segments_path), "dry_run": True})
        )
    else:
        # Minimal inline re-run of segment area classification (same schema as openai_calibrate_areas.py).
        area_ids = [f"A{i}" for i in range(1, 11)]
        schema = _build_area_schema(area_ids)
        cfg = StructuredCall(model=args.model)
        corpus = load_jsonl(corpus_path)
        if args.limit and args.limit > 0:
            corpus = corpus[: args.limit]

        def _eligible_topo_row(row: dict[str, Any]) -> tuple[str, str, str] | None:
            sid = _as_str(row.get("session_id")) or _as_str(row.get("session"))
            if args.session_id and sid != args.session_id:
                return None
            if not sid or sid not in topo_by_session:
                return None
            seg_id = _as_str(row.get("segment_id")) or _as_str(row.get("id")) or _as_str(row.get("uid"))
            txt = _segment_text(row)
            if not seg_id or not txt:
                return None
            return sid, seg_id, txt

        total_seg_api = sum(1 for row in corpus if _eligible_topo_row(row) is not None)
        log_tool_banner(
            "openai_calibrate_topology",
            model=args.model,
            segment_api_calls=total_seg_api,
            out_dir=str(out_dir),
        )

        with area_segments_path.open("w", encoding="utf-8") as fh:
            seg_done = 0
            for row in corpus:
                el = _eligible_topo_row(row)
                if not el:
                    continue
                sid, seg_id, text = el
                task_instructions = (
                    "You classify a transcript segment into TFP areas.\n"
                    "Return JSON matching the schema.\n"
                    "Provide a probability-like distribution (0..1) over the areas; values should sum to ~1.\n"
                    "Pick dominant_area as the argmax."
                )
                out_obj = call_governed_calibration(
                    tool="topology",
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
                areas = out_obj.get("areas") if isinstance(out_obj, dict) else None
                if not isinstance(areas, dict):
                    seg_done += 1
                    log_tool_progress(
                        "openai_calibrate_topology",
                        seg_done,
                        total_seg_api,
                        every=args.progress_every,
                        detail=f"session={sid} segment={seg_id} (skip bad schema)",
                    )
                    continue
                vec = []
                for a in area_ids:
                    v = areas.get(a)
                    vec.append(float(v) if isinstance(v, (int, float)) else 0.0)
                s = sum(vec)
                if s > 0:
                    vec = [v / s for v in vec]
                else:
                    vec = [1.0 / len(area_ids) for _ in area_ids]
                dom = out_obj.get("dominant_area")
                if dom not in area_ids:
                    dom = area_ids[max(range(len(vec)), key=lambda i: (vec[i], -i))]
                rec = {
                    "session_id": sid,
                    "segment_id": seg_id,
                    "areas": {a: vec[i] for i, a in enumerate(area_ids)},
                    "dominant_area": dom,
                }
                fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
                openai_by_session.setdefault(sid, []).append(rec)

                seg_done += 1
                log_tool_progress(
                    "openai_calibrate_topology",
                    seg_done,
                    total_seg_api,
                    every=args.progress_every,
                    detail=f"session={sid} segment={seg_id} (area schema)",
                )

    topo_session_items = sorted(topo_by_session.items())
    log_tool_banner(
        "openai_calibrate_topology",
        phase="curve_compare",
        model=args.model,
        bundle_sessions=len(topo_session_items),
        openai_sessions=len(openai_by_session),
        curve=args.curve_name,
        curve_area=args.curve_area,
    )

    reports: list[dict[str, Any]] = []
    overall = {"sessions": 0, "trend_corr_mean": 0.0, "drift_mae_mean": 0.0, "spike_distance_mean": 0.0}
    corr_list: list[float] = []
    mae_list: list[float] = []
    spike_dist: list[float] = []

    for si, (sid, st) in enumerate(topo_session_items, start=1):
        log_tool_progress(
            "openai_calibrate_topology",
            si,
            len(topo_session_items),
            every=args.progress_every,
            detail=f"curve_compare session={sid}",
        )
        if args.session_id and sid != args.session_id:
            continue
        curve = st.get(args.curve_name)
        if not isinstance(curve, list) or not all(isinstance(x, (int, float)) for x in curve):
            continue
        hes_curve = [float(x) for x in curve]
        openai_rows = openai_by_session.get(sid, [])
        openai_curve_raw: list[float] = []
        for r in openai_rows:
            areas = r.get("areas")
            if isinstance(areas, dict) and isinstance(areas.get(args.curve_area), (int, float)):
                openai_curve_raw.append(float(areas[args.curve_area]))
        if not openai_curve_raw:
            continue

        openai_curve_smooth = ema(openai_curve_raw, alpha=args.curve_smooth_alpha) if args.curve_smooth_alpha else openai_curve_raw
        openai_curve = _resample_linear(openai_curve_smooth, len(hes_curve))

        corr = _pearson(hes_curve, openai_curve)
        mae = sum(abs(a - b) for a, b in zip(hes_curve, openai_curve, strict=True)) / len(hes_curve)
        si_h = _spike_index(hes_curve)
        si_o = _spike_index(openai_curve)
        sd = (abs(si_h - si_o) / max(1, len(hes_curve) - 1)) if (si_h is not None and si_o is not None) else 1.0

        corr_list.append(corr)
        mae_list.append(mae)
        spike_dist.append(sd)

        reports.append(
            {
                "session_id": sid,
                "curve_name": args.curve_name,
                "curve_area": args.curve_area,
                "hesperia_curve_len": len(hes_curve),
                "openai_segments": len(openai_curve_raw),
                "trend_corr": corr,
                "drift_mae": mae,
                "spike_index_hesperia": si_h,
                "spike_index_openai": si_o,
                "spike_distance_norm": sd,
            }
        )

    if corr_list:
        overall["sessions"] = len(corr_list)
        overall["trend_corr_mean"] = sum(corr_list) / len(corr_list)
        overall["drift_mae_mean"] = sum(mae_list) / len(mae_list) if mae_list else 0.0
        overall["spike_distance_mean"] = sum(spike_dist) / len(spike_dist) if spike_dist else 0.0

    report = {
        "tool": "openai_calibrate_topology.py",
        "bundle_dir": str(bundle_dir),
        "corpus": str(corpus_path) if corpus_path.is_file() else None,
        "out_dir": str(out_dir),
        "openai": {"model": args.model, "temperature": 0, "dry_run": bool(args.dry_run)},
        "tfp_values_list": tfp_values,
        "inputs": {"area_segments_jsonl": str(area_segments_path)},
        "metrics": overall,
        "sessions": reports,
        "suggestions": {
            "curve_smooth_alpha": 0.2,
            "enable_area_competition": True,
            "adjust_centering": True,
            "knobs": [
                {
                    "knob": "session_topology_run_params",
                    "why": "If OpenAI spikes lead/lag systematically, adjust topology run params (window/step) to align state transitions.",
                },
                {
                    "knob": "CURVE_CALIBRATION_REFERENCE",
                    "why": "If drift is low but correlation is negative, check reference band orientation and centering rules.",
                },
                {
                    "knob": "AREA_CURVE_MAP",
                    "why": "If the wrong area is being tracked (e.g., A4 mismatch), verify the area→curve mapping.",
                },
            ],
        },
        "artifacts": {"report_json": str(out_dir / "topology_report.json")},
    }

    save_json(out_dir / "topology_report.json", report)
    om = report["metrics"]
    log_stderr(
        f"[openai_calibrate_topology] done curve_sessions={om['sessions']} "
        f"corr_mean={om['trend_corr_mean']:.3f} drift_mae_mean={om['drift_mae_mean']:.3f}"
    )
    print(json.dumps({"out_dir": str(out_dir), "report": str(out_dir / "topology_report.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
