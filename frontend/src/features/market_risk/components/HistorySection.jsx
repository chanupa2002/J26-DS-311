import { ChevronDown, Info } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Skeleton } from "@/components/ui/skeleton"

import { HISTORY_FEATURES, HISTORY_TEXT } from "../constants"
import { featureValueText, monthLabel } from "../utils"
import { FeatureName } from "./FeatureName"
import { RiskBadge } from "./RiskBadge"

function displayValue(name, value) {
  if (name === "F_Risk_Change_vs_Prev" && value === 0) return "No change"
  return featureValueText(name, value)
}

/**
 * Advanced section: the 14 history features, read-only, calculated by
 * POST /api/risk/history-features. `history` is the useHistoryFeatures result.
 */
export function HistorySection({ status, history, waiting }) {
  const { query, current } = history
  const data = current ? query.data : null

  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm font-medium">Advanced · History</p>
          <p className="text-xs text-muted-foreground">
            14 values calculated from this visit and the previous visits. Read-only.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {data && <span className="text-xs text-muted-foreground">Auto-calculated</span>}
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent className="space-y-4 border-t p-4">
        {status === "unknown" && (
          <p className="flex items-start gap-2 text-sm text-muted-foreground">
            <Info className="mt-0.5 size-4 shrink-0" />
            <span>
              {HISTORY_TEXT.choose} {HISTORY_TEXT.unknown}
            </span>
          </p>
        )}
        {status === "incomplete" && (
          <p className="text-sm text-muted-foreground">Fix the marked visit fields to calculate the history.</p>
        )}
        {status === "ready" && waiting && <Skeleton className="h-24 w-full" />}
        {status === "ready" && !waiting && query.isError && (
          <p role="alert" className="text-sm text-destructive">
            The history could not be calculated: {query.error?.message}
          </p>
        )}

        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {HISTORY_FEATURES.map((name) => (
            <div key={name} className="space-y-0.5">
              <dt className="text-sm leading-snug">
                <FeatureName name={name} />
              </dt>
              <dd className="text-sm font-medium tabular-nums">
                {data ? displayValue(name, data.features[name]) : "—"}
              </dd>
            </div>
          ))}
        </dl>

        {data && (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Visits used (risk class by the rule)
            </p>
            <ul className="flex flex-wrap gap-2">
              {data.visits.map((visit) => (
                <li key={visit.month} className="flex items-center gap-2 rounded-md border px-2 py-1 text-sm">
                  <span>
                    {monthLabel(visit.month)}
                    {visit.is_current && " (this visit)"}
                  </span>
                  <RiskBadge riskClass={visit.risk_class} />
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">Rule: {data.rule_version}</p>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
