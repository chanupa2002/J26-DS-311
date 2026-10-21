## 9. Addendum (2026-10-21): domain structure for v0.2

Status: S-02, M-06, M-07, D-10a, B-01 to B-05, the new-input approvals (9.6, with their open conditions) and 9.7 are approved by the researcher on 2026-10-21 and recorded by Claude on the researcher's instruction. Supersedes Section 1 (S-01) where they conflict.

### 9.1 Scope amendment

| ID | Decision | Rationale | Approval |
| --- | --- | --- | --- |
| S-02 | Supersedes the four-domain scope of S-01. v0.2 groups domains as: **Exposure** (shocks, O1); **Sensitivity** (food, health, demographic dependency, living conditions); **Adaptive capacity** (economic, financial resilience, coping). Housing is split into shelter quality (walls, floor, roof), sanitation, and crowding and tenure. | Four domains, three driven by one input, is too thin for a vulnerability measure. Exposure, sensitivity and adaptive capacity is a widely used organising frame. | ☑ (researcher, 2026-10-21) |

### 9.2 Status of candidate domains

| Domain | Group | Source | Status | Blocker |
| --- | --- | --- | --- | --- |
| Financial resilience | Adaptive capacity | N1 has-debt, N2 bank account | Proposed for v0.2 | Debt total, ratio and savings balances stay deferred (ISS-08 to ISS-10) |
| Health | Sensitivity | B3 chronic illness or disability, aggregated to household | Proposed for v0.2 | B3 code/skip conflict (ISS-04, ISS-05) to be quantified in Stage 3b |
| Shocks | Exposure | O1 | Conditional | Reference period (ISS-11) |
| Coping | Adaptive capacity | O2 | Conditional | Rule for codes 3, 4, 997 (ISS-12) |
| Energy insecurity | Sensitivity (living conditions) | L3 | Not yet evidence-reviewed | Needs the same documented review as D1 to D7 |
| Water security | Sensitivity (living conditions) | L5 | Not yet evidence-reviewed | Same |
| Wellbeing | none (validation only) | P | Not an input | Closer to an outcome; descriptive check only |
| Livelihood | Adaptive capacity | H1/H2 (D4) | Deferred | H2_02 mapping (ISS-06, ISS-14) |

### 9.3 Model design

| ID | Decision | Rationale | Approval |
| --- | --- | --- | --- |
| M-06 | Bayesian Network becomes two-level: domain nodes feed Exposure, Sensitivity and Adaptive capacity nodes, which feed the Vulnerability node. Tables by ranked nodes (M-03). | With 8 or more parents a single table has 6,561 rows; the two-level structure keeps each table at 27 to 81 rows and inspectable. | ☑ (researcher, 2026-10-21) |

### 9.4 Open decision

| ID | Question | Options | Approval |
| --- | --- | --- | --- |
| D-10a | Asset completeness rule (open question from Stage 4) | **Chosen by researcher 2026-10-21: (a) require all 18 asset items valid.** A household with any invalid or missing asset item has the asset summary treated as unknown (no imputation). Sensitivity runs: (b) share owned among valid items; (c) a minimum number of valid items. | ☑ |

### 9.5 Bayesian Network defaults (B-01 to B-05), accepted 2026-10-21

| ID | Decision | Operational value in bn_v0_1.py | Sensitivity run | Approval |
| --- | --- | --- | --- | --- |
| B-01 | Number of states | 3 (low, medium, high) at every node. Evidence from the fuzzy layer has 3 states, so a 5-state run applies to intermediate and vulnerability nodes only | n_states = 5 | ☑ |
| B-02 | Weights | Equal at both levels (parents of each node weighted equally) | Economic and food higher; demographic higher | ☑ |
| B-03 | Ranked-node spread | sigma = 0.15 on the 0 to 1 scale (researcher choice inside "moderate"; inspect with cpt_table) | sigma 0.08 and 0.25 | ☑ |
| B-04 | Partial coverage | Evidence blended toward uniform by n_used / n_total; n_used = 0 gives no evidence | no blending; no blending with a minimum coverage of 0.5 | ☑ |
| B-05 | Domain priors | Uniform | Empirical marginals from the fuzzy layer | ☑ |

Limits to state in any write-up:
- Conditional tables are expert-specified by the ranked-nodes method; nothing is learned from data or from label_high_vuln. The output is a transparent composite, not a validated probability of vulnerability.
- Domains are treated as independent evidence, although they are correlated in practice.
- Ranked nodes with a weighted mean pull outputs toward the middle. The two-level structure compounds this, so uncertainty stays high even for households deprived in several domains. Alternative combination functions are a sensitivity question for the next round.
- Until the new domains exist as scored leaves, the network runs on four leaves: exposure has no leaf and adaptive_capacity rests on economic alone.

