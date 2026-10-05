# Shared Contracts

## 1. URL prefixes

| Component | Prefix |
|---|---|
| beneficiary_selection | /api/beneficiary |
| livelihood_planning | /api/livelihood |
| evidence_trust | /api/trust |
| market_risk | /api/risk |

Each member uses only their own prefix. Any pull request that changes a prefix
is rejected.

## 2. Public service functions

| Component | Function | Input | Output | Status |
|---|---|---|---|---|
| beneficiary_selection | assess_household | TBD | TBD | Not started |
| livelihood_planning | recommend_livelihood | TBD | TBD | Not started |
| evidence_trust | score_evidence | TBD | TBD | Not started |
| market_risk | predict_market_risk | TBD | TBD | Not started |

## 3. Database tables (Supabase)

| Table | Owner (writes) | Read by |
|---|---|---|
| beneficiaries | beneficiary_selection | TBD |
| area_profiles | Shared public data | All components |
| generated_plans | livelihood_planning | TBD |
| evidence_trust tables | TBD | TBD |
| market_risk tables | TBD | TBD |

## 4. Rules

- Write only to your own tables. Get another component's data through its public
  service function or its table.
- Call another component only through its public function in services.py. Never
  import its ml/ package or private helpers.
- Change a contract only by group agreement through a pull request approved by
  the leader.
- The frontend calls APIs only through the prefixes listed above.
