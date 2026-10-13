#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Seal v0_6_0_clr_v052_4: concept recovery + C prune target + link rebuild.

Single-flow driver per GRACE-TRIAGE-HESPERIA-STABILIZE-v052_4 (cursor repo).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from prune_dict_c_hprom_r2 import _concepts_per_norm_counts, _quality_score  # noqa: E402
SRC_VER = "v0_6_0_clr_v052_3"
DST_VER = "v0_6_0_clr_v052_4"
OLD_V = "v0_6_0_clr_v052_3"
NEW_V = "v0_6_0_clr_v052_4"

_RU = re.compile(r"[а-яА-ЯёЁ]")


def _has_ru(s: str) -> bool:
    return bool(_RU.search(s))


def _words(s: str) -> list[str]:
    return [w for w in re.split(r"\s+", s.strip()) if w]


def _phrase_from_lexicals(lexicals: list[str], preferred_label: str) -> tuple[str, int]:
    """Return (normalized_form, token_count) for dict_c, 2 or 3 tokens."""
    for lx in lexicals:
        if not _has_ru(lx):
            continue
        parts = _words(lx)
        if len(parts) >= 3:
            return (" ".join(parts[:3]), 3)
        if len(parts) == 2:
            return (" ".join(parts), 2)
    parts = _words(preferred_label.replace("—", " ").replace("–", " "))
    if len(parts) >= 3:
        return (" ".join(parts[:3]), 3)
    if len(parts) == 2:
        return (" ".join(parts), 2)
    if len(parts) == 1 and len(parts[0]) > 3:
        return (parts[0][:40], 2)  # degenerate; avoid
    raise ValueError(f"cannot build 2-3 token phrase from {lexicals!r} / {preferred_label!r}")


