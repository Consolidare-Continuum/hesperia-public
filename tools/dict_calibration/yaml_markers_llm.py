# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
LLM-assisted proposals for LEVEL-4 YAML markers (lexical_markers-style).

Writes **reviewable drafts** under ``outputs/`` — not canonical ``hesperia/ontology/dictA/`` until
human freeze. With ``HESPERIA_CALIB_MOCK_OPENAI=1`` (or ``run_pipeline.py --mock-llm``) runs
deterministically with **empty** proposed entries (pipeline wiring only; no semantic alignment).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .jsonl_util import write_json
from .openai_json import calib_mock_openai, chat_json, require_openai_key
from .ru_tfp_corpus_align import _BISECT_EXC, _phrase_pool

_REPO = Path(__file__).resolve().parents[2]
_CONCEPT_NODES = _REPO / "hesperia" / "ontology" / "dictB" / "concept_nodes.yaml"

ALL_AREAS = frozenset(f"A{i}" for i in range(1, 11))
PILOT_AREAS = frozenset({"A2", "A3", "A4", "A10"})
_MAX_ENTRIES_PER_CALL = 36


def _compact_nodes(rows: list[dict[str, Any]], *, label_max: int = 72) -> str:
    lines: list[str] = []
    for r in rows:
        cid = str(r.get("id", ""))
        lab = str(r.get("label") or "")[:label_max]
        lines.append(f"{cid}: {lab}")
    return "\n".join(lines)


def _align_markers_batch_once(
    *,
    concept_rows: list[dict[str, Any]],
    phrases: list[str],
    min_conf: float,
) -> list[dict[str, Any]]:
    allowed = {str(r["id"]) for r in concept_rows}
    catalog = _compact_nodes(concept_rows, label_max=96)
    system = (
        "You propose Russian lexical markers for TFP/Kernberg concept nodes. JSON only. "
        "concept_id MUST be exactly one of the ids in the catalog. "
        "marker: single word or 2–3 word phrase (lowercase in output). "
        f"At most {_MAX_ENTRIES_PER_CALL} entries per response. "
        "Prefer markers that could appear verbatim in clinical Russian text."
    )
    user = f"""Min confidence to emit: {min_conf}

Catalog (only these concept_id values are legal):
{catalog}

Corpus phrases for inspiration (verbatim JSON array; do not invent unrelated markers):
{json.dumps(phrases, ensure_ascii=False)}

Return JSON: {{"entries": [{{"marker": "ru phrase or word", "concept_id": "from catalog", "confidence": 0.0}}]}}
Hard rule: len(entries) <= {_MAX_ENTRIES_PER_CALL}.
"""
    raw = chat_json(
        system=system,
        user=user,
        temperature=0.12,
        max_tokens=8192,
    )
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        raise ValueError("expected {{entries: [...]}}")
    phrase_set = set(phrases)
    out: list[dict[str, Any]] = []
    for item in entries[: _MAX_ENTRIES_PER_CALL + 5]:
        if not isinstance(item, dict):
            continue
        mk = str(item.get("marker", "")).strip().lower()
        cid = str(item.get("concept_id", "")).strip()
        conf = float(item.get("confidence") or 0.0)
        if not mk or cid not in allowed or conf < min_conf:
            continue
        if len(mk) < 2:
            continue
        out.append({"marker": mk, "concept_id": cid, "confidence": conf, "_phrase_hint": bool(mk in phrase_set)})
    return out


