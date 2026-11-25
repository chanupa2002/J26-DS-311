import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { WeakSignalTag } from "@/components/explain/WeakSignalTag"

import { AlertBadge } from "./AlertBadge"
import { ProbabilityBar } from "./ProbabilityBar"
import { RiskPill } from "./RiskPill"

function Horizon({ title, outlook, children }) {
  return (
    <section className="space-y-2" aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">{title}</h3>
        <RiskPill riskClass={outlook.predicted_class} />
      </div>
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">Chance of High risk</p>
        <ProbabilityBar value={outlook.p_high} threshold={outlook.alert_threshold} />
      </div>
      {children}
    </section>
  )
}

/** Expected risk in 3 months (can raise "needs attention") and 6 months (rough guide only). */
export function FutureRiskCard({ predictions }) {
  const m3 = predictions?.["3M"]
  const m6 = predictions?.["6M"]
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Expected in 3 and 6 months</CardTitle>
        <CardDescription>What the model expects, based on past visits of similar households.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        {m3 && (
          <Horizon title="In 3 months" outlook={m3}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">Needs attention?</span>
              <AlertBadge alert={m3.alert} />
            </div>
            {m3.reliability_note && <p className="text-xs">{m3.reliability_note}</p>}
          </Horizon>
        )}
        {m6 && (
          <Horizon title="In 6 months" outlook={m6}>
            {m6.reliability_note && (
              <div className="flex flex-wrap items-start gap-2 rounded-md border border-dashed p-2">
                <WeakSignalTag />
                <p className="min-w-0 flex-1">Rough guide only – no alert. {m6.reliability_note}</p>
              </div>
            )}
          </Horizon>
        )}
      </CardContent>
    </Card>
  )
}
