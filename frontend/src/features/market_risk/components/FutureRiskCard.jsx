import { ChevronDown } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { WeakSignalTag } from "@/components/explain/WeakSignalTag"

import { AlertBadge } from "./AlertBadge"
import { ProbabilityBar } from "./ProbabilityBar"
import { RiskPill } from "./RiskPill"

function Horizon({ title, subtitle, outlook, source, children }) {
  return (
    <section className="space-y-2" aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-medium">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <RiskPill riskClass={outlook.predicted_class} />
      </div>
      {outlook.p_high !== null && outlook.p_high !== undefined && (
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">Chance of High risk</p>
          <ProbabilityBar value={outlook.p_high} threshold={outlook.alert_threshold} source={source} />
        </div>
      )}
      {children}
    </section>
  )
}

/**
 * Next month (summary of past visits, no model), 3 months (machine-learning early warning
 * with alert) and, folded away, 6 months (not reliable, never alerts).
 */
export function FutureRiskCard({ predictions }) {
  const m1 = predictions?.["1M"]
  const m3 = predictions?.["3M"]
  const m6 = predictions?.["6M"]
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">What may happen next</CardTitle>
        <CardDescription>Next month from past visits; in 3 months from the early-warning model.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        {m1 && (
          <Horizon
            title="Next month (from past visits)"
            subtitle={m1.n_transitions ? `Based on ${m1.n_transitions} month-to-month changes of simulated households` : undefined}
            outlook={m1}
            source="Past visits: share that were High the next month"
          >
            <p className="text-xs text-muted-foreground">{m1.note}</p>
          </Horizon>
        )}
        {m3 && (
          <Horizon title="In 3 months (early warning)" subtitle="Machine-learning model" outlook={m3}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">Needs attention?</span>
              <AlertBadge alert={m3.alert} />
            </div>
            {m3.reliability_note && <p className="text-xs">{m3.reliability_note}</p>}
          </Horizon>
        )}
        {m6 && (
          <Collapsible className="rounded-md border border-dashed">
            <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 rounded-md p-2 text-left text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              6 months – not reliable
              <ChevronDown className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" aria-hidden="true" />
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-3 px-2 pb-2">
              <div className="flex flex-wrap items-start gap-2">
                <WeakSignalTag />
                <p className="min-w-0 flex-1 text-xs">
                  Rough guide only – no alert.{m6.reliability_note ? ` ${m6.reliability_note}` : ""}
                </p>
              </div>
              <Horizon title="In 6 months" outlook={m6} />
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  )
}
