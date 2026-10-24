import { Check, Trophy } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import {
  hasDisplayValue,
  scoreOutOf100,
  titleCaseLivelihood,
} from "../utils"

export function RecommendationList({
  recommendations = [],
  viabilityPreview = [],
  selectedLivelihood,
  chosenLivelihood,
  onSelect,
}) {
  if (!recommendations.length) return null

  const activeLivelihood = selectedLivelihood || chosenLivelihood

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Recommendations
      </h3>
      <div className="grid gap-4 lg:grid-cols-3">
        {recommendations.map((recommendation, index) => {
          const percent = scoreOutOf100(recommendation.score)
          const selected = recommendation.livelihood === activeLivelihood
          const preview = viabilityPreview[index] || null
          const hasViabilityScore = hasDisplayValue(preview?.score)
          const hasViabilityLow = hasDisplayValue(preview?.low)
          const hasViabilityHigh = hasDisplayValue(preview?.high)
          const showPreview = Boolean(
            preview &&
              (hasViabilityScore ||
                hasViabilityLow ||
                hasViabilityHigh ||
                preview.estimated === true),
          )
          const card = (
            <Card
              key={`${recommendation.livelihood}-${index}`}
              className={
                selected
                  ? onSelect
                    ? "h-full border-primary ring-2 ring-primary/20"
                    : "h-full border-primary/50"
                  : "h-full"
              }
            >
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <Badge variant="outline">#{index + 1}</Badge>
                  {selected && (
                    <Badge>
                      <Check /> {onSelect ? "Selected" : "Chosen"}
                    </Badge>
                  )}
                </div>
                <CardTitle className="text-base leading-snug">
                  {titleCaseLivelihood(recommendation.livelihood)}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Score</span>
                    <span className="font-medium">{percent.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </div>
                {showPreview && (
                  <div className="rounded-md border bg-muted/30 p-3 text-sm">
                    <div className="space-y-1">
                      {hasViabilityScore && (
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-muted-foreground">
                            Viability
                          </span>
                          <span className="font-medium">
                            {scoreOutOf100(preview.score).toFixed(1)} / 100
                          </span>
                        </div>
                      )}
                      {(hasViabilityLow || hasViabilityHigh) && (
                        <p className="text-xs text-muted-foreground">
                          {hasViabilityLow && hasViabilityHigh
                            ? `Range ${scoreOutOf100(preview.low).toFixed(1)} to ${scoreOutOf100(preview.high).toFixed(1)}`
                            : hasViabilityLow
                              ? `Range from ${scoreOutOf100(preview.low).toFixed(1)}`
                              : `Range up to ${scoreOutOf100(preview.high).toFixed(1)}`}
                        </p>
                      )}
                      {preview.estimated && (
                        <p className="text-xs text-amber-700 dark:text-amber-300">
                          Based on wider district evidence
                        </p>
                      )}
                    </div>
                  </div>
                )}
                {recommendation.reasons?.length > 0 && (
                  <ul className="flex flex-wrap gap-2">
                    {recommendation.reasons.map((reason) => (
                      <li
                        key={reason}
                        className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                      >
                        <Trophy className="size-3" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )
          if (!onSelect) return card
          return (
            <button
              key={`${recommendation.livelihood}-${index}`}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(recommendation.livelihood)}
              className="h-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              {card}
            </button>
          )
        })}
      </div>
    </section>
  )
}
