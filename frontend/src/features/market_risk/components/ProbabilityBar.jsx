import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

import { inTen, percent } from "./v2format"

/**
 * Chance of High risk as a bar with "about 3 in 10" next to it; the exact % is in the tooltip.
 * The dashed marker is the alert level from the API (no typed cut-off).
 */
export function ProbabilityBar({ value, threshold, compact = false, className }) {
  const width = Math.max(0, Math.min(1, Number(value) || 0)) * 100
  const hasThreshold = threshold !== null && threshold !== undefined && Number.isFinite(Number(threshold))
  const words = inTen(value)
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          tabIndex={0}
          aria-label={`Chance of High risk ${words} (${percent(value)})${hasThreshold ? `; alert level ${percent(threshold)}` : ""}`}
          className={cn("flex items-center gap-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", className)}
        >
          <div aria-hidden="true" className={cn("relative w-full rounded-full bg-muted", compact ? "h-2 min-w-14" : "h-3 min-w-24")}>
            <div className="h-full rounded-full bg-primary/80" style={{ width: `${width}%` }} />
            {hasThreshold && (
              <div
                className={cn("absolute border-l-2 border-dashed border-foreground", compact ? "-top-1 h-4" : "-top-1.5 h-6")}
                style={{ left: `${Number(threshold) * 100}%` }}
              />
            )}
          </div>
          <span aria-hidden="true" className={cn("shrink-0 whitespace-nowrap", compact ? "text-xs" : "text-sm font-medium")}>
            {words}
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent className="text-xs">
        <p>Model&apos;s chance of High risk: {percent(value, 1)}</p>
        {hasThreshold && <p>Alert level (dashed marker): {percent(threshold, 1)}</p>}
      </TooltipContent>
    </Tooltip>
  )
}
