#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Post–cold-pass: propose LEVEL-4-style lexical markers via OpenAI for concepts that
still need YAML/session coverage (e.g. ``concepts_with_zero_links`` after ``ru-tfp-align``).

**Inputs**
  - Cold ID list: ``--cold-pack DIR`` (uses ``cold_concept_ids.txt`` + enriches from ``cold_concepts.json``),
    or ``--coverage-report JSON``, or ``--concept-ids-file TXT`` (one id per line).
  - Corpus directory (markdown) for phrase pool (same extraction as ``ru-tfp-align``).

**Outputs** (under ``--workdir``)
  - ``lexical_markers_post_cold.yaml`` — review before merging into ``hesperia/ontology/dictA/lexical_markers.yaml``
  - ``post_cold_markers_report.json`` — counts, paths, id coverage
  - ``PROMPT_SNAPSHOT.md`` — frozen system prompt + user template + one example user block (audit)

**Requires** ``OPENAI_API_KEY`` unless ``HESPERIA_CALIB_MOCK_OPENAI=1``.

Example::

    python3 tools/post_cold_lexical_markers_align.py \\
      --cold-pack outputs/dict_calibration/ru_tfp_align_run2/cold_pack \\
      --corpus research/_noone_local/2_cleaned \\
      --workdir outputs/dict_calibration/post_cold_markers_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.dict_calibration.jsonl_util import write_json  # noqa: E402
from tools.dict_calibration.openai_json import (  # noqa: E402
    calib_mock_openai,
    chat_json,
    load_repo_dotenv,
    require_openai_key,
)
from tools.dict_calibration.ru_tfp_corpus_align import (  # noqa: E402
    _BISECT_EXC,
    _phrase_pool,
    load_zero_link_ids_from_coverage_report,
)

# ---------------------------------------------------------------------------
# Explicit prompts (edit here; PROMPT_SNAPSHOT.md copies this for audit)
# ---------------------------------------------------------------------------

MAX_ENTRIES_PER_RESPONSE = 36

POST_COLD_SYSTEM = """You are aligning Russian clinical / TFP session text to a fixed concept catalog.

Rules:
- Output ONE JSON object only (no markdown fences).
- Each entry links a Russian marker (single word OR a short 2–3 word phrase) to exactly one concept_id from the catalog block.
- concept_id MUST be copied verbatim from the catalog; no invented ids.
- Prefer markers that plausibly appear in therapist–patient Russian transcripts.
- Use lowercase for marker strings.
- Do not output duplicate (marker, concept_id) pairs; keep the strongest confidence if unsure.
- The entries array MUST have at most """ + str(
    MAX_ENTRIES_PER_RESPONSE
) + """ objects (hard cap)."""

POST_COLD_USER_TEMPLATE = """Context: these concepts had weak or no phrase coverage after a first alignment pass. Propose high-value markers that should fire when this clinical material is discussed.

Min confidence to emit: {min_conf}

--- Catalog (ONLY these concept_id values are legal; each line is id: short label) ---
{catalog}

--- Corpus phrases (frequent Russian phrases from the same corpus as alignment; use as inspiration; copy marker wording from real Russian, not English) ---
{phrases_json}

Return JSON exactly in this shape:
{{"entries": [{{"marker": "russian text", "concept_id": "must match catalog", "confidence": 0.0}}]}}

Hard rule: len(entries) <= """ + str(
    MAX_ENTRIES_PER_RESPONSE
) + """.
"""


def _compact_catalog(rows: list[dict[str, Any]], *, label_max: int = 96) -> str:
    lines: list[str] = []
    for r in rows:
        cid = str(r.get("id", ""))
        lab = str(r.get("label") or "")[:label_max]
        lines.append(f"{cid}: {lab}")
    return "\n".join(lines)


