# D5 shocks and D6 coping period/applicability audit

## D5 O1 shocks

Questionnaire PDF pp.201–203 lists O1_01_1–20. Codes are 1 Yes, severe impact; 2 Yes, moderate impact; 3 No, no impact. Items 1–19 have no explicit common reference period in the item table; item 20 explicitly asks whether another shock adversely affected household economic status in the past 12 months (p.203). A shared period for items 1–19 was not verified. No count/severity/combined exposure feature was produced.

Item-level counts below use all 6,847 household module records; 3 is explicit no impact and blank is not interpreted as no. For gated items, applicability diagnostics follow the printed rules.

| Item | Code 1 severe | Code 2 moderate | Code 3 no impact | Blank |
| --- | --- | --- | --- | --- |
| o1_01_1 | 4369 | 2197 | 281 | 0 |
| o1_01_2 | 3245 | 2134 | 1468 | 0 |
| o1_01_3 | 2054 | 1949 | 2844 | 0 |
| o1_01_4 | 1820 | 1161 | 3866 | 0 |
| o1_01_5 | 3866 | 2323 | 658 | 0 |
| o1_01_6 | 2286 | 1915 | 2646 | 0 |
| o1_01_7 | 1743 | 1442 | 3662 | 0 |
| o1_01_8 | 290 | 254 | 6303 | 0 |
| o1_01_9 | 1009 | 900 | 4938 | 0 |
| o1_01_10 | 159 | 194 | 6494 | 0 |
| o1_01_11 | 318 | 713 | 2631 | 3185 |
| o1_01_12 | 236 | 592 | 2834 | 3185 |
| o1_01_13 | 376 | 654 | 2632 | 3185 |
| o1_01_14 | 100 | 99 | 667 | 5981 |
| o1_01_15 | 127 | 69 | 36 | 6615 |
| o1_01_16 | 247 | 468 | 2947 | 3185 |
| o1_01_17 | 153 | 312 | 3197 | 3185 |
| o1_01_18 | 119 | 362 | 3199 | 3167 |
| o1_01_19 | 237 | 357 | 6253 | 0 |
| o1_01_20 | 160 | 287 | 6400 | 0 |

| Gate | Gate yes | Gate no | Gate missing | Eligible item blanks | Nonapplicable item nonblanks |
|---|---:|---:|---:|---:|---:|
| F1 agriculture | 3642 | 3205 | 0 | 0 | 100 |
| G1 livestock | 866 | 5981 | 0 | 0 | 0 |
| G2 fishing | 232 | 6615 | 0 | 0 | 0 |
| F1 agriculture OR I nonfarm business | 3727 | 3120 | 0 | 66 | 19 |

O1_11–13 and O1_16–17 are gated by F1_00a=1; O1_14 by G1_00a=1; O1_15 by G2_00=1; O1_18 by F1_00a=1 **or** I_01=1. Gate values other than 1 are not automatically assumed to mean nonapplicable unless explicitly observed as No; missing gates remain unknown. F3 Maha 2023–24 and F7 Maha 2024–25 are separate agricultural seasons and must stay separate. The script inspected each module’s household-key uniqueness and master subset; no season was selected.

## D6 O2 coping

Questionnaire PDF pp.203–208: O2 items concern coping with lack of food or money during the past 12 months. Core response categories: 1 Yes; 2 No because unnecessary; 3 No because action had already been taken before the last 12 months and could not continue; 4 Not applicable; 5 Prefer not to say. O2_05 and O2_06 are gated by F1_00a=1; follow-up multi-selects O2_02, O2_04, O2_10a and O2_11a follow Yes answers. The clean O2 file is a distinct module from O1.

The single-select coping items are profiled separately from follow-up selections. O2_02, O2_04, O2_10a and O2_11a are conditional multi-select follow-ups, not five-level core response items; expanded flags are counted below without copying free text. Core item counts use denominator 6,847 household records; blanks shown separately:

| Item | 1 Yes | 2 No/unnecessary | 3 Discontinued | 4 N/A | 5 PNS | Blank |
| --- | --- | --- | --- | --- | --- | --- |
| o2_01 | 604 | 6009 | 64 | 165 | 0 | 5 |
| o2_03 | 2931 | 3707 | 100 | 105 | 0 | 4 |
| o2_05 | 18 | 615 | 2 | 81 | 0 | 6131 |
| o2_06 | 40 | 588 | 0 | 88 | 0 | 6131 |
| o2_07 | 1652 | 4919 | 24 | 243 | 0 | 9 |
| o2_08 | 2264 | 4434 | 33 | 108 | 0 | 8 |
| o2_09 | 1952 | 4723 | 51 | 118 | 0 | 3 |
| o2_10 | 3459 | 3209 | 73 | 97 | 0 | 9 |
| o2_11 | 3041 | 3628 | 72 | 100 | 0 | 6 |
| o2_12 | 1631 | 5095 | 10 | 104 | 0 | 7 |
| o2_13 | 119 | 6527 | 24 | 173 | 0 | 4 |
| o2_14 | 22 | 6621 | 10 | 192 | 0 | 2 |
| o2_15 | 698 | 5476 | 5 | 666 | 0 | 2 |
| o2_16 | 130 | 6305 | 5 | 404 | 0 | 3 |
| o2_17 | 352 | 6242 | 20 | 226 | 0 | 7 |
| o2_18 | 780 | 5839 | 24 | 187 | 0 | 17 |

