import { BookOpen, ChevronDown, FileText, ShieldAlert } from "lucide-react"
import { useState } from "react"

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

import { DecisionForm } from "./DecisionForm"
import { SourceList } from "./SourceList"
import { SummarySteps } from "./SummarySteps"
import { MISSING_ANSWERS_RULE, NO_GUIDANCE_RULE, sourceAnchor } from "./v2format"

/** Linked SHAP factors; `withValues` adds the household's value ("Hours worked per day: 1–4 hours"). */
export function LinkedFactors({ factors = [], withValues = false }) {
  if (!factors.length) return null
  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">Linked to the 3-month warning:</p>
      <ul className="flex flex-wrap gap-1.5">
        {factors.map((factor) => (
          <li key={factor.label} className="rounded-full border bg-muted/50 px-2 py-0.5 text-xs">
            {withValues && factor.value ? `${factor.label}: ${factor.value}` : factor.label}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Z0: the unanswered questions behind the 3-month warning, as one plain line. */
function MissingAnswers({ factors = [] }) {
  if (!factors.length) return null
  return (
    <p className="text-sm">
      <span className="font-medium">Fill in at the next visit: </span>
      {factors.map((factor) => factor.label).join(", ")}
    </p>
  )
}

export function Guardrail({ text }) {
  if (!text) return null
  return (
    <p className="flex gap-2 rounded-md border-l-4 border-amber-500 bg-amber-50 p-2.5 text-sm text-amber-950 dark:bg-amber-500/10 dark:text-amber-100">
      <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span>
        <span className="font-semibold">Rule: </span>
        {text}
      </span>
    </p>
  )
}

/** Main evidence line: the rule table's plain-English reading of the cited circular. */
export function CircularSays({ text }) {
  if (!text) return null
  return (
    <p className="flex gap-2 text-sm">
      <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span>
        <span className="font-medium">What the circular says: </span>
        {text}
      </span>
    </p>
  )
}

function ResearchBasis({ text }) {
  if (!text) return null
  return (
    <Collapsible>
      <CollapsibleTrigger className="group flex items-center gap-1.5 rounded text-xs text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
        <BookOpen className="size-3.5" aria-hidden="true" />
        Why this type of action (research)
        <ChevronDown className="size-3.5 transition-transform group-data-[state=open]:rotate-180" aria-hidden="true" />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1.5 rounded-md bg-muted/50 p-2.5 text-xs">
        <p className="mb-1 font-medium">Background – not an official source</p>
        <p className="text-muted-foreground">{text}</p>
      </CollapsibleContent>
    </Collapsible>
  )
}

/**
 * Shared part of a suggestion, in reading order: why, what the circular says, linked factors,
 * rule, official sources, AI summary, research background, decision.
 */
export function SuggestionBody({ item, householdKey, decisionOpen = false }) {
  const noGuidance = item.rule_id === NO_GUIDANCE_RULE
  const missingAnswers = item.rule_id === MISSING_ANSWERS_RULE
  const [openIds, setOpenIds] = useState(() => new Set())
  const toggle = (chunkId) =>
    setOpenIds((current) => {
      const next = new Set(current)
      if (next.has(chunkId)) next.delete(chunkId)
      else next.add(chunkId)
      return next
    })
  const cite = (chunkId) => {
    setOpenIds((current) => new Set(current).add(chunkId))
    requestAnimationFrame(() => {
      const target = document.getElementById(sourceAnchor(item.rule_id, chunkId))
      target?.scrollIntoView({ block: "nearest", behavior: "smooth" })
      target?.focus({ preventScroll: true })
    })
  }
  return (
    <div className="space-y-3">
      <p className="text-sm">
        <span className="font-medium">Why: </span>
        {item.reason_label}
      </p>
      <CircularSays text={item.circular_says} />
      {missingAnswers ? (
        <MissingAnswers factors={item.related_factors} />
      ) : (
        <LinkedFactors factors={item.related_factors} withValues={noGuidance} />
      )}
      {noGuidance ? (
        <p className="text-sm">
          These factors raise the 3-month risk, but no circular in the knowledge base gives an action for them –
          discuss with the officer.
        </p>
      ) : (
        <Guardrail text={item.guardrail} />
      )}
      <SourceList sources={item.sources} scope={item.rule_id} openIds={openIds} onToggle={toggle} />
      <SummarySteps steps={item.summary_steps} sources={item.sources} onCite={cite} />
      <ResearchBasis text={item.research_basis} />
      <DecisionForm
        key={item.decision?.created_at || "none"}
        householdKey={householdKey}
        ruleId={item.rule_id}
        saved={item.decision}
        defaultOpen={decisionOpen}
      />
    </div>
  )
}
