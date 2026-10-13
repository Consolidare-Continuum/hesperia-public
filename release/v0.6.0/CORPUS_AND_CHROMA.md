# Corpus and Chroma

Do not ship corpus payloads in baseline release.
Do not ship Chroma storage in baseline release.
Describe them. Prebuild them outside the package.

## Corpus

- Store corpus text outside release payload.
- Use a manifest with `session_id`, `therapist_id`, `patient_id`, `session_number`, `date`, `path`.
- Use working examples from `tests/fixtures/tfp_calibration/` and `tests/fixtures/dict_calibration/corpus/sample.md`.
- Keep relative file paths valid from the manifest base dir.
- Load through `hesperia/corpus/session_corpus.py`.

## Chroma

- Treat Chroma as external runtime state.
- Precreate collections before retrieval tasks.
- Keep persist dirs or remote stores outside git and outside release zip.
- Record collection names, source layer, version, and ingestion command in deployment notes.
- Use working retrieval examples from the Hesperia integration layer only as reference behavior, not as bundled state.

## Required operator rule

- Prepare corpus first.
- Prepare dict pack second.
- Build or ingest Chroma third.
- Run system seal only after all three are in place.
