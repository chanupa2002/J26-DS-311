# market_risk: frontend plan

Status: **decisions made (§6). Steps F2 (foundation + Overview), F3 (Risk Check), F4 (Future Risk), F5 (market/macro auto-fill) and H2 (history from previous visits) built.** Owner: @Chamosithmini. Work only inside `frontend/src/features/market_risk/`.

Backend: `/api/risk` (see `backend/app/components/market_risk/README.md` and `schemas.py`). The models are version 2.0: SYNTHETIC panel (70 households, 9 categories), **NOT_READY**.

## 0. Facts found while reading (these shape the design)

| Fact | Where | Effect on the design |
|---|---|---|
| Routes and nav are read automatically from `routes.jsx` / `nav.js` (via `src/app/features.js`). The top bar shows `handle.title` | `src/app/router.jsx`, `features.js`, `Topbar.jsx` | Each route has `handle: { title }`, equal to the nav item title. Pages do not render their own title (and do not use `PageHeader`) |
| `api(path, options)` returns the parsed JSON body. On any error it **shows a toast** and throws `new Error(message)`. The message is the `detail` string, or for a 422 the joined `detail[].msg`. **The HTTP status and the `loc` of 422 errors are not kept** | `src/lib/api.js` | We cannot tell 422 from 503 by status. See §5 for the workaround and Q1 for the proposed shared change. Do not add a second toast: errors are already toasted |
| The ESLint rule blocks imports from other features | `eslint.config.js` | Livelihood is used only as a style reference. Its `PageState` pattern is **re-implemented** in our folder, not imported |
| Available UI: `badge`, `button`, `card`, `collapsible`, `dialog`, `input`, `label`, `select`, `separator`, `skeleton`, `table`, `tabs`, `tooltip`, `sonner`. **No** `alert`, `progress`, `checkbox`, `radio-group`, `switch`, `textarea` | `src/components/ui/` | Notices are a `Card` with an icon and `role="alert"`. Bars are Tailwind divs. 0/1/blank answers use `Select` |
| `Badge` variants: `default`, `secondary`, `destructive`, `outline` | `badge.jsx` | Class colours (`RiskBadge`, F3): Low green, Medium amber, High red, Unassigned grey, set with Tailwind classes on `Badge`. No new variants are added to the shared file |
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
1. **Validation notice** (always at the top, compact, amber, not a red banner): "Prototype model · validation pending", with "Validation pending" badges per horizon (raw `model_status` in a tooltip) and a collapsible "Why" with each `deployment_reason`.
   **About the data** card (collapsible; the summary line stays visible): trained on a synthetic panel that mirrors the monitoring data, because real records lack a stable household ID; demonstration only, must be validated on real data before use.
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
  - a plain-English `Label` and a hint from the backend field descriptions. Every question is phrased so that Yes = 1 (e.g. "Has the business stopped running?");
  - example buttons: **All OK** (→ Low), **Two signals** (→ High), **Missing answer** (→ Unassigned, Medium–High, follow-up);
  - buttons: Check risk (submit) and Reset;
  - plain React state (4 selects cannot hold an invalid value, so no zod is needed).
- **Result card:**
  - `risk_class` as a large `Badge`;
  - "Possible range" `best_case_class` – `worst_case_class` (from `possible_range`), shown when the two differ;
  - if `follow_up_needed`: an amber callout **"Follow-up visit recommended"** with `WeakSignalTag` and the possible range;
  - the `reasons` list;
  - `signal_count` / `unknown_count`;
  - `rule_version` in small text;
  - "The answers have changed since this check" when the form differs from the answers that were sent.
- **"Use in Future Risk" button** (decision Q6): navigates to `/risk/future` with router state `{ signals, risk_ord, signal_count, unknown_count }`. `signals` holds the 4 answers that were **sent** (0/1/null, keyed as in `/identify`). Future Risk maps them to 7 of the 53 features:
  - `F_Risk_Ord_t` = `risk_ord`, `F_Risk_Signal_Count_t` = `signal_count`, `F_Risk_Unknown_t` = `unknown_count`;
  - `F_Business_Not_Running_t`, `F_No_Profit_Last_Month_t`, `F_Not_Progressing_Well_t`, `F_Market_Stress_Any_t` = the 4 submitted signals (0/1/null).
  Future Risk reads `useLocation().state` once, shows "7 fields prefilled from Risk Check", and leaves the other fields blank. A page reload loses the state, which is acceptable.
