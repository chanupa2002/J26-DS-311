import { zodResolver } from "@hookform/resolvers/zod"
import { Check, CircleCheck, Pencil, X } from "lucide-react"
import { useState } from "react"
import { Controller, useForm, useWatch } from "react-hook-form"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

import { useV2Decision } from "../hooks"
import { DECISION_LABELS, dateTimeText, dayText, errorKind } from "./v2format"

const NOTE_MAX = 500
const CHOICES = [
  { value: "accept", label: "Accept", icon: Check },
  { value: "modify", label: "Change", icon: Pencil },
  { value: "reject", label: "Not suitable", icon: X },
]

const schema = z.object({
  decision: z.enum(["accept", "modify", "reject"], { message: "Choose Accept, Change or Not suitable." }),
  note: z.string().max(NOTE_MAX, `The note can have at most ${NOTE_MAX} characters.`),
  planned_visit_date: z.string().refine((value) => value === "" || /^\d{4}-\d{2}-\d{2}$/.test(value), "Use a valid date."),
})

const ERROR_TEXT = {
  changed: "This suggestion changed – refresh the page.",
  "not-found": "This suggestion changed – refresh the page.",
  store: "Could not save the decision. Please try again later.",
  unavailable: "Could not save the decision. Please try again later.",
  other: "Could not save the decision. Please try again later.",
}

/** "Accepted · planned visit 3 Dec 2026 · saved 27 Nov 2026 13:04" */
export function SavedDecision({ decision }) {
  const parts = [
    DECISION_LABELS[decision.decision] || decision.decision,
    decision.planned_visit_date ? `planned visit ${dayText(decision.planned_visit_date)}` : null,
    `saved ${dateTimeText(decision.created_at)}`,
  ].filter(Boolean)
  return (
    <div className="min-w-0 space-y-0.5 text-sm">
      <p className="flex items-start gap-1.5 font-medium">
        <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden="true" />
        <span>{parts.join(" · ")}</span>
      </p>
      {decision.note && <p className="break-words pl-5.5 text-muted-foreground">Note: {decision.note}</p>}
    </div>
  )
}

function DecisionFields({ householdKey, ruleId, saved, onDone, onCancel }) {
  const mutation = useV2Decision(householdKey)
  const formId = `decision-${ruleId}`
  const { control, register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      decision: saved?.decision,
      note: saved?.note || "",
      planned_visit_date: saved?.planned_visit_date || "",
    },
  })
  const noteLength = (useWatch({ control, name: "note" }) || "").length

  const submit = handleSubmit(async (values) => {
    const body = { decision: values.decision }
    if (values.note.trim()) body.note = values.note.trim()
    if (values.planned_visit_date) body.planned_visit_date = values.planned_visit_date
    try {
      await mutation.mutateAsync({ ruleId, body })
      onDone()
    } catch {
      // shown below from mutation.error
    }
  })

  return (
    <form onSubmit={submit} className="space-y-3" aria-label="Record decision" noValidate>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Your decision</legend>
        <Controller
          control={control}
          name="decision"
          render={({ field }) => (
            <div className="flex flex-wrap gap-2">
              {CHOICES.map(({ value, label, icon: Icon }) => (
                <Button
                  key={value}
                  type="button"
                  size="sm"
                  variant={field.value === value ? "default" : "outline"}
                  aria-pressed={field.value === value}
                  onClick={() => field.onChange(value)}
                >
                  <Icon className="size-4" aria-hidden="true" />
                  {label}
                </Button>
              ))}
            </div>
          )}
        />
        {errors.decision && <p className="text-sm text-destructive">{errors.decision.message}</p>}
      </fieldset>
      <div className="grid gap-3 sm:grid-cols-[1fr_12rem]">
        <div className="space-y-1">
          <Label htmlFor={`${formId}-note`}>Note (optional)</Label>
          <textarea
            id={`${formId}-note`}
            rows={2}
            maxLength={NOTE_MAX}
            aria-describedby={`${formId}-count`}
            className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...register("note")}
          />
          <p id={`${formId}-count`} className="text-right text-xs text-muted-foreground">
            {noteLength}/{NOTE_MAX}
          </p>
          {errors.note && <p className="text-sm text-destructive">{errors.note.message}</p>}
        </div>
        <div className="space-y-1">
          <Label htmlFor={`${formId}-date`}>Planned visit (optional)</Label>
          <Input id={`${formId}-date`} type="date" {...register("planned_visit_date")} />
          {errors.planned_visit_date && <p className="text-sm text-destructive">{errors.planned_visit_date.message}</p>}
        </div>
      </div>
      {mutation.isError && (
        <p role="alert" className="text-sm text-destructive">
          {ERROR_TEXT[errorKind(mutation.error)]}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save decision"}
        </Button>
        {onCancel && (
          <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}

/**
 * FR7 decision on one suggestion. Closed behind "Record decision" (unless defaultOpen);
 * once saved, the saved line is shown with "Change decision".
 */
export function DecisionForm({ householdKey, ruleId, saved, defaultOpen = false, className }) {
  const [editing, setEditing] = useState(!saved && defaultOpen)
  return (
    <div className={cn("space-y-2 border-t pt-3", className)}>
      {editing ? (
        <DecisionFields
          householdKey={householdKey}
          ruleId={ruleId}
          saved={saved}
          onDone={() => setEditing(false)}
          onCancel={saved || !defaultOpen ? () => setEditing(false) : undefined}
        />
      ) : saved ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SavedDecision decision={saved} />
          <Button type="button" size="sm" variant="outline" onClick={() => setEditing(true)}>
            Change decision
          </Button>
        </div>
      ) : (
        <Button type="button" size="sm" variant="outline" onClick={() => setEditing(true)}>
          Record decision
        </Button>
      )}
    </div>
  )
}
