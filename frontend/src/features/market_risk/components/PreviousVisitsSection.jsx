import { Check, ChevronDown, Pencil, Plus, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

import {
  BLANK,
  MAX_PREVIOUS_VISITS,
  PREVIOUS_VISIT_ANSWERS,
  PREVIOUS_VISIT_MONTH_RANGE,
  PREVIOUS_VISITS_HELP,
  PREVIOUS_VISITS_NOTE,
  SIGNAL_OPTIONS,
} from "../constants"
import { monthLabel, monthsBefore, newPreviousVisit } from "../utils"

const ANSWER_TEXT = Object.fromEntries(SIGNAL_OPTIONS.map((option) => [option.value, option.label]))

function SmallSelect({ id, label, help, value, onChange, options, placeholder, disabled }) {
  return (
    <div className="min-w-0 space-y-1">
      <Label htmlFor={id} className="text-xs leading-snug">
        {label}
      </Label>
      <Select value={value || undefined} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger id={id} aria-describedby={help ? `${id}-help` : undefined}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {help && (
        <p id={`${id}-help`} className="text-[11px] leading-snug text-muted-foreground">
          {help}
        </p>
      )}
    </div>
  )
}

/** One-line summary of a finished row. */
function summaryText(visit, risk) {
  const answers = PREVIOUS_VISIT_ANSWERS.map(
    ({ key, short }) => `${short}: ${ANSWER_TEXT[visit[key]] || ANSWER_TEXT[BLANK]}`,
  )
  return [monthLabel(visit.month), ...answers, `Risk: ${risk || "…"}`].join(" · ")
}

function StatusLine({ status }) {
  if (!status) return null
  if (status.kind === "waiting") {
    return <p role="status" className="text-sm text-muted-foreground">Calculating…</p>
  }
  if (status.kind === "updated") {
    return (
      <p role="status" className="text-sm text-emerald-700 dark:text-emerald-400">
        ✓ History updated ({status.count} previous {status.count === 1 ? "visit" : "visits"})
      </p>
    )
  }
  return (
    <p role="alert" className="text-sm text-destructive">
      {status.message}
    </p>
  )
}

/**
 * Earlier visits of the household (month + 4 answers), or "First visit for this household".
 * Rows are edited open and collapse to a summary with Done. Nothing is stored anywhere.
 * `errors` = { rows: { [id]: message }, section?: message } (client checks and backend 422s);
 * `riskByMonth` = risk class per month from the latest /history-features answer;
 * `status` = { kind: "waiting" | "updated" | "error", count?, message? } or null.
 */
export function PreviousVisitsSection({
  visitMonth,
  firstVisit,
  onFirstVisitChange,
  visits,
  onChange,
  errors,
  riskByMonth = {},
  status,
}) {
  const monthOptions = visitMonth ? monthsBefore(visitMonth, PREVIOUS_VISIT_MONTH_RANGE) : []
  const update = (id, patch) => onChange(visits.map((visit) => (visit.id === id ? { ...visit, ...patch } : visit)))
  const remove = (id) => onChange(visits.filter((visit) => visit.id !== id))
  const isValid = (visit) => Boolean(visit.month) && !errors?.rows?.[visit.id]
  const openInvalid = visits.some((visit) => visit.open && !isValid(visit))
  const canAdd = Boolean(visitMonth) && !firstVisit && visits.length < MAX_PREVIOUS_VISITS && !openInvalid

  return (
    <Collapsible defaultOpen className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm font-medium">Previous visits</p>
          <p className="text-xs text-muted-foreground">{PREVIOUS_VISITS_HELP}</p>
          <p className="text-xs text-muted-foreground">{PREVIOUS_VISITS_NOTE}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs tabular-nums text-muted-foreground">
            {firstVisit ? "first visit" : `${visits.length} / ${MAX_PREVIOUS_VISITS}`}
          </span>
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent className="space-y-4 border-t p-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={firstVisit}
            onChange={(event) => onFirstVisitChange(event.target.checked)}
          />
          First visit for this household (no previous visits)
        </label>

        {!visitMonth && !firstVisit && (
          <p className="text-sm text-muted-foreground">Enter the visit date first; earlier visits must be in months before it.</p>
        )}

        {!firstVisit &&
          visits.map((visit, index) => {
            const error = errors?.rows?.[visit.id]
            const valid = isValid(visit)

            if (!visit.open) {
              return (
                <div
                  key={visit.id}
                  className={cn(
                    "flex flex-col gap-2 rounded-md border bg-muted/30 px-3 py-2 sm:flex-row sm:items-center",
                    error && "border-destructive",
                  )}
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-sm">{summaryText(visit, riskByMonth[visit.month])}</p>
                    {error && (
                      <p role="alert" className="text-xs text-destructive">
                        {error}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button type="button" variant="ghost" size="sm" onClick={() => update(visit.id, { open: true })}>
                      <Pencil className="size-4" />
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(visit.id)}
                      aria-label={`Remove the ${monthLabel(visit.month)} visit`}
                    >
                      <Trash2 className="size-4" />
                      Remove
                    </Button>
                  </div>
                </div>
              )
            }

            const used = new Set(visits.filter((other) => other.id !== visit.id).map((other) => other.month))
            const options = monthOptions
              .filter((month) => !used.has(month) || month === visit.month)
              .map((month) => ({ value: month, label: monthLabel(month) }))
            if (visit.month && !options.some((option) => option.value === visit.month)) {
              options.unshift({ value: visit.month, label: `${monthLabel(visit.month)} (not before the visit)` })
            }
            const done = () => valid && update(visit.id, { open: false })
            return (
              <div
                key={visit.id}
                className={cn("space-y-2 rounded-md border p-3", error && "border-destructive")}
                onKeyDown={(event) => {
                  // Enter = Done; selects and buttons keep their own Enter behaviour.
                  if (event.key !== "Enter" || event.defaultPrevented) return
                  if (event.target.closest?.("button, [role='combobox']")) return
                  event.preventDefault()
                  done()
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-medium text-muted-foreground">Previous visit {index + 1}</p>
                  <div className="flex gap-1">
                    <Button type="button" size="sm" disabled={!valid} onClick={done}>
                      <Check className="size-4" />
                      Done
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(visit.id)}
                      aria-label={`Remove previous visit ${index + 1}`}
                    >
                      <Trash2 className="size-4" />
                      Remove
                    </Button>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  <SmallSelect
                    id={`${visit.id}-month`}
                    label="Month"
                    value={visit.month}
                    onChange={(month) => update(visit.id, { month })}
                    options={options}
                    placeholder="Choose month"
                    disabled={!visitMonth}
                  />
                  {PREVIOUS_VISIT_ANSWERS.map(({ key, label, help }) => (
                    <SmallSelect
                      key={key}
                      id={`${visit.id}-${key}`}
                      label={label}
                      help={help}
                      value={visit[key]}
                      onChange={(value) => update(visit.id, { [key]: value })}
                      options={SIGNAL_OPTIONS}
                    />
                  ))}
                </div>
                {error && (
                  <p role="alert" className="text-xs text-destructive">
                    {error}
                  </p>
                )}
              </div>
            )
          })}

        {errors?.section && (
          <p role="alert" className="text-sm text-destructive">
            {errors.section}
          </p>
        )}

        {!firstVisit && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!canAdd}
            onClick={() => onChange([...visits, newPreviousVisit()])}
          >
            <Plus className="size-4" />
            Add previous visit
            {visits.length >= MAX_PREVIOUS_VISITS && " (maximum 12)"}
          </Button>
        )}

        <StatusLine status={status} />
      </CollapsibleContent>
    </Collapsible>
  )
}
