#!/usr/bin/env python3
# HESPERIA — Shipping CLI. Single entry point; calls only service façades.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Sealed CLI entry point. Commands: analyze, compare, batch (alias batch-analyze).
Uses only runtime.services (analysis_service); no internal layers or topology.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _runtime_version_fallback() -> str:
    try:
        from hesperia.system.version import get_system_version

        return get_system_version()
    except Exception:
        return "unknown"


def _assets_root(repo_root: Path | None) -> Path:
    if repo_root is not None and repo_root.is_dir():
        d = repo_root / "assets" / "lexicon" / "curated"
        if d.is_dir():
            return d
    return Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"


def _cmd_analyze(args: object) -> int:
    text = getattr(args, "text", "") or ""
    out_path = getattr(args, "out", None)
    assets = getattr(args, "assets", None)
    assets_path = Path(assets) if assets else _assets_root(Path(__file__).resolve().parents[2])

    from runtime.services.analysis_service import run_structural_analysis

    summary_payload = run_structural_analysis(text, assets_root=assets_path, stages="full")
    from runtime.shipping.schema_guard import validate_against_public_schema
    validate_against_public_schema(summary_payload)
    out = json.dumps(summary_payload, indent=2, ensure_ascii=False, sort_keys=True)
    if out_path:
        from runtime.artifact_writer import write_public_json
        write_public_json(Path(out_path), summary_payload)
    print(out)
    return 0


def _cmd_compare(args: object) -> int:
    text1 = getattr(args, "text1", "") or ""
    text2 = getattr(args, "text2", "") or ""
    out_path = getattr(args, "out", None)
    assets = getattr(args, "assets", None)
    assets_path = Path(assets) if assets else _assets_root(Path(__file__).resolve().parents[2])

    from runtime.services.analysis_service import run_structural_analysis

    r1 = run_structural_analysis(text1, assets_root=assets_path, stages="full")
    r2 = run_structural_analysis(text2, assets_root=assets_path, stages="full")

    # Public-safe comparison: dominant domain match, confidence summary, no internal coordinates
    d1 = r1.get("L7") or {}
    d2 = r2.get("L7") or {}
    dom1 = (r1.get("usf") or {}).get("raw_metrics") or {}
    dom2 = (r2.get("usf") or {}).get("raw_metrics") or {}
    comparison = {
        "run": "compare",
        "text1_preview": text1[:80],
        "text2_preview": text2[:80],
        "summary1_trust": d1.get("OUTPUT_TRUST_TAG"),
        "summary2_trust": d2.get("OUTPUT_TRUST_TAG"),
        "result1_trust": d1.get("OUTPUT_TRUST_TAG"),
        "result2_trust": d2.get("OUTPUT_TRUST_TAG"),
        "dominant_match": _same_dominant(dom1, dom2),
        "confidence_delta": _confidence_delta(d1, d2),
    }
    from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile
    from runtime.shipping.schema_guard import validate_against_public_schema

    wrapped = attach_public_output_metadata(
        comparison,
        calibration_profile=default_calibration_profile(),
        pipeline_version=api_pipeline_version(),
        execution_flow_version=api_pipeline_version(),
        orchestration_mode="CLI_SYNC",
    )
    validate_against_public_schema(wrapped)
    out = json.dumps(wrapped, indent=2, ensure_ascii=False, sort_keys=True)
    if out_path:
        from runtime.artifact_writer import write_public_json
        write_public_json(Path(out_path), wrapped)
    print(out)
    return 0


def _same_dominant(metrics1: dict, metrics2: dict) -> bool:
    v1 = metrics1.get("macro_domain_vector") or metrics1.get("dominant_macro_domain")
    v2 = metrics2.get("macro_domain_vector") or metrics2.get("dominant_macro_domain")
    if isinstance(v1, list) and isinstance(v2, list):
        i1 = max(range(len(v1)), key=lambda i: v1[i]) if v1 else -1
        i2 = max(range(len(v2)), key=lambda i: v2[i]) if v2 else -1
        return i1 == i2
    return False


def _confidence_delta(d1: dict, d2: dict) -> str:
    c1 = d1.get("TRUST_TIER") or d1.get("OUTPUT_TRUST_TAG") or ""
    c2 = d2.get("TRUST_TIER") or d2.get("OUTPUT_TRUST_TAG") or ""
    if c1 == c2:
        return "same"
    return "different"


def _parse_batch_input(data: object) -> tuple[list[str], list[str] | None]:
    """Parse JSON input. Returns (texts, session_ids or None). session_ids only when 'sessions' format."""
    if isinstance(data, list):
        if not data:
            return [], None
        if isinstance(data[0], dict):
            return [t.get("text", "") or "" for t in data], [
                t.get("session_id", f"session_{i}") for i, t in enumerate(data)
            ]
        return [str(x) if x is not None else "" for x in data], None
    if isinstance(data, dict):
        if "sessions" in data:
            sessions = data["sessions"]
            if not sessions:
                return [], None
            return [
                s.get("text", "") or "" for s in sessions
            ], [
                s.get("session_id", f"session_{i}") for i, s in enumerate(sessions)
            ]
        if "texts" in data:
            texts = data["texts"]
            if not texts:
                return [], None
            if isinstance(texts[0], dict):
                return [t.get("text", "") or "" for t in texts], None
            return [str(x) if x is not None else "" for x in texts], None
    return [], None