def _slice_align(
    concept_rows: list[dict[str, Any]],
    phrases: list[str],
    *,
    min_conf: float,
    phrase_sub_batch: int,
    min_split: int = 12,
) -> list[dict[str, Any]]:
    if not phrases:
        return []

    def go(phs: list[str]) -> list[dict[str, Any]]:
        if not phs:
            return []
        try:
            return _align_markers_batch_once(
                concept_rows=concept_rows,
                phrases=phs,
                min_conf=min_conf,
            )
        except _BISECT_EXC as exc:
            if len(phs) <= min_split:
                print(f"yaml-markers-llm: skip batch {len(concept_rows)} concepts x {len(phs)} phrases: {exc}")
                return []
            mid = max(1, len(phs) // 2)
            return go(phs[:mid]) + go(phs[mid:])

    sb = int(phrase_sub_batch)
    if sb <= 0:
        return go(phrases)
    acc: list[dict[str, Any]] = []
    for i in range(0, len(phrases), sb):
        acc.extend(go(phrases[i : i + sb]))
    return acc


def run_yaml_markers_llm(
    corpus: Path,
    workdir: Path,
    *,
    pilot_areas: bool = False,
    concept_batch_size: int = 10,
    phrase_sub_batch: int = 80,
    min_freq: int = 2,
    max_phrases: int = 2000,
    min_conf: float = 0.45,
    nodes_path: Path | None = None,
) -> dict[str, Any]:
    """
    Load concept nodes, phrase pool from corpus, batch LLM calls, merge proposed entries.

    Mock OpenAI: set ``HESPERIA_CALIB_MOCK_OPENAI=1`` → **zero** LLM rows (deterministic).
    """
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    np = nodes_path or _CONCEPT_NODES
    data = yaml.safe_load(np.read_text(encoding="utf-8"))
    nodes = [n for n in (data.get("nodes") or []) if isinstance(n, dict)]
    areas = PILOT_AREAS if pilot_areas else ALL_AREAS
    filtered = [n for n in nodes if str(n.get("area", "")) in areas and n.get("id")]
    pool_full = _phrase_pool(corpus, min_freq=min_freq)
    pool = pool_full[:max_phrases] if max_phrases > 0 and len(pool_full) > max_phrases else pool_full

    merged: dict[tuple[str, str], float] = {}
    cb = max(1, int(concept_batch_size))
    for i in range(0, len(filtered), cb):
        batch = filtered[i : i + cb]
        rows = _slice_align(
            batch,
            pool,
            min_conf=min_conf,
            phrase_sub_batch=phrase_sub_batch,
        )
        for row in rows:
            key = (row["marker"], row["concept_id"])
            conf = float(row["confidence"])
            if key not in merged or conf > merged[key]:
                merged[key] = conf

    entries_out: list[dict[str, Any]] = []
    for (marker, cid), conf in sorted(merged.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
        entries_out.append(
            {
                "marker": marker,
                "concept_id": cid,
                "language": "ru",
                "weight": round(min(1.0, max(0.05, conf)), 3),
            }
        )

    out_yaml = {
        "version": 1,
        "domain": "TFP_KERNBERG",
        "language": "ru",
        "description": (
            "LLM-proposed lexical markers (draft; review before replacing canonical lexical_markers.yaml)."
        ),
        "marker_count": len(entries_out),
        "concept_count": len({e["concept_id"] for e in entries_out}),
        "entries": entries_out,
    }
    yaml_path = workdir / "lexical_markers_llm_proposed.yaml"
    yaml_path.write_text(
        yaml.dump(out_yaml, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    report: dict[str, Any] = {
        "n_concept_nodes": len(filtered),
        "n_phrase_pool": len(pool),
        "n_concept_batches": (len(filtered) + cb - 1) // cb,
        "n_proposed_entries": len(entries_out),
        "output_yaml": str(yaml_path),
        "mock_openai": calib_mock_openai(),
    }
    if calib_mock_openai():
        report["mock_mode_note"] = "HESPERIA_CALIB_MOCK_OPENAI=1 — proposals are empty/stub"
    write_json(workdir / "yaml_markers_llm_report.json", report)
    return report


def cmd_yaml_markers_llm_entry(args: Any) -> None:
    import os

    if getattr(args, "mock_llm", False):
        os.environ["HESPERIA_CALIB_MOCK_OPENAI"] = "1"
    else:
        require_openai_key()

    rep = run_yaml_markers_llm(
        Path(args.corpus),
        Path(args.workdir),
        pilot_areas=bool(args.pilot),
        concept_batch_size=int(args.concept_batch_size),
        phrase_sub_batch=int(args.phrase_sub_batch),
        min_freq=int(args.min_freq),
        max_phrases=int(args.max_phrases),
        min_conf=float(args.min_conf),
        nodes_path=Path(args.concept_nodes) if getattr(args, "concept_nodes", None) else None,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
