# Component 1 — BRIGHT household vulnerability data audit and pipeline

This is a review and initial preparation package for the BRIGHT Multi-Thematic Household Survey of Sri Lanka 2025. It supports research and human review; it is not an eligibility determination system. No fuzzy or Bayesian model is included.

## Inputs found

- Configured cleaned CSVs: `C:\data\processed\clean\` (65 files).
- Repository mirror: `../Data/processed/clean/` (contains an additional underscore-named duplicate F3 long export).
- Prepared tables and prior QA artifacts: `C:\data\processed\`.
- Questionnaire, codebook, original R preprocessing script, and original mechanical validation script: not present in the workspace.

The audit scripts use the configured `C:\data\processed` paths first, then the repository mirror if the configured paths are unavailable. Override paths with `BRIGHT_CLEAN_DIR` and `BRIGHT_PROCESSED_DIR`.

## Audit and provisional mapping

- `outputs/module_inventory.csv`: file dimensions, column names/types, missingness, likely grain/key, and duplicate-key checks.
- `outputs/variable_mapping.xlsx`: candidate mapping sheet and approval decisions.
- `outputs/data_quality_report.md`: findings, unresolved issues, and limitations.
- `outputs/decisions_for_review.csv`: explicit human decisions.
- `outputs/issue_register.csv`: issue-level findings and follow-up actions.
- `outputs/module_missingness.csv`: missing cells and rates for every module variable; the test suite checks counts against `expected_missingness.csv`.
- `outputs/proposed_resolution_report.md`: evidence and resolution options for priority data-quality issues.
- `outputs/updated_issue_register.csv`: issue-level follow-up register with counts, tests and approval needs.
- `outputs/implementation_status.csv`: implemented, pending and unresolved fields/families.
- `outputs/research_decisions_status.csv`: researcher responses and the limits attached to each approval.
- `outputs/indicator_registry_review.csv`: 43 provisional candidates with unapproved status and explicit review fields, exported from the existing workbook.
- `outputs/variable_mapping.xlsx`: 43 candidate indicators. This is a provisional questionnaire-informed map; it is not approval to include indicators or finalize constructs. See the issue and decision registers before using any candidate as a feature.

`R/01_audit.R` is the reproducible R entry point and uses base R. From the repository root, run `Rscript component1_audit/R/01_audit.R` to rebuild the R inventory. The generated package includes `scripts/generate_deliverables.py` to build the workbook and report locally where no R Excel-writing package is available. `R/02_tests.R` contains base-R assertions for household key uniqueness, expected row counts, questionnaire-backed code domains, missingness bounds, independent aggregation, and prevention of row multiplication. It uses the versioned `outputs/expected_module_rows.csv` baseline; update that baseline only after reviewing a legitimate source-data version change.

The generated inventory and workbook were computed with the included local Python/pandas helper. This environment has Python/pandas but no callable `Rscript` runtime, so audit R code has not been run here. The initial household pipeline uses Python for its narrow, directly verifiable operation; it does not claim that legacy transformations were reproduced.

## Initial household pipeline

See `pipeline/README.md`. `pipeline/prepare_household_core.py` creates one row per delivered household key and counts unique roster person IDs independently before a validated one-to-one join. It writes only under the git-ignored `outputs/pipeline_v0/` directory and records input hashes. The output calls this `roster_member_count`; it does not claim that the field is a validated dependency or age-composition indicator. No other D1–D7 variable is currently implemented because unresolved transformations require researcher approval.

Run from the repository root:

```powershell
python component1_audit/pipeline/prepare_household_core.py
python -m unittest discover -s component1_audit/pipeline -p 'test_*.py' -v
```

The current run uses the 6,847-key population provisionally for development diagnostics and produced unique nonmissing keys with no unmatched roster counts. Eleven synthetic unit tests validate the implemented key, aggregation, raw-candidate preservation, one-to-one person joins, FIES preservation, proxy isolation and deterministic output mechanics. They do not reconcile the published population discrepancy or validate a vulnerability construct.

Never write derived tables back into `Data/processed/clean/` or modify source CSVs. Keep local survey microdata and derived household rows out of version control and public outputs.
