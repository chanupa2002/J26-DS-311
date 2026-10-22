import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

import { BLANK } from "../constants"

/**
 * One feature input: a select when `choice` ({ options, blank }) is given, else a number field.
 * The label is the backend description; the F_* name is shown underneath.
 */
export function FeatureField({ name, description, value, onChange, choice, invalid }) {
  const id = `risk-feature-${name}`
  const hintId = `${id}-name`
  // Keep an unexpected value (e.g. from router state) selectable instead of hiding it.
  const options =
    choice && value !== "" && !choice.options.some((option) => option.value === value)
      ? [...choice.options, { value, label: value }]
      : choice?.options

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="leading-snug">
        {description || name}
      </Label>
      {choice ? (
        <Select
          value={value === "" ? BLANK : value}
          onValueChange={(next) => onChange(next === BLANK ? "" : next)}
        >
          <SelectTrigger id={id} aria-describedby={hintId}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={BLANK}>{choice.blank}</SelectItem>
            {options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <Input
          id={id}
          type="number"
          step="any"
          inputMode="decimal"
          placeholder="blank"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby={hintId}
          aria-invalid={invalid || undefined}
          className={cn(invalid && "border-destructive")}
        />
      )}
      <p id={hintId} className="font-mono text-[11px] text-muted-foreground">
        {name}
        {invalid && <span className="ml-2 text-destructive">not a number</span>}
      </p>
    </div>
  )
}
