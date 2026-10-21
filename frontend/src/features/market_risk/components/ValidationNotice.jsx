import { ChevronDown, Info } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { splitReasons } from "../utils"
import { StatusBadge } from "./StatusBadge"

/**
 * Compact, always-visible notice that the models (or the rule) are not yet validated.
 * Used on every market_risk page.
 * @param {{ title?: string, models?: { horizon: string, model_status: string, deployment_reason: string }[], reasons?: string[] }} props
 */
export function ValidationNotice({
  title = "Prototype model · validation pending",
  models = [],
  reasons = [],
}) {
  const hasDetails = models.length > 0 || reasons.length > 0

  return (
    <div
      role="note"
      className="rounded-lg border border-amber-500/40 bg-amber-50/60 px-4 py-3 text-sm dark:bg-amber-950/20"
    >
      <Collapsible>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <Info className="size-4 shrink-0 text-amber-700 dark:text-amber-400" />
          <p className="font-medium">{title}</p>
          {models.map((model) => (
            <StatusBadge
              key={model.horizon}
              prefix={model.horizon}
              status={model.model_status}
            />
          ))}
          {hasDetails && (
            <CollapsibleTrigger className="group ml-auto flex items-center gap-1 text-muted-foreground underline decoration-dotted underline-offset-4">
              Why
              <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
          )}
        </div>

        {hasDetails && (
          <CollapsibleContent className="mt-3 space-y-3 pl-7">
            {reasons.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {models.map((model) => (
              <div key={model.horizon} className="space-y-1">
                <p className="font-medium">{model.horizon} model</p>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {splitReasons(model.deployment_reason).map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            ))}
          </CollapsibleContent>
        )}
      </Collapsible>
    </div>
  )
}
