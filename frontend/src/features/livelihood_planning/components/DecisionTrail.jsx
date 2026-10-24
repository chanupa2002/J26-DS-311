import {
  CheckCircle2,
  ChevronDown,
  Info,
  MapPin,
} from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

import {
  hasDisplayValue,
  scoreOutOf100,
  titleCaseLivelihood,
} from "../utils"

const FLAG_STYLES = {
  ok: {
    icon: CheckCircle2,
    className:
      "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  },
  note: {
    icon: Info,
    className: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  },
  warning: {
    icon: MapPin,
    className:
      "border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300",
  },
}

const HELP = {
  confidence:
    "Confidence shows whether enough evidence came from this exact district.",
  "based on wider district evidence":
    "Not enough records from this exact district, so wider district data was used.",
  "early signal":
    "This pattern is visible, but more local records would make it clearer.",
  "rank stability":
    "Rank stability shows how often the result stayed in place when the score weights changed.",
}

const DISPLAY_LABELS = {
  estimated: "Based on wider district evidence",
  "estimated facts": "Facts based on wider district evidence",
  weak: "Early signal",
}

const FLAG_LABELS = {
  ok: "OK",
  note: "Note",
  warning: "Needs a local check",
}

const HIDDEN_DETAIL_KEYS = new Set(["ranking_score"])

function humanize(value) {
  const words = String(value).replaceAll("_", " ")
  return (
    DISPLAY_LABELS[words.toLowerCase()] ||
    words.replace(/\b\w/g, (letter) => letter.toUpperCase())
  )
}

function displayValue(value) {
  if (!hasDisplayValue(value)) return ""
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "number") return Number(value.toFixed(4)).toString()
  if (typeof value === "string") {
    if (value.toLowerCase() === "low") return "Needs a local check"
    if (value.toLowerCase() === "weak") return "Early signal"
    return value.replace(/\(weak signal\)/gi, "(early signal)")
  }
  return String(value)
}

function hasDetailValue(value) {
  if (Array.isArray(value)) return value.some(hasDetailValue)
  if (typeof value === "object" && value !== null) {
    return Object.entries(value).some(
      ([name, item]) =>
        !HIDDEN_DETAIL_KEYS.has(name) && hasDetailValue(item),
    )
  }
  return hasDisplayValue(value)
}

function DetailLabel({ name }) {
  const normalized = humanize(name).toLowerCase()
  const helpKey = Object.keys(HELP).find((key) => normalized.includes(key))

  if (!helpKey) return <span>{humanize(name)}</span>

  return (
    <span className="inline-flex items-center gap-1">
      {humanize(name)}
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="rounded-sm text-muted-foreground hover:text-foreground"
            aria-label={`About ${humanize(name)}`}
          >
            <Info className="size-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-64">{HELP[helpKey]}</TooltipContent>
      </Tooltip>
    </span>
  )
}

function DetailValue({ value }) {
  if (Array.isArray(value)) {
    const visibleItems = value.filter(hasDetailValue)
    if (!visibleItems.length) return null
    if (
      visibleItems.every(
        (item) => typeof item !== "object" || item === null,
      )
    ) {
      return <span>{visibleItems.map(displayValue).join(", ")}</span>
    }
    return (
      <div className="grid gap-2 sm:grid-cols-2">
        {visibleItems.map((item, index) => (
          <div
            key={`${index}-${JSON.stringify(item)}`}
            className="rounded-md border bg-background/70 p-3"
          >
            <DetailObject value={item} />
          </div>
        ))}
      </div>
    )
  }
  if (typeof value === "object" && value !== null) {
    return <DetailObject value={value} />
  }
  return <span className="break-words font-medium">{displayValue(value)}</span>
}

function DetailObject({ value }) {
  const entries = Object.entries(value).filter(
    ([name, item]) =>
      !HIDDEN_DETAIL_KEYS.has(name) && hasDetailValue(item),
  )
  if (!entries.length) return null

  return (
    <dl className="grid gap-2 text-sm">
      {entries.map(([name, item]) => (
        <div
          key={name}
          className="grid gap-1 sm:grid-cols-[minmax(9rem,0.45fr)_1fr] sm:gap-3"
        >
          <dt className="text-muted-foreground">
            <DetailLabel name={name} />
          </dt>
          <dd className="min-w-0">
            <DetailValue value={item} />
          </dd>
        </div>
      ))}
    </dl>
  )
}

