import { ChevronDown, Info, Lightbulb } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

import { useV2Recommendations } from "../hooks"
import { ActionCard } from "./ActionCard"
import { FollowUpBanner } from "./FollowUpBanner"
import { InShort } from "./InShort"
import { PlanList } from "./PlanList"
import { V2PageState } from "./V2PageState"
import { errorKind, INCOMPLETE_RULE } from "./v2format"

const FIRST_CARDS = 3
const SOURCE_LABEL = {
  "rules+retrieval": "Rules + official circulars",
  "rules+retrieval+llm": "Rules + official circulars + AI summary",
}

function Calm({ children }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
        <Info className="size-5 shrink-0" aria-hidden="true" />
        <p>{children}</p>
      </CardContent>
    </Card>
  )
}

function Loading() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading suggestions">
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  )
}

function focusTitle(id) {
  const target = document.getElementById(id)
  target?.scrollIntoView({ block: "start", behavior: "smooth" })
  target?.focus({ preventScroll: true })
}

/** "Suggested actions" on the household page: follow-up first, then action cards (FR4/FR5/FR7). */
export function SuggestedActions({ householdKey }) {
  const query = useV2Recommendations(householdKey)
  const [showAll, setShowAll] = useState(false)
  const firstHidden = useRef(null)
  const focusHidden = useRef(false)
  const pendingJump = useRef(null)

  useEffect(() => {
    if (!showAll) return
    if (pendingJump.current) {
      focusTitle(pendingJump.current)
      pendingJump.current = null
    } else if (focusHidden.current) {
      firstHidden.current?.focus()
    }
    focusHidden.current = false
  }, [showAll])

  // Plan list link: open the hidden cards first if needed, then scroll to the card and focus its title.
  const jump = (titleId, actions) => {
    const index = actions.findIndex((item) => `action-${item.rule_id}-title` === titleId)
    if (index >= FIRST_CARDS && !showAll) {
      pendingJump.current = titleId
      setShowAll(true)
    } else {
      focusTitle(titleId)
    }
  }

  let content
  if (query.isPending) content = <Loading />
  else if (query.isError) {
    const kind = errorKind(query.error)
    if (kind === "unavailable") content = <Calm>Suggestions are not available on this server yet.</Calm>
    else if (kind === "not-found") content = <Calm>Household not found.</Calm>
    else content = <V2PageState error={query.error} onRetry={() => query.refetch()} />
  } else {
    const data = query.data
    const incomplete = data.follow_up?.rule_id === INCOMPLETE_RULE
    const actions = incomplete ? [] : data.actions
    const items = [data.follow_up, ...actions].filter(Boolean)
    const decided = items.filter((item) => item.decision).length
    const anyDraft = items.some((item) => item.draft)
    const shown = showAll ? actions : actions.slice(0, FIRST_CARDS)
    const hiddenCount = actions.length - FIRST_CARDS
    content = (
      <div className="space-y-4">
        <InShort followUp={data.follow_up} actions={actions} />
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">
              {decided} of {items.length} decided
            </span>
            <span className="rounded-md border px-2 py-0.5 text-xs">{SOURCE_LABEL[data.generated_by] || data.generated_by}</span>
          </div>
          <p className="text-sm text-muted-foreground">{data.disclaimer}</p>
          {anyDraft && (
            <p role="note" className="flex gap-2 rounded-md border border-dashed p-2.5 text-sm">
              <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              Draft – the rule table is waiting for supervisor validation.
            </p>
          )}
          <PlanList followUp={data.follow_up} actions={actions} onJump={(titleId) => jump(titleId, actions)} />
        </div>
        {data.follow_up && <FollowUpBanner item={data.follow_up} householdKey={householdKey} />}
        {actions.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">
              Other suggestions ({actions.length})
            </h3>
            <div id="more-suggestions" className="space-y-3">
              {shown.map((item, index) => (
                <ActionCard
                  key={item.rule_id}
                  item={item}
                  householdKey={householdKey}
                  ref={index === FIRST_CARDS ? firstHidden : undefined}
                />
              ))}
            </div>
            {hiddenCount > 0 && (
              <Button
                type="button"
                variant="outline"
                aria-expanded={showAll}
                aria-controls="more-suggestions"
                onClick={() => {
                  focusHidden.current = !showAll
                  setShowAll(!showAll)
                }}
              >
                <ChevronDown className={`size-4 transition-transform ${showAll ? "rotate-180" : ""}`} aria-hidden="true" />
                {showAll
                  ? "Show fewer suggestions"
                  : `Show ${hiddenCount} more ${hiddenCount === 1 ? "suggestion" : "suggestions"}`}
              </Button>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <section className="space-y-3" aria-labelledby="suggested-actions-title">
      <h2 id="suggested-actions-title" className="flex items-center gap-2 text-lg font-semibold">
        <Lightbulb className="size-5" aria-hidden="true" />
        Suggested actions
      </h2>
      {content}
    </section>
  )
}
