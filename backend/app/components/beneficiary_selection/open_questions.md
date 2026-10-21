# API open questions

Research output - not an eligibility determination

- The candidate rank is a temporary insertion into the saved baseline score distribution; it does not rewrite the saved household ranking.
- Province and district are attached from the documented one-to-one household identification source in memory. Household keys are not returned.
- The compact decision index summarizes Section 9 IDs and conditions. Decision-log markdown served by `/spec` remains authoritative.
- Candidate coverage is represented as `n_used / n_total` with the supplied fraction over 1 for the existing BN coverage blend.
- Synthetic examples are for interface behavior only and are clearly marked in every API response; they do not represent households.

No decision or score validation is made by this API layer.
