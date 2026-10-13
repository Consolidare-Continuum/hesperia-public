# Public release manifest — Hesperia 1.0.0

| Field | Value |
|---|---|
| Product version | 1.0.0 |
| Licence | CC-HES-LIC-1.0 (source-visible, all rights reserved) |
| Source | development line, tag `v1.0.0-commercial` |
| History | fresh single-commit history (no private history published) |
| Released | 2026-10-13 |

## Withheld from this tree

| Path (in private tree) | Reason |
|---|---|
| `hesperia/modules/default/corpus/syzif/` | Third-party copyrighted books (full text) plus OCR tooling. Bibliography published instead. |
| `assets/data/engine_dynamics_v060/corpora/tfp_ru_sentences.jsonl`, `tfp_ru_cleaned_sentences.jsonl` | Full-text sentences of a third-party copyrighted book. |
| `hesperia/modules/tfp/data/tfp_v1/inspector_exports/` | Clinical session material (personal health data). |
| `tests/fixtures/tfp_calibration/session_11_09_2023_plain.txt` | Clinical session material (personal health data). |
| `docs/brain-export/`, `docs/brain-links/` | Internal organisation records. |
| `tools/scripts/*.service`, `tools/scripts/*.conf` (deployment) | Internal deployment configuration. |

Calibration dictionaries (token → concept weights) are retained. They contain lexical surfaces and weights, not source text.

## Verification

- Secret scan: gitleaks 8.18.4 over the full tree. The only findings are false positives on lexicon `"token"` fields.
- Clinical-text check: 6-word shingle match of the withheld session transcript against every file.
