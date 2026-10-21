# Stage 5 O1 / exposure audit

Research output - not an eligibility determination

## Score derivation and baseline handling

- `component1_audit/outputs/stage4b/build_stage4b_v0_2.py:85-86` sets `mu_shock` from Stage 3b `o1_mean_severity` after numeric parsing. Stage 3b `build_stage3b.py:62-66` maps valid O1 codes 1→1 (severe), 2→0.5 (moderate), 3→0 (none), then averages valid responses; all invalid/blank means unknown. The item count is retained in `n_o1_items_valid`.
- `component1_audit/outputs/stage4b/build_stage4b_v0_2.py:98-99` sets `dom_exposure = mu_shock`, with `n_used = n_o1_items_valid` and `n_total = 20`.
- Stage 5 baseline excludes the exposure leaf as required. Exposure is used only in the UNAPPROVED `include_exposure` sensitivity.
- The past-12-month reference period for all 20 items follows the researcher assumption; questionnaire printed page 203 explicitly states this period only for O1_01_20.

## Per-item blank rates

| item | blank_n | blank_rate | valid_n | out_of_set_n |
| --- | --- | --- | --- | --- |
| o1_01_1 | 0 | 0.000% | 6847 | 0 |
| o1_01_2 | 0 | 0.000% | 6847 | 0 |
| o1_01_3 | 0 | 0.000% | 6847 | 0 |
| o1_01_4 | 0 | 0.000% | 6847 | 0 |
| o1_01_5 | 0 | 0.000% | 6847 | 0 |
| o1_01_6 | 0 | 0.000% | 6847 | 0 |
| o1_01_7 | 0 | 0.000% | 6847 | 0 |
| o1_01_8 | 0 | 0.000% | 6847 | 0 |
| o1_01_9 | 0 | 0.000% | 6847 | 0 |
| o1_01_10 | 0 | 0.000% | 6847 | 0 |
| o1_01_11 | 3185 | 46.517% | 3662 | 0 |
| o1_01_12 | 3185 | 46.517% | 3662 | 0 |
| o1_01_13 | 3185 | 46.517% | 3662 | 0 |
| o1_01_14 | 5981 | 87.352% | 866 | 0 |
| o1_01_15 | 6615 | 96.612% | 232 | 0 |
| o1_01_16 | 3185 | 46.517% | 3662 | 0 |
| o1_01_17 | 3185 | 46.517% | 3662 | 0 |
| o1_01_18 | 3167 | 46.254% | 3680 | 0 |
| o1_01_19 | 0 | 0.000% | 6847 | 0 |
| o1_01_20 | 0 | 0.000% | 6847 | 0 |

## Most common blank patterns

| blank_items | households_n |
| --- | --- |
| o1_01_14,o1_01_15 | 3162 |
| o1_01_11,o1_01_12,o1_01_13,o1_01_14,o1_01_15,o1_01_16,o1_01_17,o1_01_18 | 2637 |
| o1_01_15 | 429 |
| o1_01_11,o1_01_12,o1_01_13,o1_01_15,o1_01_16,o1_01_17,o1_01_18 | 369 |
| o1_01_11,o1_01_12,o1_01_13,o1_01_14,o1_01_16,o1_01_17,o1_01_18 | 119 |
| o1_01_14 | 45 |
| o1_01_11,o1_01_12,o1_01_13,o1_01_16,o1_01_17,o1_01_18 | 42 |
| [no blanks] | 26 |
| o1_01_11,o1_01_12,o1_01_13,o1_01_14,o1_01_15,o1_01_16,o1_01_17 | 18 |

## Questionnaire skip-logic check

The English questionnaire, printed page 202, conditions O1_01_11–13, 16, and 17 on F1_00a=1; O1_01_14 on G1_00a=1; O1_01_15 on G2_00=1; and O1_01_18 on F1_00a=1 or I_01=1. Items 1–10, 19, and 20 have no skip condition printed on pages 201–203. The cleaned codebook crosscheck does not state O1 routing rules, so this check uses the questionnaire.

| item | eligibility_rule | eligible_n | eligible_blank_n | eligible_answered_n | ineligible_n | ineligible_blank_n | ineligible_answered_n | eligibility_unknown_n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| o1_01_11 | f1_00a == 1 | 3642 | 0 | 3642 | 3205 | 3185 | 20 | 0 |
| o1_01_12 | f1_00a == 1 | 3642 | 0 | 3642 | 3205 | 3185 | 20 | 0 |
| o1_01_13 | f1_00a == 1 | 3642 | 0 | 3642 | 3205 | 3185 | 20 | 0 |
| o1_01_14 | g1_00a == 1 | 866 | 0 | 866 | 5981 | 5981 | 0 | 0 |
| o1_01_15 | g2_00 == 1 | 232 | 0 | 232 | 6615 | 6615 | 0 | 0 |
| o1_01_16 | f1_00a == 1 | 3642 | 0 | 3642 | 3205 | 3185 | 20 | 0 |
| o1_01_17 | f1_00a == 1 | 3642 | 0 | 3642 | 3205 | 3185 | 20 | 0 |
| o1_01_18 | f1_00a == 1 OR i_01 == 1 | 3727 | 66 | 3661 | 3120 | 3101 | 19 | 0 |

The 5 F1-routed items (11–13, 16–17) have no blanks among 3,642 eligible households. Among 3,205 ineligible households, 3,185 have the expected blanks; 20 have answers despite the skip condition. Items 14 and 15 match their skip flags exactly (respectively 5,981 and 6,615 ineligible blanks; no eligible blanks). Item 18 has 66 blanks among 3,727 eligible households and 19 answers among 3,120 known-ineligible households. The pattern is mostly consistent with structured skips, with exceptions; it is not evidence that the remaining blanks are random.
- Stage 4 carried-item blank patterns match the raw O1 source blank patterns: 0 discrepant item-household blank statuses across 20 items.

## Exposure coverage

| n_used | households_n | n_total |
| --- | --- | --- |
| 12 | 2637 | 20 |
| 13 | 506 | 20 |
| 14 | 42 | 20 |
| 18 | 3162 | 20 |
| 19 | 474 | 20 |
| 20 | 26 | 20 |

Questionnaire source: `Data/BRIGHT_questionnaire_English.pdf`, printed pages 201–203. The inspected skip conditions are on printed page 202.
