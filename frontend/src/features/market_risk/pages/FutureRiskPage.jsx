import { useState } from "react"
import { useLocation } from "react-router-dom"

import { DateField } from "../components/DateField"
import { ExplanationPanel } from "../components/ExplanationPanel"
import { FeatureForm } from "../components/FeatureForm"
import { HistorySection } from "../components/HistorySection"
import { MarketContextSection } from "../components/MarketContextSection"
import { PageState } from "../components/PageState"
import { PredictionCard } from "../components/PredictionCard"
import { PreviousVisitsSection } from "../components/PreviousVisitsSection"
import { ValidationNotice } from "../components/ValidationNotice"
import { WarningList } from "../components/WarningList"
import {
  CATEGORICAL_FEATURES,
  CONTEXT_FEATURES,
  CURRENT_VISIT_ANSWERS,
  FEATURE_GROUPS,
  FEATURE_OPTIONS,
  FUTURE_RISK_NOTICE_REASON,
  GRANT_DATE_HELP,
  HISTORY_FEATURES,
  RISK_CHECK_COUNT_FEATURES,
  RISK_CHECK_SIGNAL_FEATURES,
  VISIT_DATE_HELP,
} from "../constants"
import { useFutureRisk } from "../hooks/useFutureRisk"
import { useHistoryFeatures } from "../hooks/useHistoryFeatures"
import { useMarketContext, useMarketMonths } from "../hooks/useMarketContext"
import { useModelInfo } from "../hooks/useModelInfo"
import {
  buildHistoryRequest,
  featuresFromRiskCheck,
  featuresToForm,
  formToFeatures,
  historyErrorTargets,
  isValidDate,
  lastDayOfMonth,
  monthLabel,
} from "../utils"

// Features that are filled automatically and never typed in.
const AUTO_FEATURES = [...CONTEXT_FEATURES, ...HISTORY_FEATURES]

/**
 * The editable form sections, limited to the features the backend reports (plus any unlisted
 * ones). Market/macro (from /market-context) and history (from /history-features) are excluded.
 */
function groupsFor(featureNames) {
  const known = new Set(featureNames.filter((name) => !AUTO_FEATURES.includes(name)))
  const groups = FEATURE_GROUPS.map((group) => ({
    ...group,
    features: group.features.filter((name) => known.has(name)),
  })).filter((group) => group.features.length)
  const listed = new Set(groups.flatMap((group) => group.features))
  const other = [...known].filter((name) => !listed.has(name))
  return other.length
    ? [...groups, { key: "other", title: "Other", description: "Other model inputs.", features: other }]
    : groups
}

function initialForm(state) {
  const prefill = featuresFromRiskCheck(
    state,
    RISK_CHECK_SIGNAL_FEATURES,
    RISK_CHECK_COUNT_FEATURES,
  )
  return {
    values: prefill ? featuresToForm(Object.keys(prefill), prefill) : {},
    prefilled: Boolean(prefill),
  }
}

