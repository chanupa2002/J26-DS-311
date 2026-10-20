# Codebook cross-check for Component 1 inputs (v0.1)

Source: Codebook.zip (BRIGHT cleaned-data codebook). The codebook is the authority for the
cleaned data. Where it differs from the questionnaire, the codebook wins for that variable only.

## Variables where the cleaned data DIFFERS from the questionnaire
| Variable | Questionnaire | Codebook (cleaned data) | Action |
|---|---|---|---|
| c1_10 (toilet shared) | 1 = No, 2 = Yes | 0 = no, 1 = yes | Decision D-04b. Any other value = unknown. |
| d_12 to d_16 (binary assets) | 1 = No, 2 = Yes | 0 = no, 1 = yes | Owned = 1 when value is 1. Closes open question 4. |
| b0_02 (sex), b0_01a, b0_01b | not used | 0/1 coding | Not model inputs. |

## Variables CONFIRMED unchanged (match the questionnaire and the pipeline)
| Variable | Codebook values |
|---|---|
| l1_01 to l1_08, l2_01 to l2_08 (FIES) | 1 Yes, 2 No, 3 Don't know, 4 Refused |
| c1_04 walls | 1 Brick, 2 Cement block, 3 Stone, 4 Cabook, 5 Clay, 6 Cadjan/Palmyrah, 7 Wood, 8 Asbestos, 9 Cloth, 10 Polythene, 11 Metal sheet/Takaran, 999 Other |
| c1_05 floor | 1 Cement, 2 Terrazzo/Tile/Granite, 3 Mud, 4 Wood, 5 Sand, 6 Concrete, 7 Metal, 999 Other |
| c1_06 roof | 1 Tile, 2 Asbestos, 3 Concrete, 4 Metal sheet, 5 Takaran, 6 Cadjan/Palmyrah/Straw, 7 Polythene, 999 Other |
| c1_07 tenure | 1-3 Owned, 4 Rented, 5 Gift, 6 Rent free, 7 Encroached, 8 Temporary, 999 Other |
| c1_08 toilet | 1-14 as in the questionnaire, 999 Other, specify (so the 22 coded 999 are real "Other" answers) |
| c1_02 | Number of bedrooms, open-ended numeric |
| c1_03 | 8 floor-area bands |
| h1_17 | Total monthly household income, open-ended numeric, no special codes listed |
| b0_04_years | Age in years, open-ended |

## New points the codebook raises (need a researcher decision, not a guess)
1. **Asset items are 18, not 23.** Asset items: d_01, d_03, d_05, d_06, d_08, d_10 (counts);
   d_12 to d_16 (yes/no); d_17 to d_23 (counts). d_02 and d_04 do not exist. d_07, d_09, d_11 are
   "who uses the device" multi-selects (d_07_0 ... d_07_20) and must NOT be counted as assets.
   The follow-ups d_12a-c, d_15a-c, d_20a-c to d_23a-c (age, price, resale value) are not ownership items.
2. **Variable name is hh_type (Type 1/2/3), not hhtype.** The codebook gives no meaning for the types.
   The A1 check (hh_type vs FIES form answered) should use this name, and the meaning of the types
   still has to come from the data owner.
3. **Roster membership flags.** b0_01a (lived in the household at least 6 months) and b0_01b (ate from
   the same pot in the past 7 days) exist. Decide whether roster_member_count and the age counts
   include all listed members or only those meeting these flags. Not yet decided in D-07 / D-06.
4. **Toilet code 5 and 10 mapping** (JMP class) is still unconfirmed; the codebook gives labels
   but no JMP class. Check against the JMP definitions.
5. **hhweight** (household weight) exists. Stage 4 distributions are unweighted unless stated.
