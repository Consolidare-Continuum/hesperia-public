#!/usr/bin/env python3
"""
Full TFP4 text → corpus Markdown: convert, clean, write under research/_noone_local/2_cleaned/ only.

Reads tfp4_corpus_gap_manifest.json; only entries with ingest_to_md true.
Skips second file when sha256 already written (STIPO form duplicate).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOONE = REPO / "research/_noone_local"
MANIFEST = REPO / "research/tfp4_corpus_gap_manifest.json"
DEFAULT_TFP4 = Path(os.environ.get("HESPERIA_TFP4_ROOT", "/home/igareosh/tfp/4"))


def _run(cmd: list[str], *, timeout: float | None = 7200) -> None:
    subprocess.run(cmd, check=True, timeout=timeout)


def clean_markdown_body(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\n{5,}", "\n\n\n\n", s)
    lines = [ln.rstrip() for ln in s.split("\n")]
    s = "\n".join(lines).strip()
    if s and not s.endswith("\n"):
        s += "\n"
    return s


def body_for_source(src: Path) -> tuple[str, str]:
    suf = src.suffix.lower()
    title = src.stem

    if suf == ".docx":
        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="tfp4_")
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
            return "pandoc_docx", tmp.read_text(encoding="utf-8", errors="replace")
        finally:
            tmp.unlink(missing_ok=True)

    if suf == ".doc":
        head = src.read_bytes()[:16]
        if head.startswith(b"AT&TFORM"):
            raw = subprocess.check_output(
                ["djvutxt", str(src)],
                timeout=3600,
                stderr=subprocess.DEVNULL,
            )
            text = raw.decode("utf-8", errors="replace")
            return "djvutxt", f"# {title}\n\n{text}"

        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="tfp4_")
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
                ],
                timeout=120,
            )
            body = tmp.read_text(encoding="utf-8", errors="replace")
            tmp.unlink(missing_ok=True)
            return "pandoc_doc", body
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            tmp.unlink(missing_ok=True)

        soffice = shutil.which("soffice") or "libreoffice"
        with tempfile.TemporaryDirectory(prefix="tfp4_lo_") as td:
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
                ]
            )
            outs = list(tdp.glob("*.docx"))
            if not outs:
                return "skip_doc_convert_failed", ""
            fd2, tmp2_path = tempfile.mkstemp(suffix=".md", prefix="tfp4_")
            os.close(fd2)
            tmp2 = Path(tmp2_path)
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
                        str(tmp2),
                        str(outs[0]),
                    ]
                )
                return "libreoffice_docx_then_pandoc", tmp2.read_text(
                    encoding="utf-8", errors="replace"
                )
            finally:
                tmp2.unlink(missing_ok=True)

    if suf == ".pdf":
        fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="tfp4_")
        os.close(fd)
        tmp = Path(tmp_path)
        try:
            _run(["pdftotext", "-layout", "-enc", "UTF-8", str(src), str(tmp)])
            body = tmp.read_text(encoding="utf-8", errors="replace")
            return "pdftotext", f"# {title}\n\n{body}"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "skip_pdf", ""
        finally:
            tmp.unlink(missing_ok=True)

    if suf in (".ppt", ".pptx"):
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            return "skip_ppt_no_soffice", ""
        with tempfile.TemporaryDirectory(prefix="tfp4_lo_") as tmp_dir_s:
            tmp_dir = Path(tmp_dir_s)
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
                return "skip_ppt_no_pdf", ""
            pdf = pdfs[0]
            tmp_txt = tmp_dir / "out.txt"
            _run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(tmp_txt)])
            body = tmp_txt.read_text(encoding="utf-8", errors="replace")
            return "libreoffice_pdf_pdftotext", f"# {title}\n\n{body}"

    return f"skip_suffix_{suf}", ""


# manifest path_under_tfp4 -> (relative under NOONE, optional extra yaml lines)
OUTPUT_MAP: dict[str, tuple[str, str]] = {
    "text/FV Москва  TFP-подростки 2020.pptx": (
        "2_cleaned/FV - Moscow TFP adolescents 2020.md",
        "corpus_kind: workshop_deck\n",
    ),
    "text/Moscow 2020 BPO DID and Gender Identity RUS.pptx": (
        "2_cleaned/Moscow 2020 BPO DID and Gender Identity RUS.md",
        "corpus_kind: workshop_deck\nreview_note: Compare with TFP - Moscow Workshop Dec 2020.md\n",
    ),
    "text/STIPO-R Training - February 2019 RUS.pptx": (
        "2_cleaned/STIPO-R Training February 2019 RUS.md",
        "corpus_kind: training_deck\n",
    ),
    "text/stipo.docx": ("2_cleaned/STIPO - stipo notes.md", "corpus_kind: instrument\n"),
    "text/stipo_form.docx": (
        "2_cleaned/STIPO - scoring form.md",
        "corpus_kind: instrument\n",
    ),
    "text/Бриттон Эдип на депрессивной позиции.docx": (
        "2_cleaned/Бриттон - Эдип на депрессивной позиции.md",
        "corpus_kind: paper\n",
    ),
    "text/Бриттон.До и после депрессивной позиции.docx": (
        "2_cleaned/Бриттон - До и после депрессивной позиции.md",
        "corpus_kind: paper\n",
    ),
    "text/Бриттон.Нарциссизм и нарциссические расстройства.docx": (
        "2_cleaned/Бриттон - Нарциссизм и нарциссические расстройства.md",
        "corpus_kind: paper\n",
    ),
    "text/Бриттон.Утерянная связь родительская сексуальность в Эдиповом комплексе.docx": (
        "2_cleaned/Бриттон - Утерянная связь родительская сексуальность в Эдиповом комплексе.md",
        "corpus_kind: paper\n",
    ),
    "text/Грин - Работа негатива.docx": (
        "2_cleaned/Грин - Работа негатива.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Гротштейн - Расщепление и проективная идентификация/Гротштейн - Расщепление и проективная идентификация.docx": (
        "2_cleaned/Гротштейн - Расщепление и проективная идентификация.md",
        "corpus_kind: book_excerpt\nprimary_source: docx\n",
    ),
    "text/Гротштейн - Расщепление и проективная идентификация/Гротштейн - Расщепление и проективная идентификация.pdf": (
        "2_cleaned/Гротштейн - Расщепление и проективная идентификация from PDF.md",
        "corpus_kind: book_excerpt\nprimary_source: pdf\nnote: Alternate extract from PDF; prefer docx version for structure.\n",
    ),
    "text/ДРИ ТФП.docx": ("2_cleaned/ДРИ ТФП.md", "corpus_kind: internal_notes\n"),
    "text/Дени - Контрперенос рифы и отклонения RU/Дени - Контрперенос рифы и отклонения.docx": (
        "2_cleaned/Дени - Контрперенос рифы и отклонения.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Дени - Контрперенос рифы и отклонения RU/Дени - Контрперенос рифы и отклонения.pdf": (
        "2_cleaned/Дени - Контрперенос рифы и отклонения from PDF.md",
        "corpus_kind: book_excerpt\nprimary_source: pdf\n",
    ),
    "text/Джойс МакДугалл Театр души.doc": (
        "2_cleaned/МакДугалл Джойс - Театр души.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Йоманс НРЛ часть 1.ppt": (
        "2_cleaned/Йоманс - НРЛ часть 1.md",
        "corpus_kind: workshop_deck\nseries: yeomans_nrl\n",
    ),
    "text/Йоманс НРЛ часть 2.ppt": (
        "2_cleaned/Йоманс - НРЛ часть 2.md",
        "corpus_kind: workshop_deck\nseries: yeomans_nrl\n",
    ),
    "text/Йоманс НРЛ Часть 3.ppt": (
        "2_cleaned/Йоманс - НРЛ часть 3.md",
        "corpus_kind: workshop_deck\nseries: yeomans_nrl\n",
    ),
    "text/Йоманс НРЛ Часть 4.ppt": (
        "2_cleaned/Йоманс - НРЛ часть 4.md",
        "corpus_kind: workshop_deck\nseries: yeomans_nrl\n",
    ),
    "text/Йоманс НРЛ Часть 5.ppt": (
        "2_cleaned/Йоманс - НРЛ часть 5.md",
        "corpus_kind: workshop_deck\nseries: yeomans_nrl\n",
    ),
    "text/Йоманс НРЛ.pptx": (
        "2_cleaned/Йоманс - НРЛ обзор.md",
        "corpus_kind: workshop_deck\nseries: yeomans_nrl\n",
    ),
    "text/Клиническая оценочная решетка - текст частично поврежден OCR.docx": (
        "2_cleaned/Клиническая оценочная решетка OCR damaged source.md",
        "corpus_kind: instrument\nquality_warning: Source OCR damaged; manual cleanup recommended.\n",
    ),
    "text/Кляйн - Зависть и благодарность и другие работы 1955-1963.docx": (
        "2_cleaned/Кляйн - Зависть и благодарность и другие работы 1955-1963.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Макдугалл Джойс - Театры тела.pdf": (
        "2_cleaned/МакДугалл Джойс - Театры тела.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Мельцер - Мозаика Я жизнь без боли (ЭЛ психоаналитический процесс).docx": (
        "2_cleaned/Мельцер - Мозаика Я жизнь без боли.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Москва Ключевые элементы ТФП 2019.pptx": (
        "2_cleaned/Moscow - Key elements of TFP 2019.md",
        "corpus_kind: workshop_deck\n",
    ),
    "text/Москва НАРЦИССИЗМ и АНТИСОЦИАЛЬНОСТЬ Йоманс 2020 RUS.pptx": (
        "2_cleaned/Moscow - Narcissism and antisociality Yeomans 2020 RUS.md",
        "corpus_kind: workshop_deck\n",
    ),
    "text/Москва НАРЦИССИЗМ и АНТИСОЦИАЛЬНОСТЬ Йоманс ноябрь 2019.pptx": (
        "2_cleaned/Moscow - Narcissism and antisociality Yeomans November 2019.md",
        "corpus_kind: workshop_deck\n",
    ),
    "text/Москва Неспособность отправиться в самостоятельное плавание 2020.pptx": (
        "2_cleaned/Moscow - Unable to set sail independently 2020.md",
        "corpus_kind: workshop_deck\n",
    ),
    "text/Москва О супервизии 2019 ГОТОВО.pptx": (
        "2_cleaned/Moscow - On supervision 2019.md",
        "corpus_kind: workshop_deck\n",
    ),
    "text/РУКОВОДСТВО ПО ИНТЕРВЬЮ STIPO.docx": (
        "2_cleaned/STIPO - Interview manual RU.md",
        "corpus_kind: instrument\n",
    ),
    "text/Розенберг - Мазохизм смерти и мазохизм-хранитель жизни.docx": (
        "2_cleaned/Розенберг - Мазохизм смерти и мазохизм-хранитель жизни.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Стайнер.Интерпретативные разыгрывания и аналитический сеттинг.docx": (
        "2_cleaned/Стайнер - Интерпретативные разыгрывания и аналитический сеттинг.md",
        "corpus_kind: paper\n",
    ),
    "text/ТФП подростки.docx": ("2_cleaned/ТФП подростки.md", "corpus_kind: clinical_notes\n"),
    "text/ТФП при ПРЛ - клиническое руководство (Clarkin Yeomans Kernberg).docx": (
        "2_cleaned/ТФП при ПРЛ - клиническое руководство Clarkin Yeomans Kernberg.md",
        "corpus_kind: manual\n",
    ),
    "text/Фельдман. Эдипов комплекс и его проявления во внутреннем мире  и терапевтической ситуации.docx": (
        "2_cleaned/Фельдман - Эдипов комплекс и проявления во внутреннем мире и терапевтической ситуации.md",
        "corpus_kind: paper\n",
    ),
    "text/Форма подсчета.docx": (
        "2_cleaned/STIPO - Форма подсчета.md",
        "corpus_kind: instrument\n",
    ),
    "text/Хиншельвуд - Кляйнианский клинический практикум от теории к практике.docx": (
        "2_cleaned/Хиншельвуд - Кляйнианский клинический практикум от теории к практике.md",
        "corpus_kind: book_excerpt\n",
    ),
    "text/Хиншельвуд - Контрперенос и живые моменты.docx": (
        "2_cleaned/Хиншельвуд - Контрперенос и живые моменты.md",
        "corpus_kind: book_excerpt\n",
    ),
}


def front_matter(
    title: str,
    source_rel: str,
    sha256: str,
    extra_yaml: str,
    *,
    duplicate_of: str | None = None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe = title.replace('"', "'")
    dup = ""
    if duplicate_of:
        dup = f"duplicate_of: {json.dumps(duplicate_of, ensure_ascii=False)}\n"
    return (
        "---\n"
        f'title: "{safe}"\n'
        f"tfp4_source: {json.dumps(source_rel, ensure_ascii=False)}\n"
        f"sha256: {sha256}\n"
        f"ingested_at: {now}\n"
        f"{extra_yaml}{dup}"
        "---\n\n"
    )


def main() -> None:
    tfp4 = DEFAULT_TFP4.resolve()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seen_sha: dict[str, tuple[str, str]] = {}
    log: list[str] = []

    ingest_entries = [e for e in data["entries"] if e.get("ingest_to_md")]

    def _dup_sort_key(e: dict) -> tuple:
        rel = e["path_under_tfp4"]
        # Prefer Russian "Форма подсчета" as canonical over byte-identical stipo_form.docx
        pri = 0 if "Форма подсчета" in rel else 1
        return (e["sha256"], pri, rel)

    ingest_entries.sort(key=_dup_sort_key)

    for entry in ingest_entries:
        rel = entry["path_under_tfp4"]
        if rel not in OUTPUT_MAP:
            log.append(f"MISSING_MAP\t{rel}")
            continue
        out_rel, extra_yaml = OUTPUT_MAP[rel]
        src = (tfp4 / rel).resolve()
        if not src.is_file():
            log.append(f"MISSING_SRC\t{rel}")
            continue

        h = entry["sha256"]
        out_path = NOONE / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if h in seen_sha:
            canon_rel, canon_out = seen_sha[h]
            msg = (
                f"Same sha256 as {canon_rel}; writing pointer stub → {canon_out}"
            )
            stub = (
                front_matter(
                    src.stem,
                    rel,
                    h,
                    extra_yaml + "stub: true\n",
                    duplicate_of=canon_out,
                )
                + f"Содержимое идентично файлу с тем же `sha256`; см. `{canon_out}`.\n"
            )
            out_path.write_text(stub, encoding="utf-8")
            log.append(f"STUB_SHA\t{rel}\t->\t{out_rel}")
            continue

        status, body = body_for_source(src)
        if not body.strip():
            log.append(f"FAIL\t{rel}\t{status}")
            continue

        body = clean_markdown_body(body)
        fm = front_matter(src.stem, rel, h, extra_yaml)
        out_path.write_text(fm + body, encoding="utf-8")
        seen_sha[h] = (rel, out_rel)
        log.append(f"OK\t{status}\t{rel}\t->\t{out_rel}")

    report = REPO / "research/tfp4_ingest_run_log.txt"
    report.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"\nWrote log: {report}")


if __name__ == "__main__":
    main()
