# Upcelerator 2026 source map and ingestion policy

This document is the canonical intake map for the archived source bundle:
`/data/altitudine/prichindel.com/.cache_to_sort_out/HESPERIA - Upcelerator 2026-20260704T155731Z-3-001.zip`.

Its job is simple:

- preserve which Upcelerator files said what
- classify each source by evidence type rather than flattening everything into timeless truth
- tell later documentation passes how wording from this archive may be propagated across HESPERIA

Without this map, market copy, investor phrasing, exploratory estimates, and open hypotheses get
mixed together too easily.

## 1. Evidence classes for this archive

| Evidence class | Meaning in repo terms | Typical use |
|---|---|---|
| direct business framing | The archive really used this wording to describe HESPERIA's market or product | Safe to preserve as dated terminology |
| quantified planning estimate | Numbers or ranges used for planning, TAM/SAM/SOM, or pricing orientation | Preserve with date and assumptions attached |
| investor framing | Presentation language aimed at pitching, not scientific proof | Preserve as wording, not as technical validation |
| adjacent-market snapshot | Competitor landscape statement true for that program pass | Preserve as time-bounded orientation |
| open question / hypothesis | The archive itself treats this as unresolved or exploratory | Must stay explicitly labeled as open |

## 2. File-by-file source map

| Source file | Main role | Safe carry-forward into docs | Caveat |
|---|---|---|---|
| `Assignment-2B1_Market-Definition.txt` | Defines customer filter, buyer roles, early geographies, verticals | B2B-only framing, regulated-market filter, Moldova/Romania -> EU expansion path, "reliability matters more than performance" | Market boundary, not proof of actual demand |
| `Assignment-2B2_Market-Size.txt` | Bottom-up TAM/SAM/SOM and first-customer discipline | `EUR5B` TAM, `EUR200M` SAM, `EUR1M ARR` SOM as dated planning estimates; "name the first 20 customers" execution rule | Numbers are assumptions, not measured traction |
| `Assignment-2B3_PESTLE-Analysis.txt` | Why-now logic for regulation, distrust, cost pressure, legal pressure | "forced adoption market", regulation-driven demand, status quo resistance, model-agnostic/deterministic stability language | Macro framing, not legal advice |
| `Assignment-2C1_Competitors-Description.txt` | Adjacent funded competitors plus direct-landscape note | Arize, Arthur, Patronus as adjacent reactive layer; direct structured-meaning landscape more fragmented | Competitive snapshot is time-bounded |
| `Assignment-2C3_Competitors-Detailed-Analysis.txt` | Paradigm-level distinction | reactive paradigm `monitor -> evaluate -> explain` vs deterministic paradigm `define -> map -> guarantee` | Strategic framing, not benchmark data |
| `Assignment-2C4_Competitive-Advantage.txt` | Condensed differentiator statement | "stable, auditable meaning by design", "same input, same output", structural-not-incremental advantage | Product wording, not scientific proof by itself |
| `Assignment-2D_Pitch-Deck-Script.txt` | Investor-facing market and competition script | beachhead logic, regulation-not-hype line, status quo as strongest competitor | Investor rhetoric must not be misquoted as validation evidence |

## 3. Sources outside this first plain-text pass

These files are part of the same truth layer but require their own focused ingestion passes:

- `hesperia-landing-page.html`
- `Assignment-2C2_Competitors-Grading.xlsx`
- `Assignment-3E_Analysis-Pivot.docx`
- `Assignment-3F_Key-Insights.docx`

The current repo already preserves some of their wording in
`UPCELERATOR_PRODUCTIZATION_QA.md`, but they still deserve their own explicit intake references in
later passes.

## 4. Propagation rules for later documentation runs

1. Keep the archive date visible. Upcelerator 2026 is a dated productization layer, not timeless
   company doctrine.
2. Preserve wording, but attach status. A phrase can be real archive language without being current
   market truth.
3. Route technical proof through technical docs. Buyer phrases like `deterministic validation` or
   `audit trace` must still anchor into `METHODS.md`, `VALIDATION_EVIDENCE.md`, and ISO-facing docs.
4. Keep pricing and market-size numbers attached to assumptions. Do not restate them as if they
   were observed revenue or measured demand.
5. Preserve the strongest paradigm claims as terminology. In particular:
   `accountable AI`, `forced adoption market`, `reactive paradigm`, `deterministic paradigm`,
   `stable, auditable meaning by design`.
6. Treat unresolved commercial questions as unresolved. The archive is useful partly because it did
   not pretend willingness-to-pay and conversion assumptions were settled.

## 5. What this source map unlocks

With this map in place, later HESPERIA docs can cite Upcelerator material in a disciplined way:

- `UPCELERATOR_PRODUCTIZATION_QA.md` for buyer-language Q&A
- `UPCELERATOR_MARKET_AND_COMPETITION.md` for market boundary and competition logic
- `TERMINOLOGY_AND_ABBREVIATIONS.md` for stable wording candidates
- ISO/publication docs for where those terms connect back to actual architecture and evidence

## 6. Aurel-style stabilization checklist

Before propagating any Upcelerator phrase into another document, confirm all five:

1. the statement is still visibly tied to **Upcelerator 2026**
2. its truth class is named or obvious from context
3. it is not being upgraded from market framing into technical proof
4. any engine-facing phrase points back to `METHODS.md`, `VALIDATION_EVIDENCE.md`, or
   `docs/iso/OPERATOR_GUIDE.md`
5. open or exploratory commercial claims remain open or exploratory after the rewrite

## Navigation

← [`../README.md`](../README.md) · [`UPCELERATOR_PRODUCTIZATION_QA.md`](UPCELERATOR_PRODUCTIZATION_QA.md) ·
[`UPCELERATOR_MARKET_AND_COMPETITION.md`](UPCELERATOR_MARKET_AND_COMPETITION.md) ·
[`TERMINOLOGY_AND_ABBREVIATIONS.md`](TERMINOLOGY_AND_ABBREVIATIONS.md)
