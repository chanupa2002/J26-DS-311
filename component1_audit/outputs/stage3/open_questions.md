# Stage 3 open questions

These items are stopped or explicitly scoped pending evidence; other unambiguous engineering steps may proceed.

1. **DCS material durability:** no DCS 2024 classification table/report is present in the repository file set. The prior D1 audit cites an external DCS report, but this stage is instructed to use a local table only. Material lookup durability cells therefore remain blank and all derived durability values are `unknown` until researcher completion.

2. **C1_08 free text:** among 22 households coded 999, 22 have nonblank text and 13 distinct values; across all codes, 24 records have nonblank Other text and 15 distinct values. Raw text is withheld under the hard privacy rule. Checks contain redacted category IDs and frequencies only; no ID-to-text map is written.

3. **FIES both/neither forms:** `fies_valid_items_n` is not form-specific for both-form or no-form households. To avoid combining or selecting forms, that field remains blank in those cases; raw items remain separate. No score is created for both forms.

4. **Asset code mismatch:** d_12-d_16 are registered as 1=No/2=Yes, but the cleaned data contain 0/1. Ownership derivation for these five items is stopped: their owned flags remain blank pending the source-to-clean recode crosswalk. Do not infer that 0/1 direction from common coding practice.

5. **Age sensitivity ratios:** age counts use the years field and requested bands. Sensitivity ratios use the literal bands in their names: youth / observed working-age 15-64, old-age 65+ / 15-64, and (under15 + 60+)/15-59. Households with no observed working-age member have blank ratios and flag=1 as specified; if ages are missing, the flag reflects absence of an observed in-band member, not verified absence of such a person.

6. **C1_08 proposed codes 5 and 10:** the supplied sanitation mapping is applied as proposed for traceable output, but lookup `mapping_confirmed` is FALSE for these codes and their classes must not be treated as confirmed.

7. **Stage 3 decision-log file:** the expected named `Spec v0.1 and Decision Log` was not found as a standalone repository file. This build follows the approved rules supplied in the task and the available approval/decision registers; no absent rule is inferred.
