# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Align full merged TFP Dict B (283 concepts) to Russian corpus phrases via OpenAI.

Three passes: different confidence floors + optional coverage bias; phrase pool split across passes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.lexical.normalization import normalize_text

from .anchor_bind import load_merged_dict_b
from .extract_lexical import extract_corpus
from .jsonl_util import read_jsonl, write_json, write_jsonl
from .lexical_filter import filter_rows_for_llm
from .openai_json import chat_json, require_openai_key

_BISECT_EXC: tuple[type[BaseException], ...] = (RuntimeError, ValueError)
try:
    from openai import APIStatusError

    _BISECT_EXC = (RuntimeError, ValueError, APIStatusError)
except ImportError:  # pragma: no cover
    pass


def _sanitize_llm_string(s: str) -> str:
    """Strip NULs and normalize CR so OpenAI request JSON stays well-formed."""
    if not s:
        return s
    return s.replace("\x00", "").replace("\r", " ").strip()


def _compact_catalog(rows: list[dict[str, Any]], *, label_max: int = 72) -> str:
    lines = []
    for r in rows:
        cid = _sanitize_llm_string(str(r.get("concept_id", "")))
        lab = _sanitize_llm_string(str(r.get("preferred_label") or ""))[:label_max]
        lines.append(f"{cid}: {lab}")
    return "\n".join(lines)


def _phrase_pool(corpus: Path, *, min_freq: int) -> list[str]:
    raw = extract_corpus(corpus, min_freq=min_freq)
    raw = filter_rows_for_llm(raw, max_rows=None)
    by_phrase: dict[str, int] = {}
    for row in raw:
        p = str(row.get("normalized") or row.get("text", "")).strip()
        if len(p) < 3:
            continue
        cf = normalize_text(p)["canonical_text"]
        if not cf:
            continue
        cf = _sanitize_llm_string(cf)
        if len(cf) < 3:
            continue
        fq = int(row.get("freq", 0))
        by_phrase[cf] = max(by_phrase.get(cf, 0), fq)
    return [k for k, _ in sorted(by_phrase.items(), key=lambda x: (-x[1], -len(x[0])))]


