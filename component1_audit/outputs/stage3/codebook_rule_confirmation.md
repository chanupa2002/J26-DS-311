Research output - not an eligibility determination

# Codebook rule confirmation

| Rule checked | Applied in rebuild | Authoritative crosscheck |
|---|---|---|
| C1_10 toilet sharing | 0 = not shared; 1 = shared; any other value unknown | `codebook_crosscheck_v0_1.md`, line 9 |
| d_12-d_16 binary assets | 0 = no; 1 = yes; owned when 1 | `codebook_crosscheck_v0_1.md`, line 10 |
| Asset inventory | Exactly 18 direct items; d_07/d_09/d_11 and all listed follow-ups excluded | `codebook_crosscheck_v0_1.md`, lines 29-31 |
| FIES | 1 = Yes; 2 = No; 3/4 = missing for scoring | `codebook_crosscheck_v0_1.md`, line 16 |
| FIES form cross-tab key | `hh_type` (not `hhtype`) | `codebook_crosscheck_v0_1.md`, line 32 |

No conflict was found between these crosscheck rules and the corresponding Stage 3 handling. The decision log retains an old follow-up reference to `hhtype`; the authoritative crosscheck and rebuilt table use `hh_type`.
