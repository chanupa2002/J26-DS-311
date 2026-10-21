import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { IDENTIFY_EXAMPLES, SIGNAL_OPTIONS, SIGNALS } from "../constants"

export function SignalForm({ values, onChange, onSubmit, onReset, pending }) {
  const setValue = (key, value) => onChange({ ...values, [key]: value })

  return (
    <Card>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit()
        }}
      >
        <CardHeader>
          <CardTitle>Current-visit answers</CardTitle>
          <CardDescription>
            Choose an answer for each question. Leave a question as "Not
            answered" if it was not asked.
          </CardDescription>
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <span className="text-xs text-muted-foreground">Examples:</span>
            {IDENTIFY_EXAMPLES.map((example) => (
              <Button
                key={example.label}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onChange({ ...example.values })}
              >
                {example.label}
              </Button>
            ))}
          </div>
        </CardHeader>

        <CardContent className="grid gap-5 sm:grid-cols-2">
          {SIGNALS.map((signal) => {
            const id = `risk-signal-${signal.key}`
            return (
              <div key={signal.key} className="space-y-2">
                <Label htmlFor={id}>{signal.label}</Label>
                <Select
                  value={values[signal.key]}
                  onValueChange={(value) => setValue(signal.key, value)}
                >
                  <SelectTrigger id={id} aria-describedby={`${id}-hint`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SIGNAL_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p id={`${id}-hint`} className="text-xs text-muted-foreground">
                  {signal.hint}
                </p>
              </div>
            )
          })}
        </CardContent>

        <CardFooter className="justify-end gap-2">
          <Button type="button" variant="outline" onClick={onReset}>
            Reset
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? "Checking…" : "Check risk"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
