"""T08–T12 — Load Kernberg/TFP prompt templates; safe rendering (injection-aware)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .constants import PROMPT_PACK_ID_KERNBERG_V1

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def prompt_dir() -> Path:
    return _PROMPTS_DIR


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
        enable_async=False,
    )


def load_system_prompt_kernberg_v1() -> str:
    p = _PROMPTS_DIR / "kernberg_iteration_review_system_v1.txt"
    return p.read_text(encoding="utf-8")


def render_user_prompt_kernberg_v1(
    *,
    segment_json_for_llm: dict,
    client_text_plain: str,
    parameters_summary_lines: str,
) -> str:
    """
    T09 + T12: Variables are passed from Python; client text is embedded via json.dumps
    in the template for the excerpt block — never raw-interpolate untrusted prose into Jinja.
    """
    env = _jinja_env()
    t = env.get_template("kernberg_iteration_review_user_v1.jinja")
    return t.render(
        prompt_pack_id=PROMPT_PACK_ID_KERNBERG_V1,
        segment_json_text=json.dumps(segment_json_for_llm, ensure_ascii=False, indent=2),
        client_text_json=json.dumps(client_text_plain, ensure_ascii=False),
        parameters_summary_lines=parameters_summary_lines,
    )


def red_team_note() -> str:
    """T12 — documented boundary: user template uses Jinja only for structure; prose from JSON dumps."""
    return (
        "User template uses json.dumps for client text and structured segment payload; "
        "do not add raw Jinja {{ client_text }} without escaping."
    )
