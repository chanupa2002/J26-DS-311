# Open questions and source gaps

The interface keeps unresolved inputs as Unknown and does not infer questionnaire wording or category membership.

## Source material needed

- `Data/BRIGHT_questionnaire_English.pdf` was referenced during review but was not present in the repository. Provide the approved questionnaire to replace the TODO labels for toilet types, asset item wording, and the eight food-insecurity questions.
- The codebook cross-check in `component1_audit/docs/codebook_crosscheck_v0_1.md` verifies the listed source mappings but has no province/district mapping. For this prototype, the project leader authorized the supplied mapping as authoritative; verify it against the official codebook before operational use.

## Model and input rules requiring owner confirmation

- Confirm the expected-value calculation explanation shown to users. The displayed 0–1 output and probabilities come from the current v0.2 interim network; the interface does not change scoring logic.
- Confirm household roster inclusion rules for the under-15, 15–64, and 65+ counts. The what-if form treats entered ages as the roster and labels this assumption.
- Confirm toilet type labels and classification for cleaned-file codes 5, 10, and 999. These remain Unknown in the raw-answer assessment.
- Confirm that the two food-insecurity forms are comparable before treating all eight responses as the same measure.
- The raw questionnaire assessment does not collect the v0.2 health and financial-resilience inputs because matching raw questions and derivation rules were not available. Those leaves remain Unknown. Add them only after owners confirm fields and transformations.
- The CSV batch endpoint currently accepts eight domain degrees plus coverage fractions, not raw questionnaire rows. A raw-answer batch schema requires the source questionnaire and owner-approved field mapping.

## Review notes

- Unknown, Don't know, Refused, and unanswered values must never be converted to No or zero.
- Scores are research output and are not validated for eligibility decisions.
