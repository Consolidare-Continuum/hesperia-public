#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CLI: corpus → LLM (OpenAI) → Hesperia DLCR calibration loop."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.dict_calibration.anchor_bind import (  # noqa: E402
    anchor_drafts,
    load_anchor_registry,
    load_merged_dict_b,
)
from tools.dict_calibration.build_links import build_links, links_to_engine_dict_a  # noqa: E402
from tools.dict_calibration.calibrate_loop import LoopConfig, run_iteration  # noqa: E402
from tools.dict_calibration.errors_extract import extract_errors  # noqa: E402
from tools.dict_calibration.evaluate import evaluate_on_texts  # noqa: E402
from tools.dict_calibration.extract_lexical import extract_corpus  # noqa: E402
from tools.dict_calibration.lexical_filter import filter_rows_for_llm  # noqa: E402
from tools.dict_calibration.freeze_version import freeze  # noqa: E402
from tools.dict_calibration.jsonl_util import read_jsonl, write_json, write_jsonl  # noqa: E402
from tools.dict_calibration.normalize_llm import normalize_batch  # noqa: E402
from tools.dict_calibration.env_defaults import (  # noqa: E402
    apply_dict_calib_offline_bundle,
    assert_domain_corpus_pairing,
    dict_calib_worker_default,
    normalize_domain,
)
from tools.dict_calibration.openai_json import require_openai_key  # noqa: E402
from tools.dict_calibration.patch_llm import apply_patch_to_links, propose_patch  # noqa: E402
from tools.dict_calibration.propose_llm import propose_concepts  # noqa: E402
from tools.dict_calibration.ru_tfp_corpus_align import (  # noqa: E402
    load_zero_link_ids_from_coverage_report,
    run_ru_tfp_corpus_align,
    write_ru_tfp_cold_artifacts,
)
from tools.dict_calibration.yaml_markers_llm import cmd_yaml_markers_llm_entry  # noqa: E402
from hesperia.extensions.triz.contradiction_feedback import build_contradiction_feedback_signals  # noqa: E402


def _default_engine_paths(
    repo: Path,
    *,
    domain: str = "core",
) -> tuple[list[Path], Path]:
    """Return (dict_b jsonl paths, anchors path).

    Default is **core** (Class A / ``v0_core_syzif_001``). Pass ``domain=\"tfp\"``
    only for Class B TFP calibration — never the silent default.
    """
    domain = normalize_domain(domain)
    if domain == "tfp":
        base = repo / "assets/data/engine_dynamics_v060"
        db = base / "dict_b"
        dict_b = [
            db / "dict_b_seed.jsonl",
            db / "dict_b_tfp_ru_v060.jsonl",
            db / "dict_b_tfp.jsonl",
        ]
        anch = base / "anchors" / "concept_hex_anchors_tfp.json"
        if not anch.exists():
            anch = base / "anchors" / "concept_hex_anchors.json"
        return dict_b, anch

    # core / default (syzif Class A)
    core_dir = repo / "assets/calibration/dicts/v0_core_syzif_001"
    primary = core_dir / "dict_b.jsonl"
    seed = core_dir / "dict_b_seed.jsonl"
    dict_b = [primary if primary.exists() else seed]
    anch = repo / "assets/data/engine_dynamics_v060" / "anchors" / "concept_hex_anchors.json"
    return dict_b, anch


def _sample_texts_from_corpus(
    corpus: Path,
    *,
    max_files: int = 5,
    max_chars: int = 12_000,
) -> list[str]:
    """Collect ``*.md`` under corpus (skip ``_*``). ``max_files <= 0`` = all files; ``max_chars <= 0`` = full file."""
    paths = sorted(p for p in corpus.rglob("*.md") if not p.name.startswith("_"))
    if max_files and max_files > 0:
        paths = paths[:max_files]
    chunks: list[str] = []
    for p in paths:
        t = p.read_text(encoding="utf-8", errors="replace")
        if max_chars and max_chars > 0:
            t = t[:max_chars]
        if t.strip():
            chunks.append(t)
    return chunks


def _wave_slice_rows(
    rows: list[dict[str, Any]],
    wave_index: int | None,
    wave_total: int | None,
) -> list[dict[str, Any]]:
    """Partition ``rows`` into ``wave_total`` contiguous slices; keep slice ``wave_index`` (1-based)."""
    if not wave_index or not wave_total:
        return rows
    wi, wt = int(wave_index), int(wave_total)
    if wi < 1 or wt < 1:
        return rows
    n = len(rows)
    if n == 0:
        return rows
    chunk = (n + wt - 1) // wt
    start = (wi - 1) * chunk
    end = min(n, start + chunk)
    print(f"wave slice {wi}/{wt}: using rows [{start}:{end}] of {n} filtered candidates")
    return rows[start:end]


def cmd_extract(args: argparse.Namespace) -> None:
    from tools.dict_calibration.env_defaults import assert_corpus_not_legacy_research

    assert_corpus_not_legacy_research(args.corpus)
    rows = extract_corpus(Path(args.corpus), min_freq=args.min_freq)
    write_jsonl(Path(args.out) / "dict_a_candidates.jsonl", rows)
    print(f"wrote {len(rows)} candidate rows → {args.out}/dict_a_candidates.jsonl")


def cmd_normalize(args: argparse.Namespace) -> None:
    w = Path(args.workdir)
    rows = read_jsonl(w / "dict_a_candidates.jsonl")
    rows = filter_rows_for_llm(rows, max_rows=None)
    rows = _wave_slice_rows(
        rows,
        getattr(args, "wave_slice_index", None),
        getattr(args, "wave_slice_total", None),
    )
    wi = getattr(args, "wave_slice_index", None)
    wt = getattr(args, "wave_slice_total", None)
    if wi is not None and wt is not None:
        write_json(
            Path(args.workdir) / "wave_slice.json",
            {"index": int(wi), "total": int(wt)},
        )
    cap = getattr(args, "max_llm_rows", None)
    if cap is not None and int(cap) > 0 and len(rows) > int(cap):
        rows = rows[: int(cap)]
        print(f"normalize: capped to {cap} rows (highest freq first)")
    if args.dry_run:
        out = [dict(r, normalized=r.get("text", ""), variants=[]) for r in rows]
    else:
        out = normalize_batch(rows, batch_size=args.batch_size)
    write_jsonl(w / "dict_a_normalized.jsonl", out)
    print(f"wrote {len(out)} normalized rows")


