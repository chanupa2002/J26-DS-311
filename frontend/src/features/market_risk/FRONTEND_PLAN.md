# market_risk: frontend plan

Status: **PLAN ONLY, no code yet.** Owner: @Chamosithmini. Work only inside `frontend/src/features/market_risk/`.

Backend: `/api/risk` (see `backend/app/components/market_risk/README.md` and `schemas.py`). The models are version 2.0: SYNTHETIC panel (70 households, 9 categories), **NOT_READY**.

## 0. Facts found while reading (these shape the design)

| Fact | Where | Effect on the design |
|---|---|---|
| Routes and nav are read automatically from `routes.jsx` / `nav.js` (via `src/app/features.js`). The top bar shows `handle.title` | `src/app/router.jsx`, `features.js`, `Topbar.jsx` | Each route has `handle: { title }`, equal to the nav item title. Pages do not render their own title (and do not use `PageHeader`) |
| `api(path, options)` returns the parsed JSON body. On any error it **shows a toast** and throws `new Error(message)`. The message is the `detail` string, or for a 422 the joined `detail[].msg`. **The HTTP status and the `loc` of 422 errors are not kept** | `src/lib/api.js` | We cannot tell 422 from 503 by status. See §5 for the workaround and Q1 for the proposed shared change. Do not add a second toast: errors are already toasted |
| The ESLint rule blocks imports from other features | `eslint.config.js` | Livelihood is used only as a style reference. Its `PageState` pattern is **re-implemented** in our folder, not imported |
| Available UI: `badge`, `button`, `card`, `collapsible`, `dialog`, `input`, `label`, `select`, `separator`, `skeleton`, `table`, `tabs`, `tooltip`, `sonner`. **No** `alert`, `progress`, `checkbox`, `radio-group`, `switch`, `textarea` | `src/components/ui/` | Notices are a `Card` with an icon and `role="alert"`. Bars are Tailwind divs. 0/1/blank answers use `Select` |
| `Badge` variants: `default`, `secondary`, `destructive`, `outline` | `badge.jsx` | Class colours: High → `destructive`, Medium → `default`, Low → `secondary`, Unassigned → `outline`. We do not add new variants |
| `recharts` 3.10.1, `react-hook-form`, `zod` and TanStack Query are already dependencies | `package.json` | No new libraries are needed. SHAP chart: recharts. Forms: react-hook-form + zod |
| `@/components/explain`: `ConfidenceBadge`, `EstimatedTag`, `EvidenceCard`, `ScoreRange`, `WeakSignalTag`. Their texts are fixed (e.g. ScoreRange says "Viability score") | `src/components/explain/` | Only `WeakSignalTag` and `EvidenceCard` fit as they are; see §4 |
| The dashboard already calls `/api/risk/health` | `DashboardPage.jsx` | No health page in this feature |
| Backend CORS allows `http://localhost:5173` | `backend/app/core/config.py` | Local dev works with the default `VITE_API_URL` |
| `/model-info` returns models (status, reason, data basis, test metrics, baseline, training period), the 53 features (name, type, description) and `categorical_levels`. It does **not** return the limitations or the walk-forward trade-off | `schemas.py` `ModelInfoResponse` | Limitations and the trade-off table are static text in our folder (Q2) |

## 1. Pages, routes and nav

| Nav title (= top bar title) | Path | Page | Backend calls |
|---|---|---|---|
| Overview | `/risk/overview` | `OverviewPage` | `GET /api/risk/model-info` |
| Risk Check | `/risk/check` | `RiskCheckPage` | `POST /api/risk/identify` |
| Future Risk | `/risk/future` | `FutureRiskPage` | `GET /api/risk/model-info` (dropdowns, labels), `POST /api/risk/predict`, `POST /api/risk/explain` |

`nav.js`: keep `title: "Market Risk"` and the `ChartNoAxesCombined` icon. Set `items` to the 3 entries above, in that order.
`routes.jsx`: 3 route objects `{ path, element, handle: { title } }` with the same paths and titles.

