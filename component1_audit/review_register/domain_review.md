# Component 1 indicator review by provisional domain

This review is for researcher review, not approval to include indicators in a final vulnerability score. D1-D7 remain provisional (DEC-16). The register contains the 43 existing provisional candidates plus 18 direct D-module asset questions approved for item-level validation in DEC-18. These added asset rows are questionnaire items, not prepared features. Candidate verification, validation approval and final model inclusion are separate statuses. No final indicator inclusion has been approved.

## D1 - Economic and material conditions

**Existing candidates:** `d1_income_month`, `d1_poor_walls`, `d1_poor_floor`, `d1_poor_roof`, `d1_bad_toilet`, `d1_crowded`, `d1_weak_tenure`, `d1_housing_deprivation`, `d1_asset_share`, `d1_income_pc`, `d1_income_missing`.

**Added raw asset review items (DEC-18):** `d1_asset_item_d_01`, `_d_03`, `_d_05`, `_d_06`, `_d_08`, `_d_10`, `_d_12` through `_d_23` for the 18 questions listed in the approval register. All are household-level item responses; no asset index/share or deprivation coding is implemented.

Wall, floor, roof, tenure and toilet items are separate questionnaire measures. C1_05 is flooring and C1_06 is roof; the prior map had them reversed. The C1_08 response list gives codes 1-14, while its follow-up text says 999 triggers Other, so cleaned 999 values need a source-version/code crosswalk. C1_02 is bedroom count; the questionnaire gives no crowding threshold or denominator. Housing and asset items are correlated and may count related material conditions more than once. H1_17 asks total monthly household income in LKR but repeats across employment records; it is not a per-person question. Per-capita and missingness derivatives remain deferred. The prepared bottom-quintile consumption label is a separate descriptive sensitivity proxy only (DEC-13), not ground truth or a candidate feature.

**Status:** Separate housing and direct asset items are approved for validation only (DEC-17/18); H1_17 is approved for later reconstruction as a raw candidate (DEC-19). Housing composite, asset share/index, per-capita income and missingness derivative are deferred. C1_08 needs code verification; H1_17 needs special-code/repetition/derivation checks; crowding needs a researcher-defined formula/cutoff. No D1 score is implemented. Raw inputs are in `outputs/pipeline_v0/d1_observed_candidates_pending.csv`, except C1_02/roster-derived crowding fields.

**Overlap:** housing items among themselves; asset ownership items among themselves; crowding with D3 household size/dependency; H1_17 with D4 livelihood and deferred D7 debt/income ratio.

## D2 - Food insecurity

**Candidate:** `d2_fies_raw`, based on L1_01-L1_08 (women form) and L2_01-L2_08 (men form). Items ask about eight household food-access experiences due to lack of money/resources during the last 12 months. Responses are 1 Yes, 2 No, 3 Don't know, 4 Refused; frequency and month follow-ups are separate fields for items 06-08. Forms are respondent-specific and should not be treated as 16 independent household indicators without a scoring specification.

**Status:** DEC-05/20: raw references only; no household score or item-level model features. The pending extract is `outputs/pipeline_v0/fies_item_responses_pending.csv` (6,847 rows x 19 columns), preserving L1/L2 separately. Current prepared fractional values are not reproduced by available transformation code.

**Overlap:** FIES experiences overlap with O2_11 food-expenditure coping; respondent forms may report the same household experiences.

**No new researcher decision is requested now:** the raw-only choice is recorded. Scoring/combination remains technically pending until scoring guidance, respondent universe and partial/DK/refusal rules are available.

## D3 - Household needs and dependency

**Candidates:** `d3_dep_ratio`, `d3_share_child`, `d3_share_elderly`, renamed `d3_any_member_chronic_illness_or_severe_disability` (source ID `d3_any_disability`), `d3_chronic_share`, and `d3_activity_interruption_category` (source ID `d3_activity_limited_share`).

B0_04_years and B0_04_months ask member age. The questionnaire gives no child/older age cutoff or dependency formula. B3_01 combines chronic illness or severe disability; listed codes (1 No, 2 Yes) conflict with skip text that treats B3_01=1 as eligible. Cleaned values are 0/1 and recode lineage is unavailable. B3_02 mixes condition types, so a chronic-only share is unsupported by the current mapping. B3_03 asks about activity interruption in the last year, but category 7 means complete interruption more than 12 months ago. B3 is absent for 854 roster members across 677 households.

**Status:** Age candidates remain approved for validation pending thresholds (DEC-21); the combined-condition item is approved with a revised label; B3_03 is for category-preserving item review. Chronic-only share is deferred. Raw person items are in `outputs/pipeline_v0/d3_person_items_pending.csv` (27,875 rows x 8 columns); no household aggregation or score.

**Overlap:** child/older shares and dependency ratio use the same ages; B3 condition and activity measures overlap and have conditional response universes. D3 household size also overlaps D1 crowding.

## D4 - Livelihood and income

