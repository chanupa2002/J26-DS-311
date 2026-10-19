# Consolidated D1-D7 measurement review

## Purpose and scope

This consolidates the existing D1 housing/material audit, D1-D7 registry/validation artifacts, and the D2-D7 resolution audit into a candidate measurement register. It is a measurement review only. It does not define an indicator, recode source responses, impute missing values, aggregate household-level candidates, assign weights, create fuzzy memberships/Bayesian dependencies, rank households or make eligibility decisions.

The register contains 43 inherited candidate names from `component1_audit/outputs/indicator_registry_review.csv`. These are proposals, not validated or approved final features. Previously recorded approval statuses are reproduced with their explicit scope limits.

## Evidence by domain

- **D1 housing, assets and income:** the housing audit reports 30 of 6,847 households (0.44%) matching one published DCS 2024 wall-roof-floor class under exact audited material mappings. Individual C1 material responses remain the defensible evidence; unmatched combinations are not assigned classes. C1_08 has a 999 discrepancy. H1_17 is addressed below.
- **D2 food access:** 39 missing and three fractional `d2_fies_raw` values (0.5, 1.5, 2.5) were reproduced in the resolution audit. L1/L2 item fields matched their export counterparts after unique-key joins. The derivation remains unreproducible; forms stay separate.
- **D3 household needs:** B3 has 27,021 members, all within B0; 854 roster members across 677 households lack B3 records. B3_01 code/skip conflict remains. Age years/months stay separate; no threshold or household summary is approved.
- **D4 livelihood/income:** H1/H2 key sets match. H1_17 has 6,663 multi-record households; 5,328 with one consistent nonmissing answer; zero conflicts; 1,519 with none. Do not sum repeated household income. H2_02 to clean `h1_02` mapping remains unresolved.
- **D5 shocks:** O1 code states and item gates are preserved. The common period for items 1-19 is unverified; item 20 specifies 12 months. No shock count or severity measure is approved.
- **D6 coping:** O2 retains five different response states and conditional follow-ups. No used/exhausted flag, count or share is approved.
- **D7 debt/savings:** latest key-aligned check has 31 prepared zero totals among 2,947 `n1_0=1`; 11 with all 13 raw amount slots blank and 12 with no positive raw slot. Historical 20 prepared-zero claim remains unreconciled: the prior validation script did not calculate prepared-zero counts and no underlying 20-case predicate is in the reviewed artifacts. N1_03 is amount taken, not confirmed current debt. N2/N3 differ in 1,453 of 5,393 paired nonmissing responses and remain separate.

## Cross-domain measurement risks

Eight overlap pairs are documented in `cross_domain_overlap_register.csv`: D1 income-D4 livelihood; D1 housing/D3 household size and needs; D1 assets-D6/D7; D2 food access-D6 coping; D3 health-D5 health shocks; D4 employment-D5 shocks; D6 coping-D7 finance; and D1 housing-D5 shocks. These are conceptual or temporal overlaps, not proof of causal relationships or redundancy. No candidate is removed because it may correlate with another.

## Decisions and limits

Blocking semantic decisions include D1 exact material mapping/Other codes; D2 respondent and score protocol; D3 B3 code/skip and time categories; D4 H2 mapping and H1_17 handling; D5 periods/gates; D6 category treatment; and D7 direction, current-balance meaning and N2/N3 respondent rules. Household aggregation additionally needs approved age, member, income, asset and missingness denominators. Model construction remains blocked pending those decisions and later explicit construct/overlap review.

The bottom-quintile consumption proxy remains separate and is not ground truth, eligibility, a training target or a core candidate indicator. Existing decision DEC-13 limits it to separate descriptive sensitivity.

Urgency-grouped options and consequences of deferral are in `researcher_decisions_required.md`; issue-level alternatives and tradeoffs are in `unresolved_measurement_issues.csv`.