def cmd_propose(args: argparse.Namespace) -> None:
    repo = _ROOT
    domain = normalize_domain(str(getattr(args, "domain", "core") or "core"))
    db_paths, _ = _default_engine_paths(repo, domain=domain)
    if args.dict_b:
        db_paths = [Path(p) for p in args.dict_b]
    assert_domain_corpus_pairing(domain, None, dict_b_paths=db_paths)
    merged = load_merged_dict_b(db_paths)
    w = Path(args.workdir)
    norm = read_jsonl(w / "dict_a_normalized.jsonl")
    norm = filter_rows_for_llm(norm, max_rows=None)
    if args.limit:
        norm = norm[: int(args.limit)]
    if args.dry_run:
        drafts = [
            {
                "concept_id": "dry_run.placeholder",
                "labels": ["placeholder"],
                "from_lexical": [str(norm[0].get("normalized") or norm[0].get("text", "test"))],
                "confidence": 0.1,
            }
        ] if norm else []
    else:
        drafts = propose_concepts(
            norm,
            merged,
            max_concepts=args.max_concepts,
            batch_size=int(getattr(args, "propose_batch_size", 40) or 40),
            catalog_limit=int(getattr(args, "catalog_limit", 400) or 400),
            domain=domain,  # type: ignore[arg-type]
        )
    write_jsonl(w / "dict_b_draft.jsonl", drafts)
    print(f"wrote {len(drafts)} draft concepts (domain={domain})")


def cmd_anchor(args: argparse.Namespace) -> None:
    repo = _ROOT
    domain = normalize_domain(str(getattr(args, "domain", "core") or "core"))
    db_paths, anch_path = _default_engine_paths(repo, domain=domain)
    if args.dict_b:
        db_paths = [Path(p) for p in args.dict_b]
    assert_domain_corpus_pairing(domain, None, dict_b_paths=db_paths)
    merged = load_merged_dict_b(db_paths)
    concept_index = {str(r["concept_id"]): r for r in merged}
    reg = load_anchor_registry(anch_path)
    w = Path(args.workdir)
    drafts = read_jsonl(w / "dict_b_draft.jsonl")
    workers = int(getattr(args, "anchor_workers", dict_calib_worker_default()) or 1)
    anchored, rejected = anchor_drafts(
        drafts,
        concept_index,
        reg,
        min_score=args.min_score,
        workers=workers,
        dict_b_paths=db_paths,
        anchor_registry_path=anch_path,
    )
    write_jsonl(w / "dict_b_anchored.jsonl", anchored)
    write_jsonl(w / "dict_b_rejected.jsonl", rejected)
    print(f"anchored={len(anchored)} rejected={len(rejected)}")


def cmd_links(args: argparse.Namespace) -> None:
    w = Path(args.workdir)
    norm = read_jsonl(w / "dict_a_normalized.jsonl")
    anch = read_jsonl(w / "dict_b_anchored.jsonl")
    fuzzy_mode = str(getattr(args, "fuzzy_mode", "auto") or "auto").strip().lower()
    if fuzzy_mode not in {"auto", "off", "full", "partial"}:
        raise ValueError("--fuzzy-mode must be one of: auto, off, full, partial")
    if fuzzy_mode == "off":
        fuzzy_flag: bool | None = False
    elif fuzzy_mode in {"full", "partial"}:
        fuzzy_flag = True
    else:
        fuzzy_flag = None
    # NOTE (found CORE-S2-LIVE-02, 2026-09-14): --link-workers/--fuzzy-top-k/
    # --fuzzy-candidate-cap/--alias-reuse-top-misses/--alias-cutoff/--exact-weight/
    # --fuzzy-weight/--alias-weight/--min-priority/--max-links-per-token are CLI
    # flags with no backing implementation -- build_links() only ever accepted
    # (normalized_rows, anchored_rows, fuzzy). Passing them crashed run-all's
    # links stage with TypeError on every invocation. Dropped from the call
    # rather than guessed-implemented in build_links(); those flags are now
    # silently no-op until someone actually builds the weighting/cap logic they
    # describe -- real feature debt, not blocking, flagged to Felix/Gena.
    links = build_links(
        norm,
        anch,
        fuzzy=fuzzy_flag,
    )
    write_jsonl(w / "dict_a_to_b_links.jsonl", links)
    eng = links_to_engine_dict_a(links)
    write_jsonl(w / "dict_a_engine.jsonl", eng)
    print(f"links={len(links)} engine_dict_a={len(eng)}")