def _chunk(lst: list[str], size: int) -> list[list[str]]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def _chunk_list(lst: list[Any], size: int) -> list[list[Any]]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def load_zero_link_ids_from_coverage_report(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("concepts_with_zero_links")
    if raw is None:
        raise ValueError(f"{path}: missing concepts_with_zero_links")
    if not isinstance(raw, list):
        raise ValueError(f"{path}: concepts_with_zero_links must be a list")
    return [str(x) for x in raw]


def _load_best_from_dict_a(path: Path) -> dict[str, tuple[str, float]]:
    """Map surface_form → (primary concept_id, confidence) for seeding a re-align run."""
    best: dict[str, tuple[str, float]] = {}
    for row in read_jsonl(path):
        ph = str(row.get("surface_form") or "").strip()
        if not ph:
            continue
        cids = row.get("candidate_concept_ids")
        if not isinstance(cids, list) or not cids:
            continue
        cid = str(cids[0])
        pr = int(row.get("priority") or 5)
        conf = max(0.0, min(1.0, pr / 10.0))
        if ph not in best or conf > best[ph][1]:
            best[ph] = (cid, conf)
    return best


def _md_cell(s: str, *, max_len: int = 200) -> str:
    t = " ".join(str(s).split()).replace("|", "\\|")
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t or "—"


def _write_stayed_cold_readable_md(
    path: Path,
    *,
    coverage_report: Path,
    ids: list[str],
    rows: list[dict[str, Any]],
    missing: list[str],
) -> None:
    """Human-readable list for review (e.g. after multiple align passes)."""
    lines = [
        "# Stayed cold — zero phrase links in coverage report",
        "",
        f"**Coverage report:** `{coverage_report}`",
        f"**Concepts with no linked phrase:** {len(ids)}",
        "",
        "Each row is one `concept_id` that still has **no** phrase mapped to it in the "
        "reporting align run (Dict A coverage). Use for manual markers, corpus expansion, or a further pass.",
        "",
        "## Table (merged Dict B)",
        "",
        "| # | concept_id | preferred_label | definition (excerpt) | areas |",
        "|--:|:---|:---|:---|:---|",
    ]
    for i, r in enumerate(rows, start=1):
        cid = str(r.get("concept_id", ""))
        lab = _md_cell(str(r.get("preferred_label", "")), max_len=160)
        defin = _md_cell(str(r.get("definition", "")), max_len=220)
        areas = r.get("area_ids")
        if isinstance(areas, list) and areas:
            ar = _md_cell(", ".join(str(a) for a in areas[:4]), max_len=80)
        else:
            ar = "—"
        lines.append(f"| {i} | `{cid}` | {lab} | {defin} | {ar} |")
    if missing:
        lines.extend(
            [
                "",
                "## Not found in merged Dict B",
                "",
                "These ids appeared in the report but have no row in the merge paths:",
                "",
            ]
        )
        for mid in missing:
            lines.append(f"- `{mid}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ru_tfp_cold_artifacts(
    coverage_report: Path,
    out_dir: Path,
    *,
    dict_b_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """
    Write ``cold_concept_ids.txt`` (one id per line), ``cold_concepts.json``
    (full Dict B rows), and ``stayed_cold_readable.md`` (human table) for review.
    """
    ids = load_zero_link_ids_from_coverage_report(coverage_report)
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cold_concept_ids.txt").write_text(
        "\n".join(ids) + ("\n" if ids else ""),
        encoding="utf-8",
    )
    paths = dict_b_paths
    if not paths:
        root = Path(__file__).resolve().parents[2]
        base = root / "assets/data/engine_dynamics_v060/dict_b"
        paths = [
            base / "dict_b_seed.jsonl",
            base / "dict_b_tfp_ru_v060.jsonl",
            base / "dict_b_tfp.jsonl",
        ]
    concepts = load_merged_dict_b(paths)
    by_id = {str(r["concept_id"]): r for r in concepts}
    rows = [by_id[i] for i in ids if i in by_id]
    missing = [i for i in ids if i not in by_id]
    payload = {
        "source_coverage_report": str(coverage_report.resolve()),
        "n_cold": len(ids),
        "concept_ids": ids,
        "rows": rows,
        "missing_in_dict_b": missing,
    }
    write_json(out_dir / "cold_concepts.json", payload)
    md_path = out_dir / "stayed_cold_readable.md"
    _write_stayed_cold_readable_md(
        md_path,
        coverage_report=coverage_report.resolve(),
        ids=ids,
        rows=rows,
        missing=missing,
    )
    return {
        "n_cold": len(ids),
        "n_rows_enriched": len(rows),
        "n_missing_in_dict_b": len(missing),
        "out_dir": str(out_dir),
        "stayed_cold_readable_md": str(md_path),
    }


_MAX_LINKS_PER_RESPONSE = 40


def _align_concept_batch_once(
    *,
    concept_rows: list[dict[str, Any]],
    phrases: list[str],
    pass_num: int,
    min_conf: float,
) -> list[dict[str, Any]]:
    """Single OpenAI call; keep ``links`` small so JSON is not truncated."""
    allowed = {str(r["concept_id"]) for r in concept_rows}
    catalog = _compact_catalog(concept_rows, label_max=96)
    pass_note = {
        1: "Pass 1: link clear phrase↔concept matches only.",
        2: "Pass 2: add defensible non-obvious links using labels/definitions sense.",
        3: "Pass 3: recall — link plausible clinical phrases even if wording is indirect.",
    }.get(pass_num, "")
    system = (
        "You align Russian clinical/TFP corpus phrases to concept_id keys. "
        "JSON only. concept_id MUST be exactly one of the ids in the catalog block. "
        "Each phrase at most one concept_id. Copy phrase strings EXACTLY from the JSON array. "
        f"The links array MUST have at most {_MAX_LINKS_PER_RESPONSE} objects (hard cap). "
        "Prefer the strongest matches only."
    )
    phrases = [_sanitize_llm_string(p) for p in phrases]
    phrases = [p for p in phrases if p]
    user = f"""{pass_note}
Min confidence to emit: {min_conf}

Catalog (only these concept_id values are legal):
{catalog}

Corpus phrases (verbatim JSON array):
{json.dumps(phrases, ensure_ascii=False)}

Return JSON: {{"links": [{{"phrase": "verbatim from array", "concept_id": "must be in catalog", "confidence": 0.0}}]}}
Hard rule: len(links) <= {_MAX_LINKS_PER_RESPONSE}.
"""
    tag = (
        f"pass{pass_num}/concepts={concept_rows[0]['concept_id']}.."
        f"{concept_rows[-1]['concept_id']}/n_phrases={len(phrases)}"
    )
    raw = chat_json(
        system=system,
        user=user,
        temperature=0.1 + 0.04 * pass_num,
        max_tokens=16384,
        call_tag=tag,
    )
    links = raw.get("links") if isinstance(raw, dict) else None
    if not isinstance(links, list):
        raise ValueError("expected {{links: [...]}}")
    phrase_set = set(phrases)
    out: list[dict[str, Any]] = []
    for item in links[: _MAX_LINKS_PER_RESPONSE + 5]:
        if not isinstance(item, dict):
            continue
        ph = str(item.get("phrase", "")).strip()
        cid = str(item.get("concept_id", "")).strip()
        conf = float(item.get("confidence") or 0.0)
        if ph not in phrase_set or cid not in allowed or conf < min_conf:
            continue
        out.append({"phrase": ph, "concept_id": cid, "confidence": conf})
    return out


def _align_concept_batch_slice(
    *,
    concept_rows: list[dict[str, Any]],
    phrases: list[str],
    pass_num: int,
    min_conf: float,
    min_phrase_split: int = 14,
) -> list[dict[str, Any]]:
    """
    Align with automatic bisection if JSON is truncated or invalid.
    Below ``min_phrase_split`` phrases, failures return [] (skip batch).
    """
    if not phrases:
        return []

    def go(phs: list[str]) -> list[dict[str, Any]]:
        if not phs:
            return []
        try:
            return _align_concept_batch_once(
                concept_rows=concept_rows,
                phrases=phs,
                pass_num=pass_num,
                min_conf=min_conf,
            )
        except _BISECT_EXC as exc:
            if len(phs) <= min_phrase_split:
                print(
                    f"ru-tfp-align: skipping align for {len(concept_rows)} concepts "
                    f"x {len(phs)} phrases after error: {exc}"
                )
                return []
            mid = max(1, len(phs) // 2)
            return go(phs[:mid]) + go(phs[mid:])

    return go(phrases)


def _align_chunk(
    *,
    catalog: str,
    phrases: list[str],
    pass_num: int,
    min_conf: float,
    cold_concepts: list[str] | None,
) -> list[dict[str, Any]]:
    cold_note = ""
    if cold_concepts:
        cold_note = (
            "\nConcepts with very few links so far (prefer these when plausible):\n"
            + "\n".join(cold_concepts[:40])
        )
    pass_note = {
        1: "Pass 1: high-precision only; link clear matches.",
        2: "Pass 2: add non-obvious but defensible links; disambiguate using labels.",
        3: "Pass 3: recall-oriented; include plausible borderline matches.",
    }.get(pass_num, "")
    system = (
        "You map Russian clinical/TFP corpus phrases to exact concept_id keys from the catalog. "
        "JSON only. Each phrase at most one concept_id. Phrase strings must be copied EXACTLY from the list."
    )
    user = f"""{pass_note}
{cold_note}
Min confidence to emit: {min_conf}

Catalog (concept_id: preferred_label):
{catalog}

Corpus phrases (verbatim):
{json.dumps(phrases, ensure_ascii=False)}

Return JSON: {{"links": [{{"phrase": "verbatim from list", "concept_id": "from catalog", "confidence": 0.0}}]}}
"""
    raw = chat_json(
        system=system,
        user=user,
        temperature=0.12 + 0.03 * pass_num,
        call_tag=f"pass{pass_num}/phrase_chunk/n_phrases={len(phrases)}",
    )
    links = raw.get("links") if isinstance(raw, dict) else None
    if not isinstance(links, list):
        raise ValueError("expected {{links: [...]}}")
    phrase_set = set(phrases)
    out: list[dict[str, Any]] = []
    for item in links:
        if not isinstance(item, dict):
            continue
        ph = str(item.get("phrase", "")).strip()
        cid = str(item.get("concept_id", "")).strip()
        conf = float(item.get("confidence") or 0.0)
        if ph not in phrase_set or not cid or conf < min_conf:
            continue
        out.append({"phrase": ph, "concept_id": cid, "confidence": conf})
    return out


def _merge_links(
    best: dict[str, tuple[str, float]],
    new_links: list[dict[str, Any]],
) -> None:
    for ln in new_links:
        ph = ln["phrase"]
        cid = ln["concept_id"]
        conf = float(ln["confidence"])
        if ph not in best or conf > best[ph][1]:
            best[ph] = (cid, conf)


def _to_dict_a_rows(
    best: dict[str, tuple[str, float]],
    *,
    version: str = "v0.6.0-tfp-ru-align",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # merge same normalized_form → union candidates, max priority
    by_nf: dict[str, dict[str, Any]] = {}
    for ph, (cid, conf) in sorted(best.items(), key=lambda x: (-x[1][1], x[0])):
        nf = normalize_text(ph)["canonical_text"]
        if not nf:
            continue
        pr = max(1, min(10, int(round(conf * 10))))
        if nf not in by_nf:
            by_nf[nf] = {
                "entry_id": "",
                "surface_form": ph,
                "normalized_form": nf,
                "match_type": "phrase",
                "candidate_concept_ids": [cid],
                "priority": pr,
                "version": version,
            }
        else:
            row = by_nf[nf]
            if cid not in row["candidate_concept_ids"]:
                row["candidate_concept_ids"].append(cid)
            row["priority"] = max(int(row["priority"]), pr)
    for i, row in enumerate(by_nf.values(), start=1):
        row["entry_id"] = f"RU-TFP-{i:05d}"
        rows.append(row)
    return rows


def run_ru_tfp_corpus_align(
    corpus: Path,
    workdir: Path,
    *,
    dict_b_paths: list[Path] | None = None,
    passes: int = 3,
    phrase_chunk_size: int = 280,
    concept_batch_size: int = 14,
    align_mode: str = "concept_batch",
    phrase_sub_batch: int = 150,
    min_freq: int = 2,
    max_phrases: int | None = 6000,
    concept_ids_only: frozenset[str] | None = None,
    seed_dict_a: Path | None = None,
) -> dict[str, Any]:
    require_openai_key()
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    paths = dict_b_paths
    if not paths:
        root = Path(__file__).resolve().parents[2]
        base = root / "assets/data/engine_dynamics_v060/dict_b"
        paths = [
            base / "dict_b_seed.jsonl",
            base / "dict_b_tfp_ru_v060.jsonl",
            base / "dict_b_tfp.jsonl",
        ]
    concepts = load_merged_dict_b(paths)
    if len(concepts) != 283:
        print(f"warning: merged Dict B has {len(concepts)} concepts (expected 283 for full TFP merge)")
    if concept_ids_only is not None:
        filt = [r for r in concepts if str(r["concept_id"]) in concept_ids_only]
        missing = concept_ids_only - {str(r["concept_id"]) for r in filt}
        if missing:
            print(
                f"ru-tfp-align: warning: {len(missing)} ids from --only-zero-from not in merged Dict B (skipped)"
            )
        concepts = filt
        if not concepts:
            raise ValueError("concept filter (--only-zero-from / concept_ids_only) removed all concepts")
        print(f"ru-tfp-align: concept filter active → {len(concepts)} concepts (subset run)")
    id_set = {str(r["concept_id"]) for r in concepts}
    mode = (align_mode or "concept_batch").strip().lower()
    if mode not in ("concept_batch", "phrase_chunk"):
        raise ValueError("align_mode must be concept_batch or phrase_chunk")
    print(f"ru-tfp-align: mode={mode} passes={passes} max_phrases={max_phrases}")

    pool_full = _phrase_pool(corpus, min_freq=min_freq)
    n_raw = len(pool_full)
    pool = pool_full
    if max_phrases is not None and int(max_phrases) > 0 and len(pool) > int(max_phrases):
        pool = pool[: int(max_phrases)]
        print(f"phrase pool: capped {n_raw} → {len(pool)} (max_phrases={max_phrases})")
    write_json(
        workdir / "phrase_pool.json",
        {
            "n_phrases": len(pool),
            "n_phrases_before_cap": n_raw,
            "max_phrases": max_phrases,
            "sample": pool[:30],
        },
    )

    best: dict[str, tuple[str, float]] = {}
    if seed_dict_a is not None:
        sp = seed_dict_a.resolve()
        if sp.exists():
            seed_links = [
                {"phrase": ph, "concept_id": cid, "confidence": conf}
                for ph, (cid, conf) in _load_best_from_dict_a(sp).items()
            ]
            _merge_links(best, seed_links)
            print(f"ru-tfp-align: seeded {len(best)} phrase mappings from {sp}")

    # Slightly lower floors; concept_batch prompts are narrower so model can be less timid
    conf_floors = {1: 0.48, 2: 0.42, 3: 0.36}
    catalog_full = _compact_catalog(concepts)

    for pnum in range(1, passes + 1):
        coverage = {cid: 0 for cid in id_set}
        for _ph, (cid, _c) in best.items():
            coverage[cid] = coverage.get(cid, 0) + 1
        cold = sorted(id_set, key=lambda c: (coverage.get(c, 0), c))[:60]

        n = len(pool)
        a = (pnum - 1) * n // passes
        b = pnum * n // passes
        pass_phrases = pool[a:b] if b > a else pool
        pass_links: list[dict[str, Any]] = []
        n_api = 0

        if mode == "concept_batch":
            sb = int(phrase_sub_batch)
            if sb <= 0:
                phrase_parts: list[list[str]] = [pass_phrases]
            else:
                phrase_parts = (
                    _chunk(pass_phrases, sb) if len(pass_phrases) > sb else [pass_phrases]
                )
            cbatches = _chunk_list(concepts, max(1, int(concept_batch_size)))
            for cb in cbatches:
                for phs in phrase_parts:
                    links = _align_concept_batch_slice(
                        concept_rows=cb,
                        phrases=phs,
                        pass_num=pnum,
                        min_conf=conf_floors.get(pnum, 0.4),
                    )
                    n_api += 1
                    pass_links.extend(links)
                    _merge_links(best, links)
        else:
            chunks = _chunk(pass_phrases, phrase_chunk_size)
            for ch in chunks:
                links = _align_chunk(
                    catalog=catalog_full,
                    phrases=ch,
                    pass_num=pnum,
                    min_conf=conf_floors.get(pnum, 0.5),
                    cold_concepts=cold,
                )
                links = [ln for ln in links if ln["concept_id"] in id_set]
                n_api += 1
                pass_links.extend(links)
                _merge_links(best, links)

        coverage = {cid: 0 for cid in id_set}
        for _ph, (cid, _c) in best.items():
            coverage[cid] = coverage.get(cid, 0) + 1
        write_json(
            workdir / f"pass_{pnum}_summary.json",
            {
                "align_mode": mode,
                "n_api_calls": n_api,
                "n_links_raw": len(pass_links),
                "n_phrases_mapped_total": len(best),
                "concepts_with_zero_links": sum(1 for c in id_set if coverage.get(c, 0) == 0),
            },
        )
        # Checkpoint the actual accumulated links after every pass, not just the summary
        # counts -- `best` only lives in memory otherwise, so a kill between passes (session
        # teardown, OOM, etc.) loses real paid-for API work with nothing recoverable. Cheap:
        # this is the same rows write the end of the function already does, just per-pass too.
        write_jsonl(workdir / f"pass_{pnum}_checkpoint.jsonl", _to_dict_a_rows(best))

    rows = _to_dict_a_rows(best)
    write_jsonl(workdir / "dict_a_tfp_ru_aligned.jsonl", rows)
    coverage = {cid: 0 for cid in id_set}
    for _ph, (cid, _c) in best.items():
        coverage[cid] = coverage.get(cid, 0) + 1
    report = {
        "align_mode": mode,
        "n_concepts_catalog": len(id_set),
        "n_phrases_unique_mapped": len(best),
        "n_dict_a_rows": len(rows),
        "concepts_with_zero_links": sorted([c for c in id_set if coverage.get(c, 0) == 0]),
        "passes": passes,
        "concept_ids_only": sorted(concept_ids_only) if concept_ids_only is not None else None,
        "seed_dict_a": str(seed_dict_a.resolve()) if seed_dict_a and seed_dict_a.exists() else None,
    }
    write_json(workdir / "coverage_report.json", report)
    return report
