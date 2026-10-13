#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Regenerate extended RU natural corpus from Russian Wikipedia (CC BY-SA). Measurement fixture only."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TITLES_DEFAULT = ("Психотерапия", "Психоанализ", "Трансфер_(психология)")


def fetch_extract(title: str) -> str:
    t = urllib.parse.quote(title)
    url = (
        f"https://ru.wikipedia.org/w/api.php?action=query&format=json"
        f"&prop=extracts&explaintext=1&titles={t}&redirects=1"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "HesperiaValidation/1.0 (https://github.com/igareosh/cursor; research)"
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    pages = d["query"]["pages"]
    pid = next(iter(pages))
    return str(pages[pid].get("extract") or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO
        / "tests"
        / "fixtures"
        / "tfp_calibration"
        / "extended_ru_natural_corpus_v1.txt",
    )
    args = ap.parse_args()

    blocks = []
    for title in TITLES_DEFAULT:
        blocks.append(f"\n\n## {title}\n\n" + fetch_extract(title))
    body = "\n".join(blocks).strip() + "\n"
    header = """# Extended RU natural validation corpus (measurement only).
# Source: Russian Wikipedia article extracts via MediaWiki API (CC BY-SA 4.0).
# Article titles: Психотерапия; Психоанализ; Трансфер_(психология).
# Purpose: DLCR extended REPORT validation; not product redistribution of Wikipedia.

"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(header + body, encoding="utf-8")
    wc = len(body.split())
    print(json.dumps({"out": str(args.out), "word_count": wc}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
