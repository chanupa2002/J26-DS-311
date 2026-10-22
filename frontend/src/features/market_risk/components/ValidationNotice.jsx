import { ChevronDown, Info } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

/**
 * Compact, always-visible notice that the models (or the rule) are not yet validated.
 * Used on every market_risk page. Only our own short texts are shown (never the backend's
 * deployment_reason verbatim).
 * @param {{ title?: string, reasons?: string[] }} props
 */
export function ValidationNotice({ title = "Prototype model · validation pending", reasons = [] }) {
  return (
    <div
      role="note"
      className="rounded-lg border border-amber-500/40 bg-amber-50/60 px-4 py-3 text-sm dark:bg-amber-950/20"
    >
      <Collapsible>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <Info className="size-4 shrink-0 text-amber-700 dark:text-amber-400" />
          <p className="font-medium">{title}</p>
          {reasons.length > 0 && (
            <CollapsibleTrigger className="group ml-auto flex items-center gap-1 text-muted-foreground underline decoration-dotted underline-offset-4">
              Why
              <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
          )}
        </div>
        {reasons.length > 0 && (
          <CollapsibleContent className="mt-3 pl-7">
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              {reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </CollapsibleContent>
        )}
      </Collapsible>
    </div>
  )
}
