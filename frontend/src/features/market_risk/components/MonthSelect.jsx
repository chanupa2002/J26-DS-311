import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { shortMonth } from "./v2format"

/** Month picker over the months the API says it has data for. */
export function MonthSelect({ id = "month", months = [], value, onChange, disabled }) {
  const options = value && !months.includes(value) ? [...months, value] : months
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id} className="shrink-0">
        Monitoring month
      </Label>
      <Select value={value || undefined} onValueChange={onChange} disabled={disabled || !options.length}>
        <SelectTrigger id={id} className="w-36">
          <SelectValue placeholder="Latest" />
        </SelectTrigger>
        <SelectContent>
          {[...options].reverse().map((month) => (
            <SelectItem key={month} value={month}>
              {shortMonth(month)}
              {!months.includes(month) && " (no data)"}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
