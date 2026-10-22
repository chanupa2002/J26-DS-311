import { Check, Trophy } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import { scoreOutOf100, titleCaseLivelihood } from "../utils"

export function RecommendationList({ recommendations = [], chosenLivelihood }) {
  if (!recommendations.length) return null

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Recommendations
      </h3>
      <div className="grid gap-4 lg:grid-cols-3">
        {recommendations.map((recommendation, index) => {
          const percent = scoreOutOf100(recommendation.score)
          const chosen = recommendation.livelihood === chosenLivelihood
          return (
            <Card
              key={`${recommendation.livelihood}-${index}`}
              className={chosen ? "border-primary/50" : undefined}
            >
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <Badge variant="outline">#{index + 1}</Badge>
                  {chosen && (
                    <Badge>
                      <Check /> Chosen
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
        })}
      </div>
    </section>
  )
}
