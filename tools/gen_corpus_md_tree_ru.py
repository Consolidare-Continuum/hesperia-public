#!/usr/bin/env python3
"""Generate CORPUS_MD_TREE_RU.md under research/_noone_local/2_cleaned/ (Russian-filename .md index)."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO / "research/_noone_local/2_cleaned"
INDEX_NAME = "CORPUS_MD_TREE_RU.md"
SESSION_MODULE = REPO / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1" / "corpus" / "sessions"
LEGACY_NOONE_ROOT = REPO / "research" / "_noone_local"
CYR = re.compile(r"[А-Яа-яЁё]")
# author: prefix before " - " / " — " / " -" (tight hyphen) at word boundary
AUTH_SPLIT = re.compile(r"^(.+?)(?:\s+-\s+|\s+—\s+|\s+-(?=\S))")


def parse_front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    for line in text[4:end].split("\n"):
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        out[k] = v
    return out


def author_from_text(title_or_stem: str) -> str:
    s = title_or_stem.strip()
    m = AUTH_SPLIT.match(s)
    if m:
        a = m.group(1).strip()
        if len(a) <= 80:
            return a
    if ". " in s and len(s.split(". ")[0]) < 5 and " " in s.split(". ", 1)[-1][:30]:
        head, _, tail = s.partition(". ")
        if " " in tail:
            return f"{head}. {tail.split()[0]}"
    return "—"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Default: <root>/CORPUS_MD_TREE_RU.md",
    )
    args = ap.parse_args()
    root: Path = args.root.resolve()
    out_path = args.out or (root / INDEX_NAME)

    rows: list[tuple[str, str, str, str]] = []
    for p in sorted(root.rglob("*.md")):
        if p.name == INDEX_NAME:
            continue
        if "ingest_from_tfp4_md" in str(p):
            continue
        if not CYR.search(p.name):
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = parse_front_matter(raw)
        title = fm.get("title", p.stem)
        auth = author_from_text(title)
        if auth == "—":
            auth = author_from_text(p.stem)
        rows.append((rel, p.name, auth, title))

    by_top: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for row in rows:
        top = row[0].split("/")[0] if "/" in row[0] else "."
        by_top[top].append(row)

    def _session_stems(root: Path) -> list[str]:
        if not root.is_dir():
            return []
        return sorted(
            p.name
            for p in root.glob("*.md")
            if re.match(r"^\d{2}-\d{2}-\d{4}\.md$", p.name)
            or re.match(r"^\d+-\d+-\d+-\d{4}\.md$", p.name)
        )

    # Module corpus/sessions (ingest output) + legacy root _noone_local/*.md
    sessions = sorted(
        set(_session_stems(SESSION_MODULE)) | set(_session_stems(LEGACY_NOONE_ROOT))
    )

    lines: list[str] = [
        "<!--",
        "HESPERIA — русскоязычный слой корпуса: только .md, только имена файлов с кириллицей.",
        "Автор: эвристика из YAML title или префикса имени до « - » / « — » / « -».",
        "Пересборка: python3 tools/gen_corpus_md_tree_ru.py",
        "-->",
        "",
        "# Дерево корпуса: русскоязычные Markdown-файлы",
        "",
        "Корень сканирования: `research/_noone_local/2_cleaned/`.",
        "",
        "**Критерий:** в **имени файла** есть хотя бы одна кириллическая буква. Файлы только с латиницей в имени сюда **не** входят.",
        "",
        "**Всего:** %d файлов `.md`." % len(rows),
        "",
        "Сессионные `.md`: преимущественно `hesperia/modules/tfp/data/tfp_v1/corpus/sessions/` (DD-MM-YYYY.md); устаревший корень `research/_noone_local/*.md` тоже учитывается если есть.",
        "",
        "## Дерево (плоский список)",
        "",
        "```",
        "2_cleaned/",
    ]

    if set(by_top.keys()) == {"."}:
        items = sorted(by_top["."], key=lambda r: r[0].lower())
        for j, (rel, _name, auth, _) in enumerate(items):
            flast = j == len(items) - 1
            b = "└── " if flast else "├── "
            lines.append(f"{b}{rel}  — **{auth}**")
    else:
        for top in sorted(by_top.keys()):
            items = sorted(by_top[top], key=lambda r: r[0].lower())
            lines.append(f"├── {top}/")
            for j, (rel, name, auth, _) in enumerate(items):
                flast = j == len(items) - 1
                br = "└── " if flast else "├── "
                sub = rel.split("/", 1)[1] if "/" in rel else name
                lines.append(f"│   {br}{sub}  — **{auth}**")
    lines.append("```")

    if sessions:
        lines.extend(
            [
                "",
                "## Сессии (корпус `tfp_v1/corpus/sessions/` и устар. корень `_noone_local/`)",
                "",
                "Заметки по сессиям; в основной таблице выше не показаны из‑за критерия по имени файла.",
                "",
                "```",
                *sessions,
                "```",
            ]
        )

    lines.extend(
        [
            "",
            "## Таблица: путь — автор — заголовок",
            "",
            "| Путь | Автор | Заголовок |",
            "|------|-------|-----------|",
        ]
    )
    for rel, _name, auth, title in sorted(rows, key=lambda r: r[0].lower()):
        t = title.replace("|", "\\|").replace("\n", " ")
        a = auth.replace("|", "\\|")
        r = rel.replace("|", "\\|")
        lines.append(f"| `{r}` | {a} | {t} |")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path} ({len(rows)} cyrillic-name files, {len(sessions)} session root files)"
    )


if __name__ == "__main__":
    main()
