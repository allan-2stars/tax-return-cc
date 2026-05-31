# EXPORT_PACKAGE.md

## Export ZIP file contract

The export ZIP includes ordered top-level artifacts (for deterministic review tooling).

### Canonical evidence status file

- **Filename:** `05A-EVIDENCE-STATUS.json`
- **Status:** canonical and stable
- **Purpose:** evidence completeness snapshot at export time, including required/recommended summaries and incomplete obligations.

Any downstream integration that reads evidence status from an export package should use `05A-EVIDENCE-STATUS.json` as the source of truth.