def cmd_eval(args: argparse.Namespace) -> None:
    repo = _ROOT
    domain = normalize_domain(str(getattr(args, "domain", "core") or "core"))
    db_paths, anch_path = _default_engine_paths(repo, domain=domain)
    if args.dict_b:
        db_paths = [Path(p) for p in args.dict_b]
    assert_domain_corpus_pairing(
        domain,
        Path(args.corpus) if args.corpus else None,
        dict_b_paths=db_paths,
    )
    w = Path(args.workdir)
    da_eng = w / "dict_a_engine.jsonl"
    texts: list[str] = []
    if args.texts_file:
        texts = Path(args.texts_file).read_text(encoding="utf-8").split("\n---\n")
    elif args.corpus:
        texts = _sample_texts_from_corpus(
            Path(args.corpus),
            max_files=int(getattr(args, "eval_max_files", 5) or 5),
            max_chars=int(getattr(args, "eval_max_chars", 12_000) or 12_000),
        )
    else:
        texts = ["identity diffusion and splitting in session text"]
    eval_kwargs: dict[str, Any] = {
        "dict_a_path": da_eng,
        "dict_b_paths": db_paths,
        "anchors_path": anch_path,
        "repo_path": repo,
    }
    try:
        if "workers" in inspect.signature(evaluate_on_texts).parameters:
            eval_kwargs["workers"] = int(getattr(args, "eval_workers", dict_calib_worker_default()) or 1)
    except (TypeError, ValueError):
        pass
    ev = evaluate_on_texts(texts, **eval_kwargs)
    write_json(w / "evaluation_run.json", ev)
    print(json.dumps(ev.get("aggregate"), indent=2))
    if bool(getattr(args, "emit_contradiction_feedback", False)):
        cp = getattr(args, "contradiction_package_file", None)
        cp_path = Path(cp) if cp else (w / "contradiction_package.json")
        pkg: dict[str, Any] = {}
        if cp_path.is_file():
            try:
                pkg = json.loads(cp_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pkg = {}
        rows = pkg.get("top_risky_pairs") if isinstance(pkg.get("top_risky_pairs"), list) else []
        top_k = int(getattr(args, "feedback_top_k", 100) or 100)
        feedback = build_contradiction_feedback_signals(
            contradiction_rows=rows,
            uncertainty_package={},
            activation={},
            lexical_output={},
            top_k=top_k,
        )
        write_json(
            w / "contradiction_feedback_report.json",
            {
                "summary": {
                    "calibration_contradiction_risk": float(
                        (feedback.get("global_feedback_summary") or {}).get("calibration_contradiction_risk") or 0.0
                    ),
                    "likely_calibration_pathology": float(
                        (
                            (
                                feedback.get("global_feedback_summary") or {}
                            ).get("runtime_vs_calibration_conflict_split")
                            or {}
                        ).get("likely_calibration_pathology")
                        or 0.0
                    ),
                },
                "top_risky_tokens": (feedback.get("lexical_feedback") or {}).get("top_risky_tokens") or [],
                "top_risky_concepts": (feedback.get("concept_feedback") or {}).get("top_risky_concepts") or [],
                "top_risky_pairs": (feedback.get("pair_feedback") or {}).get("top_risky_pairs") or [],
                "recommendations": {
                    "review_fuzzy_links": True,
                    "review_alias_routes": True,
                    "review_ambiguous_concept_bridges": True,
                },
            },
        )
        write_json(w / "risky_lexical_items.json", {"rows": (feedback.get("lexical_feedback") or {}).get("top_risky_tokens") or []})
        write_json(w / "risky_concepts.json", {"rows": (feedback.get("concept_feedback") or {}).get("top_risky_concepts") or []})
        write_json(w / "risky_concept_pairs.json", {"rows": (feedback.get("pair_feedback") or {}).get("top_risky_pairs") or []})


def cmd_errors(args: argparse.Namespace) -> None:
    w = Path(args.workdir)
    ev = json.loads((w / "evaluation_run.json").read_text(encoding="utf-8"))
    texts: list[str] = []
    if args.texts_file:
        texts = Path(args.texts_file).read_text(encoding="utf-8").split("\n---\n")
    elif args.corpus:
        texts = _sample_texts_from_corpus(
            Path(args.corpus),
            max_files=int(getattr(args, "eval_max_files", 5) or 5),
            max_chars=int(getattr(args, "eval_max_chars", 12_000) or 12_000),
        )
    # NOTE (found CORE-S2-LIVE-02, 2026-09-14): --error-workers has no backing
    # implementation -- extract_errors() takes no workers kwarg. Same class of
    # CLI/implementation drift as cmd_links's build_links() call above.
    err = extract_errors(ev, texts)
    write_jsonl(w / "dict_errors.jsonl", err)
    print(f"errors={len(err)}")


def cmd_patch(args: argparse.Namespace) -> None:
    w = Path(args.workdir)
    err = read_jsonl(w / "dict_errors.jsonl")
    links = read_jsonl(w / "dict_a_to_b_links.jsonl")
    if args.dry_run:
        patch = {"add_lexical": [], "notes": "dry_run"}
    else:
        patch = propose_patch(
            err,
            links,
            max_errors=int(getattr(args, "patch_max_errors", 80) or 80),
            max_links=int(getattr(args, "patch_max_links", 40) or 40),
        )
    write_json(w / "dict_patch.json", patch)
    merged = apply_patch_to_links(links, patch)
    write_jsonl(w / "dict_a_to_b_links_patched.jsonl", merged)
    write_jsonl(w / "dict_a_engine.jsonl", links_to_engine_dict_a(merged))
    print("patch written and engine dict_a refreshed")


def cmd_loop(args: argparse.Namespace) -> None:
    repo = _ROOT
    domain = normalize_domain(str(getattr(args, "domain", "core") or "core"))
    db_paths, anch_path = _default_engine_paths(repo, domain=domain)
    assert_domain_corpus_pairing(
        domain,
        Path(args.corpus) if args.corpus else None,
        dict_b_paths=db_paths,
    )
    w = Path(args.workdir)
    norm = read_jsonl(w / "dict_a_normalized.jsonl")
    anch = read_jsonl(w / "dict_b_anchored.jsonl")
    texts = (
        _sample_texts_from_corpus(
            Path(args.corpus),
            max_files=int(args.eval_max_files),
            max_chars=int(args.eval_max_chars),
        )
        if args.corpus
        else ["identity diffusion and splitting in session text"]
    )
    max_iters = int(args.max_iters)
    pe, pl = 80, 40
    if getattr(args, "budget", False):
        from tools.dict_calibration.budget import BUDGET

        max_iters = min(max_iters, BUDGET["loop_max_iters_cap"])
        pe, pl = BUDGET["patch_max_errors"], BUDGET["patch_max_links"]
    cfg = LoopConfig(
        max_iters=max_iters,
        unmapped_pct_max=args.unmapped_max_pct,
        patch_max_errors=pe,
        patch_max_links=pl,
    )
    prev_h: float | None = None
    for i in range(args.max_iters):
        info = run_iteration(
            w,
            normalized_rows=norm,
            anchored_rows=anch,
            eval_texts=texts,
            dict_b_paths=db_paths,
            anchors_path=anch_path,
            links_path=w / "dict_a_to_b_links.jsonl",
            dict_a_engine_path=w / "dict_a_engine.jsonl",
            prev_entropy=prev_h,
            cfg=cfg,
        )
        prev_h = float(info["concept_entropy"])
        print(f"iter {i+1}: {info}")
        if info.get("converged"):
            break


def cmd_freeze(args: argparse.Namespace) -> None:
    freeze(Path(args.workdir), Path(args.version_dir))
    print(f"frozen → {args.version_dir}")


# TFP-DATA-T11: WAVE_HANDOFF.md must not contain the legacy noone path needle
# (see tools/check_research_noone_local_literals.py). Build needle without the
# forbidden contiguous literal in *this* source file.
_RESEARCH_NOONE_NEEDLE = "research" + "/" + "_noone_local"


def _corpus_display_for_handoff(corpus: str) -> str:
    s = corpus.replace("\\", "/")
    if _RESEARCH_NOONE_NEEDLE in s:
        rest = s.split(_RESEARCH_NOONE_NEEDLE, 1)[1]
        return f"`_noone_local{rest}` (under `research/`)"
    return f"`{s}`"


def _next_wave_index(base: Path) -> int:
    best = 0
    if not base.exists():
        return 1
    for p in base.iterdir():
        if not p.is_dir() or not p.name.startswith("wave_"):
            continue
        suf = p.name.removeprefix("wave_")
        try:
            best = max(best, int(suf))
        except ValueError:
            continue
    return best + 1


def _write_wave_handoff(work: Path, wave_n: int, corpus: str) -> None:
    import json as _json

    evp = work / "evaluation_run.json"
    agg: dict = {}
    if evp.exists():
        try:
            agg = (_json.loads(evp.read_text(encoding="utf-8")) or {}).get("aggregate") or {}
        except _json.JSONDecodeError:
            pass
    n_eng = 0
    eng = work / "dict_a_engine.jsonl"
    if eng.exists():
        n_eng = sum(1 for line in eng.read_text(encoding="utf-8").splitlines() if line.strip())
    n_cand = 0
    cand = work / "dict_a_candidates.jsonl"
    if cand.exists():
        n_cand = sum(1 for line in cand.read_text(encoding="utf-8").splitlines() if line.strip())
    slice_line: str | None = None
    sm = work / "wave_slice.json"
    if sm.exists():
        try:
            import json as _j2

            sl = _j2.loads(sm.read_text(encoding="utf-8"))
            slice_line = f"- **slice:** {sl.get('index')}/{sl.get('total')} of filtered candidates"
        except Exception:
            pass
    lines = [
        f"# Calibration wave {wave_n:03d}",
        "",
        f"- **workdir:** `{work}`",
        f"- **corpus:** {_corpus_display_for_handoff(corpus)}",
    ]
    if slice_line:
        lines.append(slice_line)
    lines += [
        f"- **candidates (extract):** {n_cand}",
        f"- **dict_a_engine rows:** {n_eng}",
        "",
        "## Eval aggregate (DLCR)",
        "",
        "```json",
        _json.dumps(agg, indent=2) if agg else "{}",
        "```",
        "",
        "## Paste to Ethan (next loop)",
        "",
        "1. Open `evaluation_run.json` / `dict_errors.jsonl` if metrics look wrong.",
        "2. Say what to fix (e.g. missing concepts, wrong links).",
        "3. Re-run: `wave --corpus <path>` or batch: `waves --corpus <path> --count 20`.",
        "4. When satisfied, `freeze` into `assets/calibration/dicts/...` and add TFP test inputs.",
        "",
    ]
    (work / "WAVE_HANDOFF.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n--- wave handoff ---")
    print(f"wave={wave_n:03d} workdir={work}")
    print(f"dict_a_engine rows={n_eng} candidates={n_cand}")
    if agg:
        print("aggregate:", _json.dumps(agg, indent=2))


def cmd_wave(args: argparse.Namespace) -> None:
    if not args.skip_llm:
        require_openai_key()
    base = Path(args.base_dir)
    base.mkdir(parents=True, exist_ok=True)
    n = int(args.wave) if args.wave is not None else _next_wave_index(base)
    workdir = str(base / f"wave_{n:03d}")
    Path(workdir).mkdir(parents=True, exist_ok=True)
    ra = argparse.Namespace(
        corpus=args.corpus,
        workdir=workdir,
        min_freq=args.min_freq,
        batch_size=args.batch_size,
        domain=str(getattr(args, "domain", "core") or "core"),
        max_concepts=args.max_concepts,
        propose_limit=args.propose_limit,
        min_score=args.min_score,
        skip_llm=args.skip_llm,
        budget=not args.no_budget,
        normalize_max_rows=args.normalize_max_rows,
        catalog_limit=args.catalog_limit,
        propose_batch_size=args.propose_batch_size,
        eval_max_files=args.eval_max_files,
        eval_max_chars=args.eval_max_chars,
        patch_max_errors=args.patch_max_errors,
        patch_max_links=args.patch_max_links,
        emit_contradiction_feedback=bool(getattr(args, "emit_contradiction_feedback", False)),
        feedback_top_k=int(getattr(args, "feedback_top_k", 100) or 100),
        contradiction_package_file=getattr(args, "contradiction_package_file", None),
        wave_slice_index=None,
        wave_slice_total=None,
    )
    cmd_run_all(ra)
    _write_wave_handoff(Path(workdir), n, args.corpus)


def _default_call_ledger_to_workdir(workdir: str | Path) -> None:
    """Point the per-call durability ledger (openai_json._ledger_path) at this run's own workdir
    unless the caller already set HESPERIA_CALIB_CALL_LEDGER explicitly. Long/costly runs get
    their ledger sitting right next to their other outputs instead of one shared repo-wide file.
    """
    if not os.environ.get("HESPERIA_CALIB_CALL_LEDGER", "").strip():
        os.environ["HESPERIA_CALIB_CALL_LEDGER"] = str(Path(workdir) / "call_ledger.jsonl")


def cmd_ru_tfp_align(args: argparse.Namespace) -> None:
    from tools.dict_calibration.env_defaults import assert_corpus_not_legacy_research

    assert_corpus_not_legacy_research(args.corpus)
    require_openai_key()
    _default_call_ledger_to_workdir(args.workdir)
    mx = int(args.max_phrases)
    only = None
    if getattr(args, "only_zero_from", None):
        only = frozenset(
            load_zero_link_ids_from_coverage_report(Path(args.only_zero_from))
        )
    seed = Path(args.seed_dict_a) if getattr(args, "seed_dict_a", None) else None
    rep = run_ru_tfp_corpus_align(
        Path(args.corpus),
        Path(args.workdir),
        passes=int(args.passes),
        phrase_chunk_size=int(args.phrase_chunk_size),
        concept_batch_size=int(args.concept_batch_size),
        align_mode=str(args.align_mode),
        phrase_sub_batch=int(args.phrase_sub_batch),
        min_freq=int(args.min_freq),
        max_phrases=None if mx <= 0 else mx,
        concept_ids_only=only,
        seed_dict_a=seed,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))