### 9.6 New domain inputs (approved by the researcher 2026-10-21, with conditions that remain open)

The researcher approved the new domains' inputs. Approval fixes the inputs as candidates for the model. It does not remove the open evidence conditions below; each row stays subject to them and is reopened if a Stage 3b check changes a rule. Membership functions for the new inputs are not yet approved (see 9.7).

| ID | Domain (group) | Input | Source | Approved handling | Condition still open |
| --- | --- | --- | --- | --- | --- |
| N-01 | Financial resilience (adaptive capacity) | Bank account | n2_01 (0 no, 1 yes) | Blank or out-of-set = unknown | None beyond Stage 3b value-set check |
| N-02 | Financial resilience (adaptive capacity) | Has debt | n1_0 (0 no, 1 yes) | Blank or out-of-set = unknown. Direction (debt as stress vs access to credit) is a researcher judgement, tested by excluding the input | Agreement of n1_0 with the source flags (Stage 3b) |
| H-01 | Health (sensitivity) | Share of household members with chronic illness or severe disability | b3_01 (0/1), roster long; share = n_chronic / n_members_b3_valid | Households with no valid B3 member = unknown; partial B3 coverage flagged. b3_03 and b3_04 not used | ISS-04, ISS-05: quantify the b3_01 / b3_03 skip conflict (Stage 3b) |
| X-01 | Shocks (exposure) | O1 shock items (1 severe, 2 moderate, 3 none) | o1_01_1 to o1_01_20 | Raw items carried; no composite until a rule is approved | ISS-11: reference period not verified |
| C-01 | Coping (adaptive capacity) | O2 coping items | o2_* (1 yes, 2 no not necessary, 3 no already done, 4 not applicable, 997 prefer not to say) | Raw counts only; no derived coping score | ISS-12: rule for codes 3, 4, 997 |
| E-01 | Energy insecurity (sensitivity, living conditions) | L3 items | l3_* | Included as a candidate only | Evidence review not yet done; scale types and skip logic unchecked |
| W-01 | Water security (sensitivity, living conditions) | L5 items | l5_* | Included as a candidate only | Evidence review not yet done |

### 9.7 Membership definitions for the new inputs and the housing split (approved by the researcher 2026-10-21)

| ID | Approved membership | Sensitivity run | Approval |
| --- | --- | --- | --- |
| N-01 | bank_account: no = 1, yes = 0 | Exclude N-01 | ☑ |
| N-02 | has_debt: yes = 1, no = 0 (direction is a researcher judgement) | Exclude N-02; reverse direction | ☑ |
| H-01 | membership = share_chronic (already 0 to 1) | any chronic member (binary) | ☑ |
| Housing split | shelter quality = mean of wall, floor, roof; sanitation = toilet; crowding and tenure = mean of crowding and tenure | domain mean vs max operators | ☑ |

Unknown inputs stay unknown (M-04). Sub-domain n_used / n_total counts only the inputs of that sub-domain.

### 9.8 Interim network structure for v0.2 (M-07 approved by the researcher 2026-10-21)

Splitting housing into three leaves would give housing three of six equal parents at the sensitivity node, tripling its weight relative to food, demographic and health. To keep B-02 ("each domain counts the same") approximately true, the three housing leaves feed a living_conditions node first:

    shelter, sanitation, crowding_tenure -> living_conditions
    living_conditions, food, demographic, health -> sensitivity           (81-row table)
    economic, financial_resilience -> adaptive_capacity                    (9-row table)
    sensitivity, adaptive_capacity -> vulnerability
    (exposure is added when shocks has an approved rule)

Check on synthetic cases (bn_v0_1.py, interim structure): with every housing leaf at "high" and nothing else observed, sensitivity P(high) is about 0.31, against about 0.33 for food alone at "high" (nested housing counts as roughly one domain, slightly less because it passes through an extra smoothing node). In the flat alternative it is about 0.49 against 0.27, so housing would count nearly twice as much as food.

Alternative run (sensitivity): all six sensitivity leaves as direct parents of sensitivity (729 rows).

| ID | Decision | Approval |
| --- | --- | --- |
| M-07 | Use the nested living_conditions structure above as the interim v0.2 network | ☑ (researcher, 2026-10-21) |
