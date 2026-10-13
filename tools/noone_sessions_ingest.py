#!/usr/bin/env python3
"""
Ingest session transcripts from HESPERIA_NOONE_ROOT (default: /home/igareosh/noone):
only top-level files named DD-MM-YYYY.docx or DD-MM-YYYY.doc.

Writes hesperia/modules/tfp/data/tfp_v1/corpus/sessions/<stem>.md (see tools/tfp_v1_paths.py; override via HESPERIA_TFP_MODULE_DATA_ROOT) with:
  - YAML: session_date_iso, session_date_ru (дд.мм.гггг), source filename, sha256
  - Body: Cyrillic П/Т with optional turn index (П1. Т14. П. Т.) and «Пациент.»/«Терапевт.»
    normalized to **Пациент:** / **Терапевт:**
  - Timestamps glued to a turn (e.g. «00.18.32 Т. …») split so the time stays on its own line
  - Glued end-of-clause timestamps (e.g. «так.02.38», «Да.00.06.45») split onto their own line
  - Header lines from the doc (Случай …, Сессия …, Транскрипт …) kept as-is (Russian)

Re-run glued-timestamp repair on existing Markdown only:
  python3 tools/noone_sessions_ingest.py --repair-md
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_TOOLS = REPO / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from tfp_v1_paths import tfp_v1_root  # noqa: E402

OUT_DIR = tfp_v1_root(REPO) / "corpus" / "sessions"
DEFAULT_NOONE = Path(os.environ.get("HESPERIA_NOONE_ROOT", "/home/igareosh/noone"))

SESSION_FILENAME = re.compile(
    r"^(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{4})\.(?P<ext>docx|doc)$",
    re.IGNORECASE,
)
SESSION_STEM = re.compile(r"^(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{4})$")

# Time then speaker: «00.18.32 Т. …», «02.38 П2. …» (Cyrillic П/Т only)
_RE_TS_SPEAKER = re.compile(
    r"^(\d{1,2}\.\d{1,2}(?:\.\d{2,4})?)\s+([ПТ])(?:\d+)?\.\s+(.*)$",
)
_RE_THER_WORD = re.compile(r"^Терапевт\.\s*")
_RE_PAT_WORD = re.compile(r"^Пациент\.\s*")
# П / Т + optional turn index + «.» (space optional before text): П1. … Т14.Мне …
_RE_P_TURN = re.compile(r"^П(\d*)\.\s*(.*)$")
_RE_T_TURN = re.compile(r"^Т(\d*)\.\s*(.*)$")

# Sentence ended, no space before a transcript time token (Word export glitch).
_RE_GLUED_TS = re.compile(
    r"(?<=[а-яёА-ЯЁa-zA-Z!?…»\)\]])"
    r"\."
    r"(\d{1,2}\.\d{2}(?:\.\d{2,4})?)"
    r"(?=\s*(?:$|\n|\r|\*\*|\[|\\))"
)


def _plausible_session_ts(token: str) -> bool:
    """mm.ss or hh.mm.ss style as used in session transcripts (not calendar dates)."""
    parts = token.split(".")
    if len(parts) not in (2, 3):
        return False
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return False
    if any(n < 0 for n in nums):
        return False
    if len(nums) == 2:
        a, b = nums
        return a <= 59 and b <= 59
    a, b, c = nums
    if c > 59 or b > 59:
        return False
    return a <= 23


def detach_glued_session_timestamps(text: str) -> str:
    """Insert blank lines before time tokens stuck to preceding «.» without a space."""

    def fix_line(line: str) -> str:
        prev = None
        while prev != line:
            prev = line

            def repl(m: re.Match[str]) -> str:
                ts = m.group(1)
                if not _plausible_session_ts(ts):
                    return m.group(0)
                return f".\n\n{ts}"

            line = _RE_GLUED_TS.sub(repl, line)
        return line

    return "\n".join(fix_line(unicodedata.normalize("NFC", ln)) for ln in text.splitlines())


_RE_SPEAKER_PREFIX = re.compile(r"^(\*\*(?:Пациент|Терапевт):\*\*\s*)")
_RE_TS_LINE_ONLY = re.compile(r"^\d{1,2}\.\d{2}(?:\.\d{2,4})?$")


def propagate_speaker_after_orphan_timestamp(body: str) -> str:
    """After detaching a mid-utterance time, following lines stay the same speaker until next **…** — re-label."""
    lines = body.splitlines()
    last_speaker: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _RE_SPEAKER_PREFIX.match(line)
        if m:
            last_speaker = m.group(1)
        if _RE_TS_LINE_ONLY.match(line.strip()) and last_speaker:
            j = i + 1
            sp_head = last_speaker.rstrip()
            while j < len(lines):
                nxt = lines[j]
                st = nxt.strip()
                if not st:
                    j += 1
                    continue
                if st.startswith("**"):
                    if st.startswith(sp_head):
                        j += 1
                        continue
                    break
                if st.startswith("Пауза"):
                    j += 1
                    continue
                if _RE_TS_LINE_ONLY.match(st):
                    break
                if st.startswith(("Случай", "Сессия", "Транскрипт")):
                    break
                if st.startswith("\\") or st.startswith("-") or st.startswith("["):
                    j += 1
                    continue
                if not nxt.startswith(last_speaker):
                    lines[j] = last_speaker + nxt.lstrip(" \t")
                j += 1
        i += 1
    return "\n".join(lines)


def split_yaml_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    split_at = end + len("\n---\n")
    return text[:split_at], text[split_at:].lstrip("\n")


def _load_tfp4_clean():
    path = REPO / "tools/tfp4_corpus_full_ingest.py"
    spec = importlib.util.spec_from_file_location("_tfp4_corpus_full_ingest", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.clean_markdown_body


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], *, timeout: float | None = None) -> None:
    subprocess.run(cmd, check=True, timeout=timeout)


def _pandoc_docx_to_md(src: Path) -> str:
    fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="noone_sess_")
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
        return tmp.read_text(encoding="utf-8", errors="replace")
    finally:
        tmp.unlink(missing_ok=True)


def _doc_to_md_via_libreoffice(src: Path) -> str:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) required for .doc conversion")
    with tempfile.TemporaryDirectory(prefix="noone_sess_lo_") as td:
        tdp = Path(td)
        _run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                str(tdp),
                str(src),
            ],
            timeout=600,
        )
        outs = list(tdp.glob("*.docx"))
        if not outs:
            raise RuntimeError("LibreOffice produced no docx")
        return _pandoc_docx_to_md(outs[0])


def _source_to_markdown(src: Path) -> tuple[str, str]:
    suf = src.suffix.lower()
    if suf == ".docx":
        return "pandoc_docx", _pandoc_docx_to_md(src)
    if suf == ".doc":
        head = src.read_bytes()[:16]
        if head.startswith(b"AT&TFORM"):
            return "skip_djvu_disguised_doc", ""
        return "libreoffice_docx_then_pandoc", _doc_to_md_via_libreoffice(src)
    return "skip_suffix", ""


def strip_stray_turn_counter_after_speaker_label_line(line: str) -> str:
    """Remove Word artifacts like «**Пациент:** 17.Как» → «**Пациент:** Как»."""
    # Glued: digit(s) + «.» immediately before Cyrillic / opening quote
    line = re.sub(
        r"^(\*\*(?:Пациент|Терапевт):\*\*\s*)\d{1,3}\.(?=[А-Яа-яЁё«\"„'])",
        r"\1",
        line,
        count=1,
    )
    # Spaced small index (1–30) before text — typical enumeration, not «29.5 мм»
    line = re.sub(
        r"^(\*\*(?:Пациент|Терапевт):\*\*\s*)(?:[1-9]|[12][0-9]|30)\.\s+(?=[А-Яа-яЁё«\"„'])",
        r"\1",
        line,
        count=1,
    )
    return line


def normalize_session_speakers(md: str) -> str:
    """Пn./Тn./П./Т. (Cyrillic) and «Пациент.»/«Терапевт.» → **Пациент:** / **Терапевт:**; split time+speaker."""
    lines = md.splitlines()
    out: list[str] = []
    for raw in lines:
        line = unicodedata.normalize("NFC", raw)
        work = line.lstrip(" \t\u00a0")

        m = _RE_TS_SPEAKER.match(work)
        if m:
            ts, sp, rest = m.groups()
            label = "**Пациент:** " if sp == "П" else "**Терапевт:** "
            if out and out[-1].strip():
                out.append("")
            out.append(ts)
            out.append("")
            out.append(label + rest)
            continue

        if _RE_THER_WORD.match(work):
            work = _RE_THER_WORD.sub("**Терапевт:** ", work, count=1)
            out.append(strip_stray_turn_counter_after_speaker_label_line(work))
            continue
        if _RE_PAT_WORD.match(work):
            work = _RE_PAT_WORD.sub("**Пациент:** ", work, count=1)
            out.append(strip_stray_turn_counter_after_speaker_label_line(work))
            continue

        m = _RE_P_TURN.match(work)
        if m:
            rest = m.group(2)
            out.append(
                strip_stray_turn_counter_after_speaker_label_line(
                    "**Пациент:** " + rest
                )
            )
            continue

        m = _RE_T_TURN.match(work)
        if m:
            rest = m.group(2)
            out.append(
                strip_stray_turn_counter_after_speaker_label_line(
                    "**Терапевт:** " + rest
                )
            )
            continue

        out.append(strip_stray_turn_counter_after_speaker_label_line(line))
    return "\n".join(out)


def process_session_markdown_body(
    raw_md: str,
    clean_markdown_body: object | None = None,
) -> str:
    """Full body pipeline: speakers → stray index strip → glued timestamps → propagate → clean."""
    cleaner = clean_markdown_body or _load_tfp4_clean()
    body = normalize_session_speakers(raw_md)
    body = detach_glued_session_timestamps(body)
    body = propagate_speaker_after_orphan_timestamp(body)
    return cleaner(body)


def parse_session_stem(stem: str) -> tuple[str, str] | None:
    m = SESSION_STEM.match(stem)
    if not m:
        return None
    d, mo, y = int(m.group("d")), int(m.group("m")), int(m.group("y"))
    iso = f"{y:04d}-{mo:02d}-{d:02d}"
    ru = f"{d:02d}.{mo:02d}.{y:04d}"
    return iso, ru


def front_matter(
    *,
    title: str,
    source_name: str,
    sha256_hex: str,
    session_date_iso: str,
    session_date_ru: str,
    converter: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe = title.replace('"', "'")
    return (
        "---\n"
        f'title: "{safe}"\n'
        f"corpus_kind: clinical_session\n"
        f"session_date_iso: {session_date_iso}\n"
        f"session_date_ru: {session_date_ru}\n"
        f"noone_sessions_source: {json.dumps(source_name, ensure_ascii=False)}\n"
        f"sha256: {sha256_hex}\n"
        f"converter: {json.dumps(converter, ensure_ascii=False)}\n"
        f"ingested_at: {now}\n"
        "---\n\n"
    )


def infer_title(body: str, session_date_ru: str) -> str:
    for line in body.splitlines()[:12]:
        s = line.strip()
        if not s or s.startswith("---"):
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip()
        if re.match(r"^Сессия\s+\d", s, re.I):
            return s
        if "Транскрипт" in s and "сессии" in s.lower():
            return s
        if s.startswith("Случай"):
            return f"{s} — {session_date_ru}"
    return f"Сессия {session_date_ru}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--src-root",
        type=Path,
        default=DEFAULT_NOONE,
        help="Directory containing DD-MM-YYYY.docx|.doc (default: $HESPERIA_NOONE_ROOT).",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help=f"Output directory (default: {OUT_DIR}).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Overwrite existing .md")
    ap.add_argument(
        "--repair-md",
        action="store_true",
        help="Re-run full Markdown body pipeline on *.md under --out (П/Т labels, timestamps, clean).",
    )
    args = ap.parse_args()

    out_dir = args.out
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    out_dir = out_dir.resolve()

    clean_markdown_body = _load_tfp4_clean()
    log: list[str] = []

    if args.repair_md:
        if not out_dir.is_dir():
            print(f"Missing sessions directory: {out_dir}", file=sys.stderr)
            return 1
        md_files = sorted(p for p in out_dir.glob("*.md") if p.is_file())
        if not md_files:
            print(f"No .md files in {out_dir}", file=sys.stderr)
            return 1
        for path in md_files:
            try:
                full = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                log.append(f"FAIL_READ\t{path.name}\t{e!s}")
                continue
            fm, body = split_yaml_front_matter(full)
            if not fm:
                log.append(f"SKIP_NO_FM\t{path.name}")
                continue
            new_body = process_session_markdown_body(body, clean_markdown_body)
            if new_body == body:
                log.append(f"UNCHANGED\t{path.name}")
                continue
            if args.dry_run:
                log.append(f"DRY_REPAIR\t{path.name}")
                continue
            path.write_text(fm + "\n" + new_body, encoding="utf-8")
            log.append(f"OK_REPAIR\t{path.name}")
        report = REPO / "research/noone_sessions_ingest_run_log.txt"
        report.write_text("\n".join(log) + "\n", encoding="utf-8")
        print("\n".join(log))
        print(f"\nWrote log: {report}")
        return 0

    src_root = args.src_root.expanduser().resolve()

    if not src_root.is_dir():
        print(f"Missing directory: {src_root}", file=sys.stderr)
        return 1

    candidates = sorted(
        p
        for p in src_root.iterdir()
        if p.is_file() and SESSION_FILENAME.match(p.name)
    )

    if not candidates:
        print(f"No session files matching DD-MM-YYYY.docx|.doc in {src_root}", file=sys.stderr)
        return 1

    for src in candidates:
        stem = src.stem
        parsed = parse_session_stem(stem)
        if not parsed:
            log.append(f"SKIP_BAD_STEM\t{src.name}")
            continue
        iso, ru = parsed
        out_path = out_dir / f"{stem}.md"

        if out_path.exists() and not args.force:
            log.append(f"SKIP_EXISTS\t{out_path.relative_to(REPO)}")
            continue

        if args.dry_run:
            log.append(f"DRY\t{src.name}\t->\t{out_path.relative_to(REPO)}")
            continue

        try:
            status, raw_md = _source_to_markdown(src)
        except (subprocess.CalledProcessError, OSError, RuntimeError) as e:
            log.append(f"FAIL_CONVERT\t{src.name}\t{e!s}")
            continue

        if not raw_md.strip() or status.startswith("skip_"):
            log.append(f"FAIL_EMPTY\t{src.name}\t{status}")
            continue

        body = process_session_markdown_body(raw_md, clean_markdown_body)
        title = infer_title(body, ru)
        h = _sha256_file(src)
        fm = front_matter(
            title=title,
            source_name=src.name,
            sha256_hex=h,
            session_date_iso=iso,
            session_date_ru=ru,
            converter=status,
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(fm + body, encoding="utf-8")
        log.append(f"OK\t{status}\t{src.name}\t->\t{out_path.relative_to(REPO)}")

    report = REPO / "research/noone_sessions_ingest_run_log.txt"
    report.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"\nWrote log: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
