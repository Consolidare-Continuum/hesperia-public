# SPEC: fpf_bridge v7.4 — COBALT Full-Corpus Attribution & TFP Tagging (scale-up)

**Version:** v7.4 (extension)
**Status:** RATIFIED (Ethan) — 2026-07-19
**Date:** 2026-07-04 (draft) · **Ratified:** 2026-07-19
**Author:** Felix (Developer, Claude Code)
**Relates to:** `fpf_bridge_v7_2_evidence_expansion.md`, `fpf_bridge_v7_3_agentic_cursor_interface.md`
(both consume this spec's output as a hard prerequisite for real-data operation), and the ratified
`governance/SPEC-ETHAN-HESPERIA-COBALT-MODULE-BRANCH.md` / `COBALT-24` exit audit (brain repo), whose
own verdict already named this gap: *"Prod: `HESPERIA_COBALT_ENABLED=0` until operator scale-up
attribution."* This spec is that scale-up, made explicit and scoped to what v7.2/v7.3 specifically need.

**Naming note:** this is numbered v7.4, not v7.1 — `v7.1` already names
`fpf_bridge_v7_deep_learning_gaps.md` (attention/embeddings/reward, a different and still-deferred
extension). Keeping the numbers unique so "v7.1" always means one thing across this doc set.

**Scope:** COBALT + TFP only, same as v7.2/v7.3. No MRT.

---

## 0. What this closes

Every gate in the ratified COBALT spec (G1–G4) already passed — but every one of them passed **at
pilot scale**, and both the gate reports and the COBALT-24 exit audit say so explicitly, not as a
hidden caveat:

| Gate | What actually happened | Cited from |
|---|---|---|
| G1 (reindex) | CHROMA-2 heartbeat OK, **1,286,742 chunks total** — but ingest ran with `skip_ocr: True` | `ABELARD-COBALT-03-CHROMA2-G1-2026-06-29.md` |
| G2 (attribution) | `tools/cobalt_chroma2_attrib_batch.py` built and run — on **~25 documents**, not the corpus | `FELIX-COBALT-04-G2-ATTRIB-2026-06-29.md` |
| G3 (eval) | **10 queries** tested, 7/10 correct | `COLOMBO-COBALT-05-G3-EVAL-2026-06-29.md` |
| G4 (facets) | `theme=general` on the sampled bulk of the corpus; Hesperia fields present only on the G2 pilot subset | `NOAH-COBALT-06-G4-FACETS-2026-06-29.md` |

v7.2 (evidence expansion — specifically the L4 `evidence_support_baseline` and TRIZ Policy
Contradiction Detector, both COBALT-scoped) and v7.3 (the agentic Cursor interface Olga will actually
use, specifically its `HESPERIA_MCP_BRIDGE_REAL_DATA` flag) both silently assume a corpus that's
actually attributed at scale. Without this spec, both of those specs' "real data" phases would be
built on the same ~25-document pilot sample the G3 eval already ran against — meaning Olga's real
research questions would get COBALT retrieval quality no better than the pilot number (7/10, on
hand-picked queries, not her actual research questions). This spec is what makes v7.2/v7.3's real-data
flags mean what they claim to mean.

---

## 1. What "reindexed with the parameters we need for agentics" concretely means

Every chunk in CHROMA-2's `documents` collection needs, at minimum:

| Field | Status today (per G2/G4 reports) | Needed for |
|---|---|---|
| `concept_id`, `area_name`, `family_name` | Present on ~25-doc pilot subset only (`attribution_version=cobalt-g2-0.1`) | v7.2's L4 `evidence_support_baseline`, TRIZ contradiction detector — both need real coverage, not a 25-doc island |
| `attribution_version` | Present on pilot subset | Auditability — must be present corpus-wide so a future re-attribution pass can be distinguished from this one |
| **`branch` facet** (`tfp` / `cobalt` / `core`) | **Does not exist yet, anywhere** | v7.2 §3's `context_scope` tagging is meaningless for library evidence unless the chunk itself is tagged with which branch it actually belongs to — this is new work, not covered by G2's existing schema |
| OCR'd text (not `skip_ocr`) | **Explicitly skipped at ingest** (G1 report, gap #1) | Any scanned-PDF source in the corpus is currently either textless or garbled going into attribution — attribution run on ungarbled text only is not "full corpus attribution," it's "full corpus attribution minus every scanned source," silently |
| `theme` (Papra facet) | `general` on the sampled bulk | Not blocking for Hesperia-native fields, but flagged in G4 as still owed — cheap to fix in the same pass |

---

## 2. OCR gap — blocking, not cosmetic

G1's own report lists `skip_ocr: True` as gap #1, not a footnote. Running attribution (§3) before this
is resolved means the "full corpus" attribution pass would still silently exclude every scanned source
— exactly the kind of gap this whole documentation discipline (per `provenance.md`'s "verify, don't
assume" rule) exists to name rather than paper over. **Resolve or explicitly re-scope before G2
scale-up starts**: either re-run ingest with OCR enabled for the affected subset, or produce an
explicit, checked list of which documents remain textless and exclude them from claimed coverage
rather than silently attributing empty text.

---

## 3. Batch attribution at scale — reuse the existing tool, don't rebuild it

`tools/cobalt_chroma2_attrib_batch.py` already exists and already works — G2's pilot run proved the
mechanism (`concept_id`/`area_name`/`family_name` correctly written for the attributed subset). This is
purely a scale-up of an already-correct tool, run via its existing `--max-docs`/doc-manifest interface
across the full **1,286,742-chunk** corpus (batched, not a single monolithic job — same operational
caution as any job at that scale), plus the new `branch` facet from §1, computed per-document from the
same engine-trace attribution the tool already does (a document whose dominant concept lands in a
`TFP_*`-tagged family region → `branch=tfp`; otherwise `branch=cobalt` as the general-library default;
`branch=core` reserved for engine-internal reference material if any exists in the corpus, unlikely but
worth an explicit check rather than an assumption).

---

## 4. TFP tag pass — the specific gap named in this conversation

Beyond the generic `concept_id`/`area_name`/`family_name` attribution, this spec adds one targeted
pass: identify which documents in CHROMA-2 are genuinely TFP/clinical-psychoanalytic grounding
literature (Kernberg, transference-focused theory, etc. — the kind of source the G3 pilot queries
already surfaced correctly) versus general/unrelated material, and set `branch=tfp` explicitly rather
than leaving it to fall out only from family-region inference. The G3 pilot's own 10-query set (Kernberg
ТФП, countertransference, Meltzer, narcissistic transference TFP, etc.) is a ready-made seed for this —
extend it, don't discard it. **This tag is corpus-side metadata about the library, not clinical-session
data** — it never touches CHROMA-1 or any real session transcript; it only says which *library* sources
count as TFP-grounding literature.

---

## 5. Eval at scale

COBALT's own original formalization doc already specified the right target and this spec just holds
it as a real exit bar rather than an aspiration: **50–200 Q→doc pairs**, not 10. Use the G3 pilot's
10 as a seed, expand with Colombo's clinical judgment on which additional TFP/COBALT queries matter,
and re-run the same pass/fail discipline G3 already used (clinical/TFP hit vs. miss vs. acceptable
control-miss).

---

## 6. Owners (same shape as the original COBALT gate assignments)

| Item | Owner |
|---|---|
| OCR gap resolution or explicit textless-doc exclusion list (§2) | Abelard |
| Batch attribution scale-up + `branch` facet (§3) | Felix/Gena |
| TFP tag pass, seed-set expansion (§4) | Colombo |
| Eval at scale, 50–200 pairs (§5) | Colombo + Noah |
| Facet recheck post-scale-up (`theme`, Hesperia fields corpus-wide) | Noah |

---

## 7. Dependency this creates on v7.2 / v7.3

- **v7.2**: L4 `evidence_support_baseline` and the TRIZ Policy Contradiction Detector, both marked
  COBALT-scoped in v7.2 §1.4/§1.11, should not be treated as validated-at-scale until this spec's exit
  criteria pass — v7.2's own Phase 4 (TRIZ) should cite this spec as a precondition, not just a sibling.
- **v7.3**: `HESPERIA_MCP_BRIDGE_REAL_DATA=1` (v7.3 §6, Phase 4) must not flip on for COBALT-branch
  queries until this spec's §5 eval passes at the 50–200-pair scale — flipping it on against the
  25-document pilot subset would hand Olga retrieval quality indistinguishable from the pilot number,
  under the label "real data," which is the exact gap this spec exists to close.

---

## 8. Phase plan

| Phase | Scope |
|---|---|
| **0** | Ethan ratify this spec |
| **1** | Resolve OCR gap or produce explicit textless-doc exclusion list |
| **2** | Batch attribution scale-up across full corpus, `branch` facet added |
| **3** | TFP tag pass (seed-set expansion + explicit tagging) |
| **4** | Eval at 50–200-pair scale |
| **5** | Facet recheck; Grace/operator sign-off that v7.2 Phase 4 and v7.3 Phase 4 may now proceed |

---

## 9. Exit criteria

- [ ] OCR gap resolved, or an explicit, checked textless-document list exists and is excluded from
      claimed attribution coverage — **FBV74-01 Abelard OPEN**
- [ ] `concept_id`/`area_name`/`family_name`/`attribution_version`/`branch` present corpus-wide (not a
      25-document island), verified by a facet recheck, not assumed from the batch job's exit code — **execution OPEN** (classifier code DONE under FBV74-02)
- [ ] `branch=tfp` correctly set on a verified TFP/clinical-literature subset — **FBV74-03 Colombo OPEN**
- [ ] Eval re-run at 50–200 Q→doc pairs — harness DONE (FBV74-04); **real CHROMA-2 eval run OPEN**
- [x] v7.2 Phase 4 / v7.3 Phase 4 cite this spec's exit as precondition (FBV74-05 Grace PAUSED until 01..04 PASS)
- [x] Register rows on `active.md` (FBV74-00..05)

**Ratification ≠ corpus done.** This row accepts the scale-up plan and gates; Abelard/Colombo/Grace execution rows remain the real exit.

---

## 10. Ratification

| Role | Action | Date | Status |
|---|---|---|---|
| Felix | Draft spec (gap inventory, scale-up scope, TFP tag pass) | 2026-07-04 | DONE |
| Ethan | Ratify / amend | 2026-07-19 | **RATIFIED** |
| Abelard | OCR gap resolution | — | PENDING (FBV74-01) |
| Colombo | TFP tag pass + eval expansion | — | PENDING (FBV74-03; eval run) |
| Grace | Triage execution rows; FBV74-05 sign-off | 2026-07 | Rows live; FBV74-05 PAUSED |

### Ethan ratification notes (2026-07-19)

1. **Problem statement** (pilot-scale G1–G4 ≠ agentic readiness) — **accepted**.
2. **OCR gap is blocking, not cosmetic** — **accepted**; FBV74-01 must resolve or publish exclusion list before claiming full-corpus attribution.
3. **Reuse `cobalt_chroma2_attrib_batch.py` + `branch` facet** — **accepted**; no rebuild.
4. **TFP tagging is Colombo judgment**, not engineering keyword defaults — **accepted** (FBV74-03).
5. **No `REAL_DATA=1` / TRIZ-on-library** until this exit passes — **accepted** (keeps FBV72/73 honest).

`SIGNED: Developer (Felix) | Claude Code context | 2026-07-04 | fpf_bridge v7.4 COBALT corpus scale-up spec draft`

`SIGNED: Architecture (Ethan) | Hesperia day run | 2026-07-19 | FBV74-00 RATIFIED — plan + gates; OCR/TFP/eval execution still open`
