"""`python -m hesperia.run` full deterministic runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.engine.pipeline_runner import run_pipeline, write_run_manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Run full deterministic Hesperia pipeline.")
    ap.add_argument("input", help="Input text file path.")
    ap.add_argument("--config", required=True, help="Config yaml path.")
    ap.add_argument("--until", choices=["preprocess", "project", "postprocess"], default=None)
    ap.add_argument("--only", default=None, help="Only run specific module name/path/alias.")
    ap.add_argument("--out", default=None, help="Write dossier JSON to file.")
    ap.add_argument("--manifest-out", default="run_manifest.json", help="Run manifest output path.")
    args = ap.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    dossier = run_pipeline(
        text,
        config_path=Path(args.config),
        until_phase=args.until,
        only_module=args.only,
    )
    payload = json.dumps(dossier, ensure_ascii=False, sort_keys=True, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    write_run_manifest(dossier, Path(args.manifest_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

