import { CalendarClock, ClipboardList } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import { DraftTag } from "./DraftTag"
import { SuggestionBody } from "./SuggestionBody"
import { INCOMPLETE_RULE } from "./v2format"

/** Level A: the one follow-up decision for this household, shown first and larger. */
export function FollowUpBanner({ item, householdKey }) {
  const incomplete = item.rule_id === INCOMPLETE_RULE
  return (
    <Card className="border-2 border-primary/60" aria-labelledby="follow-up-title">
      <CardHeader className="space-y-1 pb-3">
        <p className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <ClipboardList className="size-4" aria-hidden="true" />
          Main follow-up
          {item.draft && <DraftTag />}
        </p>
        <CardTitle
          id="follow-up-title"
          tabIndex={-1}
          className="text-lg focus-visible:outline-2 focus-visible:outline-ring"
        >
          {item.action_category}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {incomplete && (
          <p role="note" className="rounded-md border-l-4 border-primary bg-muted p-3 text-sm font-medium">
            Complete the visit form first – no actions are suggested from an incomplete form.
          </p>
        )}
        <p className="text-base">{item.action_en}</p>
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <CalendarClock className="size-4 shrink-0" aria-hidden="true" />
          {item.timing_days !== null && item.timing_days !== undefined
            ? `Timing: within ${item.timing_days} ${item.timing_days === 1 ? "day" : "days"}`
            : "Timing: to be set by the supervisor"}
        </p>
        <SuggestionBody item={item} householdKey={householdKey} decisionOpen />
      </CardContent>
    </Card>
  )
}
