# Stage 4c fuzzy scoring rerun

Research output - not an eligibility determination

Scored the four currently specified domains using the existing frozen Stage 4 references and the existing Stage 4 fuzzy engine. The asset completeness threshold was set to 18 valid items (D-10a). Stage 3 and Stage 4 source files were read only. No overall vulnerability score or ranking was produced.

- Households scored: 6,847.
- Asset items valid: 6,847/6,847 households have all 18 valid asset items; no asset summaries were masked.
- Model version: fuzzy-0.1.0; frozen reference SHA-256 recorded in manifest.
- Domains: housing, economic, food, demographic. Domain input coverage and n_used counts: `domain_summary_d10a.csv`.

## Shocks

The approved v0.1 decision log defers D5 shocks and D6 coping because reference periods and response-state rules remain unresolved. Stage 3b contains shock-related prepared inputs, but the current fuzzy engine has no shock domain or approved membership mapping. No shock score was calculated. A future shock score needs documented indicators, valid/missing code handling, reference periods, membership functions, and within-domain aggregation rules.