def _cmd_batch_analyze(args: object) -> int:
    input_path = getattr(args, "input", None)
    texts_argv = getattr(args, "texts", None) or []
    out_path = getattr(args, "out", None)
    assets = getattr(args, "assets", None)
    assets_path = Path(assets) if assets else _assets_root(Path(__file__).resolve().parents[2])

    if input_path:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
        texts, session_ids = _parse_batch_input(data)
    else:
        texts = list(texts_argv) if texts_argv else []
        session_ids = None

    if not texts:
        print("No raw_text entries. Use --input path.json or --texts '...' '...'", file=sys.stderr)
        return 1

    from runtime.services.analysis_service import run_structural_analysis_batch

    results = run_structural_analysis_batch(texts, assets_root=assets_path)
    if session_ids is not None and len(session_ids) == len(results):
        for i, sid in enumerate(session_ids):
            results[i]["session_id"] = sid
    from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile
    from runtime.shipping.schema_guard import validate_against_public_schema

    wrapped = attach_public_output_metadata(
        {},
        calibration_profile=default_calibration_profile(),
        pipeline_version=api_pipeline_version(),
        execution_flow_version=api_pipeline_version(),
        orchestration_mode="CLI_BATCH",
    )
    wrapped["payload"] = results
    validate_against_public_schema(wrapped)
    out = json.dumps(wrapped, indent=2, ensure_ascii=False, sort_keys=True)
    if out_path:
        from runtime.artifact_writer import write_public_json
        write_public_json(Path(out_path), results)
    print(out)
    return 0


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    ap = argparse.ArgumentParser(
        prog="hesperia",
        description="Structural analysis. Commands: analyze, compare, batch | batch-analyze, router-inquire.",
    )
    ap.add_argument("--version", action="store_true", help="Show runtime version and build info.")
    ap.add_argument("--assets", type=str, default=None, help="Path to lexicon assets (default: repo/assets/lexicon/curated)")
    sub = ap.add_subparsers(dest="command", required=False)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Run structural analysis on one text.")
    p_analyze.add_argument("--text", type=str, default="", help="Input text to analyze.")
    p_analyze.add_argument("--out", type=str, default=None, help="Write result JSON to this path.")
    p_analyze.set_defaults(_run=_cmd_analyze)

    # compare
    p_compare = sub.add_parser("compare", help="Compare two texts (structural emphasis and confidence).")
    p_compare.add_argument("--text1", type=str, default="", help="First text.")
    p_compare.add_argument("--text2", type=str, default="", help="Second text.")
    p_compare.add_argument("--out", type=str, default=None, help="Write comparison JSON to this path.")
    p_compare.set_defaults(_run=_cmd_compare)

    def _add_batch_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--input", type=str, default=None, help="JSON file: list of strings, or {texts: [...]}, or {sessions: [{session_id, text}, ...]}.")
        p.add_argument("--texts", type=str, nargs="*", default=[], help="Texts as arguments.")
        p.add_argument("--out", type=str, default=None, help="Write results JSON to this path.")

    p_batch = sub.add_parser("batch-analyze", help="Run structural analysis on multiple texts.")
    _add_batch_args(p_batch)
    p_batch.set_defaults(_run=_cmd_batch_analyze)

    p_batch_alias = sub.add_parser("batch", help="Alias for batch-analyze.")
    _add_batch_args(p_batch_alias)
    p_batch_alias.set_defaults(_run=_cmd_batch_analyze)

    def _cmd_router_inquire(args: object) -> int:
        text = getattr(args, "text", "") or ""
        out_path = getattr(args, "out", None)
        context_json = getattr(args, "context_json", None)
        assets = getattr(args, "assets", None)
        assets_path = Path(assets) if assets else _assets_root(Path(__file__).resolve().parents[2])
        from runtime.services.tool_inquiry_service import (
            load_context_packet_json,
            run_tool_inquiry,
        )

        ctx = load_context_packet_json(Path(context_json)) if context_json else None
        # FPF-HSR-11/12: thinking_map_outcome travels inside context_packet on the wire (same
        # allowlist convention as the HTTP context_packet field) but run_tool_inquiry() takes it
        # as its own kwarg — extract here, same as runtime/shipping/api_main.py.
        thinking_map_outcome = None
        if ctx is not None:
            ctx = dict(ctx)
            thinking_map_outcome = ctx.pop("thinking_map_outcome", None)
        out = run_tool_inquiry(
            text, assets_path, context_packet=ctx or None, thinking_map_outcome=thinking_map_outcome
        )
        if out_path:
            Path(out_path).write_text(out + "\n", encoding="utf-8")
        print(out)
        return 0

    p_inquire = sub.add_parser(
        "router-inquire",
        help="HSR-V7-07: JSON-only router inquiry packet (no free-form prose).",
    )
    p_inquire.add_argument("--text", type=str, required=True, help="Input text for router envelope.")
    p_inquire.add_argument("--context-json", type=str, default=None, help="Optional context_rag JSON file.")
    p_inquire.add_argument("--out", type=str, default=None, help="Write JSON packet to this path.")
    p_inquire.set_defaults(_run=_cmd_router_inquire)

    args = ap.parse_args()
    if getattr(args, "version", False):
        try:
            from runtime.shipping.version_info import VERSION, COMMIT, BUILD
            print("HESPERIA Runtime")
            print(f"version: {VERSION}")
            print(f"commit: {COMMIT}")
            print(f"build: {BUILD or 'unknown'}")
        except Exception:
            print("HESPERIA Runtime")
            print(f"version: {_runtime_version_fallback()}")
            print("commit: unknown")
            print("build: unknown")
        return 0
    run = getattr(args, "_run", None)
    if run is None:
        ap.print_help()
        return 0
    try:
        return run(args)
    except Exception:
        print("analysis_error: internal_processing_error", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
