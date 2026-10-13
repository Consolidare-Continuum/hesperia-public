# Layer 4 — Evidence Retrieval Quality (`core/layers/layer_4.py`, 37_SPEC)

**Position in pipeline:** Fourth executable layer. The first layer that brings external
reference material into the structural analysis. L4 receives two sets of retrieved corpus
chunks (R_B for baseline, R_S for shadow) and measures how well the retrieved evidence aligns
with the dominant family/area identified in L1. It produces 25 variables characterizing
retrieval completeness, source diversity, evidence-to-attribution alignment, B/S stability
of the evidence pool, and chunk integrity — closing with `EVIDENCE_ACCEPTABILITY_GATE`.

**Spec origin:** `37_SPEC`. Module docstring: *"25 variables: retrieval counts, family/area
match, integrity, support index, gate. When R_B/R_S empty: deterministic zeros/shortfall;
gate fails when shortfall > MAX_SHORTFALL."*

---

## What L4 receives: corpus chunks

A "chunk" is a dict with:
- `bookId` — which reference book/document the chunk came from
- `familyId` — which semantic family (0–287) this chunk belongs to
- `chunkId` — unique chunk identifier (for Jaccard deduplication)
- `checksum_ok` (optional, default True) — integrity flag

`R_B` = list of up to TOP_K=20 chunks retrieved for the baseline run. `R_S` = same for shadow.
Both arrive pre-retrieved from the corpus — L4 does not perform retrieval itself. The retrieval
algorithm is tagged by `RETRIEVAL_MODE_ID = "LEX_BM25_V1"` by default, meaning a
lexical BM25 retrieval was used to produce R_B and R_S.

**Why BM25.** BM25 (Robertson & Sparck Jones, 1976/1994 — crystallized through TREC
evaluations in the 1990s) is the probabilistic term-frequency function that replaced
raw TF-IDF as the canonical lexical retrieval baseline. For a query term `t` in document `d`:

```
BM25(t, d) = IDF(t) × [tf(t,d) × (k₁+1)] / [tf(t,d) + k₁×(1−b + b×|d|/avgdl)]
```

