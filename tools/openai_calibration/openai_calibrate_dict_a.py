#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

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


def _rankdata(values: list[float]) -> list[float]:
    """
    Dense ranks with average for ties (deterministic).
    """
    idx = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0] * len(values)
    i = 0
    r = 1
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and values[idx[j + 1]] == values[idx[i]]:
            j += 1
        avg = (r + (r + (j - i))) / 2.0
        for k in range(i, j + 1):
            ranks[idx[k]] = avg
        r += (j - i) + 1
        i = j + 1
    return ranks


def _pearson(a: Iterable[float], b: Iterable[float]) -> float:
    av = list(a)
    bv = list(b)
    if len(av) != len(bv) or not av:
        return 0.0
    ma = sum(av) / len(av)
    mb = sum(bv) / len(bv)
    da = [x - ma for x in av]
    db = [y - mb for y in bv]
    num = sum(x * y for x, y in zip(da, db, strict=True))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    if den == 0.0:
        return 0.0
    return float(num / den)


def _spearman(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return _pearson(_rankdata(a), _rankdata(b))


def _load_tfp_values_list(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "docs" / "specs" / "TFP_VALUES_LIST"
    if not p.is_file():
        return {"found": False}
    txt = p.read_text(encoding="utf-8")
    knob_doc = "docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md" if "TFP_CALIBRATION_KNOBS_v0_1.md" in txt else None
    return {
        "found": True,
        "knob_doc": knob_doc,
        "mentions": {
            "run_tfp_file_pipeline": "runtime/pipeline/run_tfp_file_pipeline.py" in txt,
            "gena_tfp_bundle_run": "tools/gena_tfp_bundle_run.py" in txt,
            "tfp_api_calibration_one_shot": "tools/tfp_api_calibration_one_shot.py" in txt,
        },
    }


def _concept_catalog_from_dlcr_session(dlcr_session: dict[str, Any]) -> list[str]:
    out: set[str] = set()
    cw = dlcr_session.get("concept_weights")
    if isinstance(cw, dict):
        for k in cw.keys():
            if isinstance(k, str) and k:
                out.add(k)
    spans = dlcr_session.get("span_resolutions")
    if isinstance(spans, list):
        for sp in spans:
            if isinstance(sp, dict):
                cid = _as_str(sp.get("winning_concept_id"))
                if cid:
                    out.add(cid)
    return sorted(out)


def _dlcr_truth_for_segment(
    dlcr_session: dict[str, Any], seg: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """
    Returns {concept_id: {"polarity": "positive"}} for concepts overlapping the segment span.
    Fallback: session-level concept set.
    """
    explicit = seg.get("dlcr_concepts") or seg.get("expected_concepts")
    if isinstance(explicit, list) and all(isinstance(x, str) for x in explicit):
        return {x: {"polarity": "positive"} for x in explicit if x}

    spans = dlcr_session.get("span_resolutions")
    if not isinstance(spans, list):
        spans = []

    s0 = seg.get("source_char_start")
    s1 = seg.get("source_char_end")
    if isinstance(s0, int) and isinstance(s1, int) and s1 >= s0 and spans:
        picked: dict[str, dict[str, Any]] = {}
        for sp in spans:
            if not isinstance(sp, dict):
                continue
            c0 = sp.get("source_char_start")
            c1 = sp.get("source_char_end")
            if not (isinstance(c0, int) and isinstance(c1, int) and c1 >= c0):
                continue
            overlaps = not (c1 <= s0 or c0 >= s1)
            if not overlaps:
                continue
            cid = _as_str(sp.get("winning_concept_id"))
            if cid:
                picked[cid] = {"polarity": "positive"}
        if picked:
            return picked

    # Fallback: session-level.
    picked2: dict[str, dict[str, Any]] = {}
    for sp in spans:
        if not isinstance(sp, dict):
            continue
        cid = _as_str(sp.get("winning_concept_id"))
        if cid:
            picked2[cid] = {"polarity": "positive"}
    return picked2


DICT_A_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["segment_id", "concepts"],
    "properties": {
        "segment_id": {"type": "string"},
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["concept_id", "present", "polarity", "confidence"],
                "properties": {
                    "concept_id": {"type": "string"},
                    "present": {"type": "boolean"},
                    "polarity": {"type": "string", "enum": ["positive", "negated", "uncertain"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
        },
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description="OpenAI-backed Dict-A calibration (diagnostics-only).")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, default=Path("data/calibration_corpus.jsonl"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0, help="Cap corpus rows (0 = all)")
    ap.add_argument("--session-id", type=str, default=None, help="Optional corpus/session filter")
    ap.add_argument("--model", type=str, default=DEFAULT_OPENAI_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="No OpenAI; emit empty predictions")
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
    dlcr_path = bundle_dir / "04_dlcr_full.json"
    if not dlcr_path.is_file():
        raise SystemExit(json.dumps({"error": "missing_bundle_artifact", "path": str(dlcr_path)}))

    corpus_path = args.corpus.resolve()
    if not corpus_path.is_file():
        raise SystemExit(json.dumps({"error": "missing_corpus", "path": str(corpus_path)}))

    out_dir = args.out.resolve() if args.out else timestamp_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    dlcr = _read_json(dlcr_path)
    sessions = dlcr.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise SystemExit(json.dumps({"error": "invalid_dlcr", "path": str(dlcr_path)}))

    dlcr_by_session_id: dict[str, dict[str, Any]] = {}
    for s in sessions:
        if not isinstance(s, dict):
            continue
        sid = _as_str(s.get("session_id"))
        if sid:
            dlcr_by_session_id[sid] = s

    corpus = load_jsonl(corpus_path)
    if args.limit and args.limit > 0:
        corpus = corpus[: args.limit]

    # Filter corpus rows to those compatible with the bundle.
    filtered: list[dict[str, Any]] = []
    for row in corpus:
        sid = _as_str(row.get("session_id")) or _as_str(row.get("session"))
        if args.session_id and sid != args.session_id:
            continue
        if sid and sid in dlcr_by_session_id:
            filtered.append(row)
    if args.session_id and not filtered:
        raise SystemExit(
            json.dumps(
                {
                    "error": "no_corpus_rows_for_session",
                    "session_id": args.session_id,
                    "bundle_sessions": sorted(dlcr_by_session_id.keys()),
                }
            )
        )
    if not filtered:
        # Fallback: if corpus has no session_id, assume single-session bundle.
        if len(dlcr_by_session_id) == 1:
            only_sid = next(iter(dlcr_by_session_id.keys()))
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
                        "bundle_sessions": sorted(dlcr_by_session_id.keys()),
                    }
                )
            )

    def _eligible_row(row: dict[str, Any]) -> tuple[str, str, str] | None:
        sid = _as_str(row.get("session_id")) or _as_str(row.get("session"))
        if not sid or sid not in dlcr_by_session_id:
            return None
        seg_id = _as_str(row.get("segment_id")) or _as_str(row.get("id")) or _as_str(row.get("uid"))
        txt = _segment_text(row)
        if not seg_id or not txt:
            return None
        return sid, seg_id, txt

    total_segments = sum(1 for row in filtered if _eligible_row(row) is not None)
    log_tool_banner(
        "openai_calibrate_dict_a",
        model=args.model,
        dry_run=bool(args.dry_run),
        segments=total_segments,
        out_dir=str(out_dir),
    )

    cfg = StructuredCall(model=args.model)
    predictions_jsonl = out_dir / "dict_a_openai_segments.jsonl"
    pred_fh = predictions_jsonl.open("w", encoding="utf-8")

    fp = 0
    fn = 0
    neg_err = 0
    rank_mismatch: list[float] = []
    per_concept = defaultdict(lambda: {"false_pos": 0, "false_neg": 0, "negation_err": 0, "n": 0})

    examples: dict[str, list[dict[str, Any]]] = {"false_positives": [], "false_negatives": [], "negation_errors": []}

    seg_done = 0
    for row in filtered:
        el = _eligible_row(row)
        if not el:
            continue
        sid, seg_id, text = el

        dlcr_sess = dlcr_by_session_id[sid]
        catalog = _concept_catalog_from_dlcr_session(dlcr_sess)
        truth = _dlcr_truth_for_segment(dlcr_sess, row)
        truth_set = set(truth.keys())

        if args.dry_run:
            out_obj = {"segment_id": seg_id, "concepts": []}
        else:
            task_instructions = (
                "You are calibrating a TFP lexical concept extractor.\n"
                "Return JSON that matches the provided schema.\n"
                "Only use concept_id values from the ALLOWED_CONCEPT_IDS list.\n"
                "If a concept is not clearly present, do not include it."
            )
            out_obj = call_governed_calibration(
                tool="dict_a",
                task_instructions=task_instructions,
                substrate={
                    "segment_id": seg_id,
                    "text": text,
                    "allowed_concept_ids": catalog,
                },
                schema=DICT_A_SCHEMA,
                cfg=cfg,
                dry_run=False,
            )

        pred_fh.write(json.dumps({"session_id": sid, **out_obj}, ensure_ascii=False, sort_keys=True) + "\n")

        concepts = out_obj.get("concepts")
        if not isinstance(concepts, list):
            concepts = []
        pred_present: dict[str, dict[str, Any]] = {}
        for c in concepts:
            if not isinstance(c, dict):
                continue
            cid = _as_str(c.get("concept_id"))
            if not cid:
                continue
            if cid not in catalog:
                continue
            if c.get("present") is not True:
                continue
            pol = c.get("polarity")
            conf = c.get("confidence")
            if pol not in {"positive", "negated", "uncertain"}:
                pol = "uncertain"
            if not isinstance(conf, (int, float)):
                conf = 0.0
            pred_present[cid] = {"polarity": pol, "confidence": float(conf)}

        pred_set = set(pred_present.keys())

        seg_fp = sorted(pred_set - truth_set)
        seg_fn = sorted(truth_set - pred_set)
        fp += len(seg_fp)
        fn += len(seg_fn)

        for cid in seg_fp:
            per_concept[cid]["false_pos"] += 1
            per_concept[cid]["n"] += 1
        for cid in seg_fn:
            per_concept[cid]["false_neg"] += 1
            per_concept[cid]["n"] += 1

        seg_neg = []
        for cid in sorted(pred_set & truth_set):
            pol = pred_present[cid]["polarity"]
            if pol != "positive":
                neg_err += 1
                per_concept[cid]["negation_err"] += 1
                per_concept[cid]["n"] += 1
                seg_neg.append({"concept_id": cid, "polarity": pol})

        cw = dlcr_sess.get("concept_weights")
        if isinstance(cw, dict) and cw:
            shared = [cid for cid in pred_set if cid in cw and isinstance(cw.get(cid), (int, float))]
            if len(shared) >= 3:
                a = [pred_present[cid]["confidence"] for cid in shared]
                b = [float(cw[cid]) for cid in shared]
                rank_mismatch.append(1.0 - _spearman(a, b))

        if seg_fp and len(examples["false_positives"]) < 10:
            examples["false_positives"].append(
                {"session_id": sid, "segment_id": seg_id, "predicted_only": seg_fp}
            )
        if seg_fn and len(examples["false_negatives"]) < 10:
            examples["false_negatives"].append(
                {"session_id": sid, "segment_id": seg_id, "missing_truth": seg_fn}
            )
        if seg_neg and len(examples["negation_errors"]) < 10:
            examples["negation_errors"].append({"session_id": sid, "segment_id": seg_id, "concepts": seg_neg})

        seg_done += 1
        log_tool_progress(
            "openai_calibrate_dict_a",
            seg_done,
            total_segments,
            every=args.progress_every,
            detail=f"session={sid} segment={seg_id}",
        )

    pred_fh.close()

    # Suggestions (knobs) — only diagnostics, no code edits.
    inc = []
    dec = []
    neg = []
    for cid, stats in sorted(per_concept.items(), key=lambda kv: (-(kv[1]["false_neg"]), kv[0])):
        if stats["false_neg"] >= 2:
            inc.append({"concept_id": cid, "count": stats["false_neg"], "knob": "Dict-A YAML marker weights"})
    for cid, stats in sorted(per_concept.items(), key=lambda kv: (-(kv[1]["false_pos"]), kv[0])):
        if stats["false_pos"] >= 2:
            dec.append({"concept_id": cid, "count": stats["false_pos"], "knob": "Dict-A YAML marker weights"})
    for cid, stats in sorted(per_concept.items(), key=lambda kv: (-(kv[1]["negation_err"]), kv[0])):
        if stats["negation_err"] >= 1:
            neg.append(
                {
                    "concept_id": cid,
                    "count": stats["negation_err"],
                    "knob": "DLCR negation window/multiplier",
                }
            )

    report = {
        "tool": "openai_calibrate_dict_a.py",
        "bundle_dir": str(bundle_dir),
        "corpus": str(corpus_path),
        "out_dir": str(out_dir),
        "openai": {"model": args.model, "temperature": 0, "dry_run": bool(args.dry_run)},
        "tfp_values_list": tfp_values,
        "metrics": {
            "segments_evaluated": sum(1 for _ in open(predictions_jsonl, encoding="utf-8")),
            "false_positives": fp,
            "false_negatives": fn,
            "negation_errors": neg_err,
            "confidence_rank_mismatch_mean": (sum(rank_mismatch) / len(rank_mismatch)) if rank_mismatch else 0.0,
        },
        "examples": examples,
        "suggestions": {
            "increase_weight": inc,
            "decrease_weight": dec,
            "add_negation_rules": neg,
            "remove_markers": [
                {"concept_id": x["concept_id"], "knob": "Marker pruning / resolver policy"} for x in dec[:20]
            ],
        },
        "artifacts": {
            "openai_predictions_jsonl": str(predictions_jsonl),
            "report_json": str(out_dir / "dict_a_report.json"),
        },
    }

    save_json(out_dir / "dict_a_report.json", report)
    m = report["metrics"]
    log_stderr(
        f"[openai_calibrate_dict_a] done segments={m['segments_evaluated']} "
        f"fp={m['false_positives']} fn={m['false_negatives']} neg_err={m['negation_errors']}"
    )
    print(json.dumps({"out_dir": str(out_dir), "report": str(out_dir / "dict_a_report.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
