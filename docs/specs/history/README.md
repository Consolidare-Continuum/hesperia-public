# Restored specs: 34_SPEC through 42_SPEC (+ 34_SPEC N1)

These ten files were not in this repo's working tree as of 2026-06-30 (verified: `find . -iname
"*34_SPEC*"` through `*42_SPEC*` returned zero matches outside the code that cites them). They were
located in `hesperia_full_repo_snapshot_20260314.tar.gz`
(`/data/hesperia/hesperia-backup/snapshots/`), a full-repo archive tarball from three weeks after
their Feb 2026 authoring date, and copied here on 2026-07-01. The archive tarball remains the
historical source; this repo no longer depends on it to check these citations.

Each is the canonical v0.4.x math spec for one of the nine numbered pipeline layers
(`core/layers/layer_1.py` through `layer_9.py`), each independently verified line-by-line against
its implementing code — see `docs/foundations/output_catalog.md` for the resulting per-layer
variable tables, and `docs/foundations/provenance.md` for the full recovery chain and what stayed
unrecoverable (`hesperia/extensions/dynamics/`'s own spec, checked in this same archive and in the
`hesperia-dev-backup` git mirror, is genuinely absent from both).
