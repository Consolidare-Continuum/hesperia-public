# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA batch analysis runner.
Processes multiple texts and writes one dossier per text.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Tuple

# Repo root for assets and path setup
_HERE = Path(__file__).resolve().parent
_HESPERIA = _HERE.parents[1]
if str(_HESPERIA) not in sys.path:
    sys.path.insert(0, str(_HESPERIA))

from runtime.dossier import validate_dossier_schema, verify_dossier_checksum, write_dossier_json
from runtime.dossier.index_manager import update_dossier_index
from runtime.provenance import build_run_manifest, get_engine_provenance

from .run_l1_through_l9 import run_pipeline_for_text


def _batch_worker_item(
    task: Tuple[str, str, str, bool, str],
) -> Tuple[str | None, str | None]:
    """
    Worker for one text: run pipeline, build dossier, validate, write dossier.
    Returns (output_path, dossier_id) on success, (None, None) on failure. Does NOT update index.
    task: (text, output_path_str, policy_mode, validate_dossier, hesperia_root).
    """
    text, output_path_str, policy_mode, validate_dossier, hesperia_root = task
    try:
        if hesperia_root and hesperia_root not in sys.path:
            sys.path.insert(0, hesperia_root)
        from pathlib import Path
        from types import SimpleNamespace
        from runtime.dossier import validate_dossier_schema, write_dossier_json
        from runtime.provenance import build_run_manifest, get_engine_provenance
        from runtime.pipeline.run_l1_through_l9 import run_pipeline_for_text
        from core.layers import load_defaults

        assets = Path(hesperia_root) / "assets" / "lexicon" / "curated"
        defaults = load_defaults()
        out = run_pipeline_for_text(
            text,
            assets_root=assets,
            defaults=defaults,
            profile_id=None,
            profile=None,
            policy_mode=policy_mode,
        )
        dossier_payload = dict(out)
        meta = dict(dossier_payload.get("meta", {}))
        meta.update(get_engine_provenance())
        args_like = SimpleNamespace(
            text=text[:80],
            out=None,
            profile=None,
            policy_mode=policy_mode,
            write_dossier=Path(output_path_str),
            validate_dossier=validate_dossier,
        )
        meta["run_manifest"] = build_run_manifest(args_like, defaults, None, None, assets)
        dossier_payload["meta"] = meta
        if validate_dossier:
            validate_dossier_schema(dossier_payload)
        dossier_id = write_dossier_json(dossier_payload, output_path_str)
        return (output_path_str, dossier_id)
    except Exception:
        return (None, None)


def resolve_inputs(input_paths: List[Path]) -> List[Tuple[str, str]]:
    """
    Resolve CLI input to a list of (label, text).
    - Single directory: glob *.txt in that directory.
    - Single .json file: load as JSON array of strings (list of texts).
    - Otherwise: treat as list of text file paths.
    """
    if not input_paths:
        return []
    if len(input_paths) == 1:
        p = Path(input_paths[0])
        if p.is_dir():
            files = sorted(p.glob("*.txt"))
            return [(f.stem, f.read_text(encoding="utf-8")) for f in files]
        if p.suffix.lower() == ".json" and p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [(f"item_{i:03d}", (str(x) if x is not None else "")) for i, x in enumerate(data)]
            except (json.JSONDecodeError, OSError):
                pass
    # List of text files
    entries: List[Tuple[str, str]] = []
    for p in input_paths:
        path = Path(p)
        if path.exists() and path.is_file():
            entries.append((path.stem, path.read_text(encoding="utf-8")))
    return entries


