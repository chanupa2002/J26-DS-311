import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { CurrentRiskResult } from "../components/CurrentRiskResult"
import { PageState } from "../components/PageState"
import { SignalForm } from "../components/SignalForm"
import { ValidationNotice } from "../components/ValidationNotice"
import { EMPTY_SIGNAL_FORM, RULE_NOTICE, SIGNALS } from "../constants"
import { useIdentify } from "../hooks/useIdentify"
import { toSignals } from "../utils"

export function RiskCheckPage() {
  const navigate = useNavigate()
  const identify = useIdentify()
  const [values, setValues] = useState(EMPTY_SIGNAL_FORM)

  const submit = () => identify.mutate(toSignals(values))
  const reset = () => {
    setValues(EMPTY_SIGNAL_FORM)
    identify.reset()
  }

  // The result belongs to the answers that were sent (mutation variables), not the live form.
  const sent = identify.variables
  const current = toSignals(values)
  const stale =
    Boolean(sent) && SIGNALS.some(({ key }) => sent[key] !== current[key])

  const useInFutureRisk = () => {
    const result = identify.data
    navigate("/risk/future", {
      state: {
        signals: sent,
        risk_ord: result.risk_ord,
        signal_count: result.signal_count,
        unknown_count: result.unknown_count,
      },
    })
  }

  return (
    <div className="space-y-6">
      <ValidationNotice
        title={RULE_NOTICE.title}
        reasons={RULE_NOTICE.reasons}
      />

      <SignalForm
        values={values}
        onChange={setValues}
        onSubmit={submit}
        onReset={reset}
        pending={identify.isPending}
      />

      {identify.isPending && <PageState loading />}
      {identify.isError && (
        <PageState error={identify.error} onRetry={submit} />
      )}
      {identify.isIdle && (
        <PageState
          empty
          emptyMessage="Choose the answers (or an example) and press Check risk."
        />
      )}
      {identify.isSuccess && (
        <CurrentRiskResult
          result={identify.data}
          stale={stale}
          onUseInFutureRisk={useInFutureRisk}
        />
      )}
    </div>
  )
}
