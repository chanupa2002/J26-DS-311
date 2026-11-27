import { SearchX } from "lucide-react"
import { forwardRef } from "react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"

import { DraftTag } from "./DraftTag"
import { SuggestionBody } from "./SuggestionBody"
import { MISSING_ANSWERS_RULE, NO_GUIDANCE_RULE } from "./v2format"

/**
 * Level B suggestion. Z1 ("no official guidance found") and Z0 (missing answers) are dashed cards
 * without sources.
 */
export const ActionCard = forwardRef(function ActionCard({ item, householdKey }, ref) {
  const noGuidance = item.rule_id === NO_GUIDANCE_RULE
  const dashed = noGuidance || item.rule_id === MISSING_ANSWERS_RULE
  const titleId = `action-${item.rule_id}-title`
  return (
    <Card className={dashed ? "border-2 border-dashed shadow-none" : undefined} aria-labelledby={titleId}>
      <CardHeader className="space-y-2 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium">{item.action_category}</span>
          {item.draft && <DraftTag />}
        </div>
        <h3 id={titleId} ref={ref} tabIndex={-1} className="flex gap-2 font-medium leading-snug focus-visible:outline-2 focus-visible:outline-ring">
          {noGuidance && <SearchX className="mt-0.5 size-4 shrink-0" aria-hidden="true" />}
          {noGuidance ? "No official guidance found – refer to the officer" : item.action_en}
        </h3>
      </CardHeader>
      <CardContent>
        <SuggestionBody item={item} householdKey={householdKey} />
      </CardContent>
    </Card>
  )
})