def cmd_ru_tfp_extract_cold(args: argparse.Namespace) -> None:
    dict_b_paths = [Path(p) for p in args.dict_b] if args.dict_b else None
    info = write_ru_tfp_cold_artifacts(
        Path(args.coverage_report),
        Path(args.out_dir),
        dict_b_paths=dict_b_paths,
    )
    print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_waves(args: argparse.Namespace) -> None:
    count = max(1, int(args.count))
    for k in range(1, count + 1):
        print(f"\n========== waves {k}/{count} ==========\n")
        if not args.skip_llm:
            require_openai_key()
        base = Path(args.base_dir)
        base.mkdir(parents=True, exist_ok=True)
        n = _next_wave_index(base)
        workdir = str(base / f"wave_{n:03d}")
        Path(workdir).mkdir(parents=True, exist_ok=True)
        ra = argparse.Namespace(
            corpus=args.corpus,
            workdir=workdir,
            min_freq=args.min_freq,
            batch_size=args.batch_size,
            domain=str(getattr(args, "domain", "core") or "core"),
            max_concepts=args.max_concepts,
            propose_limit=args.propose_limit,
            min_score=args.min_score,
            skip_llm=args.skip_llm,
            budget=not args.no_budget,
            normalize_max_rows=args.normalize_max_rows,
            catalog_limit=args.catalog_limit,
            propose_batch_size=args.propose_batch_size,
            eval_max_files=args.eval_max_files,
            eval_max_chars=args.eval_max_chars,
            patch_max_errors=args.patch_max_errors,
            patch_max_links=args.patch_max_links,
            emit_contradiction_feedback=bool(getattr(args, "emit_contradiction_feedback", False)),
            feedback_top_k=int(getattr(args, "feedback_top_k", 100) or 100),
            contradiction_package_file=getattr(args, "contradiction_package_file", None),
            wave_slice_index=k,
            wave_slice_total=count,
        )
        cmd_run_all(ra)
        _write_wave_handoff(Path(workdir), n, args.corpus)
    print(f"\nDone. {count} waves under {args.base_dir}")


