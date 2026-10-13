# Gate report — CORE-D2 W7 sampling and graph stability

**Tasks:** `CORE-D2-070..079`
**Date:** 2026-09-16
**Authority note:** Felix, all W7 roles, explicit operator authorization ("execute solo through activation," 2026-09-16).

## Result

**PASS** (mechanism-level, against synthetic fixtures — no real corpus data exists yet).

## What was built

- `docs/specs/ETHAN-CORE-D2-W7-SAMPLING-STABILITY-CONTRACT.md` — freezes what
  CHI-015 §7 only ever described in prose: sample size 25/stratum, seed
  `20260916`, "high-NPMI novel" stratum (`npmi >= 0.3`), "authored-edge
  disagreement" stratum (`agrees` with `npmi <= 0.0`), four stability
  metrics (rank correlation, NPMI drift, G² drift ratio, top-50 Jaccard),
  and pass thresholds (`≥0.85`, `≤0.10`, `≤0.50`, `≥0.60` respectively).
- `tools/dict_calibration/dict_d_sampling.py` — seeded stratified sampling
  (`select_high_npmi_novel`, `select_authored_edge_disagreement`),
  first-co-occurring-paragraph excerpt attachment (fails closed if none
  found — should be structurally impossible for a real Dict D row), and the
  Colombo-role review-record skeleton (`disposition: null` — no content
  judgment made by this task).
- `tools/dict_calibration/dict_d_stability.py` — `leave_one_book_out`
  (mandatory recurring check) and `corpus_growth` (one-time capability
  proof), both built on `compare_rebuilds`, which computes all four frozen
  metrics between a baseline and a perturbed rebuild and reports which
  pairs appeared/disappeared under perturbation.

## Commands and results

```text
$ python -m pytest -q tests/dict_calibration/test_dict_d_sampling.py
............
12 passed

$ python -m pytest -q tests/dict_calibration tests/lexical_concept
[all dots, no failures — full suite, same commit]
```

## Notable finding during construction (kept, not smoothed over)

The first hand-built "stable" fixture (4 books, `N=10`) genuinely **failed**
its own leave-one-book-out gate — removing one book that held 20-40% of the
corpus swung the G² drift ratio past the frozen `0.50` threshold, and a
fixture where `(D,E)`'s only co-occurrence sat in a single book made that
pair vanish outright under removal, correctly failing the Jaccard threshold
too. Both were genuine, correct behavior of the metrics against a fixture
too small and too concentrated to be actually stable — not a bug in
`compare_rebuilds`. Fixed by spreading each pair's evidence across multiple
books in the "stable" fixture (`test_dict_d_sampling.py::_redundant_corpus`,
10 books) and keeping a **separate**, deliberately fragile fixture
(`test_fragile_pair_disappears_when_its_sole_book_is_removed`) to prove the
gate actually catches instability rather than always passing.

## What this does not cover yet

- No real sample content has been reviewed — `build_review_records` produces
  the disposition skeleton only; a human/AI content judgment on real
  `novel`/`agrees`-disagreement pairs requires the real corpus rerun
  (`CORE-D2-049-C/D`, still deferred per operator decision 2026-09-16).
- The W9 activation weight value is explicitly not decided by this wave (see
  the Ethan contract's "What this contract does not decide").

## Release

W8 (`CORE-D2-080..089`, runtime context and shadow calibration) is released.

---
SIGNED: Felix (all W7 roles, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2 W7 gate
