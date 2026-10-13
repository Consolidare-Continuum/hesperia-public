# Chiron gate report — CORE-D2 W2 candidate evaluation

**Task:** `CORE-D2-028`  
**Verified commit:** `2dc2f2a9dbf6e489f8c3e88a5c5d0e861065c3da`  
**Date:** 2026-09-16

## Result

**PASS.**

## Commands and results

### Focused comparison tests — pass 1

```text
$ python -m pytest -q tests/dict_calibration/test_evaluate_bundles.py
....................................................                     [100%]
52 passed
```

### Focused comparison tests — pass 2

```text
$ python -m pytest -q tests/dict_calibration/test_evaluate_bundles.py
....................................................                     [100%]
52 passed
```

### Full calibration tests

```text
$ python -m pytest -q tests/dict_calibration
........................................................................ [ 65%]
......................................                                   [100%]
110 passed
```

### Independent frozen-fixture determinism

Chiron created one temporary frozen fixture with a schema-valid ambiguous Dict A
entry and closed Dict B references, then called `evaluate_bundle_comparison`
twice with the same fixture as both baseline and candidate and the same ordered
texts `["alpha", "alpha alpha"]`.

```text
report_1_sha256=33736376d1354b5dce634e331786b2752c8592eb38c539b7574e498e4f9c08a3
report_2_sha256=33736376d1354b5dce634e331786b2752c8592eb38c539b7574e498e4f9c08a3
canonical_report_sha256=3196a90d65186947916ca994773624ad3cee84d3e32e00723a8bf617f60fc37c
canonical_bytes_equal=True
reports_equal=True
strict_weight_zero_identity=True
sample_count=2
```

The two complete canonical reports were byte-identical. Their embedded
`report_sha256` values were identical. Baseline and candidate views matched for
every sample, and accepted, rejected, coverage, entropy, and every family delta
were zero.

## Commit and boundary checks

```text
$ git rev-parse HEAD
2dc2f2a9dbf6e489f8c3e88a5c5d0e861065c3da

$ git diff-tree --no-commit-id --name-only -r HEAD
tests/dict_calibration/test_evaluate_bundles.py
tools/dict_calibration/evaluate.py

$ git diff-tree --no-commit-id --name-only -r HEAD -- assets/calibration/dicts/v0_core_syzif_001
<no output>

$ git grep -n 'v0_core_syzif_001' HEAD -- tools/dict_calibration/evaluate.py tests/dict_calibration/test_evaluate_bundles.py
<no matches>
```

Commit `2dc2f2a` neither modifies nor directly references the mock
`v0_core_syzif_001` pack as evaluation or release evidence. Its tracked mock
artifact hashes at verification time were:

```text
7a4a90f17e6a430e19135b4e5e3099598073854ad50d9145100bc78721be7175  dict_a.jsonl
ccd88a9342115cd889b82d1b194aadf3deac9487aa276f27b20d812226ec0f01  dict_b.jsonl
c24fe446dfe8182f552bb1a6e406efe155f04d4337790c0652fc047da7a44cc3  dict_d_v0_core_syzif_001.jsonl
```

An unrelated worktree modification to
`assets/calibration/dicts/v0_core_syzif_001/LIVE-PROPOSE-GATE.md` was already
present before verification. It is not part of commit `2dc2f2a`, was not used as
evidence, and was not touched by Chiron.

W2 candidate evaluation passes. This verdict does not promote a bundle,
authorize release evidence from the mock pack, or authorize a non-zero
empirical weight.

SIGNED: Independent Verifier (Chiron) | Hesperia CORE-D2 W2 gate context | 2026-09-16 | CORE-D2-028
