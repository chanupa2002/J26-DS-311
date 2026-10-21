# Stage 4b summary

Research output - not an eligibility determination


- Read-only diagnostic inputs: 6,847 unique Stage 3 households and 6,847 existing Stage 4 score rows. Proxy fields were excluded.
- No existing Stage 3/Stage 4 file, rule, default, or score was changed. No imputation or score ranking was added.

## FIES form diagnostic

Complete eight-item raw-score distributions (no form-pooling conclusion):

| hh_type | form | complete n | mean | median | SD | share at 0 | share at 8 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | L1_only | 2087 | 2.2276 | 1.0000 | 2.4928 | 0.4384 | 0.0297 |
| 1 | L2_only | 1996 | 2.5746 | 2.0000 | 2.6341 | 0.3828 | 0.0301 |
| 2 | L1_only | 600 | 2.1650 | 1.0000 | 2.5492 | 0.4683 | 0.0350 |
| 2 | L2_only | 672 | 2.6310 | 2.0000 | 2.6997 | 0.3884 | 0.0372 |

Mann-Whitney tests and rank-biserial effects (positive means L1 ranks tend higher):

| hh_type | L1 complete n | L2 complete n | U (L1) | two-sided p | rank-biserial |
|---:|---:|---:|---:|---:|---:|
| 1 | 2087 | 1996 | 1925944.5 | 1.50436e-05 | -0.075321 |
| 2 | 600 | 672 | 181457.0 | 0.00131781 | -0.099916 |

hh_type=3 L1-only context: 1,454 households; 1,446 complete eight-item scores. Per-item rates for all three hh_type groups are in `fies_item_endorsement_rates.csv`.

## Zero-bedroom sensitivity

c1_02=0: 55 households. Household-size distribution: size 2: 17, size 3: 14, size 4: 13, size 5: 5, size 6: 4, size 1: 2.
UNAPPROVED c1_02=0 to 1 bedroom: mu_crowding baseline known 0/55, sensitivity known 55/55, unknown-to-known 55; sensitivity mean 0.527273.
Housing degree for zero-bedroom households: mean change 0.059192, mean absolute change 0.098182; housing level changed for 12/55 (21.818182%).
Whole file: mu_crowding known 6792 -> 6847; 55 became known; mean absolute delta among 6792 comparable households 6.91e-19. Housing degree mean change 0.000475, mean absolute change 0.000789; housing level changed for 12/6847 (0.175259%).

## Sensitivity and dilution diagnostics

Existing sensitivity comparison extended with mean absolute soft-membership change across low/medium/high: 48 scenario-domain rows; 44 have a scored comparison. See `sensitivity_comparison_with_soft_mae.csv`.
UNAPPROVED dependency tie rescaling: ratio=0 households 1949; baseline lowest membership 0.152671; Spearman rho 1.000000; demographic level changed 224/6847 (3.271506%).
Housing dilution condition: 619/6847 (9.040456%). Max single-input membership: mean=0.267105; median=0.000000; p25=0.000000; p75=0.500000. Domain mean: mean=0.061521; median=0.000000; p25=0.000000; p75=0.083333. Weighted maximum was not run.

## Asset completeness diagnostic (D-10a)

Valid asset summaries: old MIN_VALID_ASSETS=None 6,847/6,847; D-10a all 18 valid 6,847/6,847.
Economic-domain n_used distributions before (existing Stage 4) and after D-10a are in `economic_n_used_before_after.csv`.
Under D-10a, economic domain entirely unknown (income and assets both unknown): 0/6847 households.
Economic-domain Spearman comparisons against D-10a baseline are in `asset_completeness_sensitivity_correlations.csv`; share-owned and minimum-15 are UNAPPROVED sensitivities. The share-owned option uses its own empirical reference distribution.

See the diagnostic CSVs for complete per-item rates, form counts, and binned housing distributions. No pooling conclusion or approved decision is made.

## Open questions

- The cleaned Codebook.zip is not part of the diagnostic inputs. FIES scoring follows existing Stage 3 D-01 complete-eight-item logic; this diagnostic reports observed valid/unknown counts and does not pool forms.
- The c1_02=0 to one-bedroom run is explicitly UNAPPROVED and diagnostic only; it does not alter Stage 3, Stage 4, or the frozen reference file.
- Dependency tie sensitivity is explicitly UNAPPROVED. Its linear rescaling maps the ratio=0 membership tie to 0 and preserves the top membership at 1; alternative rescaling conventions were not evaluated.
- Weighted-maximum operator was not run. No approved weights or exact weighted-maximum formula are specified; choosing weights would introduce a new decision.
- Soft-membership MAE is averaged over households with all three domain soft memberships known in both baseline and the existing sensitivity score. Sensitivity files without an existing scored file are marked not run.
- Mann-Whitney rank-biserial sign convention is r_rb=2*U_L1/(n_L1*n_L2)-1, so positive values indicate higher L1 ranks. Tests use complete eight-item scores only; no conclusion about pooling is made.
- Low/medium/high hard labels use the largest soft membership; exact ties follow low, then medium, then high (first maximum), matching the existing Stage 4 comparison convention.
- D-10a is applied only in the Stage 4b diagnostic: the existing frozen asset membership is masked unless all 18 recorded items are valid; Stage 4 files and references remain unchanged.
- UNAPPROVED share-owned sensitivity fits a separate empirical reference to the observed owned-share values because the approved frozen asset reference is defined on owned-item counts, not shares.
- UNAPPROVED minimum-15-valid sensitivity applies the existing frozen asset reference to households with at least 15 valid items; this is a diagnostic threshold only.