### 1.1 Overview (`/risk/overview`)
1. **NOT_READY banner** (always at the top): "Synthetic data only, not for real decisions", followed by each model's `model_status` and `deployment_reason`.
2. **Models:** one `Card` per horizon (3M, 6M) with:
   - `model_name`, `algorithm`, `data_basis`, `training_period`, `created`;
   - test metrics (Macro-F1, High recall, High precision, accuracy) in a `Table`;
   - the persistence-baseline Macro-F1 next to the model's;
   - `validation_methodology` in a `Tooltip`.
3. **Version 2.0 trade-off:** a small static table with the walk-forward Macro-F1 and High recall of 1.0 vs 2.0, labelled "SYNTHETIC panel".
4. **Categories:** the 9 `F_Category` levels and the 4 `F_District` levels as `Badge`s, from `categorical_levels`.
5. **Limitations:** a static list, shortened from the backend README. `Collapsible` "Show all".
6. **Features (optional):** a `Collapsible` `Table` of the 53 features (name, type, description).

### 1.2 Risk Check (`/risk/check`)
- **Form:** 4 `Select`s, one per signal:
  - `business_not_running`, `no_profit_last_month`, `not_progressing_well`, `market_stress_any`;
  - options: Yes (1), No (0), Not answered (null); default "Not answered";
  - a plain-English `Label` and a hint from the backend field descriptions;
  - buttons: Check risk (submit) and Reset.
- **Result card:**
  - `risk_class` as a large `Badge`;
  - "Possible range" `best_case_class` – `worst_case_class` (from `possible_range`), shown when the two differ;
  - if `follow_up_needed`: a notice "Follow-up visit needed: fill the blank answers" with `WeakSignalTag`;
  - the `reasons` list;
  - `signal_count` / `unknown_count`;
  - `rule_version` in small text.
- Note under the result: "Rule-based (SUSTAIN-HH-Risk-Rule v1.0, provisional, not validated by experts). No ML model."

### 1.3 Future Risk (`/risk/future`)
- **Toolbar:**
  - **Load sample:** fills the form from `sampleFeatures.js`, a copy of `backend/.../sample_data/predict_request_example.json` (synthetic, rounded);
  - **Clear:** sets all fields to blank (null);
  - **Horizon:** a `Select` with both / 3M / 6M (default both).
- **Features form (53 fields):**
  - grouped in `Collapsible` sections that follow the README groups: household signals, operating conditions, participant, history, market, macro, location;
  - labels and tooltips from `/model-info` `features[].description`;
  - numeric fields are `Input type="number"`, where empty means `null`;
  - `F_Category` / `F_District` are `Select`s filled from `categorical_levels`, plus "Not specified" (null);
  - a counter "N of 53 filled, blanks are median-imputed".
- **Submit "Predict":** one click sends `/predict` and `/explain` (`top_k: 5`) with the same body, in parallel.
- **Results:** one `Card` per horizon (side by side on desktop, stacked on mobile):
  - the `predicted_risk` `Badge`;
  - 3 probability bars (Low / Medium / High, percentages, Tailwind divs);
  - the NOT_READY notice with `model_status` and `deployment_reason`.
- **Warnings:** the `warnings` from `/predict`, e.g. "converted 'TRADE' → 'Trade'" or "12 features median-imputed", in a muted `Card` list.
- **SHAP "What pushed towards High":**
  - a recharts horizontal `BarChart` of `high_risk_factors` (label, signed contribution; + = towards High, − = away), with the value used in the tooltip;
  - shows `high_risk_probability` and `base_value`;
  - one chart per horizon, in `Tabs` 3M / 6M when both are shown;
  - the backend `note` is shown verbatim: "SHAP shows what drives the model, not real-world causes".
- **Optional `Collapsible` "Factors for the predicted class":** `top_factors` in a `Table` with `direction`.

## 2. Files per folder (all under `frontend/src/features/market_risk/`)

