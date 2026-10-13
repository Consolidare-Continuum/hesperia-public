# Hesperia — agent guide

**Start here, then go deep**: [docs/foundations/00_INDEX.md](docs/foundations/00_INDEX.md) is the
canonical narrative — a top-down trace from the current working tree ("the roof") down to why the
system exists at all ("bedrock"). For agentic work, pair it with
[docs/foundations/agentic_orientation.md](docs/foundations/agentic_orientation.md): that file is
the five-pass cold-start protocol for names, branch scope, math posture, and execution discipline.
Everything below is a map to help you find the right door, not a replacement for those two docs.

## What this is, in one sentence

Hesperia converts language into bounded, falsifiable, replayable structure, and only then lets an
LLM speak. Every mechanism in this repo either makes that conversion deterministic, or proves,
after the fact, that determinism wasn't violated.

## Where things live

Root itself is a closed, formalized set — 15 real directories + 1 symlink, why each one is
top-level rather than nested, and the process for adding a 16th: [REPO_STRUCTURE_POLICY.md](REPO_STRUCTURE_POLICY.md).

| Need | Look in |
|---|---|
| The sealed measurement pipeline (L1–L9) | `core/layers/`, `sphere/pipeline/` |
| Topology, geometry, hex substrate | `core/topology/`, `core/hexmap/`, `sphere/topology/` |
| Guards (Sigma/Gamma/Theta) | `core/guards/`, `sphere/guards/` |
| Layer 11 — the LLM reasoning bridge | `sphere/fpf_bridge/` (state graph, evidence, gates, logic) |
| Agent-facing tools built on top of the bridge | `runtime/agentic_bridge/` (read-only + validation, both flag-gated off by default) |
| Library RAG (COBALT, CHROMA-2) | `runtime/cobalt/` |
| Knowledge Metrics Engine (KME) | `hesperia/engine/kme/` |
| TRIZ contradiction/innovation analytics | `hesperia/extensions/triz/` |
| Ratified & draft specs | `assets/specs/canon/*.md` (status line at the top of each tells you if it's ratified or pending) |
| Deep engineering reasoning, per-layer math, provenance audits | `docs/foundations/` |

## Branch model — know which one you're in

**Core** (this repo's sealed engine) is shared, long-lived, domain-agnostic. **TFP** and **COBALT**
are branches/applications on top of it — real but scoped. **MRT** is closed (different grid,
finished MVP) — don't reopen it without a fresh spec. See
`docs/brain-export/colombo/HESPERIA-MODULAR-BRANCH-ARCHITECTURE.md` for the full model.

**A mechanism being usable by TFP or COBALT does not make it TFP- or COBALT-exclusive.** KME and
TRIZ are both general-purpose core semantics that happen to have been validated first on TFP
content — this got mislabeled once already (fixed in the fpf_bridge v7.2 evidence-expansion work);
don't reintroduce the same mistake for the next mechanism you touch.

## Five-pass cold start

Before broad code/spec/doc work, run this order:

1. **Surface pass** — `AGENTS.md`, `docs/README.md`, `docs/foundations/00_INDEX.md`
2. **Branch pass** — name whether you are in core, TFP, COBALT, MRT, or research
3. **Name pass** — disambiguate terms like KME/KSI, bridge/agentic bridge, Sigma/Gamma/Theta
4. **Math pass** — verify implemented math vs. spec-only math in `docs/foundations/provenance.md`
   and `docs/foundations/parameter_catalog.md`
5. **Execution pass** — tests, flags, and explicit remote choice before claiming "implemented"

The compact explanation for each pass lives in
`docs/foundations/agentic_orientation.md`.

## Named-owner map

Use the right owner context for the work in front of you:

| Context | Best fit |
|---|---|
| **Felix** | Python/TS/scripts, Hesperia runtime, bridge, tests, product implementation |
| **Gena** | Java/API-heavy work and adjacent runtime/product implementation when assigned |
| **Abelard** | Deploy, services, remotes, SSH, environment flags on real hosts, backups |
| **Colombo** | Theory, formalization, branch boundaries, scientific wording, naming discipline |
| **Chiron** (Accepted 2026-08-17) | One-man-army of Hesperia's existing operability/quality first; standing authority over Hesperia performance: params↔math↔corpus calibration and core consolidation, enable/disable of documented params (`assets/calibration/*.yaml`, `core/math/core_math.py` `DEFAULT_CONFIG`), corpus structure, thinking-map-gated moves through `runtime/agentic_bridge/`, CHROMA-2 theory grounding routed via Colombo. Required output: recipes (`docs/recipes/`) and feature-theorizing notes. Full brain-repo/MCP awareness when a task needs it (not Hesperia-only), `query_knowledge` first. Not sealed-core-source dev (→ Felix/Gena), not formalization (→ Colombo), not infra (→ Abelard). Scope: `governance/SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md` in the brain repo (`prichindel.com`). |
| **Aurel / external Codex stabilizer** | Repo-wide awareness cleanup, anti-drift passes, agentic cold-start guidance |

If the task crosses those boundaries, say so explicitly instead of quietly blending roles.

**Dev/train boundary**: Felix/Gena (dev) and Chiron (train) share one zone — `assets/calibration/*.yaml`, `core/math/core_math.py`'s `DEFAULT_CONFIG`, `hesperia/corpus/`, `docs/foundations/parameter_catalog.md` et al. Before non-trivial work there, check/set the mode marker (`governance/hesperia_work_mode.txt` in the brain repo, via `scripts/hesperia/hesperia-work-mode.sh`) — don't silently interleave a refactor with a live calibration session or vice versa. Full protocol: `governance/SPEC-ETHAN-HESPERIA-DEV-TRAIN-BOUNDARY.md` in the brain repo. Everything outside that zone (sealed `core/layers/`, `sphere/pipeline/`, `core/guards/`) is Felix/Gena's, always, no mode needed.

## The discipline this repo enforces on itself

- **A name earns "implemented" status only if `grep` finds it running.** See `docs/foundations/provenance.md`
  before citing anything as fact — a spec-only claim is real (worth recording) but is not the same
  as running code.
- **Names are commitments, not decoration.** "Used first in TFP" does not mean "TFP-only"; KME and
  TRIZ are core semantics unless a spec explicitly scopes a specific use of them more narrowly.
- **New capability ships flag-gated off by default**, proven safe against synthetic input first,
  flipped on only after the specific review it needs (security, corpus-scale, clinical judgment —
  whichever applies) passes. `HESPERIA_FGR_FREEZE`, `HESPERIA_COBALT_ENABLED`,
  `HESPERIA_FPF_EVIDENCE_EXPANSION`, `HESPERIA_MCP_BRIDGE_ENABLED` are all instances of this same
  pattern — follow it for the next one, don't invent a new convention.
- **Math language must stay honest.** Use the name of the math actually implemented in the repo
  ("Markov-like", Shannon entropy, bounded primitives, explicit YAML weights) rather than upgrading
  it to a grander framework by analogy.
- **`sphere/fpf_bridge/` and `runtime/agentic_bridge/` are read-only against the sealed pipeline.**
  Neither may write back into `core/` or `sphere/pipeline/` — that's what keeps a second analytical
  layer from becoming a second source of truth. Same rule for TRIZ against KME's active graph.
- **Run the tests before claiming something works.** `pytest tests/test_fpf_bridge.py
  tests/test_agentic_bridge_*.py tests/cobalt/` covers everything under `sphere/fpf_bridge/` and
  `runtime/agentic_bridge/`. Prefer an end-to-end smoke test over a unit-level check alone — this
  repo's own history includes a case where a unit-level check passed while a second call site
  (`binding_builder.py`) silently dropped new evidence from ever reaching the LLM prompt.

## Remotes — do not guess which one to push to

**Amended 2026-07-26:** `Atomic-Commits-Team/hesperia` is **abandoned/permanently disconnected**
— copyright assigned to Consolidare Continuum S.R.L. (dual-MSign deed). Never push there again.
`origin` was retargeted the same day: it now points at `igareosh/hesperia` too, so **dev and prod
are the same repo** — there is no longer a separate promotion remote.

| Remote | Points to | Use for |
|---|---|---|
| `dev` | `igareosh/hesperia` | Day-to-day dev work, unsealed/in-progress material — default target |
| `origin` | `igareosh/hesperia` (same repo as `dev`; was `Atomic-Commits-Team/hesperia`, abandoned) | Prod runtime pulls from here on prichindel |
| `backup` | `igareosh/hesperia-dev-backup` | Backup line |

Local `main` tracks `origin`, which is now the same repo as `dev` — push either name, they land
on `igareosh/hesperia`. There is no separate "prod promotion" step anymore; a seal/version bump
is still a deliberate, explicit act (see below), it just isn't gated by pushing to a different repo.

## Sealing vs. committing — they are not the same thing

`VERSION.yaml`'s `system_version` only moves when something is formally sealed (release-gate
discipline, `corners/release_governance.md`). Plenty of real, tested, committed code in this repo
predates its own commit (see git log around 2026-07-04 — the entire fpf_bridge module and the
v0.7.0 metric wave sat uncommitted for days despite being documented as implemented) — commit early
and often regardless of seal status; don't wait for a seal ceremony to check work in.
