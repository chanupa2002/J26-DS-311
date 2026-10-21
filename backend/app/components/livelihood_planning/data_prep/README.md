# Model 2 data preparation

The fact bank supplies `livelihood_facts`; the viability output supplies
`livelihood_scores`. Data preparation is manual and is never imported by the
API. Raw survey data and generated CSV files must not be committed.

## Loading order

Run notebooks from `livelihood_planning/notebooks/` in this order:

1. `Model2_Fact_Bank.ipynb` builds and validates `fact_bank.csv` and
   `livelihood_scores.csv`.
2. `Model2_Load_Facts.ipynb` performs the initial load of facts first, then
   scores, and checks row counts and retrieval.
3. `Model2_Service_Test.ipynb` verifies table access and the matching RPC.
4. For later approved changes, use `Model2_Update_Facts.ipynb` and repeat the
   service checks.

Review scopes, districts, SWOT labels, evidence statements, sample sizes, and
`is_estimated` values before loading. The initial load notebook replaces table
contents, so run it only against the intended Supabase project with an approved
backup.

The scripts in `data_prep/` are manual placeholders and cleaning helpers. They
must not be called by the API.
