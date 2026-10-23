import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { CurrentRiskResult } from "../components/CurrentRiskResult"
import { PageState } from "../components/PageState"
import { SignalForm } from "../components/SignalForm"
import { EMPTY_SIGNAL_FORM, SIGNALS } from "../constants"
import { useIdentify } from "../hooks/useIdentify"
import { clearLastRiskCheck, saveLastRiskCheck } from "../hooks/useLastRiskCheck"
import { toSignals } from "../utils"

export function RiskCheckPage() {
  const navigate = useNavigate()
  const identify = useIdentify()
  const [values, setValues] = useState(EMPTY_SIGNAL_FORM)

  const submit = () => {
    const signals = toSignals(values)
    // Saved (in memory only) so Future Risk can prefill them however it is opened.
    identify.mutate(signals, { onSuccess: () => saveLastRiskCheck(signals) })
  }
  const reset = () => {
    setValues(EMPTY_SIGNAL_FORM)
    identify.reset()
    clearLastRiskCheck()
  }

  // The result belongs to the answers that were sent (mutation variables), not the live form.
  const sent = identify.variables
  const current = toSignals(values)
  const stale =
    Boolean(sent) && SIGNALS.some(({ key }) => sent[key] !== current[key])

  // The answers are already in the last-Risk-Check store; Future Risk reads them on open.
  const useInFutureRisk = () => navigate("/risk/future")

  return (
    <div className="space-y-6">
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