**Candidates:** `d4_n_unemp_seeking`, `d4_unemployed_12m`, `d4_n_workers`, `d4_no_worker`, `d4_irregular_share`, `d4_informal_share`.

H1_01 records current status (codes 1-10); H1_13 is job search in the last four weeks conditional on status 8; H1_05 asks unemployment at any point in the past 12 months and H1_05a marks months. H1_08 is payment frequency, not by itself an irregularity measure. H1_04 asks about a written employment agreement; H1_11 asks payment modes; neither alone defines informality/social protection. H2_02 secondary work maps to cleaned `h1_02` in `mod_h2_secondary_employment_lon.csv`; that field crosswalk remains unconfirmed.

**Status:** H1_05/H1_05a and H1_01/H1_13 are separate validation candidates by DEC-22. Worker-count/no-worker measures are deferred; irregular/informal constructs are deferred, with H1_08/H1_04/H1_11 raw only. No household feature or companion extract is generated. Person-to-household aggregation for the two approved candidates remains a research decision.

**Overlap:** current job search and past-year unemployment are related but use different periods; H1_17 income in D1 is related but distinct. Worker count could overlap D3 age/household composition.

## D5 - Shocks and exposure

**Candidates in source map:** `d5_n_shocks_any`, `d5_n_shocks_severe`, `d5_severity`, `d5_price_shock`, `d5_income_shock`, `d5_health_shock`, `d5_climate_shock`, `d5_agri_shock`.

O1_01_1-O1_01_20 codes are 1 severe impact, 2 moderate impact, 3 no impact. Only item _20 explicitly says past 12 months in the questionnaire item table; reference period for _1-_19 is not stated. Agricultural/livestock/fishing/work items have gates (F1_00a, G1_00a, G2_00, I_01); blank cannot be presumed to mean no shock. F3 Maha 2023-24 and F7 Maha 2024-25 are different seasons.

**Status:** DEC-23 says O1 items raw only and F3/F7 separate pending each indicator's target season. No shock aggregation is implemented.

**Overlap:** climate/agriculture shocks overlap within O1; shock exposure overlaps D1 income and D4 employment changes; health shock overlaps D3 member needs.

## D6 - Coping and financial stress

**Candidates in source map:** `d6_used`, `d6_exhausted`, `d6_stress_share`. Actual source file is `mod_o2_coping.csv`, O2_01-O2_18 and conditional follow-ups. Most core responses are 1 Yes, 2 No because not necessary, 3 prior action could not continue, 4 Not applicable, 5 Prefer not to say; O2_05/O2_06 have an F1_00a gate. Listed questions refer to the past 12 months. The O2 file is distinct from `mod_o1_shocks.csv`.

**Status:** DEC-24 says raw-only; no used/exhausted flags, counts or share are implemented. O2 fields are not in `mod_o1_shocks.csv`; the separate cleaned file `mod_o2_coping.csv` is the correct source.

**Overlap:** asset sales/debt/borrowing overlap D7; reduced food expenditure overlaps D2; coping responses overlap D5 exposure. O2 items represent different concepts and should not be collapsed without a specific protocol.

## D7 - Financial resilience and protective factors

**Candidates:** `d7_has_debt`, `d7_total_debt`, `d7_n_debt_sources`, `d7_hard_to_repay`, `d7_has_bank_account`, `d7_able_to_save`, `d7_n_income_sources`, `d7_debt_income_ratio`.

N1_00 questionnaire codes are 1 No/2 Yes, while cleaned `n1_0` is 0/1 with direction unverified. N1_03 asks the loan amount taken by institution; wording does not establish current outstanding balance. Among 2,947 cleaned debt-positive households, 11 have all 13 amount slots blank; 12 have no positive sum of raw amount slots. N2_01 is the bank-account question (1 No/2 Yes), not N2_02, which asks where savings are deposited. N2_05 and N3_05 ask ability to save during the last 12 months, but cleaned values are 0/1 and paired forms disagree for 1,453 of 5,393 households.

**Status:** DEC-25 keeps debt-status/repayment and savings items raw only; N2/N3 remain form-specific. Debt totals, source counts, ratios and cross-form combinations are deferred. `d7_n_income_sources` is unsupported by an explicit item list. No D7 feature is generated.

**Overlap:** debt and savings capacity may overlap with D6 coping; account/savings variables may overlap with D1 material assets; debt/income ratio reuses H1_17 from D1.

## Cross-domain review gates

1. The 6,847-key master is approved only provisionally; the 6,850 published count needs sample disposition evidence (DEC-15).
2. The bottom-quintile consumption label is descriptive sensitivity only, never official eligibility, ground truth, a training target or model feature (DEC-13).
3. Household-level features should be created only after each raw module is independently reduced to one row per household and the key/count invariant is tested.
4. A verified candidate or validation approval does not approve final inclusion. No weights, thresholds, fuzzy memberships, Bayesian dependencies, rankings or eligibility results were created.
