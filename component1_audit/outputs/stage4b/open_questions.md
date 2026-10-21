# Stage 4b open questions

Research output - not an eligibility determination

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
