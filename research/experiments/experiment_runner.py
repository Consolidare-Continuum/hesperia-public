# HESPERIA — Experiment Framework
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Запуск экспериментов: один и тот же корпус, разные версии онтологии/весов — сравнение результатов.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from hesperia.ontology.registry import load_ontology_registry, get_dict_versions


def run_experiment(
    corpus_entries: list[dict[str, Any]],
    analyze_fn: Callable[[str], dict[str, Any]],
    base_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """
    Прогнать analyze_fn(text) по каждой сессии в corpus_entries.
    corpus_entries: список с полями path (или text) и session_id.
    Возвращает список { session_id, activation, ... }.
    """
    from hesperia.corpus.session_corpus import load_session

    base = Path(base_dir or ".")
    results = []
    for entry in corpus_entries:
        if "text" in entry:
            text = entry["text"]
        else:
            text, _ = load_session(base, entry)
        act = analyze_fn(text)
        results.append({
            "session_id": entry.get("session_id", ""),
            "activation": act,
            "entry": entry,
        })
    return results


def compare_ontology_versions(
    corpus_entries: list[dict[str, Any]],
    analyze_fn_factory: Callable[[dict[str, str]], Callable[[str], dict[str, Any]]],
    registry_paths: list[Path | str] | None = None,
    base_dir: Path | str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Запустить анализ с разными версиями онтологии (разные registry или конфиги).
    analyze_fn_factory(dict_versions) возвращает analyze_fn(text) -> activation.
    registry_paths: список путей к ontology_registry.yaml (или None = один текущий).
    Возвращает { "version_key": [ { session_id, activation }, ... ] }.
    """
    if not registry_paths:
        reg = load_ontology_registry()
        versions = get_dict_versions()
        key = reg.get("ontology_version", "default")
        fn = analyze_fn_factory(versions)
        results = run_experiment(corpus_entries, fn, base_dir=base_dir)
        return {key: results}

    out: dict[str, list[dict[str, Any]]] = {}
    for rp in registry_paths:
        reg = load_ontology_registry(rp)
        versions = get_dict_versions(rp)
        key = reg.get("ontology_version", str(rp))
        fn = analyze_fn_factory(versions)
        results = run_experiment(corpus_entries, fn, base_dir=base_dir)
        out[key] = results
    return out