def run_batch(
    input_paths: List[Path],
    output_dir: Path,
    policy_mode: str = "STRUCTURE_PLUS_CONTEXT",
    validate_dossier: bool = False,
    assets_root: Path | None = None,
    index_path: Path | str | None = None,
    workers: int = 1,
    resume: bool = False,
    content_addressed: bool = False,
) -> List[Path]:
    """
    For each resolved text: run pipeline, optionally validate, write dossier, update index.
    Returns list of written dossier paths (this run only).
    resume: if True, skip items whose expected dossier exists and passes verify_dossier_checksum;
            ensure skipped dossiers are in the index. (Slot-based; ignored for content_addressed.)
    content_addressed: if True, write dossier_<dossier_id>.json (id = first 12 chars of checksum).
    """
    from core.layers import load_defaults

    entries = resolve_inputs(input_paths)
    if not entries:
        return []

    assets = assets_root if assets_root is not None else _HESPERIA / "assets" / "lexicon" / "curated"
    defaults = load_defaults()
    profile_id = None
    profile = None

    written: List[Path] = []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    hesperia_root = str(_HESPERIA)

    def should_skip(i: int) -> bool:
        p = output_dir / f"dossier_{i:03d}.json"
        return p.exists() and verify_dossier_checksum(p)

    if workers is None or workers <= 1:
        # Sequential
        for i, (label, text) in enumerate(entries, start=1):
            if content_addressed:
                out_path = output_dir / f".tmp_{i:03d}.json"
            else:
                out_path = output_dir / f"dossier_{i:03d}.json"
            if resume and not content_addressed and should_skip(i):
                print("SKIP existing", out_path.name, file=sys.stderr)
                update_dossier_index(out_path, index_path)
                continue
            print("RUN ", out_path.name, file=sys.stderr)
            out = run_pipeline_for_text(
                text,
                assets_root=assets,
                defaults=defaults,
                profile_id=profile_id,
                profile=profile,
                policy_mode=policy_mode,
            )
            dossier_payload = dict(out)
            meta = dict(dossier_payload.get("meta", {}))
            meta.update(get_engine_provenance())
            args_like = SimpleNamespace(
                text=text[:80],
                out=None,
                profile=None,
                policy_mode=policy_mode,
                write_dossier=out_path,
                validate_dossier=validate_dossier,
            )
            meta["run_manifest"] = build_run_manifest(args_like, defaults, profile_id, profile, assets)
            dossier_payload["meta"] = meta

            if validate_dossier:
                validate_dossier_schema(dossier_payload)
            dossier_id = write_dossier_json(dossier_payload, out_path)
            if content_addressed:
                final_path = output_dir / f"dossier_{dossier_id}.json"
                out_path.rename(final_path)
                update_dossier_index(final_path, index_path)
                written.append(final_path)
            else:
                update_dossier_index(out_path, index_path)
                written.append(out_path)
        return written

    # Parallel: collect skip vs run indices
    to_run: List[Tuple[int, str, str]] = []  # (i, label, text)
    for i, (label, text) in enumerate(entries, start=1):
        out_path = output_dir / f"dossier_{i:03d}.json"
        if resume and not content_addressed and should_skip(i):
            print("SKIP existing", out_path.name, file=sys.stderr)
            update_dossier_index(out_path, index_path)
            continue
        to_run.append((i, label, text))
    for i, label, text in to_run:
        if content_addressed:
            p = output_dir / f".tmp_{i:03d}.json"
        else:
            p = output_dir / f"dossier_{i:03d}.json"
        print("RUN ", p.name, file=sys.stderr)
    tasks = [
        (
            text,
            str(output_dir / (f".tmp_{i:03d}.json" if content_addressed else f"dossier_{i:03d}.json")),
            policy_mode,
            validate_dossier,
            hesperia_root,
        )
        for i, label, text in to_run
    ]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_batch_worker_item, tasks))
    for path_str, dossier_id in results:
        if path_str and dossier_id:
            if content_addressed:
                final_path = output_dir / f"dossier_{dossier_id}.json"
                Path(path_str).rename(final_path)
                update_dossier_index(final_path, index_path)
                written.append(final_path)
            else:
                update_dossier_index(path_str, index_path)
                written.append(Path(path_str))
    return written


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m runtime.pipeline.batch_runner")
    ap.add_argument(
        "input",
        type=Path,
        nargs="+",
        help="Directory (single), JSON file with list of texts (single), or list of text files",
    )
    ap.add_argument("--out", type=Path, required=True, help="Output directory for dossiers (e.g. batch_results)")
    ap.add_argument(
        "--policy-mode",
        dest="policy_mode",
        default="STRUCTURE_PLUS_CONTEXT",
        choices=("STRUCTURE_ONLY", "STRUCTURE_PLUS_CONTEXT", "FULL_INTERPRETATION"),
        help="Interpretation policy mode",
    )
    ap.add_argument("--validate-dossier", action="store_true", help="Validate each dossier schema before writing")
    ap.add_argument("--workers", type=int, default=1, metavar="N", help="Number of parallel workers (default: 1)")
    ap.add_argument("--resume", action="store_true", help="Skip existing valid dossiers; process only missing; sync index")
    ap.add_argument("--content-addressed", action="store_true", help="Write dossiers as dossier_<id>.json (id=first 12 chars of checksum)")
    args = ap.parse_args()

    written = run_batch(
        args.input,
        args.out,
        policy_mode=args.policy_mode,
        validate_dossier=args.validate_dossier,
        workers=args.workers,
        resume=args.resume,
        content_addressed=args.content_addressed,
    )
    if written:
        print("Batch complete. Dossiers written:", len(written), file=sys.stderr)
        for p in written:
            print(p, file=sys.stderr)
    elif args.resume:
        print("Batch complete. All dossiers already present.", file=sys.stderr)
    else:
        print("No inputs resolved. Check path(s) or JSON format.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
