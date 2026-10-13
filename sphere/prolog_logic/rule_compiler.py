# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Prolog-style rule compiler: parse rule text into deterministic internal representation.
Strict grammar validation; rejects malformed rules with explicit errors.
"""

from __future__ import annotations

import re
from typing import Any

# Atom: lowercase letter, then letters/digits/underscore
_ATOM_RE = re.compile(r"[a-z][a-z0-9_]*")
# Number: integer or float
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d*)?|\.\d+")


def _strip_comment(line: str) -> str:
    """Remove comment from % to end of line."""
    idx = line.find("%")
    if idx >= 0:
        line = line[:idx]
    return line.strip()


def _parse_term(s: str) -> str | float | int:
    """Parse a single term: atom (return as str) or number (return as int/float)."""
    s = s.strip()
    if not s:
        raise ValueError(f"Empty term")
    if _NUMBER_RE.fullmatch(s):
        if "." in s:
            return float(s)
        return int(s)
    if _ATOM_RE.fullmatch(s):
        return s
    raise ValueError(f"Invalid term: {s!r} (must be lowercase atom or number)")


def _parse_predicate(s: str) -> dict[str, Any]:
    """Parse predicate or atom: name or name(term, ...). Returns {predicate, args}."""
    s = s.strip()
    if not s:
        raise ValueError("Empty predicate")
    if s[0].isupper():
        raise ValueError(f"Uppercase predicate not allowed in v1: {s!r}")
    if "(" not in s:
        if _ATOM_RE.fullmatch(s):
            return {"predicate": s, "args": []}
        raise ValueError(f"Invalid atom: {s!r}")
    # name(...)
    paren = s.index("(")
    name = s[:paren].strip()
    rest = s[paren + 1 :].strip()
    if not rest.endswith(")"):
        raise ValueError(f"Unclosed parenthesis in {s!r}")
    rest = rest[:-1].strip()  # drop )
    if not name or not _ATOM_RE.fullmatch(name):
        raise ValueError(f"Invalid predicate name: {name!r}")
    if not rest:
        return {"predicate": name, "args": []}
    # Parse comma-separated terms (no nesting in v1)
    args: list[Any] = []
    depth = 0
    start = 0
    for i, c in enumerate(rest + ","):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            term = rest[start:i].strip()
            if term:
                args.append(_parse_term(term))
            start = i + 1
    if depth != 0:
        raise ValueError(f"Nested terms not allowed in v1: {s!r}")
    term = rest[start:].strip()
    if term:
        args.append(_parse_term(term))
    return {"predicate": name, "args": args}


def parse_fact(line: str) -> dict[str, Any]:
    """
    Parse a single fact line. Must end with '.'.
    Returns {"type": "fact", "predicate": str, "args": list}.
    Raises ValueError on malformed input.
    """
    line = _strip_comment(line)
    if not line:
        raise ValueError("Empty line")
    if not line.endswith("."):
        raise ValueError(f"Fact must end with '.': {line!r}")
    line = line[:-1].strip()
    if not line:
        raise ValueError("Fact is empty after period")
    if ":-" in line:
        raise ValueError(f"Fact must not contain ':-': {line!r}")
    p = _parse_predicate(line)
    return {"type": "fact", "predicate": p["predicate"], "args": p["args"]}


def parse_rule(line: str) -> dict[str, Any]:
    """
    Parse a single rule line. Must be head :- body.
    Returns {"type": "rule", "head": {predicate, args}, "body": [{predicate, args}, ...]}.
    Raises ValueError on malformed input (e.g. empty body).
    """
    line = _strip_comment(line)
    if not line:
        raise ValueError("Empty line")
    if not line.endswith("."):
        raise ValueError(f"Rule must end with '.': {line!r}")
    line = line[:-1].strip()
    if ":-" not in line:
        raise ValueError(f"Rule must contain ':-': {line!r}")
    parts = line.split(":-", 1)
    if len(parts) != 2:
        raise ValueError(f"Rule must have exactly one ':-': {line!r}")
    head_s, body_s = parts[0].strip(), parts[1].strip()
    if not head_s:
        raise ValueError("Rule head is empty")
    if not body_s or body_s.strip() == ".":
        raise ValueError("Rule body is empty")
    head = _parse_predicate(head_s)
    # Parse body: comma-separated goals (no nesting)
    body_goals: list[dict[str, Any]] = []
    if ",," in body_s or body_s.startswith(",") or body_s.endswith(","):
        raise ValueError("Empty or duplicate separator in body")
    for part in body_s.split(","):
        part = part.strip()
        if not part:
            raise ValueError("Empty goal in rule body")
        body_goals.append(_parse_predicate(part))
    return {
        "type": "rule",
        "head": {"predicate": head["predicate"], "args": head["args"]},
        "body": body_goals,
    }


def _classify_line(line: str) -> str:
    """Return 'fact' or 'rule' based on content (after stripping)."""
    s = _strip_comment(line)
    if not s:
        return "blank"
    if ":-" in s and s.endswith("."):
        return "rule"
    return "fact"


def compile_knowledge_base(lines: list[str]) -> list[dict[str, Any]]:
    """
    Parse lines into a deterministic list of compiled facts and rules.
    Strips comments and blank lines. Preserves source order.
    Each item is either {"type": "fact", "predicate", "args"} or
    {"type": "rule", "head", "body"}.
    Raises ValueError on first malformed line.
    """
    result: list[dict[str, Any]] = []
    for i, raw in enumerate(lines):
        line = _strip_comment(raw)
        if not line:
            continue
        kind = _classify_line(raw)
        if kind == "blank":
            continue
        try:
            if kind == "rule":
                result.append(parse_rule(raw))
            else:
                result.append(parse_fact(raw))
        except ValueError as e:
            raise ValueError(f"Line {i + 1}: {e}") from e
    return result