| File | Content |
|---|---|
| `nav.js` | 3 items (§1) |
| `routes.jsx` | 3 routes with `handle.title` |
| `README.md` | Pages, endpoints used, how to test locally (like livelihood's README) |
| `constants.js` | `BASE_PATH = "/api/risk"`, class order, Badge variant per class, signal options, feature groups (name lists), static trade-off numbers and limitations |
| `sampleFeatures.js` | The 53-key sample object (synthetic, from the backend sample JSON) |
| `utils.js` | `toNullableNumber`, `formatPercent`, `formatSigned`, `errorKind(error)` (§5), `buildPredictBody(values, horizon)` |
| `api/riskApi.js` | `getRiskModelInfo()`, `identifyCurrentRisk(signals)`, `predictMarketRisk(body)`, `explainMarketRisk(body)`, all via `api()` from `@/lib/api` |
| `api/index.js` | Re-exports |
| `hooks/useModelInfo.js` | `useQuery(["risk-model-info"])`, `staleTime: Infinity` (shared by Overview and Future Risk) |
| `hooks/useIdentify.js` | `useMutation(identifyCurrentRisk)` |
| `hooks/useFutureRisk.js` | One mutation that runs predict + explain with `Promise.allSettled`. It returns `{ prediction, explanation, explainError }`, so the prediction still shows if only explain fails |
| `hooks/index.js` | Re-exports |
| `components/PageState.jsx` | Loading (Skeletons), error (`Card` + Retry), empty. Same pattern as livelihood, own copy |
| `components/NotReadyNotice.jsx` | `Card role="alert"` with an icon: status + reason(s). Used on all 3 pages (on Risk Check as the "rule is provisional" note) |
| `components/RiskBadge.jsx` | Class → `Badge` variant + text |
| `components/ModelSummaryCard.jsx` | One horizon on Overview (metrics `Table`, baseline, tooltip) |
| `components/TradeOffTable.jsx` | Static 1.0 vs 2.0 walk-forward table |
| `components/LevelList.jsx` | Category / district `Badge`s |
| `components/LimitationsList.jsx` | Static list + `Collapsible` |
| `components/SignalForm.jsx` | 4 `Select`s (react-hook-form + zod) |
| `components/CurrentRiskResult.jsx` | The Risk Check result card |
| `components/FeatureForm.jsx` | The grouped 53-field form, the category/district `Select`s, filled counter |
| `components/FeatureField.jsx` | One numeric field with `Label` + description `Tooltip` |
| `components/ProbabilityBars.jsx` | 3 bars for one horizon |
| `components/PredictionCard.jsx` | Badge + bars + NOT_READY notice for one horizon |
| `components/WarningList.jsx` | `/predict` warnings |
| `components/ShapChart.jsx` | recharts bar chart of `high_risk_factors` |
| `components/FactorTable.jsx` | `top_factors` table (optional section) |
| `components/index.js` | Re-exports |
| `pages/OverviewPage.jsx`, `pages/RiskCheckPage.jsx`, `pages/FutureRiskPage.jsx` | The 3 pages |
| `pages/index.jsx` | Re-exports |

No files outside this folder are changed. No `.env` and no new dependencies.

## 3. UI parts used per page

| Page | `@/components/ui` | `@/components/explain` | Other |
|---|---|---|---|
| Overview | `card`, `table`, `badge`, `collapsible`, `tooltip`, `skeleton`, `button` (Retry, Show all), `separator` | `WeakSignalTag` (next to the 6M metrics: "test split not embargoed") | `lucide-react` icons |
| Risk Check | `card`, `select`, `label`, `button`, `badge`, `tooltip`, `separator` | `WeakSignalTag` (follow-up needed / blanks), `EvidenceCard` (each reason as `text`, `source` = rule version) | react-hook-form + zod |
| Future Risk | `card`, `input`, `label`, `select`, `button`, `badge`, `collapsible`, `tabs`, `tooltip`, `table`, `skeleton`, `separator` | `WeakSignalTag` (blank inputs among the top factors; models NOT_READY) | react-hook-form + zod, recharts |

`ConfidenceBadge`, `ScoreRange` and `EstimatedTag` are **not** used: their fixed texts ("Viability score", "District-level monitoring data…") do not match market risk (Q4).

## 4. States

| State | Overview | Risk Check | Future Risk |
|---|---|---|---|
| Loading | `PageState loading` (Skeletons) while `/model-info` loads | Submit button "Checking…" + disabled | Form waits for `/model-info` (Skeletons). On submit, "Predicting…" + disabled, and Skeletons in the result area |
| Empty | `PageState empty` if `models` is empty | Before submit: hint text "Choose the answers and press Check risk" | Before submit: "Fill the features or press Load sample". All 53 blank is allowed (the backend imputes), with a notice |
| Error | `PageState error` + Retry (`refetch`) | Error card under the form + Retry. The form keeps its values | Error card above the results + Retry. If only `/explain` fails, the predictions still show, and the SHAP area shows the error |
| NOT_READY | Banner always shown | Provisional-rule note always shown | Notice in every prediction card. The page shows nothing as "ready" |

## 5. How 422 and 503 errors are shown

`api()` already shows a toast with the message. The page **also** shows an inline card, because toasts disappear. There is no second toast.

| Case | How we recognise it today (no status from `api()`) | What the user sees |
|---|---|---|
| **503**: model unavailable | Message starts with `"Market-risk model is unavailable"` (fixed text from `router.py`) | Card: "The prediction model is not available on the server right now. Contact the market_risk owner." with the backend message underneath and Retry |
| **422**: invalid input | Any other message from these POSTs (pydantic messages such as "Input should be a valid number") | Card: "Some inputs were not accepted:" + the message. The form stays filled |
| Network / backend down | `TypeError` from `fetch` ("Failed to fetch") | Card: "Cannot reach the backend at `VITE_API_URL`" + Retry |

**Prevent most 422s on the client:**
- the zod schema mirrors the backend: numbers finite or null; signals 0/1/null; `top_k` 1–20; horizon both/3M/6M;
- all 53 keys are always sent, with blanks as `null`, so no 422 for a missing key;
- the dropdowns only offer known levels.

Field-level 422 highlighting needs the `loc`, which `api()` drops (Q1).

## 6. Open questions

1. **Shared `api.js` change (leader-only):** to tell 422 from 503 reliably and highlight the field with a 422 error, `api()` would need to attach `status` and `detail` to the thrown error, e.g. `error.status`, `error.detail`. Should I request this? Until then the message-prefix workaround in §5 is used.
2. **Trade-off and limitations source:** these are static text in `constants.js`, so they can drift from the backend. Alternative: add an optional `promotion` / `limitations` field to `/model-info` in my backend folder (`metadata.json` already has `promotion`). Which do you prefer?
3. **Sample data in the frontend:** OK to copy the synthetic sample request (53 values, from synthetic example row 1, already committed in the backend `sample_data/`) into `sampleFeatures.js`? The alternative is a backend `GET /api/risk/sample` endpoint.
4. **`@/components/explain`:** `ScoreRange` / `ConfidenceBadge` have fixed texts. Should I ask the leader for generic props (e.g. a `label` on `ScoreRange`), or keep my own `ProbabilityBars` / `RiskBadge`?
5. **i18n:** `src/i18n/en.json` is leader-only and livelihood uses plain English strings. Plain strings in my folder for now?
6. **Feature form usability:** 53 raw engineered fields are hard to fill by hand. Should Future Risk also offer "use Risk Check result" (filling `F_Risk_Ord_t`, `F_Risk_Signal_Count_t` and `F_Risk_Unknown_t` from `/identify`)? Or should it stay a technical/demo page?
7. **Route prefix:** `/risk/...` follows the API prefix (livelihood uses `/livelihood/...`). OK?
8. **Explain on every predict:** run `/explain` automatically with every predict (two calls), or only when "Explain" is pressed?
