# Era 8: fpf_bridge v7.2–v7.4 — evidence expansion, agentic interface, corpus scale-up prep (2026-07-04)

## Evidence

```
$ git log --oneline 9e22af32..HEAD
3b283a1e docs: repo-wide consistency pass for fpf_bridge v7.2-v7.4 + new AGENTS.md
707737b9 feat: fpf_bridge v7.2/v7.3/v7.4 specs + agentic Cursor interface + COBALT scale-up prep
df96723c sync: fpf_bridge Layer 11 baseline (v7.0 + this session's v7.2 Phase 1-4/v7.3 code)
6596c6cf sync: METRIC wave v0.7.0 (anchor_map/GCS registry, 24_SPEC, ISO doc index)
```

`9e22af32` (2026-07-01, "ISO-grade LTS documentation program") was the last real commit before this
era — three days with no commits, despite `sphere/fpf_bridge/` (Era 7's entire deliverable) and the
whole v0.7.0 metric wave sitting finished, tested, and documented in the working tree the entire
time. The first two commits of this era (`6596c6cf`, `df96723c`) are that backlog finally landing —
not new work, just work that had never been checked in. `707737b9` is this era's actual new code;
`3b283a1e`, `eec627ac`, `b811319b` are this era's documentation and ISO-traceability passes.

**The "sealed core stays untouched" claim, checked rather than asserted:**

```
$ git diff --stat 9e22af32..HEAD -- core/
(empty)
```

Every corner doc in this program says Layer 11 and its extensions are read-only against the sealed
pipeline. This era is the first place that claim is checkable against this specific era's own diff,
not just against the bridge's own read-only file list (`corners/fpf_bridge.md`) or a unit test
(`tests/test_fpf_bridge.py::TestBridge::test_read_only`, which proves one pipeline result dict isn't
mutated at runtime, a different and narrower guarantee than "no commit in this era touched `core/`
at all"). Both checks agree; recording both closes the gap between "the design says core is
untouched" and "core was, in fact, not touched this era."

## What this era actually is

Era 7 gave Hesperia a bridge that exposes 7 signal types to an LLM (5 rule types, raw area
activations, one stability score) out of roughly 239 L1–L9 variables + 41 KME metrics + 3 TRIZ
export families the pipeline already computes, consumed only by Hesperia's own internal,
single-shot, server-side LLM call. This era asked, directly, whether that bridge "flies for agentic
use" — and the honest answer was no, not as originally described: the evidence surface was narrow,
and nothing let an *external* agentic LLM (Cursor, or any tool-using caller) receive the bridge
state and reason over it. Three specs answer the two different gaps that finding produced:

- **v7.2** (`fpf_bridge_v7_2_evidence_expansion.md`) — the full inventory, marking every variable
  CANDIDATE/UNFIT with a reason, then Phase 1–4 code: contradiction evidence (using the native
  `contradicts` field, previously unused anywhere in this bridge), the L7 trust trio, L4 evidence
  support, KME's 6 primitives, TRIZ's Policy Contradiction Detector. **This spec corrected itself
  mid-build, twice**: KME and TRIZ were first drafted as TFP-/COBALT-scoped by default; both are
  general-purpose Hesperia mechanisms (KME per `corners/kme.md`, never scoped to a domain; TRIZ per
  `corners/triz_extension.md`, works over any `ActiveGraph`) that happened to be validated first
  against TFP/COBALT content. Fixed by registering real bounded contexts (`ContextPrimitive`,
  FPF `A.1.1`) instead of a synthetic new field, and defaulting evidence to the shared core context.
- **v7.3** (`fpf_bridge_v7_3_agentic_cursor_interface.md`) — `runtime/agentic_bridge/`, a new
  top-level package: `get_hesperia_bridge_state` (read-only, proven by test never to call an LLM
  API) and `attempt_hesperia_transition` (validation only). **A second correction, found by reading
  the installed `fpf-thinking-map` package's own source rather than trusting the spec draft**: the
  original design assumed a gate could return a hard `GateDecision.BLOCK`; `GateCheck.evaluate()`'s
  actual logic only ever returns `PASS`/`DEGRADE`/`ABSTAIN`. The real, tested outcome space
  (`ABSTAIN` for missing evidence or wrong state, `COLLECT_EVIDENCE` for an evidence gap) is what
  shipped; `BLOCK` stays correctly wired downstream in `attempt_transition()` for if a future gate
  implementation ever produces it, but nothing claims it works today that doesn't.
- **v7.4** (`fpf_bridge_v7_4_cobalt_corpus_scaleup.md`) — names, using COBALT's own exit-audit
  numbers rather than a vague "needs more data," exactly how far pilot is from production: 25
  documents attributed and 10 queries evaluated against a 1,286,742-chunk corpus. Ships a
  conservative `branch` (tfp/cobalt) classifier seeded from the G3 pilot's own proven query terms,
  and a reusable eval harness generalizing G3's 10 queries to whatever scale is actually run —
  neither executed against the real corpus, both synthetic-tested.

## Why this ordering was the minimal right move

Every addition in this era follows the same two-part discipline every prior era in this file
established: spec before code (Ethan ratification pending on all three, same as the deep-learning-
gaps spec two eras ago), and every new capability gated behind its own env flag defaulting off
(`HESPERIA_FPF_EVIDENCE_EXPANSION`, `HESPERIA_FPF_CONTRADICTION_GATE`, `HESPERIA_FPF_KME_EVIDENCE`,
`HESPERIA_MCP_BRIDGE_ENABLED`, `HESPERIA_MCP_BRIDGE_ACT_ENABLED`) so nothing here changes production
behavior until someone deliberately turns it on. The scope boundary drawn explicitly this
time — code that's dev-only/synthetic-input/no-other-owner-required is built now; anything needing
Ethan's ratification, Sophia's security review, Abelard's OCR/corpus-scale infra work, Colombo's
TFP-literature/eval judgment, or Olga's own MCP deployment stays an open, tracked row rather than
something quietly assumed or skipped — is the same "argue, don't silently comply or silently skip"
discipline this repo's own governance expects, just written down as a boundary because three specs
and five different owners' worth of open work made it worth being explicit about.

The two corrections (KME/TRIZ scoping, `GateDecision.BLOCK`) are recorded here rather than quietly
fixed and forgotten because `provenance.md`'s own rule — a name earns "implemented" status only if
`grep` finds it running — applies exactly as much to this era's own draft claims as to any external
framework's. Getting caught being wrong about your own code twice in one era and writing both down
is more consistent with this repo's stated discipline than getting it right the first time would
have been performative.

See [`corners/fpf_bridge.md`](../corners/fpf_bridge.md) (extension pointer added this era),
[`provenance.md`](../provenance.md) (FPF anchors verified this era, `GateDecision.BLOCK` finding),
[`../../AGENTS.md`](../../AGENTS.md) (new this era — records the KME/TRIZ correction as a rule to
not relearn), [`00_INDEX.md`](../00_INDEX.md)'s "Roof, continued" section.
