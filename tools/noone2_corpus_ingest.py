#!/usr/bin/env python3
"""
Ingest flat files from HESPERIA_NOONE2_ROOT (default: /home/igareosh/noone/2) into Markdown.

- Russian / RU-marked sources → research/_noone_local/2_cleaned/
- English (Latin filenames without RU routing markers) → research/_noone_local/english_2_cleaned/

Reuses conversion logic from tools/tfp4_corpus_full_ingest.py (pandoc, pdftotext, LibreOffice for ppt).

Skips:
  - Freud_Complete_Works.pdf unless --include-freud-complete
  - .key when a sibling .pptx or .ppt exists (same stem)
  - .key otherwise (no reliable headless converter on Linux; log skip)
  - Sources whose sha256 already appears in YAML front matter of any .md under the target corpora
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOONE_LOCAL = REPO / "research/_noone_local"
OUT_RU = NOONE_LOCAL / "2_cleaned"
OUT_EN = NOONE_LOCAL / "english_2_cleaned"
DEFAULT_NOONE2 = Path(os.environ.get("HESPERIA_NOONE2_ROOT", "/home/igareosh/noone/2"))

CYR = re.compile(r"[А-Яа-яЁё]")


def _load_tfp4_ingest():
    path = REPO / "tools/tfp4_corpus_full_ingest.py"
    spec = importlib.util.spec_from_file_location("_tfp4_corpus_full_ingest", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_front_matter_sha256(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    for line in text[4:end].split("\n"):
        if line.startswith("sha256:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def collect_known_shas(roots: list[Path]) -> set[str]:
    out: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*.md"):
            if p.name.startswith("CORPUS_MD_TREE"):
                continue
            try:
                raw = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            h = parse_front_matter_sha256(raw)
            if h:
                out.add(h)
    return out


def corpus_lang_for_filename(name: str) -> str:
    """Return 'ru' or 'en' based on filename heuristics only."""
    stem = Path(name).stem
    if CYR.search(stem):
        return "ru"
    sl = stem.lower()
    if "рус" in sl:
        return "ru"
    for token in (
        " rus",
        "rus ",
        "_rus",
        "rus eng",
        "russian speakers",
        " ru de",
        "(ru)",
        "final ru",
    ):
        if token in sl:
            return "ru"
    if "moscow" in sl and "eng" not in sl and "english" not in sl:
        return "ru"
    return "en"


def sanitize_md_basename(name: str) -> str:
    base = unicodedata.normalize("NFC", Path(name).stem)
    base = re.sub(r'[<>:"/\\|?*]', "_", base)
    base = re.sub(r"\s+", " ", base).strip()
    if not base:
        base = "untitled"
    if len(base) > 180:
        base = base[:180].rstrip()
    return f"{base}.md"


def pick_out_path(
    out_dir: Path,
    src: Path,
    sha_hex: str,
    *,
    reserved: set[Path],
    force: bool,
) -> Path | None:
    """Canonical NFC basename; sha-suffix if batch collision. None = skip (target exists)."""
    base = sanitize_md_basename(src.name)
    canonical = out_dir / base

    if canonical not in reserved:
        if canonical.is_file() and not force:
            return None
        reserved.add(canonical)
        return canonical

    stem = Path(base).stem
    frag = sha_hex[:8]
    n = 0
    while True:
        suffix = f"_{frag}" if n == 0 else f"_{frag}_{n}"
        c = out_dir / f"{stem}{suffix}.md"
        if c in reserved:
            n += 1
            continue
        if c.is_file() and not force:
            n += 1
            continue
        reserved.add(c)
        return c


def front_matter(
    title: str,
    source_name: str,
    sha256: str,
    corpus_lang: str,
    *,
    converter_status: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe = title.replace('"', "'")
    return (
        "---\n"
        f'title: "{safe}"\n'
        f"noone2_source: {json.dumps(source_name, ensure_ascii=False)}\n"
        f"sha256: {sha256}\n"
        f"corpus_lang: {corpus_lang}\n"
        f"converter: {json.dumps(converter_status, ensure_ascii=False)}\n"
        f"ingested_at: {now}\n"
        "---\n\n"
    )


def sibling_ppt_exists(src: Path) -> bool:
    d = src.parent
    stem = src.stem
    for ext in (".pptx", ".ppt", ".PPTX", ".PPT"):
        if (d / f"{stem}{ext}").is_file():
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--src-root",
        type=Path,
        default=DEFAULT_NOONE2,
        help="Flat directory of source files (default: $HESPERIA_NOONE2_ROOT or ~/noone/2).",
    )
    ap.add_argument(
        "--include-freud-complete",
        action="store_true",
        help="Allow ingesting Freud_Complete_Works.pdf (very large; not recommended as one .md).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if sha256 already present in corpus front matter.",
    )
    args = ap.parse_args()

    src_root: Path = args.src_root.expanduser().resolve()
    if not src_root.is_dir():
        print(f"Missing or not a directory: {src_root}", file=sys.stderr)
        return 1

    tfp4 = _load_tfp4_ingest()
    body_for_source = tfp4.body_for_source
    clean_markdown_body = tfp4.clean_markdown_body

    OUT_EN.mkdir(parents=True, exist_ok=True)
    OUT_RU.mkdir(parents=True, exist_ok=True)

    known = collect_known_shas([OUT_RU, OUT_EN])
    if args.force:
        known = set()

    reserved_paths: set[Path] = set()

    exts = {".pdf", ".docx", ".doc", ".ppt", ".pptx", ".key"}
    files = sorted(
        p
        for p in src_root.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )

    log: list[str] = []
    for src in files:
        name = src.name
        if name == "Freud_Complete_Works.pdf" and not args.include_freud_complete:
            log.append(f"SKIP_HUGE\t{name}\t(use --include-freud-complete)")
            continue

        suf = src.suffix.lower()
        if suf == ".key":
            if sibling_ppt_exists(src):
                log.append(f"SKIP_KEY_HAS_PPTX\t{name}")
                continue
            log.append(f"SKIP_KEY_NO_CONVERTER\t{name}\t(Linux: add exported pptx/pdf or run on macOS)")
            continue

        h = _sha256_file(src)
        if h in known:
            log.append(f"SKIP_KNOWN_SHA\t{name}")
            continue

        lang = corpus_lang_for_filename(name)
        out_dir = OUT_RU if lang == "ru" else OUT_EN
        out_path = pick_out_path(
            out_dir, src, h, reserved=reserved_paths, force=args.force
        )
        if out_path is None:
            skip_target = out_dir / sanitize_md_basename(name)
            log.append(f"SKIP_EXISTS\t{skip_target.relative_to(REPO)}")
            continue

        if args.dry_run:
            log.append(f"DRY\t{lang}\t{name}\t->\t{out_path.relative_to(REPO)}")
            continue

        status, body = body_for_source(src)
        if not body.strip():
            log.append(f"FAIL\t{name}\t{status}")
            continue

        body = clean_markdown_body(body)
        fm = front_matter(src.stem, name, h, lang, converter_status=status)
        out_path.write_text(fm + body, encoding="utf-8")
        known.add(h)
        log.append(f"OK\t{status}\t{lang}\t{name}\t->\t{out_path.relative_to(REPO)}")

    report = REPO / "research/noone2_ingest_run_log.txt"
    report.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"\nWrote log: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
