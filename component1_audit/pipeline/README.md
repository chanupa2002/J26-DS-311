# Component 1 pipeline v0.1

The environment has Python and pandas but does not expose an executable `Rscript` runtime. This narrowly scoped first pipeline therefore uses Python for the only currently implemented aggregate. It keeps the existing audit R scripts intact; no R transformations are claimed to have run.

## Implemented

`prepare_household_core.py` reads the available household-identification file as the provisionally approved development spine and independently counts unique `pid` values in the B0 roster. It validates nonmissing unique household keys, unique roster `hhcode + pid`, roster-to-master membership, one-to-one merge cardinality, and exact preservation of the master key order and row count. It writes a local `household_core.csv` and a manifest with input hashes and counts.

The output column is explicitly named `roster_member_count`. It is a direct record count and is **not yet asserted to equal a questionnaire-defined household size**, nor used as a dependency indicator. A household with no roster record would remain missing, not be changed to zero. Separate companion extracts are also written:

- `fies_item_responses_pending.csv` retains L1 and L2 item codes in separate columns, with no score.
- `proxy_sensitivity_reference.csv` contains the existing prepared per-capita consumption and label, explicitly marked unvalidated and isolated from the core dataset. The researcher approved it only for descriptive sensitivity. It is not ground truth, an eligibility outcome, training target, or model feature.
- `d1_observed_candidates_pending.csv` preserves raw housing C1_04-C1_08 and the direct D-module asset fields selected for review. It keeps one raw H1_17 household value only when the repeated nonmissing values agree, records agreement/count diagnostics, and does not recode 997/998/999 or calculate a derivative. The researcher approved the separate housing items, direct asset items, and H1_17 as validation/reconstruction candidates; no asset share, housing deprivation, per-capita income, or missingness indicator is created.
- `d3_person_items_pending.csv` keeps B0 ages and B3_01-B3_03 at person level, joined one-to-one by `hhcode + pid`. It includes an explicit B3-record-present flag, preserves missing item values, and excludes B3_04 pregnancy from the health-condition candidates. No age bands or household health/activity aggregates are calculated.

Outputs stay under the git-ignored `component1_audit/outputs/pipeline_v0/` directory. Source files are read-only.

## Run

From the repository root:

```powershell
python component1_audit/pipeline/prepare_household_core.py
python -m unittest discover -s component1_audit/pipeline -p 'test_*.py' -v
```

By default inputs are read from `C:\data\processed\clean`, falling back to `Data/processed/clean` if that path is unavailable. Set `BRIGHT_CLEAN_DIR` or `BRIGHT_OUTPUT_DIR` to override. Missing files or required columns fail clearly.

## Pending

Income, consumption construction, debt, savings, shock, agriculture, material conditions and all scoring remain pending because their source mapping, universe, coding or aggregation requires missing documentation or researcher decisions. FIES item responses are preserved separately; no household FIES score is calculated. The consumption proxy is a separate descriptive-only reference; it is excluded from the core dataset. No D1-D7 score, fuzzy system, Bayesian network, threshold, weight, ranking or eligibility result is created. See `../outputs/proposed_resolution_report.md` and `../outputs/research_decisions_status.csv`.
