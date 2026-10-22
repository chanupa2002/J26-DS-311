import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

/** A YYYY-MM-DD date input with help text and an error message under it. */
export function DateField({ id, label, help, value, onChange, min, max, error }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="leading-snug">
        {label}
      </Label>
      <Input
        id={id}
        type="date"
        value={value}
        min={min}
        max={max}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={`${id}-help`}
        aria-invalid={Boolean(error) || undefined}
        className={cn(error && "border-destructive")}
      />
      <p id={`${id}-help`} className="text-[11px] text-muted-foreground">
        {help}
      </p>
      {error && (
        <p role="alert" className="text-[11px] text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
