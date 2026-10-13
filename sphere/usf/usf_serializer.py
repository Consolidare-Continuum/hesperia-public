# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF serializer: deterministic JSON to string and file.
UTF-8, stable key ordering (architecture order from generator), no injected timestamps.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def serialize_usf_to_json(usf: dict[str, Any]) -> str:
    """
    Serialize USF to JSON string. Deterministic: same USF object produces same bytes.
    Key order follows generator (do not sort). UTF-8. Indent 2.
    """
    return json.dumps(
        usf,
        ensure_ascii=False,
        sort_keys=False,
        indent=2,
    )


def save_usf_json(usf: dict[str, Any], output_path: str | Path) -> None:
    """Write USF to file as UTF-8 JSON. No non-deterministic fields added."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    s = serialize_usf_to_json(usf)
    path.write_text(s, encoding="utf-8")


def load_usf_json(input_path: str | Path) -> dict[str, Any]:
    """Load USF from JSON file. UTF-8."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"USF file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
