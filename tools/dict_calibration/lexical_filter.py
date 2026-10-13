# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Drop high-freq junk (stopwords, 1-token noise) before LLM normalize / propose."""

from __future__ import annotations

from typing import Any

# RU + EN function words / pronouns — not TFP lexical targets
_STOP = frozenset(
    """
    и в не на что как а но по из за для от до при без над под об о с со же ли бы то
    это этот эта эти тот та те том тем ту мне меня мной нам вас вам его ее их он она они
    мы ты вы кто чей кого кому чем когда где почему также уже еще только очень уже ли
    если или либо однако одной одного одна один одним одну своего своей своих своим
    всех всем всеми всего всю всё все весь вся вроде вновь между тем самым самого
    the a an of to in for and or is are was were be been being it its this that these
    those with from at by on as not but if into than then so such no nor too very
    can could should would may might must will shall has have had having do does did
    he she they we you i me my our your their his her them us about above after again
    against all any both each few more most other some such only own same so than
    too very just also now here there when where why how both either neither
    """.split()
)


def filter_rows_for_llm(rows: list[dict[str, Any]], *, max_rows: int | None = None) -> list[dict[str, Any]]:
    """
    Keep dependency/modal rows; keep n-grams with >=2 tokens or one long non-stop token;
    sort by freq desc; optionally cap.
    """
    kept: list[dict[str, Any]] = []
    for r in rows:
        use = str(r.get("normalized") or r.get("text", "")).strip().lower()
        if not use:
            continue
        pt = str(r.get("pattern_type") or "")
        if pt in ("dep", "modal"):
            kept.append(r)
            continue
        toks = use.split()
        if len(toks) >= 2:
            kept.append(r)
            continue
        if len(toks) == 1 and len(toks[0]) >= 5 and toks[0] not in _STOP:
            kept.append(r)
            continue
    kept.sort(key=lambda x: (-int(x.get("freq", 0)), -len(str(x.get("normalized") or x.get("text", "")))))
    if max_rows is not None and len(kept) > max_rows:
        kept = kept[:max_rows]
    return kept