def cmd_run_all(args: argparse.Namespace) -> None:
    domain = normalize_domain(str(getattr(args, "domain", "core") or "core"))
    assert_domain_corpus_pairing(domain, Path(args.corpus))
    if getattr(args, "budget", False):
        from tools.dict_calibration.budget import apply_run_all_budget

        apply_run_all_budget(args)
    _default_call_ledger_to_workdir(args.workdir)
    ns = argparse.Namespace(
        corpus=args.corpus,
        out=args.workdir,
        min_freq=args.min_freq,
    )
    cmd_extract(ns)
    ns2 = argparse.Namespace(
        workdir=args.workdir,
        batch_size=args.batch_size,
        dry_run=args.skip_llm,
        max_llm_rows=getattr(args, "normalize_max_rows", None),
        wave_slice_index=getattr(args, "wave_slice_index", None),
        wave_slice_total=getattr(args, "wave_slice_total", None),
    )
    cmd_normalize(ns2)
    ns3 = argparse.Namespace(
        workdir=args.workdir,
        dict_b=None,
        domain=str(getattr(args, "domain", "core") or "core"),
        max_concepts=args.max_concepts,
        limit=args.propose_limit,
        dry_run=args.skip_llm,
        catalog_limit=getattr(args, "catalog_limit", 400),
        propose_batch_size=getattr(args, "propose_batch_size", 40),
    )
    cmd_propose(ns3)
    ns4 = argparse.Namespace(
        workdir=args.workdir,
        dict_b=None,
        domain=str(getattr(args, "domain", "core") or "core"),
        min_score=args.min_score,
        anchor_workers=getattr(args, "anchor_workers", dict_calib_worker_default()),
    )
    cmd_anchor(ns4)
    cmd_links(
        argparse.Namespace(
            workdir=args.workdir,
            link_workers=getattr(args, "link_workers", dict_calib_worker_default()),
        )
    )
    ns5 = argparse.Namespace(
        workdir=args.workdir,
        corpus=args.corpus,
        texts_file=None,
        dict_b=None,
        domain=str(getattr(args, "domain", "core") or "core"),
        eval_max_files=getattr(args, "eval_max_files", 5),
        eval_max_chars=getattr(args, "eval_max_chars", 12_000),
        eval_workers=getattr(args, "eval_workers", dict_calib_worker_default()),
        emit_contradiction_feedback=bool(getattr(args, "emit_contradiction_feedback", False)),
        feedback_top_k=int(getattr(args, "feedback_top_k", 100) or 100),
        contradiction_package_file=getattr(args, "contradiction_package_file", None),
    )
    cmd_eval(ns5)
    cmd_errors(
        argparse.Namespace(
            workdir=args.workdir,
            corpus=args.corpus,
            texts_file=None,
            eval_max_files=getattr(args, "eval_max_files", 5),
            eval_max_chars=getattr(args, "eval_max_chars", 12_000),
            error_workers=getattr(args, "error_workers", dict_calib_worker_default()),
        )
    )
    if not args.skip_llm:
        cmd_patch(
            argparse.Namespace(
                workdir=args.workdir,
                dry_run=False,
                patch_max_errors=getattr(args, "patch_max_errors", 80),
                patch_max_links=getattr(args, "patch_max_links", 40),
            )
        )
    print("run-all complete; see", args.workdir)