O2_17a frequency:

| Item | 1 Yes | 2 No/unnecessary | 3 Discontinued | 4 N/A | 5 PNS | Blank |
| --- | --- | --- | --- | --- | --- | --- |
| o2_17a | 298 | 6297 | 24 | 218 | 0 | 10 |

Follow-up selection flags (number selected; respondent free text excluded):

| Field | Flag=1 count | Flag=0 count | Missing |
| --- | --- | --- | --- |
| o2_02_1 | 356 | 248 | 6243 |
| o2_02_2 | 50 | 554 | 6243 |
| o2_02_3 | 24 | 580 | 6243 |
| o2_02_4 | 46 | 558 | 6243 |
| o2_02_5 | 111 | 493 | 6243 |
| o2_02_6 | 7 | 597 | 6243 |
| o2_02_7 | 16 | 588 | 6243 |
| o2_02_8 | 30 | 574 | 6243 |
| o2_02_9 | 4 | 600 | 6243 |
| o2_02_999 | 11 | 593 | 6243 |
| o2_04_1 | 2869 | 62 | 3916 |
| o2_04_2 | 18 | 2913 | 3916 |
| o2_04_3 | 20 | 2911 | 3916 |
| o2_04_4 | 41 | 2890 | 3916 |
| o2_04_5 | 39 | 2892 | 3916 |
| o2_04_6 | 4 | 2927 | 3916 |
| o2_04_7 | 2 | 2929 | 3916 |
| o2_04_8 | 0 | 2931 | 3916 |
| o2_04_9 | 0 | 2931 | 3916 |
| o2_04_999 | 3 | 2928 | 3916 |
| o2_10a_1 | 277 | 3182 | 3388 |
| o2_10a_2 | 575 | 2884 | 3388 |
| o2_10a_3 | 714 | 2745 | 3388 |
| o2_10a_4 | 1040 | 2419 | 3388 |
| o2_10a_5 | 676 | 2783 | 3388 |
| o2_10a_6 | 228 | 3231 | 3388 |
| o2_10a_7 | 490 | 2969 | 3388 |
| o2_10a_8 | 217 | 3242 | 3388 |
| o2_10a_9 | 784 | 2675 | 3388 |
| o2_10a_10 | 1358 | 2101 | 3388 |
| o2_10a_11 | 686 | 2773 | 3388 |
| o2_10a_12 | 2946 | 513 | 3388 |
| o2_10a_13 | 2542 | 917 | 3388 |
| o2_10a_14 | 2126 | 1333 | 3388 |
| o2_10a_15 | 1899 | 1560 | 3388 |
| o2_10a_16 | 924 | 2535 | 3388 |
| o2_11a_1 | 761 | 2280 | 3806 |
| o2_11a_2 | 826 | 2215 | 3806 |
| o2_11a_3 | 1326 | 1715 | 3806 |
| o2_11a_4 | 1581 | 1460 | 3806 |
| o2_11a_5 | 2460 | 581 | 3806 |
| o2_11a_6 | 1627 | 1414 | 3806 |
| o2_11a_7 | 1860 | 1181 | 3806 |
| o2_11a_8 | 1684 | 1357 | 3806 |
| o2_11a_9 | 1062 | 1979 | 3806 |
| o2_11a_10 | 911 | 2130 | 3806 |
| o2_11a_11 | 744 | 2297 | 3806 |
| o2_11a_12 | 1281 | 1760 | 3806 |

O2 agriculture gate: {'gate_yes': 3642, 'gate_no': 3205, 'gate_missing': 0, 'o2_05_blank_when_gate_yes': 2934, 'o2_06_blank_when_gate_yes': 2934, 'o2_05_nonblank_when_gate_no': 8, 'o2_06_nonblank_when_gate_no': 8}. These are separate counts of gate yes/no/missing and item blanks among gate-yes; gate-no values and item missingness are not collapsed into response categories. For unconditional items, a blank remains response missing unless the source instrument establishes another rule.

## Measurement implications and choices

- Missing, not applicable, explicit no-impact/no-need and prefer-not-to-say represent different states; collapsing them changes the construct and denominator.
- D5 O1_04 employment/income loss is conceptually related to H1_05 unemployment, but O1_1–19 period is unspecified and H1_05 covers the last 12 months. O1_20 has a 12-month frame. Temporal equivalence is unproven.
- O1_07 serious illness/death/injury may overlap with B3 conditions, but O1 is household shock impact and B3 is member condition/activity interruption. Units and periods differ.
- D2 food access and O2 food/money coping both refer to the past 12 months; related time window does not make experiences and coping actions interchangeable.
- Candidate options for review: keep O1/O2 items separately; build a period-specific subset after confirming periods and gates; or defer an item whose universe/period cannot be established. Do not compute shock or coping counts, severity scores, flags, proportions or features now.
