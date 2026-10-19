# Toilet service coverage diagnosis (updated after D-04b)

## Findings

- `c1_08` has the same distribution in `Data/processed/clean/mod_c_housing.csv` and the Stage 3 table; both have 6,847 unique household rows and zero blank `c1_08` values. There are 22 code-999 cases.
- `c1_10` has values 0 for 6,170 households and 1 for 677 households, with no blanks, in the raw `Data/bright_csv/mod_c_housing.csv`, cleaned housing file, and Stage 3 table. The researcher-provided cleaned-file codebook for D-04b specifies 0 = not shared and 1 = shared; this overrides the questionnaire's 1 = No, 2 = Yes convention for C1_10 only.
- The join preserves all 6,847 nonmissing unique `hhcode` keys. Cleaned housing and Stage 3 key sets match, and `c1_08`/`c1_10` values match by key. This is not a join-loss problem.
- `toilet_type_class` by observed `c1_10`: improved has 6,028 with code 0 and 623 with code 1; unimproved has 117 with code 0 and 14 with code 1; open defecation has 22 with code 0 and 21 with code 1; unknown has 3 with code 0 and 19 with code 1.
- After the D-04b correction, `toilet_service_class` by type: 6,028 improved cases are basic; 623 improved cases are limited; 131 cases are unimproved; 43 are open_defecation; and 22 unknown toilet types remain unknown. Thus `mu_toilet` is observed for 6,825 households.

## Cause and disposition

**Cause was (iv, other): the raw-file code convention differed from the questionnaire and there was no join loss; the researcher-provided D-04b codebook now resolves the discrepancy for this cleaned file.** The mapping 0 = not shared and 1 = shared is applied only to C1_10. Any other or missing C1_10 value is unknown. C1_08 `toilet_type_class` is unchanged.

The full aggregate counts and cross-tabs are in `toilet_diagnosis.csv`. No household identifiers or raw respondent text are included.

## Rerun status

The Stage 3 rebuild completed after the Excel lock was released. Stage 4 is rebuilt from that Stage 3 table. D-04b changes only C1_10 interpretation; all other approved rules and defaults remain unchanged.
