import { ConfidenceBadge } from "@/components/explain/ConfidenceBadge"
import { EstimatedTag } from "@/components/explain/EstimatedTag"
import { Badge } from "@/components/ui/badge"

import { titleCaseLivelihood } from "../utils"
import { RecommendationList } from "./RecommendationList"
import { SwotGrid } from "./SwotGrid"
import { ViabilityCard } from "./ViabilityCard"

export function AssessmentResult({ result, saved = false }) {
  if (!result) return null

  const chosenLivelihood =
    result.chosen_livelihood || result.recommendations?.[0]?.livelihood
  const notes = result.notes || []

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-xl border bg-card p-5 text-card-foreground shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-semibold">
          {titleCaseLivelihood(chosenLivelihood)}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge level={result.confidence} />
          <EstimatedTag estimated={result.viability?.estimated} />
          {saved && result.status === "draft" && (
            <Badge variant="secondary">Draft saved</Badge>
          )}
        </div>
      </div>

      <RecommendationList
        recommendations={result.recommendations}
        chosenLivelihood={chosenLivelihood}
      />

      {result.viability && <ViabilityCard viability={result.viability} />}
      {result.swot && <SwotGrid swot={result.swot} />}

      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Notes
        </h3>
        <div className="rounded-lg border bg-muted/40 p-4">
          {notes.length ? (
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {notes.map((note, index) => (
                <li key={`${note}-${index}`}>{note}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No notes.</p>
          )}
        </div>
      </section>
    </div>
  )
}
