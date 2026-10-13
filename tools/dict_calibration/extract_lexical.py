# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Task 1 — Corpus → deterministic lexical candidates (no semantics).

Extracts n-grams (1–5), optional dependency pairs (spaCy), modal phrase seeds.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

# RU/EN modal / stance seeds (substring match on lowered clause)
MODAL_SEEDS = (
    "i feel ",
    "i felt ",
    "feels like ",
    "kinda feel",
    "they always ",
    "she always ",
    "he always ",
    "nobody ",
    "no one ",
    "я чувствую",
    "мне кажется",
    "как будто",
    "всегда ",
    "никто ",
    "никогда ",
    "боюсь что",
    "страшно ",
)

WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)


def _canon_line(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    return s.casefold()


def _tokens(text: str) -> list[str]:
    return WORD_RE.findall(_canon_line(text))


def _iter_markdown_docs(corpus_dir: Path) -> Iterator[tuple[str, str]]:
    for p in sorted(corpus_dir.rglob("*.md")):
        if p.name.startswith("_"):
            continue
        fid = str(p.relative_to(corpus_dir))
        body = p.read_text(encoding="utf-8", errors="replace")
        yield fid, body


def _ngrams_from_tokens(tokens: list[str], n_max: int = 5) -> Iterator[tuple[str, str]]:
    """Yield (joined n-gram, lemma placeholder = same for n-gram layer)."""
    for n in range(1, n_max + 1):
        for i in range(0, len(tokens) - n + 1):
            chunk = tokens[i : i + n]
            yield (" ".join(chunk), " ".join(chunk))


def _modal_hits(text_cf: str) -> Iterator[str]:
    for m in MODAL_SEEDS:
        if m in text_cf:
            start = 0
            while True:
                idx = text_cf.find(m, start)
                if idx < 0:
                    break
                end = min(len(text_cf), idx + 80)
                frag = text_cf[idx:end].strip()
                if frag:
                    yield frag
                start = idx + len(m)


def _spacy_dep_pairs(text: str, nlp: Any) -> Iterator[tuple[str, str, str]]:
    doc = nlp(text[:200_000])
    for tok in doc:
        if tok.dep_ in ("dobj", "obj", "obl", "attr") and tok.head.pos_ in ("VERB", "AUX"):
            h = (tok.head.lemma_ or tok.head.text or "").strip().lower()
            d = (tok.lemma_ or tok.text or "").strip().lower()
            if h and d and len(h) > 1 and len(d) > 1:
                yield (h, d, f"{h} {d}")


def extract_corpus(
    corpus_dir: Path,
    *,
    min_freq: int = 2,
    max_ngram_types: int = 200_000,
) -> list[dict[str, Any]]:
    """
    Walk ``corpus_dir`` for ``*.md`` and aggregate frequency tables.

    Returns sorted rows: ``text``, ``lemma``, ``pattern_type``, ``freq``, ``source_doc``.
    """
    corpus_dir = corpus_dir.resolve()
    ngram_counts: Counter[str] = Counter()
    ngram_docs: dict[str, str] = {}
    dep_counts: Counter[str] = Counter()
    dep_lemma: dict[str, tuple[str, str]] = {}
    dep_docs: dict[str, str] = {}
    modal_counts: Counter[str] = Counter()
    modal_docs: dict[str, str] = {}

    nlp = None
    try:
        import spacy  # type: ignore[import-untyped]

        for model in ("ru_core_news_sm", "en_core_web_sm"):
            try:
                nlp = spacy.load(model)
                break
            except OSError:
                continue
    except ImportError:
        nlp = None

    for fid, body in _iter_markdown_docs(corpus_dir):
        for para in re.split(r"\n{2,}", body):
            para_cf = _canon_line(para)
            if len(para_cf) < 3:
                continue
            toks = _tokens(para)
            for g, lem in _ngrams_from_tokens(toks, 5):
                if len(g) < 2:
                    continue
                ngram_counts[g] += 1
                ngram_docs.setdefault(g, fid)
            for frag in _modal_hits(para_cf):
                modal_counts[frag] += 1
                modal_docs.setdefault(frag, fid)
            if nlp is not None:
                try:
                    for h, d, phrase in _spacy_dep_pairs(para, nlp):
                        dep_counts[phrase] += 1
                        dep_lemma[phrase] = (h, d)
                        dep_docs.setdefault(phrase, fid)
                except Exception:
                    pass

    rows: list[dict[str, Any]] = []

    for g, c in ngram_counts.most_common():
        if c < min_freq:
            break
        if len(rows) >= max_ngram_types:
            break
        rows.append(
            {
                "text": g,
                "lemma": g,
                "pattern_type": "ngram",
                "freq": c,
                "source_doc": ngram_docs.get(g, ""),
            }
        )

    for phrase, c in dep_counts.most_common():
        if c < min_freq:
            break
        h, d = dep_lemma.get(phrase, (phrase.split()[0], phrase.split()[-1]))
        rows.append(
            {
                "text": phrase,
                "lemma": f"{h}|{d}",
                "pattern_type": "dep",
                "freq": c,
                "source_doc": dep_docs.get(phrase, ""),
            }
        )

    for frag, c in modal_counts.most_common():
        if c < min_freq:
            break
        rows.append(
            {
                "text": frag[:200],
                "lemma": frag[:200],
                "pattern_type": "modal",
                "freq": c,
                "source_doc": modal_docs.get(frag, ""),
            }
        )

    rows.sort(key=lambda r: (-int(r["freq"]), r["pattern_type"], r["text"]))
    return rows
