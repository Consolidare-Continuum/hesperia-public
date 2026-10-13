# HSR-V7 consolidation inventory

Date: 2026-07-06

## Repository state

- Branch: `main`
- Commit: `5778de1`

## No deletion or pruning

This pass includes renames and archive moves only. No files are deleted and no payloads are pruned.

## Proposed renames

1. `docs/SOURCE_OF_TRUTH.md` -> `docs/HSR-V7-SOURCE-TRUTH.md`
1. `docs/CONSOLIDATION_REPORT.md` -> `docs/HSR-V7-CONSOLIDATION-REPORT.md`

### Reasons

- Make the names explicit, searchable, and aligned with the HSR-V7 naming pattern.
- Preserve current content while making the file purpose obvious to future agents.

### Reference impact

- References to the old names must be updated after the rename.
- Runtime behavior is unaffected.
- Tests are unaffected.

## Proposed archive moves

1. `docs/brain-export/README.md` -> `docs/archive/brain-export/README.md`

### Reason

- The file is archival guidance for an archival payload tree, so it belongs with archive governance instead of alongside active documentation roots.

### Authority / status

- Status: `HISTORICAL-REFERENCE`
- Authority level: `SUPPORTING-EVIDENCE`

### Reference impact

- Update archive governance text that points at the old location.
- Runtime behavior is unaffected.
- Tests are unaffected.