def _max_c_id(rows: list[dict[str, Any]]) -> int:
    m = 0
    for r in rows:
        eid = str(r.get("entry_id", ""))
        if eid.startswith("C_CAL-"):
            try:
                m = max(m, int(eid.split("-", 1)[1]))
            except ValueError:
                pass
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-c", type=int, default=22000, help="Target dict_c row count after prune")
    ap.add_argument("--recovery-phrases", type=int, default=2, help="C phrases per lost concept (2-5)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = REPO / "assets" / "calibration" / "dicts"
    src = base / SRC_VER
    dst = base / DST_VER
    if not (src / "dict_c.jsonl").is_file():
        raise SystemExit(f"missing {src}")

    # --- lost concepts ---
    def concepts_from_links(p: Path) -> set[str]:
        s: set[str] = set()
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            cid = o.get("concept_id")
            if cid:
                s.add(str(cid))
        return s

    l2 = concepts_from_links(src.parent / "v0_6_0_clr_v052_2" / "links.jsonl")
    l3 = concepts_from_links(src / "links.jsonl")
    lost = sorted(l2 - l3)

    # v052_2 lexicals per lost concept
    by_c: dict[str, list[str]] = {c: [] for c in lost}
    for line in (base / "v0_6_0_clr_v052_2" / "links.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        c = o.get("concept_id")
        if c in by_c and o.get("lexical"):
            by_c[str(c)].append(str(o["lexical"]))

    # dict_b meta
    b_meta: dict[str, dict[str, Any]] = {}
    for line in (src / "dict_b.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        cid = o.get("concept_id")
        if cid:
            b_meta[str(cid)] = o

    # load dict_c
    dc_rows: list[dict[str, Any]] = []
    for line in (src / "dict_c.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        o = dict(o)
        o["version"] = NEW_V
        dc_rows.append(o)

    next_num = _max_c_id(dc_rows) + 1
    recovery_ids: set[str] = set()

    for cid in lost:
        meta = b_meta.get(cid, {})
        pl = str(meta.get("preferred_label") or "")
        lexs = by_c.get(cid, [])
        phrases: list[tuple[str, int]] = []
        try:
            phrases.append(_phrase_from_lexicals(lexs, pl))
        except ValueError:
            parts = _words(pl.replace("—", " "))
            if len(parts) >= 3:
                phrases.append((" ".join(parts[:3]), 3))
            elif len(parts) == 2:
                phrases.append((" ".join(parts), 2))
            else:
                raise SystemExit(f"recovery failed for {cid}")
        # second phrase: alternate lexical or shift window
        if args.recovery_phrases >= 2 and len(lexs) > 1:
            try:
                p2 = _phrase_from_lexicals(lexs[1:], pl)
                if p2[0] != phrases[0][0]:
                    phrases.append(p2)
            except ValueError:
                pass
        if len(phrases) < args.recovery_phrases and len(lexs) > 0:
            parts = _words(lexs[0])
            if len(parts) >= 4:
                alt = " ".join(parts[1:4])
                if alt != phrases[0][0]:
                    phrases.append((alt, 3))

        for norm, tc in phrases[: args.recovery_phrases]:
            eid = f"C_CAL-{next_num:05d}"
            next_num += 1
            recovery_ids.add(eid)
            dc_rows.append(
                {
                    "entry_id": eid,
                    "surface_form": norm,
                    "normalized_form": norm,
                    "token_count": tc,
                    "match_type": "exact_phrase",
                    "candidate_concept_ids": [cid],
                    "priority": 99,
                    "version": NEW_V,
                    "status": "active",
                    "language": "en",
                }
            )

    cpn_full = _concepts_per_norm_counts(dc_rows)

    def qscore(r: dict[str, Any]) -> float:
        nk = str(r.get("normalized_form", "")).strip().casefold()
        return float(_quality_score(r, cpn_full.get(nk, 1)))

    rec_set = recovery_ids
    rest = [r for r in dc_rows if str(r.get("entry_id")) not in rec_set]
    rest.sort(key=lambda r: (qscore(r), str(r.get("entry_id"))), reverse=True)
    cap = max(0, args.target_c - len(rec_set))
    kept = [r for r in dc_rows if str(r.get("entry_id")) in rec_set]
    kept.extend(rest[:cap])
    # dedupe by entry_id
    seen: set[str] = set()
    out_c: list[dict[str, Any]] = []
    for r in kept:
        eid = str(r.get("entry_id"))
        if eid in seen:
            continue
        seen.add(eid)
        out_c.append(r)

    print(
        json.dumps(
            {
                "lost_concepts": len(lost),
                "recovery_c_rows": len(recovery_ids),
                "dict_c_before_prune": len(dc_rows),
                "dict_c_after": len(out_c),
                "distinct_concepts_in_c": len(
                    {str(c) for r in out_c for c in (r.get("candidate_concept_ids") or [])}
                ),
            },
            indent=2,
        )
    )

    if args.dry_run:
        return 0

    dst.mkdir(parents=True, exist_ok=True)

    def bump_copy(name: str) -> None:
        sp, dp = src / name, dst / name
        if not sp.is_file():
            return
        text = sp.read_text(encoding="utf-8")
        text = text.replace(OLD_V, NEW_V)
        dp.write_text(text, encoding="utf-8")

    bump_copy("dict_a.jsonl")
    bump_copy("dict_b.jsonl")
    bump_copy("metrics_baseline_v052_2.json")
    if (src / "summary.json").is_file():
        bump_copy("summary.json")

    (dst / "dict_c.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out_c) + "\n",
        encoding="utf-8",
    )

    # rebuild links
    da_rows = [
        json.loads(line)
        for line in (dst / "dict_a.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    link_n = 1

    def link_line(
        sd: str,
        eid: str,
        surf: str,
        norm: str,
        cid: str,
        mt: str,
        bw: float,
    ) -> str:
        nonlocal link_n
        o = {
            "link_id": f"L_{link_n:07d}",
            "source_dict": sd,
            "source_entry_id": eid,
            "source_surface": surf,
            "normalized": norm,
            "concept_id": cid,
            "match_type": mt,
            "base_weight": bw,
            "status": "active",
            "version": NEW_V,
        }
        link_n += 1
        return json.dumps(o, ensure_ascii=False)

    lines_out: list[str] = []
    for r in da_rows:
        eid = str(r.get("entry_id", ""))
        cids = r.get("candidate_concept_ids") or []
        if not cids:
            continue
        cid = str(cids[0])
        surf = str(r.get("surface_form") or r.get("normalized_form") or "")
        norm = str(r.get("normalized_form") or surf)
        lines_out.append(link_line("A", eid, surf, norm, cid, "exact_token", 0.6))
    for r in out_c:
        eid = str(r.get("entry_id", ""))
        cids = r.get("candidate_concept_ids") or []
        if not cids:
            continue
        cid = str(cids[0])
        surf = str(r.get("surface_form") or "")
        norm = str(r.get("normalized_form") or surf)
        lines_out.append(link_line("C", eid, surf, norm, cid, "exact_phrase", 0.9))

    (dst / "links.jsonl").write_text("\n".join(lines_out) + "\n", encoding="utf-8")

    # distinct concepts in links
    lc: set[str] = set()
    for line in lines_out:
        lc.add(json.loads(line)["concept_id"])
    print(json.dumps({"links_rows": len(lines_out), "distinct_concepts_in_links": len(lc)}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
