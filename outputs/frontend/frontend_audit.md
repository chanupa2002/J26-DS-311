# Frontend audit

## Scope

Usability and explainability changes for the Component 1 beneficiary-selection research prototype, using the current v0.2 interim model. The work retains the existing fuzzy and Bayesian-network scoring rules.

## Page review

- **Overview:** describes the saved-score comparison group, plots the expected-vulnerability distribution and median, and shows unweighted province/district counts plus evidence coverage. District means are suppressed below 10 records.
- **Household Scores:** adds named location filters, percentile filtering, model score and probability interpretation, evidence-used counts, input membership details, Unknown inputs, and saved sensitivity ranges.
- **Assess a Household:** accepts raw coded answers, previews derived values, and returns a temporary estimate with probabilities, comparison percentile, evidence count, and named comparison group. Health and financial-resilience raw inputs remain Unknown.
- **CSV batch:** provides pre-upload structure preview and validation; the existing API template contains domain degrees and coverage fractions. It is not presented as raw questionnaire CSV.
- **Robustness:** presents precomputed scenario comparisons and the decision log.
- **Method & Limits:** describes the current model flow, definitions, key limitations, source decisions, and change notes.

## Explainability and access

- Unknown answers stay distinct from No and zero.
- Percentiles are relative to an explicitly named comparison group, with the saved record count.
- Every visible candidate score includes an evidence-used count.
- Glossary controls can be opened by keyboard and dismissed with Escape; chart brushing supports arrow keys.
- Glossary clarity feedback is stored only in browser local storage and contains the term ID, Yes/No response, timestamp, and page path. It contains no household identifier or answer data.
- Research-only status, model/spec versions, dataset manifest fingerprint, and API status are displayed in the page frame.

## Remaining source gaps

Question text for toilet types, assets, and food-insecurity items is marked TODO because the referenced questionnaire PDF was unavailable in the repository. Roster membership, toilet codes 5/10/999, form comparability, and absent health/financial raw inputs are documented in `open_questions.md`.

## Verification

- `python -m pytest backend/app/components/beneficiary_selection/tests/test_usability_api.py -q`: passed (5 tests).
- `npm.cmd run lint`: passed.
- `npm.cmd run build`: passed; Vite reports its existing large JavaScript chunk advisory.
- UI screenshots were not captured because no browser surface was available in the computer-use environment. No real household-level values were used in this audit artifact.
