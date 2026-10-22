import { ChevronDown, Info } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Skeleton } from "@/components/ui/skeleton"

import { CONTEXT_GROUPS, MARKET_CONTEXT_TEXT } from "../constants"
import { featureValueText } from "../utils"
import { FeatureName } from "./FeatureName"
import { PageState } from "./PageState"

function displayValue(name, value) {
  return featureValueText(name, value)
}

function Message({ children }) {
  return (
    <p className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-50/60 p-3 text-sm dark:bg-amber-950/20">
      <Info className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" />
      <span>{children}</span>
    </p>
  )
}

/**
 * Advanced section: the 13 market and macro features, read-only, filled from
 * GET /api/risk/market-context. `context` is the useMarketContext query.
 */
export function MarketContextSection({ context, ready, descriptions, onRetry }) {
  const data = context.data
  const filled = ready && context.isSuccess && data?.in_data_range
  const values = filled ? data.features : {}

  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm font-medium">Advanced · Market & macro</p>
          <p className="text-xs text-muted-foreground">
            13 values from category and visit month. Read-only. Used for this visit only;
            previous visits don't need market data.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {filled && <span className="text-xs text-muted-foreground">Auto-filled</span>}
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent className="space-y-4 border-t p-4">
        {!ready && <p className="text-sm text-muted-foreground">{MARKET_CONTEXT_TEXT.choose}</p>}
        {ready && context.isPending && <Skeleton className="h-24 w-full" />}
        {ready && context.isError && <PageState error={context.error} onRetry={onRetry} />}
        {ready && context.isSuccess && !data.in_data_range && (
          <Message>
            {MARKET_CONTEXT_TEXT.outOfRange} {data.note}
          </Message>
        )}
        {filled && data.evidence_missing && <Message>{MARKET_CONTEXT_TEXT.noEvidence}</Message>}

        {CONTEXT_GROUPS.map((group) => (
          <div key={group.key} className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {group.title}
            </p>
            <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
              {group.features.map((name) => (
                <div key={name} className="space-y-0.5">
                  <dt className="text-sm leading-snug">
                    <FeatureName name={name} description={descriptions[name]} />
                  </dt>
                  <dd className="text-sm font-medium tabular-nums">
                    {filled ? displayValue(name, values[name]) : "—"}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ))}

        {ready && context.isSuccess && (
          <p className="text-xs text-muted-foreground">Source: {data.source_note}</p>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
