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
import { featureLabel } from "../utils"

/**
 * One feature input: a select when `choice` ({ options, blank }) is given, else a number field.
 * The label is the short plain label; the backend description and F_* name are in its tooltip.
 */
export function FeatureField({ name, description, value, onChange, choice, invalid, note }) {
  const id = `risk-feature-${name}`
  const hintId = `${id}-name`
  // Keep an unexpected value (e.g. from router state) selectable instead of hiding it.
  const options =
    choice && value !== "" && !choice.options.some((option) => option.value === value)
      ? [...choice.options, { value, label: value }]
      : choice?.options

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="leading-snug" title={description ? `${description} (${name})` : name}>
        {featureLabel(name)}
      </Label>
      {choice ? (
        <Select
          value={value === "" ? BLANK : value}
          onValueChange={(next) => onChange(next === BLANK ? "" : next)}
        >
          <SelectTrigger id={id}>
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
          aria-describedby={invalid ? hintId : undefined}
          aria-invalid={invalid || undefined}
          className={cn(invalid && "border-destructive")}
        />
      )}
      {note && <p className="text-[11px] leading-snug text-muted-foreground">{note}</p>}
      {invalid && (
        <p id={hintId} className="text-[11px] text-destructive">
          Not a number
        </p>
      )}
    </div>
  )
}