where `tf` = term frequency, `IDF` = log((N−n_t+0.5)/(n_t+0.5)+1)`, `|d|` = document length,
`avgdl` = mean document length across corpus, and `k₁`, `b` are free parameters (typically
k₁≈1.2, b≈0.75). BM25 is "length-normalized TF-IDF": it caps the contribution of repeated
terms (via the `k₁` saturation) and penalizes long documents (via `b`). For TFP corpus
retrieval, BM25 finds the lexically closest chunks to the query terms derived from the text,
ranked by relevance score. L4 receives the top-K results and measures their structural quality.

**When R_B/R_S are empty.** If retrieval returns nothing, `RETRIEVAL_SHORTFALL_BASELINE =
TOP_K = 20 > MAX_SHORTFALL = 2`, which immediately fails `EVIDENCE_ACCEPTABILITY_GATE`. The
rest of L4 still runs and produces defined (all-zero or all-false) outputs — no exception,
no crash. The pipeline records that evidence is unavailable and continues.

---

## The 25 variables

### Group 1 — Retrieval completeness

| Variable | Formula | Meaning |
|---|---|---|
| `RETRIEVAL_MODE_ID` | "LEX_BM25_V1" (or configured) | Tag identifying retrieval algorithm |
| `TOP_K` | 20 (configurable) | Target chunk count per run |
| `RETRIEVED_COUNT_BASELINE` | len(R_B) | Actual chunks retrieved in baseline |
| `RETRIEVED_COUNT_SHADOW` | len(R_S) | Actual chunks retrieved in shadow |
| `RETRIEVAL_SHORTFALL_BASELINE` | max(0, TOP_K − retrieved_B) | Gap between target and actual |
| `RETRIEVAL_SHORTFALL_SHADOW` | max(0, TOP_K − retrieved_S) | Gap for shadow |

The shortfall is a direct measure of corpus coverage: if the retrieval engine cannot find
20 chunks relevant to the query, either the corpus lacks coverage for this concept domain
or the retrieval failed. More than 2 missing chunks (`MAX_SHORTFALL = 2`) fails the gate.

### Group 2 — Source diversity

| Variable | Formula | Meaning |
|---|---|---|
| `UNIQUE_BOOKS_BASELINE` | \|{bookId in R_B}\| | Distinct source books in baseline evidence |
| `UNIQUE_BOOKS_SHADOW` | \|{bookId in R_S}\| | Distinct source books in shadow evidence |
| `DUPLICATE_BOOK_RATIO_BASELINE` | 1 − (unique_books_B / retrieved_B) | Fraction of baseline chunks from repeated books |
| `DUPLICATE_BOOK_RATIO_SHADOW` | 1 − (unique_books_S / retrieved_S) | Same for shadow |

`DUPLICATE_BOOK_RATIO` is the redundancy measure: if all 20 retrieved chunks come from one
book, `DUPLICATE_BOOK_RATIO = 1 − 1/20 = 0.95`. If each comes from a different book,
`DUPLICATE_BOOK_RATIO = 0.0`. High book concentration means the evidence pool is not
diverse — the structural reading is supported by a single source, not corroborated across
the corpus. The gate threshold (`MAX_DUP_BOOK_CONC = 0.70`) allows some concentration
but rejects near-monopoly sourcing.

### Group 3 — Evidence-to-structure alignment

| Variable | Formula | Meaning |
|---|---|---|
| `FAMILY_MATCH_COUNT_BASELINE` | count(c ∈ R_B : c.familyId == dominant_family_B) | Chunks exactly in the dominant family |
| `FAMILY_MATCH_RATIO_BASELINE` | family_match / retrieved_B | Fraction of evidence in the dominant family |
| `AREA_MATCH_RATIO_BASELINE` | count(area(c.familyId) == dominant_area_B) / retrieved_B | Fraction in the dominant area |
| `TOP_K_FAMILY_COVERAGE_BASELINE` | \|{familyId in R_B}\| / (F+ε) | Fraction of 288 families represented in evidence |
| `EVIDENCE_ENTROPY_BASELINE` | H(chunk family distribution) / log(F) | Normalized Shannon entropy of evidence family spread |
| `EVIDENCE_GINI_BASELINE` | Gini(chunk family counts) | Inequality of evidence family distribution |
| `RANK_WEIGHTED_ALIGNMENT_BASELINE` | Σ w_r·[area_aligned] / Σ w_r, w_r=1/(r+1) | Reciprocal-rank-weighted area alignment |
| `HIT_EVIDENCE_OVERLAP_BASELINE` | Jaccard(active_attribution_families, evidence_families_B) | Cross-system consistency: attribution vs. retrieval |
| `HIT_EVIDENCE_OVERLAP_SHADOW` | Jaccard(active_attribution_families_S, evidence_families_S) | Same for shadow |

**FAMILY_MATCH vs. AREA_MATCH — two levels of alignment.** Family match is exact — chunk must
be in the identical family as the dominant concept. Area match is coarser — chunk must be in
any of the 24 families within the dominant area. Both are necessary because perfect family
match is demanding (retrieval may not always surface chunks in the exact dominant family) but
area match alone is too permissive (any of 24 families qualifies). Their combination in the
support index (0.45 family + 0.35 area, see below) expresses a graduated alignment requirement.

**RANK_WEIGHTED_ALIGNMENT — reciprocal rank weighting.** Each chunk at rank `r` (0-indexed)
contributes weight `w_r = 1/(r+1)`: rank-0 chunk contributes 1.0, rank-1 contributes 0.5,
rank-2 contributes 0.333, and so on. This is the per-document component of **Mean Reciprocal
Rank (MRR)**, the standard IR metric for asking "how early does the relevant result appear?"
(Voorhees, 1999, in TREC Q&A track). Applied to area alignment: if all area-aligned chunks
appear at the top of the ranking, `RANK_WEIGHTED_ALIGNMENT` is high; if they're buried at
the bottom, it is low even if area match ratio is reasonable. This penalizes retrievals where
the structurally relevant chunks were deprioritized by the BM25 scorer.

**HIT_EVIDENCE_OVERLAP — cross-system consistency check.** This is the most conceptually
distinctive variable in L4:

```
HIT_EVIDENCE_OVERLAP_BASELINE = Jaccard(
    {f : hits_B[f] > 0},       # families activated by attribution
    {c.familyId for c in R_B}  # families represented in retrieved evidence
)
```

The attribution (Dict A/B matching) and the corpus retrieval (BM25) are two independent
systems — the lexicon and the corpus. For a structurally coherent analysis, they should
agree: if attribution says "this text is about families {12, 47, 88}", the retrieved evidence
should also come from those families. A low Jaccard means the two systems are pointing at
different parts of the semantic space: the text's vocabulary activates one semantic region,
but the retrieval engine found relevant chunks in a completely different one. This is a
consistency alarm — either the retrieval is pulling off-topic material, or the attribution
is mapping to families that are poorly represented in the corpus.

**EVIDENCE_ENTROPY and EVIDENCE_GINI.** These are the same Shannon entropy and Gini
coefficient tools used in L1, now applied to the distribution of retrieved chunks over families
rather than the distribution of attributed tokens. High entropy = evidence is spread across
many families; low entropy = evidence is concentrated in a few. Conceptually, the right answer
is domain-dependent: for a topic-focused text, you want evidence concentrated in the relevant
families (low entropy, low Gini). For a wide-ranging text, spread is expected and appropriate.
L4 records these as descriptive signals — neither high nor low entropy automatically fails the
gate — and leaves the interpretation to downstream rules and guards.

### Group 4 — B/S evidence stability

| Variable | Formula | Meaning |
|---|---|---|
| `EVIDENCE_JACCARD_BS` | Jaccard({chunkId in R_B}, {chunkId in R_S}) | Chunk-level overlap between baseline and shadow retrievals |
| `BOOKSET_JACCARD_BS` | Jaccard({bookId in R_B}, {bookId in R_S}) | Book-level overlap between baseline and shadow |
| `EVIDENCE_SHIFT_SCORE` | 1 − EVIDENCE_JACCARD_BS | Fraction of evidence pool that differs between runs |

These three variables mirror what L3 did for the structural reading (B/S deltas) but now
applied to the evidence pool. `EVIDENCE_JACCARD_BS` measures whether the same corpus chunks
are retrieved under baseline and shadow inputs. `BOOKSET_JACCARD_BS` does the same at book
granularity — a coarser but more meaningful stability signal (the same overall book being
retrieved is more robust than the exact same chunk being retrieved, since chunk boundaries
can shift with indexing changes). `EVIDENCE_SHIFT_SCORE = 1 − EVIDENCE_JACCARD_BS` is the
complement: how much of the total evidence pool is exclusive to one run.

A high `EVIDENCE_SHIFT_SCORE` combined with a `SHADOW_ACCEPTABILITY_GATE = False` from L3
compounds the fragility signal: the structural reading changes under perturbation AND so does
the corpus evidence supporting it. Both together indicate a reading near a decision boundary
from multiple directions.

### Group 5 — Integrity

| Variable | Formula | Meaning |
|---|---|---|
| `INTEGRITY_CHECK_PASS_RATIO` | ok_chunks / unique_total_chunks | Fraction of unique chunks with checksum_ok=True |

Integrity is checked across the combined B+S evidence pool, deduplicated by `chunkId`. If
any unique chunk has `checksum_ok = False`, `INTEGRITY_CHECK_PASS_RATIO < 1.0`, and
`EVIDENCE_ACCEPTABILITY_GATE = False`. This is a hard binary — not a graceful degradation.
The reasoning: a corpus chunk with a failed checksum is a chunk whose content cannot be
verified. Including it in the evidence pool risks drawing structural conclusions from
corrupted data. One bad chunk fails the whole pool.

### Group 6 — Composite support and gate

**EVIDENCE_SUPPORT_INDEX_BASELINE:**

```
ESI = 0.45 × FAMILY_MATCH_RATIO + 0.35 × AREA_MATCH_RATIO + 0.20 × HIT_EVIDENCE_OVERLAP
```

Weights sum to 1.00. Three graduated alignment signals:
- **0.45 × FAMILY_MATCH_RATIO:** Exact alignment — retrieved chunks are in the exact dominant
  family. The tightest and most specific signal, receiving the highest weight.
- **0.35 × AREA_MATCH_RATIO:** Broad alignment — chunks are in the right area but not
  necessarily the dominant family. One level coarser, slightly downweighted.
- **0.20 × HIT_EVIDENCE_OVERLAP:** Cross-system consistency — the Jaccard between attribution
  and retrieval families. Lowest weight because it measures a different property (breadth of
  consistency across the whole activated space) rather than alignment with the dominant reading.

`ESI ∈ [0,1]`. `ESI = 1.0` means all retrieved chunks are in the dominant family AND all
attributed families appear in the evidence AND all chunks are in the dominant area — perfect
alignment across all three dimensions simultaneously. `ESI = 0` means no evidence aligns with
the dominant family or area at all.

**EVIDENCE_ACCEPTABILITY_GATE — four conditions, all must hold:**

```python
EVIDENCE_ACCEPTABILITY_GATE = (
    INTEGRITY_CHECK_PASS_RATIO == 1.0         # no corrupted chunks
    and RETRIEVAL_SHORTFALL_BASELINE <= 2     # at most 2 chunks missing
    and EVIDENCE_SUPPORT_INDEX_BASELINE >= 0.30  # minimum 30% support
    and DUPLICATE_BOOK_RATIO_BASELINE <= 0.70   # not too book-concentrated
)
```

| Condition | Threshold | What fails it |
|---|---|---|
| Integrity | == 1.0 (exact) | Any corrupted chunk |
| Shortfall | ≤ 2 | Corpus gap: too few relevant chunks exist |
| Support index | ≥ 0.30 | Evidence doesn't align with structural reading |
| Book concentration | ≤ 0.70 | Evidence comes from too few books |

Each condition targets an independent failure mode. A corpus that has plenty of chunks but
all from wrong families (low ESI, adequate count, passes integrity) fails differently from a
corpus that is correctly aligned but has a single dominant source (passes ESI, fails
concentration). Both are real evidence quality problems, but they have different remedies —
hence separate conditions rather than a single composite score.

---

## The retrieval-to-structure loop: what L4 is really checking

L4 sits at the junction between the text's internal structural reading (L1–L3) and the
external corpus evidence (R_B, R_S). Its central question is: **does the external corpus
confirm the structural reading the text itself produced?**

The two paths are independent:
- Attribution (Dict A/B matching) determines which families the text *activated*
- BM25 retrieval determines which corpus chunks are *lexically similar* to the text

If both agree (high `HIT_EVIDENCE_OVERLAP`, high `FAMILY_MATCH_RATIO`), the structural
reading is corroborated: the text uses language that (1) maps to the dominant family via the
controlled lexicon AND (2) retrieves corpus chunks from that same family via lexical similarity.
This is double confirmation from two independent systems.

If they disagree, it signals a potential problem with one of the three components: the lexicon
mapping, the corpus coverage, or the BM25 retrieval — and the downstream system should not
simply trust either alone.

---

## Scientific lineage

| Tool | Origin | L4 use |
|---|---|---|
| **BM25 retrieval** | Robertson & Sparck Jones (1976, "Relevance weighting of search terms"); crystallized in TREC evaluations (1994) | Tagged as retrieval mode `LEX_BM25_V1` — the standard lexical retrieval function that produced R_B and R_S |
| **Shannon entropy (applied to evidence distribution)** | Shannon (1948) | `EVIDENCE_ENTROPY_BASELINE`: spread of retrieved chunks across the 288-family space |
| **Gini coefficient (applied to evidence distribution)** | Gini (1912) | `EVIDENCE_GINI_BASELINE`: inequality/concentration of chunk family distribution |
| **Jaccard similarity** | Jaccard (1901) | Three independent uses: `HIT_EVIDENCE_OVERLAP` (attribution vs. retrieval), `EVIDENCE_JACCARD_BS` (B vs. S chunks), `BOOKSET_JACCARD_BS` (B vs. S books) |
| **Reciprocal Rank / Mean Reciprocal Rank** | Voorhees (1999) TREC Q&A evaluation | `RANK_WEIGHTED_ALIGNMENT_BASELINE`: reciprocal-rank-weighted area alignment — are the aligned chunks ranked first? |
| **Convex combination scoring** | Multi-attribute decision theory (Keeney & Raiffa, 1976) | `EVIDENCE_SUPPORT_INDEX` = 0.45 + 0.35 + 0.20, weights summing to 1.0 |

---

## Governance parameters in L4

| Parameter | Default | Role |
|---|---|---|
| `RETRIEVAL_MODE_ID` | "LEX_BM25_V1" | Tags the retrieval algorithm for provenance |
| `TOP_K` | 20 | Target chunk count; shortfall measured against this |
| `MAX_SHORTFALL` | 2 | Maximum missing chunks before gate fails |
| `MIN_SUPPORT` | 0.30 | Minimum ESI for gate pass |
| `MAX_DUP_BOOK_CONC` | 0.70 | Maximum book concentration ratio |

---

## Relationship to neighboring layers and corners

- **L1, L3:** L4 consumes `DOMINANT_FAMILY_ID` and `DOMINANT_AREA_ID` from L1 (for alignment
  measurement), and reuses `hits_B`/`hits_S` (for `HIT_EVIDENCE_OVERLAP`). It does not
  consume L2 or L3 outputs directly — L4 is a parallel branch measuring evidence quality,
  not a continuation of the topology traversal.
- **L5–L9:** `EVIDENCE_ACCEPTABILITY_GATE` propagates forward as a signal that downstream
  layers and guards can weight against. A reading with failed evidence gate is not aborted —
  it proceeds with a known evidence-quality caveat.
- **`corners/corpus_wiring.md`:** The corpus chunks in R_B/R_S come from
  `research/clinical_tfp/` (13 modules), versioned via `assets/lexicon/frozen/v06/` and gated by
  `release/v0.6.0/RELEASE_SCOPE.md` ("Do not ship corpus payloads"). L4 measures the quality
  of what the corpus delivered; `corners/corpus_wiring.md` documents what the corpus is.
- **`corners/lexicon_resolver.md`:** The `HIT_EVIDENCE_OVERLAP` variable is the quantified
  check on the coherence between the lexicon (Dict A attribution → hit families) and the
  corpus retrieval (BM25 → chunk families). That corners document describes the lexicon
  architecture; L4 measures its agreement with corpus evidence.
- **L3 `SHADOW_ACCEPTABILITY_GATE`:** L3 and L4 gates are independent and address different
  fragility risks. L3 = structural reading stability under perturbation. L4 = evidence quality
  and alignment. Both can fail simultaneously (fragile reading + poor evidence) or
  independently, and each failure has a different downstream implication.
