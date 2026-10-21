import { Info } from "lucide-react"

import { ScoreRange } from "@/components/explain/ScoreRange"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { scoreOutOf100 } from "../utils"

const SUB_SCORES = [
  ["profitability", "Profitability"],
  ["market", "Market"],
  ["area", "Area"],
  ["resilience", "Resilience"],
]

export function ViabilityCard({ viability }) {
  if (!viability) return null

  const score = scoreOutOf100(viability.score)
  const low = scoreOutOf100(viability.low)
  const high = scoreOutOf100(viability.high)

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Viability</CardTitle>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="How viability is calculated"
            >
              <Info className="size-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">
            Equal weights of 25% are used for each sub-score. The range comes
            from 1,000 weight variations.
          </TooltipContent>
        </Tooltip>
      </CardHeader>
      <CardContent className="space-y-6">
        <ScoreRange
          score={`${score.toFixed(1)} / 100`}
          low={low.toFixed(1)}
          high={high.toFixed(1)}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {SUB_SCORES.map(([key, label]) => {
            const value = scoreOutOf100(viability[key])
            return (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>{label}</span>
                  <span className="font-medium">{value.toFixed(1)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${value}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
