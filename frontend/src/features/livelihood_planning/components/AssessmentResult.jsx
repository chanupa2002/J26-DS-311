import { ConfidenceBadge } from "@/components/explain/ConfidenceBadge"
import { EstimatedTag } from "@/components/explain/EstimatedTag"
import { Badge } from "@/components/ui/badge"
import { useState } from "react"

import { titleCaseLivelihood } from "../utils"
import { useSelectedSwot } from "../hooks/useSwot"
import { DecisionTrail } from "./DecisionTrail"
import { PageState } from "./PageState"
import { RecommendationList } from "./RecommendationList"
import { SwotGrid } from "./SwotGrid"
import { ViabilityCard } from "./ViabilityCard"

export function AssessmentResult({
  result,
  saved = false,
  trailDefaultOpen = false,
  showMissingTrail = false,
  profile,
  selectable = false,
}) {
  const initialLivelihood =
    result?.selected_livelihood ||
    result?.chosen_livelihood ||
    result?.recommendations?.[0]?.livelihood
  const [selectedLivelihood, setSelectedLivelihood] = useState(
    initialLivelihood,
  )
  const needsSelectedSwot = Boolean(
    selectable &&
      profile &&
      selectedLivelihood &&
      (selectedLivelihood !== initialLivelihood || !result?.swot),
  )
  const selectedSwot = useSelectedSwot(
    profile,
    selectedLivelihood,
    needsSelectedSwot,
  )
  const selectedResult = needsSelectedSwot ? selectedSwot.data : result
  const notes = selectedResult?.notes || []
  const recommendationTrail = result?.decision_trail?.recommendation
  const swotTrail = selectedResult?.decision_trail?.swot
  const decisionTrail = recommendationTrail
    ? {
        version: result?.decision_trail?.version || 1,
        recommendation: recommendationTrail,
        ...(swotTrail ? { swot: swotTrail } : {}),
      }
    : selectedResult?.decision_trail
  const swotPending = needsSelectedSwot && selectedSwot.isPending
  const swotError = needsSelectedSwot && selectedSwot.isError

  if (!result) return null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-xl border bg-card p-5 text-card-foreground shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-semibold">
          {titleCaseLivelihood(selectedLivelihood)}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {selectedResult && !swotPending && (
            <>
              <ConfidenceBadge level={selectedResult.confidence} />
              <EstimatedTag estimated={selectedResult.viability?.estimated} />
            </>
          )}
          {saved && result.status === "draft" && (
            <Badge variant="secondary">Draft saved</Badge>
          )}
        </div>
      </div>

      <RecommendationList
        recommendations={result.recommendations}
        viabilityPreview={result.viability_preview}
        selectedLivelihood={selectedLivelihood}
        chosenLivelihood={result.chosen_livelihood}
        onSelect={selectable ? setSelectedLivelihood : undefined}
      />

      {swotPending && <PageState loading />}
      {swotError && (
        <PageState
          error={selectedSwot.error}
          onRetry={() => selectedSwot.refetch()}
        />
      )}
      {selectedResult && !swotPending && !swotError && (
        <>
          {selectedResult.viability && (
            <ViabilityCard viability={selectedResult.viability} />
          )}
          {selectedResult.swot && <SwotGrid swot={selectedResult.swot} />}
        </>
      )}
      <DecisionTrail
        trail={decisionTrail}
        defaultOpen={trailDefaultOpen}
        showMissing={showMissingTrail}
      />

      {selectedResult && !swotPending && !swotError && (
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
      )}
    </div>
  )
}
