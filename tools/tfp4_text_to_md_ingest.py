#!/usr/bin/env python3
"""Convert tfp/4 text/* sources to Markdown for corpus gaps only (see manifest)."""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _slug(name: str) -> str:
    base = unicodedata.normalize("NFC", Path(name).stem)
    base = re.sub(r"[^\w\s\-А-Яа-яЁё.]", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base[:180] or "untitled"


def _front_matter(title: str, source: str, sha256: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_title = title.replace('"', "'")
    return (
        "---\n"
        f'title: "{safe_title}"\n'
        f"source_path: {json.dumps(source, ensure_ascii=False)}\n"
        f"sha256: {sha256}\n"
        f"ingested_at: {now}\n"
        "---\n\n"
    )


def _body_for_source(src: Path) -> tuple[str, str]:
    """Return (status, markdown_body_without_front_matter)."""
    suf = src.suffix.lower()
    title = src.stem

    if suf == ".docx":
        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="tfp4_ingest_")
        os.close(fd)
        tmp = Path(tmp_path)
        try:
            _run(
                [
                    "pandoc",
                    "-f",
                    "docx",
                    "-t",
                    "markdown-smart",
                    "--wrap=none",
                    "-o",
                    str(tmp),
                    str(src),
                ]
            )
            body = tmp.read_text(encoding="utf-8", errors="replace")
            return "pandoc_docx", body
        finally:
            tmp.unlink(missing_ok=True)

    if suf == ".doc":
        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="tfp4_ingest_")
        os.close(fd)
        tmp = Path(tmp_path)
        try:
            _run(
                [
                    "pandoc",
                    "-f",
                    "doc",
                    "-t",
                    "markdown-smart",
                    "--wrap=none",
                    "-o",
                    str(tmp),
                    str(src),
                ]
            )
            body = tmp.read_text(encoding="utf-8", errors="replace")
            return "pandoc_doc", body
        except subprocess.CalledProcessError:
            return "skip_doc_needs_libreoffice", ""
        finally:
            tmp.unlink(missing_ok=True)

    if suf == ".pdf":
        fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="tfp4_ingest_")
        os.close(fd)
        tmp = Path(tmp_path)
        try:
            _run(["pdftotext", "-layout", "-enc", "UTF-8", str(src), str(tmp)])
            body = tmp.read_text(encoding="utf-8", errors="replace")
            return "pdftotext", f"# {title}\n\n{body}"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "skip_pdf_pdftotext_failed", ""
        finally:
            tmp.unlink(missing_ok=True)

    if suf in (".ppt", ".pptx"):
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            return "skip_ppt_needs_libreoffice", ""
        with tempfile.TemporaryDirectory(prefix="tfp4_lo_") as tmp_dir_s:
            tmp_dir = Path(tmp_dir_s)
            try:
                _run(
                    [
                        soffice,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(tmp_dir),
                        str(src),
                    ]
                )
                pdfs = list(tmp_dir.glob("*.pdf"))
                if not pdfs:
                    return "skip_ppt_pdf_missing", ""
                pdf = pdfs[0]
                tmp_txt = tmp_dir / "out.txt"
                _run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(tmp_txt)])
                body = tmp_txt.read_text(encoding="utf-8", errors="replace")
                return "libreoffice_pdf_then_pdftotext", f"# {title}\n\n{body}"
            except (subprocess.CalledProcessError, FileNotFoundError):
                return "skip_ppt_conversion_failed", ""

    return f"skip_unknown_suffix_{suf}", ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--tfp4-root",
        type=Path,
        default=Path(os.environ.get("HESPERIA_TFP4_ROOT", "/home/igareosh/tfp/4")),
        help="Root that contains text/ and images/ (default: $HESPERIA_TFP4_ROOT).",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=_repo_root() / "research/tfp4_corpus_gap_manifest.json",
        help="Manifest JSON path.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_repo_root() / "research/_noone_local/ingest_from_tfp4_md",
        help="Output directory for generated Markdown.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print actions only.")
    args = ap.parse_args()

    tfp4 = args.tfp4_root.resolve()
    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir = args.out
    if not out_dir.is_absolute():
        out_dir = _repo_root() / out_dir
    out_dir = out_dir.resolve()

    results: list[tuple[str, str]] = []
    for entry in data.get("entries", []):
        if not entry.get("ingest_to_md"):
            continue
        rel = entry["path_under_tfp4"]
        src = (tfp4 / rel).resolve()
        if not src.is_file():
            results.append((rel, "missing_source"))
            continue

        out_md = out_dir / f"{_slug(src.name)}.md"
        if args.dry_run:
            results.append((rel, f"would_write:{out_md.name}"))
            continue

        status, body = _body_for_source(src)
        if not body.strip() or status.startswith("skip_"):
            results.append((rel, status))
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        fm = _front_matter(src.stem, rel, entry["sha256"])
        out_md.write_text(fm + body, encoding="utf-8")
        results.append((rel, status))

    for rel, st in sorted(results):
        print(f"{st}\t{rel}")


if __name__ == "__main__":
    main()