def _read_ids_file(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def _dict_b_row_to_node(row: dict[str, Any]) -> dict[str, Any]:
    cid = str(row.get("concept_id", ""))
    areas = row.get("area_ids")
    area = str(areas[0]) if isinstance(areas, list) and areas else "?"
    fams = row.get("family_ids")
    fam = str(fams[0]) if isinstance(fams, list) and fams else "?"
    return {
        "id": cid,
        "label": str(row.get("preferred_label") or "")[:200],
        "area": area,
        "family": fam,
        "definition": str(row.get("definition") or "")[:1200],
        "example_context": "",
    }


def _load_cold_concept_rows(
    cold_pack: Path | None,
    concept_ids: list[str],
    *,
    nodes_yaml: Path,
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    data = yaml.safe_load(nodes_yaml.read_text(encoding="utf-8"))
    for n in data.get("nodes") or []:
        if isinstance(n, dict) and n.get("id"):
            by_id[str(n["id"])] = n

    cold_rows: dict[str, dict[str, Any]] = {}
    if cold_pack is not None:
        cj = cold_pack / "cold_concepts.json"
        if cj.is_file():
            payload = json.loads(cj.read_text(encoding="utf-8"))
            for r in payload.get("rows") or []:
                if isinstance(r, dict) and r.get("concept_id"):
                    cold_rows[str(r["concept_id"])] = r

    out: list[dict[str, Any]] = []
    missing: list[str] = []
    for cid in concept_ids:
        if cid in by_id:
            out.append(by_id[cid])
        elif cid in cold_rows:
            out.append(_dict_b_row_to_node(cold_rows[cid]))
        else:
            missing.append(cid)
    if missing:
        print(f"warning: {len(missing)} ids not in concept_nodes or cold_concepts.json (skipped): {missing[:8]}…")
    return out


def _align_batch(
    *,
    concept_rows: list[dict[str, Any]],
    phrases: list[str],
    min_conf: float,
) -> list[dict[str, Any]]:
    allowed = {str(r["id"]) for r in concept_rows}
    catalog = _compact_catalog(concept_rows, label_max=96)
    user = POST_COLD_USER_TEMPLATE.format(
        min_conf=min_conf,
        catalog=catalog,
        phrases_json=json.dumps(phrases, ensure_ascii=False),
    )
    raw = chat_json(
        system=POST_COLD_SYSTEM,
        user=user,
        temperature=0.1,
        max_tokens=16384,
    )
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        raise ValueError("expected {entries: [...]}")
    phrase_set = set(phrases)
    out: list[dict[str, Any]] = []
    for item in entries[: MAX_ENTRIES_PER_RESPONSE + 5]:
        if not isinstance(item, dict):
            continue
        mk = str(item.get("marker", "")).strip().lower()
        cid = str(item.get("concept_id", "")).strip()
        conf = float(item.get("confidence") or 0.0)
        if not mk or cid not in allowed or conf < min_conf:
            continue
        if len(mk) < 2:
            continue
        out.append(
            {
                "marker": mk,
                "concept_id": cid,
                "confidence": conf,
                "_corpus_hit": mk in phrase_set,
            }
        )
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
            return _align_batch(concept_rows=concept_rows, phrases=phs, min_conf=min_conf)
        except _BISECT_EXC as exc:
            if len(phs) <= min_split:
                print(f"post-cold-markers: skip {len(concept_rows)} concepts × {len(phs)} phrases: {exc}")
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


def _merge_seed_yaml(path: Path) -> dict[tuple[str, str], float]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return {}
    out: dict[tuple[str, str], float] = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        mk = str(e.get("marker", "")).strip().lower()
        cid = str(e.get("concept_id", "")).strip()
        w = float(e.get("weight", 0.5))
        if mk and cid:
            out[(mk, cid)] = max(out.get((mk, cid), 0.0), w)
    return out


def run(
    *,
    concept_rows: list[dict[str, Any]],
    phrase_pool: list[str],
    workdir: Path,
    concept_batch_size: int,
    phrase_sub_batch: int,
    min_conf: float,
    seed_yaml: Path | None,
) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    merged: dict[tuple[str, str], float] = {}
    if seed_yaml is not None:
        merged.update(_merge_seed_yaml(seed_yaml))

    cb = max(1, int(concept_batch_size))
    for i in range(0, len(concept_rows), cb):
        batch = concept_rows[i : i + cb]
        rows = _slice_align(
            batch,
            phrase_pool,
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
            "Post-cold LLM-proposed lexical markers (draft). Review before merging into canonical lexical_markers.yaml."
        ),
        "marker_count": len(entries_out),
        "concept_count": len({e["concept_id"] for e in entries_out}),
        "entries": entries_out,
    }
    yaml_path = workdir / "lexical_markers_post_cold.yaml"
    yaml_path.write_text(
        yaml.dump(out_yaml, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    # Audit trail: prompts + one example user message
    example_batch = concept_rows[: min(6, len(concept_rows))]
    example_phrases = phrase_pool[: min(40, len(phrase_pool))]
    example_user = POST_COLD_USER_TEMPLATE.format(
        min_conf=min_conf,
        catalog=_compact_catalog(example_batch, label_max=96),
        phrases_json=json.dumps(example_phrases, ensure_ascii=False),
    )
    snapshot = workdir / "PROMPT_SNAPSHOT.md"
    snapshot.write_text(
        "# Post-cold lexical markers — prompt snapshot\n\n"
        "## SYSTEM\n\n```\n"
        + POST_COLD_SYSTEM
        + "\n```\n\n## USER template\n\n```\n"
        + POST_COLD_USER_TEMPLATE
        + "\n```\n\n## Example user (first batch sample)\n\n```\n"
        + example_user
        + "\n```\n",
        encoding="utf-8",
    )

    cold_cids = {str(r["id"]) for r in concept_rows}
    covered = {e["concept_id"] for e in entries_out}
    report = {
        "n_input_concepts": len(concept_rows),
        "n_concepts_with_at_least_one_marker": len(cold_cids & covered),
        "n_phrase_pool": len(phrase_pool),
        "n_concept_batches": (len(concept_rows) + cb - 1) // cb,
        "n_proposed_entries": len(entries_out),
        "output_yaml": str(yaml_path),
        "prompt_snapshot": str(snapshot),
        "mock_openai": calib_mock_openai(),
    }
    write_json(workdir / "post_cold_markers_report.json", report)
    return report


def main() -> int:
    load_repo_dotenv()
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--cold-pack",
        type=Path,
        help="Directory with cold_concept_ids.txt (+ optional cold_concepts.json for stubs)",
    )
    src.add_argument(
        "--coverage-report",
        type=Path,
        help="coverage_report.json → concepts_with_zero_links",
    )
    src.add_argument(
        "--concept-ids-file",
        type=Path,
        help="Text file: one concept_id per line",
    )
    p.add_argument("--corpus", required=True, type=Path, help="Markdown tree (phrase pool)")
    p.add_argument("--workdir", required=True, type=Path, help="Output directory")
    p.add_argument(
        "--concept-nodes",
        type=Path,
        default=_ROOT / "hesperia/ontology/dictB/concept_nodes.yaml",
        help="Fallback ontology for labels/definitions",
    )
    p.add_argument("--concept-batch-size", type=int, default=8)
    p.add_argument("--phrase-sub-batch", type=int, default=100)
    p.add_argument("--min-freq", type=int, default=2)
    p.add_argument("--max-phrases", type=int, default=4000, help="0 = no cap")
    p.add_argument("--min-conf", type=float, default=0.42)
    p.add_argument(
        "--seed-yaml",
        type=Path,
        default=None,
        help="Existing lexical_markers.yaml: merge (max confidence/weight wins)",
    )
    args = p.parse_args()

    if not calib_mock_openai():
        require_openai_key()

    if args.cold_pack is not None:
        ids_path = args.cold_pack / "cold_concept_ids.txt"
        if not ids_path.is_file():
            print(f"Missing {ids_path}", file=sys.stderr)
            return 1
        concept_ids = _read_ids_file(ids_path)
        rows = _load_cold_concept_rows(args.cold_pack, concept_ids, nodes_yaml=args.concept_nodes)
    elif args.coverage_report is not None:
        concept_ids = load_zero_link_ids_from_coverage_report(args.coverage_report)
        rows = _load_cold_concept_rows(None, concept_ids, nodes_yaml=args.concept_nodes)
    else:
        concept_ids = _read_ids_file(args.concept_ids_file)
        rows = _load_cold_concept_rows(None, concept_ids, nodes_yaml=args.concept_nodes)

    if not rows:
        print("No concept rows resolved — check ids and concept_nodes.yaml", file=sys.stderr)
        return 1

    pool_full = _phrase_pool(args.corpus.resolve(), min_freq=int(args.min_freq))
    mx = int(args.max_phrases)
    pool = pool_full if mx <= 0 else pool_full[:mx]

    rep = run(
        concept_rows=rows,
        phrase_pool=pool,
        workdir=args.workdir.resolve(),
        concept_batch_size=int(args.concept_batch_size),
        phrase_sub_batch=int(args.phrase_sub_batch),
        min_conf=float(args.min_conf),
        seed_yaml=args.seed_yaml.resolve() if args.seed_yaml else None,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
