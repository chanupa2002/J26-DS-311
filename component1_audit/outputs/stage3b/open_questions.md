# Open questions

Research output - not an eligibility determination

- Codebook.zip was not found at the project root or under the project; requested cleaned-module codebook source rows could not be checked. Counts therefore show observed values, with unverified sets labeled accordingly.
- N1 n1_0 and N2 n2_01 use the task-provided 1=yes/0=no mappings; Codebook.zip was unavailable to independently verify the source row. The older domain_review note marks N1 direction unverified; the explicit mapping in this task was used and should be confirmed against the cleaned codebook when available.
- B3 b3_01 by b3_03 is a descriptive skip-conflict check only. b3_03 and b3_04 are not used in derived columns.
- O1 reference period: O1_01_20 states "in the past 12 months" (Data/BRIGHT_questionnaire_English.pdf, printed page 203). No common reference period is stated for O1_01_1 through O1_01_19 in the reviewed item table (printed pages 201-203). Supplied PDF SHA-256 matches the project copy: 466f554d464dde004cc13318771030c36c87b1839460f7f8b27392f7a588d4dc. No O1 composite is constructed (ISS-11).
- L3 task lists l3_01..09 and frequency items but does not identify frequency item numbers or skip conditions; no activity-based skip interpretation is made without codebook/questionnaire mapping.
- O2 code categories and same-coding lead-item scope require the cleaned Codebook.zip; checks show observed raw values/counts only, and no derived O2 column is created.
- Stage 3b implementation and tests are placed under outputs/stage3b to honor the prohibition on modifying pre-existing Stage 3/4 files; no prior pipeline/test file was changed.