function ScoreBars({ scores }) {
  const visibleScores = Array.isArray(scores)
    ? scores.filter(hasDisplayValue)
    : []
  if (!visibleScores.length) return null

  return (
    <div className="space-y-3">
      {visibleScores.map((item) => {
        const percentage = Math.max(
          0,
          Math.min(100, Number(item.percentage) || 0),
        )
        return (
          <div key={`${item.rank}-${item.livelihood}`} className="space-y-1.5">
            <div className="flex items-start justify-between gap-3 text-sm">
              <span
                className={
                  item.top_three ? "font-medium" : "text-muted-foreground"
                }
              >
                {item.rank}. {titleCaseLivelihood(item.livelihood)}
              </span>
              <span className="shrink-0 tabular-nums">
                {percentage.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full",
                  item.top_three ? "bg-primary" : "bg-muted-foreground/35",
                )}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ViabilityBars({ details }) {
  const parts = details?.parts
  const visibleParts =
    parts && typeof parts === "object"
      ? Object.entries(parts).filter(([, value]) => hasDisplayValue(value))
      : []
  const hasOverall = hasDisplayValue(details?.overall_score)
  const hasLow = hasDisplayValue(details?.range?.low)
  const hasHigh = hasDisplayValue(details?.range?.high)

  if (!visibleParts.length && !hasOverall && !hasLow && !hasHigh) return null

  const low = hasLow ? scoreOutOf100(details.range.low) : null
  const high = hasHigh ? scoreOutOf100(details.range.high) : null
  const overall = hasOverall ? scoreOutOf100(details.overall_score) : null

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {visibleParts.map(([name, rawValue]) => {
          const value = scoreOutOf100(rawValue)
          return (
            <div key={name} className="space-y-1.5">
              <div className="flex justify-between gap-3 text-sm">
                <span>{humanize(name)}</span>
                <span className="tabular-nums">{value.toFixed(1)}</span>
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
      {(hasOverall || hasLow || hasHigh) && (
        <div className="rounded-md border bg-background/70 p-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            {hasOverall && <span>Overall {overall.toFixed(1)}</span>}
            {(hasLow || hasHigh) && (
              <span className="text-muted-foreground">
                {hasLow && hasHigh
                  ? `Range ${low.toFixed(1)} to ${high.toFixed(1)}`
                  : hasLow
                    ? `Range from ${low.toFixed(1)}`
                    : `Range up to ${high.toFixed(1)}`}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function remainingDetails(step) {
  const details = step.details || {}
  const omittedKeys = new Set()

  if (step.id === "recommendation-scoring") omittedKeys.add("scores")
  if (step.id === "swot-viability") {
    omittedKeys.add("parts")
    omittedKeys.add("overall_score")
    omittedKeys.add("range")
  }
  return Object.fromEntries(
    Object.entries(details).filter(([key]) => !omittedKeys.has(key)),
  )
}

function hasStepDetails(step) {
  const details = step.details || {}
  if (hasDetailValue(remainingDetails(step))) return true
  if (step.id === "recommendation-scoring") {
    return hasDetailValue(details.scores)
  }
  if (step.id === "swot-viability") {
    return hasDisplayValue({
      parts: details.parts,
      overall_score: details.overall_score,
      range: details.range,
    })
  }
  return false
}

function StepDetails({ step }) {
  const details = step.details || {}
  const remaining = remainingDetails(step)

  return (
    <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
      {step.id === "recommendation-scoring" && (
        <ScoreBars scores={details.scores} />
      )}
      {step.id === "swot-viability" && <ViabilityBars details={details} />}
      {Object.keys(remaining).length > 0 && <DetailObject value={remaining} />}
    </div>
  )
}

function TrailStep({ step, last }) {
  const [open, setOpen] = useState(false)
  const style = FLAG_STYLES[step.flag] || FLAG_STYLES.note
  const Icon = style.icon
  const showDetails = hasStepDetails(step)

  return (
    <div className="relative grid grid-cols-[2rem_minmax(0,1fr)] gap-3 pb-6 last:pb-0">
      {!last && (
        <div
          className="absolute bottom-0 left-4 top-8 w-px bg-border"
          aria-hidden="true"
        />
      )}
      <div
        className={cn(
          "relative z-10 flex size-8 items-center justify-center rounded-full border",
          style.className,
        )}
      >
        <Icon className="size-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 space-y-2 pt-0.5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="space-y-1">
            <h4 className="font-medium">{step.title}</h4>
            <p className="text-sm text-muted-foreground">{step.summary}</p>
          </div>
          <Badge variant="outline" className={style.className}>
            {FLAG_LABELS[step.flag] || humanize(step.flag)}
          </Badge>
        </div>
        {showDetails && (
          <Collapsible open={open} onOpenChange={setOpen}>
            <CollapsibleTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="-ml-3"
              >
                {open ? "Hide numbers" : "Show numbers"}
                <ChevronDown
                  className={cn("transition-transform", open && "rotate-180")}
                />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <StepDetails step={step} />
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  )
}

/**
 * @param {{ trail?: object | null, defaultOpen?: boolean, showMissing?: boolean }} props
 */
export function DecisionTrail({
  trail,
  defaultOpen = false,
  showMissing = false,
}) {
  const steps = [
    ...(trail?.recommendation?.steps || []),
    ...(trail?.swot?.steps || []),
  ]

  if (!trail || !steps.length) {
    if (!showMissing) return null
    return (
      <Card>
        <CardContent className="space-y-2 p-5">
          <h3 className="font-semibold">How was this decided?</h3>
          <p className="text-sm text-muted-foreground">
            No decision log was saved for this older assessment.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Collapsible defaultOpen={defaultOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            className="group h-auto w-full justify-between rounded-xl px-5 py-4 text-left"
          >
            <span className="font-semibold">How was this decided?</span>
            <ChevronDown className="transition-transform group-data-[state=open]:rotate-180" />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="border-t p-5 sm:p-6">
            {steps.map((step, index) => (
              <TrailStep
                key={step.id}
                step={step}
                last={index === steps.length - 1}
              />
            ))}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}
