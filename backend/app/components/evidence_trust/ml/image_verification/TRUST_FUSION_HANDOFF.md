# Trust Fusion hand-off

`to_trust_fusion_inputs(report)` converts image verification results into the
three inputs required by Trust Fusion: quality, duplicate status, and category
match.

Unknown or missing values are represented as `"not available"`. They reduce
confidence rather than becoming failures. A confirmed self or cross-household
duplicate is marked `confirmed_duplicate=true` and `severity="critical"`.
Authenticity and progress results remain advisory/review information and are
not used as critical Trust Fusion inputs.
