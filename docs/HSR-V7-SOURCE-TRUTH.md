# HSR-V7 source truth

This file is the current authority map for live Hesperia code, specs, and documentation after the
core-fusion and import-convergence passes. It separates canonical implementation authority from
compatibility surfaces and historical material.

## Canonical implementation authority

`core/` is the canonical home for deterministic structural computation.

- `core.domain` owns shared KME/domain measurement implementation.
- `core.runtime` owns generic runtime module implementation.
- `hesperia.engine.kme` remains a narrowed compatibility package surface.
- former shim leaves under `hesperia.engine.kme` were removed where no longer required by live code or tests.
- former shim surfaces `hesperia.modules.core`, `hesperia.modules.metrics.base`, and
  `hesperia.modules.topology.core` were removed after convergence to canonical `core.runtime.*`.
- `hesperia.modules.tfp` remains a domain extension.

## Live source code

- `core/`
- `hesperia/`
- `runtime/`
- `sphere/`

## Live specs

- `docs/specs/HSR-V7-*`
- `docs/specs/HESPERIA-CORE-MODULES-AND-BRANCHES.md`
- `specs/canon/*`
- `schemas/*`

## Live documentation authority

- `docs/HSR-V7-SOURCE-TRUTH.md`
- `docs/HSR-V7-CONSOLIDATION-REPORT.md`
- `docs/iso/*`
- `docs/foundations/*`
- `docs/publication/*`

When a non-archive document discusses KME or runtime architecture, it should describe canonical
ownership using `core.domain` and `core.runtime`, and describe old `hesperia.engine.kme` /
`hesperia.modules.*` paths only as compatibility history or protected legacy surfaces.

## Historical evidence

- `release/v0.5.*`
- `release/v0.6.*`
- `docs/archive/*`
- `docs/brain-export/*`

`docs/brain-export/*` is useful evidence and research context, but it is not current implementation
authority unless a live source-truth document explicitly points to a file there for historical
background.

## Not source truth

- generated debug outputs
- stale historical docs without current-authority wording
- compatibility shims treated as implementation authority
