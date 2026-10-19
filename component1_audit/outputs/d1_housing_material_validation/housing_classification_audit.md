# D1 housing material classification validation audit

**Status:** read-only validation for researcher review. No deprivation coding, score, or model feature is implemented.

## Inputs inspected

- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf, PDF pp.14-15 (printed pp.14-15)`. It identifies C1_04 as walls, C1_05 as flooring, and C1_06 as roof; the cleaned field order agrees.
- Household master: `Data/bright_csv/mod_a_household_identification.csv`, key `hhcode` (6,847 rows).
- Cleaned module: `Data/processed/clean/mod_c_housing.csv`; columns `hhcode`, `c1_04`, `c1_04_other`, `c1_05`, `c1_05_other`, `c1_06`, `c1_06_other`.
- Census reference: [Department of Census and Statistics, Census of Population and Housing 2024, Final Report (English), section 11.5 ‘Status of housing unit’, printed p.189, table captioned ‘Basis for classifying status of housing units as permanent, semi-permanent, and improvised’](https://www.statistics.gov.lk/Resource/en/Population/CPH_2024/CPH2024_Final_Eng.pdf).

## Verified Census source rules

Section 11.5, printed page 189, Table “Basis for classifying status of housing units as permanent, semi-permanent, and improvised” gives ten rows: two permanent combinations, six semi-permanent combinations, and two improvised combinations. They are transcribed in the script's `RULES` list and evaluated without inferring equivalence. Permanent row 1 is durable listed walls + durable listed roof + listed finished floor; permanent row 2 is mud/warichchi walls + tile/asbestos/zinc aluminium/metal sheet roof + cement/concrete floor. Semi-permanent rows separately enumerate durable walls with durable roof and mud/wood/sand floor; durable walls with leaf/straw/other roof and the listed floors; analogous mud-wall combinations; and plank/metal-sheet wall combinations. Improvised is leaf/palmyrah/straw walls with any roof and floor, or plank/metal-sheet/asbestos/zinc-aluminium walls with leaf/straw roof and mud/wood/sand floor. The source does not supply a generic hierarchy or fallback for combinations outside these rows.

## Item crosswalk findings

The CSV contains every observed code including missing, frequency and denominator. Exact matches are only assigned where the BRIGHT label directly matches a Census material. Approximate mappings (wall Cadjan/Palmyrah; wall Metal sheet/Takaran; roof Metal sheet and Takaran) are retained as approximate and excluded from deterministic combined classifications. BRIGHT Clay is unresolved against the Census wording Mud/warichchi. BRIGHT wall Wood/Asbestos/Cloth/Polythene, floor Metal, and roof Polythene are unmatched to the rule's material families. “Other” code 999 and its free-text entries stay unresolved. Missing is separately recorded, never treated as a material.

## Combination feasibility and descriptive comparison

There are 6,846 households with all three material responses present. Of these, 30 (0.44% of the master) match exactly one published combination row using only exact item mappings; see the feasibility CSV for every observed triad and limitation. No classification has been written back to source data. Frequencies in the frequency report show item-response denominators and all-master denominators explicitly.

## Checks executed

- Household key `hhcode`: unique and nonmissing in master and housing module.
- Module keys are a subset of the household master; one-to-one `hhcode` merge validated.
- Join preserved master row count and key order (6,847); all master records matched the housing module.
- Item missingness, observed category coverage and response counts were calculated from cleaned module. Original BRIGHT responses were only read.
- No household identifiers or row-level records are included in outputs.

## Limitations and decisions for researcher

- Local files did not include the Census report; official online DCS final report was used.
- Census labels/categories are not fully equivalent to several BRIGHT options. Census material “Wood (finished)” is narrower than BRIGHT “Wood”; floor BRIGHT Teraso/Tile/Granite groups items across Census subcategories, which matters for rules specifying finished wood/titanium/concrete. Accordingly, status counts are conservative and may understate feasibility.
- The report's extracted text presents no explicit precedence rule for any overlap or status for unlisted combinations. No gap filling or assumed hierarchy was used.
- “Other” text was counted for distinct nonblank strings only, not reproduced, to avoid sharing respondent-provided text. Individual other text was not mapped.
- These artifacts validate the crosswalk only. Researcher approval is still needed before deprivation coding, indicator inclusion, fuzzy membership, weights, or model implementation.
