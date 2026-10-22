import { cn } from "@/lib/utils"

import { PROBABILITY_BAR_CLASS, RISK_CLASSES } from "../constants"
import { formatPercent } from "../utils"

export function ProbabilityBars({ probabilities, predicted }) {
  return (
    <div className="space-y-3">
      {RISK_CLASSES.map((riskClass) => {
        const value = Number(probabilities?.[riskClass]) || 0
        const isPredicted = riskClass === predicted
        return (
          <div key={riskClass} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className={cn(isPredicted && "font-medium")}>{riskClass}</span>
              <span className={cn("tabular-nums", isPredicted ? "font-medium" : "text-muted-foreground")}>
                {formatPercent(value)}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-muted"
              role="meter"
              aria-label={`Probability ${riskClass}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(value * 100)}
            >
              <div
                className={cn("h-full rounded-full", PROBABILITY_BAR_CLASS[riskClass])}
                style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
