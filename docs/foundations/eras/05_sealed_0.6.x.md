# Era 5: 0.6.0 Sealed Mainline and the Dev/Prod Split (2026-05-18 → 2026-06-14)

## Evidence

```
$ git log v0.5.8..0.6.0 --oneline | wc -l
76

$ git log v0.5.8..0.6.0 --oneline   (prod-sanitization sequence, abridged)
ff55ef46 draw-line(2026-05-18): rollback marker — README + ROLLBACK-LINE doc
3b31604f chore(prod): remove docs/ (documentation on igareosh/hesperia)
dedc2987 chore(prod): remove governance/ narrative
326c6969 chore(prod): remove research/ (reference corpus on igareosh/hesperia)
830e79e1 chore(prod): remove specs narrative markdown
d3260f91 ci(prod): prod-code-only workflow and verifier script
fa6f01eb fix(prod): restore specs yaml/json config; strip specs markdown only
          (corpus untouched)
276ea704 ci(prod): verifier corpus-safe — dev md/specs prose only
12f931a7 ci(prod): corpus-safe verifier (specs yaml allowed)
8cfb4841 chore(prod): immaculate sweep — dev notes removed (backup on igareosh/hesperia)
56f5ac82 draw-line(2026-05-18): dev-ready — immaculate prod, docs on igareosh/hesperia
18178deb ci(prod): allow DEV-READY-LINE marker on immaculate tree
41e05136 chore(v0.6.0): Python compliance pass — version bump, API cleanup
e196fce0 fix: validate prod tree from shipping context
257d81ee fix: align release version authority with v0.6.0
fa923eee release: add sealed v0.6.0 baseline package
fc7c5cf7 build: add checked docker bundle for v0.6.0
c9e95570 release: add 0.6.0 agentic install contract
87f5a5b6 release: sanitize 0.6.0 public release artifacts

$ git log 0.6.0..0.6.3 --oneline   (23 commits)
f87b2bb1 HES-61-01: Python /analyze engine_result contract envelope.
6df2695e fix(tfp): restore tfp_v1/nlp skeleton dir for layout gate (TFP-DATA-T15)
16286faa Ethan: seal Hesperia 0.6.3 GitHub archive — E2E without prod dicts/corpus.
9bf0289d Ethan: 0.6.3 archive example outputs (envelope, Teacher, IRC trace, analyze).
cc94b09d Default OpenAI model gpt-4o-mini (env-driven, not gpt-5.2).
```

## What this era actually is

The defining act of this era is repeated, deliberate subtraction, not addition: more than a dozen
`chore(prod): remove ...` commits strip docs, governance narrative, research corpus, and specs
prose from a "prod" line while the corresponding `ci(prod): ...` commits build a verifier that
distinguishes *narrative* markdown (removable) from *load-bearing* config (specs YAML/JSON,
explicitly "allowed" / "untouched" / "restored" across several commits — `fa6f01eb`, `12f931a7`,
`276ea704`). This back-and-forth (strip, then explicitly restore specs config, then tighten the
verifier again) shows the team iterating toward the correct boundary rather than getting it right
in one pass — direct evidence that drawing the dev/prod line was harder than it looks and required
several corrective commits to avoid accidentally stripping invariant-bearing files alongside
narrative ones.

`ff55ef46` (rollback marker) and `56f5ac82` (dev-ready marker) are paired "draw-line" tags —
`hesperia/rollback-line-20260518` and `hesperia/dev-ready-line-20260518` — establishing two
named, addressable checkpoints rather than relying on commit hashes alone, which is what
`DEV-READY-LINE-2026-05-18.md` and `docs/DOC_INDEX.md`'s "Prod (this)" table still point to
verbatim.

0.6.3's "seal... E2E without prod dicts/corpus" (`16286faa`) extends the same sanitization
discipline one step further: even the public GitHub archive is sealed *without* the proprietary
dictionaries and corpus, the clearest evidence that "sealed" in this repo always means "sealed
minus whatever should not travel with this particular distribution," not "sealed = everything."

## Why this ordering was the minimal right move

Stripping narrative content from "prod" while iteratively correcting which config files
accidentally got caught in the sweep is the necessary cost of getting a *meaningful* seal — a seal
that changes hash every time someone edits a research note is not a useful seal at all, but a seal
that accidentally strips a specs YAML invariant is actively dangerous (it would seal a tree that
silently behaves differently from the dev tree it was supposed to mirror). The repeated
correction commits are not churn; they are the seal boundary being earned through verification,
which is the same "verify before trusting" discipline as the guard triad, applied here to the
release process itself rather than to pipeline data.

See [`corners/release_governance.md`](../corners/release_governance.md).