export function FutureRiskPage() {
  const location = useLocation()
  const modelInfo = useModelInfo()
  const futureRisk = useFutureRisk()

  const [initial] = useState(() => initialForm(location.state))
  const [values, setValues] = useState(initial.values)
  const [prefilled, setPrefilled] = useState(initial.prefilled)
  const [horizon, setHorizon] = useState("both")
  const [invalid, setInvalid] = useState([])
  const [visitDate, setVisitDate] = useState("")
  const [grantDate, setGrantDate] = useState("")
  const [firstVisit, setFirstVisit] = useState(false)
  const [visits, setVisits] = useState([])

  // Visit date: a real date inside the months with market/macro data.
  const months = useMarketMonths(modelInfo.data?.categorical_levels?.F_Category?.[0])
  const monthList = months.data || []
  const minDate = monthList.length ? `${monthList[0]}-01` : undefined
  const maxDate = monthList.length ? lastDayOfMonth(monthList[monthList.length - 1]) : undefined
  let visitDateError = null
  if (visitDate && !isValidDate(visitDate)) visitDateError = "Enter a full date (YYYY-MM-DD)."
  else if (visitDate && minDate && (visitDate < minDate || visitDate > maxDate)) {
    visitDateError = `Choose a date from ${monthLabel(monthList[0])} to ${monthLabel(monthList[monthList.length - 1])}: the market and national data only cover these months.`
  }
  const usableVisitDate = visitDate && !visitDateError ? visitDate : ""
  const visitMonth = usableVisitDate.slice(0, 7)

  const category = String(values.F_Category || "").trim()
  const marketContext = useMarketContext(category, visitMonth)
  const contextReady = Boolean(category && visitMonth)

  // History: current answers in the form + previous visits -> /history-features (debounced).
  const historyInput = buildHistoryRequest({
    values,
    visitDate: usableVisitDate,
    grantDate,
    firstVisit,
    visits,
    answerMap: CURRENT_VISIT_ANSWERS,
  })
  const history = useHistoryFeatures(historyInput.request)
  const serverErrors =
    historyInput.status === "ready" && !history.waiting && history.query.isError
      ? historyErrorTargets(history.query.error?.message, visits)
      : { rows: {} }
  const visitErrors = {
    rows: { ...serverErrors.rows, ...historyInput.problems.rows },
    section: serverErrors.section,
  }
  const riskByMonth = history.current
    ? Object.fromEntries(history.query.data.visits.map((visit) => [visit.month, visit.risk_class]))
    : {}
  let historyStatus = null
  if (historyInput.status === "incomplete") {
    historyStatus = { kind: "error", message: "Fix the marked fields to update the history." }
  } else if (historyInput.status === "ready") {
    if (history.waiting) historyStatus = { kind: "waiting" }
    else if (history.query.isError) {
      historyStatus = { kind: "error", message: `The history could not be calculated: ${history.query.error?.message}` }
    } else if (history.current) {
      historyStatus = { kind: "updated", count: historyInput.request.previous_visits.length }
    }
  }

  if (modelInfo.isPending) return <PageState loading />
  if (modelInfo.isError) {
    return <PageState error={modelInfo.error} onRetry={() => modelInfo.refetch()} />
  }

  const { models = [], features = [], categorical_levels: levels = {} } =
    modelInfo.data || {}
  const featureNames = features.length
    ? features.map((feature) => feature.name)
    : [...FEATURE_GROUPS.flatMap((group) => group.features), ...AUTO_FEATURES]
  const descriptions = Object.fromEntries(
    features.map((feature) => [feature.name, feature.description]),
  )
  // Selects: coded numeric features (fixed options) and the categorical levels from /model-info.
  const choices = {
    ...FEATURE_OPTIONS,
    ...Object.fromEntries(
      CATEGORICAL_FEATURES.map((name) => [
        name,
        {
          options: (levels[name] || []).map((level) => ({ value: level, label: level })),
          blank: "Not specified",
        },
      ]),
    ),
  }

  const { features: typed, invalid: invalidNow } = formToFeatures(
    featureNames,
    CATEGORICAL_FEATURES,
    values,
  )
  // Market/macro values come from /market-context, history values from /history-features,
  // both for the current inputs only; otherwise they are sent as null (never guessed).
  const context = contextReady && marketContext.isSuccess && marketContext.data.in_data_range
    ? marketContext.data.features
    : {}
  const historyValues = history.current ? history.query.data.features : {}
  const body = {
    ...typed,
    ...Object.fromEntries(CONTEXT_FEATURES.map((name) => [name, context[name] ?? null])),
    ...Object.fromEntries(HISTORY_FEATURES.map((name) => [name, historyValues[name] ?? null])),
  }
  const request = { horizon, features: body }
  const stale =
    futureRisk.isSuccess &&
    JSON.stringify(request) !== JSON.stringify(futureRisk.variables)

  const waitingFor = contextReady && marketContext.isPending
    ? "Filling market data…"
    : history.waiting
      ? "Calculating history…"
      : null

  const changeValues = (next) => {
    setValues(next)
    if (invalid.length) setInvalid([])
  }
  const clear = () => {
    changeValues({})
    setVisitDate("")
    setGrantDate("")
    setFirstVisit(false)
    setVisits([])
    setPrefilled(false)
    futureRisk.reset()
  }
  const submit = () => {
    if (invalidNow.length) {
      setInvalid(invalidNow)
      return
    }
    futureRisk.mutate(request)
  }
  const retry = () => futureRisk.mutate(futureRisk.variables || request)

  const result = futureRisk.data

  return (
    <div className="space-y-6">
      <ValidationNotice models={models} reasons={[FUTURE_RISK_NOTICE_REASON]} />

      <FeatureForm
        groups={groupsFor(featureNames)}
        values={values}
        onChange={changeValues}
        descriptions={descriptions}
        choices={choices}
        horizon={horizon}
        onHorizonChange={setHorizon}
        invalid={invalid}
        prefilledFromRiskCheck={prefilled}
        extraFields={{
          F_Category: (
            <DateField
              id="risk-visit-date"
              label="Visit date"
              help={VISIT_DATE_HELP}
              value={visitDate}
              onChange={setVisitDate}
              min={minDate}
              max={maxDate}
              error={visitDateError || serverErrors.visitDate}
            />
          ),
          F_Grant_Status_Ord_t: (
            <DateField
              id="risk-grant-date"
              label="Grant received date"
              help={GRANT_DATE_HELP}
              value={grantDate}
              onChange={setGrantDate}
              max={usableVisitDate || maxDate}
              error={historyInput.problems.grantDate || serverErrors.grantDate}
            />
          ),
        }}
        sections={
          <PreviousVisitsSection
            visitMonth={visitMonth}
            firstVisit={firstVisit}
            onFirstVisitChange={setFirstVisit}
            visits={visits}
            onChange={setVisits}
            errors={visitErrors}
            riskByMonth={riskByMonth}
            status={historyStatus}
          />
        }
        advanced={
          <>
            <HistorySection status={historyInput.status} history={history} waiting={history.waiting} />
            <MarketContextSection
              context={marketContext}
              ready={contextReady}
              descriptions={descriptions}
              onRetry={() => marketContext.refetch()}
            />
          </>
        }
        waitingFor={waitingFor}
        onClear={clear}
        onSubmit={submit}
        pending={futureRisk.isPending}
      />

      {futureRisk.isIdle && (
        <PageState
          empty
          emptyMessage="Fill in the features you know and press Predict. Blank fields are allowed."
        />
      )}
      {futureRisk.isPending && <PageState loading />}
      {futureRisk.isError && <PageState error={futureRisk.error} onRetry={retry} />}

      {futureRisk.isSuccess && result && (
        <div className="space-y-6" aria-live="polite">
          {stale && (
            <p className="text-sm text-muted-foreground">
              The inputs have changed since this prediction. Press Predict to
              update.
            </p>
          )}
          <div className="grid gap-6 lg:grid-cols-2">
            {result.prediction.predictions.map((prediction) => (
              <PredictionCard key={prediction.horizon} prediction={prediction} />
            ))}
          </div>
          <WarningList warnings={result.prediction.warnings} />
          <ExplanationPanel
            explanation={result.explanation}
            error={result.explainError}
            onRetry={retry}
          />
        </div>
      )}
    </div>
  )
}
