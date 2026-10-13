# HESPERIA — Dict calibration pipeline (Ethan): corpus → LLM assist → DLCR truth loop.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""OpenAI-assisted dictionary calibration with Hesperia DLCR as authority."""

from __future__ import annotations

__all__ = ["DEFAULT_OUT", "repo_root"]

DEFAULT_OUT = "outputs/dict_calibration"


def repo_root() -> __import__("pathlib").Path:
    from pathlib import Path

    return Path(__file__).resolve().parents[2]
