# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Provenance metadata tests.
Verify get_engine_provenance() fields, timestamp format, and engine_version presence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.provenance.provenance_info import get_engine_provenance

# ISO-8601 UTC: 2026-03-11T14:32:05Z
ISO8601_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def test_provenance_fields_exist() -> None:
    """get_engine_provenance() returns all required fields."""
    p = get_engine_provenance()
    assert "engine_version" in p
    assert "pipeline_version" in p
    assert "schema_version" in p
    assert "generation_timestamp" in p
    assert "python_version" in p


def test_timestamp_format_valid() -> None:
    """generation_timestamp is ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)."""
    p = get_engine_provenance()
    ts = p.get("generation_timestamp", "")
    assert isinstance(ts, str)
    assert ISO8601_UTC_RE.match(ts), f"timestamp must match ISO-8601 UTC, got {ts!r}"


def test_engine_version_present() -> None:
    """engine_version is a non-empty string (pyproject or git fallback)."""
    p = get_engine_provenance()
    ev = p.get("engine_version")
    assert isinstance(ev, str)
    assert len(ev) > 0


def test_schema_version_fixed() -> None:
    """schema_version is HSD_v1.0."""
    p = get_engine_provenance()
    assert p.get("schema_version") == "HSD_v1.0"


def test_python_version_consistent() -> None:
    """python_version matches current interpreter."""
    p = get_engine_provenance()
    pv = p.get("python_version", "")
    expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert pv == expected


def test_dossier_written_with_meta() -> None:
    """Written dossier contains meta with engine_version and generation_timestamp."""
    from runtime.dossier import write_dossier_json
    from runtime.provenance import get_engine_provenance

    dossier = {"run": "L1_through_L9", "text_preview": "x", "diagnostics": {}}
    for i in range(1, 10):
        dossier[f"L{i}"] = {}
    meta = get_engine_provenance()
    dossier["meta"] = meta
    path = _REPO / "tests" / "_dossier_provenance.json"
    try:
        write_dossier_json(dossier, path)
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "meta" in data
        assert data["meta"]["engine_version"]
        assert data["meta"]["generation_timestamp"]
        assert ISO8601_UTC_RE.match(data["meta"]["generation_timestamp"])
    finally:
        path.unlink(missing_ok=True)