- `ValidationNotice` at the top: "Provisional rule · validation pending", with "Why": rule-based (no ML), not validated by experts, the class rules, and blanks ≠ No.

### 1.3 Future Risk (`/risk/future`)
- **Toolbar:**
  - **No sample button** (removed after F4; `sampleFeatures.js` deleted). The form starts blank, or prefilled from Risk Check;
  - **Clear:** sets all fields to blank (null);
  - **Horizon:** a `Select` with both / 3M / 6M (default both).
- **Features form (53 fields):**
  - grouped in `Collapsible` sections that follow the README groups: household signals, operating conditions, participant, history, market, macro, location;
  - labels and tooltips from `/model-info` `features[].description`;
  - numeric fields are `Input type="number"`, where empty means `null`;
  - `F_Category` / `F_District` are `Select`s filled from `categorical_levels`, plus "Not specified" (null);
  - a counter "N of 53 filled, blanks are median-imputed".
- **Submit "Predict":** one click sends `/predict` and `/explain` (`top_k: 5`) with the same body, **always in parallel** (decision Q8).
- **Results:** one `Card` per horizon (side by side on desktop, stacked on mobile):
  - the `predicted_risk` `Badge`;
  - 3 probability bars (Low / Medium / High, percentages, Tailwind divs);
  - the "Validation pending" status badge (raw `model_status` in a tooltip); the page shows one `ValidationNotice` at the top with the reasons.
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
| `constants.js` | `BASE_PATH = "/api/risk"`, class order, Badge variant per class, metric labels, signal options, feature groups (name lists), static trade-off numbers and limitations (decision Q2) |
| ~~`sampleFeatures.js`~~ | Removed (F4 follow-up): the sample button was dropped |
| `utils.js` | `formatMetric`, `formatPercent`, `formatSigned`, `formatDateTime`, `splitReasons`, `errorKind(error)` (§5); later `toNullableNumber`, `buildPredictBody(values, horizon)` |
| `api/riskApi.js` | `getRiskModelInfo()`, `identifyCurrentRisk(signals)`, `predictMarketRisk(body)`, `explainMarketRisk(body)`, all via `api()` from `@/lib/api` |
| `api/index.js` | Re-exports |
| `hooks/useModelInfo.js` | `useQuery(["risk-model-info"])`, `staleTime: Infinity` (shared by Overview and Future Risk) |
| `hooks/useIdentify.js` | `useMutation(identifyCurrentRisk)` |
| `hooks/useFutureRisk.js` | One mutation that runs predict + explain with `Promise.allSettled`. It returns `{ prediction, explanation, explainError }`, so the prediction still shows if only explain fails |
| `hooks/index.js` | Re-exports |
| `components/PageState.jsx` | Loading (Skeletons), error (`Card` + Retry), empty. Same pattern as livelihood, own copy |
| `components/ValidationNotice.jsx` | Compact neutral (amber) notice "Prototype model · validation pending", with status badges and a collapsible "Why" listing the reasons (`deployment_reason` or given `reasons`). **Used on all 3 pages instead of a red banner** (on Risk Check with the rule's reasons) |
| `components/StatusBadge.jsx` | Shows "Validation pending" (or "Ready"); the raw `model_status` is in a tooltip |
| `components/AboutDataCard.jsx` | Overview: collapsible "About the data". The one-line summary (synthetic panel, demonstration only) is always visible |
| `components/RiskBadge.jsx` | Class → coloured `Badge` (Low green, Medium amber, High red, Unassigned grey); `size="lg"` |
| `components/ModelMetricsCard.jsx` | One horizon on Overview (metrics `Table`, baseline, tooltip) |
| `components/TradeOffTable.jsx` | Static 1.0 vs 2.0 walk-forward table |
| `components/LevelList.jsx` | Category / district `Badge`s |
| `components/LimitationsList.jsx` | Static list + `Collapsible` |
| `components/FeatureList.jsx` | Collapsible table of the 53 features (Overview) |
| `components/SignalForm.jsx` | 4 `Select`s + example buttons + Check risk / Reset |
| `components/CurrentRiskResult.jsx` | The Risk Check result card |
| `components/FeatureForm.jsx` | The grouped 53-field form, the category/district `Select`s, filled counter |
| `components/FeatureField.jsx` | One feature: a `Select` for coded features (`FEATURE_OPTIONS`: Yes/No, Female/Male, risk levels, hours, records, grant status, market tiers; categorical levels from `/model-info`) or a number `Input` for continuous values, with `Label` + F_* name |
| `components/ProbabilityBars.jsx` | 3 bars for one horizon |
| `components/PredictionCard.jsx` | Class badge + probability bars for one horizon (no status badge: the page-level `ValidationNotice` covers it) |
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
| Risk Check | `card`, `select`, `label`, `button`, `badge`, `tooltip`, `separator` | `WeakSignalTag` (follow-up callout). `EvidenceCard` was not used: a card per reason was too heavy, so the reasons are a list | `ValidationNotice`, `RiskBadge` |
| Future Risk | `card`, `input`, `label`, `select`, `button`, `badge`, `collapsible`, `tabs`, `tooltip`, `table`, `skeleton`, `separator` | `WeakSignalTag` (blank inputs among the top factors; models NOT_READY) | react-hook-form + zod, recharts |

`ConfidenceBadge`, `ScoreRange` and `EstimatedTag` are **not** used: their fixed texts ("Viability score", "District-level monitoring data…") do not match market risk. Decision Q4: own small components instead.

## 4. States

| State | Overview | Risk Check | Future Risk |
|---|---|---|---|
| Loading | `PageState loading` (Skeletons) while `/model-info` loads | Submit button "Checking…" + disabled | Form waits for `/model-info` (Skeletons). On submit, "Predicting…" + disabled, and Skeletons in the result area |
| Empty | `PageState empty` if `models` is empty | Before submit: hint text "Choose the answers and press Check risk" | Before submit: "Fill in the features you know and press Predict". All 53 blank is allowed (the backend imputes), with a notice |
| Error | `PageState error` + Retry (`refetch`) | Error card under the form + Retry. The form keeps its values | Error card above the results + Retry. If only `/explain` fails, the predictions still show, and the SHAP area shows the error |
| Not validated | `ValidationNotice` always shown | `ValidationNotice` with the provisional-rule reasons always shown | `ValidationNotice` at the top + `StatusBadge` in every prediction card. Nothing is shown as "ready" |

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

## 6. Decisions (formerly open questions)

| # | Question | Decision |
|---|---|---|
| Q1 | Telling 422 from 503 | Detect 503 by the backend message (`"Market-risk model is unavailable"`). **No change to `api.js`**; see the suggestion for the leader in §7 |
| Q2 | Trade-off and limitations source | Constants in `constants.js` in this folder |
| Q3 | Sample in the frontend | First: copy the sample request, labelled "Synthetic sample". **Revised after F4:** the sample button and badge were removed and `sampleFeatures.js` deleted |
| Q4 | `@/components/explain` with fixed texts | Build own small components (`ProbabilityBars`, `RiskBadge`, `ModelMetricsCard`) |
| Q5 | i18n | Plain English strings |
| Q6 | Risk Check → Future Risk | Yes: a **"Use in Future Risk"** button prefills `F_Risk_Ord_t`, `F_Risk_Signal_Count_t`, `F_Risk_Unknown_t` and the 4 signal features via router state (§1.2) |
| Q7 | Route prefix | `/risk/...` |
| Q8 | When to explain | `/explain` runs with every predict, in parallel |

## 7. Suggestions for the leader (not done; shared files)

- **`frontend/src/lib/api.js`:** attach `status` and `detail` to the thrown error, e.g. `Object.assign(new Error(message), { status: response.status, detail: body?.detail })`. Features could then tell 422 from 503 by status, and highlight the field from `detail[].loc`. The current behaviour is unchanged for existing callers.

## 8. Progress

| Step | What | Status |
|---|---|---|
| F1 | This plan | ✅ Done |
| F2 | Foundation (`api/riskApi.js` with all 4 calls, `hooks/useModelInfo.js`, `constants.js`, `utils.js`), shared components (`PageState`, `ValidationNotice`, `StatusBadge`, `AboutDataCard`, `ModelMetricsCard`, `TradeOffTable`, `LevelList`, `LimitationsList`, `FeatureList`), `OverviewPage` at `/risk/overview`, routes and nav | ✅ Done |
| F3 | Risk Check page: `hooks/useIdentify.js`, `RiskBadge`, `SignalForm`, `CurrentRiskResult`, `RiskCheckPage` at `/risk/check`, route + nav | ✅ Done |
| F4 | Future Risk page: `hooks/useFutureRisk.js` (predict + explain in parallel with `Promise.allSettled`), `FeatureForm`, `FeatureField`, `PredictionCard`, `ProbabilityBars`, `WarningList`, `ShapChart`, `ExplanationPanel`, `FutureRiskPage` at `/risk/future`, route + nav. Built details:
| F4b | Future Risk follow-up: 30 coded features as selects. Option values are the trained codes, so requests are unchanged. Market tiers are Low=0 / Medium=1 / High=2, blank = insufficient evidence (`Category_Month_Table`). Sample button, badge and `sampleFeatures.js` removed; status badge removed from prediction cards; SHAP note fixed to "SHAP shows what drives the model, not real-world causes." | ✅ Done |
| F5 | Market and macro auto-fill:
  - **Visit month:** a select next to Category, with options from `available_months`. It's not a model feature.
  - **Advanced section:** the 13 `F_Mkt_*` / `F_Macro_*` features left the editable form. They are shown read-only in a collapsed "Advanced · Market & macro" section, with an "Auto-filled" badge and `source_note`.
  - **Request:** the values come straight from `GET /api/risk/market-context` (`hooks/useMarketContext.js`) and go into the request at Predict time, so a new category or month replaces them and Clear empties them. Predict waits while they load.
  - **Missing data:** if `evidence_missing`, the page says "No market price data for this category…". If `in_data_range` is false, it shows the note and sends nulls (never guessed).
  - **Month list:** one market-context call for the current month.
  - **503 detection:** also recognises the backend's "Market-context data is unavailable" message | ✅ Done |
| H2 | History from previous visits:
  - **Visit date:** "Visit month" is replaced by a "Visit date" date input, limited by `min`/`max` to `available_months`, with a message if outside. Its month drives `/market-context`. An optional "Grant received date" sits next to grant status and must not be after the visit date.
  - **Previous visits:** a section with a "First visit for this household" checkbox, or up to 12 rows: Month (only the 24 months before the visit month, each used once), the 4 answers Yes/No/Not answered, and Remove.
  - **History values:** the 14 history fields left the form. `hooks/useHistoryFeatures.js` calls `POST /api/risk/history-features` (debounced 400 ms) with the current answers from the form (incl. the Risk Check prefill) and the previous visits. The values are shown read-only in a collapsed "Advanced · History" section with an "Auto-calculated" badge, plain labels and the visits with their risk class, and go into the request at Predict time.
  - **No history given:** neither the checkbox nor any rows means the 14 values are sent as null, with a note.
  - **Errors:** client checks mark the row or field. Backend 422 messages are matched to the grant date or to the rows by month (`api()` drops `loc`).
  - **Predict and Clear:** Predict waits ("Calculating history…"); Clear also empties visit date, grant date and previous visits | ✅ Done |
| H2b | Previous visits feel "saved":
  - **Done:** each row has a Done button, enabled when the month is chosen and there is no error. Enter on the row also counts, except on a select or button, which keep their own Enter. Done collapses the row into a one-line summary with the risk class from the `/history-features` visits list, plus Edit and Remove. New rows start open, and "Add previous visit" is disabled while an open row is invalid.
  - **Status line:** Calculating… / ✓ History updated (N previous visits) / the error.
  - **Not stored:** a note under the header says visits are not stored (no browser storage is used).
  - **Wording:** "Market stress" is now "Household reported market problems" with help text, and the Market & macro subtitle notes that previous visits don't need market data. The calculation is unchanged | ✅ Done |
  - **Form:** sections Current signals (11), Business (10), Participant (3), History (14), Market (8), Macro (5), Category & District (2). The page uses the order from `/model-info`; any unlisted feature goes into "Other". Invalid numbers are flagged on the client and not sent.
  - **Warnings:** `/predict` returns one `warnings` list for the request, not one per horizon, so it is shown once under the prediction cards ("Input notes").
  - **Explain:** the backend `note` is shown verbatim. A failed `/explain` shows an error inside the SHAP card only, and Retry reruns both calls. | ✅ Done |
