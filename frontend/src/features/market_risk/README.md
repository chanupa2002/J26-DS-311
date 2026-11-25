# Market risk – v2 pages

Monthly monitoring of each funded livelihood project after the Samurdhi grant. All data on the
Households, Household detail and Model evidence pages comes from **simulated households**
(`SIM-HH-…`) and is always labelled **Simulated**. No thresholds or risk logic are typed in the
frontend: every class, probability, alert, level and threshold is shown as the API returns it.

## Pages

The system is fully automatic: officers do not type visit data. The Market Risk menu shows only
the 3 automatic pages; Household detail opens from the Households table.

| Page | Route | In menu | Endpoints (base `/api/risk/v2`) |
|---|---|---|---|
| Households | `/risk/v2/households` (`?month=YYYY-MM`) | 1st | `GET /risk/households`, `GET /market/districts` (months + KPI), `GET /model/evidence` (alert threshold) |
| Market pressure | `/risk/v2/market` (`?month=YYYY-MM`) | 2nd | `GET /market/districts` |
| Model evidence | `/risk/v2/evidence` | 3rd | `GET /model/evidence` |
| Household detail | `/risk/v2/household/:householdKey` | no (from the table) | `GET /risk/household/{household_key}` |

`/risk` and `/risk/overview` redirect to Households.

**Manual-entry pages are not in the menu.** Their code stays in the repo, and their routes still
open when the URL is typed directly: v1 Risk Check (`/risk/check`), v1 Future Risk (`/risk/future`;
v1 is also kept in the `viva-v1` tag) and Check a visit (`/risk/v2/check`, `CheckVisitV2Page` +
`VisitForm`). `POST /risk/visit` stays in the backend: it is the automatic scoring call used when a
visit is saved.

- **Current risk** is the rule result of this month's visit form (not predicted). Unassigned = form incomplete.
- **Future risk**: 3-month P(High) with the alert threshold (Youden's J, from the API) and an alert;
  6-month P(High) is indicative only and never raises an alert.
- **Why**: the top 5 SHAP factors of the 3-month outlook, tagged Business / Household shock /
  History / Market / Current risk.
- **Market pressure**: FAO Indicator of Food Price Anomalies (SDG 2.c.1) level per district and livelihood.
- Grant status is shown with the label from the API (`grant_status_label`).

Errors show the backend `detail` (for example the 503 "No market data for 2026-10" text). Queries do
not retry automatically.

## Code

- `api/riskV2Api.js` – the 5 calls; `hooks/useV2*.js` – one TanStack Query hook per endpoint.
- `components/` – `RiskPill`, `MarketPill`, `AlertBadge`, `ProbabilityBar`, `SimulatedBadge`,
  `CurrentRiskCard`, `FutureRiskCard`, `MarketCard`, `ShapBars`, `VisitResult`, `RiskTimeline`,
  `StepStrip`, `HouseholdsTable`, `MarketHeatmap`, `EvidenceTable`, `ShapGroupShare`, `VisitForm`,
  `V2PageState`, `HouseholdCharts` (risk donut, High risk by district / livelihood), `InfoTip` (ⓘ header help),
  `HowThisWorks` (collapsible research notes); display helpers in `components/v2format.js`.
- Plain language for officers: chances are shown as natural frequencies ("about 3 in 10", exact % in the
  tooltip); households needing attention (3-month alert, then High this month, then Unassigned) are listed first.
- `pages/` – `HouseholdsV2Page`, `HouseholdDetailV2Page`, `CheckVisitV2Page`, `MarketPressurePage`, `ModelEvidencePage`.

## Run locally

```bash
# backend (needs the git-ignored artifacts in backend/app/components/market_risk/artifacts_v2/)
cd backend && .venv/bin/uvicorn app.main:app --port 8000
# frontend
cd frontend && npm run dev   # http://localhost:5173 → Market Risk → Households
```

Months after the market data (currently 2026-10 and later) return 503, which the pages show as an error card.
