#!/usr/bin/env python3
"""Build tfp4_corpus_gap_manifest.json: sha256 + ingest flags vs tracked TFP corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(text_root: Path) -> dict:
    skip_exact_nfc = {
        nfc("Практически неизлечимый нарциссический пациент.docx"): (
            "2_cleaned/Практически неизлечимый нарциссический пациент.md"
        ),
        nfc("дифдиагностика.docx"): "2_cleaned/Дифференциальная диагностика.md",
        nfc("Кернберг 2014.docx"): (
            "2_cleaned/Кернберг - Обзор лечения тяжелой нарциссической патологии 2014.md"
        ),
        nfc("Narcissism - Doering for translation RUS ENG.pptx"): (
            "background/Doering - Narcissism RUS ENG.md"
        ),
        nfc("Implicit communication - Doering ПЕРЕВОД.pptx"): (
            "background/Doering - Implicit Communication RUS.md"
        ),
    }

    files = sorted((p for p in text_root.rglob("*") if p.is_file()), key=lambda p: str(p))
    entries: list[dict] = []
    tfp4_parent = text_root.parent

    for p in files:
        rel_from_tfp4 = p.relative_to(tfp4_parent)
        bn = p.name
        bn_nfc = nfc(bn)

        covered = None
        ingest = True
        note = None

        if bn_nfc in skip_exact_nfc:
            covered = skip_exact_nfc[bn_nfc]
            ingest = False
            note = "corpus_md_exists"
        elif bn.startswith("TFP раздаточный") or "Введение в TFP" in bn:
            covered = "2_cleaned/TFP - Введение раздаточный материал.md"
            ingest = False
            note = "corpus_md_exists"
        elif bn == "Москва О супервизии 2019 ГОТОВО edited.pptx":
            ingest = False
            note = "dedupe_prefer_unedited_pptx"
            covered = "text/Москва О супервизии 2019 ГОТОВО.pptx"
        elif bn == "Moscow 2020 BPO DID and Gender Identity RUS.pptx":
            note = "review_overlap_background_TFP_Moscow_Workshop_Dec_2020"

        entries.append(
            {
                "path_under_tfp4": str(rel_from_tfp4).replace("\\", "/"),
                "basename": bn,
                "sha256": sha256_file(p),
                "ingest_to_md": ingest,
                "corpus_equivalent_md": covered,
                "note": note,
            }
        )

    return {
        "source_tree": str(text_root.resolve()),
        "ingest_true_count": sum(1 for e in entries if e["ingest_to_md"]),
        "entries": entries,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--text-root",
        type=Path,
        default=Path("/home/igareosh/tfp/4/text"),
        help="Directory containing docx/ppt/pdf sources (sibling to images/).",
    )
    ap.add_argument(
        "--write",
        type=Path,
        default=Path("research/tfp4_corpus_gap_manifest.json"),
        help="Output JSON path (repo-relative or absolute).",
    )
    args = ap.parse_args()

    text_root = args.text_root.resolve()
    if not text_root.is_dir():
        raise SystemExit(f"Not a directory: {text_root}")

    out = args.write
    if not out.is_absolute():
        repo = Path(__file__).resolve().parents[1]
        out = repo / out

    manifest = build_manifest(text_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(f"ingest_to_md true: {manifest['ingest_true_count']} / {len(manifest['entries'])}")


if __name__ == "__main__":
    main()
