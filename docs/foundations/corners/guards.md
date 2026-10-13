# Corner: Guards — Sigma / Gamma / Theta in focused detail

**Location:** `sphere/guards/` (sigma_validator.py, gamma_validator.py, theta_governance.py,
guard_runtime.py), `core/guards/` (determinism.py, invariants.py), declarative specs
`specs/canon/sigma_invariants.yaml`, `specs/canon/gamma_invariants.yaml`,
`specs/canon/theta_governance_rules.yaml`.

**Born:** `e9224bfe` (2026-02-20), "Add ΣΓΘ guard layer spec and issue-001 closure docs" — the
oldest non-trivial structural commit in the repository, wired into runtime two commits later
(`cbbadcc5 Wire Sigma/Gamma/Theta guards into runtime flow`).

## Why this is a distinct concern

A deterministic pipeline can still be *wrong* deterministically — the same bug reproduces the same
bad output every time. Determinism alone does not guarantee structural validity. Three genuinely
different questions need three genuinely different checks, because they fail at different times:

- **Sigma (static)** — is the *shape* right, checked before deeper execution continues? Per
  `sigma_invariants.yaml`'s header: "structural bounds, shape, mapping integrity." Concretely: is
  `area_vector` length 12 (`SIGMA_001`)? Is `family_counts` length 288 (`SIGMA_002` — 12 areas × 24
  families)? Is the adjacency matrix 12×12 and symmetric (`SIGMA_003`/`SIGMA_004`)? These are
  single-snapshot checks with no notion of "before" or "after."
- **Gamma (dynamic)** — was the *execution* well-formed across the run? Per
  `gamma_invariants.yaml`: "runtime order, isolation, consistency." Concretely: did layers execute
  in canonical order (`GAMMA_001`)? Was there no illegal mutation of upstream artifacts
  (`GAMMA_002`, `GAMMA_003`, `GAMMA_006`)? Is the deterministic flag actually true (`GAMMA_008`)?
  These require comparing states across the run, not one snapshot.
- **Theta (governance)** — is the *final result* eligible to be called canonical output at all? Per
  `theta_governance_rules.yaml`: "canonical output eligibility... no free-form eval." Sigma and
  Gamma must both have passed (`THETA_001`); no raw artifact mutation detected (`THETA_002`); all
  four required artifacts present — USF, raw_metrics, logic_outputs, provenance (`THETA_003`); a
  placeholder Layer-10 cannot upgrade output to canonical narrative truth (`THETA_004`).

`sphere/guards/guard_runtime.py`'s own docstring states the orchestration discipline: "Orchestration
only; no policy logic here." All judgment lives in the three declarative YAML specs; the runner
just sequences Sigma → Gamma → Theta and combines results.

## What would break without it

Without Sigma, a malformed area vector (wrong length, a NaN) could silently propagate through the
entire L1–L10 stack and produce a confident-looking but structurally meaningless narrative.
Without Gamma, a layer could read data a later layer wrote, or upstream raw metrics could be
mutated in place — bugs that are deterministic (same input → same wrong output) and therefore
invisible to a pure determinism check. Without Theta, there would be no single, final point where
the system can refuse to call a result canonical despite everything upstream looking fine — every
downstream consumer would have to re-derive eligibility itself, inconsistently.

## Exhaustive invariant enumeration

This document stays at the level of "what kind of question does each guard answer."
For the full invariant-by-invariant enumeration — every Sigma/Gamma/Theta ID, its
actually-implemented check (not just its YAML name), severity, and scientific/formal
lineage (Hoare preconditions, Design by Contract, symmetric-matrix definitions, Markov
transition-counting identities) — see
[`layers/GUARDS_sigma_gamma_theta.md`](../layers/GUARDS_sigma_gamma_theta.md). That
document also flags which Gamma checks are honestly default-permissive (pass when
supporting runtime metadata is simply absent, e.g. `GAMMA_002`/`GAMMA_003`) rather than
independently verified, and a `layer_9` naming collision between the YAML logic-rule
engine and `core/layers/layer_9.py`.

## How it relates to neighbors

The guard triad is the most-referenced foundation in the codebase. The fpf_bridge spec (Layer 11,
built six eras later) wraps `guards.sigma.passed` / `guards.gamma.passed` /
`guards.theta.approved`/`.warnings` as **pre-evaluated Guard closures** — "Guards are pre-evaluated
— closures over sphere results, not re-computation" — only possible because Sigma/Gamma/Theta were
designed from day one as boolean-plus-detail verdicts cheap enough to carry forward rather than
recomputed. `core/guards/determinism.py` supplies the lower-level check Gamma's `GAMMA_008`
consumes. `core/propagation/gamma_guard.py` and `invariant_enforcer.py` extend the Gamma discipline
into the propagation layer itself. See `corners/logic_guards.md` for how the guard triad sits
alongside Layer-9 rules and Prolog inference as one combined governance surface, and
`corners/prolog_logic.md` for the symbolic-inference sub-layer specifically.