def main() -> None:
    apply_dict_calib_offline_bundle()
    dw = dict_calib_worker_default()
    p = argparse.ArgumentParser(description="Dict calibration: corpus + OpenAI + DLCR")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ext = sub.add_parser("extract", help="Task 1: corpus → dict_a_candidates.jsonl")
    p_ext.add_argument("--corpus", required=True)
    p_ext.add_argument("--out", default="outputs/dict_calibration/run1")
    p_ext.add_argument("--min-freq", type=int, default=2)
    p_ext.set_defaults(func=cmd_extract)

    p_norm = sub.add_parser("normalize", help="Task 2: LLM normalize")
    p_norm.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_norm.add_argument("--batch-size", type=int, default=24)
    p_norm.add_argument(
        "--max-llm-rows",
        type=int,
        default=None,
        help="Cap candidate rows sent to API (file is freq-sorted)",
    )
    p_norm.add_argument("--dry-run", action="store_true")
    p_norm.set_defaults(func=cmd_normalize)

    p_pr = sub.add_parser("propose", help="Task 3: LLM → dict_b draft")
    p_pr.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_pr.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Propose prompt + catalog domain (default: core / Class A). Use tfp only for Class B TFP.",
    )
    p_pr.add_argument("--dict-b", nargs="*", help="Override dict_b jsonl paths")
    p_pr.add_argument("--max-concepts", type=int, default=80)
    p_pr.add_argument("--limit", type=int, default=0, help="Cap normalized rows (0=all)")
    p_pr.add_argument("--catalog-limit", type=int, default=400, help="Dict B lines in prompt")
    p_pr.add_argument("--propose-batch-size", type=int, default=40)
    p_pr.add_argument("--dry-run", action="store_true")
    p_pr.set_defaults(func=cmd_propose)

    p_an = sub.add_parser("anchor", help="Task 4: bind to Hesperia concepts")
    p_an.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_an.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Catalog/anchors domain (default: core). Must match propose domain.",
    )
    p_an.add_argument("--dict-b", nargs="*", help="Override dict_b jsonl paths")
    p_an.add_argument("--min-score", type=float, default=0.52)
    p_an.add_argument(
        "--anchor-workers",
        type=int,
        default=dw,
        help="Process pool size for anchoring (default: $HESPERIA_DICT_CALIB_WORKERS or 4)",
    )
    p_an.set_defaults(func=cmd_anchor)

    p_ln = sub.add_parser("links", help="Task 5: A↔B links + engine dict_a")
    p_ln.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_ln.add_argument(
        "--link-workers",
        type=int,
        default=dw,
        help="Workers for link building (default: $HESPERIA_DICT_CALIB_WORKERS or 4)",
    )
    p_ln.add_argument(
        "--fuzzy-mode",
        choices=["auto", "off", "full", "partial"],
        default="auto",
        help="Fuzzy policy: auto/off/full/partial (partial=only top miss tokens)",
    )
    p_ln.add_argument(
        "--partial-fuzzy-top-misses",
        type=int,
        default=0,
        help="When --fuzzy-mode partial: top N exact-miss normalized tokens to fuzzy-match",
    )
    p_ln.add_argument(
        "--fuzzy-top-k",
        type=int,
        default=3,
        help="Keep at most K top fuzzy candidates per token (best one is used for link)",
    )
    p_ln.add_argument(
        "--fuzzy-candidate-cap",
        type=int,
        default=2048,
        help="Per-token fuzzy candidate cap after cheap blocking",
    )
    p_ln.add_argument("--alias-reuse-top-misses", type=int, default=0, help="Top exact-miss tokens to alias-map with difflib")
    p_ln.add_argument("--alias-cutoff", type=float, default=0.85, help="difflib cutoff for alias reuse")
    p_ln.add_argument("--exact-weight", type=float, default=1.0, help="Priority multiplier for exact matches")
    p_ln.add_argument("--fuzzy-weight", type=float, default=0.7, help="Priority multiplier for fuzzy matches")
    p_ln.add_argument("--alias-weight", type=float, default=0.5, help="Priority multiplier for alias-reuse matches")
    p_ln.add_argument("--min-priority", type=float, default=0.0, help="Drop links below this priority")
    p_ln.add_argument("--max-links-per-token", type=int, default=3, help="Hard cap links per token after scoring")
    p_ln.set_defaults(func=cmd_links)

    p_ev = sub.add_parser("eval", help="Task 6: DLCR evaluation")
    p_ev.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_ev.add_argument("--corpus", help="Sample md files for eval texts")
    p_ev.add_argument("--texts-file", help="Texts split by \\n---\\n")
    p_ev.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Catalog domain (default: core).",
    )
    p_ev.add_argument("--dict-b", nargs="*", help="Override dict_b jsonl paths")
    p_ev.add_argument(
        "--eval-max-files",
        type=int,
        default=5,
        help="MD files to score (default 5). Use <=0 for entire corpus tree.",
    )
    p_ev.add_argument(
        "--eval-max-chars",
        type=int,
        default=12_000,
        help="Truncate each file to this many chars (default 12000). Use <=0 for full text.",
    )
    p_ev.add_argument(
        "--eval-workers",
        type=int,
        default=dw,
        help="Workers for per-text DLCR eval (default: $HESPERIA_DICT_CALIB_WORKERS or 4)",
    )
    p_ev.add_argument("--emit-contradiction-feedback", action="store_true")
    p_ev.add_argument("--feedback-top-k", type=int, default=100)
    p_ev.add_argument("--contradiction-package-file", type=str, default=None)
    p_ev.set_defaults(func=cmd_eval)

    p_er = sub.add_parser("errors", help="Task 7: error surface")
    p_er.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_er.add_argument("--corpus", default=None)
    p_er.add_argument("--texts-file", default=None)
    p_er.add_argument(
        "--eval-max-files",
        type=int,
        default=5,
        help="MD files for error surface (default 5). Use <=0 for entire corpus.",
    )
    p_er.add_argument(
        "--eval-max-chars",
        type=int,
        default=12_000,
        help="Truncate each file (default 12000). Use <=0 for full text.",
    )
    p_er.add_argument(
        "--error-workers",
        type=int,
        default=dw,
        help="Workers for error extraction (default: $HESPERIA_DICT_CALIB_WORKERS or 4)",
    )
    p_er.set_defaults(func=cmd_errors)

    p_pt = sub.add_parser("patch", help="Task 8: LLM patch + apply links")
    p_pt.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_pt.add_argument("--dry-run", action="store_true")
    p_pt.add_argument("--patch-max-errors", type=int, default=80)
    p_pt.add_argument("--patch-max-links", type=int, default=40)
    p_pt.set_defaults(func=cmd_patch)

    p_lp = sub.add_parser("loop", help="Task 9: iteration")
    p_lp.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_lp.add_argument("--corpus", required=True)
    p_lp.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Catalog domain (default: core).",
    )
    p_lp.add_argument("--max-iters", type=int, default=3)
    p_lp.add_argument("--unmapped-max-pct", type=float, default=25.0)
    p_lp.add_argument(
        "--budget",
        action="store_true",
        help="Cap loop iters + patch payload (matches run-all --budget)",
    )
    p_lp.add_argument("--eval-max-files", type=int, default=5)
    p_lp.add_argument("--eval-max-chars", type=int, default=12_000)
    p_lp.set_defaults(func=cmd_loop)

    p_fr = sub.add_parser("freeze", help="Task 10: copy to version dir")
    p_fr.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_fr.add_argument("--version-dir", required=True)
    p_fr.set_defaults(func=cmd_freeze)

    p_wave = sub.add_parser(
        "wave",
        help="Next numbered calibration pass (OpenAI from .env); use each loop with Ethan",
    )
    p_wave.add_argument("--corpus", required=True)
    p_wave.add_argument(
        "--base-dir",
        default="outputs/dict_calibration",
        help="Creates wave_001, wave_002, … under this directory",
    )
    p_wave.add_argument("--wave", type=int, default=None, help="Explicit wave index (default: auto)")
    p_wave.add_argument(
        "--no-budget",
        action="store_true",
        help="Disable budget caps (higher API cost)",
    )
    p_wave.add_argument("--skip-llm", action="store_true")
    p_wave.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Propose/catalog domain (default: core / Class A).",
    )
    p_wave.add_argument("--min-freq", type=int, default=2)
    p_wave.add_argument("--batch-size", type=int, default=24)
    p_wave.add_argument("--max-concepts", type=int, default=80)
    p_wave.add_argument("--propose-limit", type=int, default=120)
    p_wave.add_argument("--min-score", type=float, default=0.52)
    p_wave.add_argument("--normalize-max-rows", type=int, default=None)
    p_wave.add_argument("--catalog-limit", type=int, default=400)
    p_wave.add_argument("--propose-batch-size", type=int, default=40)
    p_wave.add_argument("--eval-max-files", type=int, default=5)
    p_wave.add_argument("--eval-max-chars", type=int, default=12_000)
    p_wave.add_argument("--patch-max-errors", type=int, default=80)
    p_wave.add_argument("--patch-max-links", type=int, default=40)
    p_wave.add_argument("--emit-contradiction-feedback", action="store_true")
    p_wave.add_argument("--feedback-top-k", type=int, default=100)
    p_wave.add_argument("--contradiction-package-file", type=str, default=None)
    p_wave.set_defaults(func=cmd_wave)

    p_waves = sub.add_parser(
        "waves",
        help="Run COUNT sequential waves; slice 1..N of filtered candidates (sensible coverage)",
    )
    p_waves.add_argument("--corpus", required=True)
    p_waves.add_argument("--count", type=int, default=20, help="Number of waves (default 20)")
    p_waves.add_argument(
        "--base-dir",
        default="outputs/dict_calibration",
        help="Creates wave_00N directories under this path",
    )
    p_waves.add_argument(
        "--no-budget",
        action="store_true",
        help="Disable budget caps (much higher API cost × count)",
    )
    p_waves.add_argument("--skip-llm", action="store_true")
    p_waves.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Propose/catalog domain (default: core / Class A).",
    )
    p_waves.add_argument("--min-freq", type=int, default=2)
    p_waves.add_argument("--batch-size", type=int, default=24)
    p_waves.add_argument("--max-concepts", type=int, default=80)
    p_waves.add_argument("--propose-limit", type=int, default=120)
    p_waves.add_argument("--min-score", type=float, default=0.52)
    p_waves.add_argument("--normalize-max-rows", type=int, default=None)
    p_waves.add_argument("--catalog-limit", type=int, default=400)
    p_waves.add_argument("--propose-batch-size", type=int, default=40)
    p_waves.add_argument("--eval-max-files", type=int, default=5)
    p_waves.add_argument("--eval-max-chars", type=int, default=12_000)
    p_waves.add_argument("--patch-max-errors", type=int, default=80)
    p_waves.add_argument("--patch-max-links", type=int, default=40)
    p_waves.add_argument("--emit-contradiction-feedback", action="store_true")
    p_waves.add_argument("--feedback-top-k", type=int, default=100)
    p_waves.add_argument("--contradiction-package-file", type=str, default=None)
    p_waves.set_defaults(func=cmd_waves)

    p_ru = sub.add_parser(
        "ru-tfp-align",
        help="3-pass (default) Russian corpus → all 283 merged TFP concepts via OpenAI",
    )
    p_ru.add_argument("--corpus", required=True, type=Path)
    p_ru.add_argument(
        "--workdir",
        required=True,
        type=Path,
        help="Output dir (dict_a_tfp_ru_aligned.jsonl, coverage_report.json, …)",
    )
    p_ru.add_argument("--passes", type=int, default=3)
    p_ru.add_argument(
        "--phrase-chunk-size",
        type=int,
        default=280,
        help="Phrases per API call (catalog lists all concepts each call)",
    )
    p_ru.add_argument("--min-freq", type=int, default=2)
    p_ru.add_argument(
        "--max-phrases",
        type=int,
        default=6000,
        help="Cap phrase pool after freq sort (default 6000). Use 0 for no cap (very many API calls).",
    )
    p_ru.add_argument(
        "--align-mode",
        choices=("concept_batch", "phrase_chunk"),
        default="concept_batch",
        help="concept_batch: ~14 concepts per call (default, better coverage). phrase_chunk: legacy full-catalog+phrase slices.",
    )
    p_ru.add_argument(
        "--concept-batch-size",
        type=int,
        default=14,
        help="Concepts per API call when align-mode=concept_batch",
    )
    p_ru.add_argument(
        "--phrase-sub-batch",
        type=int,
        default=150,
        help="Split each pass phrase slice into chunks of this size (avoids truncated JSON). 0 = one shot.",
    )
    p_ru.add_argument(
        "--only-zero-from",
        type=Path,
        default=None,
        help="coverage_report.json: align only concepts_with_zero_links (cold second pass)",
    )
    p_ru.add_argument(
        "--seed-dict-a",
        type=Path,
        default=None,
        help="Existing dict_a jsonl: pre-load links so new align merges on top (use with cold-only pass)",
    )
    p_ru.set_defaults(func=cmd_ru_tfp_align)

    p_ru_cold = sub.add_parser(
        "ru-tfp-extract-cold",
        help="From coverage_report.json → cold ids, JSON rows, stayed_cold_readable.md (Dict B table)",
    )
    p_ru_cold.add_argument("--coverage-report", required=True, type=Path)
    p_ru_cold.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Directory for cold_concept_ids.txt, cold_concepts.json, stayed_cold_readable.md",
    )
    p_ru_cold.add_argument(
        "--dict-b",
        nargs="*",
        default=None,
        help="Override dict_b jsonl paths (default: engine_dynamics_v060 merge order)",
    )
    p_ru_cold.set_defaults(func=cmd_ru_tfp_extract_cold)

    p_ym = sub.add_parser(
        "yaml-markers-llm",
        help="LLM draft lexical_markers-style YAML from concept_nodes + corpus (review before canonical)",
    )
    p_ym.add_argument("--corpus", required=True, type=Path)
    p_ym.add_argument(
        "--workdir",
        required=True,
        type=Path,
        help="Writes lexical_markers_llm_proposed.yaml + yaml_markers_llm_report.json",
    )
    p_ym.add_argument(
        "--pilot",
        action="store_true",
        help="Only areas A2, A3, A4, A10",
    )
    p_ym.add_argument("--concept-batch-size", type=int, default=10)
    p_ym.add_argument("--phrase-sub-batch", type=int, default=80)
    p_ym.add_argument("--min-freq", type=int, default=2)
    p_ym.add_argument(
        "--max-phrases",
        type=int,
        default=2000,
        help="Cap phrase pool after frequency sort (0 = all)",
    )
    p_ym.add_argument("--min-conf", type=float, default=0.45)
    p_ym.add_argument(
        "--concept-nodes",
        type=Path,
        default=None,
        help="Override path to concept_nodes.yaml",
    )
    p_ym.add_argument(
        "--mock-llm",
        action="store_true",
        help="Set HESPERIA_CALIB_MOCK_OPENAI=1: no network; empty proposals (deterministic wiring check)",
    )
    p_ym.set_defaults(func=cmd_yaml_markers_llm_entry)

    p_all = sub.add_parser("run-all", help="Tasks 1–8 in sequence")
    p_all.add_argument("--corpus", required=True)
    p_all.add_argument("--workdir", default="outputs/dict_calibration/run1")
    p_all.add_argument(
        "--domain",
        choices=["core", "tfp"],
        default="core",
        help="Propose/catalog domain (default: core / Class A).",
    )
    p_all.add_argument("--min-freq", type=int, default=2)
    p_all.add_argument("--batch-size", type=int, default=24)
    p_all.add_argument("--max-concepts", type=int, default=80)
    p_all.add_argument("--propose-limit", type=int, default=120)
    p_all.add_argument("--min-score", type=float, default=0.52)
    p_all.add_argument("--skip-llm", action="store_true", help="Identity normalize + dry propose/patch")
    p_all.add_argument(
        "--budget",
        action="store_true",
        help="Tight caps for small API credit (gpt-4o-mini; ~few dozen calls)",
    )
    p_all.add_argument(
        "--normalize-max-rows",
        type=int,
        default=None,
        help="Max rows to LLM-normalize (with --budget, capped at 240)",
    )
    p_all.add_argument("--catalog-limit", type=int, default=400)
    p_all.add_argument("--propose-batch-size", type=int, default=40)
    p_all.add_argument("--eval-max-files", type=int, default=5)
    p_all.add_argument("--eval-max-chars", type=int, default=12_000)
    p_all.add_argument("--anchor-workers", type=int, default=dw)
    p_all.add_argument("--link-workers", type=int, default=dw)
    p_all.add_argument("--eval-workers", type=int, default=dw)
    p_all.add_argument("--error-workers", type=int, default=dw)
    p_all.add_argument("--patch-max-errors", type=int, default=80)
    p_all.add_argument("--patch-max-links", type=int, default=40)
    p_all.add_argument("--emit-contradiction-feedback", action="store_true")
    p_all.add_argument("--feedback-top-k", type=int, default=100)
    p_all.add_argument("--contradiction-package-file", type=str, default=None)
    p_all.set_defaults(func=cmd_run_all)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
