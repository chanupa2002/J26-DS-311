# Stage 3 open questions

These items are stopped or explicitly scoped pending evidence; other unambiguous engineering steps may proceed.

1. **C1_08 free text:** among 22 households coded 999, 22 have nonblank text and 13 distinct values; across all codes, 24 records have nonblank Other text and 15 distinct values. Raw text is withheld under the hard privacy rule. Checks contain redacted category IDs and frequencies only; no ID-to-text map is written.

2. **FIES both/neither forms:** `fies_valid_items_n` is not form-specific for both-form or no-form households. To avoid combining or selecting forms, that field remains blank in those cases; raw items remain separate. No score is created for both forms.

3. **Codebook cross-check:** `component1_audit/docs/codebook_crosscheck_v0_1.md` is authoritative for the cleaned-file codes and agrees with the current handling of C1_10, d_12-d_16, the 18-item asset set, FIES codes, and `hh_type`. d_12-d_16 use 0=No, 1=Yes, owned=1; this recoding applies only to these five assets.

4. **Roster flag rules:** the codebook defines b0_01a as lived in the household at least 6 months and b0_01b as ate from the same pot in the past 7 days, but does not decide whether either flag changes roster_member_count or age counts. Checks/A8 reports the requested flag=0 counterfactual only; no flag exclusion is applied.

5. **Age sensitivity ratios:** age counts use the years field and requested bands. Sensitivity ratios use the literal bands in their names: youth / observed working-age 15-64, old-age 65+ / 15-64, and (under15 + 60+)/15-59. Households with no observed working-age member have blank ratios and flag=1 as specified; if ages are missing, the flag reflects absence of an observed in-band member, not verified absence of such a person.

6. **C1_08 proposed codes 5 and 10:** the supplied sanitation mapping is applied as proposed for traceable output, but lookup `mapping_confirmed` is FALSE for these codes and their classes must not be treated as confirmed.

7. **D-04b correction:** the researcher-provided cleaned-file codebook overrides the questionnaire's 1=No/2=Yes convention for C1_10 only: 0=not shared and 1=shared; other/missing=unknown. Stage 3 applies this mapping only to C1_10. C1_08 type classes are unchanged.

8. **Decision log:** `component1_audit/docs/spec_v0_1_decision_log.md` is included as an input. The codebook cross-check confirms cleaned-file meanings; it does not change the other approved rules.
