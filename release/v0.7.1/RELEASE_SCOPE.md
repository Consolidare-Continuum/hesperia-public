# HESPERIA v0.7.1 — productization hardening patch (CI, security, gap-surfacing pass)

**Codename:** `v7_1_hardening`
**Baseline:** v0.7.0 sealed release
**Authority:** Direct operator task (igareosh), 2026-08-03

## What this release consolidates

A full-repo gap-surfacing and hardening pass on top of v0.7.0 — no new features, no
architecture changes, patch-level fixes only. Two classes of fix:

1. **Dropped wiring restored** — real behavior that regressed silently and had no test
   coverage catching it until this pass looked directly.
2. **Infrastructure/CI/dependency hygiene** — the actual shipping build and CI gates were
   broken since the 2026-07-31 root consolidation; this release is the first sealed point
   where they are confirmed working again, watched live on GitHub, not just claimed.

## Include (incremental over v0.7.0)

- **DLCR pipeline**: the module-level analysis entry point now correctly tags its own
  output with a run identifier again — a comment elsewhere in the codebase already
  assumed this was true; it wasn't.
- **`meta.hesperia_metric` (24_SPEC §10.1)** now actually emitted when
  `HESPERIA_METRIC_EMIT=1` — the module existed and was unit-tested since the METRIC wave
  but had zero production callers. Wired at the runtime/external-contract boundary layer,
  not inside the internal orchestration package, to respect the existing rule that the
  internal package must never import the runtime/services layer.
- **A deterministic gold-value regression table** — two output columns in a pinned test
  fixture had been transposed for 4 of 5 cases; corrected against a direct, reproducible
  engine run.
- **`Sealed runtime gate` and `prod-code-only` CI restored** — both had been failing on
  every push to `main` since the root consolidation (an import allowlist file never
  updated for an internal module move; a build-staging file list still referenced a
  top-level directory removed in that same consolidation). Confirmed green via live CI
  monitoring, not just local runs.
- **Shipping Docker images build again** — the product/shipping Dockerfiles carried the
  same stale removed-directory reference; verified with a real image build.
- **Dependency security**: the ML similarity-search package stack (`torch`,
  `transformers`, `huggingface-hub`, `sentence-transformers`) and the JS build-tool stack
  under the internal viewer app bumped to close every dependabot alert present at session
  start (37 → 0, confirmed live via independent vulnerability-scan tools and GitHub's own
  alert API). Included a coordinated major-version bump on the similarity-search package,
  verified byte-identical output for matched input before and after.
- **Dead/orphaned code removed**: one fully unreferenced internal compatibility shim, and
  two fully-orphaned duplicate dependency-pin files (only one of three near-identical
  files was ever actually installed anywhere), which had been tripling the same CVE alert
  across three files.
- Small doc/stale-reference fixes: a retired-module note that had drifted out of date;
  CLI `--help` text corrected.

## Deferred (unchanged, inherited from v0.7.0)

Same three items v0.7.0 already deferred, still explicitly out of scope — now with
`xfail(strict=True)` markers citing the prior release doc instead of silent test
failures:

- The static metric-geometry emit block (METRIC-22)
- Full point-of-view position live emit (METRIC-23, HRES-04)
- Traversal cost metric (METRIC-24/25)

## Verification

- Full test suite: clean (0 unexpected failures; 3 documented, cited `xfail`).
- Automated release-gate checks (import boundary, sealing scan, public API snapshot,
  forbidden-zone imports, shipping surface allowlist + creep-cap audit, engine boundary
  checks, DLCR regression) all pass locally.
- `Sealed runtime gate` and `prod-code-only` GitHub Actions: green, watched live.
- Independent vulnerability scans (Python + JS): zero known vulnerabilities.
- Real shipping Docker image build: succeeds.

## Pin

- System version: **0.7.1**
- `components.core_engine`, `components.calibration`: **0.7.1** (tracked with
  `system_version`, matching the 0.6.5→0.7.0 seal precedent)
- All other components (`dynamics`, `triz`, `clinical`, `router`, `fpf_bridge`)
  unchanged — not touched this pass
- `anchor_map_id`: unchanged from v0.7.0

**SIGNED: Developer (Felix) | Claude Code context | 2026-08-03 | v0.7.1 hardening patch, direct operator task**
