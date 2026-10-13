# Corner: Corpus — what exists, what's done to it, what never ships

**Location:** `research/clinical_tfp/` (13 modules), `research/tfp4_corpus_gap_manifest.json`,
`assets/lexicon/frozen/v06/`, `assets/lexicon/curated/`, `assets/calibration/`, `openai_calibrate_*.py`.
Not a "corner" in the architectural sense of the others — this is an audit of how raw material
enters the system, since the user-facing question ("how is this wired to corpus, what do we do to
it") cuts across several corners rather than living in one module.

## What corpus actually is, here

There is no large generic training corpus inside this repo. What exists is narrow and specific:
TFP (Transference-Focused Psychotherapy) session-shaped text, used for two purposes only —
**calibration** (deriving/validating thresholds, `corners/calibration.md`) and **research feature
development** (`research/clinical_tfp/`: stage detection, transference detection, affect-defense
coupling, object-representation tracking, interaction-loop detection, confidence scoring). The
corpus is not a passive bag of training examples; it is the labeled ground truth a threshold or a
feature extractor is checked against before being frozen into canon.

## What is actually done to it

1. **Gap analysis before use.** `research/tfp4_corpus_gap_manifest.json` exists specifically to
   track where corpus coverage is thin *before* a feature or threshold is built on top of it — the
   same "don't build on an unvalidated foundation" discipline as `corners/calibration.md`'s "tune
   after validation on 20–50 TFP transcripts" rule, made into an explicit, checked artifact rather
   than tribal knowledge.
2. **Feature extraction, never blind pattern mining.** Each `research/clinical_tfp/*.py` module
   targets one named, theory-grounded clinical construct (stage, transference, affect-defense
   coupling, object representation) rather than running an undirected statistical scan over the
   corpus — consistent with the founding memo's TF-IDF/PMI-as-deterministic-baseline stance
   (`references.md`): salience and association are computed from fixed, explicit rules over the
   corpus, not learned end-to-end from it.
3. **Freezing what gets used at runtime.** Whatever the corpus validates (a threshold, a dictionary
   entry, a calibration profile) is pinned by name into `VERSION.yaml`
   (`active_calibration_dict_pack`) and `assets/lexicon/frozen/v06/` — the corpus itself never ships, only
   the frozen, versioned conclusions drawn from it.

## What never ships

`release/v0.6.0/RELEASE_SCOPE.md` and `release/v0.7.0/RELEASE_SCOPE.md` both state it as a release
gate, not a guideline: "Do not ship corpus payloads" / "Exclude corpus session payload trees." This
is the same public/prod separation documented in `corners/release_governance.md`, applied
specifically to the clinical material rather than to code: a sealed, externally-shippable Hesperia
build must be provably separable from the proprietary/sensitive corpus that validated it.
`hesperia-0.6.3`'s fully data-free runnable archive is the existence proof that this separation is
real, not aspirational.

## Relationship to neighboring corners

- Feeds `corners/calibration.md` (thresholds/profiles validated against corpus), the lexicon
  resolver (`corners/lexicon_resolver.md`, frozen dictionary entries derived from corpus-informed
  calibration), and `corners/kme.md` indirectly (clinical interpretation of KME fingerprints is a
  downstream-consumer concern, not something KME computes itself — see `corners/kme.md`'s TFP
  grounding note).
- Bounded by `corners/release_governance.md`'s public/prod split, which is the enforcement
  mechanism for "corpus never ships."
