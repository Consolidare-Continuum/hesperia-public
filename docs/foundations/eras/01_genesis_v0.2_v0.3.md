# Era 1: Genesis — v0.2 → v0.3.0 (2026-02-18 → 2026-02-22)

## Evidence

```
$ git log --oneline | tail -20
d7a05dfc Add Hesperia-mapped software engineering tutorial plan
eea358ac Merge pull request #5 from Atomic-Commits-Team/v0.2
047f19d9 Release notes for Hesperia v0.2
18624acc Add unit tests for guards: sigma_guard, gamma_guard, and theta_guard
c0a91c3a Create Hesperia v0.2 Release Invoker script
13dc9358 Initialize guards module
496e67a5 Add comprehensive documentation for v0.2 release
217e8a74 Merge pull request #2 from .../codex/add-new-guard-layer-features-and-documentation
e9224bfe Add ΣΓΘ guard layer spec and issue-001 closure docs
7481e435 Add files via upload
50b29338 3
11de49e2 Add Codex context assessment (2026-02-18)
8162bf7a Add MIT license and concepts doc
fdba4e73 Add governance (waterline, tasks, schema), project/, scripts/ — full Hesperia team and today's work
9a3b770f Replace with CLIENTS/hesperia from cursor repo (canonical source)
176a556b 3
7f41a931 3
a05a0823 123
72bf6ece first commit
26f33c97 Initial commit
```

```
$ git log hesperia-v0.2-20260220..hesperia-v0.3.0 --oneline   # (28 commits, abridged)
ffc5371c Full overwrite from cursor brain: present state (no books). Specs, sphere_rag
          (shadow_layer v1.0), docs, releases v0.2.1.
351178c6 consolidation (Gena): canonical refs, workspace, DOC_INDEX, fix double extension
e4233167 API: /hesperia/analyze, /health, /privacy; minimal JSON response; logging;
          CORS/OPTIONS; deploy + systemd
cbbadcc5 Wire Sigma/Gamma/Theta guards into runtime flow
7c781d50 0.2.0.1 wired up
9e869989 Reorganize root Python guards into scripts package
```

## What this era actually is

The first eight or so commits (`26f33c97 Initial commit` through `a05a0823 123`, `7f41a931 3`,
`176a556b 3`) are placeholder/scaffold commits with no architectural content — a repository being
stood up, not a system being designed. The first commit of real consequence is
`9a3b770f Replace with CLIENTS/hesperia from cursor repo (canonical source)`, which establishes the
pattern (still visible in `docs/DOC_INDEX.md` today) of an external "brain"/"cursor" repo as the
authoring source, with this repo as the canonical landing point — i.e., from the very first
substantive commit, Hesperia was designed as a *consumer* of formalized specs written elsewhere,
not as a place where architecture is improvised in code first.

`fdba4e73 Add governance (waterline, tasks, schema), project/, scripts/` introduces governance
machinery before any pipeline code exists — a deliberate "process before product" ordering that
recurs throughout the repo's history (the guard spec precedes the guard wiring by only two commits;
the metric-registry spec, era 6, precedes its implementation by exactly the same pattern).

`e9224bfe Add ΣΓΘ guard layer spec and issue-001 closure docs` is the load-bearing commit of this
era — the first time the repo states an architectural invariant (three-part guard discipline)
rather than just accumulating documentation. `cbbadcc5 Wire Sigma/Gamma/Theta guards into runtime
flow`, four commits later, is the first time that invariant is connected to actual execution.

`e4233167 API: /hesperia/analyze, /health, /privacy` is the first appearance of `/analyze` as a
named endpoint — the same endpoint whose contract gets frozen several eras later in
`docs/ENGINE-ANALYZE-CONTRACT.md`.

## Why this ordering was the minimal right move

Building the guard *spec* before the guard *wiring*, and building governance scaffolding before
pipeline code, means the very first lines of architectural reasoning in the repo establish "we
check before we trust" as a precedent — a precedent every subsequent era inherits without having to
re-argue it. A system that had instead built the pipeline first and bolted on validation later would
have had to retrofit Sigma/Gamma/Theta-equivalent checks onto code that was never designed with
checkable boundaries in mind — a substantially harder and less complete retrofit, as evidenced by
how cleanly later layers (fpf_bridge) were able to treat guard verdicts as pre-evaluated closures
rather than needing to re-derive them.

See [`corners/guards.md`](../corners/guards.md) and [`corners/logic_guards.md`](../corners/logic_guards.md)
for the guard triad's internal reasoning.
