import { useState } from "react"
import { useLocation } from "react-router-dom"

import { ExplanationPanel } from "../components/ExplanationPanel"
import { FeatureForm } from "../components/FeatureForm"
import { MarketContextSection } from "../components/MarketContextSection"
import { PageState } from "../components/PageState"
import { PredictionCard } from "../components/PredictionCard"
import { ValidationNotice } from "../components/ValidationNotice"
import { VisitMonthField } from "../components/VisitMonthField"
import { WarningList } from "../components/WarningList"
import {
  CATEGORICAL_FEATURES,
  CONTEXT_FEATURES,
  FEATURE_GROUPS,
  FEATURE_OPTIONS,
  FUTURE_RISK_NOTICE_REASON,
  RISK_CHECK_COUNT_FEATURES,
  RISK_CHECK_SIGNAL_FEATURES,
} from "../constants"
import { useFutureRisk } from "../hooks/useFutureRisk"
import { useMarketContext, useMarketMonths } from "../hooks/useMarketContext"
import { useModelInfo } from "../hooks/useModelInfo"
import { featuresFromRiskCheck, featuresToForm, formToFeatures } from "../utils"

/**
 * The editable form sections, limited to the features the backend reports (plus any unlisted
 * ones). The 13 market and macro features are never editable: they come from /market-context.
 */
function groupsFor(featureNames) {
  const known = new Set(featureNames.filter((name) => !CONTEXT_FEATURES.includes(name)))
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
  const [visitMonth, setVisitMonth] = useState("")

  const category = String(values.F_Category || "").trim()
  const months = useMarketMonths(modelInfo.data?.categorical_levels?.F_Category?.[0])
  const marketContext = useMarketContext(category, visitMonth)
  const contextReady = Boolean(category && visitMonth)

  if (modelInfo.isPending) return <PageState loading />
  if (modelInfo.isError) {
    return <PageState error={modelInfo.error} onRetry={() => modelInfo.refetch()} />
  }

  const { models = [], features = [], categorical_levels: levels = {} } =
    modelInfo.data || {}
  const featureNames = features.length
    ? features.map((feature) => feature.name)
    : FEATURE_GROUPS.flatMap((group) => group.features)
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
  // Market and macro values always come from /market-context for the current category and
  // visit month; without an in-range answer they are sent as null (never guessed).
  const context = contextReady && marketContext.isSuccess && marketContext.data.in_data_range
    ? marketContext.data.features
    : {}
  const body = {
    ...typed,
    ...Object.fromEntries(CONTEXT_FEATURES.map((name) => [name, context[name] ?? null])),
  }
  const request = { horizon, features: body }
  const stale =
    futureRisk.isSuccess &&
    JSON.stringify(request) !== JSON.stringify(futureRisk.variables)

  const changeValues = (next) => {
    setValues(next)
    if (invalid.length) setInvalid([])
  }
  const clear = () => {
    changeValues({})
    setVisitMonth("")
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
            <VisitMonthField value={visitMonth} onChange={setVisitMonth} months={months} />
          ),
        }}
        advanced={
          <MarketContextSection
            context={marketContext}
            ready={contextReady}
            descriptions={descriptions}
            onRetry={() => marketContext.refetch()}
          />
        }
        waitingFor={contextReady && marketContext.isPending ? "Filling market data…" : null}
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
