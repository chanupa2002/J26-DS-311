import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { BLANK, VISIT_MONTH_HELP } from "../constants"

function monthLabel(month) {
  const [year, number] = month.split("-").map(Number)
  const name = new Date(year, number - 1, 1).toLocaleString("en", { month: "long", year: "numeric" })
  return `${name} (${month})`
}

/** Visit month (not a model feature): with the category it selects the market and macro values. */
export function VisitMonthField({ value, onChange, months }) {
  const id = "risk-visit-month"
  const options = months.data || []

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="leading-snug">
        Visit month
      </Label>
      <Select
        value={value || BLANK}
        onValueChange={(next) => onChange(next === BLANK ? "" : next)}
        disabled={!options.length}
      >
        <SelectTrigger id={id} aria-describedby={`${id}-help`}>
          <SelectValue placeholder={months.isPending ? "Loading months…" : "Not specified"} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={BLANK}>Not specified</SelectItem>
          {options.map((month) => (
            <SelectItem key={month} value={month}>
              {monthLabel(month)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p id={`${id}-help`} className="text-[11px] text-muted-foreground">
        {VISIT_MONTH_HELP}
      </p>
      {months.isError && (
        <p className="flex items-center gap-2 text-[11px] text-destructive">
          The months could not be loaded.
          <Button type="button" variant="outline" size="sm" className="h-6 px-2" onClick={() => months.refetch()}>
            Retry
          </Button>
        </p>
      )}
    </div>
  )
}
