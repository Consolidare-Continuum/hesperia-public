# HESPERIA — openai_key_load tests.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path

from runtime.shipping.openai_key_load import ensure_openai_api_key


def test_ensure_openai_from_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-from-env-0123456789abcdef")
    assert ensure_openai_api_key() == "sk-test-from-env-0123456789abcdef"


def test_ensure_openai_from_tmp_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    key_file = tmp_path / "openai_api_key.txt"
    key_file.write_text("sk-test-from-file-0123456789abcdef\n", encoding="utf-8")
    monkeypatch.setattr(
        "runtime.shipping.openai_key_load._CC_KEY_FILE",
        key_file,
    )
    monkeypatch.setattr(
        "runtime.shipping.openai_key_load._repo_root",
        lambda: tmp_path / "missing_repo",
    )
    assert ensure_openai_api_key() == "sk-test-from-file-0123456789abcdef"
