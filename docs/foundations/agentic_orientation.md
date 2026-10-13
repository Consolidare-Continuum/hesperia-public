# Agentic orientation — five-pass cold start, names, and math discipline

This file is the shortest safe path for an agent that needs to do real work in Hesperia without
relearning the same branch, naming, and math mistakes from scratch. Read it before touching code,
specs, or product-facing docs if your task is broader than one local bug.

## 1. Five-pass cold start

### Pass 1 — surface and contract

Read `AGENTS.md`, `docs/README.md`, and `docs/foundations/00_INDEX.md` first. They establish the
repo's direction of truth:

- `AGENTS.md` tells you how to behave in this repo.
- `docs/README.md` tells you which documentation tier owns which kind of claim.
- `00_INDEX.md` tells you what the system is trying to do and why each layer exists.

Do not start from a random spec and assume you now understand the repo.

### Pass 2 — branch and scope

Before you reason about a mechanism, say which branch/scope you are in:

- **Core** = sealed measurement engine, shared and domain-agnostic.
- **TFP** = clinical branch on top of core.
- **COBALT** = library/attribution branch on top of core.
- **MRT** = closed branch on a different grid; not to be silently reopened.

If you cannot name the branch, you are not ready to claim behavior. A capability being useful to
TFP or COBALT does **not** make it branch-exclusive.

### Pass 3 — names

Treat names here as commitments, not decoration:

- **`sphere/fpf_bridge/`** = Layer 11, a read-only projection of deterministic output into bounded
  LLM-facing state.
- **`runtime/agentic_bridge/`** = external-agent wrapper around that bridge; not new physics, not a
  second source of truth.
- **KME** = Knowledge Metrics Engine.
- **KSI** is ambiguous unless qualified:
  `KME-KSI-score` is a derived metric; `KSI-Inspector` is a tool/research label.
- **Sigma / Gamma / Theta** are Hesperia's own guard names, not imported FPF terms.

When a name is unclear, check `docs/foundations/provenance.md` before inventing a lineage.

### Pass 4 — math

Hesperia lets prose happen only after bounded measurement. The math posture is:

- Prefer implemented, bounded, replayable quantities over elegant speculation.
- Use `docs/foundations/parameter_catalog.md` for live constants and what they change in the output.
- Use `docs/foundations/provenance.md` to distinguish implemented math from spec-only math.
- Say **"Markov-like"**, not "Markov model," unless the repo actually fits or estimates one.
- Say **"Shannon entropy"**, not "Kolmogorov complexity," unless the repo truly implements the
  latter. Today it does not.
- Treat Minkowski/IPoW/GCS/BELL claims as scoped by their current implementation status, not by how
  prestigious the names sound.

### Pass 5 — execution

Only after the first four passes should an agent act. Minimum discipline:

- A thing is **implemented** only if code and tests can locate it.
- A thing is **specified** if a spec names it but code does not run it yet.
- Feature-flag state matters; "exists in tree" is not the same as "active in product."
- Use an end-to-end or integration proof when the change crosses the LLM boundary, not a unit test
  alone.
- Push deliberately: `dev` is day-to-day, `origin` is prod promotion.

## 2. Named-owner map for agentic work

These names matter because they reduce cross-role drift:

| Name | Use when | Do not use when |
|---|---|---|
| **Felix** | Python/TS/scripts, Hesperia runtime, bridge, tests, product-layer implementation | Infra, deploy, cluster administration |
| **Gena** | Java/API-heavy work, cross-service implementation, adjacent runtime/product design when assigned | Infra ownership, production operations |
| **Abelard** | Remotes, deploy, services, environment flags on real hosts, access, backups, SSH | Core product implementation or theory framing |
| **Colombo** | Formalization, branch boundaries, theory language, scientific writing, naming discipline | Shipping runtime code as if theory were implementation |
| **Aurel / external Codex stabilizer** | Repo-wide agent awareness, cold-start rules, context cleanup, anti-drift passes | Replacing branch owners or inventing a new authority line |

If a task crosses those boundaries, name the handoff explicitly instead of blending roles.

## 3. Anti-drift rules

Keep these short rules in working memory:

1. **Do not merge branch language into core language.** "Used first in TFP" is not the same as
   "belongs to TFP."
2. **Do not confuse read-only agentic layers with engine layers.**
   `runtime/agentic_bridge/` reasons over results; it does not certify results.
3. **Do not upscale a name into implementation.** BELL, IPoW, GCS, or a named Ethan spec may be
   real obligations while still being only partially built.
4. **Do not narrate raw dumps as if they were governed evidence.** The whole point of the bridge is
   bounded evidence, legal transitions, and auditable gates.
5. **Do not guess the remote.** `git push dev main` is ordinary development here; a bare `git push`
   risks prod.

## 3a. Aurel stabilization rules for productization language

When an agent uses buyer-language terms from the Upcelerator layer, apply this extra filter:

1. **Keep the date visible.** Upcelerator 2026 wording is a real repo truth layer, but it is
   time-bounded, not timeless doctrine.
2. **Preserve truth class.** Market framing, TAM/SAM/SOM, investor rhetoric, and open hypotheses
   are not one evidence type and must not be flattened into one.
3. **Route proof back to the engine docs.** `deterministic validation`, `accountable AI`, and
   `evidence-grade audit trace` are useful phrases only when tied back to `METHODS.md`,
   `VALIDATION_EVIDENCE.md`, and `/product/interpret`.
4. **Treat competition language as framing, not benchmark evidence.** `reactive paradigm`,
   `deterministic paradigm`, and `status quo competitor` help explain positioning; they do not
   replace comparative measurements.
5. **Do not promote commercial estimates into validation claims.** Market-size numbers, pilot
   pricing, and willingness-to-pay hypotheses belong to productization memory, not to technical
   proof.

## 4. Short route by task

| Need | Start here |
|---|---|
| Whole-system understanding | `docs/foundations/00_INDEX.md` |
| Name origin / "is this really implemented?" | `docs/foundations/provenance.md` |
| Constant / threshold / coefficient meaning | `docs/foundations/parameter_catalog.md` |
| Agent-facing bridge behavior | `specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md` |
| Branch model / core vs branch boundary | `AGENTS.md`, `docs/brain-export/colombo/HESPERIA-MODULAR-BRANCH-ARCHITECTURE.md` |
| Operator integration surface | `docs/iso/OPERATOR_GUIDE.md` |
| Buyer-facing "deterministic validation" / "accountable AI" wording | `docs/publication/UPCELERATOR_PRODUCTIZATION_QA.md` |
| Regulation-driven market / competitor framing | `docs/publication/UPCELERATOR_MARKET_AND_COMPETITION.md` |
| Truth class for any Upcelerator claim before you spread it | `docs/publication/UPCELERATOR_SOURCE_MAP.md` |

If you still cannot tell whether your claim belongs to core, TFP, COBALT, MRT, or research, stop
and resolve that first. Most Hesperia mistakes begin with naming the wrong layer.
